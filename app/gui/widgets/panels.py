from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QButtonGroup,QCheckBox,QComboBox,QFileDialog,QFrame,QGridLayout,QHBoxLayout,QLabel,
    QLineEdit,QProgressBar,QPushButton,QSpinBox,QTextEdit,QVBoxLayout,QWidget,
)

from app.gui.icons import make_icon
from app.gui.theme import COLORS


def human_bytes(n):
    if n is None:
        return "—"
    x=float(n)
    for unit in ("B","KB","MB","GB","TB"):
        if x<1024 or unit=="TB":
            return f"{x:.1f} {unit}"
        x/=1024


class CommandTextEdit(QTextEdit):
    submit_requested=Signal()
    def keyPressEvent(self,e:QKeyEvent):
        if e.key() in {Qt.Key_Return,Qt.Key_Enter} and not (e.modifiers()&Qt.ShiftModifier):
            e.accept();self.submit_requested.emit();return
        super().keyPressEvent(e)


class TitleBar(QWidget):
    def __init__(self,window):
        super().__init__();self.setObjectName("TitleBar");self.setFixedHeight(40);self._w=window;self._drag=None
        layout=QHBoxLayout(self);layout.setContentsMargins(10,0,5,0)
        logo=QLabel();logo.setPixmap(make_icon("play",22).pixmap(22,22));logo.setFixedSize(24,24);layout.addWidget(logo)
        title=QLabel("Pengunduh YouTube Massal");title.setStyleSheet("font-weight:600");layout.addWidget(title);layout.addStretch()
        for text,callback in (("—",window.showMinimized),("□",self._toggle),("×",window.close)):
            button=QPushButton(text);button.setFixedSize(42,30);button.clicked.connect(callback);layout.addWidget(button)
    def _toggle(self):self._w.showNormal() if self._w.isMaximized() else self._w.showMaximized()
    def mousePressEvent(self,e:QMouseEvent):
        if e.button()==Qt.LeftButton:self._drag=e.globalPosition().toPoint()-self._w.frameGeometry().topLeft()
    def mouseMoveEvent(self,e:QMouseEvent):
        if self._drag is not None and e.buttons()&Qt.LeftButton and not self._w.isMaximized():self._w.move(e.globalPosition().toPoint()-self._drag)
    def mouseReleaseEvent(self,e):self._drag=None
    def mouseDoubleClickEvent(self,e):
        if e.button()==Qt.LeftButton:self._toggle()


class Sidebar(QWidget):
    page_requested=Signal(str)
    def __init__(self):
        super().__init__();self.setObjectName("Sidebar");self.setMinimumWidth(170);self.setMaximumWidth(260)
        layout=QVBoxLayout(self);layout.setContentsMargins(10,16,10,14);layout.setSpacing(4)
        entries=[("Beranda","home"),("Unduhan","download"),("Playlist","playlist"),("Channel","channel"),("Riwayat","history"),("Pengaturan","settings")]
        for i,(name,icon_name) in enumerate(entries):
            button=QPushButton(name);button.setIcon(make_icon(icon_name,19,"#ADBECD" if i else "#FF4962"));button.setIconSize(__import__('PySide6.QtCore',fromlist=['QSize']).QSize(19,19));button.setObjectName("Nav");button.setCheckable(True);button.setAutoExclusive(True);button.setChecked(i==0);button.clicked.connect(lambda _=False,n=name:self.page_requested.emit(n));layout.addWidget(button)
        layout.addStretch();card=QFrame();card.setObjectName("Panel");content=QVBoxLayout(card);head=QHBoxLayout();storage_icon=QLabel();storage_icon.setPixmap(make_icon("download",17).pixmap(17,17));head.addWidget(storage_icon);head.addWidget(QLabel("Penyimpanan"));head.addStretch();content.addLayout(head);self.disk_label=QLabel("Memuat…");self.disk_label.setObjectName("Muted");content.addWidget(self.disk_label);self.disk=QProgressBar();self.disk.setTextVisible(False);content.addWidget(self.disk);layout.addWidget(card)
    def set_disk(self,used,total,percent):self.disk.setValue(percent);self.disk_label.setText(f"{human_bytes(used)} / {human_bytes(total)} terpakai ({percent}%)")


