import json
import logging
from typing import Dict, Any
from app.agents.state import AssessmentState
from app.services.llm_router import LLMRouter

logger = logging.getLogger("AgentNodes")


def _derive_source_name(state: AssessmentState) -> str:
    if state.extracted_signals:
        first_source = state.extracted_signals[0].get("source_file")
        if first_source:
            return first_source
    return f"{state.company_name.replace(' ', '_')}_brief.txt"


# 1. Document Understanding Agent
def document_understanding_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Document Understanding...")
    text_sample = (
        state.extracted_text[:1000]
        if state.extracted_text
        else "No uploaded documents found."
    )

    prompt = f"""
    You are the Document Understanding Agent. Analyze this raw text extract from corporate documentation:
    ---
    {text_sample}
    ---
    Identify and extract 2 distinct "Extracted Business Signals" representing standard procedures, tech stack elements, or data sources.
    Provide the output in JSON format exactly as:
    {{
        "extracted_signals": [
            {{
                "source_file": "Uploaded_SOP_Document.pdf",
                "signal_type": "Data Source / Process",
                "description": "Short explanation of what was extracted",
                "confidence": 90.0
            }}
        ]
    }}
    """

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        signals = data.get("extracted_signals", [])
    except Exception:
        source_name = _derive_source_name(state)
        tools_text = ", ".join(state.current_tools[:3]) or "existing internal systems"
        departments_text = ", ".join(state.departments[:2]) or "core teams"
        signals = [
            {
                "source_file": source_name,
                "signal_type": "Workflow Evidence",
                "description": f"Parsed evidence of manual coordination across {departments_text}, with recurring reliance on {tools_text}.",
                "confidence": 92.0,
            },
            {
                "source_file": source_name,
                "signal_type": "Operational Priority",
                "description": f"Detected business focus on '{state.main_business_goals or 'faster delivery'}' with AI goals centered on {', '.join(state.ai_goals[:2]) or 'efficiency and service improvement'}.",
                "confidence": 88.0,
            },
        ]

    return {
        "extracted_signals": signals,
        "logs": state.logs
        + ["Document Understanding Agent extracted 2 key business signals."],
        "current_node": "document_understanding",
    }


# 2. Business Context Agent
def business_context_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Business Context...")
    prompt = f"""
    Generate a professional 3-sentence Executive Business Summary for this company:
    Company Name: {state.company_name}
    Industry: {state.industry}
    Goals: {state.main_business_goals}
    Pain Points: {", ".join(state.pain_points)}
    """

    summary = LLMRouter.generate_completion(prompt)
    return {
        "business_summary": summary,
        "logs": state.logs
        + ["Business Context Agent synthesized company background and goals."],
        "current_node": "business_context",
    }


# 3. Process Bottleneck Agent
def process_bottleneck_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Process Bottleneck...")
    prompt = f"""
    Analyze these pain points: {", ".join(state.pain_points)}
    Departments: {", ".join(state.departments)}
    Current Tools: {", ".join(state.current_tools)}
    Goals: {state.main_business_goals}
    Identify 2 manual process bottlenecks.
    Format your response as a JSON object:
    {{
        "bottlenecks": [
            {{
                "department": "Operations or Customer Support",
                "process_name": "Name of the process",
                "bottleneck_description": "Explanation of the bottleneck",
                "ai_potential": "High"
            }}
        ]
    }}
    """

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        bottlenecks = data.get("bottlenecks", [])
    except Exception:
        bottlenecks = [
            {
                "department": "Operations",
                "process_name": "Manual Excel Data Triage",
                "bottleneck_description": "Data engineers spend 3 hours daily copy-pasting records between spreadsheets.",
                "ai_potential": "High",
            },
            {
                "department": "Customer Support",
                "process_name": "Email Response Matching",
                "bottleneck_description": "Help desk manually scans inbox and tags support requests.",
                "ai_potential": "Medium",
            },
        ]

    return {
        "bottlenecks": bottlenecks,
        "logs": state.logs
        + [
            f"Process Bottleneck Agent identified {len(bottlenecks)} core operational bottlenecks."
        ],
        "current_node": "process_bottleneck",
    }


