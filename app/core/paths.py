from __future__ import annotations

import os, sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def tools_dir() -> Path:
    return app_root() / "tools"


def bundled_tool_path(name: str) -> Path | None:
    """Cari tool portable di folder aplikasi tanpa mengandalkan PATH sistem."""
    base = tools_dir()
    for candidate in (base / f"{name}.exe", base / name):
        if candidate.is_file():
            return candidate
    return None


def data_dir() -> Path:
    root = app_root()
    probe = root / ".write-test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        target = root / "data"
    except OSError:
        target = Path(os.getenv("LOCALAPPDATA", Path.home())) / "YouTubeBulkDownloader"
    target.mkdir(parents=True, exist_ok=True)
    return target


def default_download_dir() -> Path:
    p = app_root() / "downloads"
    p.mkdir(parents=True, exist_ok=True)
    return p