class SourceCard(QFrame):
    open_channel=Signal()
    def __init__(self):
        super().__init__();self.setObjectName("Panel");self.setMinimumHeight(118);layout=QHBoxLayout(self);layout.setContentsMargins(14,12,14,12)
        self.avatar=QLabel("YT");self.avatar.setAlignment(Qt.AlignCenter);self.avatar.setFixedSize(58,58);self.avatar.setStyleSheet("background:#263744;border-radius:8px;font-weight:700");layout.addWidget(self.avatar)
        text=QVBoxLayout();self.kind=QLabel("Jenis  —");self.kind.setObjectName("Muted");self.title=QLabel("Masukkan URL untuk memulai");self.title.setObjectName("Heading");self.desc=QLabel("Analisis metadata tidak akan mengunduh video.");self.desc.setObjectName("Muted");self.desc.setWordWrap(True);text.addWidget(self.kind);text.addWidget(self.title);text.addWidget(self.desc);layout.addLayout(text,1)
        stats=QGridLayout();self.total=QLabel("—");self.playlists=QLabel("—");self.shorts=QLabel("—")
        for row,(label,value) in enumerate((("Total video",self.total),("Playlist",self.playlists),("Shorts",self.shorts))):
            muted=QLabel(label);muted.setObjectName("Muted");stats.addWidget(muted,row,0);stats.addWidget(value,row,1)
        layout.addLayout(stats);button=QPushButton("Lihat Channel");button.clicked.connect(self.open_channel.emit);layout.addWidget(button)
    def set_source(self,s):
        self.kind.setText(f"Jenis  {str(s.source_type).capitalize()}");self.title.setText(s.title);self.desc.setText((s.description or "Tidak ada deskripsi.")[:220]);self.total.setText("—" if s.total_detected is None else str(s.total_detected));self.playlists.setText("—" if s.playlist_count is None else str(s.playlist_count));self.shorts.setText("—" if s.shorts_count is None else str(s.shorts_count))


