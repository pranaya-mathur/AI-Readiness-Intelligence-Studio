from app.services.prioritization import (
    DEFAULT_CRITERION_WEIGHTS,
    PrioritizationEngine,
)


CTX = {
    "data_readiness": 55,
    "process_readiness": 60,
    "integration_readiness": 50,
    "governance_readiness": 65,
    "security_readiness": 70,
    "team_readiness": 58,
    "business_alignment": 75,
    "current_tools": ["SAP", "Excel"],
    "compliance_requirements": ["ISO 9001"],
}


def test_rankings_are_reproducible():
    opps = [
        {
            "use_case_name": "Quality Inspection",
            "description": "automated visual quality inspection",
            "value": "High",
            "complexity": "Medium",
            "risk": "Low",
            "evidence_refs": ["e1", "e2"],
        },
        {
            "use_case_name": "Document Processing",
            "description": "document checklist routing",
            "value": "High",
            "complexity": "Low",
            "risk": "Low",
            "evidence_refs": ["e3", "e4", "e5"],
        },
    ]
    a = PrioritizationEngine.rank_opportunities(opps, CTX)
    b = PrioritizationEngine.rank_opportunities(opps, CTX)
    assert [x.weighted_priority_score for x in a] == [x.weighted_priority_score for x in b]
    assert [x.ranking for x in a] == [x.ranking for x in b]


def test_hard_blocker_overrides_attractive_value():
    opps = [
        {
            "use_case_name": "High ROI Blocked",
            "description": "very valuable",
            "value": "High",
            "complexity": "Low",
            "risk": "Low",
            "evidence_refs": ["e1", "e2", "e3"],
            "hard_blockers": [
                {
                    "code": "legal_prohibition",
                    "description": "Legally prohibited processing",
                }
            ],
        },
        {
            "use_case_name": "Moderate Valid",
            "description": "document routing",
            "value": "Medium",
            "complexity": "Medium",
            "risk": "Medium",
            "evidence_refs": ["e4"],
        },
    ]
    ranked = PrioritizationEngine.rank_opportunities(opps, CTX)
    blocked = ranked[0]
    assert blocked.is_blocked is True
    assert blocked.recommendation_status == "blocked"
    assert blocked.weighted_priority_score is None
    assert blocked.ranking is None
    assert ranked[1].ranking == 1


def test_weight_configuration_changes_scores():
    opp = {
        "use_case_name": "Support Triage",
        "description": "ticket classification",
        "value": "High",
        "complexity": "Low",
        "risk": "Low",
        "evidence_refs": ["e1"],
        "criterion_scores": {
            "expected_business_value": 90,
            "technical_feasibility": 40,
            "data_readiness": 40,
            "process_readiness": 40,
            "integration_complexity": 40,
            "governance_security_risk": 40,
            "implementation_effort": 40,
            "time_to_value": 40,
            "organizational_change_readiness": 40,
            "evidence_sufficiency": 40,
        },
    }
    default = PrioritizationEngine.score_opportunity(opp, CTX)
    value_heavy = dict(DEFAULT_CRITERION_WEIGHTS)
    value_heavy["expected_business_value"] = 0.6
    for k in value_heavy:
        if k != "expected_business_value":
            value_heavy[k] = 0.4 / 9
    skewed = PrioritizationEngine.score_opportunity(opp, CTX, weights=value_heavy)
    assert skewed.weighted_priority_score != default.weighted_priority_score
    assert skewed.weighted_priority_score > default.weighted_priority_score


def test_missing_evidence_lowers_confidence():
    opp = {
        "use_case_name": "Sparse",
        "description": "unclear opportunity",
    }
    result = PrioritizationEngine.score_opportunity(opp, {})
    assert result.confidence_class in {"low", "insufficient"}
    assert result.missing_information
