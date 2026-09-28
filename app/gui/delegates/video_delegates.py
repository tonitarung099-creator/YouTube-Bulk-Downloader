from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QRectF,Qt,QUrl
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QPixmap
from PySide6.QtNetwork import QNetworkAccessManager,QNetworkRequest
from PySide6.QtWidgets import QStyledItemDelegate

from app.gui.models.video_table_model import DURATION_ROLE,STATUS_ROLE,THUMBNAIL_ROLE


class ThumbnailDelegate(QStyledItemDelegate):
    """Lazy thumbnail cache; network tidak pernah memblok GUI thread."""

    def __init__(self,parent=None,max_cache:int=128):
        super().__init__(parent);self._cache:OrderedDict[str,QPixmap]=OrderedDict();self._pending:set[str]=set();self._max=max_cache;self._net=QNetworkAccessManager(self);self._net.finished.connect(self._finished)

    def _request(self,url:str)->None:
        if not url or url in self._cache or url in self._pending:return
        path=Path(url)
        if path.is_file():
            pix=QPixmap(str(path))
            if not pix.isNull():self._store(url,pix)
            return
        self._pending.add(url);reply=self._net.get(QNetworkRequest(QUrl(url)));reply.setProperty("thumbnail_url",url)

    def _finished(self,reply):
        url=str(reply.property("thumbnail_url") or "");self._pending.discard(url)
        if reply.error()==reply.NetworkError.NoError:
            pix=QPixmap();pix.loadFromData(reply.readAll())
            if not pix.isNull():self._store(url,pix)
        reply.deleteLater()
        parent=self.parent()
        if parent is not None and hasattr(parent,"viewport"):parent.viewport().update()

    def _store(self,url:str,pix:QPixmap)->None:
        self._cache[url]=pix;self._cache.move_to_end(url)
        while len(self._cache)>self._max:self._cache.popitem(last=False)

    @staticmethod
    def _duration(seconds)->str:
        if seconds is None:return ""
        m,s=divmod(int(seconds),60);h,m=divmod(m,60);return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

    def paint(self,painter:QPainter,option,index):
        painter.save();rect=option.rect.adjusted(5,5,-5,-5);painter.setRenderHint(QPainter.Antialiasing,True)
        path=QPainterPath();path.addRoundedRect(QRectF(rect),5,5);painter.fillPath(path,QColor("#1B2732"));painter.setClipPath(path)
        url=str(index.data(THUMBNAIL_ROLE) or "")
        pix=self._cache.get(url)
        if pix is None and url:self._request(url)
        if pix is not None:
            scaled=pix.scaled(rect.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation);sx=max(0,(scaled.width()-rect.width())//2);sy=max(0,(scaled.height()-rect.height())//2);source=scaled.copy(sx,sy,rect.width(),rect.height());painter.drawPixmap(rect,source)
        painter.setClipping(False)
        label=self._duration(index.data(DURATION_ROLE))
        if label:
            metrics=painter.fontMetrics();w=metrics.horizontalAdvance(label)+10;h=18;badge=QRectF(rect.right()-w-4,rect.bottom()-h-3,w,h);painter.fillRect(badge,QColor(0,0,0,190));painter.setPen(QColor("#F3F5F7"));painter.drawText(badge,Qt.AlignCenter,label)
        painter.restore()


class StatusBadgeDelegate(QStyledItemDelegate):
    COLORS={
        "ready":("#26323A","#D6DEE4"),"queued":("#073454","#47BAFF"),"downloading":("#3B1A22","#FF5971"),
        "postprocessing":("#3A2B12","#FFCC66"),"pausing":("#3A2B12","#FFCC66"),"paused":("#33333C","#D3D3DC"),
        "completed":("#123328","#58E39C"),"failed":("#451A20","#FF7183"),"cancelled":("#3A2427","#E9A2AA"),"skipped":("#282B31","#AEB7BF"),
    }
    def paint(self,painter:QPainter,option,index):
        text=str(index.data(Qt.DisplayRole) or "");status=str(index.data(STATUS_ROLE) or "ready");bg,fg=self.COLORS.get(status,self.COLORS["ready"]);painter.save();painter.setRenderHint(QPainter.Antialiasing,True);metrics=painter.fontMetrics();w=min(option.rect.width()-10,metrics.horizontalAdvance(text)+18);h=24;rect=QRectF(option.rect.left()+5,option.rect.center().y()-h/2,w,h);path=QPainterPath();path.addRoundedRect(rect,5,5);painter.fillPath(path,QColor(bg));painter.setPen(QPen(QColor(fg)));painter.drawText(rect,Qt.AlignCenter,text);painter.restore()
