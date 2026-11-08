"""Phase 3 handoff isolation, approval gates, and proposal binding tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.rbac import has_permission
from app.main import app
from app.models import Assessment


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _register_and_login(
    client: TestClient, email: str, password: str = "Phase3Demo!23"
) -> str:
    reg = client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert reg.status_code in {200, 201}, reg.text
    login = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_completed_assessment(db_session, assessment_id: int, **extra):
    row = db_session.query(Assessment).filter(Assessment.id == assessment_id).first()
    assert row is not None
    row.status = "completed"
    row.analysis_mode = "real"
    row.model_run_status = "success"
    row.approval_status = extra.get("approval_status", "approved")
    row.client_summary = "[DEMO] Seeded summary"
    row.recommended_first_pilot = "Pilot A"
    for key, value in extra.items():
        setattr(row, key, value)
    db_session.commit()
    return row


def test_reviewer_cannot_edit_but_can_approve(client, db_session):
    assert not has_permission("reviewer_approver", "assessment.write")
    assert has_permission("reviewer_approver", "assessment.approve")
    assert has_permission("reviewer_approver", "investment.approve")
    assert not has_permission("reviewer_approver", "investment.write")

    owner = _register_and_login(client, "agency.handoff@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]
    client.put(
        f"/api/v1/workspaces/{ws['id']}",
        headers=headers,
        json={"workspace_type": "consulting_agency", "name": "Handoff Agency [DEMO]"},
    )
    created = client.post(
        "/api/v1/clients/",
        headers=headers,
        json={
            "name": "Client A [DEMO]",
            "industry": "Logistics",
            "organization_id": ws["id"],
        },
    )
    assert created.status_code == 201, created.text
    client_a = created.json()

    ass = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "client_id": client_a["id"],
            "company_name": client_a["name"],
            "industry": "Logistics",
            "departments": ["Ops"],
            "current_tools": ["Excel"],
            "main_business_goals": "Improve exception handling",
            "pain_points": ["Manual triage"],
            "ai_goals": ["Efficiency"],
        },
    )
    assert ass.status_code == 200, ass.text
    assessment = ass.json()
    _seed_completed_assessment(db_session, assessment["id"], approval_status="draft")

    member = client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        headers=headers,
        json={
            "email": "reviewer.handoff@demo.example",
            "role": "reviewer_approver",
            "temporary_password": "Phase3Demo!23",
        },
    )
    assert member.status_code in {200, 201}, member.text
    reviewer_token = client.post(
        "/api/v1/auth/login",
        data={
            "username": "reviewer.handoff@demo.example",
            "password": "Phase3Demo!23",
        },
    ).json()["access_token"]
    reviewer = _auth(reviewer_token)

    denied_edit = client.put(
        f"/api/v1/assessments/{assessment['id']}",
        headers=reviewer,
        json={"business_summary": "Unauthorized rewrite"},
    )
    assert denied_edit.status_code == 403

    approved = client.put(
        f"/api/v1/assessments/{assessment['id']}",
        headers=reviewer,
        json={"approval_status": "approved"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["approval_status"] == "approved"


def test_client_viewer_scoped_to_authorized_engagement_only(client, db_session):
    owner = _register_and_login(client, "agency.scope@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]

    clients = {}
    assessments = {}
    for label in ("A", "B"):
        c = client.post(
            "/api/v1/clients/",
            headers=headers,
            json={
                "name": f"Client {label} [DEMO]",
                "industry": "Services",
                "organization_id": ws["id"],
            },
        ).json()
        clients[label] = c
        a = client.post(
            "/api/v1/assessments/",
            headers=headers,
            json={
                "client_id": c["id"],
                "company_name": c["name"],
                "industry": "Services",
                "departments": ["Ops"],
                "current_tools": ["CRM"],
                "main_business_goals": f"Goal {label}",
                "pain_points": ["Manual work"],
                "ai_goals": ["Efficiency"],
            },
        ).json()
        assessments[label] = a
        _seed_completed_assessment(
            db_session,
            a["id"],
            approval_status="approved",
            workflow_status="consultant_review",
            locked_for_delivery=0,
        )

    # Proposal on A only, then lock as client-facing deliverable.
    prop_a = client.post(
        f"/api/v1/workspaces/assessments/{assessments['A']['id']}/proposal-sow",
        headers=headers,
        json={"fee_estimate": {"currency": "USD", "pilot_fee": 50000}},
    )
    assert prop_a.status_code == 200, prop_a.text
    wf_a = client.put(
        f"/api/v1/workspaces/assessments/{assessments['A']['id']}/workflow",
        headers=headers,
        json={"workflow_status": "approved", "reason": "Client A package approved"},
    )
    assert wf_a.status_code == 200, wf_a.text
    # Client B also becomes viewer-visible without sharing A's proposal.
    wf_b = client.put(
        f"/api/v1/workspaces/assessments/{assessments['B']['id']}/workflow",
        headers=headers,
        json={"workflow_status": "approved", "reason": "Client B package approved"},
    )
    assert wf_b.status_code == 200, wf_b.text

    membership = client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        headers=headers,
        json={
            "email": "viewer.a@demo.example",
            "role": "client_viewer",
            "temporary_password": "Phase3Demo!23",
            "authorized_client_ids": [clients["A"]["id"]],
        },
    )
    assert membership.status_code in {200, 201}, membership.text
    viewer_token = client.post(
        "/api/v1/auth/login",
        data={"username": "viewer.a@demo.example", "password": "Phase3Demo!23"},
    ).json()["access_token"]
    viewer = _auth(viewer_token)

    # Can see A
    ok = client.get(f"/api/v1/assessments/{assessments['A']['id']}", headers=viewer)
    assert ok.status_code == 200
    assert ok.json().get("reviewer_notes") in (None, "")

    # Cannot see B assessment / investment / proposal / export
    assert client.get(
        f"/api/v1/assessments/{assessments['B']['id']}", headers=viewer
    ).status_code in {403, 404}
    assert client.get(
        f"/api/v1/assessments/{assessments['B']['id']}/investment-intelligence",
        headers=viewer,
    ).status_code in {403, 404}
    assert client.get(
        f"/api/v1/workspaces/assessments/{assessments['B']['id']}/proposal-sow",
        headers=viewer,
    ).status_code in {403, 404}
    assert client.get(
        f"/api/v1/assessments/{assessments['B']['id']}/export/pdf",
        headers=viewer,
    ).status_code in {403, 404}

    listed = client.get("/api/v1/assessments/", headers=viewer)
    assert listed.status_code == 200
    ids = {row["id"] for row in listed.json()}
    assert assessments["A"]["id"] in ids
    assert assessments["B"]["id"] not in ids

    eng = client.get(f"/api/v1/workspaces/{ws['id']}/engagements", headers=viewer)
    assert eng.status_code == 200
    eng_ids = {e["client_id"] for e in eng.json()["engagements"]}
    assert clients["A"]["id"] in eng_ids
    assert clients["B"]["id"] not in eng_ids


def test_incomplete_cannot_be_workflow_approved(client, db_session):
    owner = _register_and_login(client, "agency.incomplete@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]
    ass = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "company_name": "Incomplete Co [DEMO]",
            "industry": "Manufacturing",
            "departments": ["Ops"],
            "current_tools": ["ERP"],
            "main_business_goals": "Reduce downtime",
            "pain_points": ["Downtime"],
            "ai_goals": ["Efficiency"],
        },
    ).json()
    row = db_session.query(Assessment).filter(Assessment.id == ass["id"]).first()
    row.status = "incomplete"
    row.approval_status = "draft"
    row.organization_id = ws["id"]
    db_session.commit()

    wf = client.put(
        f"/api/v1/workspaces/assessments/{ass['id']}/workflow",
        headers=headers,
        json={"workflow_status": "approved", "reason": "bypass attempt"},
    )
    assert wf.status_code == 409


def test_sibling_assessment_does_not_overwrite_existing_proposal(client, db_session):
    owner = _register_and_login(client, "agency.proposals@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]
    c = client.post(
        "/api/v1/clients/",
        headers=headers,
        json={
            "name": "Shared Client [DEMO]",
            "industry": "Retail",
            "organization_id": ws["id"],
        },
    ).json()

    first = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "client_id": c["id"],
            "company_name": c["name"],
            "industry": "Retail",
            "departments": ["Ops"],
            "current_tools": ["POS"],
            "main_business_goals": "First engagement",
            "pain_points": ["Manual work"],
            "ai_goals": ["Efficiency"],
        },
    ).json()
    _seed_completed_assessment(db_session, first["id"])

    prop1 = client.post(
        f"/api/v1/workspaces/assessments/{first['id']}/proposal-sow",
        headers=headers,
        json={
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 42000,
                "assumptions": ["First engagement fee"],
            }
        },
    )
    assert prop1.status_code == 200, prop1.text
    first_fee = prop1.json()["proposal_package"]["proposed_project_fees"]["pilot_fee"]
    assert first_fee == 42000

    second = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "client_id": c["id"],
            "company_name": c["name"],
            "industry": "Retail",
            "departments": ["Ops"],
            "current_tools": ["POS"],
            "main_business_goals": "Second engagement",
            "pain_points": ["Manual work"],
            "ai_goals": ["Efficiency"],
        },
    ).json()
    _seed_completed_assessment(db_session, second["id"])

    prop2 = client.post(
        f"/api/v1/workspaces/assessments/{second['id']}/proposal-sow",
        headers=headers,
        json={
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 99000,
                "assumptions": ["Second engagement fee"],
            }
        },
    )
    assert prop2.status_code == 200, prop2.text
    assert (
        prop2.json()["proposal_package"]["proposed_project_fees"]["pilot_fee"] == 99000
    )

    still_first = client.get(
        f"/api/v1/workspaces/assessments/{first['id']}/proposal-sow",
        headers=headers,
    )
    assert still_first.status_code == 200
    assert (
        still_first.json()["proposal_package"]["proposed_project_fees"]["pilot_fee"]
        == 42000
    )
    assert still_first.json()["assessment_id"] == first["id"]
    assert prop2.json()["assessment_id"] == second["id"]


def test_enterprise_org_wide_visibility_for_internal_roles(client, db_session):
    owner = _register_and_login(client, "enterprise.handoff@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]
    client.put(
        f"/api/v1/workspaces/{ws['id']}",
        headers=headers,
        json={"workspace_type": "enterprise", "name": "Helios [DEMO]"},
    )
    a1 = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "company_name": "Plant A [DEMO]",
            "industry": "Manufacturing",
            "departments": ["Ops"],
            "current_tools": ["SAP"],
            "main_business_goals": "Downtime",
            "pain_points": ["Downtime"],
            "ai_goals": ["Efficiency"],
        },
    ).json()
    a2 = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "company_name": "Plant B [DEMO]",
            "industry": "Manufacturing",
            "departments": ["Ops"],
            "current_tools": ["SAP"],
            "main_business_goals": "Quality",
            "pain_points": ["Scrap"],
            "ai_goals": ["Quality"],
        },
    ).json()
    listed = client.get("/api/v1/assessments/", headers=headers).json()
    ids = {row["id"] for row in listed}
    assert a1["id"] in ids and a2["id"] in ids
    portfolio = client.get(
        f"/api/v1/workspaces/{ws['id']}/portfolio", headers=headers
    ).json()
    p_ids = {row["assessment_id"] for row in portfolio["assessments"]}
    assert a1["id"] in p_ids and a2["id"] in p_ids


def test_client_viewer_cannot_list_membership_directory(client, db_session):
    owner = _register_and_login(client, "agency.members@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]
    c = client.post(
        "/api/v1/clients/",
        headers=headers,
        json={
            "name": "Scoped Client [DEMO]",
            "industry": "Services",
            "organization_id": ws["id"],
        },
    ).json()
    membership = client.post(
        f"/api/v1/workspaces/{ws['id']}/members",
        headers=headers,
        json={
            "email": "viewer.members@demo.example",
            "role": "client_viewer",
            "temporary_password": "Phase3Demo!23",
            "authorized_client_ids": [c["id"]],
        },
    )
    assert membership.status_code in {200, 201}, membership.text

    # Owner/admin can see the full directory.
    owner_list = client.get(f"/api/v1/workspaces/{ws['id']}/members", headers=headers)
    assert owner_list.status_code == 200, owner_list.text
    assert any(m["email"] == "viewer.members@demo.example" for m in owner_list.json())

    viewer_token = client.post(
        "/api/v1/auth/login",
        data={
            "username": "viewer.members@demo.example",
            "password": "Phase3Demo!23",
        },
    ).json()["access_token"]
    viewer = _auth(viewer_token)
    denied = client.get(f"/api/v1/workspaces/{ws['id']}/members", headers=viewer)
    assert denied.status_code == 403


def test_assessment_creation_scopes_to_selected_organization(client, db_session):
    owner = _register_and_login(client, "multi.workspace@demo.example")
    headers = _auth(owner)
    default_ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]

    # Create a second organization by registering another owner and inviting this user.
    other = _register_and_login(client, "second.org.owner@demo.example")
    other_headers = _auth(other)
    other_ws = client.get("/api/v1/workspaces/", headers=other_headers).json()[0]
    invite = client.post(
        f"/api/v1/workspaces/{other_ws['id']}/members",
        headers=other_headers,
        json={
            "email": "multi.workspace@demo.example",
            "role": "consultant_analyst",
        },
    )
    assert invite.status_code in {200, 201}, invite.text

    # Explicit organization_id must win over default owned org.
    ass = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "organization_id": other_ws["id"],
            "company_name": "Second Org Client [DEMO]",
            "industry": "Retail",
            "departments": ["Ops"],
            "current_tools": ["POS"],
            "main_business_goals": "Scoped creation",
            "pain_points": ["Manual work"],
            "ai_goals": ["Efficiency"],
        },
    )
    assert ass.status_code == 200, ass.text
    body = ass.json()
    assert body["organization_id"] == other_ws["id"]
    assert body["organization_id"] != default_ws["id"]

    clients_default = client.get(
        f"/api/v1/clients/?organization_id={default_ws['id']}", headers=headers
    ).json()
    clients_other = client.get(
        f"/api/v1/clients/?organization_id={other_ws['id']}", headers=headers
    ).json()
    assert all(c["name"] != "Second Org Client [DEMO]" for c in clients_default)
    assert any(c["name"] == "Second Org Client [DEMO]" for c in clients_other)


def test_approved_proposal_regeneration_preserves_revision_history(client, db_session):
    owner = _register_and_login(client, "agency.revisions@demo.example")
    headers = _auth(owner)
    ws = client.get("/api/v1/workspaces/", headers=headers).json()[0]
    c = client.post(
        "/api/v1/clients/",
        headers=headers,
        json={
            "name": "Revision Client [DEMO]",
            "industry": "Healthcare",
            "organization_id": ws["id"],
        },
    ).json()
    ass = client.post(
        "/api/v1/assessments/",
        headers=headers,
        json={
            "client_id": c["id"],
            "organization_id": ws["id"],
            "company_name": c["name"],
            "industry": "Healthcare",
            "departments": ["Ops"],
            "current_tools": ["EHR"],
            "main_business_goals": "Reduce charting time",
            "pain_points": ["Manual charting"],
            "ai_goals": ["Efficiency"],
        },
    ).json()
    _seed_completed_assessment(db_session, ass["id"])

    first = client.post(
        f"/api/v1/workspaces/assessments/{ass['id']}/proposal-sow",
        headers=headers,
        json={
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 55000,
                "assumptions": ["Initial approved fee"],
            }
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["proposal_package"]["proposed_project_fees"]["pilot_fee"] == 55000

    wf = client.put(
        f"/api/v1/workspaces/assessments/{ass['id']}/workflow",
        headers=headers,
        json={"workflow_status": "approved", "reason": "Client accepted v1"},
    )
    assert wf.status_code == 200, wf.text

    regenerated = client.post(
        f"/api/v1/workspaces/assessments/{ass['id']}/proposal-sow",
        headers=headers,
        json={
            "reason": "Revise commercial assumptions after reopen",
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 72000,
                "assumptions": ["Revised fee after reopen"],
            },
        },
    )
    assert regenerated.status_code == 200, regenerated.text
    assert regenerated.json()["proposal_package"]["proposed_project_fees"]["pilot_fee"] == 72000
    assert regenerated.json()["revision_count"] >= 1

    current = client.get(
        f"/api/v1/workspaces/assessments/{ass['id']}/proposal-sow",
        headers=headers,
    )
    assert current.status_code == 200
    history = current.json().get("revision_history") or []
    assert len(history) >= 1
    assert history[0]["immutable"] is True
    assert history[0]["proposal_package"]["proposed_project_fees"]["pilot_fee"] == 55000
    assert "Revise commercial" in (history[0].get("reason") or "")
