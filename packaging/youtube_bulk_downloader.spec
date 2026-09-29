# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas=[]; binaries=[]; hiddenimports=[]
for pkg in ("yt_dlp", "yt_dlp_ejs", "google.genai"):
    d,b,h=collect_all(pkg); datas+=d; binaries+=b; hiddenimports+=h

a=Analysis(["../main.py"], pathex=[".."], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
           noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(
    pyz,a.scripts,[],exclude_binaries=True,
    name="Pengunduh YouTube Massal",
    console=False,
    contents_directory="_internal",
)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name="Pengunduh YouTube Massal")
