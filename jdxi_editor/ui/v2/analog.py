"""
Analog Synth editor of the new interface.

Six panels named and ordered as on the JD-Xi display (TONE: OSC, PITCH,
FILTER, AMP, LFO, COMMON), every Analog parameter of the Parameter Guide on
screen (46, plus Pitch Env Velocity Sens from the MIDI Implementation), drawn
where a picture helps, and an information panel for the parameter under the
pointer.

It inherits the whole MIDI side of AnalogSynthEditor (presets, requests,
incoming SysEx, .syx import/export, patch files): only the widgets change.
Each parameter is a ParamValue in ``self.controls``; changes are sent at most
every SEND_INTERVAL_MS while dragging, and the last value always goes out.
"""

from __future__ import annotations

import random
from typing import Optional

from decologr import Decologr as log
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.parameter.analog.address import AnalogParam
from jdxi_editor.ui.editors.analog.editor import AnalogSynthEditor
from jdxi_editor.ui.editors.synth.base import SynthBase
from jdxi_editor.ui.preset.widget import InstrumentPresetWidget
from jdxi_editor.ui.v2.params import ParamValue, analog_info
from jdxi_editor.ui.v2.widgets import (
    Card,
    ChoiceButtons,
    EnvelopeView,
    FilterCurveView,
    InfoHub,
    InfoPanel,
    Knob,
    LfoView,
    NoteCombo,
    WaveButtons,
    section_label,
)

ACCENT = "#3fa7f5"  # Analog blue
SEND_INTERVAL_MS = 25


