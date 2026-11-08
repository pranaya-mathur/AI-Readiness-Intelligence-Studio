"""Organization/client access helpers with RBAC (Phase 3)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.rbac import (
    ROLE_OWNER_ADMIN,
    WORKSPACE_CONSULTING_AGENCY,
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


def ensure_owner_membership(db: Session, organization: Organization) -> OrganizationMembership:
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
    owned = (
        db.query(Organization).filter(Organization.owner_user_id == user.id).all()
    )
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


def get_client_for_user(
    db: Session, current_user: User, client_id: int, *, permission: str | None = None
) -> Client | None:
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return None
    membership = get_membership(db, current_user, client.organization_id)
    if not membership:
        # Legacy owner path
        org = db.query(Organization).filter(Organization.id == client.organization_id).first()
        if org and org.owner_user_id == current_user.id:
            membership = ensure_owner_membership(db, org)
        else:
            return None
    if permission and not has_permission(membership.role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{membership.role}' lacks permission '{permission}'",
        )
    return client


def assessments_visible_query(db: Session, user: User):
    """Assessments visible via legacy ownership or org membership."""
    org_ids = [
        m.organization_id
        for m in db.query(OrganizationMembership)
        .filter(OrganizationMembership.user_id == user.id)
        .all()
    ]
    owned_org_ids = [
        o.id
        for o in db.query(Organization).filter(Organization.owner_user_id == user.id).all()
    ]
    all_org_ids = list(set(org_ids + owned_org_ids))
    query = db.query(Assessment)
    if all_org_ids:
        return query.filter(
            (Assessment.user_id == user.id)
            | (Assessment.organization_id.in_(all_org_ids))
        )
    return query.filter(Assessment.user_id == user.id)


def get_accessible_assessment(
    db: Session,
    user: User,
    assessment_id: int,
    *,
    permission: str,
) -> Assessment:
    ass = assessments_visible_query(db, user).filter(Assessment.id == assessment_id).first()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Legacy personal assessment without org: creator only, treat as owner_admin.
    if ass.organization_id is None:
        if ass.user_id != user.id:
            raise HTTPException(status_code=403, detail="Assessment access denied")
        if not has_permission(ROLE_OWNER_ADMIN, permission):
            raise HTTPException(status_code=403, detail="Permission denied")
        return ass

    _org, membership = require_org_permission(
        db, user, ass.organization_id, permission
    )
    # Client viewers may only see approved/delivered client-facing packages.
    if membership.role == "client_viewer":
        workflow = (ass.workflow_status or "").lower()
        approval = (ass.approval_status or "").lower()
        locked = bool(getattr(ass, "locked_for_delivery", 0))
        client_visible = locked or workflow in {
            "approved",
            "proposal_prepared",
            "delivered",
        }
        if approval != "approved" or not client_visible:
            raise HTTPException(
                status_code=403,
                detail="Client viewers can only access approved deliverables",
            )
    return ass


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
    }


def assert_valid_role(role: str) -> str:
    return normalize_role(role)
