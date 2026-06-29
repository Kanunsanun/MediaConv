# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — MediaConv を onedir 形式で固める。

外部バイナリ(ffmpeg)はここには含めず、Inno Setup が {app}\\bin に配置する。
ビルド:  .venv\\Scripts\\pyinstaller.exe mediaconv.spec --noconfirm
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules("pdf2docx")
hiddenimports += collect_submodules("fontTools")

datas = []
datas += collect_data_files("pdf2docx")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "soundfile", "numpy.f2py"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MediaConv",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                 # GUI アプリ（コンソール窓を出さない）
    disable_windowed_traceback=False,
    icon="app.ico" if __import__("os").path.exists("app.ico") else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MediaConv",
)
