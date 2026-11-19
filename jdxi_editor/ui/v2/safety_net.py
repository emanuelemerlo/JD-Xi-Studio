"""
The safety net when the JD-Xi comes back (sound-design spec §3, Phase 2).

After a disconnection (cable out, JD-Xi switched off and on), the whole
program is read and compared with what was confirmed before:

    same                          «reconnected, nothing changed»
    different, unsaved changes    the parts that differ, and a question:
                                  Restore on the JD-Xi / Keep what the JD-Xi has
    different, nothing at risk    what the JD-Xi has is kept, with a short notice
    reading incomplete            no comparison, no restore: read again

Restoring sends only the differing parts' sections, then reads them back:
the outcome is given per part («partial» when one did not come back).
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from jdxi_editor.i18n import tr
from jdxi_editor.midi.io.synth_state import PART_NAMES, part_of_address, parts_that_differ

SAME = "same"
KEPT = "kept"
ASKED = "asked"
INCOMPLETE = "incomplete"
RESTORED = "restored"
PARTIAL = "partial"


def part_label(part: str) -> str:
    return tr(PART_NAMES.get(part, part))


class SafetyNet(QObject):
    """One reconnection: read, compare, and (if asked) restore.

    *read(on_done)* reads every section and calls on_done(complete: bool);
    *snapshot()* is what the JD-Xi confirmed (address hex -> bytes);
    *send(address_hex, data)* writes a section back; *at_risk()* says whether
    changes not saved anywhere would be lost.
    """

    finished = Signal(str, list)  # outcome, parts

    def __init__(self, read: Callable[[Callable[[bool], None]], None], snapshot: Callable[[], dict],
                 send: Callable[[str, bytes], bool], at_risk: Callable[[], bool],
                 parent: Optional[QWidget] = None, ask: Optional[Callable[[list], bool]] = None,
                 notify: Optional[Callable[[str, bool], None]] = None):
        super().__init__(parent)
        self._read = read
        self._snapshot = snapshot
        self._send = send
        self._at_risk = at_risk
        self._parent = parent
        self._ask = ask or self._ask_with_a_box
        self._notify = notify or (lambda text, problem: None)
        self.before: dict = {}
        self.outcome = ""
        self.parts: list = []

    # ------------------------------------------------------------- the steps
    def start(self, before: Optional[dict] = None) -> None:
        """*before*: the confirmed state from before the disconnection."""
        self.before = dict(before if before is not None else self._snapshot())
        self._read(self._compared)

    def _compared(self, complete: bool) -> None:
        if not complete:
            self._end(INCOMPLETE, [], tr("The JD-Xi is back, but its reading is incomplete: nothing compared "
                                         "or restored. Read again (or wait for the next reading)."), True)
            return
        after = self._snapshot()
        parts = parts_that_differ(self.before, after)
        if not parts:
            self._end(SAME, [], tr("Reconnected: the JD-Xi holds what it held before."), False)
            return
        names = ", ".join(part_label(p) for p in parts)
        if not self._at_risk():
            self._end(KEPT, parts, tr("The JD-Xi holds something else now ({parts}): that is shown.").format(
                parts=names), False)
            return
        if self._ask(parts):
            self._restore(parts)
        else:
            self._end(KEPT, parts, tr("Kept what the JD-Xi holds now ({parts}).").format(parts=names), False)

    def _restore(self, parts: list) -> None:
        sections = {key: data for key, data in self.before.items() if part_of_address(key) in parts}
        failed_parts = set()
        for key, data in sorted(sections.items()):
            if not self._send(key, data):
                failed_parts.add(part_of_address(key))

        def checked(complete: bool) -> None:
            after = self._snapshot()
            still = set(parts_that_differ(self.before, after, sections)) | failed_parts
            if not complete:
                still |= set(parts)
            done = [p for p in parts if p not in still]
            if not still:
                self._end(RESTORED, parts, tr("Restored on the JD-Xi: {parts}. It is temporary again: "
                                              "keep it with WRITE.").format(
                    parts=", ".join(part_label(p) for p in parts)), False)
            else:
                self._end(PARTIAL, sorted(still), tr("Partial restore: {done} restored, {not_done} not.").format(
                    done=", ".join(part_label(p) for p in done) or tr("nothing"),
                    not_done=", ".join(part_label(p) for p in parts if p in still)), True)

        self._read(checked)

    def _end(self, outcome: str, parts: list, text: str, problem: bool) -> None:
        self.outcome, self.parts = outcome, parts
        self._notify(text, problem)
        self.finished.emit(outcome, parts)

    # ------------------------------------------------------------- the question
    def _ask_with_a_box(self, parts: list) -> bool:
        box = QMessageBox(self._parent)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("JD-Xi reconnected"))
        box.setText(tr("The JD-Xi is back with different settings in: {parts}.\n\n"
                       "The changes you had not saved would be lost. Send them back to the JD-Xi?").format(
            parts=", ".join(part_label(p) for p in parts)))
        restore = box.addButton(tr("Restore on the JD-Xi"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(tr("Keep what the JD-Xi has"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(restore)
        box.exec()
        return box.clickedButton() is restore
