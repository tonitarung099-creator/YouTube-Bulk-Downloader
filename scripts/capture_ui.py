from __future__ import annotations
import os,sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.models.state import SourceInfo,VideoItem

app=QApplication(sys.argv);w=MainWindow();w.resize(1672,941)
items=[VideoItem(id=f"demo{i}",title=t,url=f"https://youtu.be/demo{i}",duration=210+i*30,kind="Video",upload_date=f"2026-09-{20+i:02d}") for i,t in enumerate(["Tutorial Editing Video Cepat dan Rapi","Cara Membuat Thumbnail Profesional","Workflow Kreator yang Lebih Efisien","Panduan Playlist YouTube","Tips Upload Video Berkualitas"])]
s=SourceInfo(id="fixture",title="Channel Contoh Indonesia",url="https://youtube.com/@contoh",source_type="channel",description="Fixture deterministik untuk membandingkan layout aplikasi dengan gambar referensi.",total_detected=5,playlist_count=2,shorts_count=0,items=items)
w.controller.state.source=s;w.controller.state.selected_ids={i.id for i in items};w._source_loaded(s);w.show();app.processEvents();out=Path("artifacts/ui-baseline.png");out.parent.mkdir(parents=True,exist_ok=True);w.grab().save(str(out));print(out.resolve())
