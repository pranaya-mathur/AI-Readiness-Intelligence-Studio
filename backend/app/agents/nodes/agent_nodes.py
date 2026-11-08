import json
import logging
from typing import Any

from app.agents.state import AssessmentState
from app.core.config import settings
from app.services.evidence import EvidenceExtractor
from app.services.llm_router import LLMExecutionError, LLMRouter
from app.services.scoring import ScoringEngine

logger = logging.getLogger("AgentNodes")


def _analysis_mode() -> str:
    return "demo" if settings.DEMO_MODE else "real"


def _evidence_block(state: AssessmentState) -> str:
    package = state.evidence_package or {}
    if package.get("evidence_items"):
        # Rebuild prompt block cheaply from stored package
        from app.services.evidence import EvidenceItem, EvidencePackage

        items = [
            EvidenceItem(
                evidence_id=i.get("evidence_id", "ev_unknown"),
                document_id=i.get("document_id", ""),
                source_file=i.get("source_file", ""),
                signal_type=i.get("signal_type", ""),
                description=i.get("description", ""),
                excerpt=i.get("excerpt", ""),
                page_or_section=i.get("page_or_section"),
                evidence_tier=i.get("evidence_tier", "missing"),
                confidence_label=i.get("confidence_label", "uncalibrated"),
                related_dimensions=i.get("related_dimensions") or [],
            )
            for i in package.get("evidence_items", [])
        ]
        pkg = EvidencePackage(
            documents=package.get("documents") or [],
            evidence_items=items,
            missing_evidence=package.get("missing_evidence") or [],
            insufficient_evidence=bool(package.get("insufficient_evidence")),
            total_chars_analyzed=int(package.get("total_chars_analyzed") or 0),
            truncation_applied=bool(package.get("truncation_applied")),
            analysis_notes=package.get("analysis_notes") or [],
        )
        return pkg.prompt_block()
    return (
        "UNTRUSTED_DOCUMENT_CONTENT_BEGIN\n"
        "No verified document excerpts available.\n"
        "UNTRUSTED_DOCUMENT_CONTENT_END"
    )


def _sync_model_meta(state: AssessmentState) -> dict[str, Any]:
    summary = LLMRouter.session_summary()
    return {
        "analysis_mode": summary.get("execution_mode") or _analysis_mode(),
        "model_provider": summary.get("provider") or "none",
        "model_name": summary.get("model") or "none",
        "model_run_status": summary.get("status") or "not_started",
        "model_error": summary.get("error"),
        "model_run_history": summary.get("runs") or [],
    }


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(raw[start : end + 1])
                if isinstance(data, dict):
                    return data
        except Exception:
            return None
    return None


def _incomplete(state: AssessmentState, reason: str) -> dict[str, Any]:
    meta = _sync_model_meta(state)
    return {
        **meta,
        "analysis_incomplete": True,
        "incomplete_reason": reason,
        "logs": state.logs + [f"INCOMPLETE: {reason}"],
    }


