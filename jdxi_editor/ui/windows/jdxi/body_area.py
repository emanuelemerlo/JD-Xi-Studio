"""
The main window's background around the instrument.

At its own size the window is the instrument: all body colour. In a bigger
(maximised) window the instrument keeps its size, centred; the room around it
was the same body colour, so the instrument had no edge. There the room is a
darker surface and the instrument a body with rounded corners, a light top edge
and a soft shadow, as a JD-Xi on a desk.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from jdxi_editor.ui.style.editor_style import BODY_COLOR, body_texture

SURFACE = "#19191b"  # the room around the instrument
EDGE = "#46464a"  # the body's outline
HIGHLIGHT = "#5a5a5f"  # its top edge, lit from above
PAD = 22  # body around the panel and keys
RADIUS = 18
SHADOW = 14  # how far the shadow spreads


class BodyArea(QWidget):
    """The central widget: paints the surface and the instrument's body around *stage*."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("jdxiBodyArea")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.stage: QWidget | None = None
        self._grain: QPixmap | None = None

    def body_rect(self) -> QRectF | None:
        """The instrument's body in this widget, or None when there is no room for one."""
        if self.stage is None:
            return None
        stage = self.stage.geometry()
        if (self.width() - stage.width() < 2 * (PAD + SHADOW)
                or self.height() - stage.height() < 2 * (PAD + SHADOW)):
            return None
        return QRectF(stage).adjusted(-PAD, -PAD, PAD, PAD)

    def _grain_brush(self) -> QBrush:
        if self._grain is None:
            self._grain = QPixmap.fromImage(body_texture(128, 128))
        return QBrush(self._grain)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt)
        painter = QPainter(self)
        body = self.body_rect()
        if body is None:  # the window is the instrument
            painter.fillRect(self.rect(), self._grain_brush())
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(SURFACE))
        # the shadow: rings fading out, a little lower than the body
        painter.setPen(Qt.PenStyle.NoPen)
        for step in range(SHADOW, 0, -2):
            alpha = int(70 * (1 - step / SHADOW) ** 2) + 6
            painter.setBrush(QColor(0, 0, 0, alpha))
            ring = body.adjusted(-step, -step + 4, step, step + 4)
            painter.drawRoundedRect(ring, RADIUS + step, RADIUS + step)
        path = QPainterPath()
        path.addRoundedRect(body, RADIUS, RADIUS)
        painter.fillPath(path, self._grain_brush())
        # a faint sheen from the top, and the outline with its lit top edge
        sheen = QLinearGradient(body.topLeft(), body.bottomLeft())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 14))
        sheen.setColorAt(0.25, QColor(255, 255, 255, 0))
        painter.fillPath(path, sheen)
        outline = QLinearGradient(body.topLeft(), body.bottomLeft())
        outline.setColorAt(0.0, QColor(HIGHLIGHT))
        outline.setColorAt(0.1, QColor(EDGE))
        outline.setColorAt(1.0, QColor("#2a2a2d"))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(outline), 1.2))
        painter.drawPath(path)


__all__ = ["BodyArea", "BODY_COLOR"]
