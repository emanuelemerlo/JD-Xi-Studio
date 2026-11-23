"""
Checks against a JD-Xi: the release checks that can run by themselves.

The same tests run twice:

    pytest tests/test_jdxi_checks.py            on the simulated JD-Xi (every run, no hardware)
    pytest -m hardware tests/test_jdxi_checks.py   on the real JD-Xi, on its MIDI ports

With the real JD-Xi: close JD-Xi Studio first (the ports are not shared on
Windows). Every test leaves the JD-Xi's temporary program as it found it.
The WRITE check needs a hand on the JD-Xi and a slot that may be overwritten:

    JDXI_WRITE_SLOT=H64 pytest -m hardware -s tests/test_jdxi_checks.py -k write

They cover the steps of doc/hardware-test-plan.md that need no ears:
identity (2.9), a whole reading (MEM-05), pending until read back (MEM-02),
reconnection with nothing changed (2.10) and with a part changed and
restored (2.11), Init and its Undo on the instrument (6b.1), Save on the
JD-Xi checked by reading the slot back (6.8, 6.9).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Optional

import pytest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))

from jdxi_editor.midi.io.synth_memory import build_dt1  # noqa: E402
from jdxi_editor.midi.io.synth_state import parts_that_differ  # noqa: E402

ANALOG = bytes.fromhex("19420000")
ANALOG_AMP_LEVEL = 0x2A  # a safe parameter to change and put back (as scripts/hardware_check.py)
PARTS = ("program", "digital_1", "digital_2", "analog", "drums")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(condition, seconds: float = 10.0) -> bool:
    from PySide6.QtTest import QTest

    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        QTest.qWait(20)
    return bool(condition())


def _valid_analog_tone() -> list:
    """An Analog tone as the JD-Xi holds one: the editor's own values (all in range), named."""
    from unittest.mock import MagicMock

    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.analog import AnalogToneEditor

    editor = AnalogToneEditor(MidiIOHelper(), MagicMock())
    try:
        editor.pv("FILTER_CUTOFF").setValue(90)
        editor.pv("AMP_LEVEL").setValue(100)
        return [bytes(m) for m in editor.export_dt1s()]
    finally:
        editor.close()
        editor.deleteLater()


class JDXi:
    """The instrument the checks talk to: simulated, or the real one."""

    def __init__(self, kind: str):
        from jdxi_editor.midi.io.device import device_for
        from jdxi_editor.midi.io.helper import MidiIOHelper
        from jdxi_editor.midi.sysex.request.read_session import patch_section_requests

        self.kind = kind
        self.helper = MidiIOHelper()
        self.fake = None
        self.slots: dict = {}
        self.reads: list = []  # each read: complete, and the sections not read (for failure messages)
        if kind == "simulated":
            from test_ab_compare import FakeJDXi

            self.fake = FakeJDXi(self.helper)
            self.fake.load(_valid_analog_tone())  # values a real Analog tone can have
        else:
            found_in, found_out = self.helper.find_jdxi_ports() if hasattr(self.helper, "find_jdxi_ports") \
                else (None, None)
            if not found_in or not found_out or not self.helper.connect_port_names(found_in, found_out):
                pytest.skip("no JD-Xi on the MIDI ports (close JD-Xi Studio, connect the JD-Xi)")
        self.device = device_for(self.helper)
        self.device.requests.clear()  # nothing left queued by the tests before (other windows' readings)
        if self.fake is not None:  # as the app's own path: what goes out is noted as sent
            to_jdxi = self.helper.send_raw_message

            def send(message):
                self.device.sent([int(b) for b in message])
                return to_jdxi(message)

            self.helper.send_raw_message = send
        self.requests = [rq for _label, rq in patch_section_requests()]

    # --- reading and writing
    def read_all(self) -> bool:
        from jdxi_editor.midi.sysex.request.read_session import start_read_session

        results = []
        # the app's 8 s are for a JD-Xi; the macOS CI runner (a VM) can take longer than
        # that for the simulated one: these checks are about what is read, not how fast
        session = start_read_session(self.helper, self.requests, on_finished=lambda r: results.append(r),
                                     timeout_ms=30000)
        started = time.monotonic()
        assert wait_for(lambda: results or getattr(session, "_done", False), 60), "the reading never ended"
        complete = bool(results and results[0].complete)
        missing = [f"{s.label}: {s.status.value}" for s in results[0].sections
                   if s.status.value != "ok"] if results else ["no result"]
        self.reads.append((complete, round(time.monotonic() - started, 2), missing))
        return complete

    def diagnosis(self, before: Optional[dict] = None) -> str:
        """For a failure message: the reads (complete, seconds, sections not read) and the
        bytes that differ from *before*."""
        lines = [f"reads: {self.reads}"]
        if before is not None:
            now = self.snapshot()
            for key in sorted(set(before) | set(now)):
                a, b = before.get(key, b""), now.get(key, b"")
                if a != b:
                    offsets = [i for i in range(max(len(a), len(b)))
                               if (a[i] if i < len(a) else None) != (b[i] if i < len(b) else None)]
                    lines.append(f"{key}: {len(a)}/{len(b)} bytes, differ at {offsets[:12]}")
        return "\n".join(lines[:16])

    def snapshot(self) -> dict:
        return self.device.state.snapshot()

    def send_section(self, key: str, data: bytes) -> bool:
        return bool(self.helper.send_raw_message(list(build_dt1(bytes.fromhex(key), list(data)))))

    def put_back(self, snapshot: dict) -> None:
        for key, data in sorted(snapshot.items()):
            self.send_section(key, data)
        wait_for(lambda: False, 0.3)  # let the JD-Xi take them

    def analog_byte(self, offset: int) -> int:
        return self.snapshot()["19420000"][offset]

    # --- the user's hands on the JD-Xi
    def select(self, slot: str) -> bool:
        from jdxi_editor.ui.midi.selection_info import send_program_with_expectation
        from jdxi_editor.ui.v2 import history

        if self.fake is not None:
            if slot in self.slots:
                self.fake.memory = dict(self.slots[slot])
            self.device.state.program_changed()
            return True
        with history.paused():
            return bool(send_program_with_expectation(self.helper, slot, source="jdxi_checks"))

    def press_write(self, slot: str) -> None:
        if self.fake is not None:
            self.slots[slot] = dict(self.fake.memory)
            return
        print(f"\n>>> On the JD-Xi: Shift + Menu/Write, choose {slot}, Enter, Enter. Then press Enter here.")
        input()

    def close(self) -> None:
        if self.fake is None:
            try:
                self.helper.close_ports()
            except Exception:
                pass


