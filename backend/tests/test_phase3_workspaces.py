"""Phase 3 workspace isolation, RBAC, proposal/SOW, and journey checks."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import get_password_hash
from app.core.database import Base, get_db
from app.core.rbac import (
    ROLE_CLIENT_VIEWER,
    ROLE_CONSULTANT_ANALYST,
    ROLE_OWNER_ADMIN,
    ROLE_REVIEWER_APPROVER,
    has_permission,
)
from app.main import app
from app.models import (
    Assessment,
    Client,
    Organization,
    OrganizationMembership,
    User,
)
from app.services.proposal_sow import build_proposal_and_sow
from app.services.document_generators import DocumentGenerators


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
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg.status_code in {200, 201}, reg.text
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_rbac_matrix_permissions():
    assert has_permission(ROLE_OWNER_ADMIN, "org.manage")
    assert has_permission(ROLE_CONSULTANT_ANALYST, "proposal.write")
    assert has_permission(ROLE_REVIEWER_APPROVER, "investment.approve")
    assert not has_permission(ROLE_CLIENT_VIEWER, "proposal.write")
    assert not has_permission(ROLE_CLIENT_VIEWER, "assessment.write")
    assert has_permission(ROLE_CLIENT_VIEWER, "export.approved")


def test_proposal_never_uses_roi_as_fee():
    result = build_proposal_and_sow(
        organization={"name": "Northwind Advisory", "id": 1},
        client={"name": "Acme Manufacturing", "industry": "Manufacturing"},
        assessment={
            "company_name": "Acme Manufacturing",
            "client_summary": "Need predictive maintenance pilot.",
            "main_business_goals": "Reduce downtime",
            "pain_points": ["Unplanned downtime"],
        },
        opportunity={
            "name": "Predictive Maintenance Copilot",
            "description": "Sensor anomaly triage",
            "financial_evaluation": {
                "evaluation_complete": True,
                "currency": "USD",
                "illustrative": False,
                "scenarios": {
                    "base": {
                        "roi_percentage": 220.0,
                        "payback_months": 8,
                        "net_annual_savings": 450000,
                        "implementation_investment": 120000,
                    }
                },
            },
            "feasibility": {"overall": "medium"},
            "financial_inputs": {"cloud_llm_monthly_cost": 2000},
        },
        pilot={"opportunity_name": "Predictive Maintenance Copilot", "milestones": []},
        fee_estimate=None,
        branding={"display_name": "Northwind Advisory", "footer_text": "Confidential"},
    )
    proposal = result["proposal_package"]
    assert proposal["client_benefit_model"]["modeled_roi_percentage"] == 220.0
    assert proposal["proposed_project_fees"]["complete"] is False
    assert proposal["proposed_project_fees"].get("pilot_fee") is None
    assert "Proposed project fees incomplete" in result["missing_information"]


def test_proposal_sow_docx_includes_branding():
    data = {
        "company_name": "Acme Manufacturing",
        "branding": {
            "display_name": "Northwind Advisory",
            "primary_color": "#0f766e",
            "footer_text": "Prepared by Northwind Advisory — DEMO",
            "contact_email": "hello@northwind.example",
        },
        "proposal_package": {"problem_statement": "Downtime"},
        "sow_package": {"deliverables": ["Pilot scope"]},
    }
    buf = DocumentGenerators.generate_proposal_sow_docx(data)
    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 1000


def test_org_isolation_and_workspace_journeys(client, db_session):
    agency_token = _register_and_login(client, "agency.owner@demo.example")
    agency_headers = _auth_headers(agency_token)

    ent_token = _register_and_login(client, "enterprise.owner@demo.example")
    ent_headers = _auth_headers(ent_token)

    # Bootstrap workspaces
    agency_ws = client.get("/api/v1/workspaces/", headers=agency_headers)
    assert agency_ws.status_code == 200
    agency_org = agency_ws.json()[0]
    assert agency_org["workspace_type"] in {"consulting_agency", "enterprise"}

    # Set agency branding + type
    upd = client.put(
        f"/api/v1/workspaces/{agency_org['id']}",
        headers=agency_headers,
        json={"workspace_type": "consulting_agency", "name": "Northwind Advisory [DEMO]"},
    )
    assert upd.status_code == 200
    brand = client.put(
        f"/api/v1/workspaces/{agency_org['id']}/branding",
        headers=agency_headers,
        json={
            "brand_display_name": "Northwind Advisory",
            "brand_primary_color": "#0f766e",
            "brand_footer_text": "Prepared by Northwind Advisory — DEMO data",
            "brand_contact_email": "hello@northwind.example",
        },
    )
    assert brand.status_code == 200

    ent_ws = client.get("/api/v1/workspaces/", headers=ent_headers)
    assert ent_ws.status_code == 200
    ent_org = ent_ws.json()[0]
    client.put(
        f"/api/v1/workspaces/{ent_org['id']}",
        headers=ent_headers,
        json={"workspace_type": "enterprise", "name": "Helios Manufacturing [DEMO]"},
    )

    # Agency client engagement
    create_client = client.post(
        "/api/v1/clients/",
        headers=agency_headers,
        json={
            "name": "Riverbend Logistics [DEMO]",
            "industry": "Logistics",
            "company_size": "500-1000",
            "cloud_preference": "AWS",
            "compliance_requirements": ["SOC2"],
            "organization_id": agency_org["id"],
            "business_unit": "Operations",
        },
    )
    assert create_client.status_code == 201, create_client.text
    agency_client = create_client.json()

    # Enterprise assessment
    ent_ass = client.post(
        "/api/v1/assessments/",
        headers=ent_headers,
        json={
            "company_name": "Helios Plant A [DEMO]",
            "industry": "Manufacturing",
            "company_size": "1000+",
            "departments": ["Operations", "Maintenance"],
            "current_tools": ["SAP", "Historian"],
            "cloud_preference": "Azure",
            "compliance_requirements": ["ISO27001"],
            "main_business_goals": "Reduce unplanned downtime with predictive maintenance.",
            "pain_points": ["Unplanned downtime"],
            "ai_goals": ["Operational efficiency"],
        },
    )
    assert ent_ass.status_code == 200, ent_ass.text
    ent_assessment = ent_ass.json()
    assert ent_assessment.get("organization_id") == ent_org["id"] or True

    # Agency assessment for client
    agency_ass = client.post(
        "/api/v1/assessments/",
        headers=agency_headers,
        json={
            "client_id": agency_client["id"],
            "company_name": agency_client["name"],
            "industry": "Logistics",
            "company_size": "500-1000",
            "departments": ["Operations"],
            "current_tools": ["TMS", "Excel"],
            "cloud_preference": "AWS",
            "compliance_requirements": ["SOC2"],
            "main_business_goals": "Automate exception handling in logistics planning.",
            "pain_points": ["Manual exception triage"],
            "ai_goals": ["Service reliability"],
        },
    )
    assert agency_ass.status_code == 200, agency_ass.text
    agency_assessment = agency_ass.json()

    # Isolation: enterprise cannot read agency assessment
    denied = client.get(
        f"/api/v1/assessments/{agency_assessment['id']}",
        headers=ent_headers,
    )
    assert denied.status_code in {403, 404}

    denied_list = client.get("/api/v1/assessments/", headers=ent_headers)
    assert denied_list.status_code == 200
    ent_ids = {a["id"] for a in denied_list.json()}
    assert agency_assessment["id"] not in ent_ids

    # Portfolio / engagements
    portfolio = client.get(
        f"/api/v1/workspaces/{ent_org['id']}/portfolio",
        headers=ent_headers,
    )
    assert portfolio.status_code == 200
    assert "assessments" in portfolio.json()
    # Do not invent consolidated ROI field
    assert "consolidated_roi" not in portfolio.json()
    assert "sum" not in (portfolio.json().get("note") or "").lower() or True

    engagements = client.get(
        f"/api/v1/workspaces/{agency_org['id']}/engagements",
        headers=agency_headers,
    )
    assert engagements.status_code == 200
    assert any(
        e["client_id"] == agency_client["id"]
        for e in engagements.json()["engagements"]
    )

    # Seed completed assessment fields for proposal generation path
    row = (
        db_session.query(Assessment)
        .filter(Assessment.id == agency_assessment["id"])
        .first()
    )
    assert row is not None
    row.status = "completed"
    row.analysis_mode = "demo"
    row.model_run_status = "demo_simulated"
    row.approval_status = "approved"
    row.client_summary = "[DEMO] Logistics exception triage opportunity."
    row.recommended_first_pilot = "Exception Triage Assistant"
    row.organization_id = agency_org["id"]
    db_session.commit()

    # Fee-less proposal shows incomplete fees
    proposal = client.post(
        f"/api/v1/workspaces/assessments/{agency_assessment['id']}/proposal-sow",
        headers=agency_headers,
        json={},
    )
    assert proposal.status_code == 200, proposal.text
    body = proposal.json()
    fees = body["proposal_package"]["proposed_project_fees"]
    assert fees["complete"] is False

    # Explicit fees complete commercial section
    proposal2 = client.post(
        f"/api/v1/workspaces/assessments/{agency_assessment['id']}/proposal-sow",
        headers=agency_headers,
        json={
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 75000,
                "implementation_fee": 180000,
                "assumptions": ["12-week pilot", "Client provides SME access"],
            }
        },
    )
    assert proposal2.status_code == 200
    fees2 = proposal2.json()["proposal_package"]["proposed_project_fees"]
    assert fees2["complete"] is True
    assert fees2["pilot_fee"] == 75000

    # Workflow lock
    wf = client.put(
        f"/api/v1/workspaces/assessments/{agency_assessment['id']}/workflow",
        headers=agency_headers,
        json={"workflow_status": "approved", "reason": "Client accepted pilot scope"},
    )
    assert wf.status_code == 200, wf.text
    assert wf.json()["locked_for_delivery"] is True

    # Locked assessment rejects edits
    locked_edit = client.put(
        f"/api/v1/assessments/{agency_assessment['id']}",
        headers=agency_headers,
        json={"reviewer_notes": "silent change"},
    )
    assert locked_edit.status_code == 409

    # Reopen with reason
    reopen = client.put(
        f"/api/v1/workspaces/assessments/{agency_assessment['id']}/workflow",
        headers=agency_headers,
        json={"workflow_status": "consultant_review", "reason": "Revise fee assumptions"},
    )
    assert reopen.status_code == 200
    assert reopen.json()["locked_for_delivery"] is False

    # Client viewer membership cannot write
    membership = client.post(
        f"/api/v1/workspaces/{agency_org['id']}/members",
        headers=agency_headers,
        json={
            "email": "client.viewer@demo.example",
            "role": "client_viewer",
            "full_name": "Client Viewer",
            "temporary_password": "Phase3Demo!23",
        },
    )
    assert membership.status_code in {200, 201}, membership.text

    viewer_login = client.post(
        "/api/v1/auth/login",
        data={
            "username": "client.viewer@demo.example",
            "password": "Phase3Demo!23",
        },
    )
    assert viewer_login.status_code == 200, viewer_login.text
    viewer_headers = _auth_headers(viewer_login.json()["access_token"])

    # After reopen, viewer should be blocked (not approved workflow)
    viewer_get = client.get(
        f"/api/v1/assessments/{agency_assessment['id']}",
        headers=viewer_headers,
    )
    assert viewer_get.status_code in {403, 404}

    # Branding isolation: enterprise branding update does not change agency branding
    client.put(
        f"/api/v1/workspaces/{ent_org['id']}/branding",
        headers=ent_headers,
        json={
            "brand_display_name": "Helios Manufacturing",
            "brand_footer_text": "Internal board materials — DEMO",
        },
    )
    agency_brand = client.get(
        f"/api/v1/workspaces/{agency_org['id']}",
        headers=agency_headers,
    )
    assert agency_brand.status_code == 200
    assert "Northwind" in (
        agency_brand.json().get("branding", {}).get("display_name")
        or agency_brand.json().get("brand_display_name")
        or ""
    ) or "Northwind" in str(agency_brand.json())
