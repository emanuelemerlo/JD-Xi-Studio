"""
Doubled parts on one channel: the JD-Xi never holds more voices of a key
than the note-offs it will get can end (no notes hanging until Panic).

Two tracks playing the same note on the same channel (a left/right copy of a
lead moved onto one part) send two note-ons; the engine sends one note-off,
when the last of them ends. The second note-on is preceded by a note-off.
"""

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from mido import Message, MetaMessage, MidiFile, MidiTrack
from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.playback.transport import TransportController


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _voices_left(sent) -> dict:
    """Voices the instrument still holds if every note-on starts one and a note-off ends one."""
    voices: dict = {}
    for msg in sent:
        key = (getattr(msg, "channel", None), getattr(msg, "note", None))
        if msg.type == "note_on" and msg.velocity > 0:
            voices[key] = voices.get(key, 0) + 1
        elif msg.type in ("note_off", "note_on") and voices.get(key):
            voices[key] -= 1
    return {k: n for k, n in voices.items() if n}


def test_a_second_note_on_on_a_sounding_key_is_retriggered():
    transport = TransportController(send=None)
    on = Message("note_on", channel=0, note=60, velocity=100)
    assert transport._one_voice_per_key(on) == [on]
    again = transport._one_voice_per_key(on)
    assert [m.type for m in again] == ["note_off", "note_on"]
    assert again[0].channel == 0 and again[0].note == 60
    # another key, another channel: untouched
    assert transport._one_voice_per_key(Message("note_on", channel=1, note=60, velocity=90)) == [
        Message("note_on", channel=1, note=60, velocity=90)]
    # released (note-on velocity 0 too): the next one starts clean
    transport._one_voice_per_key(Message("note_on", channel=0, note=60, velocity=0))
    assert len(transport._one_voice_per_key(on)) == 1
    # All Notes Off clears the channel
    transport._one_voice_per_key(Message("control_change", channel=0, control=123, value=0))
    assert len(transport._one_voice_per_key(on)) == 1


def test_two_tracks_doubling_a_note_leave_no_voice_hanging(app):
    mid = MidiFile(type=1, ticks_per_beat=480)
    for offset in (0, 60):  # the copy starts a little later and ends later
        track = MidiTrack()
        track.append(MetaMessage("set_tempo", tempo=250000, time=0))
        track.append(Message("note_on", channel=0, note=64, velocity=100, time=offset))
        track.append(Message("note_off", channel=0, note=64, velocity=0, time=240))
        mid.tracks.append(track)
    sent = []
    transport = TransportController(send=sent.append)
    try:
        transport.load(mid)
        transport.play()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not any(
            m.type in ("note_off", "note_on") and getattr(m, "velocity", 1) == 0 and m.note == 64
            and sent.index(m) > 1 for m in sent
        ):
            app.processEvents()
            time.sleep(0.005)
        time.sleep(0.3)
        app.processEvents()
        notes = [m for m in sent if m.type in ("note_on", "note_off")]
        assert sum(1 for m in notes if m.type == "note_on" and m.velocity) == 2  # both played
        assert _voices_left(notes) == {}
    finally:
        transport.shutdown()
