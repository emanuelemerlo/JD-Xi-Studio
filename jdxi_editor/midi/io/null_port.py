"""
A MIDI port with no device behind it, for running without a MIDI backend.

rtmidi.MidiIn() / rtmidi.MidiOut() raise when the system has no MIDI API to
open: Linux without the ALSA sequencer (/dev/snd/seq), some containers and VMs,
WSL. The editor then runs offline on these ports: no ports are listed, nothing
is sent or received, and the rest of the application works as usual.

The class implements the subset of the rtmidi.MidiIn / rtmidi.MidiOut interface
the editor uses, in both the snake_case and the camelCase spelling.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

import rtmidi
from decologr import Decologr as log


class NullMidiPort:
    """Stand-in for rtmidi.MidiIn / rtmidi.MidiOut when no MIDI API is available."""

    def __init__(self, reason: str = "") -> None:
        self.reason = reason

    # --- ports
    def get_ports(self) -> list[str]:
        return []

    def get_port_count(self) -> int:
        return 0

    def get_port_name(self, *_args) -> Optional[str]:
        return None

    def open_port(self, *_args, **_kwargs) -> "NullMidiPort":
        raise rtmidi.InvalidPortError("No MIDI backend available")

    def open_virtual_port(self, *_args, **_kwargs) -> "NullMidiPort":
        raise rtmidi.InvalidPortError("No MIDI backend available")

    def close_port(self) -> None:
        pass

    def is_port_open(self) -> bool:
        return False

    def delete(self) -> None:
        pass

    # --- input
    def set_callback(self, _callback: Callable, _data=None) -> None:
        pass

    def cancel_callback(self) -> None:
        pass

    def ignore_types(self, *_args, **_kwargs) -> None:
        pass

    def get_message(self) -> None:
        return None

    # --- output
    def send_message(self, _message) -> None:
        pass

    # --- camelCase spellings used in parts of the code base
    getPortCount = get_port_count
    getPortName = get_port_name
    openPort = open_port
    closePort = close_port
    isPortOpen = is_port_open
    setCallback = set_callback
    ignoreTypes = ignore_types


def open_rtmidi_port(port_class: type) -> Tuple[object, Optional[str]]:
    """
    Create an rtmidi port, or a NullMidiPort when the MIDI API cannot be opened.

    :param port_class: rtmidi.MidiIn or rtmidi.MidiOut
    :return: (port, error) where error is None when the real port was created
    """
    try:
        return port_class(), None
    except Exception as ex:  # rtmidi raises SystemError/RtMidiError depending on the API
        reason = f"{type(ex).__name__}: {ex}"
        log.warning(
            f"MIDI backend unavailable ({reason}); running without MIDI",
            scope="MidiIOController",
        )
        return NullMidiPort(reason), reason
