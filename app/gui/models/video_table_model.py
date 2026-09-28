from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel,QModelIndex,Qt
from app.models.state import VideoItem

THUMBNAIL_ROLE=Qt.UserRole+1
DURATION_ROLE=Qt.UserRole+2
STATUS_ROLE=Qt.UserRole+3


class VideoTableModel(QAbstractTableModel):
    headers=["","#","Thumbnail","Judul Video","Durasi","Jenis","Tanggal","Status","⋯"]
    def __init__(self,items:list[VideoItem]|None=None,parent=None):super().__init__(parent);self.items=items or []
    def set_items(self,items):self.beginResetModel();self.items=list(items);self.endResetModel()
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.items)
    def columnCount(self,parent=QModelIndex()):return len(self.headers)
    def headerData(self,section,orientation,role=Qt.DisplayRole):return self.headers[section] if orientation==Qt.Horizontal and role==Qt.DisplayRole else None
    def data(self,index,role=Qt.DisplayRole):
        if not index.isValid():return None
        item=self.items[index.row()];col=index.column()
        if role==Qt.CheckStateRole and col==0:return Qt.Checked if item.selected else Qt.Unchecked
        if role==Qt.ToolTipRole and col==3:return item.title
        if role==THUMBNAIL_ROLE:return item.thumbnail
        if role==DURATION_ROLE:return item.duration
        if role==STATUS_ROLE:return str(item.status)
        if role!=Qt.DisplayRole:return None
        if col==1:return str(index.row()+1)
        if col==2:return ""
        if col==3:return item.title
        if col==4:
            if item.duration is None:return "—"
            m,s=divmod(int(item.duration),60);h,m=divmod(m,60);return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
        if col==5:return item.kind
        if col==6:return item.upload_date or "—"
        if col==7:return {"ready":"Siap diunduh","queued":"Dalam antrean","downloading":"Mengunduh","postprocessing":"Menggabungkan","pausing":"Menjeda","paused":"Dijeda","completed":"Selesai","failed":"Gagal","cancelled":"Dibatalkan","skipped":"Dilewati"}.get(str(item.status),str(item.status))
        if col==8:return "⋯"
    def flags(self,index):
        f=super().flags(index)
        if index.column()==0:f|=Qt.ItemIsUserCheckable
        return f
    def setData(self,index,value,role=Qt.EditRole):
        if index.column()==0 and role==Qt.CheckStateRole:self.items[index.row()].selected=value==Qt.Checked;self.dataChanged.emit(index,index,[Qt.CheckStateRole]);return True
        return False
