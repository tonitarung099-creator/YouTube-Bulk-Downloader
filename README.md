# Pengunduh YouTube Massal

Aplikasi Windows desktop untuk menganalisis dan mengunduh video, playlist, atau channel YouTube secara massal dengan antarmuka PySide6 berbahasa Indonesia. Gemini hanya menerjemahkan bahasa manusia menjadi intent terstruktur; seluruh analisis, antrean, dan unduhan tetap dijalankan engine lokal.

## Fitur
- UI tiga kolom mengikuti `docs/reference/youtube-bulk-downloader-id.png`: sidebar, workspace, Agen AI Gemini.
- Video/playlist/channel, tabel seleksi, pencarian/filter, progres, antrean paralel video, jeda/lanjut/batal.
- 1080p sebagai batas maksimum yang ketat, mode audio, subtitle/thumbnail/metadata, archive anti-duplikat.
- Gemini sampai 100 API key dengan rotasi; tanpa key tetap ada parser lokal. Model default `gemini-3.8-flash` dapat diubah lewat `GEMINI_MODEL`.
- CLI lama tetap tersedia: `python main.py "cek URL" --url <URL>`; tanpa argumen membuka GUI.
- Build Windows `onedir` + ZIP portable dengan FFmpeg, ffprobe, QuickJS-NG, verifikasi isi ZIP, dan smoke-test EXE hasil ekstrak.

## Menjalankan dari source
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install ".[gui,dev]"
python main.py
```
Salin `.env.example` ke `.env` bila memakai Gemini. Jangan commit API key.

## Jika YouTube meminta verifikasi/cookie
Pada sebagian jaringan atau IP, YouTube dapat menampilkan pesan seperti **"Sign in to confirm you're not a bot"**. Aplikasi mendukung cookie Netscape secara opsional untuk kasus tersebut.

Cara paling sederhana pada versi portable:
1. Extract ZIP aplikasi.
2. Simpan file cookie dengan nama `youtube-cookies.txt` di folder `data` di sebelah EXE.
3. Buka ulang aplikasi. Cookie otomatis dipakai saat **Analisis** maupun **Unduh**.

Alternatif untuk source/developer: set environment variable `YOUTUBE_COOKIES_FILE` ke lokasi file cookie. Variabel ini memiliki prioritas lebih tinggi daripada `data/youtube-cookies.txt`.

**Jangan commit, upload, atau membagikan file cookie.** Folder `data/` sudah diabaikan Git. Gunakan cookie hanya dari akun/perangkat milik Anda sendiri.

## Runtime JavaScript YouTube
YouTube modern memakai challenge JavaScript yang perlu dijalankan yt-dlp. Portable membundel **QuickJS-NG** (`tools/qjs.exe`) sebagai runtime utama karena ukurannya jauh lebih kecil daripada Deno namun tetap didukung resmi oleh yt-dlp EJS. Build mem-pin versi QuickJS-NG dan memverifikasi SHA-256 binary sebelum dimasukkan ke ZIP.

Kode tetap mengenali `tools/deno.exe` sebagai fallback untuk kompatibilitas dengan folder portable lama/source, tetapi build rilis baru tidak lagi membundel Deno.

## Build portable Windows
```powershell
pip install ".[gui,dev]"
.\scripts\build_windows.ps1
```
Hasil: `release/Pengunduh-YouTube-Massal-Windows-portable.zip`.

Build utama memvalidasi struktur ZIP, runtime PyInstaller, FFmpeg/ffprobe/QuickJS-NG, checksum QuickJS, tidak adanya Deno/test dependency yang tidak perlu, serta startup EXE. Tes jaringan YouTube dijalankan terpisah sebagai diagnostik non-blocking karena IP GitHub Actions dapat dibatasi YouTube walaupun aplikasi lokal sehat.

## Batasan
Jeda menghentikan transfer melalui hook yt-dlp dan resume menjadwalkan ulang dengan `.part`; keberhasilan resume byte-perfect tetap bergantung server/protokol. Klasifikasi Shorts dari ekstraksi flat bisa belum diketahui sampai metadata video lengkap tersedia. Gunakan aplikasi hanya untuk konten yang memang berhak Anda unduh.
