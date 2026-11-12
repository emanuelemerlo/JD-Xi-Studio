"""
JD-Xi Studio's mark: drawn in code, so it needs no image file.

A JD-Xi in miniature on a dark tile: black, white keys and red light only,
as the instrument's panel. The original JDXI-Editor logo stays with the original project.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from jdxi_editor.i18n import tr
from jdxi_editor.project import __display_name__, __origin__

PART_COLOURS = ("#eb5757", "#f2994a", "#a78bfa", "#3fa7f5")


def draw_mark(size: int = 256) -> QPixmap:
    """The square mark (window icon, splash): a JD-Xi in miniature.

    Black panel, red light only, as the instrument: the red display, knobs
    with their red ring, the step LEDs and the mini keys. Below 48 px the
    details that would turn to mush are left out.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256.0
    small = size < 48
    red = QColor("#ff2a1a")
    tile = QPainterPath()
    tile.addRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 48 * s, 48 * s)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor("#26272b"))
    grad.setColorAt(1, QColor("#0a0a0c"))
    p.fillPath(tile, grad)
    p.setPen(QPen(QColor("#3a3c41"), max(1.0, 3 * s)))
    p.drawPath(tile)
    # the red display, with a glow
    display = QRectF(36 * s, 40 * s, (184 if small else 108) * s, 30 * s)
    glow = QColor(red)
    glow.setAlpha(70)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(glow)
    p.drawRoundedRect(display.adjusted(-4 * s, -4 * s, 4 * s, 4 * s), 8 * s, 8 * s)
    p.setBrush(QColor("#050505"))
    p.drawRoundedRect(display, 5 * s, 5 * s)
    p.setBrush(red)
    bars = 6 if not small else 3
    for i in range(bars):  # the display's text, as red segments
        w = (display.width() - 20 * s) / bars
        p.drawRoundedRect(QRectF(display.left() + 10 * s + i * w, display.top() + 10 * s, w - 6 * s, 10 * s), 2 * s, 2 * s)
    # knobs with their red ring
    knobs = [QPointF(184 * s, 56 * s)] if not small else []
    knobs += [QPointF(x * s, 110 * s) for x in ((60, 128, 196) if not small else (78, 178))]
    for i, c in enumerate(knobs):
        r = (30 if i == 0 and not small else 22) * s
        p.setPen(QPen(red, max(1.2, 5 * s)))
        p.setBrush(QColor("#111214"))
        p.drawEllipse(c, r, r)
        if not small:
            p.setPen(QPen(QColor("#f2f2f2"), 3.5 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(c, QPointF(c.x() + r * 0.45, c.y() - r * 0.55))
    # the step LEDs
    steps = 8 if not small else 4
    step_w = 184 * s / steps
    for i in range(steps):
        r = QRectF(36 * s + i * step_w + 2 * s, 146 * s, step_w - 6 * s, 14 * s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(red if i % 4 == 0 else QColor("#5a140d"))
        p.drawRoundedRect(r, 3 * s, 3 * s)
    # the mini keys
    key_top, key_h = 176 * s, 52 * s
    whites = 7 if not small else 4
    kw = 184 * s / whites
    for i in range(whites):
        r = QRectF(36 * s + i * kw + 1.5 * s, key_top, kw - 3 * s, key_h)
        path = QPainterPath()
        path.addRoundedRect(r, 4 * s, 4 * s)
        p.fillPath(path, QColor("#f4f4f4"))
    if not small:
        for i in (0, 1, 3, 4, 5):
            r = QRectF(36 * s + (i + 1) * kw - kw * 0.3, key_top, kw * 0.6, key_h * 0.6)
            path = QPainterPath()
            path.addRoundedRect(r, 3 * s, 3 * s)
            p.fillPath(path, QColor("#0e0f11"))
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