@pytest.fixture(params=["simulated", pytest.param("hardware", marks=pytest.mark.hardware)])
def jdxi(request, app):
    """The JD-Xi, its temporary program saved before and put back after."""
    instrument = JDXi(request.param)
    assert instrument.read_all(), "the JD-Xi's program could not be read whole"
    saved = instrument.snapshot()
    yield instrument
    instrument.put_back(saved)
    instrument.close()


def test_identity_makes_it_connected(jdxi):
    """2.9: connected only once it answers as a JD-Xi."""
    from jdxi_editor.midi.io import connection as conn

    # a connection of its own, as at start-up: the app's shared one is left as it is
    # (changing it would look like a reconnection to the windows that follow it)
    shared = conn.connection_for(jdxi.helper)
    replies = []
    shared._identity_seen.connect(replies.append)
    try:
        fresh = conn.Connection(jdxi.helper, poll_ms=0)
        assert jdxi.helper.send_identity_request()
        assert wait_for(lambda: replies, 5), "no Identity Reply"
        fresh.set_state_for_tests(conn.VERIFYING)
        fresh.identity_reply(replies[0])
        assert fresh.state == conn.ONLINE, replies[0]
    finally:
        shared._identity_seen.disconnect(replies.append)


def test_the_whole_program_reads_back(jdxi):
    """MEM-05: every part of the program, confirmed."""
    snapshot = jdxi.snapshot()
    from jdxi_editor.midi.io.synth_state import part_of_address

    assert {part_of_address(key) for key in snapshot} >= set(PARTS)


def test_a_write_is_pending_until_read_back(jdxi):
    """MEM-02: what is sent is not confirmed until the JD-Xi gives it back."""
    old = jdxi.analog_byte(ANALOG_AMP_LEVEL)
    new = old - 10 if old >= 10 else old + 10
    address = bytes.fromhex("19420000")[:3] + bytes([ANALOG_AMP_LEVEL])
    assert jdxi.helper.send_raw_message(list(build_dt1(address, [new])))
    assert jdxi.device.state.pending_count() >= 1
    assert not jdxi.device.state.is_confirmed(address)
    assert jdxi.read_all()
    assert jdxi.analog_byte(ANALOG_AMP_LEVEL) == new and jdxi.device.state.is_confirmed(address)


def test_reconnection_with_nothing_changed(jdxi):
    """2.10: read again, compare: the same."""
    before = jdxi.snapshot()
    assert jdxi.read_all()
    assert parts_that_differ(before, jdxi.snapshot()) == []


