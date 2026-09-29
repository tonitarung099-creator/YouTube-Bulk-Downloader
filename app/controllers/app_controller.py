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
    gemini_config_changed = Signal(int, str)
    gemini_test_result = Signal(bool, str)

    _analysis_done = Signal(int, object)
    _ai_done = Signal(object)
    _job_arrived = Signal(object)
    _gemini_test_done = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._analysis_done.connect(self._finish_analysis, Qt.ConnectionType.QueuedConnection)
        self._ai_done.connect(self._finish_ai, Qt.ConnectionType.QueuedConnection)
        self._job_arrived.connect(self._apply_job, Qt.ConnectionType.QueuedConnection)
        self._gemini_test_done.connect(self._finish_gemini_test, Qt.ConnectionType.QueuedConnection)

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
        self._closing = False
        self._pending_ai_download = False
        self.queue = QueueManager(self.state.intent.concurrent_downloads, self._job_arrived.emit)
        self.agent = GeminiLanguageAgent(model=saved.get("gemini_model") or None)

    def persist(self) -> None:
        if self._closing:
            return
        self.storage.save({
            "intent": self.state.intent.model_dump(mode="json"),
            "gemini_model": self.agent.model,
        })

    def gemini_config(self) -> tuple[int, str]:
        return len(self.agent.api_keys), self.agent.model

    def configure_gemini(self, keys: list[str], model: str | None = None) -> None:
        if self._closing:
            return
        self.agent.set_api_keys(keys)
        if model:
            self.agent.set_model(model)
        self.persist()
        count, active_model = self.gemini_config()
        self.gemini_config_changed.emit(count, active_model)
        self.ai_status.emit(f"Siap • {count} key" if count else "Belum dikonfigurasi")

    def clear_gemini_keys(self) -> None:
        if self._closing:
            return
        self.agent.set_api_keys([])
        self.gemini_config_changed.emit(0, self.agent.model)
        self.ai_status.emit("Belum dikonfigurasi")
        self.gemini_test_result.emit(False, "API key dikosongkan dari sesi aplikasi.")

    def test_gemini(self) -> None:
        if self._closing:
            return
        if not self.agent.api_keys:
            self.gemini_test_result.emit(False, "Belum ada API key Gemini.")
            return
        self.ai_status.emit("Menguji API…")
        fut = self._pool.submit(self.agent.test_connection)
        fut.add_done_callback(self._gemini_test_done.emit)

    def _finish_gemini_test(self, fut: concurrent.futures.Future) -> None:
        if self._closing:
            return
        try:
            model_name, key_index = fut.result()
        except Exception as exc:
            self.ai_status.emit("API bermasalah")
            self.gemini_test_result.emit(False, str(exc))
            return
        self.ai_status.emit(f"Online • {model_name}")
        self.gemini_test_result.emit(True, f"Terhubung ke {model_name} dengan key #{key_index + 1}.")

    def update_intent(self, **changes) -> None:
        if self._closing:
            return
        self.state.intent = self.state.intent.model_copy(update=changes)
        if "concurrent_downloads" in changes:
            self.queue.set_max_workers(self.state.intent.concurrent_downloads)
        self.persist()
        self.state_changed.emit(self.state)

    def analyze(self, url: str) -> None:
        if self._closing:
            return
        target = url.strip()
        if not target:
            self.analysis_failed.emit("URL YouTube masih kosong.")
            return
        self._analysis_seq += 1
        seq = self._analysis_seq
        self.state.active_url = target
        self.state_changed.emit(self.state)
        fut = self._pool.submit(self.source_service.analyze, target)
        fut.add_done_callback(lambda f: self._analysis_done.emit(seq, f))

    def _finish_analysis(self, seq: int, fut: concurrent.futures.Future) -> None:
        if self._closing or seq != self._analysis_seq:
            return
        try:
            source = fut.result()
        except Exception as exc:
            self._pending_ai_download = False
            self.analysis_failed.emit(str(exc))
            return
        self.state.source = source
        self.state.active_url = source.url or self.state.active_url
        self.state.selected_ids = {i.id for i in source.items}
        self.source_loaded.emit(source)
        self.state_changed.emit(self.state)
        if self._pending_ai_download:
            self._pending_ai_download = False
            accepted = self.queue_selected(all_items=False)
            self.ai_reply.emit(f"Analisis selesai. {accepted} video dimasukkan ke antrean.", None)

    def queue_selected(self, all_items: bool = False) -> int:
        if self._closing or not self.state.source:
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
        if not self._closing:
            self.queue.pause()

    def resume(self) -> None:
        if not self._closing:
            self.queue.resume()

    def cancel(self) -> None:
        self._pending_ai_download = False
        self.queue.cancel()

    def _apply_job(self, job: DownloadJob) -> None:
        if self._closing:
            return
        by_id = {j.job_id: j for j in self.state.jobs}
        by_id[job.job_id] = job
        self.state.jobs = list(by_id.values())
        self.job_changed.emit(job)
        self.state_changed.emit(self.state)

    def interpret_ai(self, text: str) -> None:
        if self._closing:
            return
        self.ai_status.emit("Menghubungkan Gemini…" if self.agent.api_keys else "Mode lokal")
        fut = self._pool.submit(self.agent.interpret, text, self.state.active_url, self.state.intent)
        fut.add_done_callback(self._ai_done.emit)

    def _finish_ai(self, fut: concurrent.futures.Future) -> None:
        if self._closing:
            return
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
        if result.provider == "gemini":
            self.ai_status.emit(f"Online • {self.agent.last_model or self.agent.model}")
        elif self.agent.api_keys and self.agent.last_error:
            self.ai_status.emit("Gemini gagal • Mode lokal")
        else:
            self.ai_status.emit("Mode lokal")
        fields = sorted(result.patch.model_fields_set) if result.patch else []
        summary = result.intent.explanation or "Perintah dipahami."
        changed = ", ".join(x for x in fields if x != "explanation")
        if changed:
            summary += "\nPerubahan: " + changed
        if result.provider != "gemini" and self.agent.api_keys and self.agent.last_error:
            summary += "\nGemini: " + self.agent._friendly_error()
        self.ai_reply.emit(summary, result)
        self.state_changed.emit(self.state)
        if result.intent.action == "analyze" and result.intent.url:
            self.analyze(result.intent.url)
        elif result.intent.action == "download":
            target = result.intent.url or self.state.active_url
            if self.state.source and target and self.state.source.url == target:
                accepted = self.queue_selected(all_items=False)
                self.ai_reply.emit(f"{accepted} video dimasukkan ke antrean unduhan.", result)
            elif target:
                self._pending_ai_download = True
                self.ai_reply.emit("Saya analisis URL dulu, lalu unduhan dimulai otomatis.", result)
                self.analyze(target)
            else:
                self.ai_reply.emit("Belum ada URL. Tempel URL YouTube terlebih dahulu.", result)
        elif result.intent.action == "pause":
            self.pause()
        elif result.intent.action == "resume":
            self.resume()
        elif result.intent.action == "cancel":
            self.cancel()

    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._analysis_seq += 1
        self._pending_ai_download = False
        self.queue.shutdown(wait=False)
        self._pool.shutdown(wait=False, cancel_futures=True)

    def disk_stats(self) -> tuple[int, int, int]:
        folder = Path(self.state.intent.output_folder or default_download_dir())
        folder.mkdir(parents=True, exist_ok=True)
        import shutil
        usage = shutil.disk_usage(folder)
        used = usage.total - usage.free
        percent = round(used * 100 / usage.total) if usage.total else 0
        return used, usage.total, percent
