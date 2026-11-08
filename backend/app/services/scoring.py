"""Versioned, deterministic AI readiness scoring rubric."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

SCORING_RUBRIC_VERSION = "v1.0.0"

# Configurable rule weights — overall is always recomputed from these.
DIMENSION_WEIGHTS: dict[str, float] = {
    "data_readiness": 0.20,
    "process_readiness": 0.15,
    "integration_readiness": 0.15,
    "governance_readiness": 0.15,
    "security_readiness": 0.15,
    "team_readiness": 0.10,
    "business_alignment": 0.10,
}

DIMENSION_KEYS = tuple(DIMENSION_WEIGHTS.keys())


@dataclass
class DimensionScore:
    dimension: str
    score: float
    justification: str
    evidence_refs: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    reviewer_status: str = "pending"  # pending | reviewed | approved
    estimate_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scorecard:
    rubric_version: str
    scoring_method: str
    dimensions: dict[str, DimensionScore]
    overall_score: float
    automation_potential: float
    automation_potential_basis: str
    readiness_interpretation: str
    insufficient_evidence: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "rubric_version": self.rubric_version,
            "scoring_method": self.scoring_method,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "overall_score": self.overall_score,
            "automation_potential": self.automation_potential,
            "automation_potential_basis": self.automation_potential_basis,
            "readiness_interpretation": self.readiness_interpretation,
            "insufficient_evidence": self.insufficient_evidence,
        }

    def flat_assessment_fields(self) -> dict[str, Any]:
        """Dashboard-compatible flat fields."""
        out: dict[str, Any] = {
            "overall_score": self.overall_score,
            "automation_potential": self.automation_potential,
            "readiness_interpretation": self.readiness_interpretation,
            "scoring_rubric_version": self.rubric_version,
            "scoring_method": self.scoring_method,
            "dimension_score_details": {
                k: v.to_dict() for k, v in self.dimensions.items()
            },
        }
        justification_map = {
            "data_readiness": "data_justification",
            "process_readiness": "process_justification",
            "integration_readiness": "integration_justification",
            "governance_readiness": "governance_justification",
            "security_readiness": "security_justification",
            "team_readiness": "team_justification",
            "business_alignment": "alignment_justification",
        }
        for key, dim in self.dimensions.items():
            out[key] = dim.score
            out[justification_map[key]] = dim.justification
        return out


class ScoringEngine:
    """Rule-based readiness scoring grounded in intake + evidence package."""

    @staticmethod
    def weighted_overall(dimension_scores: dict[str, float]) -> float:
        total = 0.0
        for key, weight in DIMENSION_WEIGHTS.items():
            value = float(dimension_scores.get(key, 0.0))
            value = max(0.0, min(100.0, value))
            total += value * weight
        return round(total, 1)

    @classmethod
    def score(
        cls,
        *,
        company_name: str,
        industry: str,
        departments: Sequence[str],
        current_tools: Sequence[str],
        pain_points: Sequence[str],
        ai_goals: Sequence[str],
        compliance_requirements: Sequence[str],
        cloud_preference: str,
        main_business_goals: str,
        evidence_package: dict[str, Any] | None = None,
        bottlenecks: Sequence[dict[str, Any]] | None = None,
        use_cases: Sequence[dict[str, Any]] | None = None,
    ) -> Scorecard:
        evidence_package = evidence_package or {}
        evidence_items = evidence_package.get("evidence_items") or []
        insufficient = bool(evidence_package.get("insufficient_evidence"))

        def refs_for(*dims: str) -> list[str]:
            """Only cite evidence explicitly related to the requested dimensions."""
            found: list[str] = []
            for item in evidence_items:
                related = [
                    str(d).lower() for d in (item.get("related_dimensions") or [])
                ]
                if not any(d.lower() in related for d in dims):
                    continue
                eid = item.get("evidence_id")
                if eid and eid not in found:
                    found.append(str(eid))
            return found[:6]

        tools_l = [t.lower() for t in current_tools]
        pains_l = [p.lower() for p in pain_points]
        goals_l = [g.lower() for g in ai_goals]
        compliance_l = [c.lower() for c in compliance_requirements]

        # document_observed cues are weaker than verified operational proof.
        observed = [
            e
            for e in evidence_items
            if e.get("evidence_tier") in {"document_observed", "verified"}
        ]
        verified_types = " ".join(
            f"{e.get('signal_type', '')} {e.get('description', '')}".lower()
            for e in observed
        )

        # --- Data ---
        data_score = 58.0
        data_missing: list[str] = []
        data_flags: list[str] = []
        if any(
            "excel" in t or "spreadsheet" in t for t in tools_l
        ) or "data silos" in " ".join(pains_l):
            data_score -= 12
        if any(
            k in verified_types for k in ("data source", "database", "warehouse", "crm")
        ):
            data_score += 4  # cue-only uplift
        else:
            data_missing.append(
                "No document-observed cues for structured/accessible data assets."
            )
            data_score -= 8
        if insufficient:
            data_score -= 6
            data_flags.append("insufficient_document_evidence")
        data_score = max(15.0, min(90.0, data_score))

        # --- Process ---
        process_score = 55.0
        process_missing: list[str] = []
        if any("manual" in p for p in pains_l):
            process_score -= 8
        if any(
            k in verified_types for k in ("workflow", "process", "sop", "bottleneck")
        ):
            process_score += 5  # cue-only uplift
        else:
            process_missing.append("No document-observed process/SOP cues uploaded.")
            process_score -= 7
        if bottlenecks:
            process_score += min(6.0, 2.0 * len(list(bottlenecks)))
        process_score = max(15.0, min(90.0, process_score))

        # --- Integration ---
        integration_score = 52.0
        integration_missing: list[str] = []
        modern = any(
            t in " ".join(tools_l)
            for t in ("salesforce", "jira", "sharepoint", "aws", "azure", "gcp", "api")
        )
        if modern:
            integration_score += 8
        if "integration" in verified_types or "api" in verified_types:
            integration_score += 4
        else:
            integration_missing.append(
                "No document-observed integration/API maturity cues."
            )
            integration_score -= 6
        if cloud_preference and "agnostic" not in cloud_preference.lower():
            integration_score += 4
        integration_score = max(15.0, min(90.0, integration_score))

        # --- Governance ---
        governance_score = 50.0
        governance_missing: list[str] = []
        if compliance_l:
            governance_score += min(12.0, 4.0 * len(compliance_l))
        if any(
            k in verified_types for k in ("governance", "audit", "policy", "compliance")
        ):
            governance_score += 4  # cue-only; not proof controls operate
            governance_missing.append(
                "Governance language observed in documents is not proof controls are operational."
            )
        else:
            governance_missing.append(
                "No document-observed AI/data governance control cues."
            )
            governance_score -= 5
        if compliance_l and "governance" not in verified_types:
            governance_score -= 4
            governance_missing.append(
                "Compliance requirements asserted without documented AI control evidence."
            )
        governance_score = max(15.0, min(92.0, governance_score))

        # --- Security ---
        security_score = 55.0
        security_missing: list[str] = []
        if any(
            k in " ".join(compliance_l)
            for k in ("soc2", "soc 2", "hipaa", "iso", "gdpr")
        ):
            security_score += 10
        if any(
            k in verified_types
            for k in ("security", "access control", "encryption", "pii")
        ):
            security_score += 4  # cue-only
            security_missing.append(
                "Security language observed is not proof controls are enforced."
            )
        else:
            security_missing.append(
                "No document-observed security-control cues in documents."
            )
            security_score -= 5
        security_score = max(20.0, min(93.0, security_score))

        # --- Team ---
        team_score = 48.0
        team_missing: list[str] = []
        if any(k in " ".join(goals_l) for k in ("upskill", "training", "enablement")):
            team_score += 10
        if "team" in verified_types or "training" in verified_types:
            team_score += 4  # cue-only
        else:
            team_missing.append(
                "No document-observed cues for AI talent or change ownership."
            )
            team_score -= 6
        if departments:
            team_score += min(6.0, 1.5 * len(list(departments)))
        team_score = max(15.0, min(88.0, team_score))

        # --- Business alignment ---
        alignment_score = 60.0
        alignment_missing: list[str] = []
        if main_business_goals.strip():
            alignment_score += 8
        else:
            alignment_missing.append("Main business goals not provided.")
            alignment_score -= 8
        if ai_goals:
            alignment_score += min(10.0, 3.0 * len(list(ai_goals)))
        if use_cases:
            alignment_score += min(6.0, 2.0 * len(list(use_cases)))
        if insufficient and not main_business_goals.strip():
            alignment_score -= 8
        alignment_score = max(20.0, min(92.0, alignment_score))

        dims = {
            "data_readiness": DimensionScore(
                dimension="data_readiness",
                score=round(data_score, 1),
                justification=(
                    f"Scored from tools ({', '.join(list(current_tools)[:3]) or 'unspecified'}), "
                    f"pain points, and {len(observed)} document-observed cues "
                    "(not operational proof)."
                ),
                evidence_refs=refs_for("data"),
                missing_information=data_missing,
                estimate_flags=data_flags,
            ),
            "process_readiness": DimensionScore(
                dimension="process_readiness",
                score=round(process_score, 1),
                justification=(
                    "Process score reflects documented workflow cues and reported manual pain points; "
                    "standardization remains limited without SOP coverage."
                    if process_missing
                    else "Process score reflects document-observed workflow/SOP cues alongside reported bottlenecks."
                ),
                evidence_refs=refs_for("process", "bottleneck"),
                missing_information=process_missing,
            ),
            "integration_readiness": DimensionScore(
                dimension="integration_readiness",
                score=round(integration_score, 1),
                justification=(
                    f"Integration readiness considers stack signals ({', '.join(list(current_tools)[:3]) or 'n/a'}) "
                    f"and cloud preference '{cloud_preference or 'unspecified'}'."
                ),
                evidence_refs=refs_for("integration"),
                missing_information=integration_missing,
            ),
            "governance_readiness": DimensionScore(
                dimension="governance_readiness",
                score=round(governance_score, 1),
                justification=(
                    f"Governance score balances asserted requirements "
                    f"({', '.join(list(compliance_requirements)[:3]) or 'none stated'}) "
                    "against document-observed policy/control cues (not operational proof)."
                ),
                evidence_refs=refs_for("governance"),
                missing_information=governance_missing,
            ),
            "security_readiness": DimensionScore(
                dimension="security_readiness",
                score=round(security_score, 1),
                justification=(
                    "Security posture estimated from compliance assertions and document-observed control language; "
                    "AI-specific handling controls still require reviewer confirmation."
                ),
                evidence_refs=refs_for("security"),
                missing_information=security_missing,
                estimate_flags=["security_controls_partially_estimated"],
            ),
            "team_readiness": DimensionScore(
                dimension="team_readiness",
                score=round(team_score, 1),
                justification=(
                    "Team readiness reflects department coverage and whether training/ownership evidence exists."
                ),
                evidence_refs=refs_for("team"),
                missing_information=team_missing,
            ),
            "business_alignment": DimensionScore(
                dimension="business_alignment",
                score=round(alignment_score, 1),
                justification=(
                    f"Alignment reflects stated goals for {company_name} in {industry or 'unspecified industry'} "
                    f"and {len(list(ai_goals))} AI goal selections."
                ),
                evidence_refs=refs_for("business"),
                missing_information=alignment_missing,
            ),
        }

        if insufficient:
            for dim in dims.values():
                dim.score = round(max(10.0, dim.score - 8.0), 1)
                if "Insufficient document evidence" not in dim.missing_information:
                    dim.missing_information.append(
                        "Insufficient document evidence for a firm conclusion."
                    )
                dim.estimate_flags.append("insufficient_evidence_penalty")

        overall = cls.weighted_overall({k: v.score for k, v in dims.items()})

        # Automation potential is an estimate unless measured metrics exist.
        auto = 22.0
        auto_basis = "estimate_from_pain_points_and_bottlenecks_not_measured"
        if any("manual" in p for p in pains_l):
            auto += 8
        if bottlenecks:
            auto += min(16.0, 5.0 * len(list(bottlenecks)))
        if use_cases:
            auto += min(12.0, 3.0 * len(list(use_cases)))
        if insufficient:
            auto = min(auto, 25.0)
            auto_basis = "estimate_capped_due_to_insufficient_evidence"
        auto = round(max(5.0, min(70.0, auto)), 1)

        if insufficient:
            interpretation = (
                f"Insufficient verified document evidence for {company_name}. "
                "Dimension scores are provisional and should not be treated as calibrated certainty. "
                "Collect process, data, and governance artifacts before locking a pilot recommendation."
            )
        else:
            top = max(dims.values(), key=lambda d: d.score)
            bottom = min(dims.values(), key=lambda d: d.score)
            interpretation = (
                f"Overall readiness is {overall}/100 under rubric {SCORING_RUBRIC_VERSION}. "
                f"Strongest dimension: {top.dimension.replace('_', ' ')} ({top.score}). "
                f"Largest gap: {bottom.dimension.replace('_', ' ')} ({bottom.score}). "
                "Use a scoped pilot with human review while closing missing evidence items."
            )

        return Scorecard(
            rubric_version=SCORING_RUBRIC_VERSION,
            scoring_method="deterministic_rubric_v1",
            dimensions=dims,
            overall_score=overall,
            automation_potential=auto,
            automation_potential_basis=auto_basis,
            readiness_interpretation=interpretation,
            insufficient_evidence=insufficient,
        )

    @classmethod
    def recompute_overall_from_assessment_fields(
        cls, fields: dict[str, float]
    ) -> float:
        return cls.weighted_overall(
            {k: float(fields.get(k, 0.0)) for k in DIMENSION_KEYS}
        )
