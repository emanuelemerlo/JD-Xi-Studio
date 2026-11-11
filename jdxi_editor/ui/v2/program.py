"""
New Program editor: the program's common settings and its four parts side by side.

Covers "Program Parameters" of the Parameter Guide (p. 10-11: COMMON, MAIN,
PITCH, OFFSET) and the part settings the JD-Xi only offers via MIDI (MIDI
Implementation: Program Common 18 00 00 00, Program Part 18 00 20-23 00,
Program Zone 18 00 30-33 00): receive channel and switches, tone selection,
velocity range and fade, scale tune, zone octave and arpeggio switch.

The four parts are shown as columns, like a mixer, one section at a time
(MAIN, PITCH, OFFSET, KEYBOARD, SCALE, MIDI): what differs from part to part
is visible at a glance.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.midi.message.roland import JDXiSysEx
from jdxi_editor.ui.v2.framework import Block, PSpec, V2Editor, rq1
from jdxi_editor.ui.v2.params import ParamValue
from jdxi_editor.ui.v2.widgets import _Graph, report_to

ACCENT = "#6fcf97"
PARTS = [("D1", "DIGITAL 1"), ("D2", "DIGITAL 2"), ("AN", "ANALOG"), ("DR", "DRUMS")]
NAME_LENGTH = 12
KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SCALE_KEYS = ["C", "CS", "D", "DS", "E", "F", "FS", "G", "GS", "A", "AS", "B"]
SCALE_TYPES = ["CUSTOM", "EQUAL", "JUST-MAJ", "JUST-MIN", "PYTHAGORE", "KIRNBERGE", "MEANTONE", "WERCKMEIS", "ARABIC"]
RECEIVE = [
    ("RECEIVE_PROGRAM_CHANGE", 0x3D, "Rx Prog Chg", "Program Change"),
    ("RECEIVE_BANK_SELECT", 0x3E, "Rx Bank Sel", "Bank Select"),
    ("RECEIVE_PITCH_BEND", 0x3F, "Rx Bend", "Pitch Bend"),
    ("RECEIVE_POLYPHONIC_KEY_PRESSURE", 0x40, "Rx Poly Pres", "Polyphonic Key Pressure"),
    ("RECEIVE_CHANNEL_PRESSURE", 0x41, "Rx Ch Pres", "Channel Pressure"),
    ("RECEIVE_MODULATION", 0x42, "Rx Mod", "Modulation"),
    ("RECEIVE_VOLUME", 0x43, "Rx Volume", "Volume"),
    ("RECEIVE_PAN", 0x44, "Rx Pan", "Pan"),
    ("RECEIVE_EXPRESSION", 0x45, "Rx Expression", "Expression"),
    ("RECEIVE_HOLD_1", 0x46, "Rx Hold-1", "Hold-1"),
]
SECTIONS = ["MAIN", "PITCH", "OFFSET", "KEYBOARD", "SCALE", "MIDI"]


def pan_text(value: int) -> str:
    return f"L{-value}" if value < 0 else (f"{value}R" if value > 0 else "0")


def pan_parse(text: str) -> Optional[int]:
    t = text.strip().upper().replace(" ", "")
    try:
        if t.startswith("L"):
            return -int(t[1:])
        if t.endswith("R"):
            return int(t[:-1])
        return int(t)
    except ValueError:
        return None


def _part_address(lmb: int, part: int) -> JDXiSysExAddress:
    return JDXiSysExAddress(0x18, 0x00, lmb + part, 0x00)


def common_block() -> Block:
    S = PSpec
    via_midi = tr("MIDI Implementation")
    params = [
        S(f"PROGRAM_NAME_{i + 1}", i, f"Name {i + 1}", lo=32, hi=127, description=tr("Name of the program (12 characters)."),
          page=10, group="COMMON")
        for i in range(NAME_LENGTH)
    ]
    params += [
        S("PROGRAM_LEVEL", 0x10, "ProgramLevel", tr("Program Level"), tr("Volume of the program."), page=10),
        S("PROGRAM_TEMPO", 0x11, "Tempo", tr("Program Tempo (BPM)"),
          tr("Tempo of the program. The Tempo knob adjusts it from 60 to 240; with the SYSTEM parameter Sync Mode set to SLAVE the tempo follows the external device."),
          lo=500, hi=30000, size=4, scale=100, page=10),
        S("VOCAL_EFFECT", 0x16, "Vocal Effect", tr("Vocal Effect"),
          tr("Which vocal effect the program uses: none, the vocoder or Auto-Pitch."), hi=2,
          choices=("OFF", "VOCODER", "AUTO-PITCH"), source=via_midi),
        S("VOCAL_EFFECT_NUMBER", 0x1C, "VFX Number", tr("Vocal Effect Number"),
          tr("Number of the vocal effect setting used by the program."), hi=20, fmt=lambda v: str(v + 1), source=via_midi),
        S("VOCAL_EFFECT_PART", 0x1D, "VFX Part", tr("Vocal Effect Part"),
          tr("Digital part whose notes the vocal effect follows."), hi=1, choices=("1", "2"), source=via_midi),
        S("AUTO_NOTE_SWITCH", 0x1E, "Auto Note", tr("Auto Note Switch"),
          tr("ON: Auto-Pitch corrects to the notes played on the keyboard."), hi=1, choices=("OFF", "ON"), source=via_midi),
    ]
    return Block("PROGRAM_COMMON", "COMMON", JDXiSysExAddress(0x18, 0x00, 0x00, 0x00), params,
                 request=rq1([0x18, 0x00, 0x00, 0x00], 0x1F))


def part_block(part: int) -> Block:
    """Program Part *part* (0 D1, 1 D2, 2 AN, 3 DR)."""
    S = PSpec
    short, _name = PARTS[part]
    drums = part == 3
    tone, signed = "TONE", dict(lo=-64, hi=63, raw_offset=64, signed=True)
    use_tone = tr("TONE: use the setting of the tone assigned to the part.")
    outputs = ["EFX1", "EFX2", "DLY", "REV", "DIR"] + (["KIT"] if drums else [])
    midi = tr("MIDI Implementation")

    def p(name, offset, label, section, **kw):
        page = kw.pop("page", 0)
        return S(name, offset, label, group=f"{section} {short}", page=page, **kw)

    params = [
        # MAIN (p. 10)
        p("PART_LEVEL", 0x09, "Level", "MAIN", description=tr("Volume of each part."), page=10),
        p("MUTE_SWITCH", 0x25, "Sound Mute", "MAIN", hi=1, choices=("OFF", "MUTE"),
          description=tr("Temporarily silences (MUTE) the part, or unmutes it (OFF)."), page=10),
        p("PART_PAN", 0x0A, "Pan", "MAIN", lo=-64, hi=63, raw_offset=64, fmt=pan_text, parse=pan_parse,
          description=tr("Stereo position of the part: L64 is far left, 0 the center, 63R far right."), page=10),
        p("PART_OUTPUT_ASSIGN", 0x2D, "Part Output", "MAIN", hi=len(outputs) - 1, choices=tuple(outputs), kind="list",
          description=tr("Effects applied to the part. EFX1: EFX1, EFX2, Delay and Reverb. EFX2: EFX2, Delay and Reverb. DLY: Delay and Reverb. REV: Reverb. DIR: no effect.")
          + (" " + tr("KIT: the settings of each partial of the kit (value not in the MIDI Implementation, to be checked on the instrument).") if drums else ""),
          page=10),
        p("PART_DELAY_SEND_LEVEL", 0x2B, "Dly Send Lev", "MAIN", long=tr("Delay Send Level"),
          description=tr("Amount of delay applied to the part; 0 for none."), depends=tr("Not with Part Output REV, DIR or KIT."), page=10),
        p("PART_REVERB_SEND_LEVEL", 0x2C, "Rev Send Lev", "MAIN", long=tr("Reverb Send Level"),
          description=tr("Amount of reverb applied to the part; 0 for none."), depends=tr("Not with Part Output DIR or KIT."), page=10),
        p("PART_MONO_POLY", 0x0D, "Mono/Poly", "MAIN", hi=2, choices=("MONO", "POLY", tone),
          description=tr("MONO: the part plays one note at a time; POLY: chords.") + " " + use_tone
          + (" " + tr("The Analog part is always monophonic.") if part == 2 else ""), page=10),
        p("PART_LEGATO_SWITCH", 0x0E, "Legato Sw", "MAIN", hi=2, choices=("OFF", "ON", tone), long=tr("Legato Switch"),
          description=tr("When playing monophonically, ON connects notes smoothly from one to the next, like hammering-on on a guitar.") + " " + use_tone, page=10),
        # PITCH (p. 10)
        p("PART_OCTAVE_SHIFT", 0x1B, "Octave Shift", "PITCH", lo=-3, hi=3, raw_offset=64, signed=True,
          description=tr("Pitch of the part in octaves (±3)."), page=10),
        p("PART_COARSE_TUNE", 0x0B, "Coarse Tune", "PITCH", lo=-48, hi=48, raw_offset=64, signed=True, unit="st",
          description=tr("Pitch of the part in semitones (±4 octaves)."), page=10),
        p("PART_FINE_TUNE", 0x0C, "Fine Tune", "PITCH", lo=-50, hi=50, raw_offset=64, signed=True, unit="cent",
          description=tr("Pitch of the part in cents (±50); one cent is 1/100 of a semitone."), page=10),
        p("PART_PITCH_BEND_RANGE", 0x0F, "Bend Range", "PITCH", hi=25, choices=tuple(str(i) for i in range(25)) + (tone,),
          kind="knob", description=tr("Pitch change in semitones when the pitch bend wheel is moved (up to two octaves, the same up and down).") + " " + use_tone, page=10),
        p("PART_PORTAMENTO_SWITCH", 0x10, "Porta Sw", "PITCH", hi=2, choices=("OFF", "ON", tone), long=tr("Portamento Switch"),
          description=tr("ON: the pitch glides from one note to the next.") + " " + use_tone, page=10),
        p("PART_PORTAMENTO_TIME", 0x11, "Porta Time", "PITCH", hi=128, size=2, choices=tuple(str(i) for i in range(128)) + (tone,),
          kind="knob", long=tr("Portamento Time"), description=tr("Time over which the pitch glides.") + " " + use_tone, page=10),
        # OFFSET (p. 11)
        p("PART_CUTOFF_OFFSET", 0x13, "Cutoff Ofst", "OFFSET", long=tr("Cutoff Offset"),
          description=tr("Shifts the cutoff frequency of the tone or kit assigned to the part."), page=11, **signed),
        p("PART_RESONANCE_OFFSET", 0x14, "Reso Offset", "OFFSET", long=tr("Resonance Offset"),
          description=tr("Shifts the resonance of the tone or kit assigned to the part."), page=11, **signed),
        p("PART_ATTACK_TIME_OFFSET", 0x15, "Attack Ofst", "OFFSET", long=tr("Attack Offset"),
          description=tr("Shifts the Attack Time of the tone or kit assigned to the part."), page=11, **signed),
        p("PART_DECAY_TIME_OFFSET", 0x16, "Decay Offset", "OFFSET",
          description=tr("Shifts the Decay Time of the tone or kit assigned to the part."), page=11, **signed),
        p("PART_RELEASE_TIME_OFFSET", 0x17, "Release Ofst", "OFFSET", long=tr("Release Offset"),
          description=tr("Shifts the Release Time of the tone or kit assigned to the part."), page=11, **signed),
        p("PART_VIBRATO_RATE", 0x18, "Vibrato Rate", "OFFSET",
          description=tr("Vibrato speed of the part: higher values modulate the pitch faster."), page=11, **signed),
        p("PART_VIBRATO_DEPTH", 0x19, "Vibrato Depth", "OFFSET",
          description=tr("Vibrato depth of the part: higher values modulate the pitch more."), page=11, **signed),
        p("PART_VIBRATO_DELAY", 0x1A, "Vibrato Delay", "OFFSET",
          description=tr("Time before the vibrato starts: higher values start it later."), page=11, **signed),
        # KEYBOARD (MIDI only)
        p("PART_VELOCITY_SENS_OFFSET", 0x1C, "Velo Sens Ofst", "KEYBOARD", lo=-63, hi=63, raw_offset=64, signed=True,
          long=tr("Velocity Sensitivity Offset"), description=tr("Shifts how much the tone responds to how hard you play."), source=midi),
        p("VELOCITY_RANGE_LOWER", 0x21, "Velo Lower", "KEYBOARD", lo=1, long=tr("Velocity Range Lower"),
          description=tr("Lowest velocity that plays the part; softer notes are not heard."), source=midi),
        p("VELOCITY_RANGE_UPPER", 0x22, "Velo Upper", "KEYBOARD", long=tr("Velocity Range Upper"),
          description=tr("Highest velocity that plays the part; harder notes are not heard."), source=midi),
        p("VELOCITY_FADE_WIDTH_LOWER", 0x23, "Fade Lower", "KEYBOARD", long=tr("Velocity Fade Width Lower"),
          description=tr("How gradually the part fades in above the lower velocity limit (0: abrupt)."), source=midi),
        p("VELOCITY_FADE_WIDTH_UPPER", 0x24, "Fade Upper", "KEYBOARD", long=tr("Velocity Fade Width Upper"),
          description=tr("How gradually the part fades out below the upper velocity limit (0: abrupt)."), source=midi),
        # SCALE (MIDI only)
        p("PART_SCALE_TUNE_TYPE", 0x2F, "Scale Type", "SCALE", hi=8, choices=tuple(SCALE_TYPES), kind="list",
          long=tr("Scale Tune Type"), description=tr("Tuning of the part: equal temperament or a historical or non-Western scale; CUSTOM uses the twelve values below."),
          source=midi),
        p("PART_SCALE_TUNE_KEY", 0x30, "Scale Key", "SCALE", hi=11, choices=tuple(KEYS), kind="list",
          long=tr("Scale Tune Key"), description=tr("Key (tonic) of the scale."), source=midi),
    ]
    for i, key in enumerate(SCALE_KEYS):
        params.append(p(f"PART_SCALE_TUNE_{key}", 0x31 + i, KEYS[i], "SCALE", unit="cent", long=tr("Scale Tune for {note}").format(note=KEYS[i]),
                        description=tr("Tuning of this note in cents (±64)."), source=midi, **signed))
    params += [
        # MIDI (MIDI only)
        p("PART_SWITCH", 0x01, "Part Sw", "MIDI", hi=1, choices=("OFF", "ON"), long=tr("Part Switch"),
          description=tr("OFF: the part does not play."), source=midi),
        p("RECEIVE_CHANNEL", 0x00, "Rx Channel", "MIDI", hi=15, fmt=lambda v: str(v + 1), long=tr("Receive Channel"),
          parse=lambda t: int(t) - 1 if t.strip().isdigit() else None,
          description=tr("MIDI channel on which the part receives (1-16)."), source=midi),
        p("TONE_BANK_SELECT_MSB", 0x06, "Bank MSB", "MIDI", long=tr("Tone Bank Select MSB (CC# 0)"),
          description=tr("Bank of the tone assigned to the part (MSB)."), source=midi),
        p("TONE_BANK_SELECT_LSB", 0x07, "Bank LSB", "MIDI", long=tr("Tone Bank Select LSB (CC# 32)"),
          description=tr("Bank of the tone assigned to the part (LSB)."), source=midi),
        p("TONE_PROGRAM_NUMBER", 0x08, "Tone No.", "MIDI", fmt=lambda v: str(v + 1), long=tr("Tone Program Number (PC)"),
          parse=lambda t: int(t) - 1 if t.strip().isdigit() else None,
          description=tr("Number of the tone assigned to the part, within the bank."), source=midi),
    ]
    for name, offset, label, message in RECEIVE:
        params.append(p(name, offset, label, "MIDI", hi=1, choices=("OFF", "ON"),
                        long=tr("Receive {message}").format(message=message),
                        description=tr("Whether the part reacts to {message} messages.").format(message=message), source=midi))
    return Block(f"PART_{short}", f"PART {short}", _part_address(0x20, part), params,
                 request=rq1([0x18, 0x00, 0x20 + part, 0x00], 0x4C))


def zone_block(part: int) -> Block:
    short, _name = PARTS[part]
    midi = tr("MIDI Implementation")
    params = [
        PSpec("ZONE_OCTAVE_SHIFT", 0x19, "Zone Octave", tr("Zone Octave Shift"),
              tr("Octave of the keyboard for this part (the [Octave] buttons)."), lo=-3, hi=3, raw_offset=64, signed=True,
              group=f"KEYBOARD {short}", source=midi),
        PSpec("ARPEGGIO_SWITCH", 0x03, "Arpeggio", tr("Arpeggio Switch"),
              tr("Whether the arpeggio plays this part."), hi=1, choices=("OFF", "ON"), group=f"KEYBOARD {short}", source=midi),
    ]
    return Block(f"ZONE_{short}", f"ZONE {short}", _part_address(0x30, part), params,
                 request=rq1([0x18, 0x00, 0x30 + part, 0x00], 0x23))


# ----------------------------------------------------------------- views
class VelocityView(_Graph):
    """Which velocities play the part, with the fades: drag the lower and upper limits."""

    def __init__(self, editor: "ProgramPartsEditor", lower, upper, fade_lower, fade_upper):
        super().__init__(ACCENT, editor.info_hub, 70)
        self.lower, self.upper, self.fade_lower, self.fade_upper = lower, upper, fade_lower, fade_upper
        for pv in (lower, upper, fade_lower, fade_upper):
            pv.watch(lambda _v: self.update())

    def _x(self, velocity: float) -> float:
        r = self.plot_rect()
        return r.left() + r.width() * velocity / 127

    def handles(self):
        r = self.plot_rect()
        return [(QPointF(self._x(self.lower.value()), r.top()), self.lower),
                (QPointF(self._x(self.upper.value()), r.top()), self.upper)]

    def drag_to(self, index: int, pos: QPointF) -> None:
        r = self.plot_rect()
        velocity = round((pos.x() - r.left()) / r.width() * 127)
        (self.lower if index == 0 else self.upper).setValue(velocity)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        lo, hi = self.lower.value(), self.upper.value()
        path = QPainterPath(QPointF(self._x(max(0, lo - self.fade_lower.value())), r.bottom()))
        path.lineTo(QPointF(self._x(lo), r.top()))
        path.lineTo(QPointF(self._x(hi), r.top()))
        path.lineTo(QPointF(self._x(min(127, hi + self.fade_upper.value())), r.bottom()))
        fill = QColor(ACCENT)
        fill.setAlpha(60)
        p.setBrush(fill)
        p.setPen(QPen(QColor(ACCENT), 1.6))
        p.drawPath(path)
        self._draw_handles(p)
        p.setPen(QColor("#8a8d94"))
        p.setFont(QFont(self.font().family(), 7))
        p.drawText(QPointF(r.left(), r.bottom() + 11), "1")
        p.drawText(QPointF(r.right() - 16, r.bottom() + 11), "127")
        p.end()


class ScaleView(_Graph):
    """The twelve notes' tuning as bars around 0 cents; drag a bar to retune that note."""

    def __init__(self, editor: "ProgramPartsEditor", notes: list[ParamValue], key: ParamValue):
        super().__init__(ACCENT, editor.info_hub, 110)
        self.notes, self.key = notes, key
        for pv in notes + [key]:
            pv.watch(lambda _v: self.update())

    def _slot(self, i: int) -> QRectF:
        r = self.plot_rect()
        w = r.width() / 12
        return QRectF(r.left() + i * w, r.top(), w, r.height())

    def handles(self):
        out = []
        for i, pv in enumerate(self.notes):
            s = self._slot(i)
            out.append((QPointF(s.center().x(), s.center().y() - s.height() / 2 * pv.value() / 64), pv))
        return out

    def nearest_handle(self, pos: QPointF) -> Optional[int]:
        for i in range(12):
            if self._slot(i).contains(pos):
                return i
        return None

    def drag_to(self, index: int, pos: QPointF) -> None:
        s = self._slot(index)
        self.notes[index].setValue(round((s.center().y() - pos.y()) / (s.height() / 2) * 64))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        p.setPen(QPen(QColor("#3a3d44"), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()))
        p.setFont(QFont(self.font().family(), 7))
        for i, pv in enumerate(self.notes):
            s = self._slot(i)
            h = s.height() / 2 * pv.value() / 64
            bar = QRectF(s.center().x() - s.width() * 0.25, s.center().y() - max(h, 0), s.width() * 0.5, abs(h))
            color = QColor(ACCENT) if i == self.key.value() else QColor("#c9cbd1")
            p.fillRect(bar, color)
            p.setPen(QColor("#8a8d94"))
            p.drawText(QRectF(s.left(), r.bottom() + 1, s.width(), 12), Qt.AlignmentFlag.AlignHCenter, KEYS[i])
        self._draw_handles(p)
        p.end()


