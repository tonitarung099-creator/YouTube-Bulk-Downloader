from __future__ import annotations

from types import SimpleNamespace

import app.ai.gemini_agent as agent_module
from app.ai.gemini_agent import GeminiLanguageAgent
from app.core.source_service import SourceService


def test_capability_question_uses_chat_mode_without_mutating_into_action() -> None:
    agent = GeminiLanguageAgent(api_keys=[])
    result = agent.interpret("kamu bisa melakukan apa saja?")
    assert result.kind == "chat"
    assert result.intent.action == "unknown"
    assert result.reply_text
    assert "tanya-jawab" in result.reply_text


def test_general_mp3_question_is_chat_not_download_command() -> None:
    agent = GeminiLanguageAgent(api_keys=[])
    result = agent.interpret("Apa itu MP3 dan apa bedanya dengan M4A?")
    assert result.kind == "chat"
    assert result.intent.action == "unknown"


def test_chat_question_uses_gemini_when_api_key_exists(monkeypatch) -> None:
    calls = []

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            calls.append((model, contents, config))
            return SimpleNamespace(text="Saya bisa menjawab pertanyaan dan menjalankan aksi aplikasi.")

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.models = FakeModels()

    monkeypatch.setattr(agent_module.genai, "Client", FakeClient)
    monkeypatch.setattr(agent_module.types, "GenerateContentConfig", lambda **kwargs: kwargs)

    agent = GeminiLanguageAgent(api_keys=["test-key"])
    result = agent.interpret("kamu bisa melakukan apa saja?")

    assert result.kind == "chat"
    assert result.provider == "gemini"
    assert result.reply_text.startswith("Saya bisa")
    assert calls
    assert "system_instruction" in calls[0][2]
    assert "response_schema" not in calls[0][2]
    assert "Konteks aplikasi" in calls[0][1]


def test_search_and_download_command_builds_safe_local_plan() -> None:
    agent = GeminiLanguageAgent(api_keys=[])
    result = agent.interpret("carikan semua lagu Iwan Fals dan download semua sebagai mp3")
    assert result.kind == "action"
    assert result.intent.action == "search"
    assert result.intent.source_type == "search"
    assert result.intent.search_query == "lagu iwan fals"
    assert result.intent.search_limit == 100
    assert result.intent.download_after_search is True
    assert result.intent.mode == "audio"
    assert result.intent.audio_format == "mp3"


def test_named_download_without_url_becomes_search_then_download() -> None:
    agent = GeminiLanguageAgent(api_keys=[])
    result = agent.interpret("download semua lagu Iwan Fals sebagai mp3")
    assert result.intent.action == "search"
    assert result.intent.search_query == "lagu iwan fals"
    assert result.intent.download_after_search is True
    assert result.intent.mode == "audio"
    assert result.intent.audio_format == "mp3"


def test_source_service_search_exposes_results() -> None:
    class FakeDownloader:
        def search(self, query, limit):
            assert query == "Iwan Fals"
            assert limit == 25
            return {
                "title": "Hasil pencarian: Iwan Fals",
                "webpage_url": "https://www.youtube.com/results?search_query=Iwan+Fals",
                "type": "search",
                "entries": [
                    {"id": "abc", "title": "Iwan Fals - Contoh", "url": "https://www.youtube.com/watch?v=abc", "is_short": False, "is_live": False}
                ],
            }

    source = SourceService(FakeDownloader()).search("Iwan Fals", 25)
    assert source.source_type == "search"
    assert source.total_detected == 1
    assert source.items[0].id == "abc"
