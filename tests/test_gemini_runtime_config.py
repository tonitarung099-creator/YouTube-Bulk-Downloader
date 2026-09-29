from __future__ import annotations

from types import SimpleNamespace

import app.ai.gemini_agent as agent_module
from app.ai.gemini_agent import GeminiLanguageAgent
from app.gui.widgets.gemini_settings import GeminiSettings


def test_api_input_accepts_lines_commas_semicolons_and_caps_at_100() -> None:
    text = "key-a\nkey-b,key-c;key-a\n" + "\n".join(f"key-{i}" for i in range(200))
    keys = GeminiSettings._normalize(text)
    assert keys[:3] == ["key-a", "key-b", "key-c"]
    assert len(keys) == 100
    assert len(set(keys)) == 100


def test_agent_keys_can_be_replaced_at_runtime() -> None:
    agent = GeminiLanguageAgent(api_keys=["old-key"])
    agent.set_api_keys(["new-a", "new-b", "new-a"])
    assert agent.api_keys == ["new-a", "new-b"]
    assert agent._cursor == 0


def test_connection_reports_working_fallback_model(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class FakeModels:
        def __init__(self, key: str):
            self.key = key

        def generate_content(self, *, model, contents, config):
            calls.append((self.key, model))
            if model == "gemini-3.5-flash-lite":
                raise RuntimeError("404 model not found")
            return SimpleNamespace(text="OK")

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels(api_key)

    monkeypatch.setattr(agent_module.genai, "Client", FakeClient)
    monkeypatch.setattr(agent_module.types, "GenerateContentConfig", lambda **kwargs: kwargs)

    agent = GeminiLanguageAgent(api_keys=["key-1"])
    model, key_index = agent.test_connection()

    assert model == "gemini-3.1-flash-lite"
    assert key_index == 0
    assert calls == [
        ("key-1", "gemini-3.5-flash-lite"),
        ("key-1", "gemini-3.1-flash-lite"),
    ]


def test_connection_without_key_has_clear_message() -> None:
    agent = GeminiLanguageAgent(api_keys=[])
    try:
        agent.test_connection()
    except RuntimeError as exc:
        assert "Belum ada API key Gemini" in str(exc)
    else:
        raise AssertionError("test_connection seharusnya gagal bila API key kosong")
