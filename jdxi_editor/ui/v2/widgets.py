"""
Controls of the new interface, each bound to ParamValue objects.

- Knob: drag up/down (Shift: fine), wheel, arrow keys, or type in its field;
  double-click returns a bipolar value to 0
- ChoiceButtons: one button per value (switches, Sub OSC, Octave Shift…)
- WaveButtons / LfoShapeButtons: the waveforms drawn on the buttons
- EnvelopeView: ADSR, or attack/decay/depth for the pitch envelope, with
  points to drag
- FilterCurveView: the low-pass response; drag it sideways for Cutoff, up and
  down for Resonance
- LfoView: the LFO's shape, speed and fade-in
- InfoPanel: name, value, range, explanation and dependencies of the
  parameter under the pointer

Every control reports the parameter under the pointer (or with the keyboard
focus) to an InfoHub, which the InfoPanel shows.
"""

from __future__ import annotations

import math
import random
from typing import Optional, Sequence

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.ui.v2.params import ParamValue

BG = QColor("#121214")
PANEL = QColor("#1b1c1f")
TRACK = QColor("#2e3036")
TEXT = QColor("#ececee")
MUTED = QColor("#a3a6ad")
GRID = QColor("#26282d")


# ------------------------------------------------------------------ info hub
class InfoHub(QObject):
    """Which parameter the pointer (or keyboard focus) is on."""

    shown = Signal(object)  # ParamValue


class _Reports(QObject):
    """Event filter: entering or focusing a widget shows its parameter."""

    def __init__(self, hub: InfoHub, value: ParamValue, parent: QObject):
        super().__init__(parent)
        self.hub, self.pv = hub, value

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Enter, QEvent.Type.FocusIn):
            self.hub.shown.emit(self.pv)
        return False


def report_to(hub: Optional[InfoHub], widget: QWidget, value: ParamValue) -> None:
    if hub is not None:
        widget.installEventFilter(_Reports(hub, value, widget))


def _dim(color: QColor, enabled: bool) -> QColor:
    if enabled:
        return color
    c = QColor(color)
    c.setAlphaF(0.35)
    return c


