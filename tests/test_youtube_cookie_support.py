from __future__ import annotations

from pathlib import Path

import pytest

import app.core.downloader as downloader_module
import app.core.paths as paths
from app.core.downloader import YouTubeDownloader
from app.models.commands import DownloadIntent


def test_youtube_cookie_file_uses_portable_data_dir(monkeypatch, tmp_path: Path) -> None:
    cookie = tmp_path / "youtube-cookies.txt"
    cookie.write_text("# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tFALSE\t0\ttest\tvalue\n", encoding="utf-8")
    monkeypatch.delenv("YOUTUBE_COOKIES_FILE", raising=False)
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)

    assert paths.youtube_cookie_file() == cookie.resolve()


def test_youtube_cookie_file_env_override_wins(monkeypatch, tmp_path: Path) -> None:
    portable = tmp_path / "portable"
    portable.mkdir()
    (portable / "youtube-cookies.txt").write_text("portable", encoding="utf-8")
    override = tmp_path / "override.txt"
    override.write_text("override", encoding="utf-8")
    monkeypatch.setattr(paths, "data_dir", lambda: portable)
    monkeypatch.setenv("YOUTUBE_COOKIES_FILE", str(override))

    assert paths.youtube_cookie_file() == override.resolve()


def test_portable_tool_options_include_cookie_and_bundled_tools(monkeypatch, tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    ffmpeg = tools / "ffmpeg.exe"
    deno = tools / "deno.exe"
    ffmpeg.write_bytes(b"ffmpeg")
    deno.write_bytes(b"deno")
    cookie = tmp_path / "youtube-cookies.txt"
    cookie.write_text("cookie", encoding="utf-8")

    def fake_tool(name: str):
        return {"ffmpeg": ffmpeg, "deno": deno}.get(name)

    monkeypatch.setattr(downloader_module, "bundled_tool_path", fake_tool)
    monkeypatch.setattr(downloader_module, "youtube_cookie_file", lambda: cookie)

    opts = YouTubeDownloader._portable_tool_options()

    assert opts["ffmpeg_location"] == str(tools)
    assert opts["js_runtimes"]["deno"]["path"] == str(deno)
    assert opts["cookiefile"] == str(cookie)


def test_analyze_turns_youtube_antibot_into_actionable_message(monkeypatch) -> None:
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, url, download=False):
            self.opts["logger"].error(
                "ERROR: [youtube] abc: Sign in to confirm you’re not a bot. "
                "Use --cookies-from-browser or --cookies for the authentication."
            )
            return None

    monkeypatch.setattr(downloader_module.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(YouTubeDownloader, "_portable_tool_options", staticmethod(lambda: {}))

    with pytest.raises(RuntimeError) as caught:
        YouTubeDownloader().analyze("https://www.youtube.com/watch?v=abc")

    message = str(caught.value)
    assert "verifikasi anti-bot" in message
    assert "data\\youtube-cookies.txt" in message
    assert "Jangan bagikan" in message


def test_download_turns_youtube_antibot_into_actionable_message(monkeypatch, tmp_path: Path) -> None:
    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, urls):
            raise downloader_module.yt_dlp.utils.DownloadError(
                "ERROR: [youtube] abc: Sign in to confirm you're not a bot. "
                "Use --cookies-from-browser or --cookies for the authentication."
            )

    monkeypatch.setattr(downloader_module.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(YouTubeDownloader, "_portable_tool_options", staticmethod(lambda: {}))
    intent = DownloadIntent(
        action="download",
        url="https://www.youtube.com/watch?v=abc",
        output_folder=str(tmp_path),
        use_archive=False,
        include_metadata=False,
    )

    with pytest.raises(RuntimeError) as caught:
        YouTubeDownloader(tmp_path).download(intent)

    assert "verifikasi anti-bot" in str(caught.value)
    assert "youtube-cookies.txt" in str(caught.value)
