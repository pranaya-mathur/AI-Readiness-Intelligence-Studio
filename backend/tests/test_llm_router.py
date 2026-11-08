import json

import pytest

from app.core import config as config_module
from app.services import llm_router as router_module
from app.services.llm_router import LLMExecutionError, LLMRouter


@pytest.fixture(autouse=True)
def _reset_router(monkeypatch):
    LLMRouter.reset_session()
    yield
    LLMRouter.reset_session()


def test_real_mode_fails_closed_when_no_provider(monkeypatch):
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_HEURISTIC_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "USE_OLLAMA", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_OLLAMA_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_EXTERNAL_MODEL_PROVIDERS", True)
    monkeypatch.setattr(config_module.settings, "LLM_MAX_RETRIES", 1)

    with pytest.raises(LLMExecutionError):
        LLMRouter.generate_completion(
            "Company Name: Acme\nGoals: efficiency", require_json=False
        )


def test_demo_mode_returns_marked_simulation(monkeypatch):
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", True)
    monkeypatch.setattr(config_module.settings, "ALLOW_HEURISTIC_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "USE_OLLAMA", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_OLLAMA_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "LLM_MAX_RETRIES", 1)

    result = LLMRouter.generate_completion_tracked(
        "Company Name: Acme\nIdentify bottlenecks\nPain Points: Manual Process Overload\nDepartments: Operations",
        require_json=True,
    )
    assert result.status == "demo_simulated"
    assert result.execution_mode == "demo"
    payload = json.loads(result.content)
    assert payload.get("analysis_mode") == "demo"
    blob = json.dumps(payload)
    assert "DEMO_SIMULATED" in blob or "demo" in blob.lower()


def test_malformed_json_retries_then_fails_in_real_mode(monkeypatch):
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_HEURISTIC_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(config_module.settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "USE_OLLAMA", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_OLLAMA_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_EXTERNAL_MODEL_PROVIDERS", True)
    monkeypatch.setattr(config_module.settings, "LLM_MAX_RETRIES", 2)
    monkeypatch.setattr(config_module.settings, "OPENAI_MODEL", "gpt-test")

    class FakeResp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(
        router_module.requests,
        "post",
        lambda *args, **kwargs: FakeResp(),
    )

    with pytest.raises(LLMExecutionError):
        LLMRouter.generate_completion("Return JSON for bottlenecks", require_json=True)


def test_timeout_marked_failed(monkeypatch):
    monkeypatch.setattr(config_module.settings, "DEMO_MODE", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_HEURISTIC_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(config_module.settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(config_module.settings, "USE_OLLAMA", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_OLLAMA_FALLBACK", False)
    monkeypatch.setattr(config_module.settings, "ALLOW_EXTERNAL_MODEL_PROVIDERS", True)
    monkeypatch.setattr(config_module.settings, "LLM_MAX_RETRIES", 1)

    def _raise(*args, **kwargs):
        raise router_module.requests.Timeout("timed out")

    monkeypatch.setattr(router_module.requests, "post", _raise)

    with pytest.raises(LLMExecutionError):
        LLMRouter.generate_completion("hello", require_json=False)
    summary = LLMRouter.session_summary()
    assert summary["status"] in {"failed", "not_started"} or summary["error"]
