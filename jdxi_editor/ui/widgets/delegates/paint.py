"""A button drawn in a table cell, in the app's dark look (a native push
button is drawn white on the dark tables)."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QStyle


def paint_cell_button(painter: QPainter, option, text: str, *, dim: bool = False) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = option.rect.adjusted(4, 4, -4, -4)
    hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
    painter.setPen(QPen(QColor("#5a5d66" if hover else "#3a3c42"), 1))
    painter.setBrush(QColor("#26272c" if hover else "#1c1d21"))
    painter.drawRoundedRect(QRectF(rect), 6, 6)
    painter.setPen(QColor("#8a8d95" if dim else "#e6e7ea"))
    shown = option.fontMetrics.elidedText(text, Qt.TextElideMode.ElideMiddle, rect.width() - 16)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, shown)
    painter.restore()
