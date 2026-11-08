#!/usr/bin/env python3
"""Release validation journeys against a live PostgreSQL-backed backend."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = os.getenv("E2E_BACKEND_BASE", "http://localhost:8001").rstrip("/")
API = f"{BASE}/api/v1"
REPO = Path(__file__).resolve().parents[2]
TEST_PACK = REPO / "AI_Readiness_E2E_Test_Pack 2"
OUT = Path("/tmp/release_validation_artifacts")
OUT.mkdir(parents=True, exist_ok=True)

results: dict[str, object] = {"base": BASE, "checks": {}}


def ok(name: str, detail: object = True) -> None:
    results["checks"][name] = {"pass": True, "detail": detail}
    print(f"[PASS] {name}: {detail}")


def fail(name: str, detail: object) -> None:
    results["checks"][name] = {"pass": False, "detail": detail}
    print(f"[FAIL] {name}: {detail}")
    raise SystemExit(1)


def auth(email: str, password: str = "ReleaseVal!23") -> dict:
    reg = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": password},
        timeout=30,
    )
    if reg.status_code not in {200, 201, 400}:
        fail("register", (email, reg.status_code, reg.text[:300]))
    login = requests.post(
        f"{API}/auth/login",
        data={"username": email, "password": password},
        timeout=30,
    )
    if login.status_code != 200:
        fail("login", (email, login.status_code, login.text[:300]))
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def main() -> None:
    ready = requests.get(f"{BASE}/readyz", timeout=15).json()
    if ready.get("status") != "ready" or ready.get("dialect") != "postgresql":
        fail("readyz", ready)
    ok("readyz", ready)

    # ------------------------------------------------------------------
    # Consulting agency journey
    # ------------------------------------------------------------------
    stamp = str(int(time.time()))
    agency = auth(f"release.agency.owner.{stamp}@demo.example")
    ws_list = requests.get(f"{API}/workspaces/", headers=agency, timeout=30).json()
    agency_org = ws_list[0]
    requests.put(
        f"{API}/workspaces/{agency_org['id']}",
        headers=agency,
        json={"workspace_type": "consulting_agency", "name": "Northwind Advisory [RELEASE]"},
        timeout=30,
    )
    client = requests.post(
        f"{API}/clients/",
        headers=agency,
        json={
            "name": f"Acme Logistics [RELEASE {stamp}]",
            "industry": "Logistics",
            "organization_id": agency_org["id"],
            "business_unit": "Operations",
        },
        timeout=30,
    )
    if client.status_code != 201:
        fail("agency_create_client", client.text)
    agency_client = client.json()
    ok("agency_create_client", agency_client["id"])

    ass = requests.post(
        f"{API}/assessments/",
        headers=agency,
        json={
            "client_id": agency_client["id"],
            "organization_id": agency_org["id"],
            "company_name": agency_client["name"],
            "industry": "Logistics",
            "company_size": "100-500 employees",
            "departments": ["Operations", "Customer Support"],
            "current_tools": ["Salesforce", "Excel"],
            "cloud_preference": "Azure",
            "compliance_requirements": ["GDPR"],
            "main_business_goals": "Reduce exception triage time and accelerate proposal turnaround.",
            "pain_points": ["Manual Process Overload", "Slow Support Response Times"],
            "ai_goals": ["Efficiency / Cost Reduction"],
        },
        timeout=30,
    )
    if ass.status_code != 200:
        fail("agency_create_assessment", ass.text)
    agency_ass = ass.json()
    if agency_ass.get("organization_id") != agency_org["id"]:
        fail("agency_assessment_org_scope", agency_ass)
    ok("agency_create_assessment", agency_ass["id"])

    files = []
    for name in [
        "Apex_Client_Brief.docx",
        "Apex_AI_Governance_Checklist.docx",
        "Apex_Sales_Playbook.pdf",
        "Apex_Support_Triage_Logs.txt",
        "Apex_Operations_Billing_Workflow.txt",
    ]:
        path = TEST_PACK / name
        files.append(("files", (name, path.read_bytes())))
    upload = requests.post(
        f"{API}/assessments/{agency_ass['id']}/upload",
        headers=agency,
        files=files,
        timeout=600,
    )
    if upload.status_code != 200:
        fail("agency_upload_run", (upload.status_code, upload.text[:500]))
    uploaded = upload.json()
    analysis_mode = uploaded.get("analysis_mode")
    model_status = uploaded.get("model_run_status")
    ok(
        "agency_upload_run",
        {
            "analysis_mode": analysis_mode,
            "model_run_status": model_status,
            "model_provider": uploaded.get("model_provider"),
            "model_name": uploaded.get("model_name"),
            "status": uploaded.get("status"),
            "overall_score": uploaded.get("overall_score"),
        },
    )
    provider = (uploaded.get("model_provider") or "").lower()
    real_model_ok = (
        analysis_mode == "real"
        and model_status == "success"
        and provider not in {"", "none", "demo"}
        and (uploaded.get("model_name") or "").lower() not in {"", "none", "walkthrough-seed"}
    )
    results["checks"]["real_model_agency"] = {
        "pass": real_model_ok,
        "detail": {
            "analysis_mode": analysis_mode,
            "model_run_status": model_status,
            "model_provider": uploaded.get("model_provider"),
            "model_name": uploaded.get("model_name"),
            "model_error": uploaded.get("model_error"),
        },
    }
    if real_model_ok:
        ok("real_model_agency", results["checks"]["real_model_agency"]["detail"])
    else:
        print(f"[WARN] agency real-model incomplete: {results['checks']['real_model_agency']}")

    inv = requests.get(
        f"{API}/assessments/{agency_ass['id']}/investment-intelligence",
        headers=agency,
        timeout=180,
    )
    if inv.status_code != 200 or not (inv.json().get("opportunities") or []):
        inv = requests.post(
            f"{API}/assessments/{agency_ass['id']}/investment-intelligence/recalculate",
            headers=agency,
            json={},
            timeout=180,
        )
    if inv.status_code != 200:
        fail("agency_investment", inv.text[:500])
    inv_body = inv.json()
    ok("agency_investment", {"opportunities": len(inv_body.get("opportunities") or [])})

    # Mark approval prerequisites if needed for proposal path
    patch = requests.put(
        f"{API}/assessments/{agency_ass['id']}",
        headers=agency,
        json={"approval_status": "approved", "client_summary": uploaded.get("client_summary") or "Release validation summary"},
        timeout=60,
    )
    if patch.status_code not in {200, 409}:
        # 409 if locked; continue
        print("approval patch", patch.status_code, patch.text[:200])

    prop = requests.post(
        f"{API}/workspaces/assessments/{agency_ass['id']}/proposal-sow",
        headers=agency,
        json={
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 65000,
                "implementation_fee": 180000,
                "assumptions": ["Release validation commercial assumptions"],
            }
        },
        timeout=120,
    )
    if prop.status_code != 200:
        fail("agency_proposal", prop.text[:500])
    ok("agency_proposal", {"complete": prop.json().get("complete")})

    wf = requests.put(
        f"{API}/workspaces/assessments/{agency_ass['id']}/workflow",
        headers=agency,
        json={"workflow_status": "approved", "reason": "Release validation approval"},
        timeout=60,
    )
    if wf.status_code != 200:
        fail("agency_approve", wf.text[:500])
    ok("agency_approve", wf.json())

    # Regeneration must preserve revision history
    regen = requests.post(
        f"{API}/workspaces/assessments/{agency_ass['id']}/proposal-sow",
        headers=agency,
        json={
            "reason": "Release validation reopen regenerate",
            "fee_estimate": {
                "currency": "USD",
                "pilot_fee": 70000,
                "implementation_fee": 190000,
                "assumptions": ["Revised after reopen"],
            },
        },
        timeout=120,
    )
    if regen.status_code != 200:
        fail("agency_proposal_regen", regen.text[:500])
    if regen.json().get("revision_count", 0) < 1:
        fail("agency_proposal_revision_history", regen.json())
    ok("agency_proposal_revision_history", regen.json().get("revision_count"))

    export = requests.get(
        f"{API}/assessments/{agency_ass['id']}/export/proposal-sow",
        headers=agency,
        timeout=120,
    )
    if export.status_code != 200:
        fail("agency_docx_export", (export.status_code, export.text[:300]))
    docx_path = OUT / "agency_proposal_sow.docx"
    docx_path.write_bytes(export.content)
    ok("agency_docx_export", {"bytes": len(export.content), "path": str(docx_path)})

    # ------------------------------------------------------------------
    # Enterprise journey (second org owner)
    # ------------------------------------------------------------------
    ent = auth(f"release.enterprise.owner.{stamp}@demo.example")
    ent_ws = requests.get(f"{API}/workspaces/", headers=ent, timeout=30).json()[0]
    requests.put(
        f"{API}/workspaces/{ent_ws['id']}",
        headers=ent,
        json={"workspace_type": "enterprise", "name": "Helios Manufacturing [RELEASE]"},
        timeout=30,
    )
    ent_ass = requests.post(
        f"{API}/assessments/",
        headers=ent,
        json={
            "organization_id": ent_ws["id"],
            "company_name": f"Helios Plant A [RELEASE {stamp}]",
            "industry": "Manufacturing",
            "company_size": "500-1000 employees",
            "departments": ["Operations", "Quality"],
            "current_tools": ["SAP", "Excel"],
            "cloud_preference": "AWS",
            "compliance_requirements": ["ISO 27001"],
            "main_business_goals": "Reduce unplanned downtime and scrap.",
            "pain_points": ["Unplanned downtime", "Manual quality checks"],
            "ai_goals": ["Efficiency / Cost Reduction", "Quality"],
        },
        timeout=30,
    )
    if ent_ass.status_code != 200:
        fail("enterprise_create_assessment", ent_ass.text)
    ent_assessment = ent_ass.json()
    ok("enterprise_create_assessment", ent_assessment["id"])

    # Use a lighter synthetic brief for enterprise to keep runtime bounded,
    # then still require real analysis_mode when available.
    brief = (
        "Helios Manufacturing Plant A release validation brief.\n"
        "Unplanned downtime averages 6 hours/week on Line 3.\n"
        "Quality scrap is elevated on changeovers.\n"
        "Operations wants predictive maintenance and quality anomaly triage pilots.\n"
    )
    ent_upload = requests.post(
        f"{API}/assessments/{ent_assessment['id']}/upload",
        headers=ent,
        files=[("files", ("helios_brief.txt", brief.encode("utf-8")))],
        timeout=600,
    )
    if ent_upload.status_code != 200:
        fail("enterprise_upload_run", ent_upload.text[:500])
    ent_uploaded = ent_upload.json()
    ok(
        "enterprise_upload_run",
        {
            "analysis_mode": ent_uploaded.get("analysis_mode"),
            "model_run_status": ent_uploaded.get("model_run_status"),
            "status": ent_uploaded.get("status"),
            "overall_score": ent_uploaded.get("overall_score"),
        },
    )
    ent_real = (
        ent_uploaded.get("analysis_mode") == "real"
        and (ent_uploaded.get("model_run_status") or "").lower() == "success"
        and (ent_uploaded.get("model_provider") or "").lower() not in {"", "none", "demo"}
    )
    results["checks"]["real_model_enterprise"] = {
        "pass": ent_real,
        "detail": {
            "analysis_mode": ent_uploaded.get("analysis_mode"),
            "model_run_status": ent_uploaded.get("model_run_status"),
            "model_provider": ent_uploaded.get("model_provider"),
            "model_name": ent_uploaded.get("model_name"),
            "model_error": ent_uploaded.get("model_error"),
        },
    }
    if ent_real:
        ok("real_model_enterprise", results["checks"]["real_model_enterprise"]["detail"])
    else:
        print(f"[WARN] enterprise real-model incomplete: {results['checks']['real_model_enterprise']}")

    # Approve + export PDF/DOCX/PPTX when completed
    if ent_uploaded.get("status") == "completed":
        requests.put(
            f"{API}/assessments/{ent_assessment['id']}",
            headers=ent,
            json={"approval_status": "approved"},
            timeout=60,
        )
        requests.put(
            f"{API}/workspaces/assessments/{ent_assessment['id']}/workflow",
            headers=ent,
            json={"workflow_status": "approved", "reason": "Enterprise release approval"},
            timeout=60,
        )
        export_ok = {}
        for fmt in ("pdf", "docx", "pptx"):
            resp = requests.get(
                f"{API}/assessments/{ent_assessment['id']}/export/{fmt}",
                headers=ent,
                timeout=180,
            )
            export_ok[fmt] = {
                "status": resp.status_code,
                "bytes": len(resp.content) if resp.status_code == 200 else 0,
            }
            if resp.status_code == 200:
                (OUT / f"enterprise_export.{fmt}").write_bytes(resp.content)
        if all(v["status"] == 200 and v["bytes"] > 1000 for v in export_ok.values()):
            ok("enterprise_exports", export_ok)
        else:
            fail("enterprise_exports", export_ok)

    # ------------------------------------------------------------------
    # RBAC / tenant isolation
    # ------------------------------------------------------------------
    # Agency owner must not read enterprise assessment
    denied = requests.get(
        f"{API}/assessments/{ent_assessment['id']}", headers=agency, timeout=30
    )
    if denied.status_code not in {403, 404}:
        fail("tenant_isolation_agency_to_enterprise", denied.status_code)
    ok("tenant_isolation_agency_to_enterprise", denied.status_code)

    denied2 = requests.get(
        f"{API}/assessments/{agency_ass['id']}", headers=ent, timeout=30
    )
    if denied2.status_code not in {403, 404}:
        fail("tenant_isolation_enterprise_to_agency", denied2.status_code)
    ok("tenant_isolation_enterprise_to_agency", denied2.status_code)

    # Client viewer membership directory restriction + engagement scope
    member = requests.post(
        f"{API}/workspaces/{agency_org['id']}/members",
        headers=agency,
        json={
            "email": f"release.viewer.{stamp}@demo.example",
            "role": "client_viewer",
            "temporary_password": "ReleaseVal!23",
            "authorized_client_ids": [agency_client["id"]],
        },
        timeout=30,
    )
    if member.status_code not in {200, 201}:
        fail("add_client_viewer", member.text)
    viewer = auth(f"release.viewer.{stamp}@demo.example")
    members_denied = requests.get(
        f"{API}/workspaces/{agency_org['id']}/members", headers=viewer, timeout=30
    )
    if members_denied.status_code != 403:
        fail("client_viewer_members_directory_blocked", members_denied.status_code)
    ok("client_viewer_members_directory_blocked", members_denied.status_code)

    # Second client unauthorized
    other_client = requests.post(
        f"{API}/clients/",
        headers=agency,
        json={
            "name": f"Unauthorized Client [RELEASE {stamp}]",
            "industry": "Retail",
            "organization_id": agency_org["id"],
        },
        timeout=30,
    ).json()
    other_ass = requests.post(
        f"{API}/assessments/",
        headers=agency,
        json={
            "client_id": other_client["id"],
            "organization_id": agency_org["id"],
            "company_name": other_client["name"],
            "industry": "Retail",
            "departments": ["Ops"],
            "current_tools": ["POS"],
            "main_business_goals": "Other",
            "pain_points": ["Manual"],
            "ai_goals": ["Efficiency"],
        },
        timeout=30,
    ).json()
    # Approve other so it would be viewer-visible if authorized
    # (seed completed fields via DB not available; rely on access control on list/get)
    cross = requests.get(f"{API}/assessments/{other_ass['id']}", headers=viewer, timeout=30)
    if cross.status_code not in {403, 404}:
        fail("client_viewer_cross_client_blocked", cross.status_code)
    ok("client_viewer_cross_client_blocked", cross.status_code)

    # Workspace client scoping: agency clients endpoint with org filter
    scoped = requests.get(
        f"{API}/clients/?organization_id={agency_org['id']}", headers=agency, timeout=30
    ).json()
    if not any(c["id"] == agency_client["id"] for c in scoped):
        fail("workspace_client_scope", scoped)
    ok("workspace_client_scope", len(scoped))

    report_path = OUT / "release_validation_results.json"
    report_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nWrote {report_path}")
    failed = [
        k
        for k, v in results["checks"].items()
        if isinstance(v, dict) and v.get("pass") is False
    ]
    if failed:
        print("FAILED CHECKS:", failed)
        sys.exit(1)
    print("ALL RELEASE JOURNEY CHECKS PASSED")


if __name__ == "__main__":
    main()