# 1. Document Understanding Agent
def document_understanding_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Document Understanding...")
    documents = state.documents or []
    if not documents and state.extracted_text:
        documents = [
            {
                "filename": "consolidated_upload.txt",
                "text": state.extracted_text,
            }
        ]

    client_assertions = []
    if state.main_business_goals:
        client_assertions.append(f"Business goals: {state.main_business_goals}")
    client_assertions.extend([f"Pain point: {p}" for p in state.pain_points])
    client_assertions.extend([f"AI goal: {g}" for g in state.ai_goals])

    package = EvidenceExtractor.build_package(
        documents, client_assertions=client_assertions
    )
    signals = EvidenceExtractor.as_signal_rows(package)
    package_dict = package.to_dict()
    evidence_prompt = package.prompt_block()

    # Optional LLM enrichment — must cite evidence ids; never fabricate excerpts.
    enrichment: list[dict[str, Any]] = []
    try:
        prompt = f"""
You are the Document Understanding Agent for an evidence-driven readiness assessment.
Use ONLY the evidence package below. Do not invent filenames, page numbers, quotations, or metrics.
If evidence is insufficient, return an empty enrichment list and set insufficient_evidence=true.

Company Name: {state.company_name}
Industry: {state.industry}

{evidence_prompt}

Return JSON:
{{
  "insufficient_evidence": <bool>,
  "enrichment_signals": [
    {{
      "source_file": "<must match an evidence source_file>",
      "signal_type": "<type>",
      "description": "<finding tied to an excerpt; no fabrication>",
      "evidence_id": "<must match an evidence_id>",
      "evidence_tier": "model_inference",
      "confidence": 0.0
    }}
  ]
}}
"""
        raw = LLMRouter.generate_completion(prompt, require_json=True)
        data = _parse_json_object(raw) or {}
        for item in data.get("enrichment_signals") or []:
            eid = item.get("evidence_id")
            known_ids = {e.get("evidence_id") for e in signals}
            known_files = {e.get("source_file") for e in signals}
            if eid and eid in known_ids and item.get("source_file") in known_files:
                enrichment.append(
                    {
                        "source_file": item.get("source_file"),
                        "signal_type": item.get("signal_type") or "Model Inference",
                        "description": item.get("description") or "",
                        "confidence": 0.0,
                        "document_id": next(
                            (
                                s.get("document_id")
                                for s in signals
                                if s.get("evidence_id") == eid
                            ),
                            "",
                        ),
                        "excerpt": next(
                            (
                                s.get("excerpt")
                                for s in signals
                                if s.get("evidence_id") == eid
                            ),
                            "",
                        ),
                        "page_or_section": next(
                            (
                                s.get("page_or_section")
                                for s in signals
                                if s.get("evidence_id") == eid
                            ),
                            None,
                        ),
                        "evidence_tier": "model_inference",
                        "evidence_id": eid,
                    }
                )
    except LLMExecutionError as exc:
        if not settings.DEMO_MODE:
            return {
                **_incomplete(state, str(exc)),
                "evidence_package": package_dict,
                "extracted_signals": signals,
                "insufficient_evidence": package.insufficient_evidence,
                "current_node": "document_understanding",
            }
        logger.warning("Document enrichment skipped in demo: %s", exc)

    combined = signals + enrichment
    meta = _sync_model_meta(state)
    return {
        **meta,
        "documents": package.documents,
        "evidence_package": package_dict,
        "extracted_signals": combined,
        "insufficient_evidence": package.insufficient_evidence,
        "extracted_text": state.extracted_text,
        "logs": state.logs
        + [
            (
                f"Document Understanding extracted {len(combined)} evidence-backed signals "
                f"(insufficient={package.insufficient_evidence})."
            )
        ],
        "current_node": "document_understanding",
    }


# 2. Business Context Agent
def business_context_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Business Context...")
    if state.analysis_incomplete:
        return {"current_node": "business_context"}

    evidence_note = (
        "Insufficient verified document evidence; summarize intake only and state gaps."
        if state.insufficient_evidence
        else "Ground the summary in intake plus verified evidence; do not invent facts."
    )
    prompt = f"""
Generate a professional 3-sentence Executive Business Summary.
{evidence_note}
Company Name: {state.company_name}
Industry: {state.industry}
Goals: {state.main_business_goals}
Pain Points: {", ".join(state.pain_points)}
AI Goals: {", ".join(state.ai_goals)}

{_evidence_block(state)}
"""
    try:
        summary = LLMRouter.generate_completion(prompt)
    except LLMExecutionError as exc:
        if settings.DEMO_MODE:
            summary = (
                f"[DEMO_SIMULATED] {state.company_name} is exploring AI opportunities. "
                "This summary is simulated and not evidence-grounded model analysis. "
                "Collect verified documents before client delivery."
            )
        else:
            return _incomplete(state, str(exc))

    return {
        **_sync_model_meta(state),
        "business_summary": summary,
        "logs": state.logs
        + ["Business Context Agent synthesized company background and goals."],
        "current_node": "business_context",
    }


