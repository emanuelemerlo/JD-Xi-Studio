"""
New Drum Kit editor.

Covers the Parameter Guide's "Drum Kit" pages (p. 20-24) and every parameter
of the MIDI Implementation tables Drum Kit Common (19 70 00 00) and Drum Kit
Partial (keys 36-72, 19 70 2E 00 ... 19 70 76 00): the 37 drum partials, each
with four waves (WMT), pitch, filter (TVF) and amplifier (TVA) settings.

The kit is shown as a grid of pads; the selected pad's partial is edited in
sections (COMMON, WAVE, PITCH, TVF, TVA), the four waves side by side, the
three envelopes drawn and draggable. A partial's page is built the first time
it is opened.
"""

from __future__ import annotations

from typing import Optional, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.midi.data.drum.data import DRUM_PARTIAL_NAMES, rm_waves
from jdxi_editor.ui.v2.framework import Block, NameField, PSpec, rq1, seven_bit, tone_editor_base
from jdxi_editor.ui.v2.params import ParamValue
from jdxi_editor.ui.v2.program import VelocityView, pan_parse, pan_text
from jdxi_editor.ui.v2.widgets import _Graph

ACCENT = "#a78bfa"  # Drums purple, as on the JD-Xi panel
NAME_LENGTH = 12
FIRST_KEY, KEYS = 36, 37
SECTIONS = ["COMMON", "WAVE", "PITCH", "TVF", "TVA"]
_NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES = tuple(f"{_NOTE[n % 12]}{n // 12 - 1}" for n in range(128))
RANDOM_PITCH = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200)
CURVES = ("FIXED", "1", "2", "3", "4", "5", "6", "7")
OUTPUTS = ("EFX1", "EFX2", "DLY", "REV", "DIR")
FILTER_TYPES = ("OFF", "LPF", "BPF", "HPF", "PKG", "LPF2", "LPF3")
WAVES = tuple(name.strip() for name in rm_waves)  # "000: OFF" ... "453: SH2 U Zap 5"
WMT_START, WMT_SIZE = 0x21, 29  # Wave 1 at 00 21, each wave 29 bytes


def key_name(partial: int) -> str:
    """'BD1 (C2)' for partial 0."""
    return f"{DRUM_PARTIAL_NAMES[partial + 1]} ({NOTE_NAMES[FIRST_KEY + partial]})"


def _offset(linear: int) -> int:
    """Linear byte position -> offset as written in the MIDI Implementation (0x94 -> 01 14)."""
    return ((linear >> 7) << 8) | (linear & 0x7F)


def common_block() -> Block:
    params = [
        PSpec(f"KIT_NAME_{i + 1}", i, f"Name {i + 1}", lo=32, hi=127, description=tr("Name of the drum kit (12 characters)."),
              page=20, group="COMMON")
        for i in range(NAME_LENGTH)
    ]
    params.append(PSpec("KIT_LEVEL", 0x0C, "Kit Level", description=tr("Volume of the whole drum kit."), page=20, group="COMMON"))
    return Block("KIT_COMMON", "COMMON", JDXiSysExAddress(0x19, 0x70, 0x00, 0x00), params,
                 request=rq1([0x19, 0x70, 0x00, 0x00], 0x40))


class _Texts:
    """The explanations, translated once for all 37 partials."""

    def __init__(self):
        self.v_sens = tr("Positive: more effect the harder you play; negative: less.")
        self.t1 = tr("How playing harder changes Time 1: positive makes it faster, negative slower.")
        self.t4 = tr("How releasing faster changes Time 4: positive makes it faster, negative slower.")
        self.curve = tr("Curve of the response to velocity; FIXED: velocity has no effect.")
        self.wave_pan = tr("Stereo position of the wave.")
        self.vel_ctrl = tr("Used when WMT Vel Ctrl is ON.")
        self.fxm_on = tr("Only with FXM Switch ON.")
        self.no_sync = tr("No effect with Wave Tempo Sync ON.")
        self.filter_on = tr("No effect with Filter Type OFF.")


