from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
import pytest

from app.api.assessment import (
    _assessment_is_client_exportable,
    _is_internal_demo_export,
    export_assessment_report,
)
from app.core import config as config_module


def test_incomplete_and_demo_not_client_exportable():
    incomplete = SimpleNamespace(
        status="incomplete",
        analysis_mode="real",
        model_run_status="failed",
        insufficient_evidence=0,
    )
    ok, reason = _assessment_is_client_exportable(incomplete)
    assert ok is False
    assert "incomplete" in reason

    demo = SimpleNamespace(
        status="completed",
        analysis_mode="demo",
        model_run_status="demo_simulated",
        insufficient_evidence=0,
    )
    ok, reason = _assessment_is_client_exportable(demo)
    assert ok is False
    assert "Demo" in reason or "demo" in reason.lower()


def test_completed_real_assessment_is_exportable():
    ass = SimpleNamespace(
        status="completed",
        analysis_mode="real",
        model_run_status="success",
        insufficient_evidence=0,
    )
    ok, reason = _assessment_is_client_exportable(ass)
    assert ok is True
    assert reason == ""


def test_internal_demo_export_requires_demo_assessment_and_env(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ENABLE_DEMO_WORKSPACE", True)
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)

    demo_ass = SimpleNamespace(
        analysis_mode="demo",
        model_run_status="demo_simulated",
    )
    assert _is_internal_demo_export(demo_ass, "demo") is True
    assert _is_internal_demo_export(demo_ass, None) is False
    assert _is_internal_demo_export(demo_ass, "showcase") is False

    # mode=demo alone must NOT unlock a real assessment
    real = SimpleNamespace(analysis_mode="real", model_run_status="success")
    assert _is_internal_demo_export(real, "demo") is False
    assert _is_internal_demo_export(real, "showcase") is False


def test_internal_demo_export_blocked_outside_demo_environment(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ENABLE_DEMO_WORKSPACE", False)
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)
    demo_ass = SimpleNamespace(
        analysis_mode="demo",
        model_run_status="demo_simulated",
    )
    assert _is_internal_demo_export(demo_ass, "demo") is False


def _mock_db_with_assessment(ass):
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.first.return_value = ass
    db.query.return_value = query
    return db


def test_export_endpoint_rejects_mode_demo_on_real_unapproved_assessment(monkeypatch):
    """Real assessments require approval even when ?mode=demo is supplied."""
    monkeypatch.setattr(config_module.settings, "ENABLE_DEMO_WORKSPACE", True)
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)

    real_ass = SimpleNamespace(
        id=42,
        user_id=1,
        company_name="Acme Corp",
        approval_status="draft",
        status="completed",
        analysis_mode="real",
        model_run_status="success",
        insufficient_evidence=0,
    )
    db = _mock_db_with_assessment(real_ass)
    user = SimpleNamespace(id=1)

    with pytest.raises(HTTPException) as exc:
        export_assessment_report(
            id=42, doc_format="pdf", mode="demo", db=db, current_user=user
        )
    assert exc.value.status_code == 409
    assert "approved" in str(exc.value.detail).lower()


def test_export_endpoint_allows_genuine_demo_bypass(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ENABLE_DEMO_WORKSPACE", True)
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)

    demo_ass = SimpleNamespace(
        id=7,
        user_id=1,
        company_name="Apex Global Consulting Partners",
        approval_status="draft",
        status="completed",
        analysis_mode="demo",
        model_run_status="demo_simulated",
        insufficient_evidence=0,
        overall_score=62,
        business_summary="Demo summary",
        client_summary="Demo client summary",
    )
    db = _mock_db_with_assessment(demo_ass)
    user = SimpleNamespace(id=1)
    fake_pdf = MagicMock()

    with (
        patch(
            "app.api.assessment._db_assessment_to_dict",
            return_value={
                "company_name": demo_ass.company_name,
                "client_summary": demo_ass.client_summary,
                "business_summary": demo_ass.business_summary,
            },
        ),
        patch(
            "app.api.assessment.DocumentGenerators.generate_pdf_report",
            return_value=fake_pdf,
        ) as gen_pdf,
        patch("app.api.assessment.StreamingResponse", return_value={"ok": True}) as stream,
    ):
        result = export_assessment_report(
            id=7, doc_format="pdf", mode="demo", db=db, current_user=user
        )

    assert result == {"ok": True}
    gen_pdf.assert_called_once()
    payload = gen_pdf.call_args.args[0]
    assert payload["export_mode"] == "demo"
    assert payload["company_name"].startswith("[DEMO]")
    stream.assert_called_once()


def test_export_endpoint_requires_approval_for_docx_pptx_on_real(monkeypatch):
    monkeypatch.setattr(config_module.settings, "ENABLE_DEMO_WORKSPACE", True)
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)

    real_ass = SimpleNamespace(
        id=99,
        user_id=1,
        company_name="Real Client Co",
        approval_status="reviewed",
        status="completed",
        analysis_mode="real",
        model_run_status="success",
        insufficient_evidence=0,
    )
    db = _mock_db_with_assessment(real_ass)
    user = SimpleNamespace(id=1)

    for fmt in ("docx", "pptx", "pdf"):
        with pytest.raises(HTTPException) as exc:
            export_assessment_report(
                id=99, doc_format=fmt, mode="demo", db=db, current_user=user
            )
        assert exc.value.status_code == 409
        assert "approved" in str(exc.value.detail).lower()
