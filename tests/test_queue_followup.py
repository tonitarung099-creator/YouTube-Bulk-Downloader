import time

from app.core import queue_manager as qm
from app.models.commands import DownloadIntent
from app.models.state import VideoItem


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
    q.add(first, DownloadIntent())
    time.sleep(.03)
    second_job = q.add(second, DownloadIntent())
    q.pause(second_job.job_id)
    gate.set()
    time.sleep(.12)
    assert "https://youtu.be/b" not in started
