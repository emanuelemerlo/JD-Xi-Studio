"""MIDI Player: the deadline scheduler (default) and the earlier timer one (JDXI_PLAYBACK_SCHEDULER=timer)."""

import os

import mido
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QElapsedTimer

from jdxi_editor.midi.playback import transport as tp


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def _song(notes: int = 8, step: int = 60) -> mido.MidiFile:
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    track = mido.MidiTrack()
    for i in range(notes):
        track.append(mido.Message("note_on", note=60 + i, velocity=90, time=0))
        track.append(mido.Message("note_off", note=60 + i, velocity=0, time=step))
    mid.tracks.append(track)
    return mid  # 8 notes, 1/8 beat each: ~0.5 s at 120 BPM


def _run(app, transport, ms: int = 3000) -> None:
    clock = QElapsedTimer()
    clock.start()
    while clock.elapsed() < ms and transport.state != tp.TransportState.STOPPED:
        app.processEvents()


def test_the_kind(monkeypatch):
    monkeypatch.delenv("JDXI_PLAYBACK_SCHEDULER", raising=False)
    assert tp.scheduler_kind() == "deadline"
    monkeypatch.setenv("JDXI_PLAYBACK_SCHEDULER", "timer")
    assert tp.scheduler_kind() == "timer"
    monkeypatch.setenv("JDXI_PLAYBACK_SCHEDULER", "anything else")
    assert tp.scheduler_kind() == "deadline"


@pytest.mark.parametrize("kind", ["deadline", "timer"])
def test_plays_every_note_and_ends(app, monkeypatch, kind):
    monkeypatch.setenv("JDXI_PLAYBACK_SCHEDULER", kind)
    sent = []
    transport = tp.TransportController(send=sent.append)
    finished = []
    transport.finished.connect(lambda: finished.append(True))  # on the UI thread
    transport.load(_song())
    assert transport.play()
    _run(app, transport)
    for _ in range(5):
        app.processEvents()
    notes = [m.note for m in sent if m.type == "note_on" and m.velocity > 0]
    assert notes == list(range(60, 68))
    assert finished and transport.position_seconds == 0.0
    transport.shutdown()


def test_pause_and_play_again_wake_it(app, monkeypatch):
    """Woken by the commands: no wait for a deadline computed before them."""
    monkeypatch.setenv("JDXI_PLAYBACK_SCHEDULER", "deadline")
    sent = []
    transport = tp.TransportController(send=sent.append)
    transport.load(_song(notes=4, step=960))  # notes 1 s apart
    transport.play()
    clock = QElapsedTimer()
    clock.start()
    while clock.elapsed() < 100:
        app.processEvents()
    transport.pause()
    transport.seek_seconds(0.999)  # just before the second note
    transport.play()
    clock.restart()
    while clock.elapsed() < 300:
        app.processEvents()
    notes = [m.note for m in sent if m.type == "note_on" and m.velocity > 0]
    assert notes[:2] == [60, 61]  # the second came at once, not after the first wait
    transport.shutdown()


def test_windows_timer_resolution_is_harmless_elsewhere():
    resolution = tp._WindowsTimerResolution()
    resolution.set(True)
    resolution.set(False)  # on Linux / macOS nothing to do, no error
