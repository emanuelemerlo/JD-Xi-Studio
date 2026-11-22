"""
How punctual is MIDI file playback? Plays a file with the MIDI Player's engine,
without sending anything to an instrument, and measures how late each note
leaves compared with when the file says it should: with the deadline scheduler
(the default since 1.0) and with the earlier one (a timer every 5 ms).

    python scripts/playback_timing.py              # a busy test song (~20 s)
    python scripts/playback_timing.py song.mid     # your file (its first 30 s)
    python scripts/playback_timing.py --seconds 10

Lateness in milliseconds: the average, 95 notes in 100 within…, the worst.
Below ~2 ms nobody hears it; 10 ms and more smear fast drums. On Windows the
numbers are the ones that matter (its timers are the coarsest).
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mido  # noqa: E402
from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402


def busy_song(seconds: float = 20.0, bpm: int = 140) -> mido.MidiFile:
    """Sixteenths on Digital 1, eighths on Digital 2, a bass line, 32nd hi-hats."""
    tpb = 480
    mid = mido.MidiFile(type=1, ticks_per_beat=tpb)
    tempo = mido.MidiTrack()
    tempo.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    mid.tracks.append(tempo)
    beats = int(seconds * bpm / 60)
    for channel, step, notes in ((0, tpb // 4, (72, 76, 79, 84)), (1, tpb // 2, (60, 64, 67)),
                                 (2, tpb, (36, 43)), (9, tpb // 8, (42,))):
        track = mido.MidiTrack()
        count = beats * tpb // step
        for i in range(count):
            note = notes[i % len(notes)]
            track.append(mido.Message("note_on", channel=channel, note=note, velocity=90, time=0))
            track.append(mido.Message("note_off", channel=channel, note=note, velocity=0, time=step))
        mid.tracks.append(track)
    return mid


def expected_note_times(mid: mido.MidiFile, limit: float) -> list[float]:
    """When each note-on is due, in seconds from the start (the file's own timing)."""
    times, now = [], 0.0
    for msg in mid:
        now += msg.time
        if now > limit:
            break
        if msg.type == "note_on" and msg.velocity > 0:
            times.append(now)
    return times


def measure(mid: mido.MidiFile, kind: str, limit: float) -> list[float]:
    os.environ["JDXI_PLAYBACK_SCHEDULER"] = kind
    from jdxi_editor.midi.playback.transport import TransportController

    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    sent: list[float] = []
    start = [0.0]

    def send(msg: mido.Message) -> None:
        if msg.type == "note_on" and msg.velocity > 0:
            sent.append(time.perf_counter() - start[0])

    transport = TransportController(send=send)
    assert transport.scheduler_kind == kind
    transport.load(mid)
    transport.finished.connect(app.quit)
    stop = QTimer()  # its own timer: a leftover one would cut the next measurement short
    stop.setSingleShot(True)
    stop.timeout.connect(app.quit)
    stop.start(int(limit * 1000) + 500)
    start[0] = time.perf_counter()
    transport.play()
    app.exec()
    stop.stop()
    transport.finished.disconnect(app.quit)
    transport.shutdown()
    due = expected_note_times(mid, limit)
    return [(got - want) * 1000.0 for got, want in zip(sent, due)]


def report(kind: str, late: list[float]) -> None:
    if not late:
        print(f"{kind:9s} no notes measured")
        return
    ordered = sorted(late)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    # the first note's lateness is the start-up delay: punctuality is the spread around it
    base = ordered[0]
    print(f"{kind:9s} {len(late):5d} notes   average {statistics.mean(late) - base:6.2f} ms   "
          f"95% within {p95 - base:6.2f} ms   worst {ordered[-1] - base:6.2f} ms")


def _late_ms(wait, seconds: float, times: int = 100) -> float:
    total = 0.0
    for _ in range(times):
        start = time.perf_counter()
        wait(seconds)
        total += time.perf_counter() - start - seconds
    return total / times * 1000.0


def diagnose() -> None:
    """How late the system's own waits end (a 2 ms wait, 100 times): what the schedulers stand on."""
    import threading

    event = threading.Event()
    rows = [("Event.wait 2 ms", event.wait), ("time.sleep 2 ms", time.sleep)]
    print(f"\nPython {sys.version.split()[0]}: clocks' resolution")
    for name in ("monotonic", "perf_counter"):
        info = time.get_clock_info(name)
        print(f"  time.{name:13s} {info.resolution * 1000:8.4f} ms  ({info.implementation})")
    print("How late a 2 ms wait ends (average)")
    for name, wait in rows:
        print(f"  {name:18s} {_late_ms(wait, 0.002):6.2f} ms")
    if sys.platform == "win32":
        import ctypes

        winmm = ctypes.WinDLL("winmm")
        result = winmm.timeBeginPeriod(1)
        print(f"  with timeBeginPeriod(1) (returned {result}):")
        for name, wait in rows:
            print(f"  {name:18s} {_late_ms(wait, 0.002):6.2f} ms")
        winmm.timeEndPeriod(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("file", nargs="?", help="a MIDI file (default: a busy test song)")
    parser.add_argument("--seconds", type=float, default=None, help="how much to play (default 20, or 30 of a file)")
    args = parser.parse_args()
    if args.file:
        mid, limit = mido.MidiFile(args.file), args.seconds or 30.0
        print(f"{args.file}: first {limit:.0f} s")
    else:
        limit = args.seconds or 20.0
        mid = busy_song(limit)
        print(f"Test song: {limit:.0f} s, 140 BPM, 16ths + 8ths + bass + 32nd hi-hats")
    print(f"Platform: {sys.platform}, Python {sys.version.split()[0]}\n")
    for kind in ("deadline", "timer"):
        report(kind, measure(mid, kind, limit))
    diagnose()


if __name__ == "__main__":
    main()
