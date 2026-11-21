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


def test_player_buttons_in_columns(app):
    """Load / Save / Close right under Play / Stop / Pause (one width, one spacing)."""
    editor = players.MidiFilePlayer(midi_helper=_helper())
    editor.resize(1600, 900)
    editor.show()
    for _ in range(30):
        app.processEvents()

    def xs(holder):
        found = [b for b in holder.findChildren(QPushButton) if b.text().strip() and b.isVisible()]
        return [b.mapTo(editor, b.rect().topLeft()).x() for b in found]

    top, bottom = xs(editor.transport), xs(editor.midi_file_group)
    assert len(bottom) == 3 and top[: len(bottom)] == bottom
    editor.transport_controller.shutdown()
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
    for title in ("PLAYER", "FIT TO THE JD-XI", "TRACKS", "PLAYBACK", "AUTOMATION", "USB RECORDER"):
        assert title in titles, titles
    assert editor.midi_file.midi_track_viewer.isVisibleTo(editor)
    assert editor.usb_recorder.isVisibleTo(editor) and editor.automation.isVisibleTo(editor)
    editor.close()


def test_more_room_for_the_tracks(app, monkeypatch):
    """Expand hides the cards not needed while listening (Player and Playback
    stay); the grip under the card sets its height, remembered."""
    from jdxi_editor.ui.v2 import tracks_space

    store = {}
    monkeypatch.setattr(tracks_space, "_settings", lambda: type("S", (), {
        "value": lambda self, key, default=None: store.get(key, default),
        "setValue": lambda self, key, value: store.__setitem__(key, value)})())
    editor = players.MidiFilePlayer(midi_helper=_helper())
    editor.resize(1500, 950)
    editor.show()
    app.processEvents()
    button = editor.tracks_expand_button
    assert button.text().endswith("Expand")
    button.click()
    assert not editor.automation.isVisibleTo(editor) and not editor.usb_recorder.isVisibleTo(editor)
    # Fit to the JD-Xi is beside the Player, above the tracks: hiding it gives them no room
    assert editor.classification_group.isVisibleTo(editor)
    assert editor.playback_options.isVisibleTo(editor) and editor.transport.isVisibleTo(editor)
    assert editor.midi_file.midi_track_viewer.isVisibleTo(editor)
    assert button.text().endswith("Restore")
    button.click()
    assert editor.automation.isVisibleTo(editor) and editor.classification_group.isVisibleTo(editor)

    grip = editor.tracks_grip
    grip.set_height(520)
    assert editor.tracks_card.minimumHeight() == 520 and store[tracks_space.SETTINGS_KEY] == 520
    grip.set_height(10)  # never smaller than a few rows
    assert editor.tracks_card.minimumHeight() == tracks_space.MIN_HEIGHT
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


def test_player_buttons_one_width_not_stretched(app):
    """Play … Panic stretched with the window while Load and Save stayed small:
    all at one width now, whatever the window."""
    from PySide6.QtWidgets import QPushButton

    editor = players.MidiFilePlayer(midi_helper=_helper())
    buttons = [b for holder in (editor.transport, editor.midi_file_group)
               for b in holder.findChildren(QPushButton) if b.text().strip()]
    assert len(buttons) >= 6
    for width in (1300, 2400):
        editor.resize(width, 950)
        editor.show()
        app.processEvents()
        assert len({b.width() for b in buttons}) == 1, [(b.text(), b.width()) for b in buttons]
    editor.close()


def test_track_channel_readable(app, tmp_path):
    """«Ch 16» fits beside the arrows (the arrows covered «Ch 10»)."""
    from unittest.mock import patch

    from mido import Message, MetaMessage, MidiFile, MidiTrack

    mid = MidiFile(type=1, ticks_per_beat=480)
    track = MidiTrack()
    track.append(MetaMessage("track_name", name="Strings", time=0))
    track.append(Message("note_on", note=60, velocity=90, channel=15, time=0))
    track.append(Message("note_off", note=60, velocity=0, channel=15, time=480))
    mid.tracks.append(track)
    path = tmp_path / "ch16.mid"
    mid.save(path)
    editor = players.MidiFilePlayer(midi_helper=_helper())
    editor.resize(1600, 900)
    editor.show()
    with patch.object(editor, "_notify_pattern_sequencer_file_loaded"):
        assert editor.midi_load_file_from_path(str(path), update_recent_files=False)
    for _ in range(20):
        app.processEvents()
    spin = next(iter(editor.midi_file.midi_track_viewer.track_channel_spins.values()))
    assert spin.text() == "Ch 16"
    room = spin.lineEdit().width()
    assert room >= spin.lineEdit().fontMetrics().horizontalAdvance("Ch 16") + 2, room
    editor.transport_controller.shutdown()
    editor.close()


def test_no_file_no_empty_ruler(app, tmp_path):
    """Before a file and after Close: a line saying how to open one, not a ruler 200 px tall
    in the middle of the card and 4000 px wide."""
    from unittest.mock import patch

    from mido import Message, MidiFile, MidiTrack

    editor = players.MidiFilePlayer(midi_helper=_helper())
    editor.resize(1600, 1000)
    editor.show()
    for _ in range(10):
        app.processEvents()
    viewer = editor.midi_file.midi_track_viewer

    def empty() -> bool:
        return (viewer._empty_note.isVisibleTo(editor) and not viewer.ruler.isVisibleTo(editor)
                and viewer.scroll_content.width() <= viewer.scroll_area.viewport().width())

    assert empty()
    mid = MidiFile(type=1, ticks_per_beat=480)
    track = MidiTrack()
    track.append(Message("note_on", note=60, velocity=90, channel=0, time=0))
    track.append(Message("note_off", note=60, velocity=0, channel=0, time=1920))
    mid.tracks.append(track)
    mid.save(tmp_path / "one.mid")
    with patch.object(editor, "_notify_pattern_sequencer_file_loaded"):
        assert editor.midi_load_file_from_path(str(tmp_path / "one.mid"), update_recent_files=False)
    for _ in range(10):
        app.processEvents()
    assert viewer.ruler.isVisibleTo(editor) and not viewer._empty_note.isVisibleTo(editor)
    assert editor.midi_close_file()
    for _ in range(10):
        app.processEvents()
    assert empty()
    editor.transport_controller.shutdown()
    editor.close()
