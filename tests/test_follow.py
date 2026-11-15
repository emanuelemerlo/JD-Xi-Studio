"""The instrument window follows the JD-Xi: tone names, octave, sliders, keys, start-up reading."""

from __future__ import annotations

from unittest.mock import Mock

import mido
import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.ui.windows.jdxi import follow
from jdxi_editor.ui.windows.jdxi.follow import PART_REQUESTS, parse_dt1


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    w = JDXiInstrument()
    w.show()
    for _ in range(10):
        app.processEvents()
    yield w
    w.close()


@pytest.fixture
def sent(window, monkeypatch):
    requests = []
    monkeypatch.setattr(follow, "send_with_delay", lambda helper, reqs: requests.append(reqs))
    monkeypatch.setattr(window.midi_helper, "midi_out", object(), raising=False)
    window.follower._last_input = 0.0
    return requests


def settle():
    for _ in range(5):
        QApplication.processEvents()


def dt1(address, values):
    checksum = (128 - sum(address + values) % 128) % 128
    return mido.Message("sysex", data=[0x41, 0x10, 0, 0, 0, 0x0E, 0x12] + address + values + [checksum])


def receive(window, message):
    window.midi_helper._handle_midi_message(message)
    settle()


def analog_tone(name=b"Toxic Bass 3", octave=64, cutoff=0, resonance=0):
    values = list(name.ljust(12)) + [0] * (0x40 - 12)
    values[0x34] = octave
    values[0x21] = cutoff
    values[0x23] = resonance
    return values


def test_parse_dt1():
    message = dt1([0x19, 0x42, 0x00, 0x10], [1, 2, 3])
    assert parse_dt1(message.data) == ((0x19, 0x42, 0x00, 0x10), [1, 2, 3])
    assert parse_dt1([0x41, 0x10, 0, 0, 0, 0x0E, 0x11, 0x19, 0x42, 0, 0, 0, 0, 0, 0x40, 0x27]) is None


def test_tone_chosen_on_the_jdxi_shows_on_the_display(window):
    window._select_synth(JDXiSynth.ANALOG_SYNTH)
    receive(window, dt1([0x19, 0x42, 0x00, 0x00], analog_tone(b"Toxic Bass 3")))
    assert window.preset_manager.current_preset_names[JDXiSynth.ANALOG_SYNTH] == "Toxic Bass 3"
    assert window.preset_manager.current_preset_name == "Toxic Bass 3"


def test_octave_and_sliders_follow_the_part_shown(window):
    window._select_synth(JDXiSynth.ANALOG_SYNTH)
    receive(window, dt1([0x19, 0x42, 0x00, 0x00], analog_tone(octave=66, cutoff=100, resonance=30)))
    assert window.current_octave == 2
    assert window.octave_up.isChecked() and not window.octave_down.isChecked()
    assert window.panel_sliders["cutoff"].value() == 100
    assert window.panel_sliders["resonance"].value() == 30
    # an octave changed with the JD-Xi's buttons (in the program zone)
    zone = [64] * 0x23
    receive(window, dt1([0x18, 0x00, 0x32, 0x00], zone))
    zone[0x19] = 63
    receive(window, dt1([0x18, 0x00, 0x32, 0x00], zone))
    assert window.current_octave == -1
    assert window.octave_down.isChecked()


def test_another_parts_values_leave_the_sliders(window):
    window._select_synth(JDXiSynth.ANALOG_SYNTH)
    receive(window, dt1([0x19, 0x42, 0x00, 0x00], analog_tone(cutoff=90)))
    partial = [0] * 0x40
    partial[0x0C] = 10
    receive(window, dt1([0x19, 0x01, 0x20, 0x00], partial))  # Digital 1, not shown
    assert window.panel_sliders["cutoff"].value() == 90
    window._select_synth(JDXiSynth.DIGITAL_SYNTH_1)
    receive(window, dt1([0x19, 0x01, 0x20, 0x00], partial))
    assert window.panel_sliders["cutoff"].value() == 10