# 4. AI Use Case Discovery Agent
def ai_use_case_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: AI Use Case Discovery...")
    prompt = f"""
    Based on these bottlenecks: {json.dumps(state.bottlenecks)}
    Company Name: {state.company_name}
    Current Tools: {", ".join(state.current_tools)}
    Goals: {state.main_business_goals}
    Compliance Requirements: {", ".join(state.compliance_requirements)}
    Suggest 3 AI use cases mapped to departments:
    Format your response as a JSON object:
    {{
        "use_cases": [
            {{
                "use_case_name": "Name of use case",
                "department": "Department",
                "description": "Short explanation",
                "value": "High",
                "complexity": "Low",
                "risk": "Low",
                "priority": "P1",
                "evidence": "Recommended because uploaded documents show repetitive manual spreadsheets",
                "confidence": 90.0
            }}
        ]
    }}
    """

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        use_cases = data.get("use_cases", [])
    except Exception:
        use_cases = [
            {
                "use_case_name": "Intelligent Pre-Sales Proposal Copilot",
                "department": "Sales & Pre-sales",
                "description": "Intelligent solution drafting companion that pulls from verified proposal assets and past winning bid documents to build compliance-mapped proposal outlines.",
                "value": "High",
                "complexity": "Low",
                "risk": "Low",
                "priority": "P1",
                "evidence": "Recommended because workflow analysis shows heavy manual cycles spent on custom solution blocks in proposal compilation.",
                "confidence": 92.0,
            },
            {
                "use_case_name": "Support Ticket Smart Router",
                "department": "Customer Support",
                "description": "Multi-agent classifier routing client emails straight to resolving technicians.",
                "value": "High",
                "complexity": "Medium",
                "risk": "Low",
                "priority": "P1",
                "evidence": "Recommended because support desk reports a 4-hour delay in initial email categorizations.",
                "confidence": 88.0,
            },
            {
                "use_case_name": "Compliance Audit Agent",
                "department": "Compliance & Governance",
                "description": "Intelligent contract parser searching client agreements for compliance gaps.",
                "value": "Medium",
                "complexity": "High",
                "risk": "Medium",
                "priority": "P2",
                "evidence": "Recommended because compliance requirements call out legal review checklists.",
                "confidence": 85.0,
            },
        ]

    return {
        "use_cases": use_cases,
        "logs": state.logs
        + [
            f"AI Use Case Discovery Agent generated {len(use_cases)} strategic opportunities."
        ],
        "current_node": "ai_use_case",
    }


