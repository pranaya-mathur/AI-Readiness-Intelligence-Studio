"""Targeted tests for Phase 1 review-finding remediation."""

from __future__ import annotations

import concurrent.futures

from app.services.evidence import EvidenceExtractor
from app.services.evidence_links import (
    enrich_finding_with_validated_refs,
    index_assessment_evidence,
    validate_evidence_refs,
)
from app.services.llm_router import LLMRouter
from app.services.scoring import ScoringEngine


def test_evidence_refs_are_dimension_specific():
    package = {
        "insufficient_evidence": False,
        "missing_evidence": [],
        "evidence_items": [
            {
                "evidence_id": "ev_data",
                "related_dimensions": ["data"],
                "evidence_tier": "document_observed",
                "signal_type": "Data Source",
                "description": "excel warehouse",
            },
            {
                "evidence_id": "ev_gov",
                "related_dimensions": ["governance"],
                "evidence_tier": "document_observed",
                "signal_type": "Governance Control",
                "description": "gdpr policy",
            },
        ],
    }
    scorecard = ScoringEngine.score(
        company_name="Acme",
        industry="Services",
        departments=["Operations"],
        current_tools=["Excel"],
        pain_points=["Data Silos"],
        ai_goals=["Efficiency"],
        compliance_requirements=["GDPR"],
        cloud_preference="Azure",
        main_business_goals="Reduce cycle time",
        evidence_package=package,
    )
    assert scorecard.dimensions["data_readiness"].evidence_refs == ["ev_data"]
    assert "ev_gov" not in scorecard.dimensions["data_readiness"].evidence_refs
    assert scorecard.dimensions["governance_readiness"].evidence_refs == ["ev_gov"]


def test_keyword_matches_are_document_observed_not_verified_controls():
    package = EvidenceExtractor.build_package(
        [
            {
                "filename": "policy.txt",
                "text": "Our GDPR audit policy requires access control and MFA for PII.",
                "pages": [
                    {
                        "page": 1,
                        "text": "Our GDPR audit policy requires access control and MFA for PII.",
                    }
                ],
            }
        ]
    )
    assert any(i.evidence_tier == "document_observed" for i in package.evidence_items)
    assert all(i.evidence_tier != "verified" for i in package.evidence_items)
    assert package.truncation_report.get("documents_analyzed") == 1
    assert any(i.page_or_section == "page 1" for i in package.evidence_items)


def test_truncation_report_is_accurate_for_oversized_multi_doc():
    docs = [
        {"filename": f"doc_{i}.txt", "text": ("workflow process " * 2000) + str(i)}
        for i in range(15)
    ]
    package = EvidenceExtractor.build_package(docs)
    report = package.truncation_report
    assert package.truncation_applied is True
    assert report["documents_considered"] == 15
    assert report["documents_analyzed"] <= 12
    assert report["documents_omitted"] >= 3
    assert report["total_chars_analyzed"] <= 48_000


def test_evidence_ref_validation_requires_assessment_membership_and_source_match():
    index = index_assessment_evidence(
        [
            {
                "evidence_id": "ev1",
                "source_file": "a.txt",
                "evidence_tier": "document_observed",
            },
            {
                "evidence_id": "ev2",
                "source_file": "b.txt",
                "evidence_tier": "document_observed",
            },
        ]
    )
    assert validate_evidence_refs(
        evidence_refs=["ev1", "ev_missing", "ev2"],
        evidence_index=index,
        claimed_source_file="a.txt",
    ) == ["ev1"]
    finding = enrich_finding_with_validated_refs(
        {"evidence_refs": ["ev2", "ev_missing"], "source_file": "b.txt"},
        index,
    )
    assert finding["evidence_refs"] == ["ev2"]


def test_llm_router_sessions_are_isolated_across_threads(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.DEMO_MODE", True)
    monkeypatch.setattr("app.core.config.settings.ALLOW_HEURISTIC_FALLBACK", False)
    monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.core.config.settings.GROQ_API_KEY", "")
    monkeypatch.setattr("app.core.config.settings.USE_OLLAMA", False)
    monkeypatch.setattr("app.core.config.settings.ALLOW_OLLAMA_FALLBACK", False)
    monkeypatch.setattr("app.core.config.settings.LLM_MAX_RETRIES", 1)

    def worker(label: str) -> str:
        LLMRouter.reset_session()
        result = LLMRouter.generate_completion_tracked(
            f"Company Name: {label}\nIdentify bottlenecks\nPain Points: Manual Process Overload\nDepartments: Operations",
            require_json=True,
        )
        summary = LLMRouter.session_summary()
        assert summary["status"] == "demo_simulated"
        # Ensure this worker only sees its own session runs.
        assert all(
            r.get("provider") == "demo_simulator" for r in (summary.get("runs") or [])
        )
        return result.status

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(worker, [f"Client-{i}" for i in range(8)]))
    assert statuses == ["demo_simulated"] * 8