class NameField(QLineEdit):
    """The program name: 12 ASCII characters, sent as one message when edited."""

    def __init__(self, editor: "ProgramPartsEditor", pvs: list[ParamValue]):
        super().__init__()
        self.editor, self.pvs = editor, pvs
        self.setMaxLength(NAME_LENGTH)
        self.setFixedWidth(170)
        self.setStyleSheet(
            "QLineEdit { background: #121214; color: #ffffff; border: 1px solid #3a3d44; border-radius: 5px;"
            " padding: 3px 6px; font-family: monospace; font-size: 13px; }"
        )
        self.setToolTip(tr("Name of the program (12 characters)."))
        for pv in pvs:
            pv.watch(lambda _v: self._show())
        report_to(editor.info_hub, self, pvs[0])
        self.editingFinished.connect(self._send)

    def text_from_values(self) -> str:
        return "".join(chr(pv.value()) if 32 <= pv.value() <= 126 else " " for pv in self.pvs).rstrip()

    def _show(self) -> None:
        if not self.hasFocus():
            self.setText(self.text_from_values())

    def _send(self) -> None:
        text = "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in self.text())[:NAME_LENGTH].ljust(NAME_LENGTH)
        if text.rstrip() == self.text_from_values():
            return
        codes = [ord(ch) for ch in text]
        for pv, code in zip(self.pvs, codes):
            pv.blockSignals(True)
            pv.setValue(code)
            pv.blockSignals(False)
        self.editor.send_bytes(self.editor.blocks[0].address, codes)