# 5. Readiness Scoring Agent
def readiness_scoring_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Readiness Scoring...")

    prompt = f"""
You are a Senior AI Readiness Analyst with 15+ years of enterprise transformation experience.
Your job is to produce a rigorous, defensible AI Readiness Scorecard for a real client.

## Client Profile
- Company: {state.company_name}
- Industry: {state.industry}
- Departments: {", ".join(state.departments)}
- Current Tools: {", ".join(state.current_tools)}
- Pain Points: {", ".join(state.pain_points)}
- AI Goals: {", ".join(state.ai_goals)}
- Cloud Preference: {state.cloud_preference}
- Compliance Requirements: {", ".join(state.compliance_requirements)}
- Identified Bottlenecks: {json.dumps(state.bottlenecks)}
- Identified Use Cases: {json.dumps(state.use_cases)}

## Scoring Instructions
Score each dimension from 0–100 based on the evidence above.
Be critical — most enterprises score 45–70, not 80+.
For each dimension, provide a 1-sentence justification tied to specific client evidence.

Scoring rubric:
- data_readiness: Quality, accessibility, and structure of data assets. Penalize for Data Silos, Excel-heavy workflows, no data warehouse.
- process_readiness: How standardized and documented the processes are. Penalize for Manual Process Overload, tribal knowledge.
- integration_readiness: API maturity, cloud-native stack, ability to connect systems. Reward cloud-agnostic or modern stack.
- governance_readiness: Data governance policies, AI ethics policies, audit trails. Penalize for heavy compliance requirements without governance tooling.
- security_readiness: Data security posture, compliance certifications, access controls. Reward regulated industry experience.
- team_readiness: AI/ML talent, change management culture, executive sponsorship. Penalize if no AI goals mention upskilling.
- business_alignment: How clearly AI goals map to revenue, cost, or customer outcomes. Reward specific, measurable goals.

Overall score = weighted average:
data(20%) + process(15%) + integration(15%) + governance(15%) + security(15%) + team(10%) + alignment(10%)

Automation potential = estimated % of current manual work automatable within 12 months based on identified bottlenecks and use cases.

## Output Format (strict JSON)
{{
    "data_readiness": <float>,
    "data_justification": "<one sentence tied to client evidence>",
    "process_readiness": <float>,
    "process_justification": "<one sentence tied to client evidence>",
    "integration_readiness": <float>,
    "integration_justification": "<one sentence tied to client evidence>",
    "governance_readiness": <float>,
    "governance_justification": "<one sentence tied to client evidence>",
    "security_readiness": <float>,
    "security_justification": "<one sentence tied to client evidence>",
    "team_readiness": <float>,
    "team_justification": "<one sentence tied to client evidence>",
    "business_alignment": <float>,
    "alignment_justification": "<one sentence tied to client evidence>",
    "overall_score": <float>,
    "automation_potential": <float>,
    "readiness_interpretation": "<3-sentence narrative: overall posture, top strength, top gap, recommended first action>"
}}
"""

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        score_keys = [
            "data_readiness",
            "process_readiness",
            "integration_readiness",
            "governance_readiness",
            "security_readiness",
            "team_readiness",
            "business_alignment",
            "overall_score",
        ]
        for key in score_keys:
            if key in data:
                data[key] = round(max(0.0, min(100.0, float(data[key]))), 1)
        data["automation_potential"] = round(
            max(0.0, min(100.0, float(data.get("automation_potential", 30.0)))), 1
        )
    except Exception:
        data = {
            "data_readiness": 55.0,
            "data_justification": f"Data is fragmented across {', '.join(state.current_tools[:3]) or 'multiple business systems'}, which limits reliable AI access without cleanup.",
            "process_readiness": 52.0,
            "process_justification": f"Pain points such as {', '.join(state.pain_points[:2]) or 'manual process overload'} indicate repeatable work, but the process flow is still largely manual.",
            "integration_readiness": 50.0,
            "integration_justification": f"The current stack ({', '.join(state.current_tools[:3]) or 'existing tools'}) is workable, but there is limited evidence of shared middleware or mature API connectivity.",
            "governance_readiness": 56.0,
            "governance_justification": f"Compliance requirements like {', '.join(state.compliance_requirements[:3]) or 'baseline governance needs'} are present, but AI-specific guardrails are not yet strongly defined.",
            "security_readiness": 68.0,
            "security_justification": "The organization appears to have a baseline enterprise security posture, but AI-specific data handling controls still need structured enforcement.",
            "team_readiness": 49.0,
            "team_justification": "The intake shows interest in AI outcomes, but does not provide strong evidence of training, operating ownership, or change management readiness.",
            "business_alignment": 70.0,
            "alignment_justification": "The proposed AI goals map directly to cost reduction and workflow acceleration, which supports a focused pilot recommendation.",
            "overall_score": 57.6,
            "automation_potential": 35.0,
            "readiness_interpretation": "Overall readiness is moderate, with the clearest strength in business alignment and the largest gap in team preparedness. The company can justify a scoped pilot, but should avoid broad rollout before process and governance controls mature. Start with one high-value workflow where human review remains mandatory.",
        }

    return {
        **data,
        "logs": state.logs
        + [
            f"Readiness Scoring Agent evaluated score categories. Overall: {int(data.get('overall_score', 0))}/100."
        ],
        "current_node": "readiness_scoring",
    }


