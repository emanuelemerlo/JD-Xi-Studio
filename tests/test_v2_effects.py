"""New Effects editor: every parameter of the manual, right addresses, receiving, types."""

from __future__ import annotations

import json
import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.midi.sysex.parser.utils import parse_sysex
from jdxi_editor.ui.v2 import effects as fx
from jdxi_editor.ui.v2 import widgets as w
from jdxi_editor.ui.v2.framework import SEND_INTERVAL_MS


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class FakeHelper(QObject):
    midi_sysex_json = Signal(str)

    def __init__(self):
        super().__init__()
        self.sent = []

    def send_midi_message(self, message):
        self.sent.append(message.to_message_list())
        return True

    def send_raw_message(self, message):
        return True


@pytest.fixture
def editor(app):
    helper = FakeHelper()
    editor = fx.EffectsEditor(helper, Mock())
    editor.read_block = lambda block: editor.reread.append(block.key)
    editor.reread = []
    editor.helper = helper
    editor.resize(1500, 950)
    editor.show()
    QApplication.processEvents()
    helper.sent.clear()  # the request made when the editor is shown
    yield editor
    editor.close()
    editor.deleteLater()
    QApplication.processEvents()


def wait(ms: int) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)


def dt1(address, data):
    body = list(address) + list(data)
    checksum = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x12] + body + [checksum, 0xF7])


def nibbles(value):
    return [(value >> 12) & 0xF, (value >> 8) & 0xF, (value >> 4) & 0xF, value & 0xF]


# Parameter Guide p. 26-27 and the Version 1.50 supplement: (block, effect type) -> labels
MANUAL = {
    ("EFFECT_1", "Distortion"): {"Type", "Drive", "Presence", "Level"},
    ("EFFECT_1", "Fuzz"): {"Type", "Drive", "Presence", "Level"},
    ("EFFECT_1", "Compressor"): {"Threshold", "Ratio", "Attack", "Release", "Level", "Side Switch",
                                 "Side Level", "Side Note", "Side Time", "Side Release", "Side Sync Sw"},
    ("EFFECT_1", "Bit Crusher"): {"Rate", "Bit", "Filter", "Level"},
    ("EFFECT_2", "Flanger"): {"Rate/Note", "Rate", "Note", "Depth", "Feedback", "Manual", "Balance", "Level"},
    ("EFFECT_2", "Phaser"): {"Rate/Note", "Rate", "Note", "Depth", "Resonance", "Manual", "Level"},
    ("EFFECT_2", "Ring Mod"): {"Frequency", "Sens", "Balance", "Level"},
    ("EFFECT_2", "Slicer"): {"Timing Ptn", "Rate", "Attack", "Trigger Level", "Level"},
}


def test_every_effect_parameter_of_the_manual_is_there(editor):
    for (block, typ), labels in MANUAL.items():
        assert {s.label for s in editor.type_specs(block, typ)} == labels, typ
    names = {s.name for s in editor.values}
    for name in ("EFX1_OUTPUT_ASSIGN", "EFX1_DELAY_SEND_LEVEL", "EFX1_REVERB_SEND_LEVEL", "EFX2_DELAY_SEND_LEVEL",
                 "EFX2_REVERB_SEND_LEVEL", "DELAY_TYPE", "DELAY_TIME_MS", "DELAY_NOTE", "DELAY_TAP_TIME",
                 "DELAY_FEEDBACK", "DELAY_HF_DAMP", "DELAY_EFFECT_LEVEL", "DELAY_REVERB_SEND_LEVEL",
                 "REVERB_TYPE", "REVERB_TIME", "REVERB_HF_DAMP", "REVERB_EFFECT_LEVEL"):
        assert name in names, name


def test_every_parameter_has_a_control_and_an_explanation(editor):
    bound = set()
    for widget in editor.findChildren(QWidget):
        pv = getattr(widget, "pv", None)
        if isinstance(pv, w.ParamValue):
            bound.add(id(pv))
    for spec, pv in editor.values.items():
        assert id(pv) in bound, (spec.group, spec.label)
        assert pv.info.description, spec.label
        assert pv.info.page or pv.info.source or "MIDI" in pv.info.depends, spec.label