def partial_block(partial: int, t: _Texts) -> Block:
    """Drum partial *partial* (0 = key 36 ... 36 = key 72)."""
    S = PSpec
    name = DRUM_PARTIAL_NAMES[partial + 1]
    bip = dict(lo=-63, hi=63, raw_offset=64, signed=True)
    on_off = ("OFF", "ON")

    def p(key, offset, label, section, **kw):
        return S(key, offset, label, group=f"{section} {name}", page=kw.pop("page", 20), **kw)

    params = [
        p(f"PARTIAL_NAME_{i + 1}", i, f"Name {i + 1}", "COMMON", lo=32, hi=127,
          description=tr("Name of the drum partial (12 characters)."), source=tr("MIDI Implementation"))
        for i in range(NAME_LENGTH)
    ]
    params += [
        # COMMON (p. 20)
        p("ASSIGN_TYPE", 0x0C, "Assign", "COMMON", hi=1, choices=("MULTI", "SINGLE"),
          description=tr("MULTI: repeated notes on the same key overlap. SINGLE: a new note stops the previous one (e.g. open hi-hat).")),
        p("MUTE_GROUP", 0x0D, "Mute Group", "COMMON", hi=31, fmt=lambda v: "OFF" if v == 0 else str(v),
          parse=lambda s: 0 if s.strip().upper() == "OFF" else (int(s) if s.strip().isdigit() else None),
          description=tr("Partials in the same group cannot sound together, like open and closed hi-hat (up to 31 groups; OFF: none).")),
        p("ENV_MODE", 0x15, "Env Mode", "COMMON", hi=1, choices=("NO-SUS", "SUSTAIN"),
          description=tr("NO-SUS: the sound decays naturally even if the key is held. One-shot waves never sustain.")),
        p("PITCH_BEND_RANGE", 0x1C, "Bend Range", "COMMON", hi=48, unit="st",
          description=tr("Pitch change in semitones with the bend lever (the same both ways).")),
        p("RECEIVE_EXPRESSION", 0x1D, "Rx Expression", "COMMON", hi=1, choices=on_off,
          description=tr("Whether this partial reacts to MIDI Expression.")),
        p("RECEIVE_HOLD_1", 0x1E, "Rx Hold-1", "COMMON", hi=1, choices=on_off,
          description=tr("Whether this partial reacts to Hold-1 (damper)."), depends=tr("No effect with Env Mode NO-SUS.")),
        p("ONE_SHOT_MODE", 0x0141, "One Shot Mode", "COMMON", hi=1, choices=on_off, page=20,
          description=tr("ON: the sound plays to the end of the wave or envelope, as with NO-SUS.")),
        p("OUTPUT_ASSIGN", 0x1B, "Output Asgn", "COMMON", hi=4, choices=OUTPUTS, page=24,
          description=tr("Effects this partial goes through when the drum part's Part Output is KIT.")),
        p("OUTPUT_LEVEL", 0x16, "Output Level", "COMMON", source=tr("MIDI Implementation"), page=0,
          description=tr("Level of the partial sent to its output.")),
        p("CHORUS_SEND_LEVEL", 0x19, "Dly Send Lev", "COMMON", page=9, long=tr("Delay Send Level"),
          description=tr("Amount of delay applied to this partial (the MIDI Implementation calls it Chorus Send Level).")),
        p("REVERB_SEND_LEVEL", 0x1A, "Rev Send Lev", "COMMON", page=9, long=tr("Reverb Send Level"),
          description=tr("Amount of reverb applied to this partial.")),
        p("RELATIVE_LEVEL", 0x0142, "Relative Level", "TVA", lo=-64, hi=63, raw_offset=64, signed=True, page=24,
          description=tr("Volume correction of the partial, normally 0; set by the key-based controller messages.")),
        # WAVE (p. 21)
        p("WMT_VELOCITY_CONTROL", 0x20, "WMT Vel Ctrl", "WAVE", hi=2, choices=("OFF", "ON", "RANDOM"), page=21,
          description=tr("ON: which waves sound depends on velocity (their velocity ranges). RANDOM: the waves sound at random.")),
    ]
    for w in range(4):
        n = w + 1
        base = WMT_START + WMT_SIZE * w

        def wv(rel, key, label, **kw):
            return S(f"WMT{n}_{key}", _offset(base + rel), label, group=f"WAVE {n} {name}", page=kw.pop("page", 21), **kw)

        params += [
            wv(0, "WAVE_SWITCH", "Wave Sw", hi=1, choices=on_off, description=tr("Turns this wave on (the [05]-[08] buttons).")),
            wv(2, "WAVE_GROUP_ID", "Group ID", hi=16384, size=4, source=tr("MIDI Implementation"), page=0,
               description=tr("Wave group of the wave (normally OFF)."), fmt=lambda v: "OFF" if v == 0 else str(v)),
            wv(6, "WAVE_NUMBER_L", "No.L (Mono)", hi=453, size=4, choices=WAVES, kind="list",
               description=tr("The wave; in mono only the left (L) one.")),
            wv(10, "WAVE_NUMBER_R", "No.R", hi=453, size=4, choices=WAVES, kind="list",
               description=tr("The right wave, for stereo waves.")),
            wv(14, "WAVE_GAIN", "Gain", hi=3, choices=("-6 dB", "0 dB", "+6 dB", "+12 dB"),
               description=tr("Gain of the wave; each 6 dB step doubles it.")),
            wv(15, "WAVE_FXM_SWITCH", "FXM Switch", hi=1, choices=on_off,
               description=tr("FXM (frequency cross modulation) adds complex overtones, for dramatic sounds and effects."), depends=t.no_sync),
            wv(16, "WAVE_FXM_COLOR", "FXM Color", hi=3, choices=("1", "2", "3", "4"),
               description=tr("How FXM modulates: higher is grainier, lower more metallic."), depends=t.fxm_on),
            wv(17, "WAVE_FXM_DEPTH", "FXM Depth", hi=16, description=tr("Depth of the FXM modulation."), depends=t.fxm_on),
            wv(18, "WAVE_TEMPO_SYNC", "Tempo Sync", hi=1, choices=on_off,
               description=tr("ON: the wave follows the tempo; pitch and FXM settings then have no effect.")),
            wv(19, "WAVE_COARSE_TUNE", "Coarse Tune", lo=-48, hi=48, raw_offset=64, signed=True, unit="st",
               description=tr("Pitch of the wave in semitones (±4 octaves)."), depends=t.no_sync),
            wv(20, "WAVE_FINE_TUNE", "Fine Tune", lo=-50, hi=50, raw_offset=64, signed=True, unit="cent",
               description=tr("Pitch of the wave in cents (±50)."), depends=t.no_sync),
            wv(21, "WAVE_PAN", "Pan", lo=-64, hi=63, raw_offset=64, fmt=pan_text, parse=pan_parse, description=t.wave_pan),
            wv(22, "WAVE_RANDOM_PAN_SWITCH", "Random Pan Sw", hi=1, choices=on_off,
               description=tr("ON: the pan changes at random at each key press (range: TVA Rnd Pan Dpth).")),
            wv(23, "WAVE_ALTERNATE_PAN_SWITCH", "Alter Pan Sw", hi=2, choices=("OFF", "ON", "REVS"),
               description=tr("ON: the pan alternates left and right at each key press (TVA Alt Pan Dpth); REVS: reversed.")),
            wv(24, "WAVE_LEVEL", "Level", description=tr("Volume of the wave.")),
            wv(25, "VELOCITY_RANGE_LOWER", "Vel Range L", lo=1, description=tr("Lowest velocity at which the wave sounds."), depends=t.vel_ctrl),
            wv(26, "VELOCITY_RANGE_UPPER", "Vel Range U", lo=1, description=tr("Highest velocity at which the wave sounds."), depends=t.vel_ctrl),
            wv(27, "VELOCITY_FADE_WIDTH_LOWER", "Vel Fade L",
               description=tr("How gradually the wave fades below its velocity range (0: not heard at all)."), depends=t.vel_ctrl),
            wv(28, "VELOCITY_FADE_WIDTH_UPPER", "Vel Fade U",
               description=tr("How gradually the wave fades above its velocity range (0: not heard at all)."), depends=t.vel_ctrl),
        ]
    params += [
        # PITCH (p. 22)
        p("PARTIAL_COARSE_TUNE", 0x0F, "Coarse Tune", "PITCH", choices=NOTE_NAMES, kind="knob", page=22,
          description=tr("The pitch (note) at which the partial sounds.")),
        p("PARTIAL_FINE_TUNE", 0x10, "Fine Tune", "PITCH", lo=-50, hi=50, raw_offset=64, signed=True, unit="cent", page=22,
          description=tr("Pitch of the partial in cents (±50).")),
        p("PARTIAL_RANDOM_PITCH_DEPTH", 0x11, "Rnd Pch Dpth", "PITCH", hi=30, choices=tuple(f"{c}" for c in RANDOM_PITCH), kind="knob",
          unit="cent", long=tr("Random Pitch Depth"), page=22,
          description=tr("Random pitch change at each key press, in cents; 0: none.")),
        p("PITCH_ENV_DEPTH", _offset(0x95), "Env Depth", "PITCH", lo=-12, hi=12, raw_offset=64, signed=True, page=22,
          description=tr("How much the pitch envelope changes the pitch; negative inverts it.")),
        p("PITCH_ENV_VELOCITY_SENS", _offset(0x96), "Env V-Sens", "PITCH", page=22, description=t.v_sens, **bip),
        p("PITCH_ENV_TIME_1_VELOCITY_SENS", _offset(0x97), "Env T1 V-Sens", "PITCH", page=22, description=t.t1, **bip),
        p("PITCH_ENV_TIME_4_VELOCITY_SENS", _offset(0x98), "Env T4 V-Sens", "PITCH", page=22, description=t.t4, **bip),
    ]
    params += [p(f"PITCH_ENV_TIME_{i + 1}", _offset(0x99 + i), f"Time {i + 1}", "PITCH", page=22,
                 description=tr("Pitch envelope times: a higher value takes longer to reach the next level.")) for i in range(4)]
    params += [p(f"PITCH_ENV_LEVEL_{i}", _offset(0x9D + i), f"Level {i}", "PITCH", page=22,
                 description=tr("Pitch at this point, above (+) or below (-) the partial's pitch."), **bip) for i in range(5)]
    params += [
        # TVF (p. 23)
        p("TVF_FILTER_TYPE", _offset(0xA2), "Filter Type", "TVF", hi=6, choices=FILTER_TYPES, page=23,
          description=tr("OFF: no filter. LPF: low-pass. BPF: band-pass. HPF: high-pass. PKG: peaking (a drum's resonance). LPF2, LPF3: softer low-pass, without resonance.")),
        p("TVF_CUTOFF_FREQUENCY", _offset(0xA3), "Cutoff", "TVF", page=23, depends=t.filter_on,
          description=tr("Frequency at which the filter begins to act.")),
        p("TVF_CUTOFF_VELOCITY_CURVE", _offset(0xA4), "Cutoff V-Crv", "TVF", hi=7, choices=CURVES, kind="list", page=23,
          description=t.curve, depends=t.filter_on),
        p("TVF_CUTOFF_VELOCITY_SENS", _offset(0xA5), "Cutoff V-Sens", "TVF", page=23, depends=t.filter_on,
          description=tr("Positive: the cutoff rises the harder you play; negative: it falls."), **bip),
        p("TVF_RESONANCE", _offset(0xA6), "Resonance", "TVF", page=23,
          description=tr("Emphasizes the sound around the cutoff; too much can distort."), depends=tr("No effect with OFF, LPF2 or LPF3.")),
        p("TVF_RESONANCE_VELOCITY_SENS", _offset(0xA7), "Res V-Sens", "TVF", page=23,
          description=tr("Positive: more resonance the harder you play; negative: less."), depends=tr("No effect with OFF, LPF2 or LPF3."), **bip),
        p("TVF_ENV_DEPTH", _offset(0xA8), "Env Depth", "TVF", page=23, depends=t.filter_on,
          description=tr("How much the filter envelope moves the cutoff; negative inverts it."), **bip),
        p("TVF_ENV_VELOCITY_CURVE_TYPE", _offset(0xA9), "Env V-Curve", "TVF", hi=7, choices=CURVES, kind="list", page=23,
          description=t.curve, depends=t.filter_on),
        p("TVF_ENV_VELOCITY_SENS", _offset(0xAA), "Env V-Sens", "TVF", page=23, depends=t.filter_on, description=t.v_sens, **bip),
        p("TVF_ENV_TIME_1_VELOCITY_SENS", _offset(0xAB), "Env T1 V-Sens", "TVF", page=23, depends=t.filter_on, description=t.t1, **bip),
        p("TVF_ENV_TIME_4_VELOCITY_SENS", _offset(0xAC), "Env T4 V-Sens", "TVF", page=23, depends=t.filter_on, description=t.t4, **bip),
    ]
    params += [p(f"TVF_ENV_TIME_{i + 1}", _offset(0xAD + i), f"Time {i + 1}", "TVF", page=23, depends=t.filter_on,
                 description=tr("Filter envelope times: a higher value takes longer to reach the next level.")) for i in range(4)]
    params += [p(f"TVF_ENV_LEVEL_{i}", _offset(0xB1 + i), f"Level {i}", "TVF", page=23, depends=t.filter_on,
                 description=tr("Cutoff at this point, relative to the Cutoff setting.")) for i in range(5)]
    params += [
        # TVA (p. 24)
        p("PARTIAL_LEVEL", 0x0E, "Level", "TVA", page=24, description=tr("Volume of the drum partial, for the balance between the drums.")),
        p("TVA_LEVEL_VELOCITY_CURVE", _offset(0xB6), "Level V-Curve", "TVA", hi=7, choices=CURVES, kind="list", page=24, description=t.curve),
        p("TVA_LEVEL_VELOCITY_SENS", _offset(0xB7), "Level V-Sens", "TVA", page=24,
          description=tr("Positive: louder the harder you play; negative: softer."), **bip),
        p("PARTIAL_PAN", 0x12, "Pan", "TVA", lo=-64, hi=63, raw_offset=64, fmt=pan_text, parse=pan_parse, page=24,
          description=tr("Stereo position of the partial.")),
        p("PARTIAL_RANDOM_PAN_DEPTH", 0x13, "Rnd Pan Dpth", "TVA", hi=63, page=24, long=tr("Random Pan Depth"),
          description=tr("Range of the random pan change; only for waves with Random Pan Sw ON.")),
        p("PARTIAL_ALTERNATE_PAN_DEPTH", 0x14, "Alt Pan Dpth", "TVA", lo=-63, hi=63, raw_offset=64, page=24, long=tr("Alternate Pan Depth"),
          fmt=lambda v: f"L{-v}" if v < 0 else (f"{v}R" if v > 0 else "0"), parse=pan_parse,
          description=tr("How far the pan alternates at each key press; L and R reverse the order. Only for waves with Alter Pan Sw ON or REVS.")),
        p("TVA_ENV_TIME_1_VELOCITY_SENS", _offset(0xB8), "Env T1 V-Sens", "TVA", page=24, description=t.t1, **bip),
        p("TVA_ENV_TIME_4_VELOCITY_SENS", _offset(0xB9), "Env T4 V-Sens", "TVA", page=24, description=t.t4, **bip),
    ]
    params += [p(f"TVA_ENV_TIME_{i + 1}", _offset(0xBA + i), f"Time {i + 1}", "TVA", page=24,
                 description=tr("Volume envelope times: a higher value takes longer to reach the next level.")) for i in range(4)]
    params += [p(f"TVA_ENV_LEVEL_{i + 1}", _offset(0xBE + i), f"Level {i + 1}", "TVA", page=24,
                 description=tr("Volume at this point, relative to the partial's Level.")) for i in range(3)]
    lmb = 0x2E + 2 * partial
    return Block(f"PARTIAL_{partial}", name, JDXiSysExAddress(0x19, 0x70, lmb, 0x00), params,
                 request=rq1([0x19, 0x70, lmb, 0x00], seven_bit(0x0143)))