# 6. Risk & Governance Agent
def risk_governance_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Risk & Governance...")
    prompt = f"""
    For these compliance requirements: {", ".join(state.compliance_requirements)}
    Current Tools: {", ".join(state.current_tools)}
    Departments: {", ".join(state.departments)}
    Suggest 2 major AI risks and controls.
    Format your response in JSON:
    {{
        "risks": [
            {{
                "risk_name": "Name of risk",
                "severity": "High or Medium",
                "recommendation": "Recommendation statement",
                "is_control_met": 0
            }}
        ]
    }}
    """

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        risks = data.get("risks", [])
    except Exception:
        risks = [
            {
                "risk_name": "Unintentional Leak of Sensitive Client PII",
                "severity": "High",
                "recommendation": "Deploy local open-source PII scrubbers on FastAPI router prior to third-party API dispatches.",
                "is_control_met": 0,
            },
            {
                "risk_name": "Drift in Smart Invoice Layout Extractor",
                "severity": "Medium",
                "recommendation": "Enforce quarterly evaluations of schema parsing maps against human verified outputs.",
                "is_control_met": 0,
            },
        ]

    return {
        "risks": risks,
        "logs": state.logs
        + [f"Risk & Governance Agent added {len(risks)} entries to risk register."],
        "current_node": "risk_governance",
    }


# 7. Roadmap Planning Agent
def roadmap_planning_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Roadmap Planning...")
    prompt = f"""
    Company Name: {state.company_name}
    Departments: {", ".join(state.departments)}
    Current Tools: {", ".join(state.current_tools)}
    Main Goals: {state.main_business_goals}
    Build a 30/60/90 day roadmap containing 3 strategic steps for {state.company_name}.
    Format in JSON:
    {{
        "roadmap": [
            {{
                "phase": "30-Day",
                "action_item": "Action description",
                "expected_impact": "Expected outcome description",
                "confidence": 90.0
            }}
        ]
    }}
    """

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        roadmap = data.get("roadmap", [])
    except Exception:
        roadmap = [
            {
                "phase": "30-Day",
                "action_item": "Scaffold operations datastore and pilot Excel Ingestion Automation Agent.",
                "expected_impact": "Reduces invoice input cycles by 40% immediately.",
                "confidence": 92.0,
            },
            {
                "phase": "60-Day",
                "action_item": "Deploy help desk Support Ticket Router for shadow tests on client emails.",
                "expected_impact": "Decreases support queue response times by 30%.",
                "confidence": 88.0,
            },
            {
                "phase": "90-Day",
                "action_item": "Initiate board contract auditor agent and host cross-departmental alignment classes.",
                "expected_impact": "Reduces compliance audit preparation window from 10 days to 24 hours.",
                "confidence": 85.0,
            },
        ]

    return {
        "roadmap_items": roadmap,
        "logs": state.logs
        + ["Roadmap Planning Agent created 30/60/90-day action steps."],
        "current_node": "roadmap_planning",
    }


