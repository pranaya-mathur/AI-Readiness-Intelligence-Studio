"""PDF/DOCX/PPTX generator smoke tests without Apex contamination."""

from app.services.document_generators import DocumentGenerators


def _sample_assessment():
    return {
        "company_name": "Helios Manufacturing",
        "industry": "Manufacturing",
        "client_summary": "Helios is evaluating AI for quality inspection triage.",
        "recommended_first_pilot": "Quality Inspection Triage Assistant",
        "why_recommended_pilot": "Verified inspection backlog evidence supports a scoped pilot.",
        "expected_pilot_impact": "Estimate: reduce inspection queue delay.",
        "reviewer_notes": "Approved for export.",
        "approval_status": "approved",
        "overall_score": 58.0,
        "automation_potential": 24.0,
        "readiness_interpretation": "Moderate readiness with evidence gaps in team enablement.",
        "data_readiness": 55,
        "data_justification": "MES extracts exist but are siloed.",
        "process_readiness": 52,
        "process_justification": "Inspection SOPs are partial.",
        "integration_readiness": 50,
        "integration_justification": "Limited API coverage.",
        "governance_readiness": 54,
        "governance_justification": "Policy drafts exist.",
        "security_readiness": 60,
        "security_justification": "Baseline controls present.",
        "team_readiness": 45,
        "team_justification": "Training plan missing.",
        "business_alignment": 70,
        "alignment_justification": "Quality KPIs are explicit.",
        "departments": ["Operations", "Quality"],
        "current_tools": ["MES", "Excel"],
        "compliance_requirements": ["ISO9001"],
        "pain_points": ["Manual Process Overload"],
        "ai_goals": ["Efficiency / Cost Reduction"],
        "bottlenecks": [
            {
                "department": "Quality",
                "process_name": "Manual defect triage",
                "bottleneck_description": "Inspectors manually classify defects.",
                "ai_potential": "High",
            }
        ],
        "use_cases": [
            {
                "use_case_name": "Quality Inspection Triage Assistant",
                "department": "Quality",
                "description": "Assist inspectors with defect classification.",
                "value": "High",
                "complexity": "Medium",
                "risk": "Medium",
                "priority": "P1",
                "evidence": "ev_quality_1",
                "confidence": 0.0,
            }
        ],
        "risks": [
            {
                "risk_name": "False defect classification",
                "severity": "High",
                "recommendation": "Keep human approval in the loop.",
                "is_control_met": 0,
            }
        ],
        "roadmap_items": [
            {
                "phase": "30-Day",
                "action_item": "Collect labeled defect samples and success metrics.",
                "expected_impact": "Estimate: clearer evaluation baseline.",
                "confidence": 0.0,
            },
            {
                "phase": "60-Day",
                "action_item": "Run shadow-mode triage with human review.",
                "expected_impact": "Estimate: validate precision before automation.",
                "confidence": 0.0,
            },
            {
                "phase": "90-Day",
                "action_item": "Expand controls and operator training.",
                "expected_impact": "Estimate: safer limited rollout.",
                "confidence": 0.0,
            },
        ],
        "extracted_signals": [
            {
                "source_file": "helios_quality_sop.pdf",
                "signal_type": "Workflow Evidence",
                "description": "Observed manual defect classification steps.",
                "confidence": 0.0,
                "excerpt": "Inspectors manually classify defects on line 3.",
                "page_or_section": "page 2",
                "evidence_tier": "verified",
            }
        ],
    }


def test_pdf_docx_pptx_generation_for_genuine_client():
    data = _sample_assessment()
    pdf = DocumentGenerators.generate_pdf_report(dict(data))
    docx = DocumentGenerators.generate_docx_proposal(dict(data))
    pptx = DocumentGenerators.generate_pptx_deck(dict(data))
    assert pdf.getbuffer().nbytes > 500
    assert docx.getbuffer().nbytes > 500
    assert pptx.getbuffer().nbytes > 500

    # Showcase cleanup must still preserve Helios identity.
    cleaned = DocumentGenerators.cleanup_export_data(
        {**data, "export_mode": "showcase"}
    )
    assert cleaned["company_name"] == "Helios Manufacturing"
    assert "Apex" not in cleaned["company_name"]
    assert "Proposal Copilot" not in (cleaned.get("recommended_first_pilot") or "")