# ----------------------------------------------------------------- views
class StepEnvelopeView(_Graph):
    """A Roland T1-T4 / L0-L4 envelope: drag a point sideways for its time, up and down for its level."""

    SLOTS = 4.6  # four times and the held part between Level 3 and key-off

    def __init__(self, hub, times: Sequence[ParamValue], levels: Sequence[Optional[ParamValue]], bipolar: bool = False):
        super().__init__(ACCENT, hub, 110)
        self.times, self.levels, self.bipolar = list(times), list(levels), bipolar
        for pv in self.times + [lv for lv in self.levels if lv is not None]:
            pv.watch(lambda _v: self.update())
            pv.watch_enabled(lambda _e: self.update())
        self.setToolTip(tr("Drag the points: sideways for the time, up and down for the level"))

    def _level_y(self, pv: Optional[ParamValue]) -> float:
        r = self.plot_rect()
        if pv is None:
            frac = 0.5 if self.bipolar else 0.0
        elif self.bipolar:
            frac = (pv.value() + 63) / 126
        else:
            frac = pv.value() / 127
        return r.bottom() - r.height() * frac

    def points(self) -> list[QPointF]:
        r = self.plot_rect()
        slot = r.width() / self.SLOTS
        x = r.left()
        out = [QPointF(x, self._level_y(self.levels[0]))]
        for i, t in enumerate(self.times):
            x += slot * t.value() / 127
            if i == 3:  # key-off after the held part
                x += slot * 0.6
            out.append(QPointF(x, self._level_y(self.levels[i + 1])))
        return out

    def handles(self):
        pts = self.points()
        return [(pts[i + 1], self.levels[i + 1] or self.times[i]) for i in range(4)]

    def drag_to(self, index: int, pos: QPointF) -> None:
        r = self.plot_rect()
        slot = r.width() / self.SLOTS
        pts = self.points()
        start = pts[index].x() + (slot * 0.6 if index == 3 else 0.0)
        self.times[index].setValue((pos.x() - start) / slot * 127)
        level = self.levels[index + 1]
        if level is not None:
            frac = (r.bottom() - pos.y()) / r.height()
            level.setValue(frac * 126 - 63 if self.bipolar else frac * 127)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        pts = self.points()
        if self.bipolar:
            p.setPen(QPen(QColor("#3a3d44"), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))
        slot = r.width() / self.SLOTS
        held = QPointF(pts[3].x() + slot * 0.6, pts[3].y())  # key held: Level 3 until key-off
        path = QPainterPath(pts[0])
        for pt in pts[1:4] + [held, pts[4]]:
            path.lineTo(pt)
        enabled = all(t.is_enabled() for t in self.times)
        color = QColor(ACCENT if enabled else "#5a5d64")
        p.setPen(QPen(color, 2))
        p.drawPath(path)
        p.setPen(QPen(QColor("#5a5d64"), 1, Qt.PenStyle.DotLine))
        p.drawLine(QPointF(held.x(), r.top()), QPointF(held.x(), r.bottom()))
        p.setPen(QColor("#8a8d94"))
        p.setFont(QFont(self.font().family(), 7))
        p.drawText(QPointF(held.x() + 4, r.top() + 10), tr("key off"))
        self._draw_handles(p)
        p.end()