# 3. Process Bottleneck Agent
def process_bottleneck_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Process Bottleneck...")
    if state.analysis_incomplete:
        return {"current_node": "process_bottleneck"}

    prompt = f"""
Identify up to 2 process bottlenecks using intake and verified evidence only.
If evidence is insufficient, return bottlenecks with evidence_tier="missing" and clearly say evidence is insufficient.
Do not invent metrics, tools, or quotations.

Pain Points: {", ".join(state.pain_points)}
Departments: {", ".join(state.departments)}
Current Tools: {", ".join(state.current_tools)}
Goals: {state.main_business_goals}

{_evidence_block(state)}

JSON:
{{
  "bottlenecks": [
    {{
      "department": "<department or Unknown>",
      "process_name": "<name or Insufficient Evidence>",
      "bottleneck_description": "<description; state if inferred vs verified>",
      "ai_potential": "High|Medium|Low|Unknown",
      "evidence_refs": ["<evidence_id>"],
      "evidence_tier": "verified|client_assertion|model_inference|assumption|missing"
    }}
  ]
}}
"""
    try:
        raw = LLMRouter.generate_completion(prompt, require_json=True)
        data = _parse_json_object(raw) or {}
        bottlenecks = data.get("bottlenecks") or []
    except LLMExecutionError as exc:
        if settings.DEMO_MODE:
            bottlenecks = [
                {
                    "department": state.departments[0]
                    if state.departments
                    else "Operations",
                    "process_name": "[DEMO_SIMULATED] Manual Coordination",
                    "bottleneck_description": (
                        "[DEMO_SIMULATED] Simulated from intake pain points only."
                    ),
                    "ai_potential": "Unknown",
                    "evidence_tier": "assumption",
                    "evidence_refs": [],
                }
            ]
        else:
            return _incomplete(state, str(exc))
    except Exception:
        bottlenecks = [
            {
                "department": "Unknown",
                "process_name": "Insufficient Evidence",
                "bottleneck_description": (
                    "Could not validate bottlenecks from available evidence. "
                    "Additional process documentation is required."
                ),
                "ai_potential": "Unknown",
                "evidence_tier": "missing",
                "evidence_refs": [],
            }
        ]

    return {
        **_sync_model_meta(state),
        "bottlenecks": bottlenecks,
        "logs": state.logs
        + [f"Process Bottleneck Agent recorded {len(bottlenecks)} bottleneck entries."],
        "current_node": "process_bottleneck",
    }


# 4. AI Use Case Discovery Agent
def ai_use_case_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: AI Use Case Discovery...")
    if state.analysis_incomplete:
        return {"current_node": "ai_use_case"}

    prompt = f"""
Suggest up to 3 AI use cases mapped to departments.
Use bottlenecks + evidence. Do not fabricate document quotes or measured ROI.
If evidence is insufficient, mark confidence 0 and evidence_tier=missing/assumption.

Company Name: {state.company_name}
Current Tools: {", ".join(state.current_tools)}
Goals: {state.main_business_goals}
Compliance Requirements: {", ".join(state.compliance_requirements)}
Bottlenecks: {json.dumps(state.bottlenecks)}

{_evidence_block(state)}

JSON:
{{
  "use_cases": [
    {{
      "use_case_name": "<name>",
      "department": "<department>",
      "description": "<short explanation>",
      "value": "High|Medium|Low|Unknown",
      "complexity": "High|Medium|Low|Unknown",
      "risk": "High|Medium|Low|Unknown",
      "priority": "P1|P2|P3",
      "evidence": "<cite evidence_ids or state insufficient evidence>",
      "confidence": 0.0,
      "evidence_refs": ["<evidence_id>"],
      "evidence_tier": "verified|client_assertion|model_inference|assumption|missing",
      "estimate_flags": ["roi_unmeasured"]
    }}
  ]
}}
"""
    try:
        raw = LLMRouter.generate_completion(prompt, require_json=True)
        data = _parse_json_object(raw) or {}
        use_cases = data.get("use_cases") or []
    except LLMExecutionError as exc:
        if settings.DEMO_MODE:
            use_cases = [
                {
                    "use_case_name": "[DEMO_SIMULATED] Evidence Gathering Assistant",
                    "department": state.departments[0]
                    if state.departments
                    else "Operations",
                    "description": "Demo-only placeholder; not a client recommendation.",
                    "value": "Unknown",
                    "complexity": "Low",
                    "risk": "Medium",
                    "priority": "P3",
                    "evidence": "Insufficient verified evidence",
                    "confidence": 0.0,
                    "evidence_tier": "assumption",
                    "estimate_flags": ["demo_simulated", "roi_unmeasured"],
                }
            ]
        else:
            return _incomplete(state, str(exc))
    except Exception:
        use_cases = [
            {
                "use_case_name": "Insufficient Evidence — Discovery Deferred",
                "department": "Unknown",
                "description": (
                    "Use-case discovery cannot be completed without verified process and data evidence."
                ),
                "value": "Unknown",
                "complexity": "Unknown",
                "risk": "Unknown",
                "priority": "P3",
                "evidence": "missing",
                "confidence": 0.0,
                "evidence_tier": "missing",
                "estimate_flags": ["insufficient_evidence", "roi_unmeasured"],
            }
        ]

    # Force confidence to uncalibrated 0 unless explicitly reviewed later.
    for uc in use_cases:
        if "confidence" in uc:
            # Preserve numeric dashboard field but treat as uncalibrated estimate marker.
            try:
                uc["confidence"] = float(uc.get("confidence") or 0.0)
            except (TypeError, ValueError):
                uc["confidence"] = 0.0
        uc.setdefault("estimate_flags", ["uncalibrated_confidence", "roi_unmeasured"])

    return {
        **_sync_model_meta(state),
        "use_cases": use_cases,
        "logs": state.logs
        + [f"AI Use Case Discovery generated {len(use_cases)} opportunities."],
        "current_node": "ai_use_case",
    }


