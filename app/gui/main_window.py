from __future__ import annotations

import webbrowser
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QScrollArea,QTableView,
    QAbstractItemView,QSplitter,QStackedWidget,QLabel,QTextEdit,QHeaderView,QComboBox
)

from app.controllers.app_controller import AppController
from app.gui.delegates.video_delegates import StatusBadgeDelegate,ThumbnailDelegate
from app.gui.models.video_table_model import VideoTableModel
from app.gui.models.video_filter_proxy import VideoFilterProxyModel
from app.gui.theme import STYLESHEET
from app.gui.widgets.checkable_header import CheckableHeader
from app.gui.widgets.panels import TitleBar,Sidebar,SourceCard,DownloadSettings,ProgressPanel,GeminiPanel


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController | None = None):
        super().__init__(); self.controller=controller or AppController(); self.setWindowTitle("Pengunduh YouTube Massal")
        self.setMinimumSize(980,650); self.resize(1672,941); self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        root=QWidget(); root.setObjectName("Root"); self.setCentralWidget(root); outer=QVBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0); outer.addWidget(TitleBar(self))
        self.splitter=QSplitter(Qt.Horizontal); self.splitter.setChildrenCollapsible(False); outer.addWidget(self.splitter,1)
        self.sidebar=Sidebar(); self.splitter.addWidget(self.sidebar)
        self.pages=QStackedWidget(); self.pages.setMinimumWidth(560); self.splitter.addWidget(self.pages)
        self.home=self._build_home(); self.pages.addWidget(self.home)
        self.extra_pages={}
        for name in ["Unduhan","Playlist","Channel","Riwayat","Pengaturan"]:
            page=self._build_extra(name); self.extra_pages[name]=page; self.pages.addWidget(page)
        self.ai=GeminiPanel(); self.ai.setMinimumWidth(280); self.ai.setMaximumWidth(520); self.splitter.addWidget(self.ai); self.splitter.setSizes([205,1076,391])
        self.setStyleSheet(STYLESHEET)
        self._wire(); self.settings.load_intent(self.controller.state.intent); self._refresh_disk()

    def _build_home(self):
        scroll=QScrollArea();scroll.setObjectName("WorkspaceScroll");scroll.viewport().setObjectName("WorkspaceViewport");scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        canvas=QWidget();canvas.setObjectName("Workspace");scroll.setWidget(canvas);lay=QVBoxLayout(canvas);lay.setContentsMargins(15,16,15,10);lay.setSpacing(12)
        toolbar=QHBoxLayout(); self.url=QLineEdit(); self.url.setPlaceholderText("Tempel URL video, playlist, atau channel YouTube…"); self.analyze_btn=QPushButton("Analisis"); self.start_btn=QPushButton("Mulai Unduh"); self.start_btn.setObjectName("Primary"); toolbar.addWidget(self.url,1); toolbar.addWidget(self.analyze_btn); toolbar.addWidget(self.start_btn); lay.addLayout(toolbar)
        self.source_card=SourceCard(); lay.addWidget(self.source_card)
        listbar=QHBoxLayout(); self.all_btn=QPushButton("Unduh Semua"); self.list_btn=QPushButton("Tampilkan Daftar Video"); self.partial_btn=QPushButton("Pilih Sebagian"); self.filter=QComboBox(); self.filter.addItems(["Semua jenis","Video","Shorts","Live"]); self.search=QLineEdit(); self.search.setPlaceholderText("Cari video"); self.search.setMaximumWidth(240)
        for w in (self.all_btn,self.list_btn,self.partial_btn): listbar.addWidget(w)
        listbar.addStretch(); listbar.addWidget(QLabel("Filter")); listbar.addWidget(self.filter); listbar.addWidget(self.search); lay.addLayout(listbar)
        self.model=VideoTableModel(); self.proxy=VideoFilterProxyModel(self); self.proxy.setSourceModel(self.model)
        self.table=QTableView(); self.table.setModel(self.proxy);self.header=CheckableHeader(Qt.Horizontal,self.table);self.table.setHorizontalHeader(self.header); self.table.setAlternatingRowColors(True); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setSortingEnabled(True); self.table.verticalHeader().setVisible(False); self.table.verticalHeader().setDefaultSectionSize(58); self.table.setMinimumHeight(328); self.table.setMaximumHeight(350)
        self.thumbnail_delegate=ThumbnailDelegate(self.table);self.status_delegate=StatusBadgeDelegate(self.table);self.table.setItemDelegateForColumn(2,self.thumbnail_delegate);self.table.setItemDelegateForColumn(7,self.status_delegate)
        hdr=self.table.horizontalHeader(); hdr.setSectionResizeMode(3,QHeaderView.Stretch)
        for c,w in {0:34,1:38,2:133,4:72,5:72,6:88,7:118,8:38}.items(): hdr.resizeSection(c,w)
        lay.addWidget(self.table)
        self.settings=DownloadSettings(); lay.addWidget(self.settings)
        self.progress=ProgressPanel(); lay.addWidget(self.progress); lay.addStretch(1)
        return scroll

    def _build_extra(self,name):
        w=QWidget();w.setObjectName("Workspace");lay=QVBoxLayout(w); lay.setContentsMargins(22,22,22,22); title=QLabel(name); title.setObjectName("Heading"); lay.addWidget(title)
        box=QTextEdit(); box.setReadOnly(True); box.setObjectName(f"{name}Text"); lay.addWidget(box,1)
        if name=="Pengaturan":
            box.setHtml("<b>Gemini</b><br>API key dibaca dari GEMINI_API_KEYS / GEMINI_API_KEY dan tidak disimpan di repository.<br><br><b>Model</b><br>gemini-3.8-flash (dapat dioverride lewat GEMINI_MODEL).<br><br><b>Portable</b><br>Konfigurasi non-rahasia tersimpan di folder data aplikasi.")
        else: box.setPlainText("Belum ada data.")
        return w

    def _wire(self):
        self.sidebar.page_requested.connect(self._go_page); self.url.returnPressed.connect(self._analyze); self.analyze_btn.clicked.connect(self._analyze); self.list_btn.clicked.connect(self._analyze); self.start_btn.clicked.connect(lambda:self._start(False)); self.all_btn.clicked.connect(lambda:self._start(True)); self.partial_btn.clicked.connect(self._select_mode)
        self.search.textChanged.connect(self.proxy.set_search); self.filter.currentTextChanged.connect(self._apply_filter); self.settings.changed.connect(lambda d:self.controller.update_intent(**d)); self.progress.pause_clicked.connect(self.controller.pause); self.progress.resume_clicked.connect(self.controller.resume); self.progress.cancel_clicked.connect(self.controller.cancel); self.ai.send.connect(self.controller.interpret_ai); self.model.dataChanged.connect(self._sync_selected);self.model.dataChanged.connect(lambda *_:self.header.viewport().update())
        self.controller.source_loaded.connect(self._source_loaded); self.controller.analysis_failed.connect(self._analysis_error); self.controller.job_changed.connect(self._job_changed); self.controller.ai_reply.connect(lambda text,_:self.ai.add_ai(text)); self.controller.ai_status.connect(self.ai.status.setText); self.controller.state_changed.connect(self._state_changed); self.source_card.open_channel.connect(self._open_channel)

    def _go_page(self,name):
        names=["Beranda","Unduhan","Playlist","Channel","Riwayat","Pengaturan"]; self.pages.setCurrentIndex(names.index(name)); self._refresh_extra()
    def _analyze(self):
        self.analyze_btn.setEnabled(False); self.analyze_btn.setText("Menganalisis…"); self.controller.analyze(self.url.text())
    def _source_loaded(self,s):
        self.analyze_btn.setEnabled(True); self.analyze_btn.setText("Analisis"); self.source_card.set_source(s); self.model.set_items(s.items); self._sync_selected(); self._apply_filter();self.header.viewport().update(); self._refresh_extra()
    def _analysis_error(self,msg):
        self.analyze_btn.setEnabled(True); self.analyze_btn.setText("Analisis"); self.source_card.title.setText("Analisis gagal"); self.source_card.desc.setText(msg)
    def _start(self,all_items):
        if not self.controller.state.source:
            self._analyze(); return
        n=self.controller.queue_selected(all_items=all_items); self.ai.add_ai(f"{n} video dimasukkan ke antrean sesuai filter Shorts/Live dan pengaturan aktif.")
    def _select_mode(self):
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for item in self.model.items:item.selected=False
        if self.model.items:
            top=self.model.index(0,0);bottom=self.model.index(len(self.model.items)-1,0);self.model.dataChanged.emit(top,bottom,[Qt.CheckStateRole])
        self._sync_selected();self.header.viewport().update();self.ai.add_ai("Mode Pilih Sebagian aktif. Pilihan dikosongkan; centang video yang ingin diunduh, lalu tekan Mulai Unduh.")
    def _sync_selected(self,*_): self.controller.state.selected_ids={i.id for i in self.model.items if i.selected}
    def _apply_filter(self,*_):
        choice=self.filter.currentText();self.proxy.set_kind(None if choice=="Semua jenis" else choice);self.proxy.set_search(self.search.text());self.header.viewport().update()
    def _job_changed(self,j):
        self.progress.set_job(j); self._refresh_extra()
        for item in self.model.items:
            if item.id==j.video.id: item.status=j.status
        if self.model.items: self.model.layoutChanged.emit()
    def _state_changed(self,state):
        if state.active_url and self.url.text()!=state.active_url: self.url.setText(state.active_url)
        self.settings.load_intent(state.intent); self._refresh_disk()
    def _refresh_disk(self):
        try:self.sidebar.set_disk(*self.controller.disk_stats())
        except Exception: pass
    def _refresh_extra(self):
        state=self.controller.state; jobs=state.jobs
        self.extra_pages["Unduhan"].findChild(QTextEdit).setPlainText("\n".join(f"{j.video.title} — {j.status}" for j in jobs) or "Belum ada antrean.")
        src=state.source;self.extra_pages["Playlist"].findChild(QTextEdit).setPlainText(src.title if src and src.source_type=="playlist" else "Belum ada playlist dianalisis.");self.extra_pages["Channel"].findChild(QTextEdit).setPlainText(src.title if src and src.source_type=="channel" else "Belum ada channel dianalisis.")
        completed=[j for j in jobs if str(j.status)=="completed"];self.extra_pages["Riwayat"].findChild(QTextEdit).setPlainText("\n".join(j.video.title for j in completed) or "Belum ada unduhan selesai.")
    def _open_channel(self):
        s=self.controller.state.source
        if s and s.channel_url: webbrowser.open(s.channel_url)
