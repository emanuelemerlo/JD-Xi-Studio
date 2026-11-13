"""
From the original program's names to JD-Xi Studio's, once.

Up to 1.0.0a2 JD-Xi Studio kept the original JDXI-Editor's settings key
(mabsoft / JD-Xi Editor) and user folder (~/.jdxi_editor), so the two programs
shared (and overwrote) each other's settings, programs and logs. From 1.0.0a3
it has its own: at the first start the old settings and files are copied into
the new places (the old ones stay, for the original program).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QSettings

from jdxi_editor.project import (
    LEGACY_DATA_NAME,
    LEGACY_ORGANIZATION,
    LEGACY_PROGRAM,
    __data_name__,
    __organization_name__,
    __program__,
)

DONE_KEY = "migrated_from_jdxi_editor"
SKIP = {"logs", "temp"}  # the old program's logs and temporary files stay where they are


def migrate(
    home: Path | None = None,
    new: QSettings | None = None,
    old: QSettings | None = None,
) -> dict[str, int]:
    """Copy the old settings and user files once; returns what was copied."""
    home = home or Path.home()
    new = new if new is not None else QSettings(__organization_name__, __program__)
    copied = {"settings": 0, "files": 0}
    if new.value(DONE_KEY, False, type=bool):
        return copied
    old = old if old is not None else QSettings(LEGACY_ORGANIZATION, LEGACY_PROGRAM)
    present = set(new.allKeys())
    for key in old.allKeys():
        if key not in present:  # what JD-Xi Studio already has is kept
            new.setValue(key, old.value(key))
            copied["settings"] += 1
    source, target = home / f".{LEGACY_DATA_NAME}", home / f".{__data_name__}"
    if source.is_dir():
        for item in source.iterdir():
            if item.name in SKIP or (target / item.name).exists():
                continue
            target.mkdir(parents=True, exist_ok=True)
            try:
                if item.is_dir():
                    shutil.copytree(item, target / item.name)
                else:
                    shutil.copy2(item, target / item.name)
                copied["files"] += 1
            except OSError:
                pass  # a file in use or unreadable: the rest is copied
    new.setValue(DONE_KEY, True)
    new.sync()
    return copied
