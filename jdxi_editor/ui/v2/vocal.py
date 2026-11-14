"""
New Vocal Effect editor: AutoPitch and Vocoder.

Covers the Parameter Guide's "AutoPitch/Vocoder" page (p. 28) and the MIDI
Implementation tables Program Vocal Effect (18 00 01 00) and the vocal effect
settings of Program Common (18 00 00 16, 1C-1E).

Which effect the program uses is chosen at the top; only its settings are
active. The key of AutoPitch is chosen on two rows, major and minor, like the
key signatures in the manual.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QVBoxLayout, QPushButton, QWidget

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.ui.v2.framework import Block, PSpec, V2Editor, rq1
from jdxi_editor.ui.v2.params import ParamValue
from jdxi_editor.ui.v2.program import pan_parse, pan_text
from jdxi_editor.ui.v2.widgets import report_to
from jdxi_editor.ui.v2 import density

ACCENT = "#e86fb0"  # pink: purple is Drums
KEYS = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
        "Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm")
NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
MIC_HPF = ("BYPASS", "1000 Hz", "1250 Hz", "1600 Hz", "2000 Hz", "2500 Hz", "3150 Hz", "4000 Hz", "5000 Hz",
           "6300 Hz", "8000 Hz", "10000 Hz", "12500 Hz", "16000 Hz")
BALANCE = tuple(f"D{100 - v}:{v}W" for v in range(101))


def vocal_blocks() -> list[Block]:
    S = PSpec
    on_off = ("OFF", "ON")
    midi = tr("MIDI Implementation")
    common = Block("PROGRAM_COMMON", "PROGRAM", JDXiSysExAddress(0x18, 0x00, 0x00, 0x00), [
        S("VOCAL_EFFECT", 0x16, "Vocal Effect", tr("Vocal Effect"),
          tr("Which vocal effect the program uses: none, the vocoder (the selected digital part is the instrument) or AutoPitch (the external input is corrected; the selected digital part turns off)."),
          hi=2, choices=("OFF", "VOCODER", "AUTO-PITCH"), page=9),
        S("VOCAL_EFFECT_NUMBER", 0x1C, "VFX Number", tr("Vocal Effect Number"),
          tr("Number of the vocal effect setting used by the program."), hi=20, fmt=lambda v: str(v + 1), source=midi),
        S("VOCAL_EFFECT_PART", 0x1D, "VFX Part", tr("Vocal Effect Part"),
          tr("Digital part used by the vocal effect (Part 1 or Part 2)."), hi=1, choices=("1", "2"), page=9),
        S("AUTO_NOTE_SWITCH", 0x1E, "Auto Note", tr("Auto Note Switch"),
          tr("ON: AutoPitch corrects to the notes played on the keyboard."), hi=1, choices=on_off, source=midi),
    ])
    for spec in common.params:
        spec.group = "PROGRAM"
    vfx = Block("VOCAL_EFFECT", "VOCAL FX", JDXiSysExAddress(0x18, 0x00, 0x01, 0x00), [
        # output, shared by AutoPitch and the vocoder (p. 28)
        S("LEVEL", 0x00, "Level", description=tr("Volume of the sound that passes through the vocal effect."), page=28, group="OUTPUT"),
        S("PAN", 0x01, "Pan", lo=-64, hi=63, raw_offset=64, fmt=pan_text, parse=pan_parse,
          description=tr("Stereo position of the sound that passes through the vocal effect."), page=28, group="OUTPUT"),
        S("OUTPUT_ASSIGN", 0x04, "Output Asgn", tr("Output Assign"),
          tr("Where the sound goes: EFX1, EFX2, Delay, Reverb, or straight out without effects (DIR)."),
          hi=4, choices=("EFX1", "EFX2", "DLY", "REV", "DIR"), page=28, group="OUTPUT"),
        S("DELAY_SEND_LEVEL", 0x02, "Dly Send Lev", tr("Delay Send Level"),
          tr("Amount of delay applied to the sound of the vocal effect."), page=28, group="OUTPUT"),
        S("REVERB_SEND_LEVEL", 0x03, "Rev Send Lev", tr("Reverb Send Level"),
          tr("Amount of reverb applied to the sound of the vocal effect."), page=28, group="OUTPUT"),
        # AutoPitch (p. 28)
        S("AUTO_PITCH_SWITCH", 0x05, "AutoPitch Sw", tr("Auto Pitch Switch"), tr("Turns AutoPitch on or off."),
          hi=1, choices=on_off, source=midi, group="AUTOPITCH"),
        S("AUTO_PITCH_TYPE", 0x06, "Type", tr("Auto Pitch Type"),
          tr("SOFT: smooth correction. HARD: quick. ELECTRIC1: stepwise. ELECTRIC2: stronger, the mechanical stepwise correction of pop music."),
          hi=3, choices=("SOFT", "HARD", "ELECTRIC1", "ELECTRIC2"), page=28, group="AUTOPITCH"),
        S("AUTO_PITCH_SCALE", 0x07, "Scale", tr("Auto Pitch Scale"),
          tr("CHROMATIC: corrects to semitones. Maj(Min): to the notes of the key below."),
          hi=1, choices=("CHROMATIC", "Maj(Min)"), page=28, group="AUTOPITCH"),
        S("AUTO_PITCH_KEY", 0x08, "Key", tr("Auto Pitch Key"),
          tr("Key of the song: e.g. C for C major, Am for A minor."), hi=23, choices=KEYS, kind="keys", page=28,
          depends=tr("Only with Scale Maj(Min)."), group="AUTOPITCH"),
        S("AUTO_PITCH_NOTE", 0x09, "Note", tr("Auto Pitch Note"),
          tr("Note AutoPitch corrects to."), hi=11, choices=NOTES, kind="list", source=midi, group="AUTOPITCH"),
        S("AUTO_PITCH_GENDER", 0x0A, "Gender", tr("Auto Pitch Gender"),
          tr("Negative: a more masculine voice; positive: more feminine."), lo=-10, hi=10, raw_offset=10, signed=True,
          page=28, group="AUTOPITCH"),
        S("AUTO_PITCH_OCTAVE", 0x0B, "Octave", tr("Auto Pitch Octave"), tr("Raises or lowers the pitch by an octave."),
          lo=-1, hi=1, raw_offset=1, signed=True, page=28, group="AUTOPITCH"),
        S("AUTO_PITCH_BALANCE", 0x0C, "Balance", tr("Auto Pitch Balance"),
          tr("Volume balance between the direct sound (D) and the effect sound (W)."), hi=100, choices=BALANCE, kind="knob",
          page=28, group="AUTOPITCH"),
        # Vocoder (p. 28)
        S("VOCODER_SWITCH", 0x0D, "Vocoder Sw", tr("Vocoder Switch"), tr("Turns the vocoder on or off."),
          hi=1, choices=on_off, source=midi, group="VOCODER"),
        S("VOCODER_ENVELOPE", 0x0E, "Envelope", tr("Vocoder Envelope"),
          tr("Character of the sound. SHARP: emphasizes the voice. SOFT: the instrument. LONG: a vintage sound with a long decay."),
          hi=2, choices=("SHARP", "SOFT", "LONG"), page=28, group="VOCODER"),
        S("VOCODER_MIC_SENS", 0x10, "Mic Sens", tr("Vocoder Mic Sens"), tr("Input sensitivity of the mic."), page=28, group="VOCODER"),
        S("VOCODER_SYNTH_LEVEL", 0x11, "Synth Level", tr("Vocoder Synth Level"), tr("Input level of the instrument sound."),
          page=28, group="VOCODER"),
        S("VOCODER_MIC_MIX", 0x12, "Mic Mix", tr("Vocoder Mic Mix Level"),
          tr("How much of the mic, after the Mic HPF, is added to the vocoder output."), page=28, group="VOCODER"),
        S("VOCODER_MIC_HPF", 0x13, "Mic HPF", tr("Vocoder Mic HPF"),
          tr("Frequency from which the high-pass filter on the mic acts; BYPASS: no filter."), hi=13, choices=MIC_HPF, kind="list",
          page=28, group="VOCODER"),
        S("VOCODER_PARAM_0F", 0x0F, "Param 0F", tr("Vocal Effect, address 00 0F"),
          tr("A value the MIDI Implementation lists without a name (0-127)."), source=midi, group="VOCODER"),
    ], request=rq1([0x18, 0x00, 0x01, 0x00], 0x18))
    common.request = rq1([0x18, 0x00, 0x00, 0x00], 0x1F)
    common.export = False  # only four of Program Common's settings: the Program editor saves the block
    return [common, vfx]


class KeyButtons(QWidget):
    """The 24 keys of AutoPitch: majors on the first row, minors on the second."""

    def __init__(self, value: ParamValue, hub):
        super().__init__()
        self.pv = value
        self.group = QButtonGroup(self)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        for i, key in enumerate(KEYS):
            button = QPushButton(key)
            button.setCheckable(True)
            button.setMinimumSize(40, 26)
            button.setStyleSheet(
                "QPushButton { background: #1b1c1f; color: #c9cbd1; border: 1px solid #3a3d44; border-radius: 5px; font-weight: 600; }"
                "QPushButton:disabled { color: #5a5d64; }"
                f"QPushButton:checked {{ background: {ACCENT}; color: #0e0f11; border-color: {ACCENT}; }}"
            )
            self.group.addButton(button, i)
            grid.addWidget(button, i // 12, i % 12)
            report_to(hub, button, value)
        self.group.idClicked.connect(value.setValue)
        value.watch(lambda v: self.group.button(v).setChecked(True))
        value.watch_enabled(self.setEnabled)


class VocalEffectEditor(V2Editor):
    """AutoPitch and the vocoder of the current program."""

    ACCENT = ACCENT

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        super().__init__(vocal_blocks(), midi_helper=midi_helper, parent=parent, title=tr("Vocal Effect"))
        self.preset_helper = preset_helper
        self._link_dependencies()

    def control(self, spec, **kwargs):
        if spec.kind == "keys":
            return KeyButtons(self.values[spec], self.info_hub)
        return super().control(spec, **kwargs)

    def build_panels(self) -> None:
        s = self.spec
        top = self.card(tr("VOCAL EFFECT OF THE PROGRAM"), tr("Parameter Guide, p. 9, 28"))
        top.body.addWidget(self.control(s("VOCAL_EFFECT")))
        row = QHBoxLayout()
        middle = Qt.AlignmentFlag.AlignVCenter
        row.addWidget(self.control(s("VOCAL_EFFECT_PART")), 0, middle)
        row.addWidget(self.control(s("AUTO_NOTE_SWITCH")), 0, middle)
        row.addWidget(self.control(s("VOCAL_EFFECT_NUMBER")), 0, middle)
        row.addStretch()
        top.body.addLayout(row)
        self.panels_layout.addWidget(top)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        align = Qt.AlignmentFlag.AlignTop
        out = self.card("OUTPUT", tr("Parameter Guide, p. 28"))
        out.body.addWidget(self.control(s("OUTPUT_ASSIGN")))
        out.body.addLayout(self.knob_row([s("LEVEL"), s("PAN")]))
        out.body.addLayout(self.knob_row([s("DELAY_SEND_LEVEL"), s("REVERB_SEND_LEVEL")]))
        if density.very_narrow():  # a narrow screen: OUTPUT above VOCODER, beside AUTOPITCH
            side = QVBoxLayout()
            side.setSpacing(12)
            side.addWidget(out)
            cards.addLayout(side, 1)
        else:
            cards.addWidget(out, 1, align)

        auto = self.card("AUTOPITCH", tr("Parameter Guide, p. 28"))
        self.cards = {"AUTOPITCH": auto}
        for name in ("AUTO_PITCH_SWITCH", "AUTO_PITCH_TYPE", "AUTO_PITCH_SCALE", "AUTO_PITCH_KEY", "AUTO_PITCH_NOTE"):
            auto.body.addWidget(self.control(s(name)))
        auto.body.addLayout(self.knob_row([s("AUTO_PITCH_GENDER"), s("AUTO_PITCH_OCTAVE"), s("AUTO_PITCH_BALANCE")]))
        cards.addWidget(auto, 2, align)

        voc = self.card("VOCODER", tr("Parameter Guide, p. 28"))
        self.cards["VOCODER"] = voc
        for name in ("VOCODER_SWITCH", "VOCODER_ENVELOPE", "VOCODER_MIC_HPF"):
            voc.body.addWidget(self.control(s(name)))
        voc.body.addLayout(self.knob_row([s("VOCODER_MIC_SENS"), s("VOCODER_SYNTH_LEVEL"), s("VOCODER_MIC_MIX"), s("VOCODER_PARAM_0F")]))
        if density.very_narrow():
            side.addWidget(voc)
            side.addStretch()
        else:
            cards.addWidget(voc, 1, align)
        self.panels_layout.addLayout(cards)
        self.panels_layout.addWidget(self.note(
            tr("Vocoder/AutoPitch can be used for one part only; with it, the analog part cannot be selected (Parameter Guide, p. 4). "
               "The settings are saved with the program: save it on the JD-Xi with [Menu/Write].")
        ))
        self.panels_layout.addStretch()

    def _link_dependencies(self) -> None:
        effect = self.pv("VOCAL_EFFECT")
        auto = [pv for spec, pv in self.values.items() if spec.group == "AUTOPITCH"]
        voc = [pv for spec, pv in self.values.items() if spec.group == "VOCODER"]
        scale, key = self.pv("AUTO_PITCH_SCALE"), self.pv("AUTO_PITCH_KEY")

        def apply(_v=None):
            for pv in auto:
                pv.set_enabled(effect.value() == 2)
            for pv in voc:
                pv.set_enabled(effect.value() == 1)
            key.set_enabled(effect.value() == 2 and scale.value() == 1)
            self.pv("AUTO_NOTE_SWITCH").set_enabled(effect.value() == 2)

        effect.watch(apply)
        scale.watch(apply)
