"""
New Effects editor: Effect 1, Effect 2, Delay and Reverb of the current program.

Every parameter of the Parameter Guide's "Effects" pages (p. 26-27) and of
the Version 1.50 side-chain compressor has a control; only the parameters of
the selected effect type are shown, as on the JD-Xi display. The signal chain
at the top shows how the effects are connected (Effect 1 Output Assign) and
which types are active.

Addresses (MIDI Implementation, Program Effect 1/2, Delay, Reverb):
18 00 02/04/06/08 00. Effect parameters are 4 nibbles around 32768, at
00 11 + 4(n-1) for Effect 1/2, 00 04 + 4(n-1) for Delay, 00 03 + 4(n-1) for
Reverb. Which parameter number holds which setting of a type is not in the
Roland documents; the numbering is the one of the JD-Xi Manager, see
unverified() for those still to be checked on an instrument.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.midi.sysex.request.midi_requests import MidiRequests
from jdxi_editor.ui.v2.framework import Block, PSpec, V2Editor
from jdxi_editor.ui.v2.params import ParamValue
from jdxi_editor.ui.v2.widgets import ChoiceButtons, _Graph
from jdxi_editor.ui.v2 import density

ACCENT = "#2dd4bf"  # teal: orange is Digital 2

NOTES = [
    "1/96", "1/64", "1/48", "1/32", "1/24", "3/64", "1/16", "1/12", "3/32", "1/8", "1/6",
    "3/16", "1/4", "1/3", "3/8", "1/2", "2/3", "3/4", "1", "4/3", "3/2", "2",
]
HF_DAMP = [
    "200 Hz", "250 Hz", "315 Hz", "400 Hz", "500 Hz", "630 Hz", "800 Hz", "1000 Hz", "1250 Hz",
    "1600 Hz", "2000 Hz", "2500 Hz", "3150 Hz", "4000 Hz", "5000 Hz", "6300 Hz", "8000 Hz", "BYPASS",
]
RATIOS = [f"{r}:1" for r in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)] + ["inf:1"]
ATTACKS = [
    "0.05", "0.06", "0.07", "0.08", "0.09", "0.10", "0.20", "0.30", "0.40", "0.50", "0.60", "0.70",
    "0.80", "0.90", "1.0", "2.0", "3.0", "4.0", "5.0", "6.0", "7.0", "8.0", "9.0", "10.0", "15.0",
    "20.0", "25.0", "30.0", "35.0", "40.0", "45.0", "50.0",
]
RELEASES = [
    "0.05", "0.07", "0.10", "0.50", "1", "5", "10", "17", "25", "50", "75", "100", "200", "300",
    "400", "500", "600", "700", "800", "900", "1000", "1200", "1500", "2000",
]
_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES = [f"{_NAMES[n % 12]}{n // 12 - 1}" for n in range(128)]  # C-1 … G9
BALANCE = [f"D{100 - v}:{v}W" for v in range(101)]  # D100:0W … D0:100W

EFX1_TYPES = ["Thru", "Distortion", "Fuzz", "Compressor", "Bit Crusher"]
EFX2_TYPES = ["Thru", "Flanger", "Phaser", "Ring Mod", "Slicer"]
EFX2_TYPE_VALUES = [0, 5, 6, 7, 8]  # as sent: MIDI Implementation, EFX2 Type (0, 5 - 8)

def unverified() -> dict[str, str]:
    """Parameter numbers taken from the JD-Xi Manager, not from a Roland document."""
    every = tr("all parameters")
    return {
        "Phaser": "Manual (6), Level (7)",
        "Ring Mod": every,
        "Slicer": every,
        "Compressor": tr("Side Time, sent as milliseconds (60-1000)"),
    }


def _program(lmb: int) -> JDXiSysExAddress:
    return JDXiSysExAddress(0x18, 0x00, lmb, 0x00)


def _efx(n: int) -> int:
    """Offset of Effect 1/2 parameter *n*: 00 11 + 4(n-1), 7 bits per byte."""
    linear = 0x11 + 4 * (n - 1)
    return ((linear >> 7) << 8) | (linear & 0x7F)


def _dly(n: int) -> int:
    return 0x04 + 4 * (n - 1)


def _rev(n: int) -> int:
    return 0x03 + 4 * (n - 1)


def _level_desc() -> str:
    return tr("Adjusts the volume.")


def effect_blocks() -> list[Block]:
    """The four effect blocks, their parameters and explanations (in the interface language)."""
    S = PSpec
    p26, p27 = 26, 27
    v150 = tr("JD-Xi Version 1.50 Supplementary Manual")
    on_off = ("OFF", "ON")

    def x1(n, label, typ, **kw):
        return S(f"EFX1_PARAM_{n}", _efx(n), label, nibbled=True, group=f"EFFECT1 · {typ.upper()}", page=kw.pop("page", p26), **kw)

    def x2(n, label, typ, **kw):
        return S(f"EFX2_PARAM_{n}", _efx(n), label, nibbled=True, group=f"EFFECT2 · {typ.upper()}", page=kw.pop("page", p27), **kw)

    dist_type = tr("Selects the type of distortion.")
    drive = tr("Adjusts the depth of distortion.")
    presence = tr("Adjusts the character of the ultra-high-frequency region.")
    side_on = tr("Only with Side Switch ON.")
    efx1 = Block("EFFECT_1", "EFFECT1", _program(0x02), request=MidiRequests.PROGRAM_EFFECT1, params=[
        S("EFX1_TYPE", 0x00, "Type", tr("Effect 1 Type"), tr("Selects the type of effect 1."), 0, 4, choices=EFX1_TYPES, page=p26),
        S("EFX1_OUTPUT_ASSIGN", 0x04, "Output Asgn", tr("Output Assign"),
          tr("Selects the output destination for the sound from effect 1. DIR: to the Output jacks. EFX2: to Effect 2 (in series). To use EFX1 and EFX2 separately for each part, set DIR."),
          0, 1, choices=("DIR", "EFX2"), page=p26),
        S("EFX1_DELAY_SEND_LEVEL", 0x02, "Dly Send Lev", tr("Effect 1 Delay Send Level"), tr("Depth of delay applied to the sound from effect 1."), page=p26),
        S("EFX1_REVERB_SEND_LEVEL", 0x03, "Rev Send Lev", tr("Effect 1 Reverb Send Level"), tr("Depth of reverb applied to the sound from effect 1."), page=p26),
        S("EFX1_LEVEL", 0x01, "EFX1 Level", tr("Effect 1 Level"), tr("Output level of the whole Effect 1 block. Not on the JD-Xi display; it can only be set via MIDI."),
          depends=tr("Set via MIDI only.")),
        # Distortion
        x1(3, "Type", "Distortion", long=tr("Distortion Type"), description=dist_type, lo=0, hi=5),
        x1(2, "Drive", "Distortion", description=drive),
        x1(4, "Presence", "Distortion", description=presence),
        x1(1, "Level", "Distortion", description=_level_desc()),
        # Fuzz
        x1(3, "Type", "Fuzz", long=tr("Fuzz Type"), description=dist_type, lo=0, hi=5),
        x1(2, "Drive", "Fuzz", description=drive),
        x1(4, "Presence", "Fuzz", description=presence),
        x1(1, "Level", "Fuzz", description=_level_desc()),
        # Compressor
        x1(1, "Threshold", "Compressor", description=tr("Level at which compression is applied.")),
        x1(2, "Ratio", "Compressor", description=tr("Compression ratio."), hi=19, choices=RATIOS, kind="list"),
        x1(3, "Attack", "Compressor", description=tr("Time from when the input exceeds the Threshold until compression begins."),
           hi=31, choices=[f"{a} ms" for a in ATTACKS], kind="list"),
        x1(4, "Release", "Compressor", description=tr("Time from when the input falls below the Threshold until compression is removed."),
           hi=23, choices=[f"{r} ms" for r in RELEASES], kind="list"),
        x1(5, "Level", "Compressor", description=_level_desc()),
        x1(6, "Side Switch", "Compressor", long=tr("Side Chain Switch"),
           description=tr("Side chain: lowers the volume of the digital/analog parts while the drum part is producing sound."),
           hi=1, choices=on_off, page=0, source=v150),
        x1(7, "Side Level", "Compressor", description=tr("Specifies the level of the side chain."), page=0, source=v150, depends=side_on),
        x1(8, "Side Note", "Compressor", description=tr("Drum instrument (note number) sent to the side chain. In the drum part you can also set it with the keyboard."),
           choices=NOTE_NAMES, kind="list", page=0, source=v150, depends=side_on),
        x1(9, "Side Time", "Compressor", description=tr("Time after which the reduced volume starts returning to normal."),
           lo=60, hi=1000, unit="ms", step=10, page=0, source=v150, depends=side_on),
        x1(10, "Side Release", "Compressor", description=tr("Time over which compression is removed once the reduced volume starts returning to normal."),
           page=0, source=v150, depends=side_on),
        x1(11, "Side Sync Sw", "Compressor", long=tr("Side Sync Switch"),
           description=tr("ON: Side Time follows the tempo (the value set is the one at tempo 120)."),
           hi=1, choices=on_off, page=0, source=v150, depends=side_on),
        # Bit Crusher
        x1(2, "Rate", "Bit Crusher", description=tr("Adjusts the sampling frequency."), page=p27),
        x1(3, "Bit", "Bit Crusher", description=tr("Adjusts the bit depth."), page=p27),
        x1(4, "Filter", "Bit Crusher", description=tr("Adjusts the filter depth."), page=p27),
        x1(1, "Level", "Bit Crusher", description=_level_desc(), page=p27),
    ])

    rate = tr("Frequency of modulation.")
    rate_note = tr("RATE: the speed is set with Rate. NOTE: it follows the tempo, as a note value.")
    by_rate, by_note = tr("Only with Rate/Note set to RATE."), tr("Only with Rate/Note set to NOTE.")
    manual = tr("Adjusts the basic frequency from which the sound will be modulated.")
    balance = tr("Volume balance between the direct sound (D) and the effect sound (W).")
    efx2 = Block("EFFECT_2", "EFFECT2", _program(0x04), request=MidiRequests.PROGRAM_EFFECT2, params=[
        S("EFX2_TYPE", 0x00, "Type", tr("Effect 2 Type"), tr("Selects the type of effect 2."), 0, 4,
          choices=EFX2_TYPES, values=EFX2_TYPE_VALUES, page=p26),
        S("EFX2_DELAY_SEND_LEVEL", 0x02, "Dly Send Lev", tr("Effect 2 Delay Send Level"), tr("Depth of delay applied to the sound from effect 2."), page=p26),
        S("EFX2_REVERB_SEND_LEVEL", 0x03, "Rev Send Lev", tr("Effect 2 Reverb Send Level"), tr("Depth of reverb applied to the sound from effect 2."), page=p26),
        S("EFX2_LEVEL", 0x01, "EFX2 Level", tr("Effect 2 Level"), tr("Output level of the whole Effect 2 block. Not on the JD-Xi display; it can only be set via MIDI."),
          depends=tr("Set via MIDI only.")),
        # Flanger
        x2(1, "Rate/Note", "Flanger", long=tr("Rate or Note"), description=rate_note, hi=1, choices=("RATE", "NOTE")),
        x2(2, "Rate", "Flanger", description=rate, depends=by_rate),
        x2(3, "Note", "Flanger", description=rate, hi=21, choices=NOTES, kind="list", depends=by_note),
        x2(4, "Depth", "Flanger", description=tr("Depth of modulation.")),
        x2(5, "Feedback", "Flanger", description=tr("Proportion of the flanger sound that is returned to the input. With 0 the flanger works as a chorus.")),
        x2(6, "Manual", "Flanger", description=manual),
        x2(7, "Balance", "Flanger", description=balance, hi=100, choices=BALANCE, kind="knob"),
        x2(8, "Level", "Flanger", description=_level_desc()),
        # Phaser
        x2(1, "Rate/Note", "Phaser", long=tr("Rate or Note"), description=rate_note, hi=1, choices=("RATE", "NOTE")),
        x2(2, "Rate", "Phaser", description=tr("Adjusts the speed of rotation."), depends=by_rate),
        x2(3, "Note", "Phaser", description=tr("Adjusts the speed of rotation."), hi=21, choices=NOTES, kind="list", depends=by_note),
        x2(4, "Depth", "Phaser", description=tr("Adjusts the depth of the phase effect.")),
        x2(5, "Resonance", "Phaser", description=tr("Adjusts the amount of resonance.")),
        x2(6, "Manual", "Phaser", description=manual),
        x2(7, "Level", "Phaser", description=_level_desc()),
        # Ring Mod
        x2(1, "Frequency", "Ring Mod", description=tr("Adjusts the frequency at which modulation is applied.")),
        x2(2, "Sens", "Ring Mod", description=tr("Adjusts the amount of frequency modulation applied.")),
        x2(3, "Balance", "Ring Mod", description=balance, hi=100, choices=BALANCE, kind="knob"),
        x2(4, "Level", "Ring Mod", description=_level_desc()),
        # Slicer
        x2(1, "Timing Ptn", "Slicer", long=tr("Timing Pattern"), description=tr("Selects the rhythm pattern by which the sound is sliced."), hi=15),
        x2(2, "Rate", "Slicer", description=tr("Adjusts the rate at which the sound is sliced."), hi=21, choices=NOTES, kind="list"),
        x2(3, "Attack", "Slicer", description=tr("Speed at which the level changes between steps.")),
        x2(4, "Trigger Level", "Slicer",
           description=tr("Sensitivity that triggers playback from the beginning of the pattern. Set 127 to keep the Slicer in step with the pattern.")),
        x2(5, "Level", "Slicer", description=_level_desc()),
    ])

    def d(n, name, label, **kw):
        return S(name, _dly(n), label, nibbled=True, page=p26, **kw)

    delay = Block("DELAY", "DELAY", _program(0x06), request=MidiRequests.PROGRAM_DELAY, params=[
        d(1, "DELAY_TYPE", "Type", description=tr("Selects the type of delay. PAN: the echoes alternate between left and right."), hi=1, choices=("SINGLE", "PAN")),
        d(2, "DELAY_TIME_NOTE_MODE", "Time/Note", long=tr("Delay time as milliseconds or note"),
          description=tr("TIME: the delay time is set in milliseconds. NOTE: it follows the tempo, as a note value."), hi=1, choices=("TIME", "NOTE")),
        d(3, "DELAY_TIME_MS", "Time", long=tr("Delay Time"), description=tr("Adjusts the delay time."), hi=2600, unit="ms", step=10,
          depends=tr("Only with Time/Note set to TIME.")),
        d(4, "DELAY_NOTE", "Time (note)", long=tr("Delay Time"), description=tr("Adjusts the delay time."), hi=21, choices=NOTES, kind="list",
          depends=tr("Only with Time/Note set to NOTE.")),
        d(5, "DELAY_TAP_TIME", "Tap Time", description=tr("Delay time of the L channel relative to the R channel (100%)."), hi=100, unit="%",
          depends=tr("Only with Type PAN.")),
        d(6, "DELAY_FEEDBACK", "Feedback", description=tr("Proportion of delay sound that is returned to the input."), hi=98, unit="%"),
        d(7, "DELAY_HF_DAMP", "HF Damp", long=tr("High Frequency Damp"),
          description=tr("Frequency at which to cut the high-frequency portion of the delay sound returned to the input (BYPASS: no cut)."),
          hi=17, choices=HF_DAMP, kind="list"),
        d(8, "DELAY_EFFECT_LEVEL", "Level", description=tr("Adjusts the volume of the delay sound. The panel [Delay] knob sets it.")),
        S("DELAY_REVERB_SEND_LEVEL", 0x03, "Rev Send Lev", tr("Delay to Reverb Send Level"),
          tr("Depth of reverb applied to the sound that passes through the delay."), page=p26),
        S("DELAY_LEVEL", 0x01, "Block Level", tr("Delay Level (block)"),
          tr("Output level of the whole Delay block. Not on the JD-Xi display; it can only be set via MIDI."), depends=tr("Set via MIDI only.")),
    ])

    def r(n, name, label, **kw):
        return S(name, _rev(n), label, nibbled=True, page=p26, **kw)

    reverb = Block("REVERB", "REVERB", _program(0x08), request=MidiRequests.PROGRAM_REVERB, params=[
        r(1, "REVERB_TYPE", "Type", description=tr("Specifies the type of reverb."), hi=5,
          choices=("ROOM1", "ROOM2", "STAGE1", "STAGE2", "HALL1", "HALL2")),
        r(2, "REVERB_TIME", "Time", description=tr("Time length of reverberation.")),
        r(3, "REVERB_HF_DAMP", "HF Damp", long=tr("High Frequency Damp"),
          description=tr("Frequency at which to cut the high-frequency portion of the reverb sound (BYPASS: no cut)."),
          hi=17, choices=HF_DAMP, kind="list"),
        r(4, "REVERB_EFFECT_LEVEL", "Level", description=tr("Adjusts the volume of the reverb sound. The panel [Reverb] knob sets it.")),
        S("REVERB_LEVEL", 0x01, "Block Level", tr("Reverb Level (block)"),
          tr("Output level of the whole Reverb block. Not on the JD-Xi display; it can only be set via MIDI."), depends=tr("Set via MIDI only.")),
    ])
    return [efx1, efx2, delay, reverb]


# ---------------------------------------------------------------- views

class ChainView(_Graph):
    """How the sound goes through the effects, with the selected types."""

    def __init__(self, editor: "EffectsEditor"):
        super().__init__(ACCENT, editor.info_hub, 86)
        self.editor = editor
        self.efx1 = editor.pv("EFX1_TYPE")
        self.efx2 = editor.pv("EFX2_TYPE")
        self.assign = editor.pv("EFX1_OUTPUT_ASSIGN")
        for pv in (self.efx1, self.efx2, self.assign):
            pv.watch(lambda _v: self.update())
        self.setToolTip(tr("Click a block to go to its settings"))

    def boxes(self) -> list[tuple[QRectF, str, str, Optional[ParamValue]]]:
        r = self.plot_rect()
        gap = 28
        w = (r.width() - 4 * gap) / 4.6
        y, h = r.top() + 4, 30
        names = [
            ("EFX1", self.efx1.text(), self.efx1),
            ("EFX2", self.efx2.text(), self.efx2),
            ("DELAY", self.editor.pv("DELAY_TYPE").text(), self.editor.pv("DELAY_TYPE")),
            ("REVERB", self.editor.pv("REVERB_TYPE").text(), self.editor.pv("REVERB_TYPE")),
        ]
        out = []
        for i, (name, typ, pv) in enumerate(names):
            out.append((QRectF(r.left() + i * (w + gap), y, w, h), name, typ, pv))
        out.append((QRectF(r.left() + 4 * (w + gap), y, w * 0.6, h), "OUT", "", None))
        return out

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0e0f11"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        boxes = self.boxes()
        series = self.assign.value() == 1
        accent, muted = QColor(ACCENT), QColor("#6b6e75")
        small = QFont(self.font().family(), 8)
        for rect, name, typ, pv in boxes:
            active = pv is None or pv.value() != 0 or name in ("DELAY", "REVERB")
            p.setPen(QPen(accent if active else muted, 1.4))
            p.setBrush(QColor("#1b1c1f"))
            p.drawRoundedRect(rect, 6, 6)
            p.setPen(QColor("#ffffff") if active else muted)
            p.setFont(QFont(self.font().family(), 8, QFont.Weight.Bold))
            p.drawText(rect.adjusted(0, 3, 0, -rect.height() / 2), Qt.AlignmentFlag.AlignHCenter, name)
            if typ:
                p.setFont(small)
                p.setPen(QColor("#c9cbd1") if active else muted)
                p.drawText(rect.adjusted(0, rect.height() / 2 - 1, 0, 0), Qt.AlignmentFlag.AlignHCenter, typ)
        efx1, efx2, dly, rev, out = (b[0] for b in boxes)
        mid = efx1.center().y()

        def arrow(a: QPointF, b: QPointF, color=accent, dashed=False):
            p.setPen(QPen(color, 1.6, Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine))
            p.drawLine(a, b)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            d = 5
            p.drawPolygon([b, QPointF(b.x() - d, b.y() - d * 0.7), QPointF(b.x() - d, b.y() + d * 0.7)])

        # EFX1 -> EFX2 (series) or straight to the output
        arrow(QPointF(efx1.right(), mid), QPointF(efx2.left(), mid), accent if series else muted, dashed=not series)
        arrow(QPointF(efx2.right(), mid), QPointF(dly.left(), mid))
        arrow(QPointF(dly.right(), mid), QPointF(rev.left(), mid))
        arrow(QPointF(rev.right(), mid), QPointF(out.left(), mid))
        p.setPen(QPen(QColor("#a3a6ad"), 1))
        p.setFont(small)
        bottom = efx1.bottom() + 16
        text = tr("Effect 1 → Effect 2 in series (Output Assign EFX2)") if series else tr(
            "Effect 1 → output, Effect 2 used by other parts (Output Assign DIR)")
        p.drawText(QPointF(efx1.left(), bottom), text)
        p.end()

    def mousePressEvent(self, event) -> None:
        for rect, name, _typ, _pv in self.boxes():
            if rect.contains(event.position()) and name in self.editor.cards:
                self.editor.scroll.ensureWidgetVisible(self.editor.cards[name], 0, 0)
                return

    def mouseMoveEvent(self, event) -> None:
        for rect, _name, _typ, pv in self.boxes():
            if rect.contains(event.position()) and pv is not None:
                self.hub.shown.emit(pv)
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                return
        self.unsetCursor()


class DelayView(_Graph):
    """The echoes over time: delay time, feedback, PAN alternation and level."""

    def __init__(self, editor: "EffectsEditor"):
        super().__init__(ACCENT, editor.info_hub, 96)
        e = editor
        self.type, self.mode = e.pv("DELAY_TYPE"), e.pv("DELAY_TIME_NOTE_MODE")
        self.ms, self.note = e.pv("DELAY_TIME_MS"), e.pv("DELAY_NOTE")
        self.tap, self.feedback, self.level = e.pv("DELAY_TAP_TIME"), e.pv("DELAY_FEEDBACK"), e.pv("DELAY_EFFECT_LEVEL")
        for pv in (self.type, self.mode, self.ms, self.note, self.tap, self.feedback, self.level):
            pv.watch(lambda _v: self.update())

    def delay_ms(self) -> float:
        if self.mode.value() == 1:  # a note value at tempo 120: a whole note lasts 2 s
            num, _, den = NOTES[self.note.value()].partition("/")
            return 2000.0 * float(num) / float(den or 1)
        return float(self.ms.value())

    def handles(self):
        return []

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        time = max(self.delay_ms(), 1.0)
        span = max(1000.0, min(time * 8, 8000.0))
        fb = self.feedback.value() / 100
        level = self.level.value() / 127
        pan = self.type.value() == 1
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.left(), r.top()))  # the direct sound
        amp, k = level, 1
        while amp > 0.02 and k < 64:
            t = time * k
            if pan and k % 2 == 1:  # the left echo comes at Tap Time % of the right one
                t = time * (k - 1) + time * self.tap.value() / 100
            if t > span:
                break
            x = r.left() + r.width() * t / span
            left = pan and k % 2 == 1
            color = QColor("#f2c94c") if left else QColor(ACCENT)
            p.setPen(QPen(color, 2))
            p.drawLine(QPointF(x, r.bottom()), QPointF(x, r.bottom() - r.height() * amp))
            amp *= fb if fb > 0 else 0
            k += 1
        p.setPen(QColor("#8a8d94"))
        p.setFont(QFont(self.font().family(), 7))
        label = tr("{time} ms between echoes").format(time=int(time))
        if self.mode.value() == 1:
            label += " " + tr("(note at tempo 120)")
        if pan:
            label += "  ·  " + tr("blue: left, orange: right")
        p.drawText(QPointF(r.left() + 4, r.bottom() + 12), label)
        p.drawText(QPointF(r.right() - 40, r.bottom() + 12), f"{span / 1000:.1f} s")
        p.end()


class CompressorView(_Graph):
    """Output level against input level: threshold and ratio."""

    def __init__(self, editor: "EffectsEditor", threshold: ParamValue, ratio: ParamValue):
        super().__init__(ACCENT, editor.info_hub, 96)
        self.threshold, self.ratio = threshold, ratio
        for pv in (threshold, ratio):
            pv.watch(lambda _v: self.update())
        self.setFixedWidth(150)

    def handles(self):
        r = self.plot_rect()
        t = self.threshold.value() / 127
        return [(QPointF(r.left() + r.width() * t, r.bottom() - r.height() * t), self.threshold)]

    def drag_to(self, index: int, pos: QPointF) -> None:
        r = self.plot_rect()
        self.threshold.setValue(round((pos.x() - r.left()) / r.width() * 127))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        t = self.threshold.value() / 127
        label = RATIOS[self.ratio.value()].split(":")[0]
        ratio = float("inf") if label == "inf" else float(label)
        path = QPainterPath(QPointF(r.left(), r.bottom()))
        knee = QPointF(r.left() + r.width() * t, r.bottom() - r.height() * t)
        path.lineTo(knee)
        end_out = t + (1 - t) / ratio
        path.lineTo(QPointF(r.right(), r.bottom() - r.height() * end_out))
        p.setPen(QPen(QColor("#3a3d44"), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.right(), r.top()))
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawPath(path)
        self._draw_handles(p)
        p.setPen(QColor("#8a8d94"))
        p.setFont(QFont(self.font().family(), 7))
        p.drawText(QPointF(r.left() + 2, r.bottom() + 12), tr("in → out"))
        p.end()


# ---------------------------------------------------------------- editor
class EffectsEditor(V2Editor):
    """Effect 1, Effect 2, Delay and Reverb of the current program."""

    ACCENT = ACCENT

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        super().__init__(effect_blocks(), midi_helper=midi_helper, parent=parent, title=tr("Effects"))
        self.preset_helper = preset_helper
        self._link_dependencies()
        for key in ("EFX1_TYPE", "EFX2_TYPE"):
            self.pv(key).valueChanged.connect(lambda _v, key=key: self._type_sent(key))

    # --- the parameters of one type
    def type_specs(self, block_key: str, typ: str) -> list[PSpec]:
        group = f"{'EFFECT1' if block_key == 'EFFECT_1' else 'EFFECT2'} · {typ.upper()}"
        block = next(b for b in self.blocks if b.key == block_key)
        return [s for s in block.params if s.group == group]

    def build_panels(self) -> None:
        self.cards: dict[str, QWidget] = {}
        self.pages: dict[str, QStackedWidget] = {}
        self.chain = ChainView(self)
        self.panels_layout.addWidget(self.chain)
        row = QHBoxLayout()
        row.setSpacing(12)
        top = Qt.AlignmentFlag.AlignTop
        row.addWidget(self._effect_card("EFX1", "EFFECT_1", EFX1_TYPES), 1, top)
        row.addWidget(self._effect_card("EFX2", "EFFECT_2", EFX2_TYPES), 1, top)
        self.panels_layout.addLayout(row)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._delay_card(), 3, top)
        row.addWidget(self._reverb_card(), 2, top)
        self.panels_layout.addLayout(row)
        self.panels_layout.addWidget(self.note(
            tr("Changes are heard at once and kept in the current program until another one is selected. "
               "To keep them, save the program on the JD-Xi with [Menu/Write]: the JD-Xi cannot be written to its memory via MIDI.")
        ))
        self.panels_layout.addStretch()

    def _effect_card(self, name: str, block_key: str, types: list[str]):
        number = name[-1]
        card = self.card(f"EFFECT {number}", tr("Parameter Guide, p. 26-27"))
        self.cards[name] = card
        type_spec = self.spec(f"EFX{number}_TYPE")
        card.body.addWidget(ChoiceButtons(self.values[type_spec], ACCENT, self.info_hub))
        if block_key == "EFFECT_1":
            card.body.addWidget(self.control(self.spec("EFX1_OUTPUT_ASSIGN")))
        pages = density.FitStack()  # as tall as the type shown (Thru: no empty space)
        self.pages[name] = pages
        unverified_notes = unverified()
        for typ in types:
            page = QWidget()
            page.setStyleSheet("background: transparent;")
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 4, 0, 0)
            specs = self.type_specs(block_key, typ)
            if not specs:
                layout.addWidget(self.note(tr("Thru: the sound passes through unchanged.")))
            elif typ == "Compressor":
                self._compressor_page(layout, specs)
            else:
                lists = [s for s in specs if s.widget_kind() != "knob"]
                for spec in lists:
                    layout.addWidget(self.control(spec))
                layout.addLayout(self.knob_row([s for s in specs if s.widget_kind() == "knob"]))
            to_check = unverified_notes.get(typ)
            if to_check:
                layout.addWidget(self.note(tr("Parameter numbers from the JD-Xi Manager, to be checked on the instrument: {which}.").format(which=to_check)))
            layout.addStretch()
            pages.addWidget(page)
        card.body.addWidget(pages)
        type_pv = self.values[type_spec]
        type_pv.watch(pages.setCurrentIndex)
        pages.setCurrentIndex(type_pv.value())
        card.body.addLayout(self.knob_row([
            self.spec(f"EFX{number}_DELAY_SEND_LEVEL"),
            self.spec(f"EFX{number}_REVERB_SEND_LEVEL"),
            self.spec(f"EFX{number}_LEVEL"),
        ]))
        return card

    def _compressor_page(self, layout: QVBoxLayout, specs: list[PSpec]) -> None:
        by = {s.label: s for s in specs}
        top = QHBoxLayout()
        top.addWidget(CompressorView(self, self.values[by["Threshold"]], self.values[by["Ratio"]]))
        lists = QVBoxLayout()
        for label in ("Ratio", "Attack", "Release"):
            lists.addWidget(self.control(by[label]))
        top.addLayout(lists, 1)
        layout.addLayout(top)
        layout.addLayout(self.knob_row([by["Threshold"], by["Level"]]))
        side = QLabel(tr("SIDE CHAIN (version 1.50)"))
        side.setStyleSheet(f"color: {ACCENT}; font-size: 10px; letter-spacing: 1px; background: transparent;")
        layout.addWidget(side)
        layout.addWidget(self.control(by["Side Switch"]))
        layout.addWidget(self.control(by["Side Note"]))
        layout.addLayout(self.knob_row([by["Side Level"], by["Side Time"], by["Side Release"]]))
        layout.addWidget(self.control(by["Side Sync Sw"]))

    def _delay_card(self):
        card = self.card("DELAY", tr("Parameter Guide, p. 26"))
        self.cards["DELAY"] = card
        s = self.spec
        card.body.addWidget(DelayView(self))
        card.body.addWidget(self.control(s("DELAY_TYPE")))
        card.body.addWidget(self.control(s("DELAY_TIME_NOTE_MODE")))
        card.body.addWidget(self.control(s("DELAY_NOTE")))
        card.body.addWidget(self.control(s("DELAY_HF_DAMP")))
        card.body.addLayout(self.knob_row([s("DELAY_TIME_MS"), s("DELAY_TAP_TIME"), s("DELAY_FEEDBACK"), s("DELAY_EFFECT_LEVEL")]))
        card.body.addLayout(self.knob_row([s("DELAY_REVERB_SEND_LEVEL"), s("DELAY_LEVEL")]))
        return card

    def _reverb_card(self):
        card = self.card("REVERB", tr("Parameter Guide, p. 26"))
        self.cards["REVERB"] = card
        s = self.spec
        card.body.addWidget(self.control(s("REVERB_TYPE")))
        card.body.addWidget(self.control(s("REVERB_HF_DAMP")))
        card.body.addLayout(self.knob_row([s("REVERB_TIME"), s("REVERB_EFFECT_LEVEL"), s("REVERB_LEVEL")]))
        return card

    # --- which controls have an effect
    def _link_dependencies(self) -> None:
        def link(source: ParamValue, rule, targets: list[ParamValue]):
            def apply(_v=None):
                on = rule(source.value())
                for t in targets:
                    t.set_enabled(on)
            source.watch(apply)
            apply()

        for typ in ("Flanger", "Phaser"):
            specs = {s.label: self.values[s] for s in self.type_specs("EFFECT_2", typ)}
            link(specs["Rate/Note"], lambda v: v == 0, [specs["Rate"]])
            link(specs["Rate/Note"], lambda v: v == 1, [specs["Note"]])
        comp = {s.label: self.values[s] for s in self.type_specs("EFFECT_1", "Compressor")}
        link(comp["Side Switch"], lambda v: v == 1,
             [comp[k] for k in ("Side Level", "Side Note", "Side Time", "Side Release", "Side Sync Sw")])
        link(self.pv("DELAY_TIME_NOTE_MODE"), lambda v: v == 0, [self.pv("DELAY_TIME_MS")])
        link(self.pv("DELAY_TIME_NOTE_MODE"), lambda v: v == 1, [self.pv("DELAY_NOTE")])
        link(self.pv("DELAY_TYPE"), lambda v: v == 1, [self.pv("DELAY_TAP_TIME")])

    def _type_sent(self, key: str) -> None:
        """A new type loads its own settings on the JD-Xi: read them back."""
        block = self.block_of[self.spec(key)]
        QTimer.singleShot(250, self, lambda: self.read_block(block))
