from __future__ import annotations

import threading, uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

from app.core.download_archive import DownloadArchive
from app.core.downloader import DownloadCancelled, DownloadPaused, YouTubeDownloader
from app.models.commands import DownloadIntent
from app.models.state import DownloadJob, JobStatus, VideoItem

EventCallback = Callable[[DownloadJob], None]


@dataclass
class _Control:
    pause: threading.Event
    cancel: threading.Event


class QueueManager:
    """Antrean paralel video dengan kontrol, archive, dan shutdown terkoordinasi."""

    ACTIVE = {JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.POSTPROCESSING, JobStatus.PAUSING}
    DUPLICATE_BLOCKING = ACTIVE | {JobStatus.PAUSED}
    TERMINAL = {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED, JobStatus.SKIPPED}

    def __init__(self, max_workers: int = 5, on_event: EventCallback | None = None) -> None:
        self.max_workers = max(1, min(10, max_workers))
        self._pending_max_workers = self.max_workers
        self.on_event = on_event
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="yt-job")
        self._jobs: dict[str, DownloadJob] = {}
        self._controls: dict[str, _Control] = {}
        self._lock = threading.RLock()
        self._archive = DownloadArchive()
        self._closed = False

    def set_max_workers(self, max_workers: int) -> bool:
        target = max(1, min(10, int(max_workers)))
        with self._lock:
            if self._closed:
                return False
            self._pending_max_workers = target
        return self._maybe_reconfigure_executor()

    def _maybe_reconfigure_executor(self) -> bool:
        with self._lock:
            if self._closed:
                return False
            if self._pending_max_workers == self.max_workers:
                return True
            if any(job.status in self.ACTIVE for job in self._jobs.values()):
                return False
            old = self._executor
            self.max_workers = self._pending_max_workers
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="yt-job")
        old.shutdown(wait=False, cancel_futures=False)
        return True

    @staticmethod
    def _same_profile(job: DownloadJob, video: VideoItem, intent: DownloadIntent) -> bool:
        return (
            job.video.id == video.id
            and job.intent.mode == intent.mode
            and job.intent.quality == intent.quality
            and job.intent.video_format == intent.video_format
            and job.intent.audio_format == intent.audio_format
        )

    def add(self, video: VideoItem, intent: DownloadIntent) -> DownloadJob:
        job = DownloadJob(job_id=uuid.uuid4().hex, video=video.model_copy(deep=True), intent=intent.model_copy(deep=True))
        with self._lock:
            if self._closed:
                job.status = JobStatus.SKIPPED
                job.error = "Aplikasi sedang ditutup; antrean tidak menerima pekerjaan baru."
                self._emit(job)
                return job
        if self._archive.contains(video, intent):
            job.status = JobStatus.SKIPPED
            job.error = "Sudah pernah selesai dengan profil kualitas/format yang sama."
            self._emit(job)
            return job
        with self._lock:
            if self._closed:
                job.status = JobStatus.SKIPPED
                job.error = "Aplikasi sedang ditutup; antrean tidak menerima pekerjaan baru."
                self._emit(job)
                return job
            duplicate = any(
                self._same_profile(existing, video, intent)
                and existing.status in self.DUPLICATE_BLOCKING
                for existing in self._jobs.values()
            )
            if duplicate:
                job.status = JobStatus.SKIPPED
                job.error = "Sudah ada dalam antrean dengan profil yang sama."
                self._emit(job)
                return job
            self._jobs[job.job_id] = job
            self._controls[job.job_id] = _Control(threading.Event(), threading.Event())
            executor = self._executor
        self._emit(job)
        executor.submit(self._run, job.job_id)
        return job

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            ctl = self._controls.get(job_id)
        if not job or not ctl:
            return
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

        # Queue manager mengelola archive sendiri supaya worker paralel tidak menulis file yang sama.
        worker_intent = job.intent.model_copy(update={"url": job.video.url, "use_archive": False})
        try:
            code = downloader.download(worker_intent, progress, ctl.pause, ctl.cancel)
            if code != 0:
                raise RuntimeError(f"yt-dlp selesai dengan kode {code}")
            if ctl.cancel.is_set():
                raise DownloadCancelled("Dibatalkan saat aplikasi ditutup.")
            self._archive.mark_completed(job.video, job.intent)
            job.status = JobStatus.COMPLETED
            job.percent = 100.0
        except DownloadPaused:
            job.status = JobStatus.CANCELLED if ctl.cancel.is_set() else JobStatus.PAUSED
        except DownloadCancelled:
            job.status = JobStatus.CANCELLED
        except Exception as exc:
            job.status = JobStatus.CANCELLED if ctl.cancel.is_set() else JobStatus.FAILED
            job.error = str(exc)
        self._emit(job)
        self._maybe_reconfigure_executor()

    def pause(self, job_id: str | None = None) -> None:
        with self._lock:
            if self._closed:
                return
            targets = [job_id] if job_id else list(self._controls)
        for jid in targets:
            job = self._jobs.get(jid)
            ctl = self._controls.get(jid)
            if job and ctl and job.status in {JobStatus.QUEUED, JobStatus.DOWNLOADING}:
                job.status = JobStatus.PAUSING
                ctl.pause.set()
                self._emit(job)

    def resume(self, job_id: str | None = None) -> None:
        with self._lock:
            if self._closed:
                return
            targets = [job_id] if job_id else list(self._controls)
            executor = self._executor
        for jid in targets:
            job = self._jobs.get(jid)
            ctl = self._controls.get(jid)
            if job and ctl and job.status == JobStatus.PAUSED:
                ctl.pause.clear()
                job.status = JobStatus.QUEUED
                self._emit(job)
                executor.submit(self._run, jid)

    def cancel(self, job_id: str | None = None) -> None:
        with self._lock:
            targets = [job_id] if job_id else list(self._controls)
        for jid in targets:
            ctl = self._controls.get(jid)
            job = self._jobs.get(jid)
            if ctl and job and job.status not in self.TERMINAL:
                ctl.cancel.set()
                if job.status in {JobStatus.QUEUED, JobStatus.PAUSED}:
                    job.status = JobStatus.CANCELLED
                    self._emit(job)
        self._maybe_reconfigure_executor()

    def shutdown(self, wait: bool = False) -> None:
        """Tutup antrean secara idempotent dan hentikan pekerjaan secepat yang aman."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            executor = self._executor
            updates: list[DownloadJob] = []
            for jid, ctl in self._controls.items():
                ctl.cancel.set()
                job = self._jobs.get(jid)
                if job and job.status in {JobStatus.QUEUED, JobStatus.PAUSED}:
                    job.status = JobStatus.CANCELLED
                    updates.append(job.model_copy(deep=True))
        for job in updates:
            self._emit(job)
        executor.shutdown(wait=wait, cancel_futures=True)

    def jobs(self) -> list[DownloadJob]:
        with self._lock:
            return [j.model_copy(deep=True) for j in self._jobs.values()]

    def _emit(self, job: DownloadJob) -> None:
        if self.on_event:
            self.on_event(job.model_copy(deep=True))
