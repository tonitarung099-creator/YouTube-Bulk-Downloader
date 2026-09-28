from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from pydantic import BaseModel, Field
from app.models.commands import DownloadIntent

class JobStatus(StrEnum):
    READY="ready"; QUEUED="queued"; DOWNLOADING="downloading"; POSTPROCESSING="postprocessing"; PAUSING="pausing"; PAUSED="paused"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"; SKIPPED="skipped"

class VideoItem(BaseModel):
    id:str; title:str="Tanpa judul"; url:str; duration:int|None=None; thumbnail:str|None=None; upload_date:str|None=None; kind:str="Video"; is_short:bool|None=None; is_live:bool=False; status:JobStatus=JobStatus.READY; selected:bool=True

class SourceInfo(BaseModel):
    id:str|None=None; title:str="—"; url:str; source_type:str="video"; description:str=""; channel_url:str|None=None; thumbnail:str|None=None; total_detected:int|None=None; playlist_count:int|None=None; shorts_count:int|None=None; items:list[VideoItem]=Field(default_factory=list)

class DownloadJob(BaseModel):
    job_id:str; video:VideoItem; intent:DownloadIntent; status:JobStatus=JobStatus.QUEUED; percent:float|None=None; downloaded_bytes:int|None=None; total_bytes:int|None=None; speed:float|None=None; eta:int|None=None; output_path:str|None=None; error:str|None=None; created_at:str=Field(default_factory=lambda:datetime.now(timezone.utc).isoformat())

class AppState(BaseModel):
    active_url:str|None=None
    source:SourceInfo|None=None
    intent:DownloadIntent=Field(default_factory=lambda:DownloadIntent(quality="1080p",video_format="mp4",audio_format="mp3",concurrent_downloads=5,include_shorts=False,include_live=False,include_subtitles=True,include_thumbnail=True,include_metadata=True,use_archive=True,output_folder=str(Path("downloads").resolve())))
    selected_ids:set[str]=Field(default_factory=set)
    jobs:list[DownloadJob]=Field(default_factory=list)