# 5. Readiness Scoring Agent (deterministic overall)
def readiness_scoring_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Readiness Scoring...")
    if state.analysis_incomplete:
        return {"current_node": "readiness_scoring"}

    scorecard = ScoringEngine.score(
        company_name=state.company_name,
        industry=state.industry,
        departments=state.departments,
        current_tools=state.current_tools,
        pain_points=state.pain_points,
        ai_goals=state.ai_goals,
        compliance_requirements=state.compliance_requirements,
        cloud_preference=state.cloud_preference,
        main_business_goals=state.main_business_goals,
        evidence_package=state.evidence_package,
        bottlenecks=state.bottlenecks,
        use_cases=state.use_cases,
    )

    # Optional narrative polish — never accept LLM overall score.
    interpretation = scorecard.readiness_interpretation
    try:
        prompt = f"""
Write a 3-sentence readiness interpretation for {state.company_name}.
Do not output scores. Do not invent metrics. Mention insufficient evidence if true={state.insufficient_evidence}.
Deterministic overall (for context only, do not recalculate): {scorecard.overall_score}
Missing evidence: {json.dumps(state.evidence_package.get("missing_evidence") or [])}
{_evidence_block(state)}
Return plain text only.
"""
        interpretation = LLMRouter.generate_completion(prompt)
        if settings.DEMO_MODE and not interpretation.startswith("[DEMO"):
            # Keep simulation marker when demo provider was used.
            summary = LLMRouter.session_summary()
            if summary.get("status") == "demo_simulated":
                interpretation = f"[DEMO_SIMULATED] {interpretation}"
    except LLMExecutionError:
        if not settings.DEMO_MODE and not scorecard.insufficient_evidence:
            # Scoring itself is deterministic; narrative failure is non-fatal if scores exist.
            pass

    flat = scorecard.flat_assessment_fields()
    flat["readiness_interpretation"] = interpretation
    flat["automation_potential_basis"] = scorecard.automation_potential_basis

    return {
        **_sync_model_meta(state),
        **flat,
        "logs": state.logs
        + [
            (
                f"Readiness Scoring used {scorecard.scoring_method} "
                f"({scorecard.rubric_version}). Overall={scorecard.overall_score}/100."
            )
        ],
        "current_node": "readiness_scoring",
    }


# 6. Risk & Governance Agent
def risk_governance_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Risk & Governance...")
    if state.analysis_incomplete:
        return {"current_node": "risk_governance"}

    prompt = f"""
Suggest up to 2 major AI risks and controls.
Do not claim controls are met unless evidence_tier=verified supports it.
Compliance Requirements: {", ".join(state.compliance_requirements)}
Current Tools: {", ".join(state.current_tools)}
Departments: {", ".join(state.departments)}
{_evidence_block(state)}

JSON:
{{
  "risks": [
    {{
      "risk_name": "<name>",
      "severity": "High|Medium|Low",
      "recommendation": "<recommendation>",
      "is_control_met": 0,
      "evidence_refs": [],
      "evidence_tier": "assumption|missing|verified|client_assertion|model_inference"
    }}
  ]
}}
"""
    try:
        raw = LLMRouter.generate_completion(prompt, require_json=True)
        data = _parse_json_object(raw) or {}
        risks = data.get("risks") or []
    except LLMExecutionError as exc:
        if settings.DEMO_MODE:
            risks = [
                {
                    "risk_name": "[DEMO_SIMULATED] Unverified Data Exposure",
                    "severity": "High",
                    "recommendation": "Keep DEMO_MODE outputs internal; require verified analysis before delivery.",
                    "is_control_met": 0,
                    "evidence_tier": "assumption",
                }
            ]
        else:
            return _incomplete(state, str(exc))
    except Exception:
        risks = [
            {
                "risk_name": "Insufficient Evidence for Risk Closure",
                "severity": "High",
                "recommendation": (
                    "Do not approve external AI processing until governance and security evidence is collected."
                ),
                "is_control_met": 0,
                "evidence_tier": "missing",
            }
        ]

    for risk in risks:
        # Never trust model claims that controls are met without verified evidence.
        if risk.get("evidence_tier") != "verified":
            risk["is_control_met"] = 0

    return {
        **_sync_model_meta(state),
        "risks": risks,
        "logs": state.logs
        + [f"Risk & Governance Agent added {len(risks)} risk register entries."],
        "current_node": "risk_governance",
    }


