# Gemini Chat + Agent

Panel Gemini sekarang punya dua mode otomatis:

- **Chat**: pertanyaan biasa dijawab sebagai percakapan dan tidak mengubah pengaturan unduhan.
- **Aksi**: perintah seperti analisis, cari, download, pilih format, kualitas, subtitle, jeda, lanjut, dan batal diteruskan ke engine lokal yang aman.

Contoh:

- `Kamu bisa melakukan apa saja?`
- `Apa bedanya MP3 dan M4A?`
- `Carikan semua lagu Iwan Fals dan download semua sebagai MP3.`
- `Download playlist ini 1080p MP4.`
- `Jeda semua unduhan.`

Untuk pencarian tanpa URL, agent menggunakan pencarian YouTube lokal melalui yt-dlp. Kata `semua` memakai batas pencarian 100 hasil secara default; batas keras aplikasi 200 hasil.

Jawaban chat memiliki konteks percakapan pendek. Aksi tetap menggunakan schema terstruktur sehingga output AI tidak pernah dijalankan sebagai shell, Python, PowerShell, atau CMD.

Jika terjadi exception UI yang tidak tertangani, aplikasi mencatat detail ke `data/crash.log` agar error tidak hilang diam-diam.
