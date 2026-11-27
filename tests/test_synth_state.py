"""
What the JD-Xi holds apart from what the app shows, and the safety net when
it comes back (sound-design spec §1.2 and §3, Phase 2).

- a DT1 sent is pending, not confirmed, until read back (MEM-02)
- read back with another value: «different», not a local edit (MEM-03)
- a program change: nothing of the old program holds
- reconnection: same / kept / asked / incomplete, per part (SD-05, SD-06)
- restore: only the differing parts; «partial» when one does not come back (SD-07)
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.io.synth_memory import build_dt1
from jdxi_editor.midi.io.synth_state import SynthState, part_of_address, parts_that_differ
from jdxi_editor.ui.v2 import safety_net as sn

ANALOG = bytes.fromhex("19420000")
D1 = bytes.fromhex("19010000")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_sent_is_pending_until_read_back():
    state = SynthState()
    state.received(build_dt1(ANALOG, list(range(10))))
    assert state.is_confirmed(ANALOG, 10)
    state.sent(build_dt1(bytes.fromhex("19420003"), [55]))
    assert state.pending_count() == 1 and not state.is_confirmed(ANALOG, 10)
    assert state.confirmed.read(bytes.fromhex("19420003"), 1) == bytes([3])  # not the value sent
    state.received(build_dt1(bytes.fromhex("19420003"), [55]))
    assert state.pending_count() == 0 and state.is_confirmed(ANALOG, 10)


def test_read_back_different_is_the_jdxis_not_a_local_edit():
    state = SynthState()
    state.sent(build_dt1(bytes.fromhex("19420003"), [55]))
    state.received(build_dt1(bytes.fromhex("19420003"), [12]))
    assert state.different() == {"19420003": (55, 12)}
    assert not state.is_confirmed(bytes.fromhex("19420003"))
    state.program_changed()
    assert state.different() == {} and state.confirmed.read(ANALOG, 1) is None


def test_parts_that_differ_only_on_sections_known_in_both():
    assert part_of_address("19420000") == "analog" and part_of_address("18000200") == "program"
    before = {"19420000": b"\x01\x02", "19010000": b"\x05"}
    after = {"19420000": b"\x01\x03", "19210000": b"\x09"}  # Digital 2 never read before
    assert parts_that_differ(before, after) == ["analog"]


class Rig:
    """A JD-Xi in memory: reads fill the snapshot from its sections."""

    def __init__(self, jdxi: dict, complete=True, refuse=()):
        self.jdxi = dict(jdxi)
        self.snap = {}
        self.complete = complete
        self.refuse = set(refuse)
        self.sent = []
        self.messages = []

    def read(self, done):
        if self.complete:
            self.snap = dict(self.jdxi)
        done(self.complete)

    def send(self, key, data):
        if part_of_address(key) in self.refuse:
            return False
        self.sent.append(key)
        self.jdxi[key] = data
        return True

    def net(self, at_risk=True, answer=True):
        self.asked = []

        def ask(parts):
            self.asked.append(parts)
            return answer

        return sn.SafetyNet(self.read, lambda: dict(self.snap), self.send, lambda: at_risk,
                            ask=ask, notify=lambda text, problem: self.messages.append((text, problem)))


BEFORE = {"19420000": b"\x01\x02", "19010000": b"\x05", "18000000": b"\x07"}


def test_same_state_says_so_and_asks_nothing(app):
    rig = Rig(BEFORE)
    net = rig.net()
    net.start(BEFORE)
    assert net.outcome == sn.SAME and rig.asked == [] and rig.sent == []


def test_different_with_nothing_at_risk_keeps_the_jdxi(app):
    rig = Rig({**BEFORE, "19420000": b"\x09\x09"})
    net = rig.net(at_risk=False)
    net.start(BEFORE)
    assert net.outcome == sn.KEPT and net.parts == ["analog"] and rig.asked == [] and rig.sent == []


def test_different_with_unsaved_changes_asks_and_restores_only_those_parts(app):
    rig = Rig({**BEFORE, "19420000": b"\x09\x09", "19010000": b"\x00"})
    net = rig.net(answer=True)
    net.start(BEFORE)
    assert rig.asked == [["digital_1", "analog"]]
    assert sorted(rig.sent) == ["19010000", "19420000"]  # not the program, which is the same
    assert net.outcome == sn.RESTORED and not rig.messages[-1][1]
    assert "WRITE" in rig.messages[-1][0]


def test_keep_what_the_jdxi_has(app):
    rig = Rig({**BEFORE, "19420000": b"\x09\x09"})
    net = rig.net(answer=False)
    net.start(BEFORE)
    assert net.outcome == sn.KEPT and rig.sent == []


def test_a_restore_that_does_not_go_through_is_partial(app):
    rig = Rig({**BEFORE, "19420000": b"\x09\x09", "19010000": b"\x00"}, refuse={"analog"})
    net = rig.net()
    net.start(BEFORE)
    assert net.outcome == sn.PARTIAL and net.parts == ["analog"]
    text, problem = rig.messages[-1]
    assert problem and "Digital 1 restored" in text and "Analog not" in text


def test_an_incomplete_reading_compares_nothing(app):
    rig = Rig({**BEFORE, "19420000": b"\x09\x09"}, complete=False)
    net = rig.net()
    net.start(BEFORE)
    assert net.outcome == sn.INCOMPLETE and rig.asked == [] and rig.sent == [] and rig.messages[-1][1]


def test_reconnection_against_a_simulated_jdxi_restores_the_part_that_changed(app):
    """CON-06 on the simulated JD-Xi: reading through the real MIDI path, the
    Analog part changed while away, restored on request and read back."""
    import os
    import sys
    import time

    sys.path.insert(0, os.path.dirname(__file__))
    from test_ab_compare import FakeJDXi, pump  # the JD-Xi of the A/B tests

    from jdxi_editor.midi.io.device import device_for
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.midi.sysex.request.read_session import patch_section_requests, start_read_session

    helper = MidiIOHelper()
    device = device_for(helper)
    device.state.program_changed()
    jdxi = FakeJDXi(helper)
    jdxi.load([build_dt1(ANALOG, [i % 100 for i in range(64)])])
    requests = [rq for _l, rq in patch_section_requests()]

    def read(done):
        session = start_read_session(helper, requests, on_finished=lambda r: done(bool(r.complete)))
        assert pump(lambda: session._done, 20)

    def send(key, data):
        return bool(helper.send_raw_message(list(build_dt1(bytes.fromhex(key), list(data)))))

    pump(lambda: False, 0.3)  # what editors of earlier tests still had queued goes out first
    results = []
    read(results.append)
    assert results == [True]
    before = device.state.snapshot()
    assert before["19420000"][:3] == bytes([0, 1, 2])
    jdxi.load([build_dt1(ANALOG, [7] * 64)])  # switched off and on: another Analog tone
    net = sn.SafetyNet(read, device.state.snapshot, send, lambda: True, ask=lambda parts: parts == ["analog"])
    net.start(before)
    assert net.outcome == sn.RESTORED, net.parts
    assert jdxi.read(ANALOG, 3) == bytes([0, 1, 2])
