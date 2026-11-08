"""Pilot selection and staged implementation roadmap (extends Phase 1 roadmap)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PILOT_PLAN_VERSION = "v1.0.0"

STAGE_DEFS = (
    ("discovery_validation", "Discovery and validation"),
    ("architecture_design", "Architecture and solution design"),
    ("poc", "Proof of concept"),
    ("mvp_pilot", "MVP / pilot"),
    ("evaluation", "Evaluation"),
    ("production_decision", "Production decision"),
)


@dataclass
class PilotStage:
    stage_id: str
    name: str
    objective: str
    scope: str
    deliverables: list[str]
    required_roles: list[str]
    dependencies: list[str]
    estimated_effort_range: str
    acceptance_criteria: list[str]
    risks: list[str]
    decision_gate: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuccessMetric:
    name: str
    baseline: str
    target: str
    measurement_method: str
    evaluation_period: str
    pass_fail_criteria: str
    provenance: str = "consultant_assumption"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PilotRecommendation:
    plan_version: str
    opportunity_name: str
    opportunity_id: int | None
    selection_rationale: str
    estimated_investment_label: str
    time_to_value_label: str
    success_metrics: list[SuccessMetric]
    stages: list[PilotStage]
    governance_constraints: list[str]
    evidence_sufficiency: str
    missing_information: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": self.plan_version,
            "opportunity_name": self.opportunity_name,
            "opportunity_id": self.opportunity_id,
            "selection_rationale": self.selection_rationale,
            "estimated_investment_label": self.estimated_investment_label,
            "time_to_value_label": self.time_to_value_label,
            "success_metrics": [m.to_dict() for m in self.success_metrics],
            "stages": [s.to_dict() for s in self.stages],
            "governance_constraints": list(self.governance_constraints),
            "evidence_sufficiency": self.evidence_sufficiency,
            "missing_information": list(self.missing_information),
        }


class PilotRoadmapEngine:
    @classmethod
    def select_and_plan(
        cls,
        evaluated_opportunities: list[dict[str, Any]],
        assessment_context: dict[str, Any] | None = None,
        preferred_opportunity_id: int | None = None,
        override_rationale: str | None = None,
    ) -> PilotRecommendation | None:
        ctx = assessment_context or {}
        if not evaluated_opportunities:
            return None

        selected = None
        if preferred_opportunity_id is not None:
            selected = next(
                (
                    o
                    for o in evaluated_opportunities
                    if o.get("id") == preferred_opportunity_id
                    or o.get("use_case_id") == preferred_opportunity_id
                ),
                None,
            )

        if selected is None:
            # Prefer highest-ranked non-blocked opportunity with sufficient evidence.
            candidates = [
                o
                for o in evaluated_opportunities
                if not o.get("is_blocked")
                and o.get("recommendation_status") in {"prioritize", "validate_first"}
            ]
            if not candidates:
                candidates = [
                    o for o in evaluated_opportunities if not o.get("is_blocked")
                ]
            if not candidates:
                return None
            candidates.sort(
                key=lambda o: (
                    o.get("ranking") is None,
                    o.get("ranking") or 999,
                    -(o.get("weighted_priority_score") or 0),
                )
            )
            selected = candidates[0]

        name = str(
            selected.get("use_case_name")
            or selected.get("name")
            or "Selected opportunity"
        )
        ranking = selected.get("ranking")
        score = selected.get("weighted_priority_score")
        status = selected.get("recommendation_status")
        confidence = selected.get("confidence_class") or "low"
        finance = selected.get("financial_evaluation") or {}
        base = (finance.get("scenarios") or {}).get("base") or {}
        feasibility = selected.get("feasibility") or {}

        if override_rationale:
            rationale = override_rationale
        else:
            rationale = (
                f"Selected '{name}' as the pilot candidate because it ranks "
                f"#{ranking if ranking is not None else 'n/a'} with weighted priority "
                f"{score if score is not None else 'n/a'}/100 "
                f"(status={status}, confidence={confidence}). "
                f"Technical approach: {feasibility.get('proposed_approach', 'to be validated')}."
            )

        investment_label = "Insufficient financial inputs"
        if (
            finance.get("evaluation_complete")
            and base.get("implementation_investment") is not None
        ):
            currency = finance.get("currency") or "USD"
            investment_label = (
                f"{currency} {base['implementation_investment']:,.0f} estimated implementation "
                f"(model {finance.get('model_version')})"
            )
            if finance.get("illustrative"):
                investment_label += " — illustrative scenario"

        ttv = selected.get("criterion_scores", {}).get("time_to_value", {})
        ttv_score = ttv.get("score") if isinstance(ttv, dict) else None
        if ttv_score is None:
            time_label = "Time-to-value not evidenced — express only as a planning range after discovery"
        elif ttv_score >= 70:
            time_label = (
                "Comparatively faster time-to-value vs other scored opportunities"
            )
        elif ttv_score >= 40:
            time_label = "Moderate time-to-value — validate during discovery"
        else:
            time_label = (
                "Slower time-to-value — sequence after higher-yield pilots if possible"
            )

        metrics = cls._success_metrics(selected, base)
        stages = cls._stages(name, feasibility)
        compliance = [str(c) for c in (ctx.get("compliance_requirements") or [])]
        missing = list(selected.get("missing_information") or [])
        if not finance.get("evaluation_complete"):
            missing.append(
                "Financial baseline incomplete for investment-grade pilot costing"
            )

        return PilotRecommendation(
            plan_version=PILOT_PLAN_VERSION,
            opportunity_name=name,
            opportunity_id=selected.get("id") or selected.get("use_case_id"),
            selection_rationale=rationale,
            estimated_investment_label=investment_label,
            time_to_value_label=time_label,
            success_metrics=metrics,
            stages=stages,
            governance_constraints=compliance,
            evidence_sufficiency=str(confidence),
            missing_information=sorted(set(missing)),
        )

    @classmethod
    def _success_metrics(
        cls, selected: dict[str, Any], base_scenario: dict[str, Any]
    ) -> list[SuccessMetric]:
        metrics = [
            SuccessMetric(
                name="Cycle-time improvement",
                baseline="Measure current median cycle time before pilot start",
                target="Agree target reduction only after baseline measurement",
                measurement_method="Process timestamp sampling on pilot cohort",
                evaluation_period="Pilot evaluation window (define in discovery)",
                pass_fail_criteria="Meet agreed target without increasing critical error rate",
                provenance="consultant_assumption",
            ),
            SuccessMetric(
                name="Human review burden",
                baseline="Current review minutes per case (to be measured)",
                target="Do not invent a percentage — set after baseline capture",
                measurement_method="Time-and-motion or system audit logs",
                evaluation_period="Pilot evaluation window",
                pass_fail_criteria="Review effort remains within agreed operating envelope",
                provenance="consultant_assumption",
            ),
        ]
        if (
            base_scenario.get("complete")
            and base_scenario.get("net_annual_savings") is not None
        ):
            metrics.append(
                SuccessMetric(
                    name="Modeled net benefit trajectory",
                    baseline=str(base_scenario.get("current_baseline_annual_cost")),
                    target=(
                        "Track actual vs modeled net savings; do not treat model as guaranteed"
                    ),
                    measurement_method="Finance-validated cost tracking vs model assumptions",
                    evaluation_period=f"{base_scenario.get('horizon_months', 24)}-month model horizon",
                    pass_fail_criteria="Decision gate uses measured results, not projected ROI alone",
                    provenance="modeled_projection",
                )
            )
        return metrics

    @classmethod
    def _stages(
        cls, opportunity_name: str, feasibility: dict[str, Any]
    ) -> list[PilotStage]:
        approach = feasibility.get("proposed_approach") or "conventional_software"
        stages: list[PilotStage] = []
        templates = {
            "discovery_validation": PilotStage(
                stage_id="discovery_validation",
                name="Discovery and validation",
                objective=f"Confirm problem framing and baselines for {opportunity_name}",
                scope="Current-state process, data samples, stakeholder map, constraint review",
                deliverables=[
                    "Validated problem statement",
                    "Baseline metrics worksheet",
                    "Evidence gap list",
                ],
                required_roles=["Product owner", "Process SME", "Analyst"],
                dependencies=["Stakeholder access", "Sample data/documents"],
                estimated_effort_range="1–3 weeks (range — finalize after scope confirmation)",
                acceptance_criteria=[
                    "Baseline measurement method agreed",
                    "Hard blockers reviewed",
                ],
                risks=["Unavailable SMEs", "Incomplete data access"],
                decision_gate="Proceed only if no unresolved hard blocker remains",
            ),
            "architecture_design": PilotStage(
                stage_id="architecture_design",
                name="Architecture and solution design",
                objective=f"Design simplest viable approach ({approach})",
                scope="Target architecture, controls, integration points, HITL design",
                deliverables=[
                    "Solution design brief",
                    "Control matrix",
                    "Interface list",
                ],
                required_roles=["Solution architect", "Security/compliance advisor"],
                dependencies=["Discovery outputs"],
                estimated_effort_range="1–4 weeks (depends on integration complexity)",
                acceptance_criteria=["Design approved by owner and security reviewer"],
                risks=["Hidden integration constraints"],
                decision_gate="Approve PoC scope and non-goals",
            ),
            "poc": PilotStage(
                stage_id="poc",
                name="Proof of concept",
                objective="Test technical viability on a constrained sample",
                scope="Non-production PoC with human review; no broad rollout",
                deliverables=["PoC build", "Quality evaluation notes", "Risk findings"],
                required_roles=["Engineer", "Evaluator SME"],
                dependencies=["Design approval", "Sample corpus"],
                estimated_effort_range="2–6 weeks (sample-size dependent)",
                acceptance_criteria=["PoC meets agreed technical gates"],
                risks=["Overfitting to sample", "Unrepresentative documents"],
                decision_gate="Go / no-go for MVP pilot",
            ),
            "mvp_pilot": PilotStage(
                stage_id="mvp_pilot",
                name="MVP / pilot",
                objective="Operate limited production-like pilot with controls",
                scope="Bounded user group, monitored outputs, escalation path",
                deliverables=[
                    "Pilot deployment",
                    "Operating runbook",
                    "Weekly metrics",
                ],
                required_roles=["Engineer", "Ops owner", "Business owner"],
                dependencies=["PoC go decision", "Support coverage"],
                estimated_effort_range="4–10 weeks (adoption and integration dependent)",
                acceptance_criteria=["Success metrics instrumented and reviewed"],
                risks=["Adoption shortfall", "Support overload"],
                decision_gate="Continue, redesign, or stop",
            ),
            "evaluation": PilotStage(
                stage_id="evaluation",
                name="Evaluation",
                objective="Compare measured outcomes to success criteria",
                scope="Metric review, cost tracking, risk residual assessment",
                deliverables=["Evaluation report", "Updated financial assumptions"],
                required_roles=["Business owner", "Finance partner", "Analyst"],
                dependencies=["Pilot metrics"],
                estimated_effort_range="1–2 weeks",
                acceptance_criteria=["Pass/fail criteria explicitly judged"],
                risks=["Moving goalposts", "Incomplete measurement"],
                decision_gate="Investment committee recommendation",
            ),
            "production_decision": PilotStage(
                stage_id="production_decision",
                name="Production decision",
                objective="Decide scale-out, deferral, or retirement of the pilot",
                scope="Production readiness, funding, ownership, roadmap update",
                deliverables=["Decision record", "Scale plan or stop memo"],
                required_roles=["Executive sponsor", "Security", "Ops"],
                dependencies=["Evaluation report"],
                estimated_effort_range="Decision workshop — duration depends on governance",
                acceptance_criteria=["Signed decision with rationale and conditions"],
                risks=["Premature scale", "Unfunded operations"],
                decision_gate="Invest / Validate further / Defer / Not recommended",
            ),
        }
        for stage_id, _label in STAGE_DEFS:
            stages.append(templates[stage_id])
        return stages