def test_only_the_selected_type_is_shown(editor):
    efx1 = editor.pages["EFX1"]
    editor.pv("EFX1_TYPE").setValue(3)
    assert efx1.currentIndex() == 3
    shown = {k.pv.info.label for k in efx1.currentWidget().findChildren(w.Knob)}
    assert "Threshold" in shown and "Drive" not in shown
    editor.pv("EFX2_TYPE").setValue(4)
    assert editor.pages["EFX2"].currentIndex() == 4


def _sent(editor):
    return [bytes(m) for m in editor.helper.sent]


def test_addresses_and_encoding_follow_the_midi_implementation(editor):
    drive = next(s for s in editor.type_specs("EFFECT_1", "Distortion") if s.label == "Drive")
    editor.values[drive].setValue(100)  # EFX1 Parameter 2 at 00 15, 32768 + 100
    wait(SEND_INTERVAL_MS * 2)
    assert _sent(editor)[-1] == dt1([0x18, 0x00, 0x02, 0x15], nibbles(32868))
    editor.pv("EFX2_TYPE").setValue(1)  # Flanger is sent as 5
    wait(SEND_INTERVAL_MS * 2)
    assert _sent(editor)[-1] == dt1([0x18, 0x00, 0x04, 0x00], [5])
    editor.pv("DELAY_TIME_MS").setValue(350)
    wait(SEND_INTERVAL_MS * 2)
    assert _sent(editor)[-1] == dt1([0x18, 0x00, 0x06, 0x0C], nibbles(32768 + 350))
    editor.pv("REVERB_TYPE").setValue(4)  # HALL1
    wait(SEND_INTERVAL_MS * 2)
    assert _sent(editor)[-1] == dt1([0x18, 0x00, 0x08, 0x03], nibbles(32772))
    editor.pv("DELAY_REVERB_SEND_LEVEL").setValue(40)  # one byte
    wait(SEND_INTERVAL_MS * 2)
    assert _sent(editor)[-1] == dt1([0x18, 0x00, 0x06, 0x03], [40])


def test_parameter_offsets_wrap_at_7_bits():
    assert fx._efx(1) == 0x11 and fx._efx(28) == 0x7D
    assert fx._efx(29) == 0x0101 and fx._efx(32) == 0x010D  # 01 0D, as in the MIDI Implementation


def test_dragging_sends_the_last_value_not_every_step(editor):
    level = editor.pv("REVERB_EFFECT_LEVEL")
    for v in range(1, 80):
        level.setValue(v)
    assert len(editor.helper.sent) == 1
    wait(SEND_INTERVAL_MS * 3)
    assert len(editor.helper.sent) == 2
    assert _sent(editor)[-1] == dt1([0x18, 0x00, 0x08, 0x0F], nibbles(32768 + 79))


def test_a_dump_from_the_jdxi_is_shown_and_not_sent_back(editor):
    data = [0] * 0x11
    data[0x00], data[0x02], data[0x04] = 3, 30, 1  # Compressor, delay send 30, to EFX2
    params = [32768] * 32
    params[0], params[1], params[5] = 32768 + 90, 32768 + 9, 32769  # threshold, ratio 10:1, side ON
    for value in params:
        data += nibbles(value)
    parsed = parse_sysex(dt1([0x18, 0x00, 0x02, 0x00], data))
    editor.dispatch_sysex_to_area(json.dumps(parsed))
    assert editor.pv("EFX1_TYPE").value() == 3 and editor.pages["EFX1"].currentIndex() == 3
    comp = {s.label: editor.values[s] for s in editor.type_specs("EFFECT_1", "Compressor")}
    assert comp["Threshold"].value() == 90 and comp["Ratio"].text() == "10:1"
    assert comp["Side Level"].is_enabled()
    assert editor.pv("EFX1_DELAY_SEND_LEVEL").value() == 30
    assert editor.pv("EFX1_OUTPUT_ASSIGN").value() == 1
    assert editor.helper.sent == [] and editor.reread == []