# ---------------------------------------------------------------- editor
class ProgramPartsEditor(V2Editor):
    """Program common settings and the four parts, one section at a time."""

    ACCENT = ACCENT

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        blocks = [common_block()] + [part_block(i) for i in range(4)] + [zone_block(i) for i in range(4)]
        super().__init__(blocks, midi_helper=midi_helper, parent=parent, title=tr("Program: common and parts"))
        self.preset_helper = preset_helper
        self._link_dependencies()

    def part(self, name: str, part: int) -> ParamValue:
        short = PARTS[part][0]
        for key in (f"PART_{short}", f"ZONE_{short}"):
            try:
                return self.pv(name, key)
            except KeyError:
                continue
        raise KeyError(name)

    # --- layout
    def build_panels(self) -> None:
        self.panels_layout.addWidget(self._common_card())
        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        self.section_buttons = QButtonGroup(self)
        self.sections = QStackedWidget()
        builders = {
            "MAIN": self._main_column, "PITCH": self._pitch_column, "OFFSET": self._offset_column,
            "KEYBOARD": self._keyboard_column, "SCALE": self._scale_column, "MIDI": self._midi_column,
        }
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
            page = QWidget()
            page.setStyleSheet("background: transparent;")
            row = QHBoxLayout(page)
            row.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(10)
            for part, (_short, title) in enumerate(PARTS):
                card = self.card(title, self._section_source(section))
                builders[section](card.body, part)
                card.body.addStretch()
                row.addWidget(card, 1, Qt.AlignmentFlag.AlignTop)
            self.sections.addWidget(page)
        tabs.addStretch()
        self.section_buttons.idClicked.connect(self.show_section)
        self.section_buttons.button(0).setChecked(True)
        self.show_section(0)
        self.panels_layout.addLayout(tabs)
        self.panels_layout.addWidget(self.sections)
        self.panels_layout.addWidget(self.note(
            tr("Changes are heard at once and kept in the current program until another one is selected. "
               "To keep them, save the program on the JD-Xi with [Menu/Write]: the JD-Xi cannot be written to its memory via MIDI.")
        ))
        self.panels_layout.addStretch()

    def show_section(self, index: int) -> None:
        """Show one section; the others take no room (the page is as tall as its content)."""
        from PySide6.QtWidgets import QSizePolicy

        for i in range(self.sections.count()):
            policy = QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored
            self.sections.widget(i).setSizePolicy(policy, policy)
        self.sections.setCurrentIndex(index)
        button = self.section_buttons.button(index)
        if button is not None and not button.isChecked():
            button.setChecked(True)
        self.sections.adjustSize()

    @staticmethod
    def _section_source(section: str) -> str:
        if section in ("MAIN", "PITCH"):
            return tr("Parameter Guide, p. 10")
        if section == "OFFSET":
            return tr("Parameter Guide, p. 11")
        return tr("MIDI Implementation")

    def _common_card(self):
        card = self.card("PROGRAM: COMMON", tr("Parameter Guide, p. 10"))
        row = QHBoxLayout()
        names = [self.values[s] for s in self.blocks[0].params[:NAME_LENGTH]]
        name_box = QVBoxLayout()
        label = QLabel(tr("Program Name"))
        label.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        name_box.addWidget(label)
        self.name_field = NameField(self, names)
        name_box.addWidget(self.name_field)
        name_box.addStretch()
        row.addLayout(name_box)
        for name in ("PROGRAM_LEVEL", "PROGRAM_TEMPO"):
            row.addWidget(self.control(self.spec(name)))
        side = QVBoxLayout()
        side.addWidget(self.control(self.spec("VOCAL_EFFECT")))
        line = QHBoxLayout()
        line.addWidget(self.control(self.spec("VOCAL_EFFECT_PART")))
        line.addWidget(self.control(self.spec("AUTO_NOTE_SWITCH")))
        side.addLayout(line)
        row.addLayout(side)
        row.addWidget(self.control(self.spec("VOCAL_EFFECT_NUMBER")))
        row.addStretch()
        card.body.addLayout(row)
        return card

    def _controls(self, body, part: int, names: list[str], knobs_per_row: int = 4) -> None:
        specs = [self.part(name, part) for name in names]
        knobs = []
        for pv in specs:
            spec = pv.param
            if spec.widget_kind() == "knob":
                knobs.append(spec)
            else:
                body.addWidget(self.control(spec))
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, spec in enumerate(knobs):
            grid.addWidget(self.control(spec), i // knobs_per_row, i % knobs_per_row)
        body.addLayout(grid)

    def _main_column(self, body, part: int) -> None:
        self._controls(body, part, ["MUTE_SWITCH", "PART_OUTPUT_ASSIGN", "PART_MONO_POLY", "PART_LEGATO_SWITCH",
                                    "PART_LEVEL", "PART_PAN", "PART_DELAY_SEND_LEVEL", "PART_REVERB_SEND_LEVEL"], 2)

    def _pitch_column(self, body, part: int) -> None:
        self._controls(body, part, ["PART_PORTAMENTO_SWITCH", "PART_OCTAVE_SHIFT", "PART_COARSE_TUNE", "PART_FINE_TUNE",
                                    "PART_PITCH_BEND_RANGE", "PART_PORTAMENTO_TIME"], 2)

    def _offset_column(self, body, part: int) -> None:
        self._controls(body, part, ["PART_CUTOFF_OFFSET", "PART_RESONANCE_OFFSET", "PART_ATTACK_TIME_OFFSET",
                                    "PART_DECAY_TIME_OFFSET", "PART_RELEASE_TIME_OFFSET", "PART_VIBRATO_RATE",
                                    "PART_VIBRATO_DEPTH", "PART_VIBRATO_DELAY"], 2)

    def _keyboard_column(self, body, part: int) -> None:
        names = ["VELOCITY_RANGE_LOWER", "VELOCITY_RANGE_UPPER", "VELOCITY_FADE_WIDTH_LOWER", "VELOCITY_FADE_WIDTH_UPPER"]
        body.addWidget(VelocityView(self, *(self.part(n, part) for n in names)))
        self._controls(body, part, ["ARPEGGIO_SWITCH", "ZONE_OCTAVE_SHIFT", "PART_VELOCITY_SENS_OFFSET"] + names, 2)

    def _scale_column(self, body, part: int) -> None:
        notes = [self.part(f"PART_SCALE_TUNE_{k}", part) for k in SCALE_KEYS]
        body.addWidget(self.control(self.part("PART_SCALE_TUNE_TYPE", part).param))
        body.addWidget(self.control(self.part("PART_SCALE_TUNE_KEY", part).param))
        body.addWidget(ScaleView(self, notes, self.part("PART_SCALE_TUNE_KEY", part)))
        grid = QGridLayout()
        grid.setSpacing(2)
        for i, pv in enumerate(notes):
            grid.addWidget(self.control(pv.param), i // 4, i % 4)
        body.addLayout(grid)

    def _midi_column(self, body, part: int) -> None:
        self._controls(body, part, ["PART_SWITCH", "RECEIVE_CHANNEL", "TONE_BANK_SELECT_MSB", "TONE_BANK_SELECT_LSB",
                                    "TONE_PROGRAM_NUMBER"], 2)
        for name, *_rest in RECEIVE:
            body.addWidget(self.control(self.part(name, part).param))

    # --- dependencies
    def _link_dependencies(self) -> None:
        for part in range(4):
            output = self.part("PART_OUTPUT_ASSIGN", part)
            delay, reverb = self.part("PART_DELAY_SEND_LEVEL", part), self.part("PART_REVERB_SEND_LEVEL", part)

            def apply(_v=None, output=output, delay=delay, reverb=reverb):
                value = output.value()  # EFX1 EFX2 DLY REV DIR KIT
                delay.set_enabled(value <= 2)
                reverb.set_enabled(value <= 3)

            output.watch(apply)
            lower, upper = self.part("VELOCITY_RANGE_LOWER", part), self.part("VELOCITY_RANGE_UPPER", part)
            # Lower is 1 - UPPER, Upper is LOWER - 127 (MIDI Implementation)
            lower.valueChanged.connect(lambda v, upper=upper: upper.setValue(v) if upper.value() < v else None)
            upper.valueChanged.connect(lambda v, lower=lower: lower.setValue(v) if lower.value() > v else None)

    # --- sending several bytes at once (the name)
    def send_bytes(self, address: JDXiSysExAddress, data: list[int]) -> bool:
        helper = getattr(self, "_midi_helper", None)
        if helper is None:
            return False
        message = JDXiSysEx(sysex_address=address, value=list(data))
        return bool(helper.send_midi_message(message))
