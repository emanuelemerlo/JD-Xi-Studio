"""
A JD-Xi unplugged or switched off: its MIDI input may refuse to close
(Windows: «error closing Windows MM MIDI input port»). Reopened, such a port
received nothing (the badge stayed «Verifying the JD-Xi…») and listing the
ports through it crashed the app: a port that fails to close is replaced.
"""

import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])

from jdxi_editor.midi.io.helper import MidiIOHelper


def test_a_port_that_does_not_close_is_replaced_and_set_up_again():
    helper = MidiIOHelper()
    dead = Mock()
    dead.is_port_open.return_value = True
    dead.close_port.side_effect = RuntimeError("MidiInWinMM::closePort: error closing")
    helper.midi_in = dead
    helper.close_ports()
    assert helper.midi_in is not dead
    # the new input gets SysEx and calls the helper's callback, as the first one
    assert getattr(helper.midi_in, "_callback", None) == helper.midi_callback


def test_the_dialog_lists_the_ports_through_ports_of_its_own():
    from jdxi_editor.ui.windows.midi.config_dialog import list_midi_ports

    helper = Mock()
    helper.get_input_ports.side_effect = AssertionError("not through the helper's port")
    helper.get_output_ports.side_effect = AssertionError("not through the helper's port")
    inputs, outputs = list_midi_ports(helper)
    assert inputs and outputs  # the test ports (tests/conftest.py)


def test_reconnecting_opens_new_ports():
    """
    Unplugged and back: the old input failed to close on Windows («openPort:
    error closing…», RtMidi's message for closePort), the reconnection gave up,
    the next one opened the broken port again: nothing received.
    """
    helper = MidiIOHelper()
    old_in, old_out = helper.midi_in, helper.midi_out
    in_name = next(p for p in helper.get_input_ports() if "JD-Xi" in p)
    out_name = next(p for p in helper.get_output_ports() if "JD-Xi" in p)
    assert helper.reconnect_port_names(in_name, out_name)
    assert helper.midi_in is not old_in and helper.midi_out is not old_out
    assert helper.midi_in.is_port_open() and helper.midi_out.is_port_open()
    assert getattr(helper.midi_in, "_callback", None) == helper.midi_callback
