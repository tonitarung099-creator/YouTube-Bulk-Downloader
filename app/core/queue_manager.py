from __future__ import annotations

import threading, uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from app.core.downloader import DownloadCancelled, DownloadPaused, YouTubeDownloader
from app.models.commands import DownloadIntent
from app.models.state import DownloadJob, JobStatus, VideoItem

EventCallback = Callable[[DownloadJob], None]


@dataclass
class _Control:
    pause: threading.Event
    cancel: threading.Event


class QueueManager:
    """Antrean paralel video dengan kontrol jeda/lanjut/batal per pekerjaan."""

    ACTIVE = {JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.POSTPROCESSING, JobStatus.PAUSING}

    def __init__(self, max_workers: int = 5, on_event: EventCallback | None = None) -> None:
        self.max_workers = max(1, min(10, max_workers))
        self._pending_max_workers = self.max_workers
        self.on_event = on_event
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="yt-job")
        self._jobs: dict[str, DownloadJob] = {}
        self._controls: dict[str, _Control] = {}
        self._lock = threading.RLock()

    def set_max_workers(self, max_workers: int) -> bool:
        """Terapkan limit baru segera bila antrean idle, atau setelah pekerjaan aktif selesai."""
        target = max(1, min(10, int(max_workers)))
        with self._lock:
            self._pending_max_workers = target
        return self._maybe_reconfigure_executor()

    def _maybe_reconfigure_executor(self) -> bool:
        with self._lock:
            if self._pending_max_workers == self.max_workers:
                return True
            if any(job.status in self.ACTIVE for job in self._jobs.values()):
                return False
            old = self._executor
            self.max_workers = self._pending_max_workers
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="yt-job")
        old.shutdown(wait=False, cancel_futures=False)
        return True

    def add(self, video: VideoItem, intent: DownloadIntent) -> DownloadJob:
        job = DownloadJob(job_id=uuid.uuid4().hex, video=video.model_copy(deep=True), intent=intent.model_copy(deep=True))
        with self._lock:
            duplicate = any(
                j.video.id == video.id
                and j.intent.quality == intent.quality
                and j.intent.mode == intent.mode
                and j.status in {JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.POSTPROCESSING}
                for j in self._jobs.values()
            )
            if duplicate:
                job.status = JobStatus.SKIPPED
                job.error = "Sudah ada dalam antrean dengan profil yang sama."
                self._emit(job)
                return job
            self._jobs[job.job_id] = job
            self._controls[job.job_id] = _Control(threading.Event(), threading.Event())
        self._emit(job)
        self._executor.submit(self._run, job.job_id)
        return job

    def _run(self, job_id: str) -> None:
        job = self._jobs[job_id]
        ctl = self._controls[job_id]
        if ctl.cancel.is_set():
            job.status = JobStatus.CANCELLED
            self._emit(job)
            self._maybe_reconfigure_executor()
            return
        if ctl.pause.is_set():
            job.status = JobStatus.PAUSED
            self._emit(job)
            self._maybe_reconfigure_executor()
            return

        job.status = JobStatus.DOWNLOADING
        self._emit(job)
        downloader = YouTubeDownloader()

        def progress(data: dict) -> None:
            if data.get("status") == "finished" and data.get("postprocessor"):
                job.status = JobStatus.POSTPROCESSING
            job.downloaded_bytes = data.get("downloaded_bytes")
            job.total_bytes = data.get("total_bytes") or data.get("total_bytes_estimate")
            job.speed = data.get("speed")
            job.eta = data.get("eta")
            if job.downloaded_bytes is not None and job.total_bytes:
                job.percent = min(100.0, job.downloaded_bytes * 100.0 / job.total_bytes)
            self._emit(job)

        intent = job.intent.model_copy(update={"url": job.video.url})
        try:
            code = downloader.download(intent, progress, ctl.pause, ctl.cancel)
            if code != 0:
                raise RuntimeError(f"yt-dlp selesai dengan kode {code}")
            job.status = JobStatus.COMPLETED
            job.percent = 100.0
        except DownloadPaused:
            job.status = JobStatus.PAUSED
        except DownloadCancelled:
            job.status = JobStatus.CANCELLED
        except Exception as exc:
            job.status = JobStatus.CANCELLED if ctl.cancel.is_set() else JobStatus.FAILED
            job.error = str(exc)
        self._emit(job)
        self._maybe_reconfigure_executor()

    def pause(self, job_id: str | None = None) -> None:
        targets = [job_id] if job_id else list(self._controls)
        for jid in targets:
            job = self._jobs.get(jid)
            ctl = self._controls.get(jid)
            if job and ctl and job.status in {JobStatus.QUEUED, JobStatus.DOWNLOADING}:
                job.status = JobStatus.PAUSING
                ctl.pause.set()
                self._emit(job)

    def resume(self, job_id: str | None = None) -> None:
        targets = [job_id] if job_id else list(self._controls)
        for jid in targets:
            job = self._jobs.get(jid)
            ctl = self._controls.get(jid)
            if job and ctl and job.status == JobStatus.PAUSED:
                ctl.pause.clear()
                job.status = JobStatus.QUEUED
                self._emit(job)
                self._executor.submit(self._run, jid)

    def cancel(self, job_id: str | None = None) -> None:
        targets = [job_id] if job_id else list(self._controls)
        for jid in targets:
            ctl = self._controls.get(jid)
            job = self._jobs.get(jid)
            if ctl and job and job.status not in {JobStatus.COMPLETED, JobStatus.CANCELLED}:
                ctl.cancel.set()
                if job.status in {JobStatus.QUEUED, JobStatus.PAUSED}:
                    job.status = JobStatus.CANCELLED
                    self._emit(job)
        self._maybe_reconfigure_executor()

    def jobs(self) -> list[DownloadJob]:
        with self._lock:
            return [j.model_copy(deep=True) for j in self._jobs.values()]

    def _emit(self, job: DownloadJob) -> None:
        if self.on_event:
            self.on_event(job.model_copy(deep=True))
