from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yt_dlp

from app.core.paths import bundled_tool_path, youtube_cookie_file
from app.models.commands import DownloadIntent

ProgressCallback = Callable[[dict[str, Any]], None]


class DownloadPaused(Exception):
    pass


class DownloadCancelled(Exception):
    pass


class _YtDlpMessageCollector:
    """Tangkap warning/error yt-dlp agar UI bisa memberi pesan yang lebih berguna."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str) -> None:
        return None

    def warning(self, message: str) -> None:
        self.messages.append(str(message))

    def error(self, message: str) -> None:
        self.messages.append(str(message))

    def text(self) -> str:
        return "\n".join(self.messages)


class YouTubeDownloader:
    """Executor lokal; tidak pernah menjalankan shell dari output AI."""

    _ANTI_BOT_MESSAGE = (
        "YouTube meminta verifikasi anti-bot. Tambahkan atau perbarui cookie YouTube dengan menaruh "
        "file Netscape bernama 'youtube-cookies.txt' di folder data aplikasi: data\\youtube-cookies.txt. "
        "Lalu coba Analisis/Unduh lagi. Jangan bagikan file cookie tersebut kepada orang lain."
    )

    def __init__(self, base_output: str | Path = "downloads") -> None:
        self.base_output = Path(base_output)

    @staticmethod
    def validate_youtube_url(url: str) -> None:
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        if parsed.scheme not in {"http", "https"} or host not in {
            "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"
        }:
            raise ValueError("URL YouTube tidak valid.")

    def analyze(self, url: str) -> dict[str, Any]:
        self.validate_youtube_url(url)
        messages = _YtDlpMessageCollector()
        opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "ignoreerrors": True,
            "logger": messages,
        }
        opts.update(self._portable_tool_options())
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            if self._is_youtube_verification_error(messages.text()):
                raise RuntimeError(self._ANTI_BOT_MESSAGE)
            raise RuntimeError("Metadata tidak ditemukan. Pastikan URL masih tersedia dan dapat diakses.")
        entries = [e for e in (info.get("entries") or []) if isinstance(e, dict) and e.get("id")]
        source_type = self._source_type(info, url)
        normalized = [self._normalize_entry(e, source_type) for e in entries]
        if not normalized and source_type == "video":
            normalized = [self._normalize_entry(info, "video")]
        return {
            "id": info.get("id"),
            "title": info.get("title") or info.get("channel") or info.get("uploader") or "Tanpa judul",
            "description": info.get("description") or "",
            "webpage_url": info.get("webpage_url") or url,
            "channel_url": info.get("channel_url") or info.get("uploader_url"),
            "thumbnail": info.get("thumbnail"),
            "type": source_type,
            "entry_count": len(normalized) if normalized else None,
            "entries": normalized,
        }

    @staticmethod
    def _source_type(info: dict[str, Any], url: str) -> str:
        kind = str(info.get("_type") or "").lower()
        extractor = str(info.get("extractor_key") or "").lower()
        if "playlist" in kind or "playlist" in extractor or "list=" in url:
            return "playlist"
        if any(x in url for x in ("/channel/", "/@", "/c/", "/user/")) and kind != "video":
            return "channel"
        return "video"

    @staticmethod
    def _normalize_entry(e: dict[str, Any], parent_type: str) -> dict[str, Any]:
        vid = str(e.get("id") or "")
        url = e.get("webpage_url") or e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
        live_status = e.get("live_status")
        is_live = bool(e.get("is_live") or live_status in {"is_live", "is_upcoming", "post_live"})
        entry_type = str(e.get("_type") or "video")
        is_short: bool | None = None
        if "/shorts/" in str(url):
            is_short = True
        elif entry_type == "url" and parent_type == "channel":
            is_short = None
        else:
            is_short = False
        return {
            "id": vid,
            "title": e.get("title") or "Tanpa judul",
            "url": url,
            "duration": e.get("duration"),
            "thumbnail": e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get("url"),
            "upload_date": e.get("upload_date") or e.get("release_date"),
            "is_short": is_short,
            "is_live": is_live,
            "entry_type": entry_type,
        }

    def build_options(self, intent: DownloadIntent, progress_cb: ProgressCallback | None = None,
                      pause_event: threading.Event | None = None,
                      cancel_event: threading.Event | None = None) -> dict[str, Any]:
        output_dir = Path(intent.output_folder) if intent.output_folder else self.base_output
        output_dir.mkdir(parents=True, exist_ok=True)

        def progress_hook(data: dict[str, Any]) -> None:
            if cancel_event and cancel_event.is_set():
                raise DownloadCancelled("Dibatalkan pengguna.")
            if pause_event and pause_event.is_set():
                raise DownloadPaused("Dijeda pengguna.")
            if progress_cb:
                progress_cb(data)

        opts: dict[str, Any] = {
            "outtmpl": str(output_dir / "%(uploader|Unknown)s" / "%(title)s [%(id)s].%(ext)s"),
            "ignoreerrors": False,
            "continuedl": True,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": intent.fragment_downloads,
            "windowsfilenames": True,
            "writeinfojson": intent.include_metadata,
            "addmetadata": intent.include_metadata,
            "writethumbnail": intent.include_thumbnail,
            "writesubtitles": intent.include_subtitles,
            "writeautomaticsub": intent.include_subtitles,
            "subtitleslangs": intent.subtitle_languages,
            "match_filter": self._make_filter(intent),
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [progress_hook],
        }
        opts.update(self._portable_tool_options())
        if intent.video_format != "best":
            opts["merge_output_format"] = intent.video_format
        if intent.use_archive:
            opts["download_archive"] = str(output_dir / ".download-archive.txt")
        if intent.mode == "audio":
            opts["format"] = "bestaudio/best"
            if intent.audio_format != "best":
                opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": intent.audio_format, "preferredquality": "0"}]
        else:
            opts["format"] = self._video_format(intent.quality)
        return opts

    def download(self, intent: DownloadIntent, progress_cb: ProgressCallback | None = None,
                 pause_event: threading.Event | None = None,
                 cancel_event: threading.Event | None = None) -> int:
        if not intent.url:
            raise ValueError("URL belum tersedia.")
        self.validate_youtube_url(intent.url)
        opts = self.build_options(intent, progress_cb, pause_event, cancel_event)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.download([intent.url])
        except yt_dlp.utils.DownloadError as exc:
            if self._is_youtube_verification_error(str(exc)):
                raise RuntimeError(self._ANTI_BOT_MESSAGE) from exc
            raise

    @staticmethod
    def _portable_tool_options() -> dict[str, Any]:
        opts: dict[str, Any] = {}
        ffmpeg = bundled_tool_path("ffmpeg")
        if ffmpeg:
            opts["ffmpeg_location"] = str(ffmpeg.parent)
        deno = bundled_tool_path("deno")
        if deno:
            opts["js_runtimes"] = {"deno": {"path": str(deno)}}
        cookie_file = youtube_cookie_file()
        if cookie_file:
            opts["cookiefile"] = str(cookie_file)
        return opts

    @staticmethod
    def _is_youtube_verification_error(message: str) -> bool:
        text = str(message).casefold().replace("’", "'")
        markers = (
            "confirm you're not a bot",
            "use --cookies-from-browser or --cookies",
            "sign in to confirm",
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def _video_format(quality: str) -> str:
        if quality == "best":
            return "bestvideo*+bestaudio/best"
        height = int(quality.removesuffix("p"))
        return f"bestvideo*[height<={height}]+bestaudio/best[height<={height}]"

    @staticmethod
    def _make_filter(intent: DownloadIntent):
        def _filter(info: dict[str, Any], *, incomplete: bool = False):
            if incomplete:
                return None
            url = str(info.get("webpage_url") or info.get("original_url") or "")
            if not intent.include_shorts and "/shorts/" in url:
                return "Shorts dilewati sesuai pengaturan."
            live_status = info.get("live_status")
            if not intent.include_live and (info.get("is_live") or live_status in {"is_live", "is_upcoming", "post_live"}):
                return "Live/stream dilewati sesuai pengaturan."
            return None
        return _filter
