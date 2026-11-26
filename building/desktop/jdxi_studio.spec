# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the macOS and Linux builds (the Windows one is
building/windows/jdxi_editor.spec, with its installer).

- macOS: dist/JD-Xi Studio.app (then a disk image: building/desktop/package.py dmg)
- Linux: dist/JD-Xi-Studio/ with the JD-Xi-Studio executable (then a .deb:
  building/desktop/package.py deb)

Build from outside the checkout after installing the package (not editable), so
that the resources come from the installed package (jdxi_editor/_bundle/resources,
already scaled down by hatch_build.py):

    python -m pip install . pyinstaller
    cd /tmp && pyinstaller --noconfirm <checkout>/building/desktop/jdxi_studio.spec
"""

import os
import sys
from pathlib import Path

import jdxi_editor
from jdxi_editor.project import __version__
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent
PACKAGE = Path(jdxi_editor.__file__).resolve().parent
BUNDLED_RESOURCES = PACKAGE / "_bundle" / "resources"
if not BUNDLED_RESOURCES.is_dir():
    raise SystemExit(
        f"{BUNDLED_RESOURCES} not found: install the package with "
        "'pip install .' (not -e) before running PyInstaller"
    )
MACOS = sys.platform == "darwin"
NAME = "JD-Xi-Studio"

datas = [(str(BUNDLED_RESOURCES), "resources")]
datas += collect_data_files("jdxi_editor", excludes=["_bundle/**"])
datas += collect_data_files("picoui")
datas += collect_data_files("qtawesome")
datas += collect_data_files("qdarktheme")

hiddenimports = []
for package in ("jdxi_editor", "picoui", "picomidi", "decologr", "mido", "rtmidi"):
    hiddenimports += collect_submodules(package)
hiddenimports += [
    "mido.backends.rtmidi",
    "sqlalchemy.dialects.sqlite",
    "PySide6.QtNetwork",
    "PySide6.QtSvg",
    "PySide6.QtPrintSupport",
]

a = Analysis(
    [str(ROOT / "run_editor.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Not used by the app: Qt bindings it does not use, and the analysis libraries of the
    # dev tools (scripts/, the "audio" and "plots" extras) when they are in the environment
    excludes=["PyQt5", "PyQt6", "tkinter", "scipy", "pandas", "matplotlib", "librosa", "numba",
              "llvmlite", "soundfile", "IPython", "babel", "torch"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=os.environ.get("JDXI_CONSOLE") == "1",
    disable_windowed_traceback=False,
    # PyInstaller signs the macOS executable ad hoc (needed to run on Apple
    # silicon); a Developer ID signature and notarisation come later
    icon=str(ROOT / "resources" / "jdxi_icon.icns") if MACOS else None,  # Linux: the .deb's icon
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=NAME,
)

if MACOS:
    app = BUNDLE(
        coll,
        name="JD-Xi Studio.app",
        icon=str(ROOT / "resources" / "jdxi_icon.icns"),
        bundle_identifier="io.github.emanuelemerlo.jdxistudio",
        version=__version__,
        info_plist={
            "CFBundleName": "JD-Xi Studio",
            "CFBundleDisplayName": "JD-Xi Studio",
            "CFBundleShortVersionString": __version__,
            "CFBundleVersion": __version__,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "LSApplicationCategoryType": "public.app-category.music",
            # The USB recorder records the JD-Xi's audio over USB. An app that
            # opens an input without saying why gets silence from macOS, with
            # no question and no error (seen by the original project with its
            # 1.0.0 disk image: markxbrooks/JDXI-Editor 1917cdbd)
            "NSMicrophoneUsageDescription": (
                "JD-Xi Studio records the JD-Xi's audio over USB (USB recorder)."
            ),
        },
    )
