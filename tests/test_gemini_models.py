from __future__ import annotations

from types import SimpleNamespace

import app.ai.gemini_agent as agent_module
from app.ai.gemini_agent import GEMINI_MODELS, GeminiLanguageAgent


EXPECTED_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
)


def test_default_models_are_exactly_requested_flash_lite_set(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    agent = GeminiLanguageAgent(api_keys=[])
    assert GEMINI_MODELS == EXPECTED_MODELS
    assert agent.models == EXPECTED_MODELS
    assert agent.model == "gemini-3.5-flash-lite"


def test_unknown_or_legacy_model_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    agent = GeminiLanguageAgent(api_keys=[])
    assert agent.models == EXPECTED_MODELS
    assert "gemini-3.8-flash" not in agent.models


def test_allowed_model_override_stays_inside_flash_lite_set(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    agent = GeminiLanguageAgent(api_keys=[])
    assert agent.models[0] == "gemini-3.1-flash-lite"
    assert set(agent.models) == set(EXPECTED_MODELS)


def test_agent_falls_back_to_next_flash_lite_model(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    calls: list[str] = []

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            calls.append(model)
            if model == "gemini-3.5-flash-lite":
                raise RuntimeError("404 model not found")
            return SimpleNamespace(text='{"action":"analyze","explanation":"ok"}')

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(agent_module.genai, "Client", FakeClient)
    monkeypatch.setattr(agent_module.types, "GenerateContentConfig", lambda **kwargs: kwargs)

    agent = GeminiLanguageAgent(api_keys=["test-key"])
    result = agent.interpret("cek video")

    assert calls == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    assert result.provider == "gemini"
    assert result.intent.action == "analyze"
    assert agent.last_model == "gemini-3.1-flash-lite"
