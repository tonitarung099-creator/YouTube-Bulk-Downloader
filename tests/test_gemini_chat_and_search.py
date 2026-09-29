from __future__ import annotations

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


def test_search_and_download_command_builds_safe_local_plan() -> None:
    agent = GeminiLanguageAgent(api_keys=[])
    result = agent.interpret("carikan semua lagu Iwan Fals dan download semua sebagai mp3")
    assert result.kind == "action"
    assert result.intent.action == "search"
    assert result.intent.source_type == "search"
    assert "iwan fals" in (result.intent.search_query or "")
    assert result.intent.search_limit == 100
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
