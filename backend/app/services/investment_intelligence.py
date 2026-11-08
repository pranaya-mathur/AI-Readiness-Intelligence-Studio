"""Orchestrates Phase 2 decision intelligence over discovered opportunities."""

from __future__ import annotations

from typing import Any

from app.services.feasibility import TechnicalFeasibilityEngine
from app.services.financial_model import FinancialModelEngine
from app.services.pilot_roadmap import PilotRoadmapEngine
from app.services.prioritization import (
    PRIORITIZATION_RUBRIC_VERSION,
    PrioritizationEngine,
)

INVESTMENT_PACKAGE_VERSION = "v1.0.0"

DECISION_STATUSES = {
    "invest",
    "validate_first",
    "defer",
    "not_recommended",
    "pending_review",
}


def assessment_context_from_orm(ass: Any) -> dict[str, Any]:
    return {
        "data_readiness": getattr(ass, "data_readiness", None),
        "process_readiness": getattr(ass, "process_readiness", None),
        "integration_readiness": getattr(ass, "integration_readiness", None),
        "governance_readiness": getattr(ass, "governance_readiness", None),
        "security_readiness": getattr(ass, "security_readiness", None),
        "team_readiness": getattr(ass, "team_readiness", None),
        "business_alignment": getattr(ass, "business_alignment", None),
        "current_tools": getattr(ass, "current_tools", None) or [],
        "compliance_requirements": getattr(ass, "compliance_requirements", None) or [],
        "industry": getattr(ass, "industry", None),
        "company_size": getattr(ass, "company_size", None),
        "insufficient_evidence": getattr(ass, "insufficient_evidence", 0),
    }


def use_case_to_opportunity_dict(
    uc: Any, financial_inputs: dict[str, Any] | None = None
) -> dict[str, Any]:
    if isinstance(uc, dict):
        base = dict(uc)
    else:
        base = {
            "id": getattr(uc, "id", None),
            "use_case_id": getattr(uc, "id", None),
            "use_case_name": getattr(uc, "use_case_name", None),
            "name": getattr(uc, "use_case_name", None),
            "description": getattr(uc, "description", None),
            "department": getattr(uc, "department", None),
            "value": getattr(uc, "value", None),
            "complexity": getattr(uc, "complexity", None),
            "risk": getattr(uc, "risk", None),
            "priority": getattr(uc, "priority", None),
            "evidence": getattr(uc, "evidence", None),
            "evidence_refs": getattr(uc, "evidence_refs", None) or [],
            "confidence": getattr(uc, "confidence", None),
        }
    if financial_inputs:
        base["financial_inputs"] = financial_inputs
    return base


