from __future__ import annotations
import os,sys
from pathlib import Path

def app_root()->Path:
    if getattr(sys,"frozen",False): return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]

def data_dir()->Path:
    root=app_root(); probe=root/".write-test"
    try:
        probe.write_text("ok",encoding="utf-8"); probe.unlink(missing_ok=True); target=root/"data"
    except OSError:
        target=Path(os.getenv("LOCALAPPDATA",Path.home()))/"YouTubeBulkDownloader"
    target.mkdir(parents=True,exist_ok=True); return target

def default_download_dir()->Path:
    p=app_root()/"downloads"; p.mkdir(parents=True,exist_ok=True); return p
