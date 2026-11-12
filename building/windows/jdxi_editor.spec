# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Windows build (one folder: dist/JD-Xi-Studio/, with JD-Xi-Studio.exe).

Build from the repository root after installing the package (not editable):

    python -m pip install ".[soundfont]" pyinstaller
    pyinstaller --noconfirm building/windows/jdxi_editor.spec

The resources come from the installed package (jdxi_editor/_bundle/resources,
already scaled down by hatch_build.py) and are placed at resources/ next to the
code, where jdxi_editor.resources looks first in a frozen app (sys._MEIPASS).
FluidSynth's DLLs go to fluidsynth/bin (see jdxi_editor.midi.fluidsynth_library).
"""

import os
from pathlib import Path

import jdxi_editor
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent.parent
PACKAGE = Path(jdxi_editor.__file__).resolve().parent
BUNDLED_RESOURCES = PACKAGE / "_bundle" / "resources"
if not BUNDLED_RESOURCES.is_dir():
    raise SystemExit(
        f"{BUNDLED_RESOURCES} not found: install the package with "
        "'pip install .' (not -e) before running PyInstaller"
    )

datas = [(str(BUNDLED_RESOURCES), "resources")]
datas += collect_data_files("jdxi_editor", excludes=["_bundle/**"])
datas += collect_data_files("picoui")
datas += collect_data_files("qtawesome")
datas += collect_data_files("qdarktheme")
datas += collect_data_files("music21", includes=["**/*.json", "**/*.xml", "**/*.txt"])

binaries = [
    (str(dll), "fluidsynth/bin") for dll in sorted((ROOT / "fluidsynth" / "bin").glob("*.dll"))
]

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
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Not used by the editor; keeps the folder smaller
    excludes=["PyQt5", "PyQt6", "tkinter", "jdxi_editor.devel"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JD-Xi-Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Set JDXI_CONSOLE=1 when building to get a console window for debugging
    console=os.environ.get("JDXI_CONSOLE") == "1",
    disable_windowed_traceback=False,
    icon=str(ROOT / "resources" / "jdxi_icon.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="JD-Xi-Studio",
)
