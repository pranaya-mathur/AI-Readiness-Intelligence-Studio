from types import SimpleNamespace

from app.api.assessment import (
    _assessment_is_client_exportable,
    _is_internal_demo_export,
)


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


def test_internal_demo_export_mode_detection():
    ass = SimpleNamespace(analysis_mode="demo")
    assert _is_internal_demo_export(ass, "demo") is True
    assert _is_internal_demo_export(ass, None) is False
    real = SimpleNamespace(analysis_mode="real")
    assert _is_internal_demo_export(real, "showcase") is False