def test_reconnection_with_a_part_changed_restores_it(jdxi):
    """2.11: the Analog part changed while away; Restore puts it back and checks it."""
    from jdxi_editor.ui.v2 import safety_net as sn

    before = jdxi.snapshot()
    old = before["19420000"][ANALOG_AMP_LEVEL]
    address = bytes.fromhex("19420000")[:3] + bytes([ANALOG_AMP_LEVEL])
    jdxi.helper.send_raw_message(list(build_dt1(address, [old - 10 if old >= 10 else old + 10])))
    asked = []
    net = sn.SafetyNet(lambda done: done(jdxi.read_all()), jdxi.snapshot, jdxi.send_section, lambda: True,
                       ask=lambda parts: asked.append(parts) or True)
    net.start(before)
    assert asked == [["analog"]]
    assert net.outcome == sn.RESTORED, f"{net.parts}\n{jdxi.diagnosis(before)}"
    assert jdxi.analog_byte(ANALOG_AMP_LEVEL) == old


def test_init_and_its_undo_on_the_instrument(jdxi, app):
    """6b.1: Init of the Analog part reaches the JD-Xi; one Undo brings the sound back there."""
    from unittest.mock import MagicMock

    from jdxi_editor.ui.v2 import new_sound
    from jdxi_editor.ui.v2.analog import AnalogToneEditor

    before = jdxi.snapshot()
    editor = AnalogToneEditor(jdxi.helper, MagicMock())
    try:
        assert jdxi.read_all()  # the editor shows what the JD-Xi holds (as when it opens)
        wait_for(lambda: False, 0.3)
        editor.history.reset()
        assert new_sound.init_part(editor, ask=False)
        wait_for(lambda: False, 0.5)  # the edits go out every 25 ms
        assert jdxi.read_all()
        cutoff = editor.pv("FILTER_CUTOFF")
        assert cutoff.value() == 127
        assert parts_that_differ(before, jdxi.snapshot()) == ["analog"]  # nothing else
        editor.history._sealed = True
        assert editor.history.undo()
        wait_for(lambda: False, 0.5)
        assert jdxi.read_all()
        assert parts_that_differ(before, jdxi.snapshot()) == []  # the sound before, on the JD-Xi
    finally:
        editor.close()
        editor.deleteLater()


def _write_slot(jdxi) -> str:
    if jdxi.kind == "simulated":
        return "H64"
    slot = os.environ.get("JDXI_WRITE_SLOT", "").strip().upper()
    if not slot:
        pytest.skip("set JDXI_WRITE_SLOT (a slot E01–H64 that may be overwritten) and run with -s")
    return slot


def test_save_on_the_jdxi_is_checked_by_reading_the_slot(jdxi, monkeypatch):
    """6.8: name prepared, WRITE on the JD-Xi, the slot read back: «Saved in … ✓»."""
    from jdxi_editor.ui.v2 import write_wizard as ww

    slot = _write_slot(jdxi)
    monkeypatch.setattr(ww.WriteSession, "_remember", lambda self: None)  # keep the user's library as it is
    session = ww.WriteSession(lambda done: done(jdxi.read_all()), jdxi.snapshot,
                              lambda m: bool(jdxi.helper.send_raw_message(m)), jdxi.select, [])
    prepared = []
    assert session.prepare("Check Write", prepared.append) and prepared == [True]
    jdxi.press_write(slot)
    outcome = []
    session.finished.connect(lambda saved, message: outcome.append((saved, message)))
    session.verify(slot)
    assert outcome and outcome[0][0], f"{outcome}\n{jdxi.diagnosis(session.expected)}"


def test_a_write_not_done_is_not_confirmed(jdxi, monkeypatch):
    """6.9: without the WRITE, no confirmation (simulated only: on the real JD-Xi the
    slot would have to hold something else for sure)."""
    if jdxi.kind != "simulated":
        pytest.skip("simulated only")
    from jdxi_editor.ui.v2 import write_wizard as ww

    monkeypatch.setattr(ww.WriteSession, "_remember", lambda self: None)
    jdxi.slots["H63"] = {key: 0 for key in jdxi.fake.memory}
    session = ww.WriteSession(lambda done: done(jdxi.read_all()), jdxi.snapshot,
                              lambda m: bool(jdxi.helper.send_raw_message(m)), jdxi.select, [])
    session.prepare("Not Written", lambda ok: None)
    outcome = []
    session.finished.connect(lambda saved, message: outcome.append((saved, message)))
    session.verify("H63")
    assert outcome and not outcome[0][0]