def test_slider_values_from_the_jdxi_are_not_sent_back(window, monkeypatch):
    calls = Mock()
    monkeypatch.setattr(window.midi_helper, "send_control_change", calls)
    window._select_synth(JDXiSynth.ANALOG_SYNTH)
    receive(window, dt1([0x19, 0x42, 0x00, 0x00], analog_tone(cutoff=77)))
    assert window.panel_sliders["cutoff"].value() == 77
    calls.assert_not_called()


def test_notes_played_on_the_jdxi_light_the_keys(window):
    key = window.piano_keyboard._keys_by_note[60]
    receive(window, mido.Message("note_on", note=60, velocity=90, channel=2))
    assert key.is_pressed
    receive(window, mido.Message("note_on", note=60, velocity=0, channel=2))
    assert not key.is_pressed
    receive(window, mido.Message("note_on", note=60, velocity=90, channel=0))
    receive(window, mido.Message("note_off", note=60, channel=0))
    assert not key.is_pressed


def test_poll_reads_the_part_shown(window, sent):
    window._select_synth(JDXiSynth.ANALOG_SYNTH)
    sent.clear()
    window.follower._last_input = 0.0
    window.follower.poll()
    assert sent == [PART_REQUESTS[JDXiSynth.ANALOG_SYNTH]]


def test_no_poll_just_after_input_or_while_playing(window, sent, monkeypatch):
    window._select_synth(JDXiSynth.DIGITAL_SYNTH_1)
    sent.clear()
    window.follower.on_outgoing([0xB0, 74, 10])  # a value sent from the app
    window.follower.poll()
    assert sent == []
    window.follower._last_input = 0.0
    window.follower.on_outgoing(bytes.fromhex(PART_REQUESTS[JDXiSynth.ANALOG_SYNTH][0].replace(" ", "")))
    window.follower.poll()
    assert sent == [PART_REQUESTS[JDXiSynth.DIGITAL_SYNTH_1]]  # requests do not count as input
    sent.clear()
    playing = Mock(is_playing=True)
    monkeypatch.setattr(follow, "playback_activity", lambda: playing)
    window.follower._last_input = 0.0
    window.follower.poll()
    assert sent == []


def test_no_poll_without_midi_out(window, sent, monkeypatch):
    monkeypatch.setattr(window.midi_helper, "midi_out", None, raising=False)
    window.follower.poll()
    window.follower.read_all()
    assert sent == []


def test_tone_program_change_reads_the_part_not_the_program(window, sent):
    before = getattr(window, "current_program_number", None)
    receive(window, mido.Message("program_change", program=4, channel=2))  # Analog channel
    assert PART_REQUESTS[JDXiSynth.ANALOG_SYNTH] in sent
    assert getattr(window, "current_program_number", None) == before


def test_program_change_on_the_program_channel(window, sent, monkeypatch):
    requested = Mock()
    monkeypatch.setattr(window, "data_request", requested)
    window.set_current_program_number(16, 4)
    assert window.current_program_number == 5
    requested.assert_called_once()


def test_octave_buttons_write_the_part_shown(window, monkeypatch):
    messages = []
    monkeypatch.setattr(window.midi_helper, "send_midi_message", lambda m: messages.append(m) or True)
    window._select_synth(JDXiSynth.ANALOG_SYNTH)
    window.current_octave = 0
    window._midi_send_octave(+1)
    raw = [int(b) for b in messages[-1].to_message_list()]
    at = raw.index(0x12) + 1  # after DT1: address, value
    assert raw[at : at + 5] == [0x19, 0x42, 0x00, 0x34, 0x41]


