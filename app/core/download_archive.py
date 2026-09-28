from __future__ import annotations

import json
import threading
from pathlib import Path

from app.models.commands import DownloadIntent
from app.models.state import VideoItem


class DownloadArchive:
    """Archive aplikasi yang aman untuk worker paralel dan sadar profil output."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    @staticmethod
    def profile(video: VideoItem, intent: DownloadIntent) -> dict[str, str]:
        return {
            "id": video.id,
            "mode": intent.mode,
            "quality": intent.quality,
            "video_format": intent.video_format,
            "audio_format": intent.audio_format,
        }

    @staticmethod
    def path_for(intent: DownloadIntent) -> Path:
        folder = Path(intent.output_folder or "downloads")
        folder.mkdir(parents=True, exist_ok=True)
        return folder / ".app-download-archive.jsonl"

    def contains(self, video: VideoItem, intent: DownloadIntent) -> bool:
        if not intent.use_archive:
            return False
        wanted = self.profile(video, intent)
        path = self.path_for(intent)
        if not path.exists():
            return False
        with self._lock:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    for raw in handle:
                        try:
                            row = json.loads(raw)
                        except (json.JSONDecodeError, TypeError):
                            continue
                        if all(row.get(key) == value for key, value in wanted.items()):
                            return True
            except OSError:
                return False
        return False

    def mark_completed(self, video: VideoItem, intent: DownloadIntent) -> None:
        if not intent.use_archive:
            return
        row = self.profile(video, intent)
        path = self.path_for(intent)
        with self._lock:
            if self.contains(video, intent):
                return
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
