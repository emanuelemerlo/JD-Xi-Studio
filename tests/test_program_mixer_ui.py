"""
Program mixer UI (no MIDI hardware).

- mixer mute buttons are lit while muted, dark while playing
- the Mixer Level Settings sit on their own glossy panel
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])

from jdxi_editor.ui.editors.program.channel_strip import ChannelStrip
from jdxi_editor.ui.style.factory import generate_sequencer_button_style


def test_mute_lit_only_while_muted():
    strip = ChannelStrip(title="BD1", slider=None, value_label=None, icon=None)
    assert strip.mute.styleSheet() == generate_sequencer_button_style(False)
    strip.mute.setChecked(True)
    assert strip.mute.styleSheet() == generate_sequencer_button_style(True)


def _lightness_at(host, widget, x, y):
    from PySide6.QtCore import QPoint

    point = widget.mapTo(host, QPoint(x, y))
    return host.grab().toImage().pixelColor(point).lightness()


def test_program_mixer_sits_on_a_glossy_panel():
    """The Program editor's Mixer Level Settings are a section on their own glossy panel."""
    from jdxi_editor.ui.editors.program.editor import ProgramEditor
    from jdxi_editor.ui.style.editor_style import SHEEN_PROPERTY

    editor = ProgramEditor(midi_helper=MagicMock(), preset_helper=MagicMock())
    try:
        assert editor.mixer_panel.property(SHEEN_PROPERTY)
        assert editor.mixer_panel.isAncestorOf(editor.mixer_widget.mixer_group)
    finally:
        editor.close()
        editor.deleteLater()