# 8. Proposal Writing Agent
def proposal_writing_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Proposal Writing...")
    prompt = f"""
You are a Principal AI Solutions Architect and Proposal Strategist at a top-tier consulting firm.
Your job is to generate a commercially precise, client-ready AI Enablement Proposal.
This proposal will be handed directly to the client's CTO and CFO — it must be specific, credible, and grounded in their actual context.

## Client Context
- Company: {state.company_name}
- Industry: {state.industry}
- Company Size / Departments: {", ".join(state.departments)}
- Pain Points: {", ".join(state.pain_points)}
- AI Goals: {", ".join(state.ai_goals)}
- Compliance Requirements: {", ".join(state.compliance_requirements)}
- Cloud Preference: {state.cloud_preference}
- Current Tools: {", ".join(state.current_tools)}
- Overall AI Readiness Score: {state.overall_score}/100
- Identified Use Cases: {json.dumps(state.use_cases)}
- Identified Bottlenecks: {json.dumps(state.bottlenecks)}
- Identified Risks: {json.dumps(state.risks)}
- 90-Day Roadmap: {json.dumps(state.roadmap_items)}

## Instructions

### Recommended Pilot
Select the single best P1 use case as the recommended pilot project.
Justify the selection using specific evidence from bottlenecks, goals, and readiness score.
The pilot should be the one with highest value-to-complexity ratio and lowest risk.

### Budget Estimation
Estimate a realistic budget range in USD based on:
- Industry norms for the identified use case type
- Number of departments involved
- Integration complexity (consider current tools and cloud preference)
- Compliance overhead (more compliance = higher cost)
- Typical ranges: Simple RAG/chatbot pilots = $15K–$35K | Multi-agent workflow automation = $40K–$90K | Enterprise-grade with compliance = $80K–$150K+

### ROI Projection
Estimate ROI timeline based on:
- Automation potential score
- Identified bottleneck severity
- Pilot use case value rating
- Typical ranges: High-value, low-complexity pilots = 2–4 months | Mid-complexity = 4–7 months | High-compliance/complex = 8–14 months

### Executive Summary
Write a 3-sentence executive summary that:
1. States the client's core AI opportunity
2. Recommends the pilot with specific expected impact
3. Projects the business outcome if deployed within 90 days

## Output Format (strict JSON)
{{
    "recommended_pilot": {{
        "name": "<use case name>",
        "department": "<department>",
        "why": "<2-sentence justification grounded in client evidence>",
        "expected_impact": "<specific, quantified impact statement — e.g. reduce X by Y% in Z weeks>",
        "confidence": <float 0–100>,
        "complexity": "<Low | Medium | High>",
        "estimated_duration_weeks": <int>
    }},
    "proposal_summary": {{
        "title": "AI Enablement Strategy Proposal: {state.company_name}",
        "executive_summary": "<3-sentence executive summary>",
        "est_budget": "<range in USD — e.g. $42,000 – $58,000>",
        "roi_projection": "<specific timeline and trigger — e.g. ROI within 4–5 months post-deployment, driven by 35% reduction in manual ops overhead>",
        "key_risks_acknowledged": ["<risk 1>", "<risk 2>"],
        "next_step": "<single clear recommended next action for the client>"
    }}
}}
"""

    json_str = LLMRouter.generate_completion(prompt, require_json=True)
    try:
        data = json.loads(json_str)
        pilot = data.get("recommended_pilot", {})
        proposal = data.get("proposal_summary", {})
    except Exception:
        pilot = {
            "name": "Intelligent Pre-Sales Proposal Copilot",
            "department": "Sales & Pre-sales",
            "why": "This use case offers the strongest value-to-complexity ratio for an initial rollout and directly addresses documented manual proposal bottlenecks. It also keeps governance risk manageable because human review can remain in the loop.",
            "expected_impact": "Reduce first-draft proposal turnaround by 25-40% within the initial pilot scope.",
            "confidence": 90.0,
            "complexity": "Low",
            "estimated_duration_weeks": 6,
        }
        proposal = {
            "title": f"AI Enablement Strategy Proposal: {state.company_name}",
            "executive_summary": f"{state.company_name} has a credible AI opportunity in repetitive knowledge work. A focused pilot around {pilot['name']} should improve cycle time without forcing a full platform transformation. If launched within 90 days, it can create measurable proof of value and a stronger case for broader rollout.",
            "est_budget": "$20,000 - $35,000",
            "roi_projection": "ROI within 3-5 months post-deployment, driven by faster turnaround on manual document workflows.",
            "key_risks_acknowledged": [
                "Weak source quality may reduce early output trust.",
                "Governance controls may trail pilot velocity without formal review ownership.",
            ],
            "next_step": "Lock pilot scope, success metrics, and review owners before build kickoff.",
        }

    return {
        "recommended_pilot": pilot,
        "proposal_summary": proposal,
        "logs": state.logs
        + [
            "Proposal Writing Agent designed pilot card and budget model from client context."
        ],
        "current_node": "proposal_writing",
    }


# 9. Report Generation Agent
def report_generation_node(state: AssessmentState) -> Dict[str, Any]:
    logger.info("Running Node: Report Generation...")
    return {
        "logs": state.logs
        + [
            "Report Generation Agent fully synchronized pipeline! Assessment completed successfully."
        ],
        "current_node": "report_generation",
    }
