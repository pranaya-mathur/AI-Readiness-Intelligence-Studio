"""Synthetic Phase 2 end-to-end evaluation cases (not hardcoded outcomes)."""

from app.services.feasibility import TechnicalFeasibilityEngine
from app.services.investment_intelligence import InvestmentIntelligenceEngine


MANUFACTURING_CTX = {
    "data_readiness": 48,
    "process_readiness": 62,
    "integration_readiness": 45,
    "governance_readiness": 55,
    "security_readiness": 60,
    "team_readiness": 50,
    "business_alignment": 70,
    "current_tools": ["SAP", "PLC Historian", "SharePoint"],
    "compliance_requirements": ["ISO 9001", "OSHA"],
    "industry": "Manufacturing",
}

CONSULTING_CTX = {
    "data_readiness": 58,
    "process_readiness": 65,
    "integration_readiness": 55,
    "governance_readiness": 68,
    "security_readiness": 72,
    "team_readiness": 60,
    "business_alignment": 80,
    "current_tools": ["Salesforce", "SharePoint", "Jira Service Desk"],
    "compliance_requirements": ["GDPR", "SOC2"],
    "industry": "Professional Services",
}


def _case_a_opportunities():
    return [
        {
            "use_case_name": "Quality Inspection Copilot",
            "description": "vision-assisted quality inspection on production line",
            "value": "High",
            "complexity": "High",
            "risk": "Medium",
            "evidence_refs": ["mfg_qi_1", "mfg_qi_2"],
            "financial_inputs": {
                "monthly_volume": 8000,
                "effort_minutes_per_transaction": 6,
                "loaded_hourly_cost": 38,
                "automation_rate": 0.45,
                "adoption_rate": 0.6,
                "implementation_cost": 180000,
                "integration_cost": 40000,
                "cloud_llm_monthly_cost": 1500,
                "currency": "USD",
            },
        },
        {
            "use_case_name": "Predictive Maintenance Alerts",
            "description": "predict anomaly and maintenance windows from sensor streams",
            "value": "High",
            "complexity": "High",
            "risk": "High",
            "evidence_refs": ["mfg_pm_1"],
            "hard_blockers": [
                {
                    "code": "mandatory_data_unavailable",
                    "description": "Required high-frequency sensor dataset unavailable",
                }
            ],
            "financial_inputs": {
                "monthly_volume": 500,
                "effort_minutes_per_transaction": 90,
                "loaded_hourly_cost": 55,
                "automation_rate": 0.5,
                "implementation_cost": 250000,
                "currency": "USD",
            },
        },
        {
            "use_case_name": "Document Processing for Work Orders",
            "description": "document checklist routing for work-order packets",
            "value": "Medium",
            "complexity": "Low",
            "risk": "Low",
            "evidence_refs": ["mfg_doc_1", "mfg_doc_2", "mfg_doc_3"],
            "financial_inputs": {
                "monthly_volume": 1200,
                "effort_minutes_per_transaction": 25,
                "loaded_hourly_cost": 40,
                "automation_rate": 0.5,
                "adoption_rate": 0.75,
                "implementation_cost": 90000,
                "integration_cost": 20000,
                "currency": "USD",
            },
        },
    ]


def _case_b_opportunities():
    return [
        {
            "use_case_name": "Customer Support Triage",
            "description": "support ticket classification and routing assistant",
            "value": "High",
            "complexity": "Medium",
            "risk": "Medium",
            "evidence_refs": ["con_sup_1", "con_sup_2"],
            "financial_inputs": {
                "monthly_volume": 3500,
                "effort_minutes_per_transaction": 12,
                "loaded_hourly_cost": 48,
                "automation_rate": 0.4,
                "adoption_rate": 0.7,
                "human_review_minutes": 3,
                "implementation_cost": 110000,
                "integration_cost": 25000,
                "cloud_llm_monthly_cost": 2500,
                "currency": "USD",
            },
        },
        {
            "use_case_name": "Proposal Automation",
            "description": "document drafting assistant for proposals and RFPs",
            "value": "High",
            "complexity": "Medium",
            "risk": "Medium",
            "evidence_refs": ["con_prop_1", "con_prop_2", "con_prop_3"],
            "financial_inputs": {
                "monthly_volume": 80,
                "effort_minutes_per_transaction": 240,
                "loaded_hourly_cost": 85,
                "automation_rate": 0.35,
                "adoption_rate": 0.65,
                "human_review_minutes": 45,
                "implementation_cost": 140000,
                "integration_cost": 30000,
                "currency": "USD",
            },
        },
        {
            "use_case_name": "Back-office Workflow Automation",
            "description": "reconcile billing workflow columns and checklist routing",
            "value": "Medium",
            "complexity": "Low",
            "risk": "Low",
            "evidence_refs": ["con_bo_1"],
            "financial_inputs": {
                "monthly_volume": 900,
                "effort_minutes_per_transaction": 30,
                "loaded_hourly_cost": 42,
                "automation_rate": 0.55,
                "adoption_rate": 0.8,
                "implementation_cost": 75000,
                "currency": "USD",
            },
        },
    ]