def test_effect2_type_values_are_read_back(editor):
    data = [7, 100, 0, 0] + [0] * 13 + nibbles(32768 + 64) * 32  # Ring Mod
    parsed = parse_sysex(dt1([0x18, 0x00, 0x04, 0x00], data))
    editor.dispatch_sysex_to_area(json.dumps(parsed))
    assert editor.pv("EFX2_TYPE").text() == "Ring Mod"
    assert editor.pv("EFX2_LEVEL").value() == 100


def test_delay_and_reverb_dumps(editor):
    delay = [0, 90, 0, 25] + sum((nibbles(32768 + v) for v in (1, 0, 480, 3, 60, 40, 17, 110)), [])
    delay += nibbles(32768) * 16
    editor.dispatch_sysex_to_area(json.dumps(parse_sysex(dt1([0x18, 0x00, 0x06, 0x00], delay))))
    assert editor.pv("DELAY_TYPE").text() == "PAN"
    assert editor.pv("DELAY_TIME_MS").value() == 480 and editor.pv("DELAY_FEEDBACK").text() == "40 %"
    assert editor.pv("DELAY_HF_DAMP").text() == "BYPASS" and editor.pv("DELAY_EFFECT_LEVEL").value() == 110
    assert editor.pv("DELAY_REVERB_SEND_LEVEL").value() == 25 and editor.pv("DELAY_LEVEL").value() == 90
    reverb = [0, 100, 0] + sum((nibbles(32768 + v) for v in (5, 80, 10, 70)), []) + nibbles(32768) * 20
    editor.dispatch_sysex_to_area(json.dumps(parse_sysex(dt1([0x18, 0x00, 0x08, 0x00], reverb))))
    assert editor.pv("REVERB_TYPE").text() == "HALL2" and editor.pv("REVERB_TIME").value() == 80
    assert editor.pv("REVERB_HF_DAMP").text() == "2000 Hz" and editor.pv("REVERB_EFFECT_LEVEL").value() == 70


def test_controls_without_effect_are_greyed_out(editor):
    flanger = {s.label: editor.values[s] for s in editor.type_specs("EFFECT_2", "Flanger")}
    flanger["Rate/Note"].setValue(1)
    assert not flanger["Rate"].is_enabled() and flanger["Note"].is_enabled()
    editor.pv("DELAY_TIME_NOTE_MODE").setValue(1)
    assert not editor.pv("DELAY_TIME_MS").is_enabled() and editor.pv("DELAY_NOTE").is_enabled()
    editor.pv("DELAY_TYPE").setValue(0)
    assert not editor.pv("DELAY_TAP_TIME").is_enabled()


def test_a_new_type_is_read_back_from_the_jdxi(editor):
    editor.pv("EFX1_TYPE").setValue(1)
    wait(400)
    assert editor.reread == ["EFFECT_1"]


def test_the_information_panel_names_the_effect(editor):
    pv = editor.pv("DELAY_TAP_TIME")
    editor.pv("DELAY_TYPE").setValue(0)
    editor.info_hub.shown.emit(pv)
    panel = editor.info_panel
    assert panel.group.text() == "PROGRAM: DELAY"
    assert panel.source.text() == "Parameter Guide, p. 26"
    assert panel.depends.text().startswith("Inactive now.")
    side = next(s for s in editor.type_specs("EFFECT_1", "Compressor") if s.label == "Side Time")
    editor.info_hub.shown.emit(editor.values[side])
    assert panel.source.text() == "JD-Xi Version 1.50 Supplementary Manual"


def test_the_chain_follows_output_assign(editor):
    editor.pv("EFX1_OUTPUT_ASSIGN").setValue(1)
    image = editor.chain.grab()
    assert not image.isNull()
    names = [b[1] for b in editor.chain.boxes()]
    assert names == ["EFX1", "EFX2", "DELAY", "REVERB", "OUT"]
