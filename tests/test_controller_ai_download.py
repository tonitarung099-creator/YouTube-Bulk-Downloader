from __future__ import annotations

import concurrent.futures

from PySide6.QtWidgets import QApplication

import app.controllers.app_controller as controller_module
from app.controllers.app_controller import AppController
from app.models.commands import AgentResult, DownloadIntentPatch
from app.models.state import DownloadJob, JobStatus, SourceInfo, VideoItem


class _Storage:
    def load(self):
        return {}

    def save(self, data):
        return None


class _SourceService:
    pass


class _Agent:
    def __init__(self, model=None):
        self.model = "gemini-3.5-flash-lite"
        self.api_keys = []
        self.last_error = None
        self.last_model = None


class _Queue:
    def __init__(self, max_workers, on_event):
        self.max_workers = max_workers
        self.on_event = on_event
        self.added: list[tuple[VideoItem, object]] = []

    def set_max_workers(self, value):
        self.max_workers = value
        return True

    def add(self, video, intent):
        self.added.append((video, intent))
        return DownloadJob(job_id=f"job-{len(self.added)}", video=video, intent=intent, status=JobStatus.QUEUED)

    def shutdown(self, wait=False):
        return None

    def pause(self):
        return None

    def resume(self):
        return None

    def cancel(self):
        return None


def _controller(monkeypatch, tmp_path) -> AppController:
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(controller_module, "JsonStorage", _Storage)
    monkeypatch.setattr(controller_module, "SourceService", _SourceService)
    monkeypatch.setattr(controller_module, "GeminiLanguageAgent", _Agent)
    monkeypatch.setattr(controller_module, "QueueManager", _Queue)
    monkeypatch.setattr(controller_module, "default_download_dir", lambda: tmp_path)
    return AppController()


def _download_result(controller: AppController, url: str) -> AgentResult:
    intent = controller.state.intent.model_copy(update={"action": "download", "url": url})
    patch = DownloadIntentPatch(action="download", url=url, explanation="Unduh sekarang")
    return AgentResult(intent=intent, patch=patch, provider="local_fallback")


def test_ai_download_queues_existing_analyzed_source(monkeypatch, tmp_path) -> None:
    controller = _controller(monkeypatch, tmp_path)
    url = "https://www.youtube.com/watch?v=abc123"
    video = VideoItem(id="abc123", title="Tes", url=url)
    controller.state.source = SourceInfo(id="abc123", title="Tes", url=url, source_type="video", items=[video])
    controller.state.active_url = url
    controller.state.selected_ids = {video.id}

    future: concurrent.futures.Future = concurrent.futures.Future()
    future.set_result(_download_result(controller, url))
    controller._finish_ai(future)

    assert len(controller.queue.added) == 1
    assert controller.queue.added[0][0].id == "abc123"
    controller.shutdown()


def test_ai_download_analyzes_first_when_source_missing(monkeypatch, tmp_path) -> None:
    controller = _controller(monkeypatch, tmp_path)
    url = "https://www.youtube.com/watch?v=xyz789"
    called: list[str] = []
    controller.analyze = lambda target: called.append(target)

    future: concurrent.futures.Future = concurrent.futures.Future()
    future.set_result(_download_result(controller, url))
    controller._finish_ai(future)

    assert controller._pending_ai_download is True
    assert called == [url]
    controller.shutdown()
