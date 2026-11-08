"""Versioned, deterministic AI opportunity prioritization rubric.

LLM may propose opportunities and narratives; numerical scores are computed here.
Hard feasibility blockers are evaluated separately and never overridden by ROI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PRIORITIZATION_RUBRIC_VERSION = "v1.0.0"

# Configurable criterion weights (must sum to 1.0).
DEFAULT_CRITERION_WEIGHTS: dict[str, float] = {
    "expected_business_value": 0.18,
    "technical_feasibility": 0.14,
    "data_readiness": 0.12,
    "process_readiness": 0.10,
    "integration_complexity": 0.10,  # higher score = lower complexity (inverted input)
    "governance_security_risk": 0.10,  # higher score = lower residual risk
    "implementation_effort": 0.08,  # higher score = lower effort
    "time_to_value": 0.08,  # higher score = faster value
    "organizational_change_readiness": 0.05,
    "evidence_sufficiency": 0.05,
}

CRITERION_KEYS = tuple(DEFAULT_CRITERION_WEIGHTS.keys())

# Qualitative labels → 0-100 for deterministic mapping when numeric input absent.
_QUAL_HIGH_IS_GOOD = {"high": 85.0, "medium": 55.0, "low": 25.0, "unknown": 0.0}
_QUAL_HIGH_IS_BAD = {"high": 25.0, "medium": 55.0, "low": 85.0, "unknown": 0.0}

HARD_BLOCKER_CODES = {
    "legal_prohibition",
    "mandatory_data_unavailable",
    "missing_required_client_approval",
    "critical_security_dependency",
}


@dataclass
class CriterionResult:
    criterion: str
    score: float
    weight: float
    weighted_contribution: float
    basis: str
    missing_information: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HardBlocker:
    code: str
    description: str
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OpportunityPriorityResult:
    rubric_version: str
    criterion_scores: dict[str, CriterionResult]
    criterion_weights: dict[str, float]
    weighted_priority_score: float | None
    ranking: int | None
    ranking_explanation: str
    evidence_refs: list[str]
    missing_information: list[str]
    confidence_class: str  # high | medium | low | insufficient
    recommendation_status: (
        str  # prioritize | validate_first | defer | blocked | not_recommended
    )
    hard_blockers: list[HardBlocker]
    is_blocked: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "rubric_version": self.rubric_version,
            "criterion_scores": {
                k: v.to_dict() for k, v in self.criterion_scores.items()
            },
            "criterion_weights": dict(self.criterion_weights),
            "weighted_priority_score": self.weighted_priority_score,
            "ranking": self.ranking,
            "ranking_explanation": self.ranking_explanation,
            "evidence_refs": list(self.evidence_refs),
            "missing_information": list(self.missing_information),
            "confidence_class": self.confidence_class,
            "recommendation_status": self.recommendation_status,
            "hard_blockers": [b.to_dict() for b in self.hard_blockers],
            "is_blocked": self.is_blocked,
        }


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
    base = dict(DEFAULT_CRITERION_WEIGHTS)
    if weights:
        for key, val in weights.items():
            if key in base and val is not None:
                base[key] = float(val)
    total = sum(base.values())
    if total <= 0:
        return dict(DEFAULT_CRITERION_WEIGHTS)
    return {k: v / total for k, v in base.items()}


def _qual_to_score(raw: Any, *, high_is_good: bool) -> tuple[float, str, list[str]]:
    if raw is None:
        return 0.0, "unknown", ["Missing qualitative input"]
    if isinstance(raw, (int, float)):
        return _clamp(float(raw)), "numeric_input", []
    label = str(raw).strip().lower()
    table = _QUAL_HIGH_IS_GOOD if high_is_good else _QUAL_HIGH_IS_BAD
    if label in table:
        score = table[label]
        basis = "qualitative_map" if label != "unknown" else "unknown"
        missing = ["Qualitative rating unknown"] if label == "unknown" else []
        return score, basis, missing
    return 0.0, "unrecognized", [f"Unrecognized qualitative value: {raw}"]


def detect_hard_blockers(
    opportunity: dict[str, Any],
    assessment_context: dict[str, Any] | None = None,
) -> list[HardBlocker]:
    """Separate hard blockers from weighted scoring."""
    blockers: list[HardBlocker] = []
    ctx = assessment_context or {}
    explicit = opportunity.get("hard_blockers") or []
    for item in explicit:
        if isinstance(item, dict):
            code = str(item.get("code") or "unspecified")
            blockers.append(
                HardBlocker(
                    code=code,
                    description=str(item.get("description") or code),
                    evidence_refs=list(item.get("evidence_refs") or []),
                )
            )
        elif isinstance(item, str) and item.strip():
            blockers.append(HardBlocker(code=item.strip(), description=item.strip()))

    flags = {str(f).lower() for f in (opportunity.get("blocker_flags") or [])}
    text_blob = " ".join(
        str(x or "")
        for x in [
            opportunity.get("description"),
            opportunity.get("feasibility_notes"),
            opportunity.get("governance_notes"),
            *(opportunity.get("missing_information") or []),
        ]
    ).lower()

    if "legal_prohibition" in flags or "legally prohibited" in text_blob:
        blockers.append(
            HardBlocker(
                code="legal_prohibition",
                description="Processing appears legally prohibited for this use case.",
                evidence_refs=list(opportunity.get("evidence_refs") or []),
            )
        )
    if (
        "mandatory_data_unavailable" in flags
        or "mandatory dataset unavailable" in text_blob
    ):
        blockers.append(
            HardBlocker(
                code="mandatory_data_unavailable",
                description="Mandatory datasets required for the opportunity are unavailable.",
                evidence_refs=list(opportunity.get("evidence_refs") or []),
            )
        )
    if "missing_required_client_approval" in flags or opportunity.get(
        "requires_client_approval_missing"
    ):
        blockers.append(
            HardBlocker(
                code="missing_required_client_approval",
                description="Required client approval is missing.",
                evidence_refs=list(opportunity.get("evidence_refs") or []),
            )
        )
    try:
        security_rd = float(ctx.get("security_readiness") or 0)
    except (TypeError, ValueError):
        security_rd = 0.0
    if "critical_security_dependency" in flags or (
        security_rd < 25
        and "security" in text_blob
        and opportunity.get("requires_security_clearance")
    ):
        blockers.append(
            HardBlocker(
                code="critical_security_dependency",
                description="Unresolved critical security dependency blocks safe delivery.",
                evidence_refs=list(opportunity.get("evidence_refs") or []),
            )
        )

    # De-duplicate by code
    seen: set[str] = set()
    unique: list[HardBlocker] = []
    for b in blockers:
        if b.code in seen:
            continue
        seen.add(b.code)
        unique.append(b)
    return unique


class PrioritizationEngine:
    """Deterministic opportunity ranking — never trusts LLM numeric priority."""

    @classmethod
    def score_opportunity(
        cls,
        opportunity: dict[str, Any],
        assessment_context: dict[str, Any] | None = None,
        weights: dict[str, float] | None = None,
        criterion_overrides: dict[str, float] | None = None,
    ) -> OpportunityPriorityResult:
        ctx = assessment_context or {}
        norm_weights = _normalize_weights(weights)
        blockers = detect_hard_blockers(opportunity, ctx)
        is_blocked = len(blockers) > 0

        criterion_inputs = cls._derive_criterion_inputs(opportunity, ctx)
        if criterion_overrides:
            for key, val in criterion_overrides.items():
                if key in criterion_inputs and val is not None:
                    criterion_inputs[key] = (
                        _clamp(float(val)),
                        "human_override",
                        [],
                        list(criterion_inputs[key][3]),
                    )

        results: dict[str, CriterionResult] = {}
        missing: list[str] = []
        evidence_refs: list[str] = list(opportunity.get("evidence_refs") or [])
        weighted_sum = 0.0
        available_weight = 0.0

        for key in CRITERION_KEYS:
            score, basis, crit_missing, refs = criterion_inputs[key]
            weight = norm_weights[key]
            if basis in {"unknown", "unrecognized"} or score <= 0 and crit_missing:
                contribution = 0.0
            else:
                contribution = score * weight
                available_weight += weight
                weighted_sum += contribution
            results[key] = CriterionResult(
                criterion=key,
                score=round(score, 2),
                weight=round(weight, 4),
                weighted_contribution=round(contribution, 2),
                basis=basis,
                missing_information=crit_missing,
                evidence_refs=refs,
            )
            missing.extend(crit_missing)
            for r in refs:
                if r not in evidence_refs:
                    evidence_refs.append(r)

        # Normalize by available weight so unknown criteria do not silently inflate ranks.
        if available_weight > 0:
            priority = round(weighted_sum / available_weight, 2)
        else:
            priority = None

        unknown_count = sum(
            1
            for r in results.values()
            if r.basis in {"unknown", "unrecognized"} or r.missing_information
        )
        if priority is None or unknown_count >= 6:
            confidence = "insufficient"
        elif unknown_count >= 3:
            confidence = "low"
        elif unknown_count >= 1:
            confidence = "medium"
        else:
            confidence = "high"

        if is_blocked:
            status = "blocked"
            explanation = (
                "Opportunity is blocked by hard feasibility conditions and cannot be "
                "prioritized regardless of estimated business value."
            )
            priority_out = None
        elif priority is None:
            status = "validate_first"
            explanation = (
                "Insufficient scored criteria to produce a reproducible priority. "
                "Collect baseline evidence before ranking."
            )
        elif priority >= 70 and confidence in {"high", "medium"}:
            status = "prioritize"
            explanation = (
                f"Weighted priority {priority}/100 with {confidence} confidence across "
                f"{len(CRITERION_KEYS)} rubric criteria ({PRIORITIZATION_RUBRIC_VERSION})."
            )
        elif priority >= 45:
            status = "validate_first"
            explanation = (
                f"Moderate priority {priority}/100. Validate missing assumptions and "
                "feasibility before committing investment."
            )
        else:
            status = "defer"
            explanation = (
                f"Low priority {priority}/100 relative to rubric weights. Defer until "
                "readiness, evidence, or value drivers improve."
            )

        return OpportunityPriorityResult(
            rubric_version=PRIORITIZATION_RUBRIC_VERSION,
            criterion_scores=results,
            criterion_weights=norm_weights,
            weighted_priority_score=priority_out if is_blocked else priority,
            ranking=None,
            ranking_explanation=explanation,
            evidence_refs=evidence_refs,
            missing_information=sorted(set(missing)),
            confidence_class=confidence if not is_blocked else "insufficient",
            recommendation_status=status,
            hard_blockers=blockers,
            is_blocked=is_blocked,
        )

    @classmethod
    def rank_opportunities(
        cls,
        opportunities: list[dict[str, Any]],
        assessment_context: dict[str, Any] | None = None,
        weights: dict[str, float] | None = None,
    ) -> list[OpportunityPriorityResult]:
        scored: list[tuple[int, OpportunityPriorityResult]] = []
        for idx, opp in enumerate(opportunities):
            scored.append(
                (
                    idx,
                    cls.score_opportunity(opp, assessment_context, weights=weights),
                )
            )

        def sort_key(item: tuple[int, OpportunityPriorityResult]) -> tuple:
            _i, result = item
            if result.is_blocked or result.weighted_priority_score is None:
                return (1, 0.0, _i)
            return (0, -float(result.weighted_priority_score), _i)

        ordered = sorted(scored, key=sort_key)
        rank = 1
        for _orig_idx, result in ordered:
            if result.is_blocked or result.weighted_priority_score is None:
                result.ranking = None
            else:
                result.ranking = rank
                result.ranking_explanation = (
                    f"Rank #{rank}: {result.ranking_explanation}"
                )
                rank += 1

        # Preserve input order in the returned list.
        by_orig = {orig_idx: result for orig_idx, result in ordered}
        return [by_orig[i] for i in range(len(opportunities))]

    @classmethod
    def _derive_criterion_inputs(
        cls,
        opportunity: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, tuple[float, str, list[str], list[str]]]:
        refs = list(opportunity.get("evidence_refs") or [])
        explicit = opportunity.get("criterion_scores") or {}

        def from_explicit_or_qual(
            key: str,
            qual_key: str,
            *,
            high_is_good: bool,
            fallback: float | None = None,
            fallback_basis: str = "assessment_context",
        ) -> tuple[float, str, list[str], list[str]]:
            if key in explicit and explicit[key] is not None:
                return _clamp(float(explicit[key])), "provided_numeric", [], refs
            if opportunity.get(qual_key) is not None:
                score, basis, missing = _qual_to_score(
                    opportunity.get(qual_key), high_is_good=high_is_good
                )
                return score, basis, missing, refs
            if fallback is not None:
                return _clamp(fallback), fallback_basis, [], refs
            score, basis, missing = _qual_to_score(None, high_is_good=high_is_good)
            return score, basis, missing, refs

        complexity = opportunity.get("complexity") or opportunity.get(
            "integration_complexity"
        )

        data_rd = ctx.get("data_readiness")
        process_rd = ctx.get("process_readiness")
        integration_rd = ctx.get("integration_readiness")
        governance_rd = ctx.get("governance_readiness")
        security_rd = ctx.get("security_readiness")
        team_rd = ctx.get("team_readiness")
        alignment = ctx.get("business_alignment")

        tech_fallback = None
        if integration_rd is not None and data_rd is not None:
            tech_fallback = (float(integration_rd) + float(data_rd)) / 2.0

        gov_sec_fallback = None
        if governance_rd is not None and security_rd is not None:
            # Higher readiness => lower residual risk score contribution already high-is-good.
            gov_sec_fallback = (float(governance_rd) + float(security_rd)) / 2.0

        evidence_score = 0.0
        evidence_basis = "unknown"
        evidence_missing = ["No validated evidence references for this opportunity"]
        if refs:
            evidence_score = min(100.0, 40.0 + 15.0 * len(refs))
            evidence_basis = "evidence_refs_count"
            evidence_missing = []
        if opportunity.get("evidence"):
            evidence_score = max(evidence_score, 55.0)
            evidence_basis = "narrative_evidence"
            evidence_missing = []

        # Explicit evidence_sufficiency numeric wins.
        if (
            "evidence_sufficiency" in explicit
            and explicit["evidence_sufficiency"] is not None
        ):
            evidence_score = _clamp(float(explicit["evidence_sufficiency"]))
            evidence_basis = "provided_numeric"
            evidence_missing = []

        return {
            "expected_business_value": from_explicit_or_qual(
                "expected_business_value",
                "value",
                high_is_good=True,
                fallback=float(alignment) if alignment is not None else None,
            ),
            "technical_feasibility": from_explicit_or_qual(
                "technical_feasibility",
                "technical_feasibility",
                high_is_good=True,
                fallback=tech_fallback,
            ),
            "data_readiness": from_explicit_or_qual(
                "data_readiness",
                "data_readiness",
                high_is_good=True,
                fallback=float(data_rd) if data_rd is not None else None,
            ),
            "process_readiness": from_explicit_or_qual(
                "process_readiness",
                "process_readiness",
                high_is_good=True,
                fallback=float(process_rd) if process_rd is not None else None,
            ),
            "integration_complexity": from_explicit_or_qual(
                "integration_complexity",
                "complexity",
                high_is_good=False,  # high complexity => low score
                fallback=(100.0 - float(complexity))
                if isinstance(complexity, (int, float))
                else (
                    _qual_to_score(complexity, high_is_good=False)[0]
                    if complexity
                    else (float(integration_rd) if integration_rd is not None else None)
                ),
            ),
            "governance_security_risk": from_explicit_or_qual(
                "governance_security_risk",
                "risk",
                high_is_good=False,
                fallback=gov_sec_fallback,
            ),
            "implementation_effort": from_explicit_or_qual(
                "implementation_effort",
                "implementation_effort",
                high_is_good=False,
                fallback=_qual_to_score(complexity, high_is_good=False)[0]
                if complexity
                else None,
            ),
            "time_to_value": from_explicit_or_qual(
                "time_to_value",
                "time_to_value",
                high_is_good=True,
                fallback=None,
            ),
            "organizational_change_readiness": from_explicit_or_qual(
                "organizational_change_readiness",
                "organizational_change_readiness",
                high_is_good=True,
                fallback=float(team_rd) if team_rd is not None else None,
            ),
            "evidence_sufficiency": (
                evidence_score,
                evidence_basis,
                evidence_missing,
                refs,
            ),
        }
