# YouTube Bulk Downloader

Aplikasi Windows untuk mengunduh video yang memang kamu berhak unduh dari YouTube,
baik satu video, playlist, maupun channel, dengan `yt-dlp` sebagai engine lokal.

## Arah arsitektur

- **yt-dlp**: engine download.
- **FFmpeg**: merge/convert audio-video.
- **PySide6**: GUI Windows (tahap berikutnya).
- **Gemini Agent**: memahami bahasa manusia dan mengubahnya menjadi intent JSON.
- **Executor lokal**: hanya menjalankan aksi yang sudah didefinisikan aplikasi.
  Gemini tidak diberi akses shell.

Contoh perintah:

```text
download semua video channel ini 1080p, jangan shorts, sertakan subtitle
ambil playlist ini jadi audio mp3
cek isi channel ini dulu
download 720p dan jangan download ulang file yang sudah pernah selesai
```

Contoh hasil intent:

```json
{
  "action": "download",
  "source_type": "channel",
  "mode": "video",
  "quality": "1080p",
  "include_shorts": false,
  "include_subtitles": true,
  "use_archive": true
}
```

## Gemini

Gunakan `.env`:

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.8-flash
```

Bisa juga mengisi `GEMINI_API_KEYS` dengan beberapa API key resmi yang kamu miliki.
Agent membatasi daftar key maksimal 100 dan dapat berpindah key pada error kuota,
rate-limit, atau autentikasi. Jika Gemini tidak tersedia, parser lokal tetap mencoba
memahami perintah dasar.

## Menjalankan prototype

```bash
python -m pip install -e .
python main.py "download channel ini 1080p jangan shorts" --url "URL_CHANNEL"
```

Untuk benar-benar menjalankan download:

```bash
python main.py "download channel ini 1080p jangan shorts" --url "URL_CHANNEL" --execute
```

## Tahap berikutnya

1. Import/adapt fondasi GUI PySide6 dari `Plutoeat/yt-dlp-gui` dengan mempertahankan
   atribusi lisensi MIT yang diperlukan.
2. Buat tampilan modern Bahasa Indonesia.
3. Hubungkan kotak chat AI ke `GeminiLanguageAgent`.
4. Tampilkan preview intent sebelum eksekusi.
5. Queue, pause/resume, progress per video, archive, cookie/login, subtitle, thumbnail.
6. Packaging Windows portable ZIP beserta FFmpeg/yt-dlp yang dibutuhkan.
