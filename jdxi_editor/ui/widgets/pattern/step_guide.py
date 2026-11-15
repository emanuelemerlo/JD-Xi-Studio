"""
Step Guide

The grey step-length lines printed above the JD-Xi's 16 step buttons, drawn
above the Pattern Editor's steps: groups of 3 steps (across the first 12),
of 8, and of 4.

    ───── ───── ───── ─────
    ─────────────── ───────────────
    ─────── ─────── ─────── ───────
    [ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ][ ]

Each line runs from the left edge of its first step to the right edge of its
last, read from the step buttons themselves, so it lines up however the row
is laid out.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

# (steps per line, number of lines) for each row, top to bottom
GUIDE_ROWS = ((3, 4), (8, 2), (4, 4))
# The note printed before each line on the JD-Xi: (flags, triplet) — an eighth-note triplet,
# a thirty-second note, a sixteenth... as drawn on the panel (one flag on the first and last
# rows, three on the middle one)
GUIDE_NOTES = ((1, True), (3, False), (1, False))
NOTE_NAMES = ("1/8 triplet", "1/32", "1/16")
LINE_COLOR = "#8C8C8C"
LINE_WIDTH = 2
ROW_SPACING = 15  # px between rows: room for the note before each line
MARGIN = 6  # px above the first row and below the last


class StepGuide(QWidget):
    """Step-length lines above a row of step buttons."""

    def __init__(
        self,
        step_buttons: Callable[[], Sequence[QWidget]],
        parent: Optional[QWidget] = None,
        row_spacing: int = ROW_SPACING,
        margin: int = MARGIN,
        line_width: int = LINE_WIDTH,
        notes: bool = False,
    ):
        """
        :param step_buttons: returns the step buttons the lines are drawn over
            (one row of the current measure)
        :param row_spacing, margin, line_width: smaller over smaller steps (the keyboard window)
        :param notes: the note before each line, as on the panel: the line then starts at the
            middle of its first step, the note over the step's left half
        """
        super().__init__(parent)
        self._step_buttons = step_buttons
        self.row_spacing, self.margin, self.line_width = row_spacing, margin, line_width
        self.notes = notes
        self.top = row_spacing if notes else margin  # room above for the first row's notes
        self.setFixedHeight(self.top + margin + (len(GUIDE_ROWS) - 1) * row_spacing + line_width)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def segments(self) -> list[tuple[int, int, int]]:
        """(x1, x2, y) of every line, in this widget's coordinates."""
        buttons = list(self._step_buttons() or [])
        if not buttons:
            return []
        edges = []
        for button in buttons:
            left = button.mapTo(self.window(), QPoint(0, 0))
            left = self.mapFrom(self.window(), left).x()
            edges.append((left, left + button.width() - 1))
        result = []
        for row, (length, count) in enumerate(GUIDE_ROWS):
            y = self.top + row * self.row_spacing
            for group in range(count):
                first, last = group * length, (group + 1) * length - 1
                if last < len(edges):
                    left = edges[first][0]
                    if self.notes:  # from the middle of the first step, as on the panel
                        left = (edges[first][0] + edges[first][1]) // 2 + 2
                    result.append((left, edges[last][1], y))
        return result

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        pen = QPen(QColor(LINE_COLOR), self.line_width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        for x1, x2, y in self.segments():
            painter.drawLine(x1, y, x2, y)
        if self.notes:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rows = [y for _x1, _x2, y in self.segments()]
            for x1, _x2, y in self.segments():
                row = sorted(set(rows)).index(y)
                flags, triplet = GUIDE_NOTES[row]
                self._draw_note(painter, x1 - 3, y, flags, triplet)
        painter.end()

    def _draw_note(self, painter: QPainter, right: int, y: int, flags: int, triplet: bool) -> None:
        """A small note whose head sits on the line's height, ending at `right`."""
        size = max(5, self.row_spacing - 3)  # the note's height, within its row
        colour = QColor(LINE_COLOR)
        stem_x = right - (7 if triplet else 3)
        head_w, head_h = 6, 4
        painter.setPen(QPen(colour, 1.2))
        painter.setBrush(colour)
        painter.drawEllipse(stem_x - head_w + 1, y - head_h // 2, head_w, head_h)
        top = y - size + 2
        painter.drawLine(stem_x, y, stem_x, top)
        for i in range(flags):
            fy = top + i * 3
            painter.drawLine(QPoint(stem_x, round(fy)), QPoint(stem_x + 4, round(fy + 3)))
        if triplet:
            font = painter.font()
            font.setPixelSize(max(6, size - 2))
            painter.setFont(font)
            painter.drawText(stem_x + 3, y + 4, "3")
        painter.setBrush(Qt.BrushStyle.NoBrush)
