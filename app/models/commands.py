from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class DownloadIntent(BaseModel):
    """Perintah terstruktur yang aman untuk dieksekusi engine lokal."""

    action: Literal[
        "analyze",
        "download",
        "pause",
        "resume",
        "cancel",
        "open_folder",
        "unknown",
    ] = "unknown"
    source_type: Literal["auto", "video", "playlist", "channel"] = "auto"
    url: Optional[str] = None
    mode: Literal["video", "audio"] = "video"
    quality: Literal["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"] = "best"
    video_format: Literal["mp4", "mkv", "webm", "best"] = "mp4"
    audio_format: Literal["mp3", "m4a", "opus", "best"] = "best"
    include_shorts: bool = True
    include_live: bool = True
    include_subtitles: bool = False
    include_thumbnail: bool = False
    include_metadata: bool = True
    use_archive: bool = True
    concurrent_downloads: int = Field(default=3, ge=1, le=10)
    output_folder: Optional[str] = None
    explanation: str = "Perintah belum dikenali."


class AgentResult(BaseModel):
    intent: DownloadIntent
    provider: Literal["gemini", "local_fallback"]
    key_index: Optional[int] = None
