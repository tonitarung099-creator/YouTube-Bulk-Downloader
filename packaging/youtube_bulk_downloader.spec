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
    excludes=[
        "google.genai.tests",
        "pytest",
        # UI aplikasi hanya memakai QtCore/Gui/Widgets/Network. Modul berikut tidak pernah
        # diimpor, tetapi dependency scanner Qt dapat tetap menarik runtime-nya.
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtPdf",
        "PySide6.QtVirtualKeyboard",
    ],
    noarchive=False,
)

# Prune binary/data Qt yang tidak dipakai. Pertahankan QtCore/Gui/Widgets/Network,
# plugin image utama, OpenGL, dan opengl32sw agar kompatibilitas laptop tetap aman.
_UNUSED_QT_SUFFIXES = (
    "PySide6/Qt6Quick.dll",
    "PySide6/Qt6Qml.dll",
    "PySide6/Qt6QmlMeta.dll",
    "PySide6/Qt6QmlModels.dll",
    "PySide6/Qt6QmlWorkerScript.dll",
    "PySide6/Qt6Pdf.dll",
    "PySide6/Qt6VirtualKeyboard.dll",
    "PySide6/plugins/imageformats/qpdf.dll",
    "PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll",
)


def _without_unused_qt(entries):
    result = []
    for entry in entries:
        destination = str(entry[0]).replace("\\", "/")
        if any(destination.endswith(suffix) for suffix in _UNUSED_QT_SUFFIXES):
            continue
        result.append(entry)
    return result


a.binaries = _without_unused_qt(a.binaries)
a.datas = _without_unused_qt(a.datas)

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
