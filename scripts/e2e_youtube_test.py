from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import app.core.paths as app_paths
from app.core.downloader import YouTubeDownloader
from app.models.commands import DownloadIntent

# Fixture yang saat ini dipakai oleh suite extractor YouTube milik yt-dlp.
TEST_URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4&t=1s&end=9"
EXPECTED_ID = "YE7VzlLtp-4"


def main() -> int:
    parser = argparse.ArgumentParser(description="Uji end-to-end YouTube memakai tool portable hasil build.")
    parser.add_argument("--tools-dir", type=Path, required=True)
    args = parser.parse_args()

    tools_dir = args.tools_dir.resolve()
    required_tools = [tools_dir / "ffmpeg.exe", tools_dir / "ffprobe.exe", tools_dir / "qjs.exe"]
    missing = [str(p) for p in required_tools if not p.is_file()]
    if missing:
        raise RuntimeError(f"Tool portable tidak lengkap untuk E2E: {missing}")

    # Arahkan resolver tool source-mode ke tool yang benar-benar berasal dari ZIP portable.
    app_paths.tools_dir = lambda: tools_dir

    workdir = Path(tempfile.mkdtemp(prefix="youtube-bulk-e2e-"))
    try:
        downloader = YouTubeDownloader(workdir)
        source = downloader.analyze(TEST_URL)
        if source.get("id") != EXPECTED_ID:
            raise RuntimeError(f"ID metadata tidak sesuai: {source.get('id')!r}")
        if source.get("type") != "video":
            raise RuntimeError(f"Jenis sumber bukan video: {source.get('type')!r}")

        intent = DownloadIntent(
            action="download",
            source_type="video",
            url=TEST_URL,
            mode="video",
            quality="360p",
            video_format="mp4",
            include_shorts=True,
            include_live=False,
            include_subtitles=False,
            include_thumbnail=False,
            include_metadata=False,
            use_archive=False,
            concurrent_downloads=1,
            fragment_downloads=1,
            output_folder=str(workdir),
        )

        events: list[str] = []
        code = downloader.download(intent, lambda data: events.append(str(data.get("status") or "")))
        if code != 0:
            raise RuntimeError(f"yt-dlp mengembalikan kode {code}")

        media_exts = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
        media = [
            p for p in workdir.rglob("*")
            if p.is_file() and p.suffix.lower() in media_exts and p.stat().st_size > 1024
        ]
        if not media:
            files = [str(p.relative_to(workdir)) for p in workdir.rglob("*") if p.is_file()]
            raise RuntimeError(f"Tidak ada file media hasil unduhan. Isi: {files}")
        if "finished" not in events:
            raise RuntimeError(f"Progress hook tidak pernah menerima status finished: {events}")

        largest = max(media, key=lambda p: p.stat().st_size)
        print(f"E2E YouTube OK: {source.get('title')} -> {largest.name} ({largest.stat().st_size} byte)")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
