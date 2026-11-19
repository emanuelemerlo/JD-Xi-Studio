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


def test_mixer_parts_have_their_tab_colour_and_the_master_is_neutral():
    """PR-26: each part in its tab's colour; the Master apart, in a neutral light."""
    from jdxi_editor.ui.editors.program.editor import ProgramEditor
    from jdxi_editor.ui.editors.program.mixer.section import MASTER_COLOUR
    from jdxi_editor.ui.v2.brand import PART_COLOURS

    editor = ProgramEditor(midi_helper=MagicMock(), preset_helper=MagicMock())
    try:
        colours = [t.slider.property("strip_colour") for t in editor.mixer_widget.tracks]
        # Master, Digital 1, Digital 2, Drums, Analog
        assert colours == [MASTER_COLOUR, *PART_COLOURS]
        assert MASTER_COLOUR not in PART_COLOURS
        for track, colour in zip(editor.mixer_widget.tracks, colours):
            assert colour in track.slider.styleSheet() and colour in track.label.styleSheet()
    finally:
        editor.close()
        editor.deleteLater()


def test_mixer_level_box_and_fader_follow_each_other():
    """A level typed above the fader moves it (and so is sent); the fader, also
    when the JD-Xi sets it silently, shows its level in the box."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSlider

    from jdxi_editor.ui.editors.program.editor import ProgramEditor

    editor = ProgramEditor(midi_helper=MagicMock(), preset_helper=MagicMock())
    try:
        fader = editor.mixer_widget.tracks[1].slider  # Digital 1
        box = fader.level_box
        assert fader.slider.tickPosition() == QSlider.TickPosition.NoTicks
        sent = []
        fader.valueChanged.connect(sent.append)
        box.setValue(77)
        assert fader.value() == 77 and sent and sent[-1] == 77
        fader.setValueSilently(12)
        assert box.value() == 12
        fader.setValue(100)
        assert box.value() == 100
    finally:
        editor.close()
        editor.deleteLater()
