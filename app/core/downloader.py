from __future__ import annotations

from pathlib import Path
from typing import Any

import yt_dlp

from app.models.commands import DownloadIntent


class YouTubeDownloader:
    """Executor lokal. Tidak menerima shell command dari AI."""

    def __init__(self, base_output: str | Path = "downloads") -> None:
        self.base_output = Path(base_output)

    def analyze(self, url: str) -> dict[str, Any]:
        opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        entries = info.get("entries") or []
        return {
            "id": info.get("id"),
            "title": info.get("title") or info.get("channel") or info.get("uploader"),
            "webpage_url": info.get("webpage_url") or url,
            "type": info.get("_type") or "video",
            "entry_count": len(entries) if entries else 1,
            "entries": [
                {
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "url": e.get("url"),
                }
                for e in entries
                if e
            ],
        }

    def download(self, intent: DownloadIntent) -> int:
        if not intent.url:
            raise ValueError("URL belum tersedia.")

        output_dir = Path(intent.output_folder) if intent.output_folder else self.base_output
        output_dir.mkdir(parents=True, exist_ok=True)

        opts: dict[str, Any] = {
            "outtmpl": str(output_dir / "%(uploader|Unknown)s" / "%(title)s [%(id)s].%(ext)s"),
            "ignoreerrors": True,
            "continuedl": True,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": intent.concurrent_downloads,
            "windowsfilenames": True,
            "writemetadata": intent.include_metadata,
            "writethumbnail": intent.include_thumbnail,
            "writesubtitles": intent.include_subtitles,
            "writeautomaticsub": intent.include_subtitles,
            "subtitleslangs": ["id", "en", "en.*"],
            "merge_output_format": intent.video_format if intent.video_format != "best" else None,
            "match_filter": self._make_filter(intent),
        }

        if intent.use_archive:
            opts["download_archive"] = str(output_dir / ".download-archive.txt")

        if intent.mode == "audio":
            opts["format"] = "bestaudio/best"
            if intent.audio_format != "best":
                opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": intent.audio_format,
                        "preferredquality": "0",
                    }
                ]
        else:
            opts["format"] = self._video_format(intent.quality)

        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.download([intent.url])

    @staticmethod
    def _video_format(quality: str) -> str:
        if quality == "best":
            return "bestvideo*+bestaudio/best"
        height = int(quality.removesuffix("p"))
        return (
            f"bestvideo*[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )

    @staticmethod
    def _make_filter(intent: DownloadIntent):
        def _filter(info: dict[str, Any], *, incomplete: bool = False):
            if incomplete:
                return None

            webpage_url = str(info.get("webpage_url") or info.get("original_url") or "")
            if not intent.include_shorts and "/shorts/" in webpage_url:
                return "Shorts dilewati sesuai perintah."

            live_status = info.get("live_status")
            if not intent.include_live and (
                info.get("is_live") or live_status in {"is_live", "is_upcoming", "post_live"}
            ):
                return "Live/stream dilewati sesuai perintah."

            return None

        return _filter
