"""Technical feasibility assessment — prefers simplest viable approach.

Does not invent architecture or claim integrations without evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

FEASIBILITY_MODEL_VERSION = "v1.0.0"

APPROACH_ORDER = (
    "deterministic_rules_or_rpa",
    "conventional_software",
    "classical_ml",
    "supervised_nlp_classification",
    "retrieval_augmented_generation",
    "llm_assisted_workflow",
    "agentic_orchestration",
)


@dataclass
class FeasibilityAssessment:
    model_version: str
    proposed_approach: str
    approach_rationale: str
    prerequisites: list[str]
    dependencies: list[str]
    known_constraints: list[str]
    major_risks: list[str]
    unvalidated_assumptions: list[str]
    proof_of_concept_requirements: list[str]
    production_considerations: list[str]
    human_in_the_loop_required: bool
    evidence_refs: list[str] = field(default_factory=list)
    score: float | None = None
    missing_information: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TechnicalFeasibilityEngine:
    @classmethod
    def assess(
        cls,
        opportunity: dict[str, Any],
        assessment_context: dict[str, Any] | None = None,
    ) -> FeasibilityAssessment:
        ctx = assessment_context or {}
        name = str(
            opportunity.get("use_case_name") or opportunity.get("name") or ""
        ).lower()
        description = str(opportunity.get("description") or "").lower()
        blob = f"{name} {description}"
        tools = [str(t).lower() for t in (ctx.get("current_tools") or [])]
        refs = list(opportunity.get("evidence_refs") or [])
        missing: list[str] = []

        data_rd = float(ctx.get("data_readiness") or 0)
        process_rd = float(ctx.get("process_readiness") or 0)
        integration_rd = float(ctx.get("integration_readiness") or 0)
        security_rd = float(ctx.get("security_readiness") or 0)
        governance_rd = float(ctx.get("governance_readiness") or 0)

        has_api_signal = any(
            k in " ".join(tools) or k in blob
            for k in ("api", "salesforce", "servicenow", "jira", "sap", "webhook")
        )
        structured_workflow = any(
            k in blob
            for k in (
                "triage",
                "classify",
                "routing",
                "reconcile",
                "checklist",
                "invoice",
            )
        )
        document_heavy = any(
            k in blob
            for k in ("document", "proposal", "contract", "pdf", "rfp", "knowledge")
        )
        open_ended = any(
            k in blob
            for k in ("agent", "autonomous", "multi-step planning", "orchestrat")
        )

        # Prefer simplest viable approach — never default to agents.
        if structured_workflow and not document_heavy and not open_ended:
            approach = "deterministic_rules_or_rpa"
            rationale = (
                "Workflow appears rule-friendly (classification/routing/reconciliation). "
                "Start with deterministic automation before introducing models."
            )
        elif document_heavy and data_rd >= 40:
            approach = "retrieval_augmented_generation"
            rationale = (
                "Document-centric opportunity with partial data readiness. "
                "RAG with human review is simpler and safer than agentic orchestration."
            )
        elif structured_workflow and has_api_signal:
            approach = "supervised_nlp_classification"
            rationale = (
                "Labeled operational patterns and system integrations suggest classical "
                "or supervised NLP classification with API orchestration."
            )
        elif "predict" in blob or "forecast" in blob or "anomaly" in blob:
            approach = "classical_ml"
            rationale = "Predictive/anomaly framing fits classical ML better than generative agents."
        elif document_heavy:
            approach = "llm_assisted_workflow"
            rationale = (
                "Document drafting/assistance can use an LLM-assisted human-in-the-loop "
                "workflow without autonomous agents."
            )
        elif open_ended and integration_rd >= 60 and governance_rd >= 60:
            approach = "agentic_orchestration"
            rationale = (
                "Only after simpler options are insufficient and governance/integration "
                "readiness support controlled tool use."
            )
        else:
            approach = "conventional_software"
            rationale = (
                "Insufficient evidence for advanced AI. Prefer conventional software "
                "improvements and validate AI fit in a constrained PoC."
            )
            missing.append(
                "Technical approach not fully evidenced from current materials"
            )

        prerequisites = [
            "Documented current-state process map for the target workflow",
            "Access to representative sample data or documents",
        ]
        if approach in {
            "retrieval_augmented_generation",
            "llm_assisted_workflow",
            "agentic_orchestration",
        }:
            prerequisites.append("Approved data-handling policy for model providers")
        if not has_api_signal:
            prerequisites.append("Confirm system API or export path for integration")
            missing.append("Integration/API availability not evidenced")

        dependencies = []
        if tools:
            dependencies.append(
                f"Existing tools in landscape: {', '.join(ctx.get('current_tools') or [])}"
            )
        else:
            dependencies.append("Application landscape inventory incomplete")
            missing.append("Application landscape details missing")

        constraints = []
        compliance = ctx.get("compliance_requirements") or []
        if compliance:
            constraints.append(
                f"Compliance constraints: {', '.join(map(str, compliance))}"
            )
        if security_rd < 40:
            constraints.append(
                "Security readiness is limited — production exposure must stay constrained"
            )
        if data_rd < 40:
            constraints.append(
                "Data readiness is limited — expect data cleanup before scale"
            )

        risks = []
        if approach.startswith("llm") or "rag" in approach or "agentic" in approach:
            risks.append(
                "Model hallucination or incorrect recommendations without human review"
            )
        if integration_rd < 45:
            risks.append("Integration friction may extend time-to-value")
        if opportunity.get("risk") in {"High", "high"}:
            risks.append("Opportunity marked high residual risk in discovery")

        unvalidated = [
            "End-user adoption rate not measured",
            "Latency/throughput targets not specified",
        ]
        if not refs:
            unvalidated.append("Opportunity evidence references not validated")

        poc = [
            "Define success metrics and baseline measurement method",
            "Build a narrow PoC on a representative sample with human review",
            "Evaluate accuracy/quality, cycle time, and exception rate before MVP",
        ]
        production = [
            "Operational owner and support model must be assigned",
            "Monitoring, rollback, and audit logging for model/system outputs",
            "Human-in-the-loop gates for client-facing or regulated outputs",
        ]

        # Feasibility score: blend readiness with approach simplicity.
        simplicity_bonus = {
            "deterministic_rules_or_rpa": 15,
            "conventional_software": 12,
            "classical_ml": 8,
            "supervised_nlp_classification": 8,
            "retrieval_augmented_generation": 5,
            "llm_assisted_workflow": 4,
            "agentic_orchestration": 0,
        }.get(approach, 0)
        score = round(
            min(
                100.0,
                0.35 * data_rd
                + 0.25 * process_rd
                + 0.25 * integration_rd
                + 0.15 * ((security_rd + governance_rd) / 2.0)
                + simplicity_bonus,
            ),
            2,
        )

        return FeasibilityAssessment(
            model_version=FEASIBILITY_MODEL_VERSION,
            proposed_approach=approach,
            approach_rationale=rationale,
            prerequisites=prerequisites,
            dependencies=dependencies,
            known_constraints=constraints,
            major_risks=risks,
            unvalidated_assumptions=unvalidated,
            proof_of_concept_requirements=poc,
            production_considerations=production,
            human_in_the_loop_required=approach
            in {
                "retrieval_augmented_generation",
                "llm_assisted_workflow",
                "agentic_orchestration",
                "supervised_nlp_classification",
            },
            evidence_refs=refs,
            score=score,
            missing_information=sorted(set(missing)),
        )