class AnalogToneEditor(AnalogSynthEditor):
    """The Analog Synth tone, every parameter on one screen."""

    def update_instrument_image(self) -> None:
        """The preset's category as a card, as in the Digital and Drums panels."""
        from jdxi_editor.ui.v2.framework import show_category_card

        show_category_card(self, ACCENT)

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        self.values: dict[AnalogParam, ParamValue] = {}
        self.info_hub: Optional[InfoHub] = None
        self._pending: dict = {}
        super().__init__(midi_helper=midi_helper, preset_helper=preset_helper, parent=parent)

    def reload_sound(self) -> None:
        from jdxi_editor.ui.v2.framework import restore_sound

        restore_sound(self)

    # ------------------------------------------------------------------ layout
    def setup_ui(self) -> None:
        self.setMinimumSize(1000, 640)
        self.resize(1320, 820)
        self.setStyleSheet("AnalogToneEditor { background: #121214; }")
        self._send_timer = QTimer(self)
        self._send_timer.setInterval(SEND_INTERVAL_MS)
        self._send_timer.timeout.connect(self._flush_pending)
        self.info_hub = InfoHub(self)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        self.main_layout = root

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.scroll = scroll
        self.cards_host = QWidget()
        self.cards_host.setStyleSheet("background: transparent;")
        self.cards = QHBoxLayout(self.cards_host)
        self.cards.setContentsMargins(0, 0, 0, 0)
        self.cards.setSpacing(12)
        self._columns = 0
        scroll.setWidget(self.cards_host)
        # the editor's name as a badge in its colour, as at the top of the other editors
        from jdxi_editor.ui.v2.restyle import title_badge

        left = QVBoxLayout()
        left.setSpacing(10)
        bar = QHBoxLayout()
        self.title_label = title_badge(tr("Analog"), ACCENT)
        bar.addWidget(self.title_label)
        # the user's changes: undo / redo, reload, and a warning before they are lost
        from jdxi_editor.ui.v2.history import ANALOG, EditHistory
        from jdxi_editor.ui.v2.restyle import edit_controls

        self.history = EditHistory(ANALOG, tr("Analog"), self)
        self.modified_label, self.edit_buttons = edit_controls(self, reload=self.reload_sound)
        bar.addWidget(self.modified_label)
        bar.addStretch()
        for button in self.edit_buttons:
            bar.addWidget(button)
        left.addLayout(bar)
        left.addWidget(scroll, 1)
        root.addLayout(left, 1)

        # Tone panel and information panel, scrolling on short screens
        side_host = QWidget()
        side_host.setStyleSheet("background: transparent;")
        side = QVBoxLayout(side_host)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(12)
        # Tone choice, reading from the JD-Xi, .syx: the existing preset panel
        self.instrument_preset = InstrumentPresetWidget(parent=self)
        self.instrument_preset.setup_header_layout()
        self.instrument_preset.setup()
        self.instrument_preset_group = self.instrument_preset.create_instrument_preset_group()
        self.instrument_preset.add_preset_group(self.instrument_preset_group)
        (
            self.instrument_image_group,
            self.instrument_image_label,
            self.instrument_group_layout,
        ) = self.instrument_preset.create_instrument_image_group()
        self.instrument_preset.add_image_group(self.instrument_image_group)
        self.instrument_preset.setFixedWidth(340)
        # the app's theme for the preset panel only (its buttons need it)
        from jdxi_editor.core.jdxi import JDXi

        JDXi.UI.Theme.apply_editor_style(self.instrument_preset)
        # the same look as the Digital and Drums panels: no blue frame of its own,
        # both tabs readable (they scrolled behind arrows)
        from PySide6.QtWidgets import QTabWidget

        from jdxi_editor.ui.v2.framework import finish_preset_panel

        self.instrument_preset_group.setStyleSheet("")
        for tabs in self.instrument_preset.findChildren(QTabWidget):
            tabs.setUsesScrollButtons(False)
            tabs.tabBar().setExpanding(True)
            tabs.setStyleSheet("QTabBar::tab { padding: 6px 8px; }")

        finish_preset_panel(self, ACCENT)
        side.addWidget(self.instrument_preset)
        self.info_panel = InfoPanel(ACCENT)
        self.info_panel.setFixedWidth(340)
        self.info_hub.shown.connect(self.info_panel.show_param)
        self.info_panel.setMinimumHeight(260)
        side.addWidget(self.info_panel, 1)
        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_scroll.setFixedWidth(356)
        side_scroll.setWidget(side_host)
        root.addWidget(side_scroll)

    def _pv(self, param: AnalogParam) -> ParamValue:
        return self.values[param]

    def _create_sections(self) -> None:
        """Build a ParamValue for every parameter and the six panels."""
        infos = analog_info()
        for param in AnalogParam:
            info = infos.get(param.name)
            if info is None:  # TONE_NAME_1..12: edited with the tone name
                continue
            lo, hi = param.get_display_value()
            pv = ParamValue(param, info, lo, hi, self)
            pv.valueChanged.connect(lambda v, param=param: self._queue_send(param, v))
            self.values[param] = pv
        self.controls.update(self.values)
        self.history.watch(self.values.values())

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
            column.setSpacing(12)
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

    # --- the old editor's section plumbing has nothing to do here
    def _build_parameter_mappings(self) -> None:
        pass

    def add_tabs(self) -> None:
        pass

    def update_filter_controls_state(self, mode: int) -> None:
        pass

    # ---------------------------------------------------------------- sending
    def _queue_send(self, param: AnalogParam, value: int) -> None:
        """Send now if idle; while dragging, at most every SEND_INTERVAL_MS."""
        self._pending[param] = value
        if not self._send_timer.isActive():
            self._flush_pending()
            self._send_timer.start()

    def _flush_pending(self) -> None:
        if not self._pending:
            self._send_timer.stop()
            return
        pending, self._pending = self._pending, {}
        for param, value in pending.items():
            self.send_midi_parameter(param, value, self.address)

    # --------------------------------------------------------------- receiving
    def _update_controls(self, partial_no: int, sysex_data: dict, successes: list, failures: list) -> None:
        """Values read from the JD-Xi: shown, not sent back."""
        for name, raw in sysex_data.items():
            param = AnalogParam.get_by_name(name) if isinstance(name, str) else None
            pv = self.values.get(param) if param is not None else None
            if pv is None:
                continue
            try:
                display = param.convert_from_midi(int(raw)) if hasattr(param, "convert_from_midi") else int(raw)
            except (TypeError, ValueError):
                failures.append(name)
                continue
            pv.blockSignals(True)
            pv.setValue(display)
            pv.blockSignals(False)
            successes.append(name)

    def get_controls_as_dict(self) -> dict:
        return SynthBase.get_controls_as_dict(self)

    def randomize_analog_patch(self) -> int:
        """Random values in each parameter's range (as on the display), sent at once."""
        changed = 0
        for pv in self.values.values():
            step = max(1, pv.info.step)
            choices = range(pv.minimum, pv.maximum + 1, step)
            pv.setValue(random.choice(list(choices)))
            changed += 1
        self.values[AnalogParam.AMP_LEVEL].setValue(100)  # never silent
        log.message(f"Randomized {changed} Analog parameters", scope=self.__class__.__name__)
        return changed
