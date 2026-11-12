"""The UI audit (scripts/ui_audit.py) finds no problem, at 100% and at 150% with Windows-like fonts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("scale, font_dpi", [("1", "96"), ("1.5", "120")])
def test_ui_audit_is_clean(tmp_path, scale, font_dpi):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_SCALE_FACTOR=scale, QT_FONT_DPI=font_dpi,
               JDXI_LANGUAGE="en", HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "ui_audit.py")], env=env, cwd=ROOT,
                         capture_output=True, text=True, timeout=300)
    report = "\n".join(line for line in run.stdout.splitlines() if line.startswith(("UI audit", "  ")))
    assert run.returncode == 0, report + "\n" + run.stderr[-2000:]