class DownloadSettings(QFrame):
    changed=Signal(dict)
    def __init__(self):
        super().__init__();self.setObjectName("Panel");root=QVBoxLayout(self);root.setContentsMargins(14,10,14,12)
        heading=QHBoxLayout();gear=QLabel();gear.setPixmap(make_icon("settings",18).pixmap(18,18));heading.addWidget(gear);title=QLabel("Pengaturan Unduhan");title.setObjectName("Heading");heading.addWidget(title);heading.addStretch();root.addLayout(heading)
        grid=QGridLayout();root.addLayout(grid);grid.addWidget(QLabel("Kualitas video"),0,0);qbox=QHBoxLayout();self.qgroup=QButtonGroup(self);self.qgroup.setExclusive(True)
        for q,label in (("best","Terbaik"),("1080p","1080p"),("720p","720p"),("audio","Audio saja")):
            b=QPushButton(label);b.setCheckable(True);b.setProperty("value",q);self.qgroup.addButton(b);qbox.addWidget(b);b.clicked.connect(self._emit);b.setChecked(q=="1080p")
        grid.addLayout(qbox,0,1);grid.addWidget(QLabel("Format video"),1,0);self.video=QComboBox();self.video.addItems(["MP4","MKV","WebM"]);self.video.currentTextChanged.connect(self._emit);grid.addWidget(self.video,1,1)
        grid.addWidget(QLabel("Format audio"),2,0);self.audio=QComboBox();self.audio.addItems(["MP3","M4A","Opus","Terbaik"]);self.audio.currentTextChanged.connect(self._emit);grid.addWidget(self.audio,2,1)
        grid.addWidget(QLabel("Folder output"),3,0);path=QHBoxLayout();self.folder=QLineEdit();self.folder.editingFinished.connect(self._emit);choose=QPushButton("Pilih");choose.setIcon(make_icon("settings",16));choose.clicked.connect(self._choose);path.addWidget(self.folder,1);path.addWidget(choose);grid.addLayout(path,3,1)
        right=QGridLayout();self.parallel=QSpinBox();self.parallel.setRange(1,10);self.parallel.setValue(5);self.parallel.valueChanged.connect(self._emit);right.addWidget(QLabel("Unduhan paralel"),0,0);right.addWidget(self.parallel,0,1)
        self.archive=QCheckBox("Jangan unduh ulang");self.subtitle=QCheckBox("Unduh subtitle");self.thumb=QCheckBox("Unduh thumbnail");self.meta=QCheckBox("Simpan metadata");self.shorts=QCheckBox("Sertakan Shorts");self.live=QCheckBox("Sertakan Live")
        for i,w in enumerate([self.archive,self.subtitle,self.thumb,self.meta,self.shorts,self.live],1):right.addWidget(w,(i+1)//2,(i+1)%2);w.stateChanged.connect(self._emit)
        for w in [self.archive,self.subtitle,self.thumb,self.meta]:w.setChecked(True)
        grid.addLayout(right,0,2,4,1)
    def _choose(self):
        p=QFileDialog.getExistingDirectory(self,"Pilih folder output",self.folder.text() or str(Path.home()))
        if p:self.folder.setText(p);self._emit()
    def _emit(self,*_):
        b=self.qgroup.checkedButton();q=b.property("value") if b else "1080p";mode="audio" if q=="audio" else "video";self.changed.emit({"mode":mode,"quality":"best" if q=="audio" else q,"video_format":self.video.currentText().lower(),"audio_format":"best" if self.audio.currentText()=="Terbaik" else self.audio.currentText().lower(),"output_folder":self.folder.text() or None,"concurrent_downloads":self.parallel.value(),"use_archive":self.archive.isChecked(),"include_subtitles":self.subtitle.isChecked(),"include_thumbnail":self.thumb.isChecked(),"include_metadata":self.meta.isChecked(),"include_shorts":self.shorts.isChecked(),"include_live":self.live.isChecked()})
    def load_intent(self,i):
        controls=[self.folder,self.parallel,self.video,self.audio,self.archive,self.subtitle,self.thumb,self.meta,self.shorts,self.live,*self.qgroup.buttons()];previous=[w.blockSignals(True) for w in controls]
        try:
            self.folder.setText(i.output_folder or "");self.parallel.setValue(i.concurrent_downloads);self.archive.setChecked(i.use_archive);self.subtitle.setChecked(i.include_subtitles);self.thumb.setChecked(i.include_thumbnail);self.meta.setChecked(i.include_metadata);self.shorts.setChecked(i.include_shorts);self.live.setChecked(i.include_live);self.video.setCurrentText(i.video_format.upper() if i.video_format!="best" else "MP4");self.audio.setCurrentText({"mp3":"MP3","m4a":"M4A","opus":"Opus","best":"Terbaik"}.get(i.audio_format,"Terbaik"))
            for b in self.qgroup.buttons():b.setChecked((i.mode=="audio" and b.property("value")=="audio") or (i.mode=="video" and b.property("value")==i.quality))
        finally:
            for w,old in zip(controls,previous):w.blockSignals(old)


class ProgressPanel(QFrame):
    pause_clicked=Signal();resume_clicked=Signal();cancel_clicked=Signal()
    def __init__(self):
        super().__init__();self.setObjectName("Panel");layout=QVBoxLayout(self);top=QHBoxLayout();download_icon=QLabel();download_icon.setPixmap(make_icon("download",17,"#FF4962").pixmap(17,17));top.addWidget(download_icon);self.title=QLabel("Belum ada unduhan aktif");self.percent=QLabel("0%");top.addWidget(self.title,1);top.addWidget(self.percent);layout.addLayout(top);self.bar=QProgressBar();self.bar.setTextVisible(False);layout.addWidget(self.bar);bottom=QHBoxLayout();self.detail=QLabel("Siap");self.detail.setObjectName("Muted");bottom.addWidget(self.detail,1);self.pause=QPushButton("Jeda");self.resume=QPushButton("Lanjutkan");self.cancel=QPushButton("Batalkan");self.pause.clicked.connect(self.pause_clicked);self.resume.clicked.connect(self.resume_clicked);self.cancel.clicked.connect(self.cancel_clicked);bottom.addWidget(self.pause);bottom.addWidget(self.resume);bottom.addWidget(self.cancel);layout.addLayout(bottom)
    def set_job(self,j):
        self.title.setText(j.video.title);p=int(j.percent or 0);self.bar.setValue(p);self.percent.setText(f"{p}%" if j.percent is not None else "—");speed=f" • {human_bytes(j.speed)}/s" if j.speed else "";eta=f" • Sisa {int(j.eta)} dtk" if j.eta is not None else "";self.detail.setText(f"{str(j.status).replace('_',' ').title()}  {human_bytes(j.downloaded_bytes)} / {human_bytes(j.total_bytes)}{speed}{eta}");self.pause.setEnabled(str(j.status) in {"queued","downloading"});self.resume.setEnabled(str(j.status)=="paused");self.cancel.setEnabled(str(j.status) not in {"completed","cancelled"})


class GeminiPanel(QWidget):
    send=Signal(str)
    def __init__(self):
        super().__init__();self.setObjectName("GeminiPanel");layout=QVBoxLayout(self);head=QHBoxLayout();spark=QLabel();spark.setPixmap(make_icon("sparkle",19).pixmap(19,19));name=QLabel("Agen AI Gemini");name.setObjectName("Heading");self.status=QLabel("Belum dikonfigurasi");self.status.setObjectName("Muted");head.addWidget(spark);head.addWidget(name);head.addStretch();head.addWidget(self.status);layout.addLayout(head);description=QLabel("Pahami perintah bahasa manusia, lalu engine lokal yang bekerja.");description.setWordWrap(True);description.setObjectName("Muted");layout.addWidget(description);self.chat=QTextEdit();self.chat.setReadOnly(True);layout.addWidget(self.chat,1);row=QHBoxLayout();self.input=CommandTextEdit();self.input.setFixedHeight(46);self.input.setPlaceholderText("Ketik perintah…");self.input.submit_requested.connect(self._send);button=QPushButton("Kirim");button.setObjectName("Primary");button.setFixedHeight(46);button.clicked.connect(self._send);row.addWidget(self.input,1);row.addWidget(button);layout.addLayout(row)
    def _send(self):
        text=self.input.toPlainText().strip()
        if not text:return
        self.add_user(text);self.input.clear();self.send.emit(text)
    def add_user(self,text):self.chat.append(f"<p align='right'><b>Anda</b><br>{text}</p>")
    def add_ai(self,text):self.chat.append(f"<p><span style='color:{COLORS['cyan']}'><b>Gemini</b></span><br>{text.replace(chr(10),'<br>')}</p>")
