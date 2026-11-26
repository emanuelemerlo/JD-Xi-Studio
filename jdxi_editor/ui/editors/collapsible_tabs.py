"""
A tab bar whose tabs can be reduced to a small bar, as some browsers do.

The editors window keeps its optional tabs (Program settings, Recipes,
Settings) always in the bar: reduced, each is a narrow bar in its own colour,
its name in the tooltip; a click expands it (and shows it), the ◂ on an
expanded one reduces it again. The bar knows nothing of the editors: tabs are
marked collapsible with a key, and the window decides what the keys are and
remembers which are expanded.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QTabBar, QToolButton

from jdxi_editor.i18n import tr

COLLAPSED_WIDTH = 22  # px: the reduced tab, a bar with its colour
BAR_COLOR = "#8a8d94"


def bar_icon(color: str, height: int = 14) -> QIcon:
    """A narrow rounded bar, the face of a reduced tab."""
    pixmap = QPixmap(4, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(0, 0, 4, height, 2, 2)
    painter.end()
    return QIcon(pixmap)


class CollapsibleTabBar(QTabBar):
    """
    Tabs marked with a key (set_collapsible) can be reduced and expanded.

    Signals:
        collapsed_changed(str, bool): the tab with *key* was reduced (True) or expanded
    """

    collapsed_changed = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._keys: dict[str, dict] = {}  # key -> {"text", "icon", "color", "collapsed"}
        self.currentChanged.connect(self._expand_when_shown)

    # --- which tabs -----------------------------------------------------------

    def set_collapsible(self, index: int, key: str, color: str = BAR_COLOR) -> None:
        """Mark the tab at *index* as reducible, under *key* (expanded at first)."""
        if index < 0:
            return
        self.setTabData(index, key)
        entry = self._keys.setdefault(key, {"collapsed": False})
        entry.update(text=self.tabText(index) or entry.get("text", ""), icon=self.tabIcon(index), color=color)
        self._apply(index)

    def index_of(self, key: str) -> int:
        for index in range(self.count()):
            if self.tabData(index) == key:
                return index
        return -1

    def key_at(self, index: int) -> Optional[str]:
        key = self.tabData(index) if 0 <= index < self.count() else None
        return key if key in self._keys else None

    def is_collapsed(self, index: int) -> bool:
        key = self.key_at(index)
        return bool(key and self._keys[key]["collapsed"])

    def expanded_keys(self) -> list[str]:
        return [k for k, e in self._keys.items() if not e["collapsed"] and self.index_of(k) >= 0]

    # --- reduce and expand ----------------------------------------------------

    def set_collapsed(self, key: str, collapsed: bool) -> None:
        entry = self._keys.get(key)
        index = self.index_of(key)
        if entry is None or index < 0 or entry["collapsed"] == collapsed:
            return
        if collapsed and index == self.currentIndex():
            self.setCurrentIndex(self._neighbour(index))  # never left on a reduced tab
        entry["collapsed"] = collapsed
        self._apply(index)
        self.collapsed_changed.emit(key, collapsed)

    def _neighbour(self, index: int) -> int:
        """The nearest tab that is not reduced (on the left first)."""
        for step in range(1, self.count()):
            for candidate in (index - step, index + step):
                if 0 <= candidate < self.count() and not self.is_collapsed(candidate):
                    return candidate
        return index

    def _expand_when_shown(self, index: int) -> None:
        """A reduced tab chosen (a click on its bar, Ctrl+Tab): it opens."""
        key = self.key_at(index)
        if key and self._keys[key]["collapsed"]:
            self.set_collapsed(key, False)

    def _apply(self, index: int) -> None:
        key = self.key_at(index)
        if key is None:
            return
        entry = self._keys[key]
        side = QTabBar.ButtonPosition.RightSide
        if entry["collapsed"]:
            self.setTabText(index, "")
            self.setTabIcon(index, bar_icon(entry["color"]))
            self.setTabButton(index, side, None)
        else:
            self.setTabText(index, entry["text"])
            self.setTabIcon(index, entry["icon"] or QIcon())
            if self.tabButton(index, side) is None:
                self.setTabButton(index, side, self._reduce_button(key))
        self.updateGeometry()
        self.update()

    def _reduce_button(self, key: str) -> QToolButton:
        button = QToolButton()
        button.setText("◂")
        button.setToolTip(tr("Reduce the tab to a bar (a click on the bar opens it again)"))
        button.setFixedSize(16, 16)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            "QToolButton { color: #a3a6ad; border: none; background: transparent; font-size: 11px;"
            " padding: 0; } QToolButton:hover { color: #ffffff; background: #3a3d45; border-radius: 8px; }"
        )
        button.clicked.connect(lambda _checked=False, k=key: self.set_collapsed(k, True))
        return button

    # --- size -----------------------------------------------------------------

    def tabSizeHint(self, index: int) -> QSize:
        size = super().tabSizeHint(index)
        if self.is_collapsed(index):
            return QSize(COLLAPSED_WIDTH, size.height())
        return size

    def minimumTabSizeHint(self, index: int) -> QSize:
        size = super().minimumTabSizeHint(index)
        if self.is_collapsed(index):
            return QSize(COLLAPSED_WIDTH, size.height())
        return size
