"""Settings: System Common and System Controller (MIDI Implementation), and the editor's tools."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.ui.v2.settings import SettingsEditor, _channel_parse, _channel_text, settings_blocks


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_blocks_follow_the_midi_implementation():
    common, controller = settings_blocks()
    assert common.size() == 0x2B and controller.size() == 0x11
    offsets = {p.name: p.offset for p in common.params}
    assert offsets == {"MASTER_TUNE": 0x00, "MASTER_KEY_SHIFT": 0x04, "MASTER_LEVEL": 0x05,
                       "PROGRAM_CTRL_CH": 0x11, "RX_PROGRAM_CHANGE": 0x29, "RX_BANK_SELECT": 0x2A}
    offsets = {p.name: p.offset for p in controller.params}
    assert offsets == {"TRANSMIT_PROGRAM_CHANGE": 0, "TRANSMIT_BANK_SELECT": 1, "KEYBOARD_VELOCITY": 2,
                       "KEYBOARD_VELOCITY_CURVE": 3, "KEYBOARD_VELOCITY_CURVE_OFFSET": 4}
    tune = common.params[0]
    assert tune.get_nibbled_size() == 4
    assert (tune.convert_to_midi(-1000), tune.convert_to_midi(0), tune.convert_to_midi(1000)) == (24, 1024, 2024)
    shift = common.params[1]
    assert (shift.convert_to_midi(-24), shift.convert_to_midi(24)) == (40, 88)
    curve, offset = controller.params[3], controller.params[4]
    assert (curve.convert_to_midi(0), curve.convert_to_midi(2)) == (1, 3)
    assert (offset.convert_to_midi(-10), offset.convert_to_midi(9)) == (54, 73)
    assert not common.export and not controller.export  # not part of a patch


def test_program_control_channel_is_1_16_then_off():
    assert [_channel_text(v) for v in (0, 15, 16)] == ["1", "16", "OFF"]
    assert [_channel_parse(t) for t in ("1", "16", "off", "17")] == [0, 15, 16, None]


def test_page_and_tools(app):
    instrument = MagicMock()
    helper = MagicMock(is_input_open=True, is_output_open=False, in_port_name="JD-Xi", out_port_name="")
    editor = SettingsEditor(midi_helper=helper, parent=None, instrument=instrument)
    try:
        assert editor.pv("MASTER_TUNE").text().startswith("0.0")
        editor.update_connection()
        assert "Half connected" in editor.connection_label.text() and "JD-Xi" in editor.connection_label.text()
        for method in ("_show_midi_config", "_patch_load", "on_preferences", "_show_midi_message_monitor"):
            editor.buttons[method].click()
            assert getattr(instrument, method).called, method
    finally:
        editor.close()
