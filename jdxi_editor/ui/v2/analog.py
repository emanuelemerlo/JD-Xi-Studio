"""
Analog Synth editor of the new interface.

Six panels named and ordered as on the JD-Xi display (TONE: OSC, PITCH,
FILTER, AMP, LFO, COMMON), every Analog parameter of the Parameter Guide on
screen (46, plus Pitch Env Velocity Sens from the MIDI Implementation), drawn
where a picture helps, and an information panel for the parameter under the
pointer.

Built on the v2 framework like Digital and Drums (tone_editor_base): one block,
the Analog tone at 19 42 00 00, a PSpec per parameter. Values from the JD-Xi
are read straight from its DT1 messages (a whole block or one parameter);
changes are sent at most every SEND_INTERVAL_MS while dragging, and the last
value always goes out. (It used to inherit the old AnalogSynthEditor: its own
receiving path and value model.) ``editor.values`` takes an AnalogParam as key
as well as a PSpec.
"""

from __future__ import annotations

import random
from typing import Optional

from decologr import Decologr as log
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from dataclasses import dataclass
from jdxi_editor.i18n import tr
from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.midi.data.parameter.analog.address import AnalogParam
from jdxi_editor.ui.v2.framework import Block, NameField, PSpec, rq1, tone_editor_base
from jdxi_editor.ui.v2.params import ParamInfo, ParamValue, analog_info
from jdxi_editor.ui.v2.widgets import (
    Card,
    ChoiceButtons,
    EnvelopeView,
    FilterCurveView,
    Knob,
    LfoView,
    NoteCombo,
    WaveButtons,
    section_label,
)
from jdxi_editor.ui.v2 import density

ACCENT = "#3fa7f5"  # Analog blue
SEND_INTERVAL_MS = 25



ANALOG_ADDRESS = (0x19, 0x42, 0x00, 0x00)
ANALOG_SIZE = 0x40
NAME_LENGTH = 12


@dataclass(eq=False)
class AnalogSpec(PSpec):
    """An Analog parameter: its information is the Analog editor's own (analog_info)."""

    param_info: Optional[ParamInfo] = None

    def info(self, group: str, area: str = "TONE") -> ParamInfo:
        return self.param_info if self.param_info is not None else super().info(group, area)


def analog_block() -> Block:
    """The Analog tone (Temporary Tone 19 42 00 00): its name, then every parameter."""
    params: list[PSpec] = [
        PSpec(f"TONE_NAME_{i + 1}", i, f"Name {i + 1}", lo=32, hi=127,
              description=tr("Name of the tone (12 characters)."), page=12)
        for i in range(NAME_LENGTH)
    ]
    infos = analog_info()
    for param in AnalogParam:
        info = infos.get(param.name)
        if info is None:  # the name's characters: above
            continue
        lo, hi = param.get_display_value()
        factor = 10 if param.name.endswith("_KEYFOLLOW") else 1  # -100..+100 in steps of 10
        raw_offset = param.convert_to_midi(lo) - lo // factor
        params.append(AnalogSpec(param.name, param.address, info.label, lo=lo, hi=hi,
                                 raw_offset=raw_offset, factor=factor, choices=tuple(info.choices),
                                 param_info=info))
    return Block("COMMON", "TONE", JDXiSysExAddress(*ANALOG_ADDRESS), params,
                 request=rq1(list(ANALOG_ADDRESS), ANALOG_SIZE))


class AnalogValues(dict):
    """The editor's values by PSpec, and by AnalogParam for the code that names them so."""

    def __init__(self, values: dict, by_name: dict):
        super().__init__(values)
        self._by_name = by_name

    def _key(self, key):
        return self._by_name.get(key.name, key) if isinstance(key, AnalogParam) else key

    def __getitem__(self, key):
        return super().__getitem__(self._key(key))

    def __contains__(self, key) -> bool:
        return super().__contains__(self._key(key))

    def get(self, key, default=None):
        return super().get(self._key(key), default)


