"""
JD-Xi Studio's mark: drawn in code, so it needs no image file.

A dark tile with the four part colours as a step sequencer row (Digital 1
red, Digital 2 orange, Drums purple, Analog blue) over three keys, and the
name. The original JDXI-Editor logo stays with the original project.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from jdxi_editor.i18n import tr
from jdxi_editor.project import __display_name__, __origin__

PART_COLOURS = ("#eb5757", "#f2994a", "#a78bfa", "#3fa7f5")


def draw_mark(size: int = 256) -> QPixmap:
    """The square mark (window icon, splash)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256.0
    tile = QPainterPath()
    tile.addRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 52 * s, 52 * s)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor("#24262b"))
    grad.setColorAt(1, QColor("#0e0f11"))
    p.fillPath(tile, grad)
    p.setPen(QPen(QColor("#3a3d44"), 3 * s))
    p.drawPath(tile)
    # the step row: four pads in the part colours
    pad, gap, top = 40 * s, 12 * s, 58 * s
    left = (size - (4 * pad + 3 * gap)) / 2
    for i, colour in enumerate(PART_COLOURS):
        r = QRectF(left + i * (pad + gap), top, pad, pad)
        path = QPainterPath()
        path.addRoundedRect(r, 9 * s, 9 * s)
        p.fillPath(path, QColor(colour))
    # three keys below
    key_w, key_h, key_top = 46 * s, 74 * s, 126 * s
    key_left = (size - 3 * key_w - 2 * 6 * s) / 2
    for i in range(3):
        r = QRectF(key_left + i * (key_w + 6 * s), key_top, key_w, key_h)
        path = QPainterPath()
        path.addRoundedRect(r, 7 * s, 7 * s)
        p.fillPath(path, QColor("#f2f2f2"))
    for i in range(2):
        x = key_left + (i + 1) * (key_w + 6 * s) - 3 * s - 14 * s
        r = QRectF(x, key_top, 28 * s, 44 * s)
        path = QPainterPath()
        path.addRoundedRect(r, 5 * s, 5 * s)
        p.fillPath(path, QColor("#16171a"))
    p.end()
    return pm


def icon() -> QIcon:
    out = QIcon()
    for size in (16, 32, 48, 64, 128, 256):
        out.addPixmap(draw_mark(size))
    return out


def origin_line() -> str:
    """'based on JDXI-Editor by Mark Brooks', translated."""
    project, _, author = __origin__.partition(" by ")
    return tr("based on {project} by {author}").format(project=project, author=author)


def title_font(size: int) -> QFont:
    font = QFont()
    font.setFamilies(["Myriad Pro", "Segoe UI", "Helvetica Neue", "Arial"])
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.Bold)
    return font


__all__ = ["draw_mark", "icon", "origin_line", "title_font", "__display_name__"]
