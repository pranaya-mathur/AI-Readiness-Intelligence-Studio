from app.services.scoring import DIMENSION_WEIGHTS, ScoringEngine


def test_deterministic_weighted_overall():
    scores = {k: 50.0 for k in DIMENSION_WEIGHTS}
    assert ScoringEngine.weighted_overall(scores) == 50.0
    scores["data_readiness"] = 100.0
    expected = round(50.0 + (50.0 * DIMENSION_WEIGHTS["data_readiness"]), 1)
    assert ScoringEngine.weighted_overall(scores) == expected


def test_score_recompute_stable_and_evidence_sensitive():
    weak = ScoringEngine.score(
        company_name="Acme",
        industry="Services",
        departments=["Operations"],
        current_tools=["Excel"],
        pain_points=["Manual Process Overload", "Data Silos"],
        ai_goals=["Efficiency / Cost Reduction"],
        compliance_requirements=[],
        cloud_preference="Cloud-agnostic",
        main_business_goals="",
        evidence_package={
            "evidence_items": [],
            "insufficient_evidence": True,
            "missing_evidence": ["none"],
        },
    )
    strong = ScoringEngine.score(
        company_name="Acme",
        industry="Services",
        departments=["Operations", "Sales & Pre-sales"],
        current_tools=["Salesforce", "Azure"],
        pain_points=["Manual Process Overload"],
        ai_goals=["Efficiency / Cost Reduction", "Upskilling"],
        compliance_requirements=["GDPR", "SOC2"],
        cloud_preference="Azure",
        main_business_goals="Reduce proposal cycle time",
        evidence_package={
            "insufficient_evidence": False,
            "missing_evidence": [],
            "evidence_items": [
                {
                    "evidence_id": "ev1",
                    "related_dimensions": ["data", "process", "governance", "security"],
                    "evidence_tier": "verified",
                    "signal_type": "Workflow Evidence",
                    "description": "SOP workflow with API integration and GDPR audit policy",
                }
            ],
        },
        bottlenecks=[{"process_name": "Manual"}],
        use_cases=[{"use_case_name": "Copilot"}],
    )
    assert weak.scoring_method == "deterministic_rubric_v1"
    assert weak.rubric_version == strong.rubric_version
    assert strong.overall_score >= weak.overall_score
    assert "estimate" in weak.automation_potential_basis
    flat = strong.flat_assessment_fields()
    assert flat[
        "overall_score"
    ] == ScoringEngine.recompute_overall_from_assessment_fields(flat)
    for dim in strong.dimensions.values():
        assert dim.reviewer_status == "pending"
        assert isinstance(dim.evidence_refs, list)
        assert isinstance(dim.missing_information, list)
