import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models import Assessment, Client, Organization, User
from app.schemas.assessment import ClientCreate, ClientResponse

logger = logging.getLogger("ClientAPI")
router = APIRouter()


def get_or_create_default_organization(db: Session, current_user: User) -> Organization:
    organization = (
        db.query(Organization)
        .filter(Organization.owner_user_id == current_user.id)
        .first()
    )
    if organization:
        return organization

    organization = Organization(
        owner_user_id=current_user.id,
        name=f"{current_user.email.split('@')[0].replace('.', ' ').title()} Advisory",
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def get_client_for_user(
    db: Session, current_user: User, client_id: int
) -> Client | None:
    return (
        db.query(Client)
        .join(Organization, Client.organization_id == Organization.id)
        .filter(Client.id == client_id, Organization.owner_user_id == current_user.id)
        .first()
    )


@router.get("/", response_model=List[ClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization = get_or_create_default_organization(db, current_user)
    return (
        db.query(Client)
        .filter(Client.organization_id == organization.id)
        .order_by(Client.updated_at.desc(), Client.name.asc())
        .all()
    )


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    client = get_client_for_user(db, current_user, client_id)
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
    return None
