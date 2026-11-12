"""New Digital Synth editor: every parameter, addresses for Digital 1 and 2, receiving, views."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.v2 import digital as dg
from jdxi_editor.ui.v2 import widgets as w
from jdxi_editor.ui.v2.framework import SEND_INTERVAL_MS


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Sysex:
    type = "sysex"

    def __init__(self, data):
        self.data = data


def make(app, cls):
    helper = MidiIOHelper()
    editor = cls(helper, Mock())
    sent = []
    helper.send_midi_message = lambda message: sent.append(bytes(message.to_message_list())) or True
    editor.sent = sent
    editor.helper = helper
    editor.resize(1600, 1000)
    editor.show()
    QApplication.processEvents()
    return editor


@pytest.fixture
def editor(app):
    editor = make(app, dg.DigitalToneEditor)
    yield editor
    editor.close()
    editor.deleteLater()
    QApplication.processEvents()


def wait(ms: int) -> None:
    # At least half a second: slow CI machines (macOS runners) fire the send
    # timer late; waiting longer changes nothing, nothing else is pending
    deadline = time.monotonic() + max(ms, 500) / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)


def dt1(address, data):
    body = list(address) + list(data)
    checksum = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x12] + body + [checksum, 0xF7])


# MIDI Implementation, SuperNATURAL Synth Tone Common / Modify / Partial (reserves left out)
COMMON = list(range(0x0D)) + [0x12, 0x13, 0x14, 0x15, 0x16, 0x17] + list(range(0x19, 0x20)) + [0x2E, 0x31, 0x32, 0x34, 0x35, 0x36, 0x3C]
MODIFY = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]
PARTIAL = [0x00, 0x01] + list(range(0x03, 0x2B)) + list(range(0x2C, 0x32)) + [0x34, 0x35, 0x39, 0x3A, 0x3B, 0x3C]


def test_every_parameter_of_the_midi_implementation_is_there(editor):
    blocks = {b.key: b for b in editor.blocks}
    assert sorted(s.offset for s in blocks["COMMON"].params) == COMMON
    assert sorted(s.offset for s in blocks["MODIFY"].params) == MODIFY
    for n in (1, 2, 3):
        assert sorted(s.offset for s in blocks[f"PARTIAL_{n}"].params) == PARTIAL


def test_every_parameter_has_a_control_and_an_explanation(editor):
    bound = set()
    for widget in editor.findChildren(QWidget):
        for name in ("pv", "a", "d", "s", "r", "depth", "cutoff", "resonance", "mode", "slope", "shape", "rate", "fade", "sync", "note"):
            value = getattr(widget, name, None)
            if isinstance(value, w.ParamValue):
                bound.add(id(value))
        for pv in getattr(widget, "pvs", []):
            bound.add(id(pv))
    for spec, pv in editor.values.items():
        assert id(pv) in bound, (spec.group, spec.label)
        assert pv.info.description, spec.label
        assert pv.info.page, spec.label


def _last(editor):
    wait(SEND_INTERVAL_MS * 2)
    return editor.sent[-1]


def test_addresses_and_encoding(editor):
    editor.partial("FILTER_CUTOFF", 1).setValue(90)  # partial 2 at 19 01 21 0C
    assert _last(editor) == dt1([0x19, 0x01, 0x21, 0x0C], [90])
    editor.partial("FILTER_CUTOFF_KEYFOLLOW", 0).setValue(50)  # +50 = 69 (54-74)
    assert _last(editor) == dt1([0x19, 0x01, 0x20, 0x0D], [69])
    editor.partial("WAVE_NUMBER", 2).setValue(137)  # 4 nibbles, as is
    assert _last(editor) == dt1([0x19, 0x01, 0x22, 0x35], [0x00, 0x00, 0x08, 0x09])
    editor.partial("AMP_PAN", 0).setValue(-30)
    assert _last(editor) == dt1([0x19, 0x01, 0x20, 0x1B], [34])
    editor.pv("RING_SWITCH").setValue(1)  # ON is sent as 2 (OFF, ---, ON)
    assert _last(editor) == dt1([0x19, 0x01, 0x00, 0x1F], [2])
    editor.pv("ENVELOPE_LOOP_MODE").setValue(2)
    assert _last(editor) == dt1([0x19, 0x01, 0x50, 0x04], [2])
    editor.pv("OCTAVE_SHIFT").setValue(-2)
    assert _last(editor) == dt1([0x19, 0x01, 0x00, 0x15], [62])


def test_digital_2_uses_its_own_area(app):
    editor = make(app, dg.Digital2ToneEditor)
    try:
        assert editor.synth_number == 2
        editor.partial("OSC_PITCH", 0).setValue(7)
        assert _last(editor) == dt1([0x19, 0x21, 0x20, 0x03], [71])
        assert editor.instrument_preset_group.title() == "Digital Synth"
    finally:
        editor.close()
        editor.deleteLater()


def test_a_partial_dump_is_shown_and_not_sent_back(editor):
    data = [0] * 0x3D
    data[0x00], data[0x03], data[0x0A], data[0x0C], data[0x0D] = 6, 76, 1, 100, 74  # SP-SAW, +12, LPF1, KF +100
    data[0x1B], data[0x1C], data[0x3A] = 94, 4, 80  # pan 30R, S&H, S-Saw detune
    data[0x35:0x39] = [0x00, 0x00, 0x00, 0x05]  # Wave Number 5
    editor.helper.midi_message_incoming.emit(_Sysex(dt1([0x19, 0x01, 0x21, 0x00], data)[1:-1]))
    v = lambda name: editor.partial(name, 1)  # noqa: E731
    assert v("OSC_WAVE").text() == "SP-SAW" and v("OSC_PITCH").value() == 12
    assert v("FILTER_MODE").text() == "LPF1" and v("FILTER_CUTOFF").value() == 100
    assert v("FILTER_CUTOFF_KEYFOLLOW").value() == 100 and v("AMP_PAN").text() == "30R"
    assert v("LFO_SHAPE").text() == "S&H" and v("SUPER_SAW_DETUNE").value() == 80
    assert v("WAVE_NUMBER").value() == 5
    assert v("SUPER_SAW_DETUNE").is_enabled() and not v("OSC_PULSE_WIDTH").is_enabled()
    assert editor.partial("OSC_WAVE", 0).value() == 0  # partial 1 untouched
    assert editor.sent == []


def test_the_common_dump_and_the_name(editor):
    data = [ord(c) for c in "JP8 Strings "] + [110, 0, 0, 0, 0, 0, 1, 20, 1, 65, 12, 12, 0, 1, 1, 0, 0, 0, 0, 2]
    editor.receive_dt1(dt1([0x19, 0x01, 0x00, 0x00], data))
    assert editor.name_field.text() == "JP8 Strings"
    assert editor.pv("TONE_LEVEL").value() == 110 and editor.pv("OCTAVE_SHIFT").value() == 1
    assert editor.pv("MONO_SWITCH").text() == "MONO" and editor.pv("LEGATO_SWITCH").is_enabled()
    assert editor.pv("RING_SWITCH").text() == "ON"
    assert editor.pv("PARTIAL1_SWITCH").text() == "ON" and editor.pv("PARTIAL2_SWITCH").text() == "OFF"
    assert editor.sent == []
    editor.name_field.setText("Saw Lead")
    editor.name_field.editingFinished.emit()
    assert editor.sent == [dt1([0x19, 0x01, 0x00, 0x00], [ord(c) for c in "Saw Lead".ljust(12)])]


def test_controls_without_effect_are_greyed_out(editor):
    v = lambda name: editor.partial(name, 0)  # noqa: E731
    v("OSC_WAVE").setValue(2)  # PW-SQR
    assert v("OSC_PULSE_WIDTH").is_enabled() and not v("WAVE_NUMBER").is_enabled()
    assert not editor.pv("WAVE_SHAPE").is_enabled()
    editor.pv("RING_SWITCH").setValue(1)  # partials 1 and 2 lose PW
    assert not v("OSC_PULSE_WIDTH").is_enabled()
    v3 = editor.partial("OSC_WAVE", 2)
    v3.setValue(2)
    assert editor.partial("OSC_PULSE_WIDTH", 2).is_enabled()  # partial 3 keeps it
    v("OSC_WAVE").setValue(7)  # PCM
    assert v("WAVE_NUMBER").is_enabled() and v("WAVE_GAIN").is_enabled() and not v("OSC_WAVE_VARIATION").is_enabled()
    v("FILTER_MODE").setValue(0)
    assert not v("FILTER_CUTOFF").is_enabled()
    v("LFO_TEMPO_SYNC_SWITCH").setValue(1)
    assert not v("LFO_RATE").is_enabled() and v("LFO_TEMPO_SYNC_NOTE").is_enabled()
    editor.pv("UNISON_SWITCH").setValue(0)
    assert not editor.pv("UNISON_SIZE").is_enabled()


def test_one_partial_at_a_time(editor):
    assert editor.partial_pages.currentIndex() == 0
    editor.partial_buttons.button(2).click()
    assert editor.partial_pages.currentIndex() == 2
    page = editor.partial_pages.currentWidget()
    knobs = {k.pv for k in page.findChildren(w.Knob)}
    assert editor.partial("FILTER_CUTOFF", 2) in knobs and editor.partial("FILTER_CUTOFF", 0) not in knobs


def test_filter_view_draws_every_type(editor):
    view = editor.findChildren(dg.DigitalFilterView)[0]
    for mode in range(8):
        for slope in (0, 1):
            view.mode.setValue(mode)
            view.slope.setValue(slope)
            assert not view.grab().isNull()
    view.mode.setValue(2)  # HPF: low frequencies cut
    assert view._response_db(30) < view._response_db(15000)
    view.mode.setValue(1)  # LPF: high frequencies cut
    assert view._response_db(30) > view._response_db(15000)


def test_the_category_card_follows_the_list(editor, app):
    """Choosing a category selects one of its presets: the card shows that category."""
    combo = editor.instrument_preset.instrument_selection_combo
    shown = []
    original = editor.update_instrument_image
    editor.update_instrument_image = lambda: (shown.append(editor._selected_category()), original())
    try:
        index = combo.category_combo.findText("Bass")
        assert index > 0
        combo.category_combo.setCurrentIndex(index)
        for _ in range(5):
            app.processEvents()
        assert shown and shown[-1] == "Bass"
    finally:
        editor.update_instrument_image = original
        combo.category_combo.setCurrentIndex(0)