# 7. Roadmap Planning Agent
def roadmap_planning_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Roadmap Planning...")
    if state.analysis_incomplete:
        return {"current_node": "roadmap_planning"}

    prompt = f"""
Build a 30/60/90 day roadmap with 3 steps for {state.company_name}.
If evidence is insufficient, first steps must prioritize evidence collection.
Do not invent ROI percentages.
Departments: {", ".join(state.departments)}
Current Tools: {", ".join(state.current_tools)}
Main Goals: {state.main_business_goals}
Use Cases: {json.dumps(state.use_cases)}
{_evidence_block(state)}

JSON:
{{
  "roadmap": [
    {{
      "phase": "30-Day",
      "action_item": "<action>",
      "expected_impact": "<impact; mark estimates clearly>",
      "confidence": 0.0,
      "estimate_flags": ["uncalibrated_confidence"]
    }}
  ]
}}
"""
    try:
        raw = LLMRouter.generate_completion(prompt, require_json=True)
        data = _parse_json_object(raw) or {}
        roadmap = data.get("roadmap") or []
    except LLMExecutionError as exc:
        if settings.DEMO_MODE:
            roadmap = [
                {
                    "phase": "30-Day",
                    "action_item": "[DEMO_SIMULATED] Collect missing evidence and confirm scope.",
                    "expected_impact": "Estimate only — demo simulation.",
                    "confidence": 0.0,
                }
            ]
        else:
            return _incomplete(state, str(exc))
    except Exception:
        roadmap = [
            {
                "phase": "30-Day",
                "action_item": "Collect missing process, data, and governance evidence before pilot build.",
                "expected_impact": "Estimate: enables defensible scoring and pilot selection.",
                "confidence": 0.0,
                "estimate_flags": ["insufficient_evidence"],
            },
            {
                "phase": "60-Day",
                "action_item": "Run a human-reviewed discovery workshop and validate bottlenecks with owners.",
                "expected_impact": "Estimate: converts assumptions into verified findings.",
                "confidence": 0.0,
            },
            {
                "phase": "90-Day",
                "action_item": "Only then scope a bounded pilot with explicit success metrics and review gates.",
                "expected_impact": "Estimate: reduces delivery risk from unsupported claims.",
                "confidence": 0.0,
            },
        ]

    for item in roadmap:
        item["confidence"] = 0.0

    return {
        **_sync_model_meta(state),
        "roadmap_items": roadmap,
        "logs": state.logs
        + ["Roadmap Planning Agent created 30/60/90-day action steps."],
        "current_node": "roadmap_planning",
    }


