from __future__ import annotations

import concurrent.futures
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal

from app.ai.gemini_agent import GeminiLanguageAgent
from app.core.paths import default_download_dir
from app.core.queue_manager import QueueManager
from app.core.source_service import SourceService
from app.core.storage import JsonStorage
from app.models.commands import DownloadIntent
from app.models.state import AppState, DownloadJob, JobStatus


class AppController(QObject):
    state_changed = Signal(object)
    source_loaded = Signal(object)
    analysis_failed = Signal(str)
    job_changed = Signal(object)
    ai_reply = Signal(str, object)
    ai_status = Signal(str)

    # Callback Future/queue berjalan dari thread worker. Semua perubahan state Qt
    # dimarshalkan melalui queued signal agar hanya terjadi di thread controller/UI.
    _analysis_done = Signal(int, object)
    _ai_done = Signal(object)
    _job_arrived = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._analysis_done.connect(self._finish_analysis, Qt.ConnectionType.QueuedConnection)
        self._ai_done.connect(self._finish_ai, Qt.ConnectionType.QueuedConnection)
        self._job_arrived.connect(self._apply_job, Qt.ConnectionType.QueuedConnection)

        self.storage = JsonStorage()
        saved = self.storage.load()
        self.state = AppState()
        if saved.get("intent"):
            try:
                self.state.intent = DownloadIntent.model_validate(saved["intent"])
            except Exception:
                pass
        if not self.state.intent.output_folder:
            self.state.intent.output_folder = str(default_download_dir())
        self.source_service = SourceService()
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="ui-work")
        self._analysis_seq = 0
        self.queue = QueueManager(self.state.intent.concurrent_downloads, self._job_arrived.emit)
        self.agent = GeminiLanguageAgent(model=saved.get("gemini_model") or None)

    def persist(self) -> None:
        self.storage.save({
            "intent": self.state.intent.model_dump(mode="json"),
            "gemini_model": self.agent.model,
        })

    def update_intent(self, **changes) -> None:
        self.state.intent = self.state.intent.model_copy(update=changes)
        if "concurrent_downloads" in changes:
            self.queue.set_max_workers(self.state.intent.concurrent_downloads)
        self.persist()
        self.state_changed.emit(self.state)

    def analyze(self, url: str) -> None:
        self._analysis_seq += 1
        seq = self._analysis_seq
        self.state.active_url = url.strip()
        self.state_changed.emit(self.state)
        fut = self._pool.submit(self.source_service.analyze, self.state.active_url)
        fut.add_done_callback(lambda f: self._analysis_done.emit(seq, f))

    def _finish_analysis(self, seq: int, fut: concurrent.futures.Future) -> None:
        if seq != self._analysis_seq:
            return
        try:
            source = fut.result()
        except Exception as exc:
            self.analysis_failed.emit(str(exc))
            return
        self.state.source = source
        self.state.selected_ids = {i.id for i in source.items}
        self.source_loaded.emit(source)
        self.state_changed.emit(self.state)

    def queue_selected(self, all_items: bool = False) -> int:
        if not self.state.source:
            return 0
        items = self.state.source.items if all_items else [i for i in self.state.source.items if i.id in self.state.selected_ids]
        eligible = [i for i in items if (self.state.intent.include_shorts or i.is_short is not True) and (self.state.intent.include_live or not i.is_live)]
        accepted = 0
        for item in eligible:
            job = self.queue.add(item, self.state.intent)
            if job.status != JobStatus.SKIPPED:
                accepted += 1
        return accepted

    def pause(self) -> None:
        self.queue.pause()

    def resume(self) -> None:
        self.queue.resume()

    def cancel(self) -> None:
        self.queue.cancel()

    def _apply_job(self, job: DownloadJob) -> None:
        by_id = {j.job_id: j for j in self.state.jobs}
        by_id[job.job_id] = job
        self.state.jobs = list(by_id.values())
        self.job_changed.emit(job)
        self.state_changed.emit(self.state)

    def interpret_ai(self, text: str) -> None:
        self.ai_status.emit("Menghubungkan" if self.agent.api_keys else "Mode lokal")
        fut = self._pool.submit(self.agent.interpret, text, self.state.active_url, self.state.intent)
        fut.add_done_callback(self._ai_done.emit)

    def _finish_ai(self, fut: concurrent.futures.Future) -> None:
        try:
            result = fut.result()
        except Exception as exc:
            self.ai_status.emit("Gangguan")
            self.ai_reply.emit(f"Gagal memahami perintah: {exc}", None)
            return
        self.state.intent = result.intent
        self.queue.set_max_workers(self.state.intent.concurrent_downloads)
        if result.intent.url:
            self.state.active_url = result.intent.url
        self.persist()
        self.ai_status.emit("Online" if result.provider == "gemini" else "Mode lokal")
        fields = sorted(result.patch.model_fields_set) if result.patch else []
        summary = result.intent.explanation or "Perintah dipahami."
        if fields:
            summary += "\nPerubahan: " + ", ".join(x for x in fields if x != "explanation")
        self.ai_reply.emit(summary, result)
        self.state_changed.emit(self.state)
        if result.intent.action == "analyze" and result.intent.url:
            self.analyze(result.intent.url)
        elif result.intent.action == "pause":
            self.pause()
        elif result.intent.action == "resume":
            self.resume()
        elif result.intent.action == "cancel":
            self.cancel()

    def disk_stats(self) -> tuple[int, int, int]:
        folder = Path(self.state.intent.output_folder or default_download_dir())
        import shutil
        usage = shutil.disk_usage(folder)
        used = usage.total - usage.free
        percent = round(used * 100 / usage.total) if usage.total else 0
        return used, usage.total, percent