def test_preset_arrows_load_the_tone(window, monkeypatch):
    """‹ › in a tone editor's preset panel load the tone, as the JD-Xi's buttons do."""
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.preset import widget
    from jdxi_editor.ui.v2.analog import AnalogToneEditor

    helper = MidiIOHelper()
    raw = []
    monkeypatch.setattr(helper, "send_raw_message", lambda m: raw.append(list(m)) or True)  # a shared helper
    editor = AnalogToneEditor(helper, Mock())
    panel = editor.instrument_preset
    panel.instrument_selection_combo.combo_box.setCurrentIndex(0)
    panel._on_next_preset()
    panel._on_next_preset()  # two clicks: one tone sent, the one stopped on
    assert [m for m in raw if m[0] != 0xF0] == []  # nothing loaded yet
    panel._step_load_timer.setInterval(0)
    panel._step_load_timer.start()
    for _ in range(20):
        QApplication.processEvents()
    channel_messages = [m for m in raw if m[0] != 0xF0]
    assert channel_messages == [[0xB2, 0, 94], [0xB2, 32, 64], [0xC2, 2]]
    editor.close()
    editor.deleteLater()
    assert widget.STEP_LOAD_DELAY_MS > 0


@pytest.fixture
def program_channel_reset():
    from jdxi_editor.midi.io import program_channel

    program_channel.reset()
    yield program_channel
    program_channel.reset()


def test_programs_go_to_the_jdxis_program_channel(window, program_channel_reset, monkeypatch):
    """SYSTEM › Program Ctrl Ch read at start: programs sent where the JD-Xi listens."""
    raw = []
    monkeypatch.setattr(window.midi_helper, "send_raw_message", lambda m: raw.append(list(m)) or True)
    system = [0] * 0x2B
    system[0x11], system[0x29], system[0x2A] = 2, 1, 1  # Program Ctrl Ch 3
    receive(window, dt1([0x02, 0x00, 0x00, 0x00], system))
    assert program_channel_reset.channel() == 2
    window.midi_helper.send_bank_select_and_program_change(15, 85, 64, 1)
    assert [m for m in raw if m[0] != 0xF0] == [[0xB2, 0, 85], [0xB2, 32, 64], [0xC2, 1]]
    raw.clear()
    window.midi_helper.send_bank_select_and_program_change(0, 95, 64, 1)  # a tone: unchanged
    assert [m for m in raw if m[0] != 0xF0][-1] == [0xC0, 1]


def test_program_changes_off_on_the_jdxi_are_reported(window, program_channel_reset):
    system = [0] * 0x2B
    system[0x11], system[0x29], system[0x2A] = 16, 0, 1  # OFF, Rx Program Change OFF
    receive(window, dt1([0x02, 0x00, 0x00, 0x00], system))
    assert "Program Ctrl Ch: OFF" in program_channel_reset.problem()
    assert "Rx Program Change: OFF" in program_channel_reset.problem()
    assert "MENU" in window.statusBar().currentMessage()
    assert program_channel_reset.channel() == 15  # still sent on 16


def test_tone_arrows_of_the_window_load_the_tone_shown(window, monkeypatch):
    raw = []
    monkeypatch.setattr(window.midi_helper, "send_raw_message", lambda m: raw.append(list(m)) or True)
    window._select_synth(JDXiSynth.DIGITAL_SYNTH_1)
    window.current_preset_index = 0
    window._preset_next()  # 002
    assert [m for m in raw if m[0] != 0xF0][-1] == [0xC0, 1]


def test_a_one_parameter_dt1_sets_that_parameter_only():
    """A DT1 for one parameter (the JD-Xi sends them) used to be read as a whole block: all 0."""
    from jdxi_editor.midi.sysex.parser.utils import parse_sysex

    address, values = [0x19, 0x42, 0x00, 0x21], [110]
    checksum = (128 - sum(address + values) % 128) % 128
    parsed = parse_sysex(bytes([0xF0, 0x41, 0x10, 0, 0, 0, 0x0E, 0x12, *address, *values, checksum, 0xF7]))
    assert parsed["FILTER_CUTOFF"] == 110
    assert "FILTER_RESONANCE" not in parsed and "LFO_RATE" not in parsed
