"""
«Save on the JD-Xi», guided and checked (sound-design spec §5, Phase 4),
against the simulated JD-Xi of the A/B tests.

- the name goes to the temporary program; the slots come from the user-program
  names, «Init Program» proposed as free (WR-01)
- a slot with a program needs a confirmation
- the check: the slot read back holds what was prepared → «Saved in E-xx ✓»,
  the slot is the reference (WR-01, WR-04)
- WRITE not done, or done elsewhere: no confirmation, the parts that differ (WR-02, WR-03)
"""

from __future__ import annotations

import os
import sys

import pytest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))

from jdxi_editor.midi.io.synth_memory import build_dt1  # noqa: E402
from jdxi_editor.midi.program.program import JDXiProgram  # noqa: E402
from jdxi_editor.ui.v2 import write_wizard as ww  # noqa: E402

ANALOG = bytes.fromhex("19420000")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class Rig:
    """The JD-Xi simulated as in the A/B tests, with user slots of its own:
    selecting a slot loads it into the temporary area (as the real one does)."""

    def __init__(self):
        from test_ab_compare import FakeJDXi, pump

        from jdxi_editor.midi.io.device import device_for
        from jdxi_editor.midi.io.helper import MidiIOHelper
        from jdxi_editor.midi.sysex.request.read_session import patch_section_requests, start_read_session

        self.pump = pump
        self.helper = MidiIOHelper()
        self.device = device_for(self.helper)
        self.device.state.program_changed()
        self.device.requests.clear()  # nothing left queued by the tests before (other windows' readings)
        self.jdxi = FakeJDXi(self.helper)
        self.jdxi.load([build_dt1(ANALOG, [i % 100 for i in range(64)])])
        self.slots: dict = {}  # slot -> the temporary area's memory saved there
        self.selected = []
        requests = [rq for _l, rq in patch_section_requests()]

        def read(done):
            session = start_read_session(self.helper, requests, on_finished=lambda r: done(bool(r.complete)))
            assert pump(lambda: session._done, 20)

        def select(slot):
            self.selected.append(slot)
            if slot in self.slots:
                self.jdxi.memory = dict(self.slots[slot])
            self.device.state.program_changed()
            return True

        programs = [JDXiProgram(id="E01", name="Dark Pad"), JDXiProgram(id="E02", name="Init Program"),
                    JDXiProgram(id="E03", name="My Lead")]
        self.session = ww.WriteSession(read, self.device.state.snapshot,
                                       lambda m: bool(self.helper.send_raw_message(m)), select, programs)

    def write(self, slot):
        """The user's WRITE on the JD-Xi: the temporary area kept in *slot*."""
        self.slots[slot] = dict(self.jdxi.memory)


def test_slots_free_proposed_and_confirmation(app):
    rig = Rig()
    session = rig.session
    assert session.proposed() == "E02"  # «Init Program»
    assert session.needs_confirmation("E01") and not session.needs_confirmation("E02")
    assert not session.needs_confirmation("F10")  # nothing known: free
    assert ww.clean_name("Bass ½ très long name") == "Bass   tr s "  # ASCII only, 12 characters
    assert len(ww.clean_name("x")) == 12


def test_a_write_done_in_the_slot_is_confirmed(app, monkeypatch):
    from jdxi_editor.ui.v2 import history
    from jdxi_editor.ui.v2.context import sound_context

    monkeypatch.setattr(ww.WriteSession, "_remember", lambda self: sound_context().slot_saved(self.slot))
    rig = Rig()
    session = rig.session
    prepared = []
    assert session.prepare("Night Bass", prepared.append)
    assert prepared == [True] and "18000000" in session.expected
    assert session.expected["18000000"][:12] == b"Night Bass  "  # the name went to the temporary program
    rig.write("E02")
    outcome = []
    session.finished.connect(lambda saved, message: outcome.append((saved, message)))
    session.verify("E02")
    assert outcome == [(True, "Saved in E02 ✓")] and rig.selected == ["E02"]
    assert sound_context().saved_slot == "E02"
    _ = history  # (the real _remember also marks the editors saved)


def test_no_write_or_another_slot_is_not_confirmed(app, monkeypatch):
    monkeypatch.setattr(ww.WriteSession, "_remember", lambda self: None)
    rig = Rig()
    session = rig.session
    session.prepare("Night Bass", lambda ok: None)
    rig.slots["E02"] = {k: 0 for k in rig.jdxi.memory}  # E02 holds another program: no WRITE there
    outcome = []
    session.finished.connect(lambda saved, message: outcome.append((saved, message)))
    session.verify("E02")
    assert outcome and not outcome[0][0]
    assert "Not saved in E02" in outcome[0][1] and "Analog" in outcome[0][1]


def test_the_dialog_walks_the_steps(app, monkeypatch):
    monkeypatch.setattr(ww.WriteSession, "_remember", lambda self: None)
    rig = Rig()
    dialog = ww.WriteDialog(rig.session, "Old Name")
    assert dialog.chosen_slot() == "E02" and dialog.name_edit.text() == "Old Name"
    dialog.name_edit.setText("Night Bass")
    dialog.prepare()
    assert dialog.pages.currentIndex() == 1 and "E02" in dialog.instructions.text()
    assert "not saved yet" in dialog.instructions.text()
    rig.write("E02")
    dialog.check()
    assert dialog.pages.currentIndex() == 2 and "Saved in E02" in dialog.result_label.text()
    # a slot holding a program asks first; «Cancel» keeps the dialog on its first page
    dialog2 = ww.WriteDialog(rig.session, "x")
    dialog2.slot_combo.setCurrentIndex(dialog2.slot_combo.findData("E01"))
    monkeypatch.setattr(dialog2, "confirm_overwrite", lambda slot: False)
    dialog2.prepare()
    assert dialog2.pages.currentIndex() == 0
