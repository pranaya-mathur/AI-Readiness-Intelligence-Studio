"""Organization/client access helpers with RBAC (Phase 3)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session, Query

from app.core.rbac import (
    ROLE_CLIENT_VIEWER,
    ROLE_OWNER_ADMIN,
    WORKSPACE_CONSULTING_AGENCY,
    WORKSPACE_ENTERPRISE,
    has_permission,
    normalize_role,
)
from app.models import (
    Assessment,
    Client,
    Organization,
    OrganizationMembership,
    User,
)
from app.services.approval_gates import CLIENT_FACING_WORKFLOWS


def ensure_owner_membership(
    db: Session, organization: Organization
) -> OrganizationMembership:
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.user_id == organization.owner_user_id,
        )
        .first()
    )
    if membership:
        return membership
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=organization.owner_user_id,
        role=ROLE_OWNER_ADMIN,
        authorized_client_ids=None,
    )
    db.add(membership)
    db.flush()
    return membership


def get_or_create_default_organization(
    db: Session,
    current_user: User,
    *,
    workspace_type: str | None = None,
) -> Organization:
    organization = (
        db.query(Organization)
        .filter(Organization.owner_user_id == current_user.id)
        .first()
    )
    if organization:
        ensure_owner_membership(db, organization)
        if not organization.workspace_type:
            organization.workspace_type = WORKSPACE_CONSULTING_AGENCY
        if not organization.brand_display_name:
            organization.brand_display_name = organization.name
        db.flush()
        return organization

    wt = workspace_type or WORKSPACE_CONSULTING_AGENCY
    organization = Organization(
        owner_user_id=current_user.id,
        name=f"{current_user.email.split('@')[0].replace('.', ' ').title()} Advisory",
        workspace_type=wt,
        brand_display_name=f"{current_user.email.split('@')[0].replace('.', ' ').title()} Advisory",
    )
    db.add(organization)
    db.flush()
    ensure_owner_membership(db, organization)
    db.flush()
    return organization


def get_membership(
    db: Session, user: User, organization_id: int
) -> OrganizationMembership | None:
    return (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
        .first()
    )


def list_user_organizations(db: Session, user: User) -> list[Organization]:
    get_or_create_default_organization(db, user)
    org_ids = [
        m.organization_id
        for m in db.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .all()
    ]
    owned = db.query(Organization).filter(Organization.owner_user_id == user.id).all()
    for org in owned:
        if org.id not in org_ids:
            ensure_owner_membership(db, org)
            org_ids.append(org.id)
    if not org_ids:
        return []
    return (
        db.query(Organization)
        .filter(Organization.id.in_(org_ids))
        .order_by(Organization.name.asc())
        .all()
    )


def require_org_permission(
    db: Session,
    user: User,
    organization_id: int,
    permission: str,
) -> tuple[Organization, OrganizationMembership]:
    organization = (
        db.query(Organization).filter(Organization.id == organization_id).first()
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    membership = get_membership(db, user, organization_id)
    if not membership and organization.owner_user_id == user.id:
        membership = ensure_owner_membership(db, organization)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if not has_permission(membership.role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{membership.role}' lacks permission '{permission}'",
        )
    return organization, membership


def authorized_client_id_set(membership: OrganizationMembership) -> set[int] | None:
    """Return explicit client IDs for scoped viewers; None means org-wide."""
    if membership.role != ROLE_CLIENT_VIEWER:
        return None
    raw = membership.authorized_client_ids or []
    if not isinstance(raw, list):
        return set()
    out: set[int] = set()
    for item in raw:
        try:
            out.add(int(item))
        except (TypeError, ValueError):
            continue
    return out


def client_is_authorized_for_membership(
    membership: OrganizationMembership, client_id: int | None
) -> bool:
    allowed = authorized_client_id_set(membership)
    if allowed is None:
        return True
    if client_id is None:
        return False
    return int(client_id) in allowed


def assessment_is_client_viewer_visible(ass: Assessment) -> bool:
    workflow = (ass.workflow_status or "").lower()
    approval = (ass.approval_status or "").lower()
    locked = bool(getattr(ass, "locked_for_delivery", 0))
    return approval == "approved" and (locked or workflow in CLIENT_FACING_WORKFLOWS)


def get_client_for_user(
    db: Session,
    current_user: User,
    client_id: int,
    *,
    permission: str | None = None,
) -> Client | None:
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return None
    membership = get_membership(db, current_user, client.organization_id)
    if not membership:
        org = (
            db.query(Organization)
            .filter(Organization.id == client.organization_id)
            .first()
        )
        if org and org.owner_user_id == current_user.id:
            membership = ensure_owner_membership(db, org)
        else:
            return None
    if permission and not has_permission(membership.role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{membership.role}' lacks permission '{permission}'",
        )
    if not client_is_authorized_for_membership(membership, client.id):
        return None
    return client


def assessments_visible_query(db: Session, user: User) -> Query:
    """Assessments visible via legacy ownership or org membership.

    Client viewers are restricted to explicitly authorized client engagements
    and only approved/client-facing assessments.
    """
    memberships = (
        db.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .all()
    )
    owned_orgs = (
        db.query(Organization).filter(Organization.owner_user_id == user.id).all()
    )
    owned_ids = {o.id for o in owned_orgs}
    for org in owned_orgs:
        if not any(m.organization_id == org.id for m in memberships):
            memberships.append(ensure_owner_membership(db, org))

    # Build OR clauses per membership.
    from sqlalchemy import and_, or_

    clauses = [Assessment.user_id == user.id]
    for membership in memberships:
        org_id = membership.organization_id
        if membership.role == ROLE_CLIENT_VIEWER:
            allowed = authorized_client_id_set(membership) or set()
            if not allowed:
                continue
            clauses.append(
                and_(
                    Assessment.organization_id == org_id,
                    Assessment.client_id.in_(list(allowed)),
                    Assessment.approval_status == "approved",
                    or_(
                        Assessment.locked_for_delivery == 1,
                        Assessment.workflow_status.in_(list(CLIENT_FACING_WORKFLOWS)),
                    ),
                )
            )
        else:
            # Internal enterprise/agency members: org-wide visibility.
            clauses.append(Assessment.organization_id == org_id)
            if org_id in owned_ids:
                continue

    return db.query(Assessment).filter(or_(*clauses))


def get_accessible_assessment(
    db: Session,
    user: User,
    assessment_id: int,
    *,
    permission: str,
) -> Assessment:
    ass = (
        assessments_visible_query(db, user)
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if ass.organization_id is None:
        if ass.user_id != user.id:
            raise HTTPException(status_code=403, detail="Assessment access denied")
        if not has_permission(ROLE_OWNER_ADMIN, permission):
            raise HTTPException(status_code=403, detail="Permission denied")
        return ass

    _org, membership = require_org_permission(db, user, ass.organization_id, permission)
    if membership.role == ROLE_CLIENT_VIEWER:
        if not client_is_authorized_for_membership(membership, ass.client_id):
            raise HTTPException(
                status_code=403, detail="Client engagement not authorized"
            )
        if not assessment_is_client_viewer_visible(ass):
            raise HTTPException(
                status_code=403,
                detail="Client viewers can only access approved deliverables",
            )
    return ass


def strip_internal_fields_for_role(payload: dict, role: str | None) -> dict:
    """Remove consultant/internal-only fields for client viewers."""
    if role != ROLE_CLIENT_VIEWER:
        return payload
    cleaned = dict(payload)
    cleaned["reviewer_notes"] = None
    cleaned.pop("consultant_notes", None)
    # Keep client-facing summaries only.
    return cleaned


def branding_dict(organization: Organization) -> dict:
    return {
        "organization_id": organization.id,
        "workspace_type": organization.workspace_type or WORKSPACE_CONSULTING_AGENCY,
        "display_name": organization.brand_display_name or organization.name,
        "logo_url": organization.brand_logo_url,
        "primary_color": organization.brand_primary_color or "#3b82f6",
        "secondary_color": organization.brand_secondary_color or "#6366f1",
        "contact_email": organization.brand_contact_email,
        "contact_phone": organization.brand_contact_phone,
        "footer_text": organization.brand_footer_text
        or f"Prepared by {organization.brand_display_name or organization.name}",
        "is_enterprise": (organization.workspace_type or "") == WORKSPACE_ENTERPRISE,
    }


def assert_valid_role(role: str) -> str:
    return normalize_role(role)


def validate_authorized_clients(
    db: Session, organization_id: int, client_ids: list[int] | None, role: str
) -> list[int] | None:
    if role != ROLE_CLIENT_VIEWER:
        return None
    if not client_ids:
        raise HTTPException(
            status_code=400,
            detail="client_viewer memberships require authorized_client_ids",
        )
    unique = sorted({int(c) for c in client_ids})
    found = (
        db.query(Client.id)
        .filter(Client.organization_id == organization_id, Client.id.in_(unique))
        .all()
    )
    found_ids = {row[0] for row in found}
    missing = [c for c in unique if c not in found_ids]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"authorized_client_ids not in organization: {missing}",
        )
    return unique
