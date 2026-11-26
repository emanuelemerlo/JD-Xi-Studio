"""The notes a part of the MIDI file plays, on the main window's keyboard."""

import time

import mido
import pytest
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.midi.playback.transport import TransportController
from jdxi_editor.ui.editors.midi_player.fit_jdxi import PART_COLORS
from jdxi_editor.ui.editors.midi_player.keyboard_feed import KeyboardFeed
from jdxi_editor.ui.widgets.piano.keyboard import PianoKeyboard


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def transport(app):
    t = TransportController(send=lambda m: None)
    yield t
    t.shutdown()


def _on(t, channel, note):
    t._on_engine_event(mido.Message("note_on", channel=channel, note=note, velocity=90))


def _off(t, channel, note):
    t._on_engine_event(mido.Message("note_off", channel=channel, note=note, velocity=0))


def test_notes_on_are_those_sent_on_the_channel(transport):
    _on(transport, 2, 45)
    _on(transport, 0, 60)
    assert transport.notes_on(2) == {45}
    assert transport.notes_on(0) == {60}
    _off(transport, 2, 45)
    # a note just ended still shows for a moment (a short note is not missed)...
    assert transport.notes_on(2) == {45}
    # ...then it goes
    assert transport.notes_on(2, hold_s=0.0) == set()


def test_all_notes_off_clears_the_channel(transport):
    _on(transport, 2, 45)
    transport._on_engine_event(mido.Message("control_change", channel=2, control=123, value=0))
    assert transport.notes_on(2, hold_s=0.0) == set()


def test_the_keyboard_shows_the_notes_in_the_part_colour(app):
    holder = QWidget()
    keyboard = PianoKeyboard(parent=holder)
    keys = keyboard._keys_by_note
    keyboard.show_file_notes({48, 52}, PART_COLORS[3])
    assert keys[48].file_color is not None and keys[48].file_color.name() == PART_COLORS[3].lower()
    assert keys[52].file_color is not None
    assert keys[50].file_color is None
    keyboard.show_file_notes(set())
    assert all(k.file_color is None for k in keys.values())


def test_notes_beyond_the_keys_mark_the_edge(app):
    holder = QWidget()
    keyboard = PianoKeyboard(parent=holder)
    keys = keyboard._keys_by_note
    low, high = min(keys), max(keys)
    keyboard.show_file_notes({low - 12, 60}, "#00A0E9")
    assert keys[low].beyond == "<" and keys[high].beyond == ""
    assert keys[low].file_color is None  # the edge key itself is not played
    keyboard.show_file_notes({high + 1})
    assert keys[high].beyond == ">" and keys[low].beyond == ""
    keyboard.grab()  # paints


def test_the_feed_follows_the_chosen_part_and_its_octave(app, transport):
    holder = QWidget()
    keyboard = PianoKeyboard(parent=holder)
    octave = {2: 1}
    feed = KeyboardFeed(transport.notes_on, lambda: keyboard, lambda ch: octave.get(ch, 0))
    _on(transport, 2, 57)  # A3 played by the Analog part at Octave +1: the key of A2
    _on(transport, 0, 60)
    feed.set_channel(2)
    assert keyboard._keys_by_note[45].file_color is not None
    assert keyboard._keys_by_note[60].file_color is None  # Digital 1 is not shown
    feed.set_channel(None)
    assert all(k.file_color is None for k in keyboard._keys_by_note.values())


def test_the_choice_is_remembered(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QSettings

    from jdxi_editor.ui.widgets.transport import playback_options as po

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))

    class Parent(QWidget):
        chosen = []

        def __getattr__(self, name):
            if name == "on_keyboard_part_changed":
                return self.chosen.append
            return lambda *a, **k: None

    parent = Parent()
    options = po.PlaybackOptionsWidget(parent=parent)
    assert options.keyboard_channel is None  # Off at first
    options.keyboard_combo.setCurrentIndex(options.keyboard_combo.findData(2))
    assert parent.chosen == [2]
