# Pengunduh YouTube Massal

Aplikasi Windows desktop untuk menganalisis dan mengunduh video, playlist, atau channel YouTube secara massal dengan antarmuka PySide6 berbahasa Indonesia. Gemini hanya menerjemahkan bahasa manusia menjadi intent terstruktur; seluruh analisis, antrean, dan unduhan tetap dijalankan engine lokal.

## Fitur
- UI tiga kolom mengikuti `docs/reference/youtube-bulk-downloader-id.png`: sidebar, workspace, Agen AI Gemini.
- Video/playlist/channel, tabel seleksi, pencarian/filter, progres, antrean paralel video, jeda/lanjut/batal.
- 1080p sebagai batas maksimum yang ketat, mode audio, subtitle/thumbnail/metadata, archive anti-duplikat.
- Gemini sampai 100 API key dengan rotasi; tanpa key tetap ada parser lokal. Model default `gemini-3.8-flash` dapat diubah lewat `GEMINI_MODEL`.
- CLI lama tetap tersedia: `python main.py "cek URL" --url <URL>`; tanpa argumen membuka GUI.
- Build Windows `onedir` + ZIP portable dan FFmpeg/ffprobe melalui GitHub Actions.

## Menjalankan dari source
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install ".[gui,dev]"
python main.py
```
Salin `.env.example` ke `.env` bila memakai Gemini. Jangan commit API key.

## Build portable Windows
```powershell
pip install ".[gui,dev]"
.\scripts\build_windows.ps1
```
Hasil: `release/Pengunduh-YouTube-Massal-Windows-portable.zip`.

## Batasan
Jeda menghentikan transfer melalui hook yt-dlp dan resume menjadwalkan ulang dengan `.part`; keberhasilan resume byte-perfect tetap bergantung server/protokol. Klasifikasi Shorts dari ekstraksi flat bisa belum diketahui sampai metadata video lengkap tersedia. Gunakan aplikasi hanya untuk konten yang memang berhak Anda unduh.
