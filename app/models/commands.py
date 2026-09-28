from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

Action = Literal["analyze", "download", "pause", "resume", "cancel", "open_folder", "unknown"]
SourceType = Literal["auto", "video", "playlist", "channel"]
Quality = Literal["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]


class DownloadIntent(BaseModel):
    """Snapshot pengaturan yang aman untuk executor lokal."""
    action: Action = "unknown"
    source_type: SourceType = "auto"
    url: Optional[str] = None
    mode: Literal["video", "audio"] = "video"
    quality: Quality = "best"
    video_format: Literal["mp4", "mkv", "webm", "best"] = "mp4"
    audio_format: Literal["mp3", "m4a", "opus", "best"] = "best"
    include_shorts: bool = True
    include_live: bool = True
    include_subtitles: bool = False
    include_thumbnail: bool = False
    include_metadata: bool = True
    use_archive: bool = True
    concurrent_downloads: int = Field(default=3, ge=1, le=10)
    fragment_downloads: int = Field(default=4, ge=1, le=16)
    output_folder: Optional[str] = None
    subtitle_languages: list[str] = Field(default_factory=lambda: ["id", "en", "en.*"])
    selected_ids: list[str] = Field(default_factory=list)
    explanation: str = "Perintah belum dikenali."


class DownloadIntentPatch(BaseModel):
    action: Optional[Action] = None
    source_type: Optional[SourceType] = None
    url: Optional[str] = None
    mode: Optional[Literal["video", "audio"]] = None
    quality: Optional[Quality] = None
    video_format: Optional[Literal["mp4", "mkv", "webm", "best"]] = None
    audio_format: Optional[Literal["mp3", "m4a", "opus", "best"]] = None
    include_shorts: Optional[bool] = None
    include_live: Optional[bool] = None
    include_subtitles: Optional[bool] = None
    include_thumbnail: Optional[bool] = None
    include_metadata: Optional[bool] = None
    use_archive: Optional[bool] = None
    concurrent_downloads: Optional[int] = Field(default=None, ge=1, le=10)
    fragment_downloads: Optional[int] = Field(default=None, ge=1, le=16)
    output_folder: Optional[str] = None
    subtitle_languages: Optional[list[str]] = None
    selected_ids: Optional[list[str]] = None
    explanation: str = ""


class AgentResult(BaseModel):
    intent: DownloadIntent
    provider: Literal["gemini", "local_fallback"]
    key_index: Optional[int] = None
    patch: Optional[DownloadIntentPatch] = None
