from __future__ import annotations
import webbrowser
from PySide6.QtCore import Qt,QSortFilterProxyModel,QRegularExpression
from PySide6.QtWidgets import QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QPushButton,QScrollArea,QTableView,QAbstractItemView,QSplitter,QStackedWidget,QLabel,QComboBox,QTextEdit,QHeaderView
from app.controllers.app_controller import AppController
from app.gui.models.video_table_model import VideoTableModel
from app.gui.theme import STYLESHEET
from app.gui.widgets.panels import TitleBar,Sidebar,SourceCard,DownloadSettings,ProgressPanel,GeminiPanel

class MainWindow(QMainWindow):
    def __init__(self,controller:AppController|None=None):
        super().__init__();self.controller=controller or AppController();self.setWindowTitle("Pengunduh YouTube Massal");self.setMinimumSize(980,650);self.resize(1672,941);self.setWindowFlags(Qt.FramelessWindowHint|Qt.Window);root=QWidget();root.setObjectName("Root");self.setCentralWidget(root);outer=QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);outer.addWidget(TitleBar(self));self.splitter=QSplitter(Qt.Horizontal);self.splitter.setChildrenCollapsible(False);outer.addWidget(self.splitter,1);self.sidebar=Sidebar();self.splitter.addWidget(self.sidebar);self.pages=QStackedWidget();self.pages.setMinimumWidth(560);self.splitter.addWidget(self.pages);self.home=self._build_home();self.pages.addWidget(self.home);self.extra_pages={}
        for name in ["Unduhan","Playlist","Channel","Riwayat","Pengaturan"]:p=self._build_extra(name);self.extra_pages[name]=p;self.pages.addWidget(p)
        self.ai=GeminiPanel();self.ai.setMinimumWidth(280);self.ai.setMaximumWidth(520);self.splitter.addWidget(self.ai);self.splitter.setSizes([205,1076,391]);self.setStyleSheet(STYLESHEET);self._wire();self.settings.load_intent(self.controller.state.intent);self._refresh_disk()
    def _build_home(self):
        scroll=QScrollArea();scroll.setWidgetResizable(True);canvas=QWidget();scroll.setWidget(canvas);l=QVBoxLayout(canvas);l.setContentsMargins(15,16,15,10);l.setSpacing(12);toolbar=QHBoxLayout();self.url=QLineEdit();self.url.setPlaceholderText("Tempel URL video, playlist, atau channel YouTube…");self.analyze_btn=QPushButton("Analisis");self.start_btn=QPushButton("Mulai Unduh");self.start_btn.setObjectName("Primary");toolbar.addWidget(self.url,1);toolbar.addWidget(self.analyze_btn);toolbar.addWidget(self.start_btn);l.addLayout(toolbar);self.source_card=SourceCard();l.addWidget(self.source_card);bar=QHBoxLayout();self.all_btn=QPushButton("Unduh Semua");self.list_btn=QPushButton("Tampilkan Daftar Video");self.partial_btn=QPushButton("Pilih Sebagian");self.filter=QComboBox();self.filter.addItems(["Semua jenis","Video","Shorts","Live"]);self.search=QLineEdit();self.search.setPlaceholderText("Cari video");self.search.setMaximumWidth(240)
        for w in (self.all_btn,self.list_btn,self.partial_btn):bar.addWidget(w)
        bar.addStretch();bar.addWidget(QLabel("Filter"));bar.addWidget(self.filter);bar.addWidget(self.search);l.addLayout(bar);self.model=VideoTableModel();self.proxy=QSortFilterProxyModel(self);self.proxy.setSourceModel(self.model);self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive);self.proxy.setFilterKeyColumn(3);self.table=QTableView();self.table.setModel(self.proxy);self.table.setAlternatingRowColors(True);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setSortingEnabled(True);self.table.verticalHeader().setVisible(False);self.table.verticalHeader().setDefaultSectionSize(58);self.table.setMinimumHeight(280);self.table.setMaximumHeight(360);self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch);l.addWidget(self.table);self.settings=DownloadSettings();l.addWidget(self.settings);self.progress=ProgressPanel();l.addWidget(self.progress);l.addStretch();return scroll
    def _build_extra(self,name):
        w=QWidget();l=QVBoxLayout(w);l.setContentsMargins(22,22,22,22);t=QLabel(name);t.setObjectName("Heading");l.addWidget(t);box=QTextEdit();box.setReadOnly(True);l.addWidget(box,1)
        if name=="Pengaturan":box.setHtml("<b>Gemini</b><br>API key dibaca dari GEMINI_API_KEYS / GEMINI_API_KEY dan tidak disimpan di repository.<br><br><b>Model</b><br>gemini-3.8-flash (dapat dioverride lewat GEMINI_MODEL).<br><br><b>Portable</b><br>Konfigurasi non-rahasia tersimpan di folder data aplikasi.")
        else:box.setPlainText("Belum ada data.")
        return w
    def _wire(self):
        self.sidebar.page_requested.connect(self._go_page);self.url.returnPressed.connect(self._analyze);self.analyze_btn.clicked.connect(self._analyze);self.list_btn.clicked.connect(self._analyze);self.start_btn.clicked.connect(lambda:self._start(False));self.all_btn.clicked.connect(lambda:self._start(True));self.partial_btn.clicked.connect(self._select_mode);self.search.textChanged.connect(self.proxy.setFilterFixedString);self.filter.currentTextChanged.connect(self._apply_filter);self.settings.changed.connect(lambda d:self.controller.update_intent(**d));self.progress.pause_clicked.connect(self.controller.pause);self.progress.resume_clicked.connect(self.controller.resume);self.progress.cancel_clicked.connect(self.controller.cancel);self.ai.send.connect(self.controller.interpret_ai);self.model.dataChanged.connect(self._sync_selected);self.controller.source_loaded.connect(self._source_loaded);self.controller.analysis_failed.connect(self._analysis_error);self.controller.job_changed.connect(self._job_changed);self.controller.ai_reply.connect(lambda text,_:self.ai.add_ai(text));self.controller.ai_status.connect(self.ai.status.setText);self.controller.state_changed.connect(self._state_changed);self.source_card.open_channel.connect(self._open_channel)
    def _go_page(self,name):self.pages.setCurrentIndex(["Beranda","Unduhan","Playlist","Channel","Riwayat","Pengaturan"].index(name));self._refresh_extra()
    def _analyze(self):self.analyze_btn.setEnabled(False);self.analyze_btn.setText("Menganalisis…");self.controller.analyze(self.url.text())
    def _source_loaded(self,s):self.analyze_btn.setEnabled(True);self.analyze_btn.setText("Analisis");self.source_card.set_source(s);self.model.set_items(s.items);self._sync_selected();self._apply_filter();self._refresh_extra()
    def _analysis_error(self,msg):self.analyze_btn.setEnabled(True);self.analyze_btn.setText("Analisis");self.source_card.title.setText("Analisis gagal");self.source_card.desc.setText(msg)
    def _start(self,all_items):
        if not self.controller.state.source:self._analyze();return
        n=self.controller.queue_selected(all_items=all_items);self.ai.add_ai(f"{n} video dimasukkan ke antrean sesuai filter Shorts/Live dan pengaturan aktif.")
    def _select_mode(self):self.table.setSelectionMode(QAbstractItemView.ExtendedSelection);self.ai.add_ai("Mode Pilih Sebagian aktif. Centang baris yang ingin diunduh, lalu tekan Mulai Unduh.")
    def _sync_selected(self,*_):self.controller.state.selected_ids={i.id for i in self.model.items if i.selected}
    def _apply_filter(self,*_):
        choice=self.filter.currentText()
        if choice!="Semua jenis":self.proxy.setFilterKeyColumn(5);self.proxy.setFilterRegularExpression(QRegularExpression(f"^{choice}$",QRegularExpression.CaseInsensitiveOption))
        else:self.proxy.setFilterKeyColumn(3);self.proxy.setFilterFixedString(self.search.text())
    def _job_changed(self,j):
        self.progress.set_job(j);self._refresh_extra()
        for item in self.model.items:
            if item.id==j.video.id:item.status=j.status
        if self.model.items:self.model.layoutChanged.emit()
    def _state_changed(self,state):
        if state.active_url and self.url.text()!=state.active_url:self.url.setText(state.active_url)
        self.settings.load_intent(state.intent);self._refresh_disk()
    def _refresh_disk(self):
        try:self.sidebar.set_disk(*self.controller.disk_stats())
        except Exception:pass
    def _refresh_extra(self):
        s=self.controller.state;jobs=s.jobs;self.extra_pages["Unduhan"].findChild(QTextEdit).setPlainText("\n".join(f"{j.video.title} — {j.status}" for j in jobs) or "Belum ada antrean.");src=s.source;self.extra_pages["Playlist"].findChild(QTextEdit).setPlainText(src.title if src and src.source_type=="playlist" else "Belum ada playlist dianalisis.");self.extra_pages["Channel"].findChild(QTextEdit).setPlainText(src.title if src and src.source_type=="channel" else "Belum ada channel dianalisis.");done=[j for j in jobs if str(j.status)=="completed"];self.extra_pages["Riwayat"].findChild(QTextEdit).setPlainText("\n".join(j.video.title for j in done) or "Belum ada unduhan selesai.")
    def _open_channel(self):
        s=self.controller.state.source
        if s and s.channel_url:webbrowser.open(s.channel_url)
