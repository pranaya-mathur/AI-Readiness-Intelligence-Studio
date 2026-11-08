import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.rbac import PERM_ASSESSMENT_READ, PERM_CLIENT_MANAGE, WORKFLOW_DRAFT
from app.models import Assessment, Client, User
from app.schemas.assessment import ClientCreate, ClientResponse
from app.services.access_control import (
    get_client_for_user,
    get_or_create_default_organization,
    require_org_permission,
)

logger = logging.getLogger("ClientAPI")
router = APIRouter()


class ClientCreateScoped(ClientCreate):
    organization_id: int | None = None
    business_unit: str | None = None


class ClientResponsePhase3(ClientResponse):
    organization_id: int | None = None
    business_unit: str | None = None
    engagement_status: str | None = None
    assigned_consultant_user_id: int | None = None


# Re-export helpers used by assessment.py for backward compatibility.
__all__ = [
    "router",
    "get_or_create_default_organization",
    "get_client_for_user",
]


@router.get("/", response_model=list[ClientResponsePhase3])
def list_clients(
    organization_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if organization_id is None:
        organization = get_or_create_default_organization(db, current_user)
        organization_id = organization.id
        db.commit()
    require_org_permission(db, current_user, organization_id, PERM_ASSESSMENT_READ)
    clients = (
        db.query(Client)
        .filter(Client.organization_id == organization_id)
        .order_by(Client.updated_at.desc(), Client.name.asc())
        .all()
    )
    return clients


@router.post(
    "/", response_model=ClientResponsePhase3, status_code=status.HTTP_201_CREATED
)
def create_client(
    payload: ClientCreateScoped,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.organization_id:
        organization, _m = require_org_permission(
            db, current_user, payload.organization_id, PERM_CLIENT_MANAGE
        )
    else:
        organization = get_or_create_default_organization(db, current_user)

    existing = (
        db.query(Client)
        .filter(Client.organization_id == organization.id, Client.name == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Client already exists")

    client = Client(
        organization_id=organization.id,
        name=payload.name,
        industry=payload.industry,
        company_size=payload.company_size,
        cloud_preference=payload.cloud_preference,
        compliance_requirements=payload.compliance_requirements,
        business_unit=payload.business_unit,
        engagement_status=WORKFLOW_DRAFT,
        assigned_consultant_user_id=current_user.id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = get_client_for_user(
        db, current_user, client_id, permission=PERM_CLIENT_MANAGE
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    linked_assessment_count = (
        db.query(Assessment).filter(Assessment.client_id == client.id).count()
    )
    if linked_assessment_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Delete or reassign this client's assessments before removing the client",
        )

    db.delete(client)
    db.commit()