# ---------------------------------------------------------------------- card
class Card(QFrame):
    """A titled panel; the title is the group name on the JD-Xi display."""

    def __init__(self, title: str, accent: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("v2card")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setStyleSheet(
            "QFrame#v2card { background: #1b1c1f; border: 1px solid #2e3036; border-radius: 10px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)
        head = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {accent}; font-weight: 700; letter-spacing: 2px; font-size: 12px; background: transparent;"
        )
        head.addWidget(title_label)
        head.addStretch()
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet("color: #a3a6ad; font-size: 11px; background: transparent;")
            head.addWidget(sub)
        layout.addLayout(head)
        self.body = layout


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("color: #a3a6ad; font-size: 11px; background: transparent;")
    return label


# ---------------------------------------------------------------------- knob
class Knob(QWidget):
    """A knob for one ParamValue, with its name above and value field below."""

    SIZE = 46

    def __init__(self, value: ParamValue, accent: str, hub: Optional[InfoHub] = None, parent=None):
        super().__init__(parent)
        self.pv = value
        self.accent = QColor(accent)
        self._drag_origin: Optional[QPointF] = None
        self._drag_value = 0.0
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(64)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.name = QLabel(value.info.label)
        self.name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.name.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        layout.addWidget(self.name)
        self.dial = QWidget()
        self.dial.setFixedSize(self.SIZE, self.SIZE)
        self.dial.paintEvent = self._paint_dial  # type: ignore[method-assign]
        self.dial.setCursor(Qt.CursorShape.SizeVerCursor)
        layout.addWidget(self.dial, 0, Qt.AlignmentFlag.AlignHCenter)
        self.field = QLineEdit()
        self.field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.field.setFixedWidth(62)
        self.field.setStyleSheet(
            "QLineEdit { background: #121214; color: #ffffff; border: 1px solid #3a3d44; border-radius: 5px;"
            " font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; padding: 1px 2px; }"
            "QLineEdit:disabled { color: #6b6e75; }"
        )
        self.field.editingFinished.connect(self._typed)
        layout.addWidget(self.field, 0, Qt.AlignmentFlag.AlignHCenter)
        self.setToolTip(f"{value.info.long or value.info.label}: {value.range_text}")
        for widget in (self, self.dial, self.field):
            report_to(hub, widget, value)
        self.dial.installEventFilter(self)
        value.watch(self._show)
        value.watch_enabled(self._enable)

    def sizeHint(self) -> QSize:
        return QSize(66, self.SIZE + 44)

    def _show(self, value: int) -> None:
        if not self.field.hasFocus():
            self.field.setText(self.pv.text(value))
        self.dial.update()

    def _enable(self, enabled: bool) -> None:
        self.setEnabled(enabled)
        self.dial.update()

    def _typed(self) -> None:
        text = self.field.text().strip()
        info = self.pv.info
        for index, choice in enumerate(info.choices):
            if text.lower() == choice.lower():
                self.pv.setValue(index)
                return
        if info.parse is not None:
            parsed = info.parse(text)
            if parsed is None:
                self._show(self.pv.value())
                return
            self.pv.setValue(parsed)
            self._show(self.pv.value())
            return
        number = "".join(ch for ch in text.replace(",", ".") if ch.isdigit() or ch in "+-.")
        try:
            value = round(float(number) * info.scale) if info.scale > 1 else int(float(number))
        except ValueError:
            self._show(self.pv.value())
            return
        if info.show_negative:
            value = abs(value)
        self.pv.setValue(value)
        self._show(self.pv.value())

    def _fraction(self, value: int) -> float:
        span = self.pv.maximum - self.pv.minimum
        return (value - self.pv.minimum) / span if span else 0.0

    def _paint_dial(self, _event) -> None:
        p = QPainter(self.dial)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self.isEnabled()
        r = QRectF(6, 6, self.SIZE - 12, self.SIZE - 12)
        start, sweep = 225.0, -270.0  # degrees, counter-clockwise from 3 o'clock
        p.setPen(QPen(TRACK, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, int(start * 16), int(sweep * 16))
        frac = self._fraction(self.pv.value())
        bipolar = self.pv.minimum < 0 < self.pv.maximum
        origin = self._fraction(0) if bipolar else 0.0
        p.setPen(QPen(_dim(self.accent, enabled), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        a0 = start + sweep * origin
        p.drawArc(r, int(a0 * 16), int(sweep * (frac - origin) * 16))
        # pointer
        angle = math.radians(start + sweep * frac)
        c = r.center()
        tip = QPointF(c.x() + math.cos(angle) * (r.width() / 2 - 8), c.y() - math.sin(angle) * (r.height() / 2 - 8))
        p.setPen(QPen(_dim(TEXT, enabled), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(c, tip)
        if self.hasFocus() or self.field.hasFocus():
            p.setPen(QPen(self.accent, 1, Qt.PenStyle.DotLine))
            p.drawEllipse(r.adjusted(-3, -3, 3, 3))
        p.end()

    # --- dragging, wheel and keys on the dial
    def eventFilter(self, obj, event) -> bool:
        if obj is not self.dial or not self.isEnabled():
            return False
        t = event.type()
        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.position()
            self._drag_value = float(self.pv.value())
            self.setFocus()
            return True
        if t == QEvent.Type.MouseMove and self._drag_origin is not None:
            fine = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            pixels = 600.0 if fine else 160.0  # pixels for the whole range
            delta = (self._drag_origin.y() - event.position().y()) / pixels
            span = self.pv.maximum - self.pv.minimum
            self.pv.setValue(self._drag_value + delta * span)
            return True
        if t == QEvent.Type.MouseButtonRelease:
            self._drag_origin = None
            return True
        if t == QEvent.Type.MouseButtonDblClick:
            if self.pv.minimum < 0 < self.pv.maximum:
                self.pv.setValue(0)
            return True
        if t == QEvent.Type.Wheel:
            steps = 1 if event.angleDelta().y() > 0 else -1
            self.pv.setValue(self.pv.value() + steps * max(1, self.pv.info.step))
            return True
        return False

    def keyPressEvent(self, event) -> None:
        step = max(1, self.pv.info.step)
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Right):
            self.pv.setValue(self.pv.value() + step)
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_Left):
            self.pv.setValue(self.pv.value() - step)
        elif key == Qt.Key.Key_PageUp:
            self.pv.setValue(self.pv.value() + step * 10)
        elif key == Qt.Key.Key_PageDown:
            self.pv.setValue(self.pv.value() - step * 10)
        else:
            super().keyPressEvent(event)


# ------------------------------------------------------------ choice buttons
class ChoiceButtons(QWidget):
    """One checkable button per value; for switches and short lists."""

    def __init__(
        self,
        value: ParamValue,
        accent: str,
        hub: Optional[InfoHub] = None,
        labels: Optional[Sequence[str]] = None,
        values: Optional[Sequence[int]] = None,
        show_name: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.pv = value
        self.values = list(values) if values is not None else list(range(value.minimum, value.maximum + 1))
        labels = list(labels) if labels is not None else [value.info.format(v) for v in self.values]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        if show_name:
            name = QLabel(value.info.label)
            name.setMinimumWidth(70)
            name.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
            layout.addWidget(name)
            report_to(hub, name, value)
        strip = QFrame()
        strip.setStyleSheet("QFrame { background: #121214; border: 1px solid #3a3d44; border-radius: 7px; }")
        strip_layout = QHBoxLayout(strip)
        strip_layout.setContentsMargins(2, 2, 2, 2)
        strip_layout.setSpacing(2)
        self.buttons: list[QPushButton] = []
        for v, text in zip(self.values, labels):
            button = self._make_button(v, text)
            button.setCheckable(True)
            button.setMinimumHeight(28)
            button.setStyleSheet(
                "QPushButton { background: transparent; color: #c9cbd1; border: 0; border-radius: 5px;"
                " padding: 2px 9px; font-size: 11px; font-weight: 600; }"
                f"QPushButton:checked {{ background: {accent}; color: #0e1116; }}"
                "QPushButton:disabled { color: #5b5f68; }"
                "QPushButton:checked:disabled { background: #2e3036; color: #8a8d94; }"
            )
            button.clicked.connect(lambda _=False, v=v: self.pv.setValue(v))
            report_to(hub, button, value)
            strip_layout.addWidget(button)
            self.buttons.append(button)
        layout.addWidget(strip)
        layout.addStretch()
        value.watch(self._show)
        value.watch_enabled(self.setEnabled)

    def _make_button(self, value: int, text: str) -> QPushButton:
        return QPushButton(text)

    def _show(self, value: int) -> None:
        for v, button in zip(self.values, self.buttons):
            button.setChecked(v == value)


def _wave_path(name: str, rect: QRectF, duty: float = 0.5) -> QPainterPath:
    """Two cycles of a waveform inside rect."""
    path = QPainterPath()
    x0, w, top, bottom = rect.left(), rect.width(), rect.top(), rect.bottom()
    mid = (top + bottom) / 2
    cycles = 2
    cw = w / cycles
    if name == "SAW":
        path.moveTo(x0, bottom)
        for i in range(cycles):
            path.lineTo(x0 + (i + 1) * cw, top)
            path.lineTo(x0 + (i + 1) * cw, bottom)
    elif name == "TRI":
        path.moveTo(x0, mid)
        for i in range(cycles):
            b = x0 + i * cw
            path.lineTo(b + cw * 0.25, top)
            path.lineTo(b + cw * 0.75, bottom)
            path.lineTo(b + cw, mid)
    elif name in ("SQR", "PW-SQR"):
        path.moveTo(x0, bottom)
        for i in range(cycles):
            b = x0 + i * cw
            path.lineTo(b, top)
            path.lineTo(b + cw * duty, top)
            path.lineTo(b + cw * duty, bottom)
            path.lineTo(b + cw, bottom)
    elif name in ("SIN", "SINE"):
        steps = 48
        for s in range(steps + 1):
            x = x0 + w * s / steps
            y = mid - math.sin(2 * math.pi * cycles * s / steps) * (bottom - top) / 2
            path.lineTo(x, y) if s else path.moveTo(x, y)
    elif name == "S&H":
        rnd = random.Random(7)
        n = 6
        for s in range(n):
            y = top + rnd.random() * (bottom - top)
            x1, x2 = x0 + w * s / n, x0 + w * (s + 1) / n
            path.lineTo(x1, y) if s else path.moveTo(x1, y)
            path.lineTo(x2, y)
    elif name == "RND":
        rnd = random.Random(11)
        pts = [top + rnd.random() * (bottom - top) for _ in range(7)]
        steps = 48
        for s in range(steps + 1):
            t = s / steps * (len(pts) - 1)
            i = min(int(t), len(pts) - 2)
            f = t - i
            f = f * f * (3 - 2 * f)
            y = pts[i] * (1 - f) + pts[i + 1] * f
            x = x0 + w * s / steps
            path.lineTo(x, y) if s else path.moveTo(x, y)
    elif name == "NOISE":
        rnd = random.Random(3)
        steps = 40
        for s in range(steps + 1):
            x, y = x0 + w * s / steps, top + rnd.random() * (bottom - top)
            path.lineTo(x, y) if s else path.moveTo(x, y)
    elif name in ("SUPER-SAW", "SP-SAW"):
        for shift in (0.0, 0.3, 0.6):  # detuned saws on top of each other
            steps = 60
            previous = None
            for k in range(steps + 1):
                x = x0 + w * k / steps
                phase = ((x - x0) / cw + shift) % 1.0
                y = bottom - (bottom - top) * phase
                if previous is None or phase < previous:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
                previous = phase
    elif name == "PCM":
        steps = 60
        for s in range(steps + 1):
            t = s / steps
            env = math.exp(-2.2 * t)
            y = mid - (bottom - top) / 2 * env * (0.65 * math.sin(2 * math.pi * 5 * t) + 0.35 * math.sin(2 * math.pi * 13 * t))
            x = x0 + w * t
            path.lineTo(x, y) if s else path.moveTo(x, y)
    return path


class _WaveButton(QPushButton):
    def __init__(self, name: str, owner: "WaveButtons"):
        super().__init__("")
        self.wave = name
        self.owner = owner
        self.setMinimumSize(owner.button_width, 44)
        self.setToolTip(name)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#0e1116") if self.isChecked() else QColor("#c9cbd1")
        color = _dim(color, self.isEnabled())
        r = QRectF(self.rect()).adjusted(10, 8, -10, -18)
        p.setPen(QPen(color, 2))
        p.drawPath(_wave_path(self.wave, r, self.owner.duty()))
        p.setFont(QFont(self.font().family(), 8, QFont.Weight.DemiBold))
        p.drawText(QRectF(self.rect()).adjusted(0, 0, 0, -3), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.wave)
        p.end()


class WaveButtons(ChoiceButtons):
    """Waveforms drawn on the buttons; PW-SQR follows the pulse width."""

    def __init__(self, value: ParamValue, accent: str, hub=None, pulse_width: Optional[ParamValue] = None, show_name=False, button_width: int = 50, parent=None):
        self.pulse_width = pulse_width
        self.button_width = button_width
        super().__init__(value, accent, hub, labels=list(value.info.choices), show_name=show_name, parent=parent)
        if pulse_width is not None:
            pulse_width.watch(lambda _v: [b.update() for b in self.buttons])

    def duty(self) -> float:
        if self.pulse_width is None:
            return 0.5
        # Pulse Width 0 is close to a square wave; higher values narrow the pulse
        return 0.5 - 0.42 * self.pulse_width.value() / 127

    def _make_button(self, value: int, text: str) -> QPushButton:
        return _WaveButton(text, self)


# ------------------------------------------------------------- note value combo
class NoteCombo(QWidget):
    """A list of values (e.g. Sync Note) with the parameter name."""

    def __init__(self, value: ParamValue, hub=None, parent=None):
        super().__init__(parent)
        self.pv = value
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        name = QLabel(value.info.label)
        name.setMinimumWidth(78)
        name.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        self.combo = QComboBox()
        self.combo.setStyleSheet(
            "QComboBox { background: #121214; color: #ffffff; border: 1px solid #3a3d44; border-radius: 5px;"
            " padding: 2px 6px; font-size: 12px; }"
            "QComboBox:disabled { color: #6b6e75; }"
            "QComboBox QAbstractItemView { background: #1b1c1f; color: #e6e6e6;"
            " selection-background-color: #333333; }"
        )
        self.combo.addItems(list(value.info.choices))
        self.combo.currentIndexChanged.connect(lambda i: self.pv.setValue(i))
        layout.addWidget(name)
        layout.addWidget(self.combo)
        layout.addStretch()
        for w in (name, self.combo):
            report_to(hub, w, value)
        value.watch(self._show)
        value.watch_enabled(self.setEnabled)

    def _show(self, value: int) -> None:
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(value)
        self.combo.blockSignals(False)


# ------------------------------------------------------------------ graphs
class _Graph(QWidget):
    """Base of the drawn views: a dark rounded area with a grid."""

    def __init__(self, accent: str, hub: Optional[InfoHub], height: int = 120, parent=None):
        super().__init__(parent)
        self.accent = QColor(accent)
        self.hub = hub
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self._drag: Optional[int] = None
        self._hover: Optional[int] = None

    def plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(10, 10, -10, -16)

    def _background(self, p: QPainter) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(BG)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        p.setPen(QPen(GRID, 1))
        r = self.plot_rect()
        for i in range(1, 4):
            y = r.top() + r.height() * i / 4
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))

    def handles(self) -> list[tuple[QPointF, ParamValue]]:
        return []

    def _handle_at(self, pos: QPointF) -> Optional[int]:
        for i, (pt, _pv) in enumerate(self.handles()):
            if (pt - pos).manhattanLength() < 14:
                return i
        return None

    def _draw_handles(self, p: QPainter) -> None:
        for i, (pt, pv) in enumerate(self.handles()):
            active = i in (self._drag, self._hover)
            p.setPen(QPen(QColor("#0e1116"), 2))
            p.setBrush(_dim(self.accent if active else TEXT, pv.is_enabled()))
            p.drawEllipse(pt, 6 if active else 5, 6 if active else 5)

    def mousePressEvent(self, event) -> None:
        self._drag = self._handle_at(event.position())
        if self._drag is None:
            self._drag = self.nearest_handle(event.position())
        if self._drag is not None:
            self.drag_to(self._drag, event.position())
        self.update()

    def nearest_handle(self, pos: QPointF) -> Optional[int]:
        return None

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._drag is not None:
            self.drag_to(self._drag, pos)
        else:
            hover = self._handle_at(pos)
            if hover != self._hover:
                self._hover = hover
                self.update()
            if hover is not None and self.hub is not None:
                self.hub.shown.emit(self.handles()[hover][1])
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event) -> None:
        self._drag = None
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()

    def drag_to(self, index: int, pos: QPointF) -> None:
        pass


class EnvelopeView(_Graph):
    """ADSR (attack, decay, sustain, release) or pitch (attack, decay, depth)."""

    def __init__(self, accent: str, hub, attack, decay, sustain=None, release=None, depth=None, parent=None):
        super().__init__(accent, hub, 110, parent)
        self.a, self.d, self.s, self.r, self.depth = attack, decay, sustain, release, depth
        for pv in (attack, decay, sustain, release, depth):
            if pv is not None:
                pv.watch(lambda _v: self.update())
                pv.watch_enabled(lambda _e: self.update())
        self.setToolTip(tr("Drag the points to change the envelope"))

    def _x(self, r: QRectF, frac: float, slot: int, slots: int) -> float:
        return r.left() + r.width() * (slot + frac) / slots

    def points(self) -> list[QPointF]:
        r = self.plot_rect()
        a = self.a.value() / 127
        d = self.d.value() / 127
        if self.depth is not None:  # pitch: rise to depth, back to the note
            mid = r.center().y()
            dep = self.depth.value() / 63
            xa = r.left() + r.width() * 0.45 * a
            xd = xa + r.width() * 0.45 * d
            return [QPointF(r.left(), mid), QPointF(xa, mid - dep * r.height() / 2), QPointF(xd, mid), QPointF(r.right(), mid)]
        s = self.s.value() / 127
        rel = self.r.value() / 127
        seg = r.width() * 0.27
        xa = r.left() + seg * a
        xd = xa + seg * d
        xs = xd + r.width() * 0.19
        xr = xs + seg * rel
        ys = r.bottom() - s * r.height()
        return [QPointF(r.left(), r.bottom()), QPointF(xa, r.top()), QPointF(xd, ys), QPointF(xs, ys), QPointF(xr, r.bottom())]

    def handles(self):
        pts = self.points()
        if self.depth is not None:
            return [(pts[1], self.a), (pts[2], self.d)]
        return [(pts[1], self.a), (pts[2], self.d), (pts[2], self.s), (pts[4], self.r)]

    def nearest_handle(self, pos):
        hs = self.handles()
        best = min(range(len(hs)), key=lambda i: abs(hs[i][0].x() - pos.x()))
        return best

    def drag_to(self, index: int, pos: QPointF) -> None:
        r = self.plot_rect()
        pts = self.points()
        if self.depth is not None:
            if index == 0:
                self.a.setValue((pos.x() - r.left()) / (r.width() * 0.45) * 127)
                self.depth.setValue((r.center().y() - pos.y()) / (r.height() / 2) * 63)
            else:
                self.d.setValue((pos.x() - pts[1].x()) / (r.width() * 0.45) * 127)
            return
        seg = r.width() * 0.27
        if index == 0:
            self.a.setValue((pos.x() - r.left()) / seg * 127)
        elif index in (1, 2):
            self.d.setValue((pos.x() - pts[1].x()) / seg * 127)
            self.s.setValue((r.bottom() - pos.y()) / r.height() * 127)
        else:
            self.r.setValue((pos.x() - pts[3].x()) / seg * 127)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        enabled = all(pv.is_enabled() for pv in (self.a, self.d) if pv is not None)
        pts = self.points()
        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        fill = QPainterPath(path)
        r = self.plot_rect()
        base = r.center().y() if self.depth is not None else r.bottom()
        fill.lineTo(pts[-1].x(), base)
        fill.lineTo(pts[0].x(), base)
        color = _dim(self.accent, enabled)
        shade = QColor(color)
        shade.setAlphaF(0.16 if enabled else 0.06)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shade)
        p.drawPath(fill)
        p.setPen(QPen(color, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        if self.depth is None:  # key released here
            p.setPen(QPen(MUTED, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(pts[3].x(), r.top()), QPointF(pts[3].x(), r.bottom()))
            p.setFont(QFont(self.font().family(), 7))
            p.drawText(QPointF(pts[3].x() + 3, r.bottom() + 12), tr("key off"))
        self._draw_handles(p)
        p.end()


class FilterCurveView(_Graph):
    """Low-pass response: x = frequency (log), handle = cutoff and resonance."""

    def __init__(self, accent: str, hub, cutoff: ParamValue, resonance: ParamValue, mode: ParamValue, parent=None):
        super().__init__(accent, hub, 130, parent)
        self.cutoff, self.resonance, self.mode = cutoff, resonance, mode
        for pv in (cutoff, resonance, mode):
            pv.watch(lambda _v: self.update())
        self.setToolTip(tr("Drag sideways for Cutoff, up and down for Resonance"))

    @staticmethod
    def frequency(cutoff: int) -> float:
        return 20.0 * 1000.0 ** (cutoff / 127.0)

    def _response_db(self, f: float) -> float:
        fc = self.frequency(self.cutoff.value())
        q = 0.7 + self.resonance.value() / 127.0 * 8.0
        u = f / fc
        resonant = 1.0 / math.sqrt((1 - u * u) ** 2 + (u / q) ** 2)
        plain = 1.0 / math.sqrt((1 - u * u) ** 2 + (u / 0.707) ** 2)
        return 20 * math.log10(max(resonant * plain, 1e-6))

    def _x(self, f: float) -> float:
        r = self.plot_rect()
        return r.left() + r.width() * math.log10(f / 20.0) / 3.0

    def _y(self, db: float) -> float:
        r = self.plot_rect()
        db = max(-48.0, min(24.0, db))
        return r.top() + r.height() * (24.0 - db) / 72.0

    def handles(self):
        fc = self.frequency(self.cutoff.value())
        db = self._response_db(fc)
        return [(QPointF(self._x(fc), self._y(db)), self.cutoff)]

    def nearest_handle(self, pos):
        return 0

    def drag_to(self, index: int, pos: QPointF) -> None:
        if not self.mode.value():
            return  # BYPASS
        r = self.plot_rect()
        frac = (pos.x() - r.left()) / r.width()
        self.cutoff.setValue(frac * 127)
        # higher on the screen = more resonance; 0 dB line = none
        top_db = (r.top() + r.height() * 24 / 72 - pos.y()) / (r.height() * 24 / 72)
        self.resonance.setValue(max(0.0, top_db) * 127)
        if self.hub is not None:
            self.hub.shown.emit(self.cutoff)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        p.setFont(QFont(self.font().family(), 7))
        p.setPen(MUTED)
        for f, label in ((100, "100"), (1000, "1k"), (10000, "10k")):
            x = self._x(f)
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(MUTED)
            p.drawText(QPointF(x + 2, r.bottom() + 12), f"{label} Hz")
        bypass = not self.mode.value()
        color = _dim(self.accent, not bypass)
        path = QPainterPath()
        steps = 120
        for s in range(steps + 1):
            f = 20.0 * 1000.0 ** (s / steps)
            db = 0.0 if bypass else self._response_db(f)
            pt = QPointF(self._x(f), self._y(db))
            path.lineTo(pt) if s else path.moveTo(pt)
        fill = QPainterPath(path)
        fill.lineTo(r.right(), r.bottom())
        fill.lineTo(r.left(), r.bottom())
        shade = QColor(color)
        shade.setAlphaF(0.14 if not bypass else 0.05)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shade)
        p.drawPath(fill)
        p.setPen(QPen(color, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        if bypass:
            p.setPen(MUTED)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, tr("BYPASS: no filter"))
        else:
            self._draw_handles(p)
        p.end()


class LfoView(_Graph):
    """The LFO over time: shape, speed (Rate or Sync Note) and fade-in."""

    def __init__(self, accent, hub, shape, rate, fade, sync, note, parent=None):
        super().__init__(accent, hub, 90, parent)
        self.shape, self.rate, self.fade, self.sync, self.note = shape, rate, fade, sync, note
        for pv in (shape, rate, fade, sync, note):
            if pv is not None:  # the Modulation LFO has no fade
                pv.watch(lambda _v: self.update())

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        name = self.shape.text()
        if self.sync.value():
            cycles = 2.0
            speed = tr("1 cycle = {note}").format(note=self.note.text())
        else:
            cycles = 1.0 + self.rate.value() / 127 * 9
            speed = tr("Rate {rate}").format(rate=self.rate.value())
        fade = self.fade.value() / 127 * 0.6 if self.fade is not None else 0.0
        path = QPainterPath()
        steps = 240
        rnd = random.Random(5)
        levels = [rnd.uniform(-1, 1) for _ in range(64)]
        for s in range(steps + 1):
            t = s / steps
            phase = (t * cycles) % 1.0
            k = int(t * cycles)
            if name == "TRI":
                v = 1 - 4 * abs(phase - 0.25) if phase < 0.75 else 4 * phase - 4
            elif name == "SIN":
                v = math.sin(2 * math.pi * phase)
            elif name == "SAW":
                v = 1 - 2 * phase
            elif name == "SQR":
                v = 1 if phase < 0.5 else -1
            elif name == "S&H":
                v = levels[k % len(levels)]
            else:
                f = phase * phase * (3 - 2 * phase)
                v = levels[k % len(levels)] * (1 - f) + levels[(k + 1) % len(levels)] * f
            amp = min(1.0, t / fade) if fade > 0 else 1.0
            pt = QPointF(r.left() + r.width() * t, r.center().y() - v * amp * r.height() / 2 * 0.9)
            path.lineTo(pt) if s else path.moveTo(pt)
        p.setPen(QPen(self.accent, 2))
        p.drawPath(path)
        p.setPen(MUTED)
        p.setFont(QFont(self.font().family(), 7))
        p.drawText(QPointF(r.left(), r.bottom() + 12), speed)
        if fade > 0:  # where the LFO reaches full depth
            x = r.left() + r.width() * fade
            p.setPen(QPen(MUTED, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(MUTED)
            p.drawText(QPointF(x + 3, r.top() + 9), tr("full depth"))
        p.end()


# ----------------------------------------------------------------- info panel
class InfoPanel(QFrame):
    """What the parameter under the pointer is, does and depends on."""

    def __init__(self, accent: str, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.pv: Optional[ParamValue] = None
        self._watched: set[int] = set()
        self.setObjectName("v2info")
        self.setStyleSheet(
            "QFrame#v2info { background: #1b1c1f; border: 1px solid #2e3036; border-radius: 10px; }"
            "QLabel { background: transparent; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(6)
        head = QLabel(tr("PARAMETER"))
        head.setStyleSheet(f"color: {accent}; font-weight: 700; letter-spacing: 2px; font-size: 12px;")
        layout.addWidget(head)
        self.group = QLabel()
        self.group.setStyleSheet("color: #a3a6ad; font-size: 11px;")
        self.name = QLabel(tr("Point at a control"))
        self.name.setStyleSheet("color: #ffffff; font-size: 17px; font-weight: 700;")
        self.name.setWordWrap(True)
        self.long = QLabel()
        self.long.setStyleSheet("color: #c9cbd1; font-size: 12px;")
        self.long.setWordWrap(True)
        self.value = QLabel()
        self.value.setStyleSheet(
            f"color: {accent}; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 22px; font-weight: 600;"
        )
        self.range = QLabel()
        self.range.setStyleSheet("color: #a3a6ad; font-size: 11px;")
        self.range.setWordWrap(True)
        self.description = QLabel(
            tr("Its name on the display, range and explanation appear here, with what it depends on.")
        )
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color: #ececee; font-size: 13px; line-height: 140%;")
        self.depends = QLabel()
        self.depends.setWordWrap(True)
        self.depends.setStyleSheet("color: #ffd27a; font-size: 12px;")
        self.source = QLabel()
        self.source.setStyleSheet("color: #8a8d94; font-size: 11px;")
        for w in (self.group, self.name, self.long, self.value, self.range, self.description, self.depends):
            layout.addWidget(w)
        layout.addStretch()
        layout.addWidget(self.source)
        self.setMinimumWidth(240)

    def show_text(self, group: str, name: str, description: str, source: str = "") -> None:
        """A control that is not a JD-Xi parameter (Pattern, player): its name and what it does."""
        self.pv = None
        self.group.setText(group)
        self.name.setText(name)
        self.long.setText("")
        self.value.setText("")
        self.range.setText("")
        self.description.setText(description)
        self.depends.setText("")
        self.source.setText(source)

    def show_param(self, pv: ParamValue) -> None:
        self.pv = pv
        if id(pv) not in self._watched:  # each value watched once
            self._watched.add(id(pv))
            pv.watch(lambda _v, pv=pv: self._refresh_value(pv))
            pv.watch_enabled(lambda _e, pv=pv: self._refresh_value(pv))
        info = pv.info
        self.group.setText(f"{info.area}: {info.group}" if info.area else info.group)
        self.name.setText(info.label)
        self.long.setText(info.long if info.long and info.long != info.label else "")
        self.range.setText(tr("Range: {range}").format(range=pv.range_text))
        self.description.setText(info.description)
        if info.source:
            self.source.setText(info.source)
        else:
            self.source.setText(
                tr("Parameter Guide, p. {page}").format(page=info.page) if info.page else tr("MIDI Implementation")
            )
        self._refresh_value(pv)

    def _refresh_value(self, pv: ParamValue) -> None:
        if pv is not self.pv:
            return
        self.value.setText(pv.text())
        note = pv.info.depends
        if not pv.is_enabled():
            note = tr("Inactive now. {reason}").format(reason=note)
        self.depends.setText(note)