# 8. Proposal Writing Agent
def proposal_writing_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Proposal Writing...")
    if state.analysis_incomplete:
        return {"current_node": "proposal_writing"}

    if state.insufficient_evidence and not settings.DEMO_MODE:
        pilot = {
            "name": "Evidence Completion Sprint",
            "department": "Operations",
            "why": (
                "Verified document evidence is insufficient for a defensible production pilot "
                "recommendation. Close evidence gaps first."
            ),
            "expected_impact": "Estimate only: improves evidence completeness prior to ROI claims.",
            "confidence": 0.0,
            "complexity": "Low",
            "estimated_duration_weeks": 4,
            "evidence_tier": "missing",
            "estimate_flags": ["insufficient_evidence", "roi_unmeasured"],
        }
        proposal = {
            "title": f"AI Enablement Strategy Proposal: {state.company_name}",
            "executive_summary": (
                f"{state.company_name} does not yet have sufficient verified evidence for a firm "
                "AI pilot recommendation. Next step is structured evidence collection with human review."
            ),
            "est_budget": "Estimate only — pending evidence",
            "roi_projection": "ROI assumption unavailable — not supported by measured data",
            "key_risks_acknowledged": [
                "Insufficient verified evidence",
                "Risk of over-claiming automation benefits",
            ],
            "next_step": "Upload process, data, and governance artifacts, then re-run analysis.",
        }
        return {
            **_sync_model_meta(state),
            "recommended_pilot": pilot,
            "proposal_summary": proposal,
            "logs": state.logs
            + ["Proposal Writing deferred firm pilot due to insufficient evidence."],
            "current_node": "proposal_writing",
        }

    prompt = f"""
Generate a commercially careful AI Enablement Proposal.
Mark budget and ROI as estimates unless measured data is present (it is not).
Do not invent document quotations.

Company: {state.company_name}
Industry: {state.industry}
Pain Points: {", ".join(state.pain_points)}
AI Goals: {", ".join(state.ai_goals)}
Compliance Requirements: {", ".join(state.compliance_requirements)}
Overall AI Readiness Score: {state.overall_score}/100
Use Cases: {json.dumps(state.use_cases)}
Bottlenecks: {json.dumps(state.bottlenecks)}
Risks: {json.dumps(state.risks)}
Roadmap: {json.dumps(state.roadmap_items)}
{_evidence_block(state)}

JSON:
{{
  "recommended_pilot": {{
    "name": "<use case name>",
    "department": "<department>",
    "why": "<justification grounded in evidence or explicitly assumed>",
    "expected_impact": "<mark as estimate>",
    "confidence": 0.0,
    "complexity": "Low|Medium|High|Unknown",
    "estimated_duration_weeks": 6,
    "estimate_flags": ["roi_unmeasured", "uncalibrated_confidence"]
  }},
  "proposal_summary": {{
    "title": "AI Enablement Strategy Proposal: {state.company_name}",
    "executive_summary": "<3 sentences>",
    "est_budget": "<estimate range; label as estimate>",
    "roi_projection": "<assumption labeled as estimate>",
    "key_risks_acknowledged": ["<risk 1>", "<risk 2>"],
    "next_step": "<single next action>"
  }}
}}
"""
    try:
        raw = LLMRouter.generate_completion(prompt, require_json=True)
        data = _parse_json_object(raw) or {}
        pilot = data.get("recommended_pilot") or {}
        proposal = data.get("proposal_summary") or {}
    except LLMExecutionError as exc:
        if settings.DEMO_MODE:
            pilot = {
                "name": "[DEMO_SIMULATED] Evidence-Gathering Sprint",
                "department": "Operations",
                "why": "Demo mode only.",
                "expected_impact": "Estimate only.",
                "confidence": 0.0,
                "complexity": "Low",
                "estimated_duration_weeks": 4,
            }
            proposal = {
                "title": f"[DEMO_SIMULATED] AI Enablement Strategy Proposal: {state.company_name}",
                "executive_summary": "[DEMO_SIMULATED] Simulated proposal — not client-ready.",
                "est_budget": "Estimate only",
                "roi_projection": "ROI assumption — not measured",
                "key_risks_acknowledged": ["Demo simulation"],
                "next_step": "Disable DEMO_MODE and configure a model provider.",
            }
        else:
            return _incomplete(state, str(exc))
    except Exception:
        return _incomplete(state, "Malformed proposal output from model")

    if "confidence" in pilot:
        pilot["confidence"] = 0.0
    pilot.setdefault("estimate_flags", ["roi_unmeasured", "uncalibrated_confidence"])

    return {
        **_sync_model_meta(state),
        "recommended_pilot": pilot,
        "proposal_summary": proposal,
        "logs": state.logs
        + ["Proposal Writing Agent produced pilot card with estimate flags."],
        "current_node": "proposal_writing",
    }


# 9. Report Generation Agent
def report_generation_node(state: AssessmentState) -> dict[str, Any]:
    logger.info("Running Node: Report Generation...")
    meta = _sync_model_meta(state)
    status_note = (
        "Assessment marked incomplete due to model/evidence failure."
        if state.analysis_incomplete
        else "Assessment pipeline synchronized."
    )
    return {
        **meta,
        "logs": state.logs + [f"Report Generation Agent: {status_note}"],
        "current_node": "report_generation",
    }
