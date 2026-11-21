"""MIDI Player › Close: the player empty as at start; asks first when the file has unsaved changes."""

import os
from unittest.mock import Mock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from mido import Message, MetaMessage, MidiFile, MidiTrack
from PySide6.QtWidgets import QApplication, QMessageBox

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.editors.midi_player.editor import MidiFilePlayer


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _song() -> MidiFile:
    mid = MidiFile(type=1, ticks_per_beat=480)
    track = MidiTrack()
    track.append(MetaMessage("track_name", name="Lead", time=0))
    for bar in range(4):
        track.append(Message("note_on", note=60 + bar, velocity=90, channel=0, time=0))
        track.append(Message("note_off", note=60 + bar, velocity=0, channel=0, time=1920))
    mid.tracks.append(track)
    return mid


@pytest.fixture
def player(app, tmp_path):
    helper = Mock(spec=MidiIOHelper)
    helper.midi_out = Mock()
    editor = MidiFilePlayer(midi_helper=helper)
    editor.song_path = tmp_path / "song.mid"
    _song().save(editor.song_path)
    yield editor
    editor.transport_controller.shutdown()
    editor.close()
    app.processEvents()


def _load(editor):
    with patch.object(editor, "_notify_pattern_sequencer_file_loaded"):
        assert editor.midi_load_file_from_path(str(editor.song_path), update_recent_files=False)


def _answer(monkeypatch, text):
    """The unsaved-changes question answered with the button whose text has *text*."""
    asked = []
    monkeypatch.setattr(QMessageBox, "exec", lambda box: asked.append(box.text()) or 0)
    monkeypatch.setattr(QMessageBox, "clickedButton",
                        lambda box: next(b for b in box.buttons() if text in b.text()))
    return asked


def test_save_and_close_only_with_a_file(player):
    group = player.midi_file_group
    assert not group.save_button.isEnabled() and not group.close_button.isEnabled()
    assert player.midi_close_file()  # nothing open: nothing to do
    _load(player)
    assert group.save_button.isEnabled() and group.close_button.isEnabled()


def test_close_empties_the_player(player, monkeypatch):
    _load(player)
    asked = _answer(monkeypatch, "Cancel")
    assert player.midi_close_file()
    assert asked == []  # nothing changed: no question
    assert player.midi_state.file is None and not player.is_midi_ready()
    assert not player.transport_controller.play()  # Play does nothing now
    assert player.midi_file.midi_track_viewer.midi_file is None
    assert player.midi_state.file_duration_seconds == 0
    assert not player.midi_file_group.close_button.isEnabled()
    _load(player)  # and a file opens again as before
    assert player.is_midi_ready()


def test_close_with_changes_asks_first(player, monkeypatch):
    _load(player)
    player._on_track_viewer_file_changed(player.midi_state.file)  # an edit of the tracks
    asked = _answer(monkeypatch, "Cancel")
    assert not player.midi_close_file()
    assert asked and player.midi_state.file is not None  # still open
    _answer(monkeypatch, "without saving")
    assert player.midi_close_file()
    assert player.midi_state.file is None
