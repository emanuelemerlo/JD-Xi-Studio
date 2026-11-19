"""
«New sound» (sound-design spec §6, Phase 5): three ways in, each with a line
that says what it does.

    From scratch (Init)   the part's tone to a plain starting point
    From a preset         a factory tone (the preset itself never changes)
    From a recipe         a recipe from the library

Init, Digital and Analog each its own (within their parameters):
- Digital: partial 1 on (2 and 3 off), sawtooth, low-pass filter open,
  amplitude envelope A=0 / S=max / R short, no LFO, no modulation
- Analog: sawtooth, filter open, the same envelopes, LFO at zero

It touches only the part's tone (its Temporary Tone blocks): not the other
parts, not the program's effects, not the part's send levels. It is one
step of Undo. A part with changes is asked about first (the uniform warning).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMenu, QToolButton, QWidget

from jdxi_editor.i18n import tr

INIT_NAME = "Init Tone"

# name -> display value, or a choice's label (str); every other parameter goes
# to its neutral value: 0 when the range is around 0, else the bottom of it
DIGITAL_COMMON = {
    "TONE_LEVEL": 100,
    "PARTIAL1_SWITCH": 1, "PARTIAL2_SWITCH": 0, "PARTIAL3_SWITCH": 0,
    "PARTIAL1_SELECT": 1,
    "PITCH_BEND_RANGE_UP": 2, "PITCH_BEND_RANGE_DOWN": 2,
}
DIGITAL_PARTIAL = {
    "OSC_WAVE": "SAW",
    "OSC_PULSE_WIDTH": 64,
    "FILTER_MODE": "LPF",
    "FILTER_CUTOFF": 127,
    "FILTER_RESONANCE": 0,
    "FILTER_ENV_SUSTAIN_LEVEL": 127,
    "AMP_LEVEL": 100,
    "AMP_ENV_ATTACK_TIME": 0,
    "AMP_ENV_DECAY_TIME": 0,
    "AMP_ENV_SUSTAIN_LEVEL": 127,
    "AMP_ENV_RELEASE_TIME": 20,
    "LFO_RATE": 64,
    "MOD_LFO_RATE": 64,
}
ANALOG = {
    "OSC_WAVEFORM": "SAW",
    "OSC_PULSE_WIDTH": 64,
    "SUB_OSCILLATOR_TYPE": "OFF",
    "FILTER_MODE_SWITCH": "LPF",
    "FILTER_CUTOFF": 127,
    "FILTER_RESONANCE": 0,
    "FILTER_ENV_SUSTAIN_LEVEL": 127,
    "AMP_LEVEL": 100,
    "AMP_ENV_ATTACK_TIME": 0,
    "AMP_ENV_DECAY_TIME": 0,
    "AMP_ENV_SUSTAIN_LEVEL": 127,
    "AMP_ENV_RELEASE_TIME": 20,
    "PITCH_BEND_UP": 2, "PITCH_BEND_DOWN": 2,
    "LFO_RATE": 64,
}


def _neutral(spec) -> int:
    return 0 if spec.lo < 0 <= spec.hi else spec.lo


def _display_value(spec, wanted) -> Optional[int]:
    """*wanted* (a number, or a choice's label) as the parameter's display value."""
    if isinstance(wanted, str):
        labels = [str(c).upper() for c in spec.choices]
        target = wanted.upper()
        for i, label in enumerate(labels):
            if label == target or label.startswith(target):
                return spec.lo + i
        return None
    return max(spec.lo, min(spec.hi, int(wanted)))


def init_values(editor) -> dict:
    """ParamValue -> value for Init, on the editor's tone blocks (none for others)."""
    synth = getattr(editor, "SYNTH_TYPE", None)
    from jdxi_editor.core.synth.type import JDXiSynth

    analog = synth == JDXiSynth.ANALOG_SYNTH
    digital = synth in (JDXiSynth.DIGITAL_SYNTH_1, JDXiSynth.DIGITAL_SYNTH_2)
    if not (analog or digital):
        return {}
    plan = {}
    for block in editor.blocks:
        if digital:
            overrides = DIGITAL_COMMON if block.key == "COMMON" else (
                DIGITAL_PARTIAL if block.key.startswith("PARTIAL") else {})
        else:
            overrides = ANALOG
        for spec in block.params:
            if spec.name.startswith("TONE_NAME"):
                continue  # the name: set as text (Init Tone)
            pv = editor.values.get(spec)
            if pv is None:
                continue
            wanted = overrides.get(spec.name)
            value = _display_value(spec, wanted) if wanted is not None else None
            plan[pv] = value if value is not None else _neutral(spec)
    return plan


def can_init(editor) -> bool:
    return bool(init_values(editor))


def init_part(editor, ask: bool = True) -> bool:
    """Init the editor's part: one step of Undo. False if not done (cancelled)."""
    from jdxi_editor.ui.v2 import history as history_module

    plan = init_values(editor)
    if not plan:
        return False
    history = getattr(editor, "history", None)
    if ask and history is not None and history.modified and history_module.asks_before_discarding():
        answer = history_module.ask([history.label], tr("Init replaces this part's tone (Undo brings it back)."),
                                    editor)
        if answer == "save":
            if history_module.save_callback is not None:
                history_module.save_callback()
            return False
        if answer != "discard":
            return False
    if history is not None:
        history.begin_group()
    try:
        for pv, value in plan.items():
            if pv.value() != value:
                pv.setValue(value)
        _set_name(editor, INIT_NAME)  # in the same step of Undo
    finally:
        if history is not None:
            history.end_group()
    from jdxi_editor.ui.v2.context import sound_context

    part = getattr(history, "part", "")
    sound_context().part_origin(part, tr("Init"))
    return True


def _set_name(editor, name: str) -> None:
    """The tone name, character by character in its TONE_NAME parameters."""
    text = name.ljust(12)[:12]
    for block in editor.blocks:
        for spec in block.params:
            if spec.name.startswith("TONE_NAME_"):
                index = int(spec.name.rsplit("_", 1)[1]) - 1
                pv = editor.values.get(spec)
                if pv is not None and 0 <= index < 12 and pv.value() != ord(text[index]):
                    pv.setValue(ord(text[index]))
    name_field = getattr(editor, "name_field", None)
    if name_field is not None:
        refresh = getattr(name_field, "text_from_values", None)
        name_field.blockSignals(True)
        name_field.setText(refresh() if callable(refresh) else name)
        name_field.blockSignals(False)


class NewSoundButton(QToolButton):
    """«New sound ▾» in a tone editor's bar: Init, a preset, a recipe."""

    def __init__(self, editor: QWidget):
        super().__init__(editor)
        self.editor = editor
        self.setText(tr("New sound"))
        self.setObjectName("v2EditButton")
        self.setToolTip(tr("Start a new sound for this part: from scratch, from a preset or from a recipe"))
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        init = menu.addAction(tr("From scratch (Init)"))
        init.setToolTip(tr("This part only: a plain sawtooth, filter open, no LFO. Undo brings back the sound before."))
        init.triggered.connect(lambda: init_part(self.editor))
        init.setEnabled(can_init(editor))
        preset = menu.addAction(tr("From a preset…"))
        preset.setToolTip(tr("A factory tone (the preset itself never changes). It is a tone change on the "
                             "JD-Xi, not undoable: take an A/B photo first to come back."))
        preset.triggered.connect(self._presets)
        recipe = menu.addAction(tr("From a recipe…"))
        recipe.setToolTip(tr("A recipe from the library, step by step"))
        recipe.triggered.connect(self._recipes)
        self.setMenu(menu)
        self.menu_actions = {"init": init, "preset": preset, "recipe": recipe}
        model = (getattr(editor, "edit_buttons", None) or [None])[0]
        if model is not None:  # the look of Undo / Redo / Reload beside it
            self.setAutoRaise(model.autoRaise())
            self.setStyleSheet(model.styleSheet() + " QToolButton { padding: 2px 10px; }"
                               " QToolButton::menu-indicator { subcontrol-position: right center; }")
            self.setMinimumHeight(model.sizeHint().height())
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(self.text()) + 40)  # the text and its ▾

    def _instrument(self):
        widget = self.editor
        while widget is not None:
            if hasattr(widget, "show_editor") and hasattr(widget, "editor_registry"):
                return widget
            widget = widget.parentWidget()
        getter = getattr(self.editor, "_get_parent_instrument", None)
        return getter() if callable(getter) else None

    def _presets(self) -> None:
        group = getattr(self.editor, "instrument_preset_group", None)
        if group is not None:
            group.setFocus()
            scroll = group.parentWidget()
            while scroll is not None and not hasattr(scroll, "ensureWidgetVisible"):
                scroll = scroll.parentWidget()
            if scroll is not None:
                scroll.ensureWidgetVisible(group)

    def _recipes(self) -> None:
        instrument = self._instrument()
        if instrument is not None:
            instrument.show_editor("recipes")
