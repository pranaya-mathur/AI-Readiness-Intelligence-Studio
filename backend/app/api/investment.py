"""Phase 2 Investment Intelligence API."""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.rbac import (
    PERM_ASSESSMENT_READ,
    PERM_INVESTMENT_APPROVE,
    PERM_INVESTMENT_WRITE,
)
from app.models import Assessment, OpportunityEvaluation, User
from app.services.access_control import get_accessible_assessment
from app.services.financial_model import FINANCIAL_MODEL_VERSION, FinancialModelEngine
from app.services.investment_intelligence import (
    InvestmentIntelligenceEngine,
    assessment_context_from_orm,
)
from app.services.investment_persistence import (
    build_and_persist_investment_package,
    record_review_event,
    serialize_investment_package,
)
from app.services.approval_gates import assert_investment_decision_allowed
from app.services.prioritization import PrioritizationEngine

router = APIRouter()


class FinancialInputsUpdate(BaseModel):
    financial_inputs: dict[str, Any]
    reason: str | None = None
    allow_illustrative: bool = False


class CriterionOverrideUpdate(BaseModel):
    criterion_scores: dict[str, float]
    reason: str = Field(..., min_length=3)


class PilotOverrideUpdate(BaseModel):
    opportunity_evaluation_id: int
    reason: str = Field(..., min_length=3)


class InvestmentDecisionUpdate(BaseModel):
    status: str
    explanation: str = Field(..., min_length=3)


class RecalculateRequest(BaseModel):
    criterion_weights: dict[str, float] | None = None
    allow_illustrative_finance: bool = False


def _get_owned_assessment(
    db: Session,
    assessment_id: int,
    user: User,
    *,
    permission: str = PERM_ASSESSMENT_READ,
) -> Assessment:
    ass = get_accessible_assessment(
        db, user, assessment_id, permission=permission
    )
    if getattr(ass, "locked_for_delivery", 0) and permission != PERM_ASSESSMENT_READ:
        raise HTTPException(
            status_code=409,
            detail=(
                "Assessment is locked for delivery. Reopen via workspace workflow "
                "before changing investment inputs."
            ),
        )
    return ass


