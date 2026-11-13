"""
The editor starts without a MIDI backend, and without a JD-Xi it opens the MIDI
configuration without blocking.
"""

import sys

import pytest
import rtmidi
from PySide6.QtWidgets import QApplication, QMessageBox

from jdxi_editor.midi.io.null_port import NullMidiPort, open_rtmidi_port

_APP = QApplication.instance() or QApplication(sys.argv)


class _NoMidiApi:
    """An rtmidi port class on a system with no MIDI API."""

    def __init__(self, *_args, **_kwargs):
        raise SystemError("MidiInAlsa::initialize: error creating ALSA sequencer client object.")


@pytest.fixture
def fresh_helper_singleton():
    """Give the test its own MidiIOHelper; the shared one is restored afterwards."""
    from jdxi_editor.midi.io.helper import MidiIOHelper

    shared = MidiIOHelper._instance
    MidiIOHelper._instance = None
    yield MidiIOHelper
    MidiIOHelper._instance = shared


def test_open_rtmidi_port_falls_back_to_a_null_port():
    port, error = open_rtmidi_port(_NoMidiApi)
    assert isinstance(port, NullMidiPort)
    assert "ALSA sequencer" in error
    assert port.get_ports() == [] and not port.is_port_open()
    port.send_message([0xF0, 0x41, 0xF7])  # dropped, no error
    with pytest.raises(rtmidi.InvalidPortError):
        port.open_port(0)


def test_open_rtmidi_port_uses_the_real_class_when_it_works():
    try:
        rtmidi.MidiOut().delete()
    except Exception as ex:  # no ALSA sequencer (CI runners, containers): nothing real to open
        pytest.skip(f"no MIDI backend here: {ex}")
    port, error = open_rtmidi_port(rtmidi.MidiOut)
    assert error is None
    assert not isinstance(port, NullMidiPort)


def test_helper_runs_offline_without_a_midi_api(monkeypatch, fresh_helper_singleton):
    monkeypatch.setattr(rtmidi, "MidiIn", _NoMidiApi)
    monkeypatch.setattr(rtmidi, "MidiOut", _NoMidiApi)
    helper = fresh_helper_singleton()
    assert not helper.midi_available
    assert "ALSA" in helper.midi_backend_error
    assert helper.get_input_ports() == [] and helper.get_output_ports() == []
    assert not helper.is_input_open and not helper.is_output_open
    helper.auto_connect_jdxi()  # nothing to connect to, no error


def _visible(kind):
    return [w for w in QApplication.topLevelWidgets() if isinstance(w, kind) and w.isVisible()]


def _build_window(fresh_helper_singleton):
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    window = JDXiInstrument()  # must return: nothing in the constructor waits for a click
    window.show()
    for _ in range(20):
        _APP.processEvents()
    return window


def test_window_starts_offline_and_says_so(monkeypatch, fresh_helper_singleton):
    monkeypatch.setattr(rtmidi, "MidiIn", _NoMidiApi)
    monkeypatch.setattr(rtmidi, "MidiOut", _NoMidiApi)
    window = _build_window(fresh_helper_singleton)
    try:
        assert not window.midi_helper.midi_available
        assert "Offline" in window.statusBar().currentMessage()
        boxes = _visible(QMessageBox)
        # macOS shows no title on message boxes (Qt leaves it empty there): check the text
        assert len(boxes) == 1 and "MIDI" in boxes[0].text()
    finally:
        for box in _visible(QMessageBox):
            box.close()
        window.close()


def test_without_a_jdxi_the_midi_configuration_opens_without_blocking(
    monkeypatch, fresh_helper_singleton
):
    from jdxi_editor.ui.windows.midi.config_dialog import MIDIConfigDialog

    if not hasattr(rtmidi.MidiIn, "ports"):
        pytest.skip("needs the fake MIDI ports from conftest (not with real MIDI)")
    monkeypatch.setattr(rtmidi.MidiIn, "ports", ["Some Other Synth"])
    monkeypatch.setattr(rtmidi.MidiOut, "ports", ["Some Other Synth"])
    window = _build_window(fresh_helper_singleton)
    try:
        dialogs = _visible(MIDIConfigDialog)
        assert len(dialogs) == 1
        # Asking again brings the same dialog forward instead of opening another
        window._show_midi_config()
        _APP.processEvents()
        assert _visible(MIDIConfigDialog) == dialogs
        dialogs[0].reject()
        for _ in range(5):
            _APP.processEvents()
        assert _visible(MIDIConfigDialog) == []
        assert window._midi_config_dialog is None
    finally:
        window.close()
