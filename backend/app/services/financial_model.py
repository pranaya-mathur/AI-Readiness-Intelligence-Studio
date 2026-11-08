"""Deterministic financial feasibility / ROI engine.

Never invents missing financial inputs to produce attractive ROI.
Distinguishes measured, client-provided, consultant-assumed, modeled, and unknown.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

FINANCIAL_MODEL_VERSION = "v1.0.0"

Provenance = Literal[
    "measured_baseline",
    "client_provided_estimate",
    "consultant_assumption",
    "modeled_projection",
    "unknown",
    "illustrative_scenario",
]

SCENARIO_KEYS = ("conservative", "base", "optimistic")

REQUIRED_FOR_COMPLETE = (
    "monthly_volume",
    "effort_minutes_per_transaction",
    "loaded_hourly_cost",
    "automation_rate",
    "implementation_cost",
)


@dataclass
class AssumptionField:
    key: str
    value: float | str | None
    provenance: Provenance
    unit: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioResult:
    scenario: str
    complete: bool
    incomplete_reason: str | None
    currency: str
    horizon_months: int
    current_baseline_annual_cost: float | None
    gross_annual_savings: float | None
    net_annual_savings: float | None
    implementation_investment: float | None
    recurring_opex_annual: float | None
    annualized_net_benefit: float | None
    roi_percentage: float | None
    payback_months: float | None
    cumulative_cash_flow: list[dict[str, float]]
    break_even_month: int | None
    assumptions_used: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SensitivityPoint:
    parameter: str
    delta_pct: float
    resulting_roi_pct: float | None
    resulting_payback_months: float | None
    resulting_net_annual_savings: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinancialEvaluation:
    model_version: str
    currency: str
    evaluation_complete: bool
    incomplete_message: str | None
    illustrative: bool
    assumptions: dict[str, AssumptionField]
    scenarios: dict[str, ScenarioResult]
    sensitivity: list[SensitivityPoint]
    cost_breakdown: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "currency": self.currency,
            "evaluation_complete": self.evaluation_complete,
            "incomplete_message": self.incomplete_message,
            "illustrative": self.illustrative,
            "assumptions": {k: v.to_dict() for k, v in self.assumptions.items()},
            "scenarios": {k: v.to_dict() for k, v in self.scenarios.items()},
            "sensitivity": [s.to_dict() for s in self.sensitivity],
            "cost_breakdown": self.cost_breakdown,
        }


def _f(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _provenance(raw: Any, default: Provenance = "unknown") -> Provenance:
    allowed = {
        "measured_baseline",
        "client_provided_estimate",
        "consultant_assumption",
        "modeled_projection",
        "unknown",
        "illustrative_scenario",
    }
    if raw in allowed:
        return raw  # type: ignore[return-value]
    return default


class FinancialModelEngine:
    """Calculation-based ROI — reproducible and fail-closed on missing inputs."""

    @classmethod
    def evaluate(
        cls,
        inputs: dict[str, Any] | None,
        *,
        allow_illustrative: bool = False,
        weights_sensitivity: bool = True,
    ) -> FinancialEvaluation:
        raw = dict(inputs or {})
        illustrative = bool(raw.get("illustrative")) and allow_illustrative
        currency = str(raw.get("currency") or "USD")
        horizon = int(raw.get("evaluation_horizon_months") or 24)
        if horizon <= 0:
            horizon = 24

        assumptions = cls._parse_assumptions(raw, illustrative=illustrative)
        missing_required = [
            key
            for key in REQUIRED_FOR_COMPLETE
            if assumptions[key].value is None
            or assumptions[key].provenance == "unknown"
        ]

        if missing_required and not illustrative:
            incomplete = (
                "Financial evaluation incomplete — additional baseline information "
                f"required: {', '.join(missing_required)}."
            )
            empty_scenarios = {
                name: cls._empty_scenario(name, currency, horizon, incomplete)
                for name in SCENARIO_KEYS
            }
            return FinancialEvaluation(
                model_version=FINANCIAL_MODEL_VERSION,
                currency=currency,
                evaluation_complete=False,
                incomplete_message=incomplete,
                illustrative=False,
                assumptions=assumptions,
                scenarios=empty_scenarios,
                sensitivity=[],
                cost_breakdown={"status": "incomplete", "missing": missing_required},
            )

        if missing_required and illustrative:
            # Fill only explicitly selected illustrative defaults — clearly labeled.
            cls._apply_illustrative_defaults(assumptions)

        scenarios: dict[str, ScenarioResult] = {}
        for name in SCENARIO_KEYS:
            scenarios[name] = cls._compute_scenario(
                name, assumptions, currency=currency, horizon_months=horizon
            )

        sensitivity: list[SensitivityPoint] = []
        if weights_sensitivity and scenarios["base"].complete:
            sensitivity = cls._sensitivity(
                assumptions, currency=currency, horizon=horizon
            )

        cost_breakdown = {
            "implementation_cost": assumptions["implementation_cost"].value,
            "integration_cost": assumptions["integration_cost"].value,
            "cloud_llm_monthly": assumptions["cloud_llm_monthly_cost"].value,
            "licensing_monthly": assumptions["licensing_monthly_cost"].value,
            "support_monthly": assumptions["support_monthly_cost"].value,
            "baseline_annual_cost": scenarios["base"].current_baseline_annual_cost,
            "gross_annual_savings": scenarios["base"].gross_annual_savings,
            "recurring_opex_annual": scenarios["base"].recurring_opex_annual,
            "net_annual_savings": scenarios["base"].net_annual_savings,
        }

        return FinancialEvaluation(
            model_version=FINANCIAL_MODEL_VERSION,
            currency=currency,
            evaluation_complete=True,
            incomplete_message=None,
            illustrative=illustrative,
            assumptions=assumptions,
            scenarios=scenarios,
            sensitivity=sensitivity,
            cost_breakdown=cost_breakdown,
        )

    @classmethod
    def _parse_assumptions(
        cls, raw: dict[str, Any], *, illustrative: bool
    ) -> dict[str, AssumptionField]:
        meta = raw.get("provenance") or {}
        keys = {
            "monthly_volume": ("transactions/month", None),
            "effort_minutes_per_transaction": ("minutes", None),
            "loaded_hourly_cost": ("currency/hour", None),
            "automation_rate": ("0-1", None),
            "human_review_minutes": ("minutes", 0.0),
            "adoption_rate": ("0-1", 0.7),
            "error_rework_reduction_rate": ("0-1", 0.0),
            "implementation_cost": ("currency", None),
            "integration_cost": ("currency", 0.0),
            "cloud_llm_monthly_cost": ("currency/month", 0.0),
            "licensing_monthly_cost": ("currency/month", 0.0),
            "support_monthly_cost": ("currency/month", 0.0),
            "maintenance_monthly_cost": ("currency/month", 0.0),
        }
        out: dict[str, AssumptionField] = {}
        for key, (unit, default) in keys.items():
            val = _f(raw.get(key))
            if val is None and default is not None and key in raw:
                val = _f(default)
            if (
                val is None
                and default is not None
                and key
                not in (
                    "monthly_volume",
                    "effort_minutes_per_transaction",
                    "loaded_hourly_cost",
                    "automation_rate",
                    "implementation_cost",
                )
            ):
                # Optional fields may use safe zero defaults with consultant provenance
                # only when explicitly omitted (not when required core inputs missing).
                if key in raw and raw.get(key) is None:
                    val = None
                elif key not in raw:
                    val = float(default)
            prov = _provenance(
                meta.get(key),
                "illustrative_scenario"
                if illustrative and val is not None and key in REQUIRED_FOR_COMPLETE
                else (
                    "consultant_assumption"
                    if val is not None
                    and key not in REQUIRED_FOR_COMPLETE
                    and key not in raw
                    else ("unknown" if val is None else "client_provided_estimate")
                ),
            )
            if val is None:
                prov = "unknown"
            out[key] = AssumptionField(
                key=key,
                value=val,
                provenance=prov,
                unit=unit,
                notes=raw.get(f"{key}_notes"),
            )
        return out

    @classmethod
    def _apply_illustrative_defaults(
        cls, assumptions: dict[str, AssumptionField]
    ) -> None:
        defaults = {
            "monthly_volume": 1000.0,
            "effort_minutes_per_transaction": 30.0,
            "loaded_hourly_cost": 50.0,
            "automation_rate": 0.4,
            "implementation_cost": 75000.0,
        }
        for key, val in defaults.items():
            if (
                assumptions[key].value is None
                or assumptions[key].provenance == "unknown"
            ):
                assumptions[key] = AssumptionField(
                    key=key,
                    value=val,
                    provenance="illustrative_scenario",
                    unit=assumptions[key].unit,
                    notes="Illustrative placeholder — not a measured baseline",
                )

    @classmethod
    def _scenario_multipliers(cls, scenario: str) -> dict[str, float]:
        if scenario == "conservative":
            return {
                "automation_rate": 0.75,
                "adoption_rate": 0.8,
                "implementation_cost": 1.15,
                "opex": 1.1,
            }
        if scenario == "optimistic":
            return {
                "automation_rate": 1.15,
                "adoption_rate": 1.1,
                "implementation_cost": 0.9,
                "opex": 0.9,
            }
        return {
            "automation_rate": 1.0,
            "adoption_rate": 1.0,
            "implementation_cost": 1.0,
            "opex": 1.0,
        }

    @classmethod
    def _compute_scenario(
        cls,
        scenario: str,
        assumptions: dict[str, AssumptionField],
        *,
        currency: str,
        horizon_months: int,
    ) -> ScenarioResult:
        mult = cls._scenario_multipliers(scenario)
        monthly_volume = _f(assumptions["monthly_volume"].value)
        effort_min = _f(assumptions["effort_minutes_per_transaction"].value)
        hourly = _f(assumptions["loaded_hourly_cost"].value)
        automation = _f(assumptions["automation_rate"].value)
        review_min = _f(assumptions["human_review_minutes"].value) or 0.0
        adoption = _f(assumptions["adoption_rate"].value) or 0.0
        rework = _f(assumptions["error_rework_reduction_rate"].value) or 0.0
        impl = _f(assumptions["implementation_cost"].value)
        integ = _f(assumptions["integration_cost"].value) or 0.0
        cloud = _f(assumptions["cloud_llm_monthly_cost"].value) or 0.0
        license_ = _f(assumptions["licensing_monthly_cost"].value) or 0.0
        support = _f(assumptions["support_monthly_cost"].value) or 0.0
        maint = _f(assumptions["maintenance_monthly_cost"].value) or 0.0

        used = {
            k: {"value": assumptions[k].value, "provenance": assumptions[k].provenance}
            for k in assumptions
        }

        if None in (monthly_volume, effort_min, hourly, automation, impl):
            return cls._empty_scenario(
                scenario,
                currency,
                horizon_months,
                "Financial evaluation incomplete — additional baseline information required.",
            )

        # Clamp rates into sane bounds without inventing attractiveness.
        automation = max(0.0, min(1.0, automation * mult["automation_rate"]))
        adoption = max(0.0, min(1.0, adoption * mult["adoption_rate"]))
        rework = max(0.0, min(1.0, rework))
        impl_total = max(0.0, (impl + integ) * mult["implementation_cost"])
        opex_monthly = (cloud + license_ + support + maint) * mult["opex"]

        hours_per_txn = effort_min / 60.0
        baseline_monthly = monthly_volume * hours_per_txn * hourly
        baseline_annual = baseline_monthly * 12.0

        # Assisted/automated fraction of effort, after adoption, minus remaining review.
        review_hours = review_min / 60.0
        saved_hours_per_txn = max(0.0, hours_per_txn * automation - review_hours)
        gross_monthly = monthly_volume * saved_hours_per_txn * hourly * adoption
        # Optional rework reduction as additive modeled benefit on baseline.
        gross_monthly += baseline_monthly * rework * adoption * 0.25
        gross_annual = gross_monthly * 12.0

        recurring_annual = opex_monthly * 12.0
        net_annual = gross_annual - recurring_annual
        annualized_net_benefit = net_annual - (
            impl_total / max(horizon_months / 12.0, 1e-9)
        )

        if impl_total == 0 and net_annual > 0:
            roi = None  # undefined / infinite — expose as None with payback 0
            payback = 0.0
        elif impl_total == 0 and net_annual <= 0:
            roi = 0.0 if net_annual == 0 else -100.0
            payback = None
        else:
            roi = (net_annual / impl_total) * 100.0
            if net_annual <= 0:
                payback = None
            else:
                payback = (impl_total / net_annual) * 12.0

        cash_flow: list[dict[str, float]] = []
        cumulative = -impl_total
        break_even: int | None = None
        for month in range(1, horizon_months + 1):
            cumulative += net_annual / 12.0
            cash_flow.append(
                {"month": float(month), "cumulative": round(cumulative, 2)}
            )
            if break_even is None and cumulative >= 0:
                break_even = month

        return ScenarioResult(
            scenario=scenario,
            complete=True,
            incomplete_reason=None,
            currency=currency,
            horizon_months=horizon_months,
            current_baseline_annual_cost=round(baseline_annual, 2),
            gross_annual_savings=round(gross_annual, 2),
            net_annual_savings=round(net_annual, 2),
            implementation_investment=round(impl_total, 2),
            recurring_opex_annual=round(recurring_annual, 2),
            annualized_net_benefit=round(annualized_net_benefit, 2),
            roi_percentage=None if roi is None else round(roi, 2),
            payback_months=None if payback is None else round(payback, 2),
            cumulative_cash_flow=cash_flow,
            break_even_month=break_even,
            assumptions_used=used,
        )

    @classmethod
    def _empty_scenario(
        cls, scenario: str, currency: str, horizon: int, reason: str
    ) -> ScenarioResult:
        return ScenarioResult(
            scenario=scenario,
            complete=False,
            incomplete_reason=reason,
            currency=currency,
            horizon_months=horizon,
            current_baseline_annual_cost=None,
            gross_annual_savings=None,
            net_annual_savings=None,
            implementation_investment=None,
            recurring_opex_annual=None,
            annualized_net_benefit=None,
            roi_percentage=None,
            payback_months=None,
            cumulative_cash_flow=[],
            break_even_month=None,
            assumptions_used={},
        )

    @classmethod
    def _sensitivity(
        cls,
        assumptions: dict[str, AssumptionField],
        *,
        currency: str,
        horizon: int,
    ) -> list[SensitivityPoint]:
        points: list[SensitivityPoint] = []
        params = (
            ("adoption_rate", [-0.2, -0.1, 0.1, 0.2]),
            ("monthly_volume", [-0.2, -0.1, 0.1, 0.2]),
            ("human_review_minutes", [-0.2, -0.1, 0.1, 0.2]),
            ("cloud_llm_monthly_cost", [-0.2, -0.1, 0.1, 0.2]),
            ("automation_rate", [-0.2, -0.1, 0.1, 0.2]),
        )
        for param, deltas in params:
            base_val = _f(assumptions[param].value)
            if base_val is None:
                continue
            for delta in deltas:
                tweaked = {
                    k: AssumptionField(**asdict(v)) for k, v in assumptions.items()
                }
                tweaked[param] = AssumptionField(
                    key=param,
                    value=max(0.0, base_val * (1.0 + delta)),
                    provenance="modeled_projection",
                    unit=assumptions[param].unit,
                )
                result = cls._compute_scenario(
                    "base", tweaked, currency=currency, horizon_months=horizon
                )
                points.append(
                    SensitivityPoint(
                        parameter=param,
                        delta_pct=delta * 100.0,
                        resulting_roi_pct=result.roi_percentage,
                        resulting_payback_months=result.payback_months,
                        resulting_net_annual_savings=result.net_annual_savings,
                    )
                )
        return points
