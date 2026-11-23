"""MIDI Player: the deadline scheduler (default) and the earlier timer one (JDXI_PLAYBACK_SCHEDULER=timer)."""

import os

import mido
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QElapsedTimer
from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.playback import transport as tp


@pytest.fixture(scope="module")
def app():
    # a QApplication, not a QCoreApplication: a later test in the same run
    # that builds widgets would abort on a core-only instance
    return QCoreApplication.instance() or QApplication([])


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
    try:
        transport.load(_song())
        assert transport.play()
        _run(app, transport)
        # «finished» comes queued from the scheduler: on a busy machine (the whole
        # suite) after the 5 rounds of events it was given (the notes all played)
        clock = QElapsedTimer()
        clock.start()
        while not finished and clock.elapsed() < 3000:
            app.processEvents()
        notes = [m.note for m in sent if m.type == "note_on" and m.velocity > 0]
        assert notes == list(range(60, 68))
        assert finished and transport.position_seconds == 0.0
    finally:
        transport.shutdown()  # its thread stopped even when an assert fails (else a crash at exit)


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


def test_windows_wait_ends_on_time_and_wakes(monkeypatch):
    """The Windows wait (event for most of it, then 1 ms sleeps) ends on time and still wakes."""
    import threading
    import time

    from picomidi.playback.engine import PlaybackEngine

    real_platform = tp.sys.platform
    monkeypatch.setattr(tp.sys, "platform", "win32")
    scheduler = tp._PreciseWaitScheduler(PlaybackEngine(), lock=threading.RLock())
    start = time.perf_counter()
    scheduler._wait_for_wake(0.05)
    elapsed = time.perf_counter() - start
    # the Windows path's precision is Windows' (and Linux's); a macOS runner's
    # 1 ms sleeps are coarser: there it must only end, not too early
    assert 0.049 <= elapsed < (0.15 if real_platform == "darwin" else 0.06)
    # a wake in the last 20 ms (pause, seek…) ends the wait at once
    threading.Timer(0.035, scheduler.wake).start()
    start = time.perf_counter()
    scheduler._wait_for_wake(0.5)
    assert time.perf_counter() - start < 0.06
    assert not scheduler._wake.is_set()  # cleared for the next wait


def test_the_engine_reads_a_precise_clock():
    """picomidi's engine read time.monotonic(): 15.6 ms steps on Windows before Python 3.13."""
    import time

    transport = tp.TransportController()
    assert isinstance(transport.engine, tp.PreciseClockEngine)
    before = time.perf_counter()
    now = transport.engine._now()
    assert before <= now <= time.perf_counter()  # the same clock as perf_counter
    transport.shutdown()
