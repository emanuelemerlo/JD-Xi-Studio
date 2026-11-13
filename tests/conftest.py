import pytest
"""
Shared test setup: the tests run on in-memory MIDI ports instead of rtmidi's.

Many tests build the editor's MidiIOHelper, which opens rtmidi.MidiIn and
rtmidi.MidiOut. On machines without a MIDI API (Linux CI runners and
containers have no ALSA sequencer) that fails, and on machines with one the
result depends on what is plugged in. Without a JD-Xi port the main window also
opens the MIDI configuration dialog. So by default rtmidi's port classes are
replaced, before any test module is imported, with fakes that list one port
named "JD-Xi" (the editor auto-connects to it) and record what is sent.

To use the real MIDI ports and a connected JD-Xi, run the hardware tests:

    pytest -m hardware

or set JDXI_TEST_REAL_MIDI=1.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

# The tests check English texts: run in English whatever the machine's
# language or Preferences (tests of the translations set it themselves)
os.environ.setdefault("JDXI_LANGUAGE", "en")

import rtmidi

FAKE_JDXI_PORT = "JD-Xi (test)"


class FakeMidiPort:
    """In-memory stand-in for rtmidi.MidiIn / rtmidi.MidiOut."""

    ports = [FAKE_JDXI_PORT]

    def __init__(self, *_args, **_kwargs) -> None:
        self._open_port: Optional[int] = None
        self._callback: Optional[Callable] = None
        self._callback_data = None
        self.sent: list[list[int]] = []

    # --- ports
    def get_ports(self) -> list[str]:
        return list(self.ports)

    def get_port_count(self) -> int:
        return len(self.ports)

    def get_port_name(self, index: int, *_args) -> Optional[str]:
        return self.ports[index] if 0 <= index < len(self.ports) else None

    def open_port(self, port: int = 0, *_args, **_kwargs) -> "FakeMidiPort":
        if not 0 <= port < len(self.ports):
            raise rtmidi.InvalidPortError(f"Invalid port number: {port}")
        self._open_port = port
        return self

    def open_virtual_port(self, *_args, **_kwargs) -> "FakeMidiPort":
        self._open_port = 0
        return self

    def close_port(self) -> None:
        self._open_port = None

    def is_port_open(self) -> bool:
        return self._open_port is not None

    def delete(self) -> None:
        self.close_port()

    def get_current_api(self) -> int:
        return rtmidi.API_RTMIDI_DUMMY

    def set_client_name(self, *_args) -> None:
        pass

    def set_port_name(self, *_args) -> None:
        pass

    # --- input
    def set_callback(self, callback: Callable, data=None) -> None:
        self._callback, self._callback_data = callback, data

    def cancel_callback(self) -> None:
        self._callback = None

    def ignore_types(self, *_args, **_kwargs) -> None:
        pass

    def get_message(self) -> None:
        return None

    def receive(self, message: list[int], delta_time: float = 0.0) -> None:
        """Deliver a message to the input callback, as the JD-Xi would."""
        if self._callback is not None:
            self._callback((list(message), delta_time), self._callback_data)

    # --- output
    def send_message(self, message) -> None:
        self.sent.append(list(message))

    # --- context manager, as rtmidi's ports
    def __enter__(self) -> "FakeMidiPort":
        return self

    def __exit__(self, *_exc) -> None:
        self.close_port()

    # --- camelCase spellings used in parts of the code base
    getPortCount = get_port_count
    getPortName = get_port_name
    openPort = open_port
    closePort = close_port
    isPortOpen = is_port_open
    setCallback = set_callback
    ignoreTypes = ignore_types


class FakeMidiIn(FakeMidiPort):
    pass


class FakeMidiOut(FakeMidiPort):
    pass


def _wants_real_midi(config) -> bool:
    if os.environ.get("JDXI_TEST_REAL_MIDI") == "1":
        return True
    return "hardware" in (config.getoption("markexpr", default="") or "").replace(
        "not hardware", ""
    )


def pytest_configure(config) -> None:
    # Runs before test modules are imported, so every MidiIOHelper the tests
    # create gets the fake ports
    if not _wants_real_midi(config):
        rtmidi.MidiIn = FakeMidiIn
        rtmidi.MidiOut = FakeMidiOut


@pytest.fixture(autouse=True)
def _no_unsaved_changes_dialog(monkeypatch):
    """Tests change values: the "unsaved changes" question (a modal dialog) answers Discard."""
    from jdxi_editor.ui.v2 import history

    monkeypatch.setattr(history, "ask", lambda labels, action, parent=None: "discard")
