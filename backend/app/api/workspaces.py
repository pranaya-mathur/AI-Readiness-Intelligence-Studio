"""Phase 3 workspace, membership, branding, portfolio, and proposal APIs."""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_password_hash
from app.core.database import get_db
from app.core.rbac import (
    PERM_ASSESSMENT_APPROVE,
    PERM_ASSESSMENT_READ,
    PERM_ASSESSMENT_WRITE,
    PERM_BRANDING_MANAGE,
    PERM_CLIENT_MANAGE,
    PERM_MEMBER_MANAGE,
    PERM_ORG_MANAGE,
    PERM_PROPOSAL_WRITE,
    PERM_VIEW_CONSULTANT_NOTES,
    ROLE_CLIENT_VIEWER,
    WORKFLOW_STATUSES,
    WORKSPACE_TYPES,
    has_permission,
)
from app.models import (
    Assessment,
    Client,
    Organization,
    OrganizationMembership,
    User,
)
from app.services.access_control import (
    assert_valid_role,
    branding_dict,
    client_is_authorized_for_membership,
    get_accessible_assessment,
    get_client_for_user,
    get_membership,
    list_user_organizations,
    require_org_permission,
    validate_authorized_clients,
)
from app.services.approval_gates import assert_workflow_transition
from app.services.investment_persistence import serialize_investment_package
from app.services.proposal_sow import build_proposal_and_sow

router = APIRouter()


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    workspace_type: str | None = None


class BrandingUpdate(BaseModel):
    brand_display_name: str | None = None
    brand_logo_url: str | None = None
    brand_primary_color: str | None = None
    brand_secondary_color: str | None = None
    brand_contact_email: str | None = None
    brand_contact_phone: str | None = None
    brand_footer_text: str | None = None


class MemberCreate(BaseModel):
    email: str
    role: str
    full_name: str | None = None
    temporary_password: str | None = Field(
        default=None,
        description="Optional password if creating a new user account",
    )
    authorized_client_ids: list[int] | None = None


class MemberRoleUpdate(BaseModel):
    role: str
    authorized_client_ids: list[int] | None = None


class EngagementUpdate(BaseModel):
    engagement_status: str | None = None
    assigned_consultant_user_id: int | None = None
    consultant_notes: str | None = None
    business_unit: str | None = None
    fee_estimate: dict[str, Any] | None = None


class WorkflowUpdate(BaseModel):
    workflow_status: str
    reason: str | None = None


class FeeEstimateUpdate(BaseModel):
    fee_estimate: dict[str, Any] | None = None
    reason: str | None = None


