# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Roulette.
Build with:  pyinstaller roulette.spec
Output (macOS):   dist/Roulette.app
Output (Windows): dist/Roulette/   (directory bundle)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
ASSETS = ROOT / "app" / "assets"

# Use .ico on Windows if available, otherwise fall back to .png
_ico = ASSETS / "icon.ico"
_png = ASSETS / "icon.png"
_icon_file = str(_ico) if sys.platform == "win32" and _ico.exists() else str(_png)

a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ASSETS / "icon.png"),      "app/assets"),
        (str(ASSETS / "toggle_on.svg"), "app/assets"),
        (str(ASSETS / "toggle_off.svg"),"app/assets"),
    ],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "test", "distutils"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Roulette",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,         # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,      # native arch of the build machine
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Roulette",
)

# macOS-only: wrap in .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Roulette.app",
        icon=str(_png),
        bundle_identifier="com.roulette.app",
        info_plist={
            "CFBundleDisplayName": "Roulette",
            "CFBundleShortVersionString": "1.3.0",
            "CFBundleVersion": "3",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,   # allow dark mode
            "LSMinimumSystemVersion": "12.0",
        },
    )
