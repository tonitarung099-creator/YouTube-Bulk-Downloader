import time

from app.core import queue_manager as qm
from app.models.commands import DownloadIntent
from app.models.state import JobStatus, VideoItem


def test_parallel_limit_can_change_while_idle():
    q = qm.QueueManager(max_workers=5)
    assert q.max_workers == 5
    assert q.set_max_workers(2) is True
    assert q.max_workers == 2


def test_paused_queued_job_does_not_start_download(monkeypatch):
    started = []
    gate = qm.threading.Event()

    def controlled(self, intent, progress_cb=None, pause_event=None, cancel_event=None):
        started.append(intent.url)
        gate.wait(.2)
        return 0

    monkeypatch.setattr(qm.YouTubeDownloader, "download", controlled)
    q = qm.QueueManager(max_workers=1)
    first = VideoItem(id="a", title="A", url="https://youtu.be/a")
    second = VideoItem(id="b", title="B", url="https://youtu.be/b")
    q.add(first, DownloadIntent(use_archive=False))
    time.sleep(.03)
    second_job = q.add(second, DownloadIntent(use_archive=False))
    q.pause(second_job.job_id)
    gate.set()
    time.sleep(.12)
    assert "https://youtu.be/b" not in started


def test_archive_is_written_after_success_and_is_profile_aware(monkeypatch, tmp_path):
    received = []

    def successful(self, intent, progress_cb=None, pause_event=None, cancel_event=None):
        received.append(intent)
        return 0

    monkeypatch.setattr(qm.YouTubeDownloader, "download", successful)
    video = VideoItem(id="archive-1", title="Arsip", url="https://youtu.be/archive-1")
    base = DownloadIntent(output_folder=str(tmp_path), quality="1080p", video_format="mp4", use_archive=True)

    first_queue = qm.QueueManager(max_workers=1)
    first = first_queue.add(video, base)
    for _ in range(50):
        if first_queue.jobs()[0].status == JobStatus.COMPLETED:
            break
        time.sleep(.01)
    assert first_queue.jobs()[0].status == JobStatus.COMPLETED
    assert received and received[0].use_archive is False

    second_queue = qm.QueueManager(max_workers=1)
    same = second_queue.add(video, base)
    assert same.status == JobStatus.SKIPPED

    different = second_queue.add(video, base.model_copy(update={"quality": "720p"}))
    assert different.status != JobStatus.SKIPPED
