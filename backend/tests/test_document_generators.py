from app.services.document_generators import DocumentGenerators


def test_showcase_does_not_inject_apex_into_other_clients():
    payload = {
        "company_name": "Northwind Logistics - E2E Test Override",
        "client_summary": "Northwind summary overridden by e2e test validator.",
        "recommended_first_pilot": "Warehouse Slotting Assistant",
        "why_recommended_pilot": "Grounded in Northwind ops evidence.",
        "expected_pilot_impact": "Estimate: reduce slotting rework.",
        "reviewer_notes": "Approved after human review.",
        "export_mode": "showcase",
        "use_cases": [
            {
                "use_case_name": "Warehouse Slotting Assistant",
                "description": "Improve warehouse slotting",
                "department": "Operations",
            }
        ],
        "roadmap_items": [
            {
                "phase": "30-Day",
                "action_item": "Collect WMS extracts and confirm slotting KPIs.",
                "expected_impact": "Estimate: clearer pilot baseline.",
                "confidence": 0.0,
            }
        ],
        "extracted_signals": [
            {
                "source_file": "northwind_ops.txt",
                "description": "Observed manual slotting handoffs in WMS notes.",
            }
        ],
        "data_readiness": 55,
        "process_readiness": 50,
        "integration_readiness": 48,
        "governance_readiness": 52,
        "security_readiness": 60,
        "team_readiness": 45,
        "business_alignment": 70,
        "departments": ["Operations"],
        "compliance_requirements": [],
        "current_tools": ["WMS"],
    }
    cleaned = DocumentGenerators.cleanup_export_data(payload)
    assert "Apex" not in (cleaned.get("company_name") or "")
    assert "Apex" not in (cleaned.get("client_summary") or "")
    assert cleaned.get("recommended_first_pilot") == "Warehouse Slotting Assistant"
    action, _impact = DocumentGenerators.get_clean_roadmap_item(
        "30-Day",
        cleaned["roadmap_items"][0]["action_item"],
        cleaned["roadmap_items"][0]["expected_impact"],
    )
    assert "Proposal Copilot" not in action
    evidence = DocumentGenerators.get_client_facing_evidence(
        "northwind_ops.txt",
        "Observed manual slotting handoffs in WMS notes.",
    )
    assert "Apex" not in evidence
    assert "slotting" in evidence.lower()


def test_apex_demo_still_gets_apex_commercial_model():
    strategy = DocumentGenerators.calculate_commercial_strategy(
        {
            "company_name": "Apex Global Consulting Partners",
            "recommended_first_pilot": "Intelligent Pre-Sales Proposal Copilot",
            "use_cases": [],
            "departments": ["Sales & Pre-sales"],
            "data_readiness": 55,
            "process_readiness": 60,
            "integration_readiness": 50,
            "governance_readiness": 68,
            "security_readiness": 72,
            "team_readiness": 58,
            "business_alignment": 75,
            "compliance_requirements": ["GDPR"],
            "current_tools": ["Salesforce"],
        }
    )
    assert strategy["model"] == "Pilot MVP Build"
