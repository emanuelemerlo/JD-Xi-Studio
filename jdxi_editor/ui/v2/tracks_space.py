"""
More room for the MIDI Player's tracks, on the same page (a tab of their own
would look like another editor):

- a grip under the Tracks card: drag it to make the card taller or shorter;
  the height is remembered;
- an Expand button in the card: hides the cards not needed while listening
  (Fit to the JD-Xi, Automation, USB recorder, Event filter) so the tracks
  take the room; Player and Playback stay. Again: everything back.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter
from PySide6.QtWidgets import QPushButton, QWidget

from jdxi_editor.i18n import tr

SETTINGS_KEY = "midi_player/tracks_height"
MIN_HEIGHT = 180
DEFAULT_HEIGHT = 300


def _settings() -> QSettings:
    from jdxi_editor.project import __organization_name__, __program__

    return QSettings(__organization_name__, __program__)


def saved_height() -> int:
    try:
        value = int(_settings().value(SETTINGS_KEY, DEFAULT_HEIGHT))
    except (TypeError, ValueError):
        value = DEFAULT_HEIGHT
    return max(MIN_HEIGHT, value)


class TracksGrip(QWidget):
    """A thin bar under the Tracks card: drag it to set the card's height."""

    def __init__(self, target: QWidget, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.target = target
        self.setFixedHeight(10)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.setToolTip(tr("Drag to make the tracks taller or shorter"))
        self._start_y: Optional[float] = None
        self._start_height = 0
        self.set_height(saved_height(), save=False)

    def set_height(self, height: int, save: bool = True) -> None:
        height = max(MIN_HEIGHT, int(height))
        # a minimum, not a fixed height: Expand can still give it more room
        self.target.setMinimumHeight(height)
        if save:
            _settings().setValue(SETTINGS_KEY, height)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_y = event.globalPosition().y()
            self._start_height = self.target.height()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._start_y is not None:
            self.set_height(self._start_height + event.globalPosition().y() - self._start_y, save=False)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._start_y is not None:
            self._start_y = None
            self.set_height(self.target.minimumHeight())  # remembered
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.set_height(DEFAULT_HEIGHT)  # back to the usual height

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#5a5d66" if self.underMouse() else "#3a3c42"))
        width = 48
        painter.drawRoundedRect((self.width() - width) // 2, 3, width, 4, 2, 2)


class ExpandButton(QPushButton):
    """Expand / Restore: the cards not needed while listening hidden or back."""

    def __init__(self, hidden_while_expanded: Callable[[], Iterable[QWidget]], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._others = hidden_while_expanded
        self.setCheckable(True)
        self.toggled.connect(self._apply)
        self._label()

    def _label(self) -> None:
        if self.isChecked():
            self.setText("⤡ " + tr("Restore"))
            self.setToolTip(tr("Show the other cards again"))
        else:
            self.setText("⤢ " + tr("Expand"))
            self.setToolTip(tr("More room for the tracks: hide Fit to the JD-Xi, Automation, "
                               "USB recorder and Event filter (Player and Playback stay)"))

    def _apply(self, expanded: bool) -> None:
        for widget in self._others():
            widget.setVisible(not expanded)
        self._label()
