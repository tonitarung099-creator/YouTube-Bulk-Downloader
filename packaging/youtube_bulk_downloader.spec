# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all


datas = []
binaries = []
hiddenimports = []

# yt-dlp memakai banyak import dinamis, jadi tetap dikoleksi penuh.
for pkg in ("yt_dlp", "yt_dlp_ejs"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Google GenAI juga memakai import dinamis, tetapi test suite upstream tidak diperlukan
# saat runtime dan sebelumnya ikut membawa pytest serta ratusan modul test ke ZIP portable.
def _genai_runtime_module(name: str) -> bool:
    return not (
        name.startswith("google.genai.tests")
        or name.startswith("google.genai._test")
    )


d, b, h = collect_all(
    "google.genai",
    include_py_files=False,
    filter_submodules=_genai_runtime_module,
    exclude_datas=["tests/**", "**/tests/**"],
)
datas += d
binaries += b
hiddenimports += h

a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["google.genai.tests", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Pengunduh YouTube Massal",
    console=False,
    contents_directory="_internal",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Pengunduh YouTube Massal",
)
