from __future__ import annotations

import threading
import time

from PySide6.QtCore import QCoreApplication

import app.controllers.app_controller as controller_module
from app.controllers.app_controller import AppController
from app.models.commands import DownloadIntent
from app.models.state import DownloadJob, VideoItem


class _FakeStorage:
    def load(self):
        return {}

    def save(self, data):
        return None


class _FakeSourceService:
    pass


class _FakeAgent:
    def __init__(self, model=None):
        self.model = model or "test-model"
        self.api_keys = []


class _FakeQueue:
    def __init__(self, max_workers, on_event):
        self.max_workers = max_workers
        self.on_event = on_event

    def set_max_workers(self, max_workers):
        self.max_workers = max_workers
        return True


def test_queue_worker_callback_updates_state_only_on_qt_main_thread(monkeypatch, tmp_path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(controller_module, "JsonStorage", _FakeStorage)
    monkeypatch.setattr(controller_module, "SourceService", _FakeSourceService)
    monkeypatch.setattr(controller_module, "GeminiLanguageAgent", _FakeAgent)
    monkeypatch.setattr(controller_module, "QueueManager", _FakeQueue)
    monkeypatch.setattr(controller_module, "default_download_dir", lambda: tmp_path)

    controller = AppController()
    main_thread_id = threading.get_ident()
    delivered_on: list[int] = []
    controller.job_changed.connect(lambda _job: delivered_on.append(threading.get_ident()))

    video = VideoItem(id="abc123", title="Test", url="https://www.youtube.com/watch?v=abc123")
    intent = DownloadIntent(output_folder=str(tmp_path))
    job = DownloadJob(job_id="job-1", video=video, intent=intent)

    worker = threading.Thread(target=lambda: controller.queue.on_event(job), name="test-worker")
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()

    # QueuedConnection harus mencegah worker menyentuh AppState secara langsung.
    assert controller.state.jobs == []
    assert delivered_on == []

    deadline = time.monotonic() + 2
    while not controller.state.jobs and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)

    assert [j.job_id for j in controller.state.jobs] == ["job-1"]
    assert delivered_on == [main_thread_id]

    controller._pool.shutdown(wait=False, cancel_futures=True)