@router.get("/{assessment_id}/investment-intelligence")
def get_investment_intelligence(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = _get_owned_assessment(
        db, assessment_id, current_user, permission=PERM_ASSESSMENT_READ
    )
    if not ass.opportunity_evaluations and ass.use_cases:
        build_and_persist_investment_package(db, ass)
        db.commit()
        db.refresh(ass)
    return serialize_investment_package(ass)


@router.post("/{assessment_id}/investment-intelligence/recalculate")
def recalculate_investment_intelligence(
    assessment_id: int,
    payload: RecalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = _get_owned_assessment(
        db, assessment_id, current_user, permission=PERM_INVESTMENT_WRITE
    )
    build_and_persist_investment_package(
        db,
        ass,
        criterion_weights=payload.criterion_weights,
        allow_illustrative_finance=payload.allow_illustrative_finance,
        preferred_pilot_id=ass.recommended_opportunity_id,
    )
    record_review_event(
        db,
        ass,
        reviewer_user_id=current_user.id,
        event_type="recalculate",
        reason="Deterministic investment package recalculated",
        new_value={"weights": payload.criterion_weights},
    )
    db.commit()
    db.refresh(ass)
    return serialize_investment_package(ass)


@router.put(
    "/{assessment_id}/investment-intelligence/opportunities/{opportunity_id}/financials"
)
def update_opportunity_financials(
    assessment_id: int,
    opportunity_id: int,
    payload: FinancialInputsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = _get_owned_assessment(
        db, assessment_id, current_user, permission=PERM_INVESTMENT_WRITE
    )
    row = (
        db.query(OpportunityEvaluation)
        .filter(
            OpportunityEvaluation.id == opportunity_id,
            OpportunityEvaluation.assessment_id == ass.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity evaluation not found")

    previous = row.financial_inputs
    if row.original_financial_inputs is None:
        row.original_financial_inputs = previous
    finance = FinancialModelEngine.evaluate(
        payload.financial_inputs,
        allow_illustrative=payload.allow_illustrative
        or bool(payload.financial_inputs.get("illustrative")),
    )
    row.financial_inputs = payload.financial_inputs
    row.financial_evaluation = finance.to_dict()
    row.financial_model_version = FINANCIAL_MODEL_VERSION

    record_review_event(
        db,
        ass,
        reviewer_user_id=current_user.id,
        event_type="financial_inputs_update",
        field_name="financial_inputs",
        previous_value=previous,
        new_value=payload.financial_inputs,
        reason=payload.reason,
        opportunity_evaluation_id=row.id,
    )

    # Rebuild package rankings/pilot with preserved finance inputs.
    build_and_persist_investment_package(
        db,
        ass,
        financial_inputs_by_use_case={
            int(r.use_case_id): dict(r.financial_inputs or {})
            for r in ass.opportunity_evaluations
            if r.use_case_id and r.financial_inputs
        }
        | ({int(row.use_case_id): payload.financial_inputs} if row.use_case_id else {}),
        preferred_pilot_id=ass.recommended_opportunity_id,
        allow_illustrative_finance=payload.allow_illustrative,
    )
    db.commit()
    db.refresh(ass)
    return serialize_investment_package(ass)


@router.put(
    "/{assessment_id}/investment-intelligence/opportunities/{opportunity_id}/criteria"
)
def override_opportunity_criteria(
    assessment_id: int,
    opportunity_id: int,
    payload: CriterionOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = _get_owned_assessment(
        db, assessment_id, current_user, permission=PERM_INVESTMENT_WRITE
    )
    row = (
        db.query(OpportunityEvaluation)
        .filter(
            OpportunityEvaluation.id == opportunity_id,
            OpportunityEvaluation.assessment_id == ass.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity evaluation not found")

    previous = row.criterion_scores
    if row.original_criterion_scores is None:
        row.original_criterion_scores = previous

    opp = {
        "use_case_name": row.name,
        "description": row.description,
        "evidence_refs": row.evidence_refs or [],
        "hard_blockers": row.hard_blockers or [],
        "criterion_scores": payload.criterion_scores,
        "financial_inputs": row.financial_inputs or {},
    }
    result = PrioritizationEngine.score_opportunity(
        opp,
        assessment_context_from_orm(ass),
        criterion_overrides=payload.criterion_scores,
    )
    row.reviewed_criterion_scores = {
        k: v.to_dict() for k, v in result.criterion_scores.items()
    }
    row.criterion_scores = row.reviewed_criterion_scores
    row.weighted_priority_score = result.weighted_priority_score
    row.ranking_explanation = result.ranking_explanation
    row.confidence_class = result.confidence_class
    row.recommendation_status = result.recommendation_status
    row.hard_blockers = [b.to_dict() for b in result.hard_blockers]
    row.is_blocked = 1 if result.is_blocked else 0
    row.missing_information = result.missing_information

    record_review_event(
        db,
        ass,
        reviewer_user_id=current_user.id,
        event_type="criterion_override",
        field_name="criterion_scores",
        previous_value=previous,
        new_value=payload.criterion_scores,
        reason=payload.reason,
        opportunity_evaluation_id=row.id,
    )

    # Re-rank across all opportunities with reviewed scores preserved via criterion_scores JSON.
    opportunities = []
    for ev in ass.opportunity_evaluations:
        numeric_overrides = {}
        scores = ev.criterion_scores or {}
        for key, meta in scores.items():
            if isinstance(meta, dict) and meta.get("score") is not None:
                numeric_overrides[key] = float(meta["score"])
        opportunities.append(
            {
                "id": ev.id,
                "use_case_id": ev.use_case_id,
                "use_case_name": ev.name,
                "description": ev.description,
                "department": ev.department,
                "evidence_refs": ev.evidence_refs or [],
                "hard_blockers": ev.hard_blockers or [],
                "criterion_scores": numeric_overrides,
                "financial_inputs": ev.financial_inputs or {},
            }
        )
    package = InvestmentIntelligenceEngine.build_package(
        opportunities,
        assessment_context_from_orm(ass),
        preferred_pilot_id=ass.recommended_opportunity_id,
        decision_status=ass.investment_decision_status
        if ass.investment_decision_reviewer_id
        else None,
        decision_explanation=ass.investment_decision_explanation
        if ass.investment_decision_reviewer_id
        else None,
    )
    # Update ranking fields from package without wiping reviewer finance inputs.
    by_id = {o.get("id"): o for o in package.get("opportunities") or []}
    for ev in ass.opportunity_evaluations:
        refreshed = by_id.get(ev.id) or {}
        ev.ranking = refreshed.get("ranking")
        ev.weighted_priority_score = refreshed.get("weighted_priority_score")
        ev.ranking_explanation = refreshed.get("ranking_explanation")
        ev.recommendation_status = refreshed.get("recommendation_status")
        ev.confidence_class = refreshed.get("confidence_class")
        if refreshed.get("financial_evaluation"):
            ev.financial_evaluation = refreshed["financial_evaluation"]
        ev.pilot_selected = 0
    pilot = package.get("pilot_recommendation") or {}
    for ev in ass.opportunity_evaluations:
        if (
            pilot.get("opportunity_id") == ev.id
            or (pilot.get("opportunity_name") or "").strip().lower()
            == (ev.name or "").strip().lower()
        ):
            ev.pilot_selected = 1
            ass.recommended_opportunity_id = ev.id
            ass.recommended_first_pilot = ev.name
            ass.why_recommended_pilot = pilot.get("selection_rationale")
            ass.expected_pilot_impact = pilot.get("time_to_value_label")
    ass.investment_package = package
    ass.pilot_plan = pilot or None
    if not ass.investment_decision_reviewer_id:
        decision = package.get("decision_summary") or {}
        ass.investment_decision_status = decision.get("status")
        ass.investment_decision_explanation = decision.get("explanation")

    db.commit()
    db.refresh(ass)
    return serialize_investment_package(ass)


@router.put("/{assessment_id}/investment-intelligence/pilot")
def override_pilot_recommendation(
    assessment_id: int,
    payload: PilotOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = _get_owned_assessment(
        db, assessment_id, current_user, permission=PERM_INVESTMENT_WRITE
    )
    row = (
        db.query(OpportunityEvaluation)
        .filter(
            OpportunityEvaluation.id == payload.opportunity_evaluation_id,
            OpportunityEvaluation.assessment_id == ass.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Opportunity evaluation not found")
    if row.is_blocked:
        raise HTTPException(
            status_code=409,
            detail="Cannot select a blocked opportunity as the pilot recommendation.",
        )

    previous = ass.recommended_opportunity_id
    build_and_persist_investment_package(
        db,
        ass,
        preferred_pilot_id=row.id,
        pilot_override_rationale=payload.reason,
    )
    # Preferred id is evaluation id; persistence matches by name — force selection.
    for ev in ass.opportunity_evaluations:
        ev.pilot_selected = 1 if ev.id == row.id else 0
    ass.recommended_opportunity_id = row.id
    ass.recommended_first_pilot = row.name
    ass.why_recommended_pilot = payload.reason
    if ass.pilot_plan:
        plan = dict(ass.pilot_plan)
        plan["opportunity_id"] = row.id
        plan["opportunity_name"] = row.name
        plan["selection_rationale"] = payload.reason
        ass.pilot_plan = plan
    if ass.investment_package:
        pkg = dict(ass.investment_package)
        pkg["pilot_recommendation"] = ass.pilot_plan
        ass.investment_package = pkg

    record_review_event(
        db,
        ass,
        reviewer_user_id=current_user.id,
        event_type="pilot_override",
        field_name="recommended_opportunity_id",
        previous_value=previous,
        new_value=row.id,
        reason=payload.reason,
        opportunity_evaluation_id=row.id,
    )
    db.commit()
    db.refresh(ass)
    return serialize_investment_package(ass)


@router.put("/{assessment_id}/investment-intelligence/decision")
def record_investment_decision(
    assessment_id: int,
    payload: InvestmentDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = _get_owned_assessment(
        db, assessment_id, current_user, permission=PERM_INVESTMENT_APPROVE
    )
    assert_investment_decision_allowed(payload.status)

    previous = {
        "status": ass.investment_decision_status,
        "explanation": ass.investment_decision_explanation,
    }
    ass.investment_decision_status = payload.status
    ass.investment_decision_explanation = payload.explanation
    ass.investment_decision_reviewer_id = current_user.id
    ass.investment_decision_at = datetime.datetime.utcnow()

    record_review_event(
        db,
        ass,
        reviewer_user_id=current_user.id,
        event_type="investment_decision",
        field_name="investment_decision_status",
        previous_value=previous,
        new_value={"status": payload.status, "explanation": payload.explanation},
        reason=payload.explanation,
    )
    if ass.investment_package:
        pkg = dict(ass.investment_package)
        pkg["decision_summary"] = {
            "status": payload.status,
            "explanation": payload.explanation,
            "source": "human_review",
            "missing_evidence": (pkg.get("decision_summary") or {}).get(
                "missing_evidence"
            )
            or [],
        }
        ass.investment_package = pkg

    db.commit()
    db.refresh(ass)
    return serialize_investment_package(ass)
