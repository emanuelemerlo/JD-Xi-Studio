"""
«New sound» (sound-design spec §6, Phase 5): Init on the part only, one Undo.

- Digital: partial 1 on, 2 and 3 off, sawtooth, filter open, amp sustain max, no LFO
- Analog: sawtooth, filter open, sustain max, LFO at zero
- the other parts and the program are not touched; Undo brings the sound back (HIST-02)
- with changes: asked first; Cancel does nothing
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.v2 import history as history_module
from jdxi_editor.ui.v2 import new_sound as ns


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editors(app):
    from jdxi_editor.ui.v2.analog import AnalogToneEditor
    from jdxi_editor.ui.v2.digital import DigitalToneEditor

    helper = MidiIOHelper()
    made = {"digital": DigitalToneEditor(helper, MagicMock()), "analog": AnalogToneEditor(helper, MagicMock())}
    yield made
    for editor in made.values():
        editor.close()
        editor.deleteLater()


def _v(editor, name, block=None):
    return editor.pv(name, block).value()


def _label(editor, name, block=None):
    spec = editor.spec(name, block)
    return str(spec.choices[_v(editor, name, block) - spec.lo]).upper()


def test_digital_init_and_one_undo(editors):
    d = editors["digital"]
    d.history.reset()
    d.pv("FILTER_CUTOFF", "PARTIAL_1").setValue(30)
    d.pv("PARTIAL2_SWITCH").setValue(1)
    d.pv("LFO_PITCH_DEPTH", "PARTIAL_1").setValue(40)
    before = {pv: pv.value() for pv in d.values.values()}
    assert ns.init_part(d, ask=False)
    assert _v(d, "PARTIAL1_SWITCH") == 1 and _v(d, "PARTIAL2_SWITCH") == 0 and _v(d, "PARTIAL3_SWITCH") == 0
    assert _label(d, "OSC_WAVE", "PARTIAL_1").startswith("SAW")
    assert _label(d, "FILTER_MODE", "PARTIAL_1").startswith("LPF")
    assert _v(d, "FILTER_CUTOFF", "PARTIAL_1") == 127 and _v(d, "AMP_ENV_SUSTAIN_LEVEL", "PARTIAL_1") == 127
    assert _v(d, "AMP_ENV_ATTACK_TIME", "PARTIAL_1") == 0 and _v(d, "LFO_PITCH_DEPTH", "PARTIAL_1") == 0
    assert d.name_field.text().strip() == "Init Tone"
    d.history._sealed = True
    assert d.history.undo()  # one step back: the whole Init, name included
    assert {pv: pv.value() for pv in d.values.values()} == before


def test_analog_init_only_its_own_tone(editors):
    a, d = editors["analog"], editors["digital"]
    digital_before = {pv: pv.value() for pv in d.values.values()}
    a.history.reset()
    a.pv("FILTER_CUTOFF").setValue(20)
    a.pv("LFO_FILTER_DEPTH").setValue(30)
    assert ns.init_part(a, ask=False)
    assert _label(a, "OSC_WAVEFORM").startswith("SAW") and _v(a, "FILTER_CUTOFF") == 127
    assert _v(a, "LFO_FILTER_DEPTH") == 0 and _v(a, "AMP_ENV_SUSTAIN_LEVEL") == 127
    assert all(pv.value() == value for pv, value in digital_before.items())  # the other part untouched
    assert a.history.undo() and _v(a, "FILTER_CUTOFF") == 20 and _v(a, "LFO_FILTER_DEPTH") == 30


def test_init_is_one_undo_step(editors):
    a = editors["analog"]
    a.history.reset()
    a.pv("FILTER_CUTOFF").setValue(20)
    a.history._sealed = True  # the edit above is its own step
    ns.init_part(a, ask=False)
    assert a.history.undo()  # one step: the whole Init
    assert _v(a, "FILTER_CUTOFF") == 20
    assert a.history.undo()  # the edit before
    assert not a.history.can_undo()


def test_with_changes_it_asks_and_cancel_does_nothing(editors, monkeypatch):
    a = editors["analog"]
    a.history.reset()
    a.pv("FILTER_CUTOFF").setValue(20)
    asked = []
    monkeypatch.setattr(history_module, "ask", lambda labels, action, parent=None: asked.append(labels) or "cancel")
    monkeypatch.setattr(history_module, "asks_before_discarding", lambda settings=None: True)
    assert not ns.init_part(a)
    assert asked and _v(a, "FILTER_CUTOFF") == 20
    monkeypatch.setattr(history_module, "ask", lambda labels, action, parent=None: "discard")
    assert ns.init_part(a) and _v(a, "FILTER_CUTOFF") == 127


def test_the_editors_have_the_new_sound_menu(editors):
    d = editors["digital"]
    button = d.new_sound_button
    assert set(button.menu_actions) == {"init", "preset", "recipe"}
    assert button.menu_actions["init"].isEnabled()
    assert "A/B" in button.menu_actions["preset"].toolTip()
