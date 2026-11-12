"""Make a label's text fit its width by making the font a little smaller (never larger)."""

from __future__ import annotations

import re

from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLabel

MIN_PX = 8


def _need(label: QLabel, font) -> int:
    return QFontMetrics(font).horizontalAdvance(label.text().replace("&", ""))


def fit_text(label: QLabel) -> bool:
    """Shrink *label*'s font (pixel size, in its style sheet when it sets one) until the
    text fits its contents width; returns True when it changed something."""
    if label.wordWrap() or "\n" in label.text() or label.width() <= 1:
        return False
    room = label.contentsRect().width()
    font = label.font()
    if _need(label, font) <= room:
        return False
    px = font.pixelSize()
    if px <= 0:  # a point size: as pixels at this screen's resolution
        px = round(font.pointSizeF() * label.logicalDpiY() / 72)
    start = px
    while px > MIN_PX:
        px -= 1
        font.setPixelSize(px)
        if _need(label, font) <= room:
            break
    if px == start:
        return False
    sheet = label.styleSheet()
    label.setFont(font)
    # a style sheet's font-size wins over setFont: change it there too
    if re.search(r"font-size\s*:", sheet):
        label.setStyleSheet(re.sub(r"font-size\s*:\s*[^;}]+", f"font-size: {px}px", sheet))
    elif "{" not in sheet:  # plain declarations (or none): add the size
        label.setStyleSheet(sheet.rstrip() + f" font-size: {px}px;")
    return True
