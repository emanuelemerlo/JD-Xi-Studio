"""MIDI connection dialog: opens at once, slow work in the background, connection test."""

from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from jdxi_editor.ui.windows.midi import config_dialog as cd

JDXI_REPLY = (0x7E, 0x10, 0x06, 0x02, 0x41, 0x0E, 0x03, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def delete_dialogs():
    """Like the app (WA_DeleteOnClose): each dialog is deleted when done."""
    yield
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, cd.MIDIConfigDialog):
            widget.deleteLater()
    QApplication.processEvents()


class _Sysex:
    type = "sysex"

    def __init__(self, data):
        self.data = data


class FakeHelper(QObject):
    midi_message_incoming = Signal(object)

    def __init__(self, inputs, outputs, reply=JDXI_REPLY, open_ports=True):
        super().__init__()
        self.inputs, self.outputs, self.reply = inputs, outputs, reply
        self.current_in = inputs[0] if open_ports and inputs else None
        self.current_out = outputs[0] if open_ports and outputs else None
        self.is_input_open = self.is_output_open = open_ports
        self.sent, self.reconnected = [], []
        self.soundfont_synth = None

    def get_input_ports(self):
        return list(self.inputs)

    def get_output_ports(self):
        return list(self.outputs)

    def reconnect_port_names(self, in_port, out_port):
        self.reconnected.append((in_port, out_port))
        self.current_in, self.current_out = in_port, out_port
        self.is_input_open = self.is_output_open = True
        return True

    def send_raw_message(self, message):
        self.sent.append(list(message))
        if self.reply is not None:  # the instrument answers a little later
            QTimer.singleShot(20, self, lambda: self.midi_message_incoming.emit(_Sysex(self.reply)))
        return True


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def test_opens_at_once_while_slow_port_listing_runs_in_background(app, monkeypatch):
    def slow_listing(helper):
        time.sleep(0.8)  # like a busy MIDI driver
        return (["Focusrite USB MIDI", "JD-Xi"], ["Microsoft GS Wavetable Synth", "JD-Xi"])

    monkeypatch.setattr(cd, "list_midi_ports", slow_listing)
    helper = FakeHelper([], [], open_ports=False)
    started = time.monotonic()
    dialog = cd.MIDIConfigDialog(helper)
    dialog.show()
    QApplication.processEvents()
    assert time.monotonic() - started < 0.5
    assert wait_until(lambda: dialog.input_combo.count() == 2)
    # the JD-Xi comes first, marked, and is chosen
    assert dialog.input_combo.itemText(0) == "★ JD-Xi"
    assert dialog.get_input_port() == "JD-Xi" and dialog.get_output_port() == "JD-Xi"
    assert dialog.find_button.isEnabled() and not dialog.help_label.isVisibleTo(dialog)
    dialog.reject()


def test_fluidsynth_and_audio_devices_wait_until_asked(app, monkeypatch):
    calls = []
    monkeypatch.setattr(cd, "list_audio_outputs", lambda: calls.append("audio") or [])
    monkeypatch.setattr(cd, "find_soundfonts", lambda *a: calls.append("sf2") or [])
    helper = FakeHelper(["JD-Xi"], ["JD-Xi"])
    dialog = cd.MIDIConfigDialog(helper)
    QApplication.processEvents()
    assert not dialog.synth_box.isChecked() and not dialog.synth_panel.isVisibleTo(dialog)
    assert calls == [] and helper.soundfont_synth is None  # nothing started on open
    dialog.synth_box.setChecked(True)
    assert wait_until(lambda: sorted(calls) == ["audio", "sf2"])
    assert not dialog.fs_start_btn.isEnabled()  # no SoundFont chosen
    dialog.reject()


def test_connection_test_reports_the_jdxi(app):
    helper = FakeHelper(["JD-Xi"], ["JD-Xi"])
    dialog = cd.MIDIConfigDialog(helper)  # open ports: tests by itself
    assert wait_until(lambda: dialog.status_kind == "ok")
    assert helper.sent == [cd.IDENTITY_REQUEST]
    assert dialog.test_button.isEnabled()
    dialog.reject()


def test_no_reply_ends_with_advice_not_a_wait(app, monkeypatch):
    monkeypatch.setattr(cd, "IDENTITY_TIMEOUT_MS", 100)
    helper = FakeHelper(["Focusrite USB MIDI"], ["Microsoft GS Wavetable Synth"], reply=None)
    dialog = cd.MIDIConfigDialog(helper)
    QApplication.processEvents()
    assert dialog.help_label.isVisibleTo(dialog)  # no JD-Xi among the ports
    started = time.monotonic()
    dialog.test_connection()
    assert time.monotonic() - started < 0.1  # returns at once
    assert dialog.status_kind == "busy" and not dialog.test_button.isEnabled()
    assert wait_until(lambda: dialog.status_kind == "error")
    assert "Microsoft GS Wavetable Synth" in dialog.status_label.text()
    assert dialog.test_button.isEnabled()
    dialog.reject()


def test_another_instrument_is_not_taken_for_the_jdxi(app):
    other = (0x7E, 0x10, 0x06, 0x02, 0x43, 0x00, 0x41, 0x00, 0x00)  # Yamaha
    helper = FakeHelper(["Synth"], ["Synth"], reply=other)
    dialog = cd.MIDIConfigDialog(helper)
    assert wait_until(lambda: "43h" in dialog.status_label.text())
    assert dialog.status_kind == "error"
    dialog.reject()


def test_ok_reconnects_only_changed_ports_after_closing(app, monkeypatch):
    monkeypatch.setattr(
        cd, "list_midi_ports", lambda h: (["Focusrite USB MIDI", "JD-Xi"], ["JD-Xi", "Other"])
    )
    helper = FakeHelper(["Focusrite USB MIDI"], ["Other"], reply=None)
    dialog = cd.MIDIConfigDialog(helper)
    assert wait_until(lambda: dialog.input_combo.count() == 2)
    dialog.input_combo.setCurrentIndex(dialog.input_combo.findData("Focusrite USB MIDI"))
    dialog.output_combo.setCurrentIndex(dialog.output_combo.findData("Other"))
    dialog.accept()
    assert helper.reconnected == []  # unchanged: nothing reopened

    dialog = cd.MIDIConfigDialog(helper)
    assert wait_until(lambda: dialog.input_combo.count() == 2)
    dialog.select_jdxi_ports()
    dialog.accept()
    assert helper.reconnected == [("JD-Xi", "JD-Xi")]
    assert not dialog.isVisible()


def test_identity_reply_parsing():
    reply = cd.parse_identity_reply(JDXI_REPLY)
    assert reply["is_jdxi"] and reply["manufacturer"] == 0x41
    assert cd.parse_identity_reply((0x41, 0x10, 0x00)) is None  # a DT1, not a reply