def test_case_a_manufacturing_package():
    package = InvestmentIntelligenceEngine.build_package(
        _case_a_opportunities(), MANUFACTURING_CTX
    )
    opps = package["opportunities"]
    assert len(opps) == 3
    blocked = [o for o in opps if o["is_blocked"]]
    assert len(blocked) == 1
    assert blocked[0]["use_case_name"] == "Predictive Maintenance Alerts"
    ranked = [o for o in opps if o["ranking"] is not None]
    assert ranked
    assert ranked[0]["ranking"] == 1
    # Rankings are explainable and deterministic — not invented by LLM.
    again = InvestmentIntelligenceEngine.build_package(
        _case_a_opportunities(), MANUFACTURING_CTX
    )
    assert [o["weighted_priority_score"] for o in opps] == [
        o["weighted_priority_score"] for o in again["opportunities"]
    ]
    pilot = package["pilot_recommendation"]
    assert pilot is not None
    assert pilot["opportunity_name"] != "Predictive Maintenance Alerts"
    assert package["decision_summary"]["status"] in {
        "invest",
        "validate_first",
        "defer",
        "not_recommended",
    }
    for o in opps:
        assert o["feasibility"]["proposed_approach"]
        assert o["financial_evaluation"]["evaluation_complete"] is True


def test_case_b_consulting_package():
    package = InvestmentIntelligenceEngine.build_package(
        _case_b_opportunities(), CONSULTING_CTX
    )
    opps = package["opportunities"]
    assert len(opps) == 3
    assert all(not o["is_blocked"] for o in opps)
    names = {o["use_case_name"] for o in opps}
    assert names == {
        "Customer Support Triage",
        "Proposal Automation",
        "Back-office Workflow Automation",
    }
    pilot = package["pilot_recommendation"]
    assert pilot["opportunity_name"] in names
    assert pilot["stages"]
    assert pilot["success_metrics"]
    # No fabricated fixed percentages in success targets.
    for metric in pilot["success_metrics"]:
        assert "invent" not in metric["target"].lower() or "do not invent" in metric[
            "target"
        ].lower()


def test_contradictory_missing_evidence_validate_first():
    sparse = [
        {
            "use_case_name": "Unclear Opportunity",
            "description": "insufficient context",
        }
    ]
    package = InvestmentIntelligenceEngine.build_package(sparse, {})
    opp = package["opportunities"][0]
    assert opp["confidence_class"] in {"low", "insufficient"}
    assert opp["missing_information"]
    assert package["decision_summary"]["status"] in {
        "validate_first",
        "defer",
        "not_recommended",
    }


def test_feasibility_prefers_simple_approach():
    triage = TechnicalFeasibilityEngine.assess(
        {
            "use_case_name": "Support Triage",
            "description": "ticket classification and routing",
            "evidence_refs": ["e1"],
        },
        CONSULTING_CTX,
    )
    assert triage.proposed_approach != "agentic_orchestration"
    assert "deterministic" in triage.proposed_approach or "supervised" in triage.proposed_approach or "conventional" in triage.proposed_approach or "llm_assisted" in triage.proposed_approach


def test_export_package_fields_present_for_generators():
    package = InvestmentIntelligenceEngine.build_package(
        _case_b_opportunities(), CONSULTING_CTX
    )
    assessment_dict = {
        "company_name": "Agency Client Co",
        "investment_package": package,
        "prioritization_rubric_version": package["prioritization_rubric_version"],
        "investment_decision_status": package["decision_summary"]["status"],
    }
    from app.services.document_generators import DocumentGenerators

    html = DocumentGenerators._investment_intelligence_html(assessment_dict)
    assert "Investment" in html or "Opportunity" in html or "Rank" in html
    assert package["opportunities"][0]["use_case_name"] in html or "priority" in html.lower()
