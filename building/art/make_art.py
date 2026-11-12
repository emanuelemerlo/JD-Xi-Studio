"""
Draws JD-Xi Studio's pictures and icons: one family of clean illustrations in
the JD-Xi's look (a black body, a red LED display, the part colours), in code,
so they can be redrawn at any size and stay consistent.

    python building/art/make_art.py          # writes into resources/

What it writes
  - the project's logo (jdxi_studio_logo.png: README, GitHub), which replaces
    the original JDXI-Editor logo;
  - the program icon (jdxi_icon.png / _512.png / .ico / .icns) and the
    Windows installer side image, from the mark in jdxi_editor/ui/v2/brand.py.
"""

from __future__ import annotations

import io
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

RES = ROOT / "resources"
W, H = 640, 400
LED = QColor("#ff3b1f")  # the JD-Xi's red display
DIGITAL = "#eb5757"



PADS = ("#eb5757", "#f2994a", "#f2c94c", "#e6e6e6")


# --- drawing helpers ---------------------------------------------------------


def canvas(w: int = W, h: int = H) -> tuple[QImage, QPainter]:
    image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    return image, p


def rounded(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def font(px: float, bold: bool = True, mono: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(["DejaVu Sans Mono", "Consolas", "Menlo"] if mono else ["Segoe UI", "Helvetica Neue", "DejaVu Sans", "Arial"])
    f.setPixelSize(int(px))
    f.setBold(bold)
    if mono:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, px * 0.12)
    return f


def lcd(p: QPainter, rect: QRectF, text: str, glyph=None) -> None:
    """The red LED display, with the text (and a small drawing) in it."""
    p.fillPath(rounded(rect, 4), QColor("#000000"))
    p.setPen(QPen(QColor("#2a2c31"), 1.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(rounded(rect, 4))
    inner = rect.adjusted(10, 6, -10, -6)
    if glyph is not None:
        box = QRectF(inner.left(), inner.top(), inner.height() * 1.6, inner.height())
        glyph(p, box)
        inner.setLeft(box.right() + 10)
    glow = QColor(LED)
    glow.setAlpha(70)
    px = min(inner.height() * 0.62, 30)
    p.setFont(font(px, mono=True))
    while px > 10 and p.fontMetrics().horizontalAdvance(text) > inner.width():
        px -= 1  # the whole name, a little smaller when long
        p.setFont(font(px, mono=True))
    for dx, colour in ((1.5, glow), (-1.5, glow), (0, LED)):
        p.setPen(colour)
        p.drawText(inner.translated(dx, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


def knob(p: QPainter, c: QPointF, r: float, angle: float = -40, ring: str | None = None) -> None:
    g = QRadialGradient(c.x() - r * 0.3, c.y() - r * 0.4, r * 1.4)
    g.setColorAt(0, QColor("#4a4d55"))
    g.setColorAt(1, QColor("#16171a"))
    p.setPen(QPen(QColor(ring) if ring else QColor("#05060a"), 2 if ring else 1.2))
    p.setBrush(g)
    p.drawEllipse(c, r, r)
    a = math.radians(angle - 90)
    p.setPen(QPen(QColor("#f2f2f2"), max(1.5, r * 0.14), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(c, QPointF(c.x() + math.cos(a) * r * 0.75, c.y() + math.sin(a) * r * 0.75))


def keys(p: QPainter, rect: QRectF, octaves: int, lit: set[int] | None = None, accent: str = DIGITAL) -> None:
    """A keyboard; *lit*: white-key indexes shown pressed in the accent colour."""
    whites = octaves * 7 + 1
    kw = rect.width() / whites
    for i in range(whites):
        r = QRectF(rect.left() + i * kw + 0.8, rect.top(), kw - 1.6, rect.height())
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        if lit and i in lit:
            g.setColorAt(0, QColor(accent).lighter(130))
            g.setColorAt(1, QColor(accent))
        else:
            g.setColorAt(0, QColor("#d8d8d8"))
            g.setColorAt(0.15, QColor("#fbfbfb"))
            g.setColorAt(1, QColor("#e9e9e9"))
        p.fillPath(rounded(r, 2.5), g)
    for i in range(whites - 1):
        if i % 7 in (2, 6):
            continue
        r = QRectF(rect.left() + (i + 1) * kw - kw * 0.3, rect.top(), kw * 0.6, rect.height() * 0.62)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor("#0a0a0b"))
        g.setColorAt(1, QColor("#2a2b2f"))
        p.fillPath(rounded(r, 2), g)


# --- the project's logo ---------------------------------------------------------


RED = QColor("#ff2a1a")  # the JD-Xi's panel: black, white labels and red light only


def red_knob(p: QPainter, c: QPointF, r: float, angle: float) -> None:
    """A black knob with the red ring of light around it, as on the JD-Xi."""
    glow = QRadialGradient(c, r * 1.55)
    glow.setColorAt(0.6, QColor(255, 42, 26, 120))
    glow.setColorAt(1, QColor(255, 42, 26, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(glow)
    p.drawEllipse(c, r * 1.55, r * 1.55)
    p.setPen(QPen(RED, r * 0.16))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(c, r * 1.12, r * 1.12)
    knob(p, c, r, angle)


def red_button(p: QPainter, r: QRectF, lit: bool) -> None:
    p.fillPath(rounded(r, 3), QColor("#0b0b0c"))
    p.setPen(QPen(RED if lit else QColor("#7a1a12"), 2.4))
    p.setBrush(QColor(255, 42, 26, 150) if lit else Qt.BrushStyle.NoBrush)
    p.drawPath(rounded(r.adjusted(3, 3, -3, -3), 2))


def label(p: QPainter, rect: QRectF, text: str, px: float = 13, colour: str = "#e6e6e6") -> None:
    p.setPen(QColor(colour))
    p.setFont(font(px))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


def panel_top(w: int = 1000, h: int = 560) -> QImage:
    """The instrument seen from above, laid out as the JD-Xi: the controls take the
    back two thirds, the 37 mini keys the front; black, white and red only."""
    image, p = canvas(w, h)
    rect = QRectF(4, 4, w - 8, h - 8)
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, QColor("#1e1f22"))
    g.setColorAt(1, QColor("#0e0f11"))
    p.fillPath(rounded(rect, 18), g)
    p.setPen(QPen(QColor("#3a3c41"), 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(rounded(rect.adjusted(1, 1, -1, -1), 17))
    # the control panel (a slightly lighter plate) over the keys
    plate = QRectF(18, 18, w - 36, 330)
    p.fillPath(rounded(plate, 8), QColor("#141416"))
    p.setPen(QPen(QColor("#2c2e33"), 1.5))
    p.drawPath(rounded(plate, 8))
    # left: display, small buttons, volume
    lcd(p, QRectF(150, 44, 190, 54), "JD-Xi", None)
    for i in range(8):
        red_button(p, QRectF(150 + (i % 4) * 48, 118 + (i // 4) * 40, 36, 28), i == 5)
    red_knob(p, QPointF(70, 130), 22, -30)  # mic gain
    red_knob(p, QPointF(70, 262), 26, 20)  # master volume
    for i in range(4):  # tempo, octave
        red_button(p, QRectF(150 + i * 48, 250, 36, 28), i == 3)
    # centre: part select column and the big vocoder knob
    for i in range(4):
        c = QPointF(390, 60 + i * 50)
        p.setPen(QPen(RED if i == 0 else QColor("#7a1a12"), 3))
        p.setBrush(QColor("#0b0b0c"))
        p.drawEllipse(c, 15, 15)
    red_knob(p, QPointF(500, 110), 44, 60)
    for i in range(4):
        red_button(p, QRectF(372 + i * 50, 250, 36, 28), i == 0)
    # right: filter, amp, LFO, effects
    p.setPen(QPen(QColor("#3a3c41"), 1.5))
    p.drawLine(QPointF(590, 30), QPointF(590, 210))
    for i, name in enumerate(("FILTER", "AMP/ENV", "LFO", "EFFECTS")):
        label(p, QRectF(600 + i * 96, 26, 96, 20), name, 13)
    for i in range(8):
        red_knob(p, QPointF(624 + i * 46, 80), 16, -90 + i * 30)
    for i in range(5):
        red_knob(p, QPointF(650 + i * 72, 156), 16, -40 + i * 25)
    # the 16 step buttons along the front of the panel
    for i in range(16):
        x = 372 + i * ((w - 400) / 16)
        red_button(p, QRectF(x, 300, (w - 400) / 16 - 8, 34), i in (0, 4, 8, 11, 12))
    for i in range(4):
        x = 372 + i * 4 * ((w - 400) / 16)
        p.fillRect(QRectF(x, 290, 4 * ((w - 400) / 16) - 10, 2.5), QColor("#d9d9d9"))
    # pitch / mod and the keys
    for i in range(2):
        r = QRectF(48 + i * 60, 400, 34, 120)
        p.fillPath(rounded(r, 4), QColor("#060607"))
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor("#4a4d55"))
        g.setColorAt(0.5, QColor("#1b1c1f"))
        g.setColorAt(1, QColor("#4a4d55"))
        p.fillPath(rounded(r.adjusted(7, 8, -7, -8), 3), g)
    keys(p, QRectF(170, 362, w - 190, h - 380), 3)
    p.end()
    return image


def logo(size: int = 640) -> QImage:
    """JD-Xi Studio's logo: the instrument in a gentle perspective, its microphone, the name."""
    from PySide6.QtGui import QPolygonF, QTransform

    image, p = canvas(size, size)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    bg = QRadialGradient(size / 2, size * 0.42, size * 0.7)
    bg.setColorAt(0, QColor("#20110e"))
    bg.setColorAt(0.55, QColor("#0d0d0f"))
    bg.setColorAt(1, QColor("#050506"))
    p.fillRect(QRectF(0, 0, size, size), bg)
    top = panel_top()
    tw, th = top.width(), top.height()
    s = size / 640
    # a gentle tilt: the controls (at the back) keep most of their depth
    back_y, front_y, back_in = 112 * s, 384 * s, 34 * s
    left, right = 24 * s, 616 * s
    quad = QPolygonF([QPointF(left + back_in, back_y), QPointF(right - back_in, back_y), QPointF(right, front_y), QPointF(left, front_y)])
    src = QPolygonF([QPointF(0, 0), QPointF(tw, 0), QPointF(tw, th), QPointF(0, th)])
    t = QTransform()
    QTransform.quadToQuad(src, quad, t)
    # the gooseneck microphone, plugged in at the back left
    p.setPen(QPen(QColor("#5a5d64"), 6 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    neck = QPainterPath(QPointF(92 * s, 140 * s))
    neck.cubicTo(QPointF(84 * s, 80 * s), QPointF(120 * s, 52 * s), QPointF(160 * s, 40 * s))
    p.drawPath(neck)
    p.save()
    p.translate(QPointF(176 * s, 34 * s))
    p.rotate(70)
    g = QLinearGradient(-16 * s, 0, 16 * s, 0)
    g.setColorAt(0, QColor("#6b6e75"))
    g.setColorAt(1, QColor("#1b1c1f"))
    p.setPen(QPen(QColor("#0a0a0b"), 1.5))
    p.setBrush(g)
    p.drawRoundedRect(QRectF(-16 * s, -22 * s, 32 * s, 44 * s), 16 * s, 16 * s)
    p.restore()
    # a red glow on the floor and the front edge (the body's thickness)
    glow = QRadialGradient(320 * s, front_y + 18 * s, 300 * s)
    glow.setColorAt(0, QColor(255, 42, 26, 80))
    glow.setColorAt(1, QColor(255, 42, 26, 0))
    p.save()
    p.translate(320 * s, front_y + 18 * s)
    p.scale(1, 0.14)
    p.translate(-320 * s, -(front_y + 18 * s))
    p.fillRect(QRectF(0, front_y - 100 * s, size, 240 * s), glow)
    p.restore()
    front = QPainterPath()
    front.moveTo(left, front_y)
    front.lineTo(right, front_y)
    front.lineTo(right - 4 * s, front_y + 22 * s)
    front.lineTo(left + 4 * s, front_y + 22 * s)
    front.closeSubpath()
    g = QLinearGradient(0, front_y, 0, front_y + 22 * s)
    g.setColorAt(0, QColor("#1d1e22"))
    g.setColorAt(1, QColor("#08090a"))
    p.fillPath(front, g)
    p.save()
    p.setTransform(t)
    p.drawImage(0, 0, top)
    p.restore()
    # the name: white, "Xi" in the panel's red
    p.setFont(font(84 * s))
    fm = p.fontMetrics()
    x0 = (size - fm.horizontalAdvance("JD-Xi")) / 2
    p.setPen(QColor("#f4f4f4"))
    p.drawText(QPointF(x0, 500 * s), "JD-")
    p.setPen(RED)
    p.drawText(QPointF(x0 + fm.horizontalAdvance("JD-"), 500 * s), "Xi")
    f = font(34 * s)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 16 * s)
    p.setFont(f)
    p.setPen(QColor("#d9d9d9"))
    p.drawText(QRectF(8 * s, 512 * s, size, 50 * s), Qt.AlignmentFlag.AlignHCenter, "STUDIO")
    # the step row under the name, red as on the instrument
    for i in range(16):
        r = QRectF(size / 2 - 8 * 26 * s + i * 26 * s + 3 * s, 578 * s, 20 * s, 10 * s)
        p.fillPath(rounded(r, 2 * s), RED if i % 4 == 0 else QColor("#4a120c"))
    p.end()
    return image


# --- the program icon -----------------------------------------------------------


def icon_image(size: int) -> QImage:
    from jdxi_editor.ui.v2.brand import draw_mark

    return draw_mark(size).toImage()


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


def write_icons() -> None:
    from PIL import Image

    big = Image.open(io.BytesIO(png_bytes(icon_image(1024)))).convert("RGBA")
    icon_image(256).save(str(RES / "jdxi_icon.png"))
    icon_image(512).save(str(RES / "jdxi_icon_512.png"))
    # .ico: each size drawn at that size (sharper than scaling one down)
    sizes = (16, 24, 32, 48, 64, 128, 256)
    frames = [Image.open(io.BytesIO(png_bytes(icon_image(s)))).convert("RGBA") for s in sizes]
    frames[-1].save(RES / "jdxi_icon.ico", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    for name in ("jdxi_icon.icns", "jdxi_editor.icns", "jdxi_icon_512.icns"):
        big.save(RES / name)
    for name in ("jdxi_icon.icns", "jdxi_icon_512.icns"):  # the macOS builders read these
        big.save(ROOT / name)


def write_installer_image() -> None:
    """The Inno Setup side image (164x314, as a .bmp)."""
    from PIL import Image

    from jdxi_editor.ui.v2.brand import draw_mark

    image, p = canvas(328, 628)
    g = QLinearGradient(0, 0, 0, 628)
    g.setColorAt(0, QColor("#1b1c1f"))
    g.setColorAt(1, QColor("#0b0c0e"))
    p.fillRect(QRectF(0, 0, 328, 628), g)
    p.fillRect(QRectF(0, 0, 328, 6), QColor(LED))
    p.drawPixmap(64, 120, draw_mark(200))
    p.setPen(QColor("#f2f2f2"))
    p.setFont(font(40))
    p.drawText(QRectF(0, 350, 328, 50), Qt.AlignmentFlag.AlignCenter, "JD-Xi")
    p.setPen(QColor(LED))
    p.drawText(QRectF(0, 398, 328, 50), Qt.AlignmentFlag.AlignCenter, "Studio")
    for i in range(4):
        p.fillPath(rounded(QRectF(76 + i * 46, 520, 36, 22), 4), QColor("#ff2a1a") if i == 0 else QColor("#5a140d"))
    p.end()
    pil = Image.open(io.BytesIO(png_bytes(image))).convert("RGB").resize((164, 314), Image.LANCZOS)
    pil.save(RES / "installer_side.bmp")


# --- what goes where ------------------------------------------------------------

def main() -> None:
    _app = QGuiApplication.instance() or QGuiApplication([])  # fonts need it
    logo().save(str(RES / "jdxi_studio_logo.png"))
    write_icons()
    write_installer_image()
    print("pictures and icons written to", RES)


if __name__ == "__main__":
    main()