class InvestmentIntelligenceEngine:
    @classmethod
    def build_package(
        cls,
        opportunities: list[dict[str, Any]],
        assessment_context: dict[str, Any] | None = None,
        *,
        criterion_weights: dict[str, float] | None = None,
        preferred_pilot_id: int | None = None,
        pilot_override_rationale: str | None = None,
        allow_illustrative_finance: bool = False,
        decision_status: str | None = None,
        decision_explanation: str | None = None,
    ) -> dict[str, Any]:
        ctx = assessment_context or {}
        priority_results = PrioritizationEngine.rank_opportunities(
            opportunities, ctx, weights=criterion_weights
        )

        evaluated: list[dict[str, Any]] = []
        for opp, priority in zip(opportunities, priority_results):
            feasibility = TechnicalFeasibilityEngine.assess(opp, ctx)
            # Fold feasibility score into technical criterion only when not overridden.
            finance_inputs = dict(opp.get("financial_inputs") or {})
            finance = FinancialModelEngine.evaluate(
                finance_inputs,
                allow_illustrative=allow_illustrative_finance
                or bool(finance_inputs.get("illustrative")),
            )

            row = {
                **opp,
                "rubric_version": priority.rubric_version,
                "criterion_scores": {
                    k: v.to_dict() for k, v in priority.criterion_scores.items()
                },
                "criterion_weights": priority.criterion_weights,
                "weighted_priority_score": priority.weighted_priority_score,
                "ranking": priority.ranking,
                "ranking_explanation": priority.ranking_explanation,
                "evidence_refs": priority.evidence_refs,
                "missing_information": sorted(
                    set(priority.missing_information + feasibility.missing_information)
                ),
                "confidence_class": priority.confidence_class,
                "recommendation_status": priority.recommendation_status,
                "hard_blockers": [b.to_dict() for b in priority.hard_blockers],
                "is_blocked": priority.is_blocked,
                "feasibility": feasibility.to_dict(),
                "financial_evaluation": finance.to_dict(),
                "original_priority_score": priority.weighted_priority_score,
            }
            evaluated.append(row)

        pilot = PilotRoadmapEngine.select_and_plan(
            evaluated,
            ctx,
            preferred_opportunity_id=preferred_pilot_id,
            override_rationale=pilot_override_rationale,
        )

        decision = cls._derive_decision(
            evaluated, pilot, decision_status, decision_explanation
        )

        portfolio = sorted(
            evaluated,
            key=lambda r: (
                r.get("ranking") is None,
                r.get("ranking") or 999,
                -(r.get("weighted_priority_score") or 0),
            ),
        )

        return {
            "package_version": INVESTMENT_PACKAGE_VERSION,
            "prioritization_rubric_version": PRIORITIZATION_RUBRIC_VERSION,
            "opportunities": portfolio,
            "pilot_recommendation": pilot.to_dict() if pilot else None,
            "decision_summary": decision,
            "assessment_context_snapshot": {
                k: ctx.get(k)
                for k in (
                    "data_readiness",
                    "process_readiness",
                    "integration_readiness",
                    "governance_readiness",
                    "security_readiness",
                    "team_readiness",
                    "business_alignment",
                )
            },
        }

    @classmethod
    def recalculate_opportunity_finance(
        cls,
        opportunity: dict[str, Any],
        financial_inputs: dict[str, Any],
        *,
        allow_illustrative: bool = False,
    ) -> dict[str, Any]:
        finance = FinancialModelEngine.evaluate(
            financial_inputs,
            allow_illustrative=allow_illustrative
            or bool(financial_inputs.get("illustrative")),
        )
        updated = dict(opportunity)
        updated["financial_inputs"] = financial_inputs
        updated["financial_evaluation"] = finance.to_dict()
        return updated

    @classmethod
    def _derive_decision(
        cls,
        evaluated: list[dict[str, Any]],
        pilot: Any,
        status_override: str | None,
        explanation_override: str | None,
    ) -> dict[str, Any]:
        if status_override and status_override in DECISION_STATUSES:
            return {
                "status": status_override,
                "explanation": explanation_override
                or "Human reviewer recorded an investment decision.",
                "missing_evidence": sorted(
                    {m for o in evaluated for m in (o.get("missing_information") or [])}
                ),
                "source": "human_review",
            }

        if not evaluated:
            return {
                "status": "not_recommended",
                "explanation": "No evaluated opportunities available.",
                "missing_evidence": ["No opportunities discovered"],
                "source": "system",
            }

        blocked_all = all(o.get("is_blocked") for o in evaluated)
        if blocked_all:
            return {
                "status": "not_recommended",
                "explanation": "All opportunities are blocked by hard feasibility conditions.",
                "missing_evidence": [],
                "source": "system",
            }

        top = next((o for o in evaluated if o.get("ranking") == 1), None)
        missing = sorted(
            {m for o in evaluated for m in (o.get("missing_information") or [])}
        )
        if top and top.get("recommendation_status") == "prioritize":
            finance_ok = (top.get("financial_evaluation") or {}).get(
                "evaluation_complete"
            )
            if not finance_ok:
                return {
                    "status": "validate_first",
                    "explanation": (
                        f"Top opportunity '{top.get('use_case_name') or top.get('name')}' "
                        "ranks highly but financial baselines are incomplete."
                    ),
                    "missing_evidence": missing,
                    "source": "system",
                }
            return {
                "status": "invest",
                "explanation": (
                    f"System recommendation: invest in pilot for "
                    f"'{pilot.opportunity_name if pilot else top.get('use_case_name')}' "
                    "based on deterministic prioritization and complete financial inputs."
                ),
                "missing_evidence": missing,
                "source": "system",
            }

        if top and top.get("recommendation_status") == "validate_first":
            return {
                "status": "validate_first",
                "explanation": "Top opportunity requires further validation before investment.",
                "missing_evidence": missing,
                "source": "system",
            }

        return {
            "status": "defer",
            "explanation": "No opportunity currently meets invest/validate thresholds.",
            "missing_evidence": missing,
            "source": "system",
        }
