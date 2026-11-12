"""Pattern and MIDI file player in the new look: same editors, same controls, flat buttons."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QGroupBox, QPushButton

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.editors.midi_player import editor as old_player
from jdxi_editor.ui.editors.pattern import pattern as old_pattern
from jdxi_editor.ui.style.editor_style import FLAT_PROPERTY
from jdxi_editor.ui.style.jdxi import JDXiUIStyle
from jdxi_editor.ui.v2 import players


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _helper():
    helper = Mock(spec=MidiIOHelper)
    helper.midi_out = Mock()
    helper.send_raw_message = lambda b: True
    return helper


def _check_look(editor):
    buttons = editor.findChildren(QPushButton)
    assert not [b for b in buttons if b.styleSheet() == JDXiUIStyle.BUTTON_ROUND]
    assert all(g.property(FLAT_PROPERTY) for g in editor.findChildren(QGroupBox))
    assert "#121214" in editor.styleSheet()
    return {b.text() for b in buttons if b.text()}


def test_same_class_names_for_the_main_window():
    # get_existing_editor() finds open editors by class name.
    assert players.PatternSequenceEditor.__name__ == old_pattern.PatternSequenceEditor.__name__
    assert players.MidiFilePlayer.__name__ == old_player.MidiFilePlayer.__name__
    from jdxi_editor.ui.windows.jdxi import instrument

    assert instrument.PatternSequenceEditor is players.PatternSequenceEditor
    assert instrument.MidiFilePlayer is players.MidiFilePlayer


def test_pattern_keeps_its_controls(app):
    editor = players.PatternSequenceEditor(midi_helper=_helper(), preset_helper=Mock())
    assert isinstance(editor, old_pattern.PatternSequenceEditor)
    texts = _check_look(editor)
    assert {"Play", "Stop", "Load", "Save"} <= texts
    # Each flat button keeps its own action: Load/Save are not swapped.
    for button in editor.findChildren(QPushButton):
        if button.text() in ("Load", "Save") and button.toolTip():
            assert button.text().lower() in button.toolTip().lower()
    assert len(editor.buttons) == 4 and len(editor.buttons[0]) == 16  # the sequencer grid
    editor.close()


def test_player_keeps_its_controls(app):
    editor = players.MidiFilePlayer(midi_helper=_helper())
    assert isinstance(editor, old_player.MidiFilePlayer)
    texts = _check_look(editor)
    assert {"Play", "Stop", "Pause", "Load", "Save"} <= texts
    for button in editor.findChildren(QPushButton):
        if button.text() in ("Load", "Save") and button.toolTip():
            assert button.text().lower() in button.toolTip().lower(), (button.text(), button.toolTip())
    editor.close()


def test_pattern_cards_as_in_the_mockup(app):
    editor = players.PatternSequenceEditor(midi_helper=_helper(), preset_helper=Mock())
    editor.resize(1500, 950)
    editor.show()
    titles = [g.title() for g in editor.findChildren(QGroupBox) if g.title()]
    for title in ("TRANSPORT", "NEW STEPS", "PATTERN SEQUENCER", "FILE", "USB RECORDER"):
        assert title in titles, titles
    # Transport, tempo, steps and the recorder are on show (not behind a toggle)
    for widget in (editor.play_button, editor.stop_button, editor.pause_button, editor.shuffle_button,
                   editor.tempo_spinbox, editor.tap_tempo_button, editor.beats_per_measure_combo,
                   editor.velocity_spinbox, editor.duration_combo, editor.add_measure_button,
                   editor.copy_button, editor.paste_button, editor.usb_recorder):
        assert widget.isVisibleTo(editor), widget
    # the same engine: the buttons still drive it
    editor.tempo_spinbox.setValue(96)
    assert editor.tempo_spinbox.value() == 96
    editor.close()


def test_player_cards_as_in_the_mockup(app):
    editor = players.MidiFilePlayer(midi_helper=_helper())
    editor.resize(1500, 950)
    editor.show()
    titles = [g.title() for g in editor.findChildren(QGroupBox) if g.title()]
    for title in ("PLAYER", "CLASSIFICATION", "TRACKS", "PLAYBACK", "AUTOMATION", "USB RECORDER"):
        assert title in titles, titles
    assert editor.midi_file.midi_track_viewer.isVisibleTo(editor)
    assert editor.usb_recorder.isVisibleTo(editor) and editor.automation.isVisibleTo(editor)
    editor.close()


def test_pattern_fills_the_width_with_the_side_panel(app):
    from jdxi_editor.ui.widgets.pattern.sequencer_button import SequencerButton

    editor = players.PatternSequenceEditor(midi_helper=_helper(), preset_helper=Mock())
    editor.resize(1600, 900)
    editor.show()
    for _ in range(10):
        app.processEvents()
    assert editor.base_widget.centered_wrapper is None  # not centred with margins any more
    assert editor.info_panel.isVisible() and editor.info_panel.width() == 320
    editor.explain(editor.play_button)
    assert editor.info_panel.name.text() == "Play"
    step = editor.pattern_widget.findChildren(SequencerButton)[0]
    editor.explain(step)
    assert editor.info_panel.name.text() == "Step"
    editor.close()
