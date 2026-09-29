from __future__ import annotations

from pathlib import Path

import app.core.downloader as downloader_module
import app.core.paths as paths
from app.core.downloader import YouTubeDownloader


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
