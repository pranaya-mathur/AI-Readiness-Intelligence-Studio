"""Persist / reload Phase 2 investment intelligence packages."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Assessment, InvestmentReviewEvent, OpportunityEvaluation
from app.services.financial_model import FINANCIAL_MODEL_VERSION
from app.services.investment_intelligence import (
    InvestmentIntelligenceEngine,
    assessment_context_from_orm,
    use_case_to_opportunity_dict,
)
from app.services.prioritization import PRIORITIZATION_RUBRIC_VERSION


def build_and_persist_investment_package(
    db: Session,
    ass: Assessment,
    *,
    financial_inputs_by_use_case: dict[int, dict[str, Any]] | None = None,
    preferred_pilot_id: int | None = None,
    pilot_override_rationale: str | None = None,
    allow_illustrative_finance: bool = False,
    criterion_weights: dict[str, float] | None = None,
    preserve_financial_inputs: bool = True,
) -> dict[str, Any]:
    """Rebuild opportunity evaluations from current use cases and persist."""
    existing_finance: dict[int, dict[str, Any]] = {}
    if preserve_financial_inputs:
        for row in ass.opportunity_evaluations or []:
            if row.use_case_id and row.financial_inputs:
                existing_finance[int(row.use_case_id)] = dict(row.financial_inputs)

    if financial_inputs_by_use_case:
        existing_finance.update(financial_inputs_by_use_case)

    opportunities = []
    for uc in ass.use_cases or []:
        opportunities.append(
            use_case_to_opportunity_dict(uc, existing_finance.get(int(uc.id)))
        )

    package = InvestmentIntelligenceEngine.build_package(
        opportunities,
        assessment_context_from_orm(ass),
        criterion_weights=criterion_weights,
        preferred_pilot_id=preferred_pilot_id or ass.recommended_opportunity_id,
        pilot_override_rationale=pilot_override_rationale,
        allow_illustrative_finance=allow_illustrative_finance,
        decision_status=ass.investment_decision_status
        if ass.investment_decision_reviewer_id
        else None,
        decision_explanation=ass.investment_decision_explanation
        if ass.investment_decision_reviewer_id
        else None,
    )

    # Replace evaluation rows while preserving audit events.
    db.query(OpportunityEvaluation).filter(
        OpportunityEvaluation.assessment_id == ass.id
    ).delete()
    db.flush()

    pilot = package.get("pilot_recommendation") or {}
    pilot_name = (pilot.get("opportunity_name") or "").strip().lower()
    recommended_id = None

    for row in package.get("opportunities") or []:
        uc_id = row.get("use_case_id") or row.get("id")
        name = str(row.get("use_case_name") or row.get("name") or "Opportunity")
        selected = 1 if pilot_name and name.strip().lower() == pilot_name else 0
        eval_row = OpportunityEvaluation(
            assessment_id=ass.id,
            use_case_id=uc_id,
            name=name,
            description=row.get("description"),
            department=row.get("department"),
            criterion_scores=row.get("criterion_scores"),
            criterion_weights=row.get("criterion_weights"),
            original_criterion_scores=row.get("criterion_scores"),
            reviewed_criterion_scores=None,
            weighted_priority_score=row.get("weighted_priority_score"),
            original_priority_score=row.get("original_priority_score"),
            ranking=row.get("ranking"),
            ranking_explanation=row.get("ranking_explanation"),
            evidence_refs=row.get("evidence_refs"),
            missing_information=row.get("missing_information"),
            confidence_class=row.get("confidence_class"),
            recommendation_status=row.get("recommendation_status"),
            hard_blockers=row.get("hard_blockers"),
            is_blocked=1 if row.get("is_blocked") else 0,
            feasibility=row.get("feasibility"),
            financial_inputs=row.get("financial_inputs")
            or existing_finance.get(int(uc_id or 0)),
            original_financial_inputs=row.get("financial_inputs")
            or existing_finance.get(int(uc_id or 0)),
            financial_evaluation=row.get("financial_evaluation"),
            pilot_selected=selected,
            prioritization_rubric_version=PRIORITIZATION_RUBRIC_VERSION,
            financial_model_version=FINANCIAL_MODEL_VERSION,
        )
        db.add(eval_row)
        db.flush()
        row["id"] = eval_row.id
        row["use_case_id"] = uc_id
        if selected:
            recommended_id = eval_row.id
            if pilot:
                pilot["opportunity_id"] = eval_row.id

    decision = package.get("decision_summary") or {}
    ass.prioritization_rubric_version = PRIORITIZATION_RUBRIC_VERSION
    ass.financial_model_version = FINANCIAL_MODEL_VERSION
    ass.investment_package = package
    ass.pilot_plan = pilot or None
    ass.recommended_opportunity_id = recommended_id
    if not ass.investment_decision_reviewer_id:
        ass.investment_decision_status = decision.get("status")
        ass.investment_decision_explanation = decision.get("explanation")

    # Align Phase 1 pilot fields with selected opportunity when available.
    if pilot and pilot.get("opportunity_name"):
        ass.recommended_first_pilot = pilot["opportunity_name"]
        ass.why_recommended_pilot = pilot.get("selection_rationale")
        ass.expected_pilot_impact = pilot.get("time_to_value_label")

    db.flush()
    return package


def serialize_investment_package(ass: Assessment) -> dict[str, Any]:
    if ass.investment_package:
        package = dict(ass.investment_package)
    else:
        package = {
            "package_version": None,
            "opportunities": [],
            "pilot_recommendation": ass.pilot_plan,
            "decision_summary": {
                "status": ass.investment_decision_status,
                "explanation": ass.investment_decision_explanation,
            },
        }

    # Prefer live ORM rows when present.
    if ass.opportunity_evaluations:
        package["opportunities"] = [
            {
                "id": row.id,
                "use_case_id": row.use_case_id,
                "name": row.name,
                "use_case_name": row.name,
                "description": row.description,
                "department": row.department,
                "criterion_scores": row.criterion_scores,
                "criterion_weights": row.criterion_weights,
                "original_criterion_scores": row.original_criterion_scores,
                "reviewed_criterion_scores": row.reviewed_criterion_scores,
                "weighted_priority_score": row.weighted_priority_score,
                "original_priority_score": row.original_priority_score,
                "ranking": row.ranking,
                "ranking_explanation": row.ranking_explanation,
                "evidence_refs": row.evidence_refs,
                "missing_information": row.missing_information,
                "confidence_class": row.confidence_class,
                "recommendation_status": row.recommendation_status,
                "hard_blockers": row.hard_blockers,
                "is_blocked": bool(row.is_blocked),
                "feasibility": row.feasibility,
                "financial_inputs": row.financial_inputs,
                "original_financial_inputs": row.original_financial_inputs,
                "financial_evaluation": row.financial_evaluation,
                "pilot_selected": bool(row.pilot_selected),
                "prioritization_rubric_version": row.prioritization_rubric_version,
                "financial_model_version": row.financial_model_version,
            }
            for row in sorted(
                ass.opportunity_evaluations,
                key=lambda r: (
                    r.ranking is None,
                    r.ranking or 999,
                    -(r.weighted_priority_score or 0),
                ),
            )
        ]
    package["decision_summary"] = {
        "status": ass.investment_decision_status,
        "explanation": ass.investment_decision_explanation,
        "reviewer_user_id": ass.investment_decision_reviewer_id,
        "decided_at": ass.investment_decision_at.isoformat()
        if ass.investment_decision_at
        else None,
        "missing_evidence": (package.get("decision_summary") or {}).get(
            "missing_evidence"
        )
        or [],
    }
    package["pilot_recommendation"] = ass.pilot_plan
    package["prioritization_rubric_version"] = ass.prioritization_rubric_version
    package["financial_model_version"] = ass.financial_model_version
    package["review_events"] = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "field_name": e.field_name,
            "previous_value": e.previous_value,
            "new_value": e.new_value,
            "reason": e.reason,
            "reviewer_user_id": e.reviewer_user_id,
            "opportunity_evaluation_id": e.opportunity_evaluation_id,
            "prioritization_rubric_version": e.prioritization_rubric_version,
            "financial_model_version": e.financial_model_version,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in (ass.investment_review_events or [])
    ]
    return package


def record_review_event(
    db: Session,
    ass: Assessment,
    *,
    reviewer_user_id: int | None,
    event_type: str,
    field_name: str | None = None,
    previous_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
    opportunity_evaluation_id: int | None = None,
) -> InvestmentReviewEvent:
    event = InvestmentReviewEvent(
        assessment_id=ass.id,
        opportunity_evaluation_id=opportunity_evaluation_id,
        reviewer_user_id=reviewer_user_id,
        event_type=event_type,
        field_name=field_name,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        prioritization_rubric_version=ass.prioritization_rubric_version
        or PRIORITIZATION_RUBRIC_VERSION,
        financial_model_version=ass.financial_model_version or FINANCIAL_MODEL_VERSION,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(event)
    db.flush()
    return event
