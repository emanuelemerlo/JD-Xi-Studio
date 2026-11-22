"""MIDI Player › Automation: each type offers its own presets, and the type follows the channel.

The type combo's text was passed as the preset list's key (an enum): nothing matched and the
drum kits came back, so Analog (and Digital, once changed) offered drum kits — a program change
in a bank the JD-Xi part ignores.
"""

import os
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.v2 import players


@pytest.fixture(scope="module")
def automation():
    app = QApplication.instance() or QApplication([])
    helper = Mock(spec=MidiIOHelper)
    helper.midi_out = Mock()
    editor = players.MidiFilePlayer(midi_helper=helper)
    yield editor.automation
    editor.transport_controller.shutdown()
    editor.close()
    app.processEvents()


def _first(automation) -> str:
    return automation.automation_program_combo.itemText(0)


def _bank(automation) -> int:
    msb, _lsb, _pc = automation.automation_program_combo.currentData()
    return int(msb)


def test_each_type_its_presets(automation):
    combo = automation.automation_type_combo
    for index, (text, msb) in enumerate((("Digital", 95), ("Analog", 94), ("Drums", 86))):
        combo.setCurrentIndex(index)
        assert combo.currentText() == text
        assert _bank(automation) == msb, (text, _first(automation))
    combo.setCurrentIndex(0)  # back to Digital: its tones, not the kits left from Drums
    assert _bank(automation) == 95


def test_the_type_follows_the_channel(automation):
    channel = automation.automation_channel_combo
    for index, (text, msb) in ((2, ("Analog", 94)), (9, ("Drums", 86)), (0, ("Digital", 95)), (1, ("Digital", 95))):
        channel.setCurrentIndex(index)
        assert automation.automation_type_combo.currentText() == text
        assert _bank(automation) == msb