def _org_payload(db: Session, org: Organization, user: User) -> dict[str, Any]:
    membership = get_membership(db, user, org.id)
    return {
        "id": org.id,
        "name": org.name,
        "workspace_type": org.workspace_type,
        "branding": branding_dict(org),
        "role": membership.role if membership else None,
        "owner_user_id": org.owner_user_id,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


@router.get("/")
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orgs = list_user_organizations(db, current_user)
    db.commit()
    return [_org_payload(db, org, current_user) for org in orgs]


@router.get("/{organization_id}")
def get_workspace(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _membership = require_org_permission(
        db, current_user, organization_id, PERM_ASSESSMENT_READ
    )
    return _org_payload(db, org, current_user)


@router.put("/{organization_id}")
def update_workspace(
    organization_id: int,
    payload: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _m = require_org_permission(db, current_user, organization_id, PERM_ORG_MANAGE)
    if payload.name:
        org.name = payload.name
    if payload.workspace_type:
        if payload.workspace_type not in WORKSPACE_TYPES:
            raise HTTPException(status_code=400, detail="Invalid workspace_type")
        org.workspace_type = payload.workspace_type
    db.commit()
    db.refresh(org)
    return _org_payload(db, org, current_user)


@router.put("/{organization_id}/branding")
def update_branding(
    organization_id: int,
    payload: BrandingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, _m = require_org_permission(
        db, current_user, organization_id, PERM_BRANDING_MANAGE
    )
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(org, key, value)
    db.commit()
    db.refresh(org)
    return branding_dict(org)


@router.get("/{organization_id}/members")
def list_members(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Full membership directory (emails + client assignments) is internal-admin only.
    # Client viewers and other external roles must not enumerate unrelated members.
    require_org_permission(db, current_user, organization_id, PERM_MEMBER_MANAGE)
    rows = (
        db.query(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .filter(OrganizationMembership.organization_id == organization_id)
        .all()
    )
    return [
        {
            "membership_id": m.id,
            "user_id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": m.role,
            "authorized_client_ids": m.authorized_client_ids,
        }
        for m, u in rows
    ]


@router.post("/{organization_id}/members")
def add_member(
    organization_id: int,
    payload: MemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_org_permission(db, current_user, organization_id, PERM_MEMBER_MANAGE)
    role = assert_valid_role(payload.role)
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        if not payload.temporary_password or len(payload.temporary_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New users require temporary_password (min 8 characters)",
            )
        user = User(
            email=payload.email,
            hashed_password=get_password_hash(payload.temporary_password),
            full_name=payload.full_name,
        )
        db.add(user)
        db.flush()
    existing = get_membership(db, user, organization_id)
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")
    authorized = validate_authorized_clients(
        db, organization_id, payload.authorized_client_ids, role
    )
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=role,
        authorized_client_ids=authorized,
    )
    db.add(membership)
    db.commit()
    return {
        "user_id": user.id,
        "email": user.email,
        "role": role,
        "authorized_client_ids": authorized,
    }


@router.put("/{organization_id}/members/{user_id}")
def update_member_role(
    organization_id: int,
    user_id: int,
    payload: MemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_org_permission(db, current_user, organization_id, PERM_MEMBER_MANAGE)
    role = assert_valid_role(payload.role)
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.role = role
    if payload.authorized_client_ids is not None or role == ROLE_CLIENT_VIEWER:
        membership.authorized_client_ids = validate_authorized_clients(
            db,
            organization_id,
            payload.authorized_client_ids
            if payload.authorized_client_ids is not None
            else membership.authorized_client_ids,
            role,
        )
    elif role != ROLE_CLIENT_VIEWER:
        membership.authorized_client_ids = None
    db.commit()
    return {
        "user_id": user_id,
        "role": role,
        "authorized_client_ids": membership.authorized_client_ids,
    }


@router.get("/{organization_id}/portfolio")
def enterprise_portfolio(
    organization_id: int,
    business_unit: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, membership = require_org_permission(
        db, current_user, organization_id, PERM_ASSESSMENT_READ
    )
    query = db.query(Assessment).filter(Assessment.organization_id == organization_id)
    if business_unit:
        query = query.filter(Assessment.business_unit == business_unit)
    assessments = query.order_by(Assessment.updated_at.desc()).all()
    items = []
    for ass in assessments:
        if membership.role == ROLE_CLIENT_VIEWER:
            if not client_is_authorized_for_membership(membership, ass.client_id):
                continue
            from app.services.access_control import assessment_is_client_viewer_visible

            if not assessment_is_client_viewer_visible(ass):
                continue
        items.append(
            {
                "assessment_id": ass.id,
                "company_name": ass.company_name,
                "business_unit": ass.business_unit,
                "client_id": ass.client_id,
                "status": ass.status,
                "workflow_status": ass.workflow_status,
                "approval_status": ass.approval_status,
                "investment_decision_status": ass.investment_decision_status,
                "overall_score": ass.overall_score,
                "recommended_first_pilot": ass.recommended_first_pilot,
                "updated_at": ass.updated_at.isoformat() if ass.updated_at else None,
            }
        )
    units = sorted({i["business_unit"] for i in items if i.get("business_unit")})
    return {
        "organization_id": organization_id,
        "workspace_type": org.workspace_type,
        "business_units": units,
        "assessments": items,
        "note": (
            "Portfolio lists assessments independently. Do not sum ROI across "
            "unrelated or overlapping opportunities."
        ),
    }


@router.get("/{organization_id}/engagements")
def agency_engagements(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org, membership = require_org_permission(
        db, current_user, organization_id, PERM_ASSESSMENT_READ
    )
    clients = (
        db.query(Client)
        .filter(Client.organization_id == organization_id)
        .order_by(Client.updated_at.desc())
        .all()
    )
    can_notes = has_permission(membership.role, PERM_VIEW_CONSULTANT_NOTES)
    rows = []
    for client in clients:
        if (
            membership.role == ROLE_CLIENT_VIEWER
            and not client_is_authorized_for_membership(membership, client.id)
        ):
            continue
        assessment_count = (
            db.query(Assessment).filter(Assessment.client_id == client.id).count()
        )
        rows.append(
            {
                "client_id": client.id,
                "name": client.name,
                "industry": client.industry,
                "business_unit": client.business_unit,
                "engagement_status": client.engagement_status,
                "assigned_consultant_user_id": client.assigned_consultant_user_id,
                "consultant_notes": client.consultant_notes if can_notes else None,
                "has_proposal": bool(client.proposal_package),
                "has_sow": bool(client.sow_package),
                "fee_estimate_complete": bool(
                    (client.fee_estimate or {}).get("pilot_fee") is not None
                    or (client.fee_estimate or {}).get("implementation_fee") is not None
                ),
                "assessment_count": assessment_count,
                "updated_at": client.updated_at.isoformat()
                if client.updated_at
                else None,
            }
        )
    return {
        "organization_id": organization_id,
        "workspace_type": org.workspace_type,
        "engagements": rows,
    }


@router.put("/{organization_id}/engagements/{client_id}")
def update_engagement(
    organization_id: int,
    client_id: int,
    payload: EngagementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_org_permission(db, current_user, organization_id, PERM_CLIENT_MANAGE)
    client = get_client_for_user(
        db, current_user, client_id, permission=PERM_CLIENT_MANAGE
    )
    if not client or client.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Engagement not found")
    data = payload.model_dump(exclude_unset=True)
    if "engagement_status" in data and data["engagement_status"]:
        if data["engagement_status"] not in WORKFLOW_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid engagement_status")
    for key, value in data.items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return {
        "client_id": client.id,
        "engagement_status": client.engagement_status,
        "assigned_consultant_user_id": client.assigned_consultant_user_id,
        "consultant_notes": client.consultant_notes,
        "business_unit": client.business_unit,
        "fee_estimate": client.fee_estimate,
    }


@router.put("/assessments/{assessment_id}/workflow")
def update_assessment_workflow(
    assessment_id: int,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.workflow_status not in WORKFLOW_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid workflow_status")
    # Approvals require approve permission; other transitions require write.
    permission = (
        PERM_ASSESSMENT_APPROVE
        if payload.workflow_status in {"approved", "delivered"}
        else PERM_CLIENT_MANAGE
    )
    if payload.workflow_status not in {"approved", "delivered", "proposal_prepared"}:
        permission = PERM_ASSESSMENT_WRITE
    if payload.workflow_status == "proposal_prepared":
        permission = PERM_PROPOSAL_WRITE

    ass = get_accessible_assessment(
        db, current_user, assessment_id, permission=permission
    )
    # Approval prerequisites apply before status mutation (including reopen targets).
    if not (
        ass.locked_for_delivery
        and payload.reason
        and payload.workflow_status not in {"approved", "delivered"}
    ):
        assert_workflow_transition(ass, payload.workflow_status)
    if ass.locked_for_delivery and payload.workflow_status != "delivered":
        # Allow reopen only with approve permission and explicit reason.
        if not payload.reason:
            raise HTTPException(
                status_code=409,
                detail="Approved/delivered assessment is locked. Provide reason to reopen.",
            )
        get_accessible_assessment(
            db, current_user, assessment_id, permission=PERM_ASSESSMENT_APPROVE
        )
        ass.locked_for_delivery = 0

    previous = ass.workflow_status
    ass.workflow_status = payload.workflow_status
    if payload.workflow_status == "approved":
        ass.workflow_approved_at = datetime.datetime.utcnow()
        ass.workflow_approved_by_user_id = current_user.id
        ass.locked_for_delivery = 1
        ass.proposal_locked = 1
        if ass.proposal_package and not ass.proposal_approved_at:
            ass.proposal_approved_at = datetime.datetime.utcnow()
    if payload.workflow_status == "delivered":
        ass.locked_for_delivery = 1
        ass.proposal_locked = 1
    if ass.client_id:
        client = db.query(Client).filter(Client.id == ass.client_id).first()
        if client:
            client.engagement_status = payload.workflow_status
    db.commit()
    return {
        "assessment_id": ass.id,
        "previous_workflow_status": previous,
        "workflow_status": ass.workflow_status,
        "locked_for_delivery": bool(ass.locked_for_delivery),
        "reason": payload.reason,
    }


@router.post("/assessments/{assessment_id}/proposal-sow")
def generate_proposal_sow(
    assessment_id: int,
    payload: FeeEstimateUpdate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = get_accessible_assessment(
        db, current_user, assessment_id, permission=PERM_PROPOSAL_WRITE
    )
    if not ass.organization_id:
        raise HTTPException(
            status_code=400,
            detail="Assessment must belong to an organization workspace",
        )
    org, _m = require_org_permission(
        db, current_user, ass.organization_id, PERM_PROPOSAL_WRITE
    )
    client = None
    if ass.client_id:
        client = db.query(Client).filter(Client.id == ass.client_id).first()
    if not client:
        raise HTTPException(
            status_code=400, detail="Client engagement required for proposal/SOW"
        )

    workflow = (ass.workflow_status or "").lower()
    deliverable_locked = bool(getattr(ass, "proposal_locked", 0)) or workflow in {
        "approved",
        "delivered",
    }
    reopen_reason = payload.reason if payload else None
    if deliverable_locked:
        if not reopen_reason:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approved proposal/SOW is locked for this assessment. "
                    "Provide a reason to reopen before regenerating."
                ),
            )
        get_accessible_assessment(
            db, current_user, assessment_id, permission=PERM_ASSESSMENT_APPROVE
        )
        ass.proposal_locked = 0

    # Capture issued packages before any fee/package mutation for immutable history.
    prior_proposal = getattr(ass, "proposal_package", None)
    prior_sow = getattr(ass, "sow_package", None)
    prior_fee = getattr(ass, "fee_estimate", None)
    prior_approved_at = getattr(ass, "proposal_approved_at", None)
    was_issued = bool(deliverable_locked or prior_approved_at or reopen_reason)

    fee_estimate = (
        payload.fee_estimate
        if payload and payload.fee_estimate is not None
        else prior_fee
    )
    if payload and payload.fee_estimate is not None:
        ass.fee_estimate = payload.fee_estimate

    package = serialize_investment_package(ass)
    opportunities = package.get("opportunities") or []
    selected = next((o for o in opportunities if o.get("pilot_selected")), None)
    if selected is None and ass.recommended_opportunity_id:
        selected = next(
            (o for o in opportunities if o.get("id") == ass.recommended_opportunity_id),
            None,
        )
    if selected is None and opportunities:
        selected = next(
            (o for o in opportunities if o.get("ranking") == 1), opportunities[0]
        )

    result = build_proposal_and_sow(
        organization={"name": org.name, "id": org.id},
        client={
            "name": client.name,
            "industry": client.industry,
            "business_unit": client.business_unit,
            "fee_estimate": fee_estimate,
        },
        assessment={
            "id": ass.id,
            "company_name": ass.company_name,
            "industry": ass.industry,
            "business_unit": ass.business_unit,
            "main_business_goals": ass.main_business_goals,
            "client_summary": ass.client_summary,
            "business_summary": ass.business_summary,
            "pain_points": ass.pain_points,
            "recommended_first_pilot": ass.recommended_first_pilot,
            "why_recommended_pilot": ass.why_recommended_pilot,
            "approval_status": ass.approval_status,
            "investment_decision_status": ass.investment_decision_status,
            "workflow_status": ass.workflow_status,
        },
        opportunity=selected,
        pilot=package.get("pilot_recommendation") or ass.pilot_plan,
        fee_estimate=fee_estimate,
        branding=branding_dict(org),
    )
    proposal = dict(result["proposal_package"])
    sow = dict(result["sow_package"])
    proposal["assessment_id"] = ass.id
    proposal["client_id"] = client.id
    sow["assessment_id"] = ass.id
    sow["client_id"] = client.id

    if was_issued and (prior_proposal or prior_sow):
        history = list(getattr(ass, "proposal_revision_history", None) or [])
        history.append(
            {
                "revision": len(history) + 1,
                "immutable": True,
                "archived_at": datetime.datetime.utcnow().isoformat() + "Z",
                "reason": reopen_reason or "Regenerated after prior issuance",
                "workflow_status_at_archive": ass.workflow_status,
                "proposal_approved_at": (
                    prior_approved_at.isoformat() + "Z" if prior_approved_at else None
                ),
                "proposal_package": prior_proposal,
                "sow_package": prior_sow,
                "fee_estimate": prior_fee,
            }
        )
        ass.proposal_revision_history = history

    ass.proposal_package = proposal
    ass.sow_package = sow
    if ass.workflow_status not in {"delivered", "approved"}:
        # Proposal prepared is gated by shared approval rules.
        assert_workflow_transition(ass, "proposal_prepared")
        ass.workflow_status = "proposal_prepared"
        client.engagement_status = "proposal_prepared"
    # Lock only after client-facing approval/delivery workflow — drafts remain editable.
    if (ass.workflow_status or "").lower() in {"approved", "delivered"}:
        ass.proposal_locked = 1
        ass.proposal_approved_at = datetime.datetime.utcnow()
    else:
        ass.proposal_locked = 0
    db.commit()
    return {
        "proposal_package": ass.proposal_package,
        "sow_package": ass.sow_package,
        "fee_estimate": ass.fee_estimate,
        "assessment_id": ass.id,
        "client_id": client.id,
        "proposal_locked": bool(ass.proposal_locked),
        "revision_count": len(getattr(ass, "proposal_revision_history", None) or []),
        "complete": result.get("complete"),
        "missing_information": result.get("missing_information"),
    }


@router.get("/assessments/{assessment_id}/proposal-sow")
def get_proposal_sow(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ass = get_accessible_assessment(
        db, current_user, assessment_id, permission=PERM_ASSESSMENT_READ
    )
    if not ass.client_id:
        raise HTTPException(
            status_code=404, detail="No client engagement on assessment"
        )
    client = db.query(Client).filter(Client.id == ass.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    proposal = getattr(ass, "proposal_package", None)
    sow = getattr(ass, "sow_package", None)
    fee = getattr(ass, "fee_estimate", None)

    # Backward-compatible legacy fallback: use client packages only when they
    # are explicitly bound to this assessment_id (or only one assessment exists).
    if not proposal and client.proposal_package:
        legacy = client.proposal_package
        bound_id = legacy.get("assessment_id") if isinstance(legacy, dict) else None
        sibling_count = (
            db.query(Assessment).filter(Assessment.client_id == client.id).count()
        )
        if bound_id == ass.id or (bound_id is None and sibling_count == 1):
            proposal = legacy
            sow = client.sow_package
            fee = fee or client.fee_estimate
            # Soft migrate onto assessment without touching other assessments.
            if not getattr(ass, "proposal_package", None):
                if isinstance(proposal, dict):
                    proposal = dict(proposal)
                    proposal["assessment_id"] = ass.id
                if isinstance(sow, dict):
                    sow = dict(sow)
                    sow["assessment_id"] = ass.id
                ass.proposal_package = proposal
                ass.sow_package = sow
                if fee is not None:
                    ass.fee_estimate = fee
                db.commit()

    return {
        "proposal_package": proposal,
        "sow_package": sow,
        "fee_estimate": fee,
        "assessment_id": ass.id,
        "client_id": client.id,
        "proposal_locked": bool(getattr(ass, "proposal_locked", 0)),
        "revision_history": getattr(ass, "proposal_revision_history", None) or [],
        "complete": bool(proposal and sow),
    }