class AnalogToneEditor(tone_editor_base()):
    """The Analog Synth tone, every parameter on one screen."""

    ACCENT = ACCENT
    SYNTH_TYPE = JDXiSynth.ANALOG_SYNTH
    PRESET_KIND = "Analog"

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        self.preset_helper = preset_helper
        super().__init__([analog_block()], midi_helper=midi_helper, parent=parent, title=tr("Analog"))
        self.preset_helper = preset_helper

    def _pv(self, param: AnalogParam) -> ParamValue:
        return self.values[param]

    # ------------------------------------------------------------------ layout
    def build_panels(self) -> None:
        """The six panels in columns (three when there is room) and the tone's name."""
        block = self.blocks[0]
        self.values = AnalogValues(self.values, {s.name: s for s in block.params})
        self.controls = dict(self.values)
        names = [self.values[s] for s in block.params[:NAME_LENGTH]]
        name_row = QHBoxLayout()
        label = QLabel(tr("Tone Name"))
        label.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        name_row.addWidget(label)
        self.name_field = NameField(self, names, block.address, tr("Name of the tone (12 characters)."))
        name_row.addWidget(self.name_field)
        name_row.addStretch()
        self.panels_layout.addLayout(name_row)
        self.cards_host = QWidget()
        self.cards_host.setStyleSheet("background: transparent;")
        self.cards = QHBoxLayout(self.cards_host)
        self.cards.setContentsMargins(0, 0, 0, 0)
        self.cards.setSpacing(density.px(12))
        self._columns = 0
        self.panels_layout.addWidget(self.cards_host)
        self.panels_layout.addStretch()
        self._create_panels()

    def side_widgets(self) -> list:
        widgets = super().side_widgets()
        # both preset tabs readable (they scrolled behind arrows)
        from PySide6.QtWidgets import QTabWidget

        self.instrument_preset_group.setStyleSheet("")
        for tabs in self.instrument_preset.findChildren(QTabWidget):
            tabs.setUsesScrollButtons(False)
            tabs.tabBar().setExpanding(True)
            tabs.setStyleSheet("QTabBar::tab { padding: 6px 8px; }")
        return widgets

    def _create_panels(self) -> None:
        """The six panels, as on the JD-Xi display."""
        P = AnalogParam
        hub = self.info_hub
        knob = lambda p: Knob(self._pv(p), ACCENT, hub)  # noqa: E731

        # --- OSC
        osc = Card("OSC", ACCENT, tr("oscillator"))
        osc.body.addWidget(
            WaveButtons(self._pv(P.OSC_WAVEFORM), ACCENT, hub, pulse_width=self._pv(P.OSC_PULSE_WIDTH), button_width=74)
        )
        row = QHBoxLayout()
        for p in (P.OSC_PULSE_WIDTH, P.OSC_PULSE_WIDTH_MOD_DEPTH):
            row.addWidget(knob(p))
        row.addStretch()
        osc.body.addLayout(row)
        osc.body.addWidget(ChoiceButtons(self._pv(P.SUB_OSCILLATOR_TYPE), ACCENT, hub))
        osc.body.addStretch()

        # --- PITCH
        pitch = Card("PITCH", ACCENT, tr("pitch and pitch envelope"))
        row = QHBoxLayout()
        for p in (P.OSC_PITCH_COARSE, P.OSC_PITCH_FINE):
            row.addWidget(knob(p))
        row.addStretch()
        pitch.body.addLayout(row)
        pitch.body.addWidget(section_label(tr("Pitch envelope")))
        pitch.body.addWidget(
            EnvelopeView(
                ACCENT, hub,
                self._pv(P.OSC_PITCH_ENV_ATTACK_TIME), self._pv(P.OSC_PITCH_ENV_DECAY_TIME),
                depth=self._pv(P.OSC_PITCH_ENV_DEPTH),
            )
        )
        row = QHBoxLayout()
        for p in (P.OSC_PITCH_ENV_ATTACK_TIME, P.OSC_PITCH_ENV_DECAY_TIME, P.OSC_PITCH_ENV_DEPTH, P.OSC_PITCH_ENV_VELOCITY_SENSITIVITY):
            row.addWidget(knob(p))
        pitch.body.addLayout(row)

        # --- FILTER
        flt = Card("FILTER", ACCENT, tr("analog low-pass filter"))
        flt.body.addWidget(ChoiceButtons(self._pv(P.FILTER_MODE_SWITCH), ACCENT, hub))
        flt.body.addWidget(
            FilterCurveView(ACCENT, hub, self._pv(P.FILTER_CUTOFF), self._pv(P.FILTER_RESONANCE), self._pv(P.FILTER_MODE_SWITCH))
        )
        row = QHBoxLayout()
        for p in (P.FILTER_CUTOFF, P.FILTER_RESONANCE, P.FILTER_CUTOFF_KEYFOLLOW):
            row.addWidget(knob(p))
        row.addStretch()
        flt.body.addLayout(row)
        flt.body.addWidget(section_label(tr("Filter envelope")))
        flt.body.addWidget(
            EnvelopeView(
                ACCENT, hub,
                self._pv(P.FILTER_ENV_ATTACK_TIME), self._pv(P.FILTER_ENV_DECAY_TIME),
                self._pv(P.FILTER_ENV_SUSTAIN_LEVEL), self._pv(P.FILTER_ENV_RELEASE_TIME),
            )
        )
        row = QHBoxLayout()
        for p in (P.FILTER_ENV_ATTACK_TIME, P.FILTER_ENV_DECAY_TIME, P.FILTER_ENV_SUSTAIN_LEVEL, P.FILTER_ENV_RELEASE_TIME):
            row.addWidget(knob(p))
        flt.body.addLayout(row)
        row = QHBoxLayout()  # how much the envelope moves the cutoff
        for p in (P.FILTER_ENV_DEPTH, P.FILTER_ENV_VELOCITY_SENSITIVITY):
            row.addWidget(knob(p))
        row.addStretch()
        flt.body.addLayout(row)

        # --- AMP
        amp = Card("AMP", ACCENT, tr("volume and envelope"))
        row = QHBoxLayout()
        for p in (P.AMP_LEVEL, P.AMP_LEVEL_VELOCITY_SENSITIVITY, P.AMP_LEVEL_KEYFOLLOW):
            row.addWidget(knob(p))
        row.addStretch()
        amp.body.addLayout(row)
        amp.body.addWidget(section_label(tr("Amp envelope")))
        amp.body.addWidget(
            EnvelopeView(
                ACCENT, hub,
                self._pv(P.AMP_ENV_ATTACK_TIME), self._pv(P.AMP_ENV_DECAY_TIME),
                self._pv(P.AMP_ENV_SUSTAIN_LEVEL), self._pv(P.AMP_ENV_RELEASE_TIME),
            )
        )
        row = QHBoxLayout()
        for p in (P.AMP_ENV_ATTACK_TIME, P.AMP_ENV_DECAY_TIME, P.AMP_ENV_SUSTAIN_LEVEL, P.AMP_ENV_RELEASE_TIME):
            row.addWidget(knob(p))
        amp.body.addLayout(row)
        amp.body.addStretch()

        # --- LFO
        lfo = Card("LFO", ACCENT, tr("vibrato, wah, tremolo"))
        lfo.body.addWidget(WaveButtons(self._pv(P.LFO_SHAPE), ACCENT, hub))
        lfo.body.addWidget(
            LfoView(
                ACCENT, hub, self._pv(P.LFO_SHAPE), self._pv(P.LFO_RATE), self._pv(P.LFO_FADE_TIME),
                self._pv(P.LFO_TEMPO_SYNC_SWITCH), self._pv(P.LFO_TEMPO_SYNC_NOTE),
            )
        )
        row = QHBoxLayout()
        row.addWidget(knob(P.LFO_RATE))
        row.addWidget(knob(P.LFO_FADE_TIME))
        switches = QVBoxLayout()
        switches.addWidget(ChoiceButtons(self._pv(P.LFO_TEMPO_SYNC_SWITCH), ACCENT, hub))
        switches.addWidget(NoteCombo(self._pv(P.LFO_TEMPO_SYNC_NOTE), hub))
        switches.addWidget(ChoiceButtons(self._pv(P.LFO_KEY_TRIGGER), ACCENT, hub))
        row.addLayout(switches)
        lfo.body.addLayout(row)
        lfo.body.addWidget(section_label(tr("Depth: vibrato, wah, tremolo")))
        row = QHBoxLayout()
        for p in (P.LFO_PITCH_DEPTH, P.LFO_FILTER_DEPTH, P.LFO_AMP_DEPTH):
            row.addWidget(knob(p))
        row.addStretch()
        lfo.body.addLayout(row)
        lfo.body.addWidget(section_label(tr("Modulation wheel (CC01)")))
        row = QHBoxLayout()
        for p in (P.LFO_PITCH_MODULATION_CONTROL, P.LFO_FILTER_MODULATION_CONTROL, P.LFO_AMP_MODULATION_CONTROL, P.LFO_RATE_MODULATION_CONTROL):
            row.addWidget(knob(p))
        row.addStretch()
        lfo.body.addLayout(row)

        # --- COMMON
        common = Card("COMMON", ACCENT, tr("playing"))
        common.body.addWidget(ChoiceButtons(self._pv(P.PORTAMENTO_SWITCH), ACCENT, hub))
        common.body.addWidget(ChoiceButtons(self._pv(P.LEGATO_SWITCH), ACCENT, hub))
        common.body.addWidget(
            ChoiceButtons(self._pv(P.OCTAVE_SHIFT), ACCENT, hub, labels=["-3", "-2", "-1", "0", "+1", "+2", "+3"])
        )
        row = QHBoxLayout()
        for p in (P.PORTAMENTO_TIME, P.PITCH_BEND_UP, P.PITCH_BEND_DOWN):
            row.addWidget(knob(p))
        row.addStretch()
        common.body.addLayout(row)
        mono = QLabel(tr("The Analog part is monophonic: one note at a time."))
        mono.setWordWrap(True)
        mono.setStyleSheet("color: #8a8d94; font-size: 11px; background: transparent;")
        common.body.addWidget(mono)
        common.body.addStretch()

        self.panels = {"OSC": osc, "PITCH": pitch, "FILTER": flt, "AMP": amp, "LFO": lfo, "COMMON": common}
        self._reflow()

        self._link_dependencies()

    # Panels in columns, in display order; three columns when there is room
    LAYOUTS = {
        3: (("OSC", "AMP"), ("PITCH", "LFO"), ("FILTER", "COMMON")),
        2: (("OSC", "PITCH", "AMP"), ("FILTER", "LFO", "COMMON")),
    }
    def _needed_width(self, columns: int) -> int:
        spacing = self.cards.spacing()
        widths = [max(self.panels[n].minimumSizeHint().width() for n in names) for names in self.LAYOUTS[columns]]
        return sum(widths) + spacing * (columns - 1)

    def _reflow(self) -> None:
        room = self.scroll.viewport().width() - self.scroll.verticalScrollBar().sizeHint().width()
        columns = 3 if room >= self._needed_width(3) else 2
        if columns == self._columns:
            return
        self._columns = columns
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.layout() is not None:
                while item.layout().count():
                    item.layout().takeAt(0)
        for names in self.LAYOUTS[columns]:
            column = QVBoxLayout()
            column.setSpacing(density.px(12))
            for name in names:
                column.addWidget(self.panels[name])
            column.addStretch(1)
            self.cards.addLayout(column, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if getattr(self, "panels", None):
            self._reflow()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if getattr(self, "panels", None):
            self._reflow()

    def _link_dependencies(self) -> None:
        """Grey out what has no effect with the current settings."""
        P = AnalogParam
        v = self.values
        v[P.OSC_WAVEFORM].watch(
            lambda w: [v[p].set_enabled(w == 2) for p in (P.OSC_PULSE_WIDTH, P.OSC_PULSE_WIDTH_MOD_DEPTH)]
        )
        lpf = (
            P.FILTER_CUTOFF, P.FILTER_RESONANCE, P.FILTER_CUTOFF_KEYFOLLOW, P.FILTER_ENV_VELOCITY_SENSITIVITY,
            P.FILTER_ENV_ATTACK_TIME, P.FILTER_ENV_DECAY_TIME, P.FILTER_ENV_SUSTAIN_LEVEL,
            P.FILTER_ENV_RELEASE_TIME, P.FILTER_ENV_DEPTH,
        )
        v[P.FILTER_MODE_SWITCH].watch(lambda m: [v[p].set_enabled(bool(m)) for p in lpf])
        v[P.LFO_TEMPO_SYNC_SWITCH].watch(
            lambda s: (v[P.LFO_RATE].set_enabled(not s), v[P.LFO_TEMPO_SYNC_NOTE].set_enabled(bool(s)))
        )
        v[P.PORTAMENTO_SWITCH].watch(lambda s: v[P.PORTAMENTO_TIME].set_enabled(bool(s)))

    def randomize_analog_patch(self) -> int:
        """Random values in each parameter's range (as on the display), sent at once."""
        changed = 0
        for spec, pv in self.values.items():
            if spec.name.startswith("TONE_NAME_"):
                continue  # the name stays
            step = max(1, pv.info.step)
            choices = range(pv.minimum, pv.maximum + 1, step)
            pv.setValue(random.choice(list(choices)))
            changed += 1
        self.values[AnalogParam.AMP_LEVEL].setValue(100)  # never silent
        log.message(f"Randomized {changed} Analog parameters", scope=self.__class__.__name__)
        return changed
