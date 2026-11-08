from app.services.financial_model import FinancialModelEngine


COMPLETE_INPUTS = {
    "monthly_volume": 2000,
    "effort_minutes_per_transaction": 20,
    "loaded_hourly_cost": 45,
    "automation_rate": 0.5,
    "adoption_rate": 0.7,
    "human_review_minutes": 2,
    "implementation_cost": 120000,
    "integration_cost": 30000,
    "cloud_llm_monthly_cost": 2000,
    "licensing_monthly_cost": 500,
    "support_monthly_cost": 1000,
    "currency": "USD",
    "evaluation_horizon_months": 24,
    "provenance": {
        "monthly_volume": "measured_baseline",
        "effort_minutes_per_transaction": "client_provided_estimate",
        "loaded_hourly_cost": "consultant_assumption",
        "automation_rate": "consultant_assumption",
        "implementation_cost": "consultant_assumption",
    },
}


def test_complete_roi_is_deterministic():
    a = FinancialModelEngine.evaluate(COMPLETE_INPUTS)
    b = FinancialModelEngine.evaluate(COMPLETE_INPUTS)
    assert a.evaluation_complete is True
    assert a.scenarios["base"].roi_percentage == b.scenarios["base"].roi_percentage
    assert a.scenarios["base"].payback_months == b.scenarios["base"].payback_months
    assert a.scenarios["base"].net_annual_savings == b.scenarios["base"].net_annual_savings


def test_missing_inputs_do_not_fabricate_roi():
    result = FinancialModelEngine.evaluate({"currency": "EUR"})
    assert result.evaluation_complete is False
    assert "additional baseline information required" in (result.incomplete_message or "").lower()
    assert result.scenarios["base"].roi_percentage is None
    assert result.scenarios["base"].complete is False


def test_negative_and_zero_roi_safe():
    costly = dict(COMPLETE_INPUTS)
    costly["automation_rate"] = 0.01
    costly["adoption_rate"] = 0.1
    costly["implementation_cost"] = 5_000_000
    result = FinancialModelEngine.evaluate(costly)
    assert result.evaluation_complete is True
    assert result.scenarios["base"].roi_percentage is not None
    assert result.scenarios["base"].roi_percentage < 0
    assert result.scenarios["base"].payback_months is None

    zero_impl = dict(COMPLETE_INPUTS)
    zero_impl["implementation_cost"] = 0
    zero_impl["integration_cost"] = 0
    z = FinancialModelEngine.evaluate(zero_impl)
    assert z.evaluation_complete is True


def test_scenarios_diverge():
    result = FinancialModelEngine.evaluate(COMPLETE_INPUTS)
    cons = result.scenarios["conservative"].roi_percentage
    base = result.scenarios["base"].roi_percentage
    opt = result.scenarios["optimistic"].roi_percentage
    assert cons is not None and base is not None and opt is not None
    assert cons <= base <= opt


def test_sensitivity_analysis_present():
    result = FinancialModelEngine.evaluate(COMPLETE_INPUTS)
    assert result.sensitivity
    params = {p.parameter for p in result.sensitivity}
    assert "adoption_rate" in params
    assert "monthly_volume" in params


def test_illustrative_only_when_explicit():
    blocked = FinancialModelEngine.evaluate({}, allow_illustrative=False)
    assert blocked.evaluation_complete is False
    illustrative = FinancialModelEngine.evaluate(
        {"illustrative": True}, allow_illustrative=True
    )
    assert illustrative.evaluation_complete is True
    assert illustrative.illustrative is True
    assert all(
        illustrative.assumptions[k].provenance == "illustrative_scenario"
        for k in (
            "monthly_volume",
            "effort_minutes_per_transaction",
            "loaded_hourly_cost",
            "automation_rate",
            "implementation_cost",
        )
    )


def test_recalculation_changes_with_assumptions():
    base = FinancialModelEngine.evaluate(COMPLETE_INPUTS)
    tweaked = dict(COMPLETE_INPUTS)
    tweaked["adoption_rate"] = 0.95
    updated = FinancialModelEngine.evaluate(tweaked)
    assert (
        updated.scenarios["base"].net_annual_savings
        != base.scenarios["base"].net_annual_savings
    )