class PadGrid(QWidget):
    """The 37 drum partials as pads, in keyboard order; click one to edit it."""

    def __init__(self, editor: "DrumKitEditor"):
        super().__init__()
        self.editor = editor
        self.group = QButtonGroup(self)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        for i in range(KEYS):
            name, note = DRUM_PARTIAL_NAMES[i + 1], NOTE_NAMES[FIRST_KEY + i]
            button = QPushButton(f"{name}\n{note}")
            button.setCheckable(True)
            button.setMinimumSize(58, 40)
            button.setToolTip(tr("Edit {name} (key {note})").format(name=name, note=note))
            button.setStyleSheet(
                "QPushButton { background: #1b1c1f; color: #c9cbd1; border: 1px solid #3a3d44; border-radius: 6px;"
                " font-size: 10px; font-weight: 600; }"
                "QPushButton:hover { border-color: #6b6e75; }"
                f"QPushButton:checked {{ background: {ACCENT}; color: #0e0f11; border-color: {ACCENT}; }}"
            )
            self.group.addButton(button, i)
            grid.addWidget(button, i // 13, i % 13)
        self.group.idClicked.connect(editor.show_partial)


# ---------------------------------------------------------------- editor
class DrumKitEditor(tone_editor_base()):
    """Drum kit common settings and the 37 drum partials."""

    ACCENT = ACCENT
    SYNTH_TYPE = JDXiSynth.DRUM_KIT
    PRESET_KIND = "Drums"

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        texts = _Texts()
        blocks = [common_block()] + [partial_block(i, texts) for i in range(KEYS)]
        super().__init__(blocks, midi_helper=midi_helper, parent=parent, title=tr("Drum Kit"))
        self.preset_helper = preset_helper
        self._link_dependencies()

    def partial(self, name: str, partial: int) -> ParamValue:
        return self.pv(name, f"PARTIAL_{partial}")

    # --- layout
    def build_panels(self) -> None:
        self.pages: dict[int, QWidget] = {}
        self.current_partial = 0
        self.current_section = 0
        card = self.card("KIT: COMMON", tr("Parameter Guide, p. 20"))
        row = QHBoxLayout()
        box = QVBoxLayout()
        label = QLabel(tr("Kit Name"))
        label.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        box.addWidget(label)
        names = [self.values[s] for s in self.blocks[0].params[:NAME_LENGTH]]
        self.name_field = NameField(self, names, self.blocks[0].address, tr("Name of the drum kit (12 characters)."))
        box.addWidget(self.name_field)
        box.addStretch()
        row.addLayout(box)
        row.addWidget(self.control(self.spec("KIT_LEVEL")))
        row.addStretch()
        card.body.addLayout(row)
        self.pads = PadGrid(self)
        card.body.addWidget(self.pads)
        self.panels_layout.addWidget(card)

        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        self.partial_title = QLabel()
        self.partial_title.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: 700; letter-spacing: 1px; background: transparent;")
        tabs.addWidget(self.partial_title)
        tabs.addSpacing(16)
        self.section_buttons = QButtonGroup(self)
        for index, section in enumerate(SECTIONS):
            button = QPushButton(section)
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { background: #1b1c1f; color: #c9cbd1; border: 1px solid #3a3d44; border-radius: 6px;"
                " padding: 5px 14px; font-weight: 600; letter-spacing: 1px; }"
                f"QPushButton:checked {{ background: {ACCENT}; color: #0e0f11; border-color: {ACCENT}; }}"
            )
            self.section_buttons.addButton(button, index)
            tabs.addWidget(button)
        tabs.addStretch()
        self.section_buttons.idClicked.connect(self.show_section)
        self.panels_layout.addLayout(tabs)
        self.partial_stack = QStackedWidget()
        self.panels_layout.addWidget(self.partial_stack)
        self.panels_layout.addWidget(self.note(
            tr("Changes are heard at once and kept in the current program until another one is selected. "
               "To keep them, save the program on the JD-Xi with [Menu/Write]: the JD-Xi cannot be written to its memory via MIDI.")
        ))
        self.panels_layout.addStretch()
        self.show_partial(0)

    def show_partial(self, partial: int) -> None:
        self.current_partial = partial
        if partial not in self.pages:
            self.pages[partial] = self._partial_page(partial)
            self.partial_stack.addWidget(self.pages[partial])
        page = self.pages[partial]
        for i in range(self.partial_stack.count()):
            widget = self.partial_stack.widget(i)
            policy = QSizePolicy.Policy.Preferred if widget is page else QSizePolicy.Policy.Ignored
            widget.setSizePolicy(policy, policy)
        self.partial_stack.setCurrentWidget(page)
        button = self.pads.group.button(partial)
        if not button.isChecked():
            button.setChecked(True)
        self.partial_title.setText(key_name(partial))
        self.show_section(self.current_section)

    def show_section(self, index: int) -> None:
        self.current_section = index
        sections: QStackedWidget = self.pages[self.current_partial].sections
        for i in range(sections.count()):
            policy = QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored
            sections.widget(i).setSizePolicy(policy, policy)
        sections.setCurrentIndex(index)
        button = self.section_buttons.button(index)
        if not button.isChecked():
            button.setChecked(True)
        sections.adjustSize()
        self.partial_stack.adjustSize()

    def _partial_page(self, partial: int) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        page.sections = QStackedWidget()
        layout.addWidget(page.sections)
        v = lambda name: self.partial(name, partial)  # noqa: E731
        s = lambda name: v(name).param  # noqa: E731
        name = DRUM_PARTIAL_NAMES[partial + 1]
        top = Qt.AlignmentFlag.AlignTop

        def section(*cards):
            host = QWidget()
            host.setStyleSheet("background: transparent;")
            row = QHBoxLayout(host)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            for card in cards:
                row.addWidget(card, 1, top)
            page.sections.addWidget(host)

        # COMMON
        common = self.card(f"{name}: COMMON", tr("Parameter Guide, p. 20, 24"))
        box = QHBoxLayout()
        label = QLabel(tr("Partial Name"))
        label.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        box.addWidget(label)
        block = self.blocks[partial + 1]
        page.name_field = NameField(self, [self.values[sp] for sp in block.params[:NAME_LENGTH]], block.address,
                                    tr("Name of the drum partial (12 characters)."))
        box.addWidget(page.name_field)
        box.addStretch()
        common.body.addLayout(box)
        for key in ("ASSIGN_TYPE", "ENV_MODE", "ONE_SHOT_MODE", "OUTPUT_ASSIGN", "RECEIVE_EXPRESSION", "RECEIVE_HOLD_1"):
            common.body.addWidget(self.control(s(key)))
        common.body.addLayout(self.knob_row([s("MUTE_GROUP"), s("PITCH_BEND_RANGE")]))
        sends = self.card(tr("OUTPUT"), tr("Parameter Guide, p. 9"))
        sends.body.addLayout(self.knob_row([s("OUTPUT_LEVEL"), s("CHORUS_SEND_LEVEL"), s("REVERB_SEND_LEVEL")]))
        section(common, sends)

        # WAVE: the four waves side by side
        host = QWidget()
        host.setStyleSheet("background: transparent;")
        col = QVBoxLayout(host)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self.control(s("WMT_VELOCITY_CONTROL")))
        row = QHBoxLayout()
        row.setSpacing(10)
        for w in range(1, 5):
            card = self.card(f"WAVE {w}", tr("Parameter Guide, p. 21"))
            k = lambda key, w=w: s(f"WMT{w}_{key}")  # noqa: E731
            for key in ("WAVE_SWITCH", "WAVE_NUMBER_L", "WAVE_NUMBER_R", "WAVE_GAIN", "WAVE_TEMPO_SYNC", "WAVE_FXM_SWITCH", "WAVE_FXM_COLOR",
                        "WAVE_RANDOM_PAN_SWITCH", "WAVE_ALTERNATE_PAN_SWITCH"):
                card.body.addWidget(self.control(k(key)))
            grid = QGridLayout()
            grid.setSpacing(2)
            knobs = ["WAVE_LEVEL", "WAVE_PAN", "WAVE_COARSE_TUNE", "WAVE_FINE_TUNE", "WAVE_FXM_DEPTH", "WAVE_GROUP_ID"]
            for i, key in enumerate(knobs):
                grid.addWidget(self.control(k(key)), i // 3, i % 3)
            card.body.addLayout(grid)
            names = ["VELOCITY_RANGE_LOWER", "VELOCITY_RANGE_UPPER", "VELOCITY_FADE_WIDTH_LOWER", "VELOCITY_FADE_WIDTH_UPPER"]
            card.body.addWidget(VelocityView(self, *(v(f"WMT{w}_{n}") for n in names), accent=ACCENT))
            grid = QGridLayout()
            grid.setSpacing(2)
            for i, key in enumerate(names):
                grid.addWidget(self.control(k(key)), i // 2, i % 2)
            card.body.addLayout(grid)
            row.addWidget(card, 1, top)
        col.addLayout(row)
        page.sections.addWidget(host)

        # PITCH
        pitch = self.card(f"{name}: PITCH", tr("Parameter Guide, p. 22"))
        pitch.body.addLayout(self.knob_row([s("PARTIAL_COARSE_TUNE"), s("PARTIAL_FINE_TUNE"), s("PARTIAL_RANDOM_PITCH_DEPTH")]))
        env = self.card(tr("PITCH ENVELOPE"), tr("Parameter Guide, p. 22"))
        env.body.addWidget(StepEnvelopeView(self.info_hub, [v(f"PITCH_ENV_TIME_{i}") for i in range(1, 5)],
                                            [v(f"PITCH_ENV_LEVEL_{i}") for i in range(5)], bipolar=True))
        env.body.addLayout(self.knob_row([s(f"PITCH_ENV_TIME_{i}") for i in range(1, 5)]))
        env.body.addLayout(self.knob_row([s(f"PITCH_ENV_LEVEL_{i}") for i in range(5)]))
        env.body.addLayout(self.knob_row([s("PITCH_ENV_DEPTH"), s("PITCH_ENV_VELOCITY_SENS"), s("PITCH_ENV_TIME_1_VELOCITY_SENS"),
                                          s("PITCH_ENV_TIME_4_VELOCITY_SENS")]))
        section(pitch, env)

        # TVF
        tvf = self.card(f"{name}: TVF", tr("Parameter Guide, p. 23"))
        tvf.body.addWidget(self.control(s("TVF_FILTER_TYPE")))
        tvf.body.addWidget(self.control(s("TVF_CUTOFF_VELOCITY_CURVE")))
        tvf.body.addLayout(self.knob_row([s("TVF_CUTOFF_FREQUENCY"), s("TVF_CUTOFF_VELOCITY_SENS"), s("TVF_RESONANCE"),
                                          s("TVF_RESONANCE_VELOCITY_SENS")]))
        env = self.card(tr("TVF ENVELOPE"), tr("Parameter Guide, p. 23"))
        env.body.addWidget(StepEnvelopeView(self.info_hub, [v(f"TVF_ENV_TIME_{i}") for i in range(1, 5)],
                                            [v(f"TVF_ENV_LEVEL_{i}") for i in range(5)]))
        env.body.addWidget(self.control(s("TVF_ENV_VELOCITY_CURVE_TYPE")))
        env.body.addLayout(self.knob_row([s(f"TVF_ENV_TIME_{i}") for i in range(1, 5)]))
        env.body.addLayout(self.knob_row([s(f"TVF_ENV_LEVEL_{i}") for i in range(5)]))
        env.body.addLayout(self.knob_row([s("TVF_ENV_DEPTH"), s("TVF_ENV_VELOCITY_SENS"), s("TVF_ENV_TIME_1_VELOCITY_SENS"),
                                          s("TVF_ENV_TIME_4_VELOCITY_SENS")]))
        section(tvf, env)

        # TVA
        tva = self.card(f"{name}: TVA", tr("Parameter Guide, p. 24"))
        tva.body.addWidget(self.control(s("TVA_LEVEL_VELOCITY_CURVE")))
        tva.body.addLayout(self.knob_row([s("PARTIAL_LEVEL"), s("TVA_LEVEL_VELOCITY_SENS"), s("RELATIVE_LEVEL")]))
        tva.body.addLayout(self.knob_row([s("PARTIAL_PAN"), s("PARTIAL_RANDOM_PAN_DEPTH"), s("PARTIAL_ALTERNATE_PAN_DEPTH")]))
        env = self.card(tr("TVA ENVELOPE"), tr("Parameter Guide, p. 24"))
        env.body.addWidget(StepEnvelopeView(self.info_hub, [v(f"TVA_ENV_TIME_{i}") for i in range(1, 5)],
                                            [None] + [v(f"TVA_ENV_LEVEL_{i}") for i in range(1, 4)] + [None]))
        env.body.addLayout(self.knob_row([s(f"TVA_ENV_TIME_{i}") for i in range(1, 5)]))
        env.body.addLayout(self.knob_row([s(f"TVA_ENV_LEVEL_{i}") for i in range(1, 4)]))
        env.body.addLayout(self.knob_row([s("TVA_ENV_TIME_1_VELOCITY_SENS"), s("TVA_ENV_TIME_4_VELOCITY_SENS")]))
        section(tva, env)
        return page

    # --- which controls have an effect
    def _link_dependencies(self) -> None:
        def link(sources, rule, targets):
            def apply(_v=None):
                on = rule(*(src.value() for src in sources))
                for t in targets:
                    t.set_enabled(on)
            for src in sources:
                src.watch(apply)

        for partial in range(KEYS):
            v = lambda name, partial=partial: self.partial(name, partial)  # noqa: E731
            link([v("ENV_MODE")], lambda m: m == 1, [v("RECEIVE_HOLD_1")])
            ftype = v("TVF_FILTER_TYPE")
            tvf = [v(n) for n in ("TVF_CUTOFF_FREQUENCY", "TVF_CUTOFF_VELOCITY_CURVE", "TVF_CUTOFF_VELOCITY_SENS", "TVF_ENV_DEPTH",
                                  "TVF_ENV_VELOCITY_CURVE_TYPE", "TVF_ENV_VELOCITY_SENS", "TVF_ENV_TIME_1_VELOCITY_SENS",
                                  "TVF_ENV_TIME_4_VELOCITY_SENS")]
            tvf += [v(f"TVF_ENV_TIME_{i}") for i in range(1, 5)] + [v(f"TVF_ENV_LEVEL_{i}") for i in range(5)]
            link([ftype], lambda f: f != 0, tvf)
            link([ftype], lambda f: FILTER_TYPES[f] not in ("OFF", "LPF2", "LPF3"),
                 [v("TVF_RESONANCE"), v("TVF_RESONANCE_VELOCITY_SENS")])
            vel_ctrl = v("WMT_VELOCITY_CONTROL")
            for w in range(1, 5):
                k = lambda key, w=w: v(f"WMT{w}_{key}")  # noqa: E731
                link([vel_ctrl], lambda c: c == 1, [k("VELOCITY_RANGE_LOWER"), k("VELOCITY_RANGE_UPPER"),
                                                    k("VELOCITY_FADE_WIDTH_LOWER"), k("VELOCITY_FADE_WIDTH_UPPER")])
                link([k("WAVE_TEMPO_SYNC")], lambda t: t == 0, [k("WAVE_COARSE_TUNE"), k("WAVE_FINE_TUNE"), k("WAVE_FXM_SWITCH")])
                link([k("WAVE_FXM_SWITCH"), k("WAVE_TEMPO_SYNC")], lambda f, t: f == 1 and t == 0,
                     [k("WAVE_FXM_COLOR"), k("WAVE_FXM_DEPTH")])
                others = ["WAVE_NUMBER_L", "WAVE_NUMBER_R", "WAVE_GAIN", "WAVE_TEMPO_SYNC", "WAVE_PAN", "WAVE_RANDOM_PAN_SWITCH",
                          "WAVE_ALTERNATE_PAN_SWITCH", "WAVE_LEVEL", "WAVE_GROUP_ID"]
                link([k("WAVE_SWITCH")], lambda on: on == 1, [k(key) for key in others])
                lower, upper = k("VELOCITY_RANGE_LOWER"), k("VELOCITY_RANGE_UPPER")
                # "If you set the lower above the upper, or the upper below the lower, the other follows" (p. 21)
                lower.valueChanged.connect(lambda x, upper=upper: upper.setValue(x) if upper.value() < x else None)
                upper.valueChanged.connect(lambda x, lower=lower: lower.setValue(x) if lower.value() > x else None)
