from __future__ import annotations

import os,sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow
from app.models.state import SourceInfo,VideoItem

app=QApplication(sys.argv)
w=MainWindow();w.resize(1672,941)
items=[VideoItem(id=f"demo{i}",title=t,url=f"https://youtu.be/demo{i}",duration=210+i*30,kind="Video",upload_date=f"2026-09-{20+i:02d}") for i,t in enumerate(["Tutorial Editing Video Cepat dan Rapi","Cara Membuat Thumbnail Profesional","Workflow Kreator yang Lebih Efisien","Panduan Playlist YouTube","Tips Upload Video Berkualitas"])]
s=SourceInfo(id="fixture",title="Channel Contoh Indonesia",url="https://youtube.com/@contoh",source_type="channel",description="Fixture deterministik untuk membandingkan layout aplikasi dengan gambar referensi.",total_detected=5,playlist_count=2,shorts_count=0,items=items)
w.controller.state.source=s;w.controller.state.selected_ids={i.id for i in items};w._source_loaded(s);w.show();app.processEvents()

out_dir=Path("artifacts");out_dir.mkdir(parents=True,exist_ok=True)
baseline_path=out_dir/"ui-baseline.png"
w.grab().save(str(baseline_path))

reference_path=Path("docs/reference/youtube-bulk-downloader-id.png")
reference=QImage(str(reference_path));baseline=QImage(str(baseline_path))
if reference.isNull() or baseline.isNull():
    raise SystemExit("Gagal membaca gambar referensi atau screenshot baseline.")

# Side-by-side: referensi kiri, hasil aplikasi kanan.
h=max(reference.height(),baseline.height());comparison=QImage(reference.width()+baseline.width(),h,QImage.Format_ARGB32);comparison.fill(Qt.black)
p=QPainter(comparison);p.drawImage(0,0,reference);p.drawImage(reference.width(),0,baseline);p.end();comparison.save(str(out_dir/"ui-comparison.png"))

# Overlay 50% untuk memudahkan melihat pergeseran panel utama.
scaled=baseline.scaled(reference.size(),Qt.IgnoreAspectRatio,Qt.SmoothTransformation);overlay=QImage(reference.size(),QImage.Format_ARGB32);overlay.fill(Qt.transparent)
p=QPainter(overlay);p.drawImage(0,0,reference);p.setOpacity(.5);p.drawImage(0,0,scaled);p.end();overlay.save(str(out_dir/"ui-overlay.png"))

print(f"baseline={baseline_path.resolve()}")
print(f"reference={reference.width()}x{reference.height()} baseline={baseline.width()}x{baseline.height()}")
print(f"comparison={(out_dir/'ui-comparison.png').resolve()}")
