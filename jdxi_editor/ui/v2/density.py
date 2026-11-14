"""
How dense the editors are, from the screen they open on.

The editors are designed for about 2560x1440 (4K at 150%). On a lower screen
(1080p at 125% is 1536x864, a 2496x1664 at 175% is 1426x951) they become
*compact*: smaller knobs, graphs and spacing, so less scrolling; the text
keeps its size. A narrow screen also gets a narrower side panel.

JDXI_COMPACT=1 / 0 forces it (screenshots, tests).
"""

from __future__ import annotations

import os
from functools import lru_cache

from PySide6.QtGui import QGuiApplication

COMPACT_BELOW_HEIGHT = 1150  # available height (logical px) under which the editors are compact
NARROW_BELOW_WIDTH = 1800  # available width under which the side panel is narrower
VERY_NARROW_BELOW_WIDTH = 1500  # ... and some rows of cards become columns
COMPACT_FACTOR = 0.74


@lru_cache(maxsize=1)
def _screen() -> tuple[int, int]:
    app = QGuiApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is None:
        return 2560, 1400
    area = screen.availableGeometry()
    return area.width(), area.height()


def compact() -> bool:
    forced = os.environ.get("JDXI_COMPACT")
    if forced in ("0", "1"):
        return forced == "1"
    return _screen()[1] < COMPACT_BELOW_HEIGHT


def narrow() -> bool:
    forced = os.environ.get("JDXI_COMPACT")
    if forced in ("0", "1"):
        return forced == "1"
    return _screen()[0] < NARROW_BELOW_WIDTH


def very_narrow() -> bool:
    """Too narrow for some rows of cards side by side (a 2496x1664 screen at 175%: 1426 wide)."""
    forced = os.environ.get("JDXI_NARROW")
    if forced in ("0", "1"):
        return forced == "1"
    return _screen()[0] < VERY_NARROW_BELOW_WIDTH


def px(size: int, minimum: int = 0) -> int:
    """A size (not text) for this density."""
    return max(minimum, round(size * COMPACT_FACTOR)) if compact() else size


def side_width(size: int) -> int:
    """A width in the side panel (presets, information)."""
    return round(size * 0.9) if narrow() else size


@lru_cache(maxsize=1)
def _fit_stack_class():
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    class FitStack(QWidget):
        """Pages shown one at a time, as tall as the page shown (a QStackedWidget is as tall
        as its tallest page, whatever its size policies say): the others are hidden."""

        currentChanged = Signal(int)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(0, 0, 0, 0)
            self._pages: list = []
            self._current = -1

        def addWidget(self, page) -> int:
            self._pages.append(page)
            self._layout.addWidget(page)
            if self._current < 0:
                self._current = 0
            page.setVisible(len(self._pages) - 1 == self._current)
            return len(self._pages) - 1

        def count(self) -> int:
            return len(self._pages)

        def widget(self, index: int):
            return self._pages[index] if 0 <= index < len(self._pages) else None

        def currentIndex(self) -> int:
            return self._current

        def currentWidget(self):
            return self.widget(self._current)

        def setCurrentIndex(self, index: int) -> None:
            if not 0 <= index < len(self._pages) or index == self._current:
                return
            self._current = index
            for i, page in enumerate(self._pages):
                page.setVisible(i == index)
            self.currentChanged.emit(index)

    return FitStack


def FitStack(parent=None):
    return _fit_stack_class()(parent)
