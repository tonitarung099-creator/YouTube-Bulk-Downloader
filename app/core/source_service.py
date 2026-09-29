from __future__ import annotations

from app.core.downloader import YouTubeDownloader
from app.models.state import SourceInfo,VideoItem


class SourceService:
    def __init__(self,downloader:YouTubeDownloader|None=None)->None:self.downloader=downloader or YouTubeDownloader()

    @staticmethod
    def _kind(entry:dict)->str:
        if entry.get("is_live"):return "Live"
        if entry.get("is_short") is True:return "Shorts"
        if entry.get("is_short") is False:return "Video"
        return "Belum diketahui"

    def _to_source(self,raw:dict,fallback_url:str)->SourceInfo:
        items=[VideoItem(id=e["id"],title=e.get("title") or "Tanpa judul",url=e.get("url") or fallback_url,duration=e.get("duration"),thumbnail=e.get("thumbnail"),upload_date=e.get("upload_date"),kind=self._kind(e),is_short=e.get("is_short"),is_live=bool(e.get("is_live"))) for e in raw.get("entries",[]) if e.get("id")]
        known=all(i.is_short is not None for i in items)
        return SourceInfo(id=raw.get("id"),title=raw.get("title") or "—",url=raw.get("webpage_url") or fallback_url,source_type=raw.get("type") or "video",description=raw.get("description") or "",channel_url=raw.get("channel_url"),thumbnail=raw.get("thumbnail"),total_detected=len(items) if items else raw.get("entry_count"),shorts_count=sum(i.is_short is True for i in items) if items and known else None,items=items)

    def analyze(self,url:str)->SourceInfo:
        return self._to_source(self.downloader.analyze(url),url)

    def search(self,query:str,limit:int=50)->SourceInfo:
        raw=self.downloader.search(query,limit)
        return self._to_source(raw,raw.get("webpage_url") or "https://www.youtube.com/")
