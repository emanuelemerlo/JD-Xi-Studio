"""
JD-Xi Studio's mark: drawn in code, so it needs no image file.

A JD-Xi in miniature on a dark tile: black, white keys and red light only,
as the instrument's panel. The original JDXI-Editor logo stays with the original project.
"""

from __future__ import annotations

import math

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
    if size <= 32:  # title bars, taskbar: the name, stacked, is what stays readable
        _draw_name_mark(p, size)
        p.end()
        return pm
    small = size < 48  # fewer, bigger elements
    tiny = False
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
    if tiny:
        display = QRectF(40 * s, 44 * s, 176 * s, 44 * s)
    elif small:
        display = QRectF(40 * s, 40 * s, 176 * s, 32 * s)
    else:
        display = QRectF(36 * s, 36 * s, 104 * s, 26 * s)
    glow = QColor(red)
    glow.setAlpha(70)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(glow)
    p.drawRoundedRect(display.adjusted(-4 * s, -4 * s, 4 * s, 4 * s), 8 * s, 8 * s)
    p.setBrush(QColor("#050505"))
    p.drawRoundedRect(display, 5 * s, 5 * s)
    p.setBrush(red)
    _display_text(p, display, red, s)
    # the big category dial: an endless knob, no pointer; the category LED lit
    # on the white circle around it shows where it is (Bass, as in the manual)
    if not small:
        c, r = QPointF(194 * s, 52 * s), 18 * s
        ring = r * 1.42
        p.setPen(QPen(QColor("#d9d9d9"), max(1.0, 1.6 * s)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, ring, ring)
        p.setPen(QPen(QColor("#3a3c41"), max(1.0, 1.5 * s)))
        p.setBrush(QColor("#111214"))
        p.drawEllipse(c, r, r)
        led = max(1.2, 3.2 * s)
        for i in range(8):
            a = math.radians(i * 45 - 90)
            dot = QPointF(c.x() + math.cos(a) * ring, c.y() + math.sin(a) * ring)
            lit = i == 5  # Bass
            if lit:
                halo = QColor(red)
                halo.setAlpha(90)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(halo)
                p.drawEllipse(dot, led * 2.2, led * 2.2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(red if lit else QColor("#4a0f0a"))
            p.drawEllipse(dot, led, led)
    # the other knobs, with their red ring and pointer
    if not tiny:
        knobs = [QPointF(x * s, 116 * s) for x in ((62, 128, 194) if not small else (84, 172))]
        for c in knobs:
            r = (18 if not small else 22) * s
            p.setPen(QPen(red, max(1.2, (4 if not small else 6) * s)))
            p.setBrush(QColor("#111214"))
            p.drawEllipse(c, r, r)
            if not small:
                p.setPen(QPen(QColor("#f2f2f2"), 3.2 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(c, QPointF(c.x() + r * 0.45, c.y() - r * 0.55))
    # the step LEDs
    if not small:
        steps = 8
        step_w = 184 * s / steps
        for i in range(steps):
            r = QRectF(36 * s + i * step_w + 3 * s, 148 * s, step_w - 8 * s, 11 * s)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(red if i % 4 == 0 else QColor("#5a140d"))
            p.drawRoundedRect(r, 3 * s, 3 * s)
    # the mini keys
    if tiny:
        key_top, key_h = 116 * s, 112 * s
    elif small:
        key_top, key_h = 160 * s, 68 * s
    else:
        key_top, key_h = 172 * s, 56 * s
    whites = 7 if not small else 3
    left = 36 * s if not small else 40 * s
    kw = (184 if not small else 176) * s / whites
    for i in range(whites):
        r = QRectF(left + i * kw + 2 * s, key_top, kw - 4 * s, key_h)
        path = QPainterPath()
        path.addRoundedRect(r, 4 * s, 4 * s)
        p.fillPath(path, QColor("#f4f4f4"))
    if not small:
        for i in (0, 1, 3, 4, 5):
            r = QRectF(left + (i + 1) * kw - kw * 0.3, key_top, kw * 0.6, key_h * 0.6)
            path = QPainterPath()
            path.addRoundedRect(r, 3 * s, 3 * s)
            p.fillPath(path, QColor("#0e0f11"))
    p.end()
    return pm


def _display_text(p, display, colour, s) -> None:
    """«JD-Xi» on the display, in a monospaced (LCD-like) bold face, fitted to it."""
    from PySide6.QtGui import QPainterPath

    font = QFont()
    font.setFamilies(["DejaVu Sans Mono", "Consolas", "Menlo", "Courier New", "monospace"])
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(100)
    font.setWeight(QFont.Weight.Bold)
    path = QPainterPath()
    path.addText(0, 0, font, "JD-Xi")
    box = path.boundingRect()
    inset_x, inset_y = 7 * s, 6 * s
    scale = min((display.width() - 2 * inset_x) / box.width(), (display.height() - 2 * inset_y) / box.height())
    p.save()
    p.translate(display.center().x() - box.center().x() * scale, display.center().y() - box.center().y() * scale)
    p.scale(scale, scale)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(colour)
    p.drawPath(path)
    p.restore()


def _draw_name_mark(p: QPainter, size: int) -> None:
    """The small icon: the dark tile with «JD» over «Xi» (white and the panel's
    red, the lettering of the logo), drawn as outlines filling the tile so it
    stays sharp down to 16 px."""
    from PySide6.QtGui import QFont

    s = size / 256.0
    tile = QPainterPath()
    tile.addRoundedRect(QRectF(4 * s, 4 * s, 248 * s, 248 * s), 52 * s, 52 * s)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor("#26272b"))
    grad.setColorAt(1, QColor("#0a0a0c"))
    p.fillPath(tile, grad)
    font = QFont()
    font.setFamilies(["Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial"])
    font.setPixelSize(100)
    font.setWeight(QFont.Weight.Black)
    rows = []
    for text in ("JD", "Xi"):
        path = QPainterPath()
        path.addText(0, 0, font, text)
        rows.append(path)
    box_w, box_h, gap = 200 * s, 94 * s, 14 * s  # each row's room in the tile
    # one scale for both rows: the letters of «JD» and «Xi» equally tall
    cap = max(r.boundingRect().height() for r in rows)
    scale = min(min(box_w / r.boundingRect().width() for r in rows), box_h / cap)
    top = (size - 2 * box_h - gap) / 2
    for i, (path, colour) in enumerate(zip(rows, (QColor("#f4f4f4"), QColor("#ff2a1a")))):
        r = path.boundingRect()
        w = r.width() * scale
        x = (size - w) / 2
        y = top + i * (box_h + gap) + (box_h - cap * scale) / 2
        p.save()
        p.translate(x - r.left() * scale, y - r.top() * scale)
        p.scale(scale, scale)
        p.fillPath(path, colour)
        if size <= 24:  # a touch bolder where a pixel is a lot
            p.setPen(QPen(colour, 0.45 / scale))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
        p.restore()


def icon() -> QIcon:
    out = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
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
