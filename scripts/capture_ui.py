from __future__ import annotations

import os,sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QColor,QFont,QImage,QPainter
from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow
from app.models.state import DownloadJob,JobStatus,SourceInfo,VideoItem

app=QApplication(sys.argv)
out_dir=Path("artifacts");out_dir.mkdir(parents=True,exist_ok=True);thumb_dir=out_dir/"fixture-thumbnails";thumb_dir.mkdir(exist_ok=True)

# Thumbnail fixture lokal: bukan gambar referensi dan tidak digunakan saat startup aplikasi normal.
thumb_paths=[]
for i,(bg,label) in enumerate((("#6A1722","LAPTOP"),("#16405E","WINDOWS"),("#5C4A13","PHONE"),("#224F45","EDITING"),("#4B293C","GADGET")),1):
    image=QImage(240,100,QImage.Format_ARGB32);image.fill(QColor(bg));p=QPainter(image);p.setPen(QColor("white"));font=QFont("Segoe UI",18,QFont.Bold);p.setFont(font);p.drawText(QRectF(10,10,220,80),Qt.AlignCenter,label);p.end();path=thumb_dir/f"thumb-{i}.png";image.save(str(path));thumb_paths.append(str(path.resolve()))

titles=["10 Rekomendasi Laptop Terbaik 2026 untuk Pelajar dan Kerja","Cara Setting Windows 11 Agar Lebih Cepat dan Ringan","Review Smartphone Terbaru — Masih Layak?","7 Tips Editing Video untuk Pemula","5 Gadget Murah Tapi Bagus di 2026"]
statuses=[JobStatus.READY,JobStatus.READY,JobStatus.QUEUED,JobStatus.QUEUED,JobStatus.QUEUED]
items=[VideoItem(id=f"demo{i}",title=title,url=f"https://youtu.be/demo{i}",duration=624+i*70,thumbnail=thumb_paths[i],kind="Video",upload_date=f"{2+i*3} jam lalu",status=statuses[i],selected=i<2) for i,title in enumerate(titles)]
source=SourceInfo(id="fixture",title="Channel Teknologi Indonesia",url="https://youtube.com/@contoh",source_type="channel",description="Review Gadget | Tutorial | Tips & Trik | Teknologi Indonesia",total_detected=1284,playlist_count=18,shorts_count=236,items=items)

w=MainWindow();w.resize(1672,941);w.controller.state.source=source;w.controller.state.selected_ids={item.id for item in items if item.selected};w.controller.state.intent.output_folder=r"D:\Download\YouTube";w._source_loaded(source);w.url.setText("https://www.youtube.com/@ChannelTeknologiIndonesia")
w.ai.status.setText("Online");w.ai.add_user("Unduh semua video dari channel ini dalam kualitas 1080p, tapi tanpa Shorts.");w.ai.add_ai("Perintah dipahami\nSumber: Channel YouTube\nKualitas: 1080p (MP4)\nTanpa Shorts");w.ai.add_user("Tambahkan juga subtitle bahasa Indonesia jika tersedia.");w.ai.add_ai("Perintah dipahami\nSubtitle: Indonesia (jika tersedia)\nKualitas tetap: 1080p")
job=DownloadJob(job_id="fixture-job",video=items[1],intent=w.controller.state.intent,status=JobStatus.DOWNLOADING,percent=66,downloaded_bytes=452*1024*1024,total_bytes=658*1024*1024,speed=8.4*1024*1024,eta=122);w.progress.set_job(job)
w.show();app.processEvents()

baseline_path=out_dir/"ui-baseline.png";w.grab().save(str(baseline_path))
reference_path=Path("docs/reference/youtube-bulk-downloader-id.png");reference=QImage(str(reference_path));baseline=QImage(str(baseline_path))
if reference.isNull() or baseline.isNull():raise SystemExit("Gagal membaca gambar referensi atau screenshot baseline.")

h=max(reference.height(),baseline.height());comparison=QImage(reference.width()+baseline.width(),h,QImage.Format_ARGB32);comparison.fill(Qt.black);p=QPainter(comparison);p.drawImage(0,0,reference);p.drawImage(reference.width(),0,baseline);p.end();comparison.save(str(out_dir/"ui-comparison.png"))
scaled=baseline.scaled(reference.size(),Qt.IgnoreAspectRatio,Qt.SmoothTransformation);overlay=QImage(reference.size(),QImage.Format_ARGB32);overlay.fill(Qt.transparent);p=QPainter(overlay);p.drawImage(0,0,reference);p.setOpacity(.5);p.drawImage(0,0,scaled);p.end();overlay.save(str(out_dir/"ui-overlay.png"))
print(f"baseline={baseline_path.resolve()}");print(f"reference={reference.width()}x{reference.height()} baseline={baseline.width()}x{baseline.height()}");print(f"comparison={(out_dir/'ui-comparison.png').resolve()}")
