"""
«Save on the JD-Xi», guided (sound-design spec §5, Phase 4).

The real save is the JD-Xi's WRITE (only whole programs, into E–H): the app
prepares it, guides it and checks it.

1. the name (12 characters) goes to the temporary program: «prepared, not
   yet saved»
2. the slot: E–H from the user-program names the app knows (they may be old:
   the date of their last update is shown); slots named «Init Program» /
   «Init Tone» are proposed as probably free, any other one can be chosen
3. a slot that holds a program needs an explicit confirmation
4. what to do on the JD-Xi, step by step; the app waits for «Done»
5. the check: the temporary program is read first (what should be saved),
   then the slot is selected and read back: the same → «Saved in E-13 ✓»,
   otherwise no confirmation, with the parts that differ
6. a backup on file can be saved alongside
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.io.synth_state import parts_that_differ

USER_BANKS = "EFGH"
# a slot holding the init program is probably free; a slot with no name known
# is NOT: the database may be old or incomplete, and the JD-Xi cannot be asked
# without loading the slot (which would replace the sound being saved)
FREE_NAMES = ("init program", "init tone")
NAME_ADDRESS = bytes.fromhex("18000000")  # Program Common: the name, 12 characters
NAME_LENGTH = 12


def clean_name(name: str) -> str:
    """12 printable ASCII characters, padded with spaces (as the JD-Xi keeps them)."""
    text = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in (name or ""))[:NAME_LENGTH]
    return text.ljust(NAME_LENGTH)


def is_free(name: Optional[str]) -> bool:
    return (name or "").strip().lower() in FREE_NAMES


class WriteSession(QObject):
    """The steps of one save, without windows (the dialog drives it).

    *read(done)* reads the whole temporary program and calls done(complete);
    *snapshot()* gives the confirmed sections; *send(message)* sends a MIDI
    message; *select(slot)* selects a program on the JD-Xi.
    """

    finished = Signal(bool, str)  # saved, message

    def __init__(self, read: Callable, snapshot: Callable[[], dict], send: Callable[[list], bool],
                 select: Callable[[str], bool], programs: Optional[list] = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._read, self._snapshot, self._send, self._select = read, snapshot, send, select
        self.programs = {p.id.upper(): p for p in (programs or []) if getattr(p, "id", None)}
        self.name = ""
        self.slot = ""
        self.expected: dict = {}
        self.saved = False
        self.message = ""

    # ------------------------------------------------------------- the slot
    def slots(self) -> list[tuple[str, str, bool]]:
        """(slot, name known, probably free) for E01…H64."""
        found = []
        for bank in USER_BANKS:
            for number in range(1, 65):
                slot = f"{bank}{number:02d}"
                program = self.programs.get(slot)
                name = (getattr(program, "name", "") or "").strip()
                found.append((slot, name, is_free(name)))
        return found

    def proposed(self) -> str:
        """The first slot that looks free, else E01."""
        return next((slot for slot, _n, free in self.slots() if free), "E01")

    def needs_confirmation(self, slot: str) -> bool:
        """Every slot but one known to hold the init program (unknown ≠ free)."""
        return not is_free(getattr(self.programs.get(slot.upper()), "name", ""))

    def known_name(self, slot: str) -> str:
        """The name the database has for *slot* ("" when nothing is known)."""
        return (getattr(self.programs.get(slot.upper()), "name", "") or "").strip()

    # ------------------------------------------------------------- the steps
    def prepare(self, name: str, done: Callable[[bool], None]) -> bool:
        """Send the name to the temporary program, then read what will be saved."""
        from jdxi_editor.midi.io.synth_memory import build_dt1

        self.name = clean_name(name)
        if not self._send(list(build_dt1(NAME_ADDRESS, [ord(c) for c in self.name]))):
            return False

        def read_done(complete: bool) -> None:
            self.expected = self._snapshot() if complete else {}
            done(bool(complete and self.expected))

        self._read(read_done)
        return True

    def verify(self, slot: str) -> None:
        """After the WRITE: select *slot* (it stays selected) and compare what it holds."""
        self.slot = slot.upper()
        if not self._select(self.slot):
            self._end(False, tr("Not confirmed: {slot} could not be selected on the JD-Xi.").format(slot=self.slot))
            return

        def read_done(complete: bool) -> None:
            if not complete:
                self._end(False, tr("Not confirmed: {slot} could not be read back whole. "
                                    "It may be saved: select it on the JD-Xi to check.").format(slot=self.slot))
                return
            parts = parts_that_differ(self.expected, self._snapshot(), self.expected.keys())
            if parts:
                from jdxi_editor.ui.v2.safety_net import part_label

                self._end(False, tr("Not saved in {slot}: it holds something else ({parts}). "
                                    "Your sound is still only temporary.").format(
                    slot=self.slot, parts=", ".join(part_label(p) for p in parts)))
                return
            self._end(True, tr("Saved in {slot} ✓").format(slot=self.slot))

        self._read(read_done)

    def _end(self, saved: bool, message: str) -> None:
        self.saved, self.message = saved, message
        if saved:
            self._remember()
        self.finished.emit(saved, message)

    def _remember(self) -> None:
        """The slot is the reference now; the user-program list gets the new name."""
        try:
            from jdxi_editor.ui.v2 import history
            from jdxi_editor.ui.v2.context import sound_context

            history.mark_all_saved()
            context = sound_context()
            context.slot_saved(self.slot)
            context.set_program_name(self.name.strip())
        except Exception:
            pass
        try:
            from dataclasses import replace

            from jdxi_editor.midi.io.input_handler import add_or_replace_program_and_save
            from jdxi_editor.midi.program.program import JDXiProgram

            old = self.programs.get(self.slot)
            program = replace(old, name=self.name.strip()) if old is not None else JDXiProgram(
                id=self.slot, name=self.name.strip())
            add_or_replace_program_and_save(program)
        except Exception:
            pass


def user_programs_updated() -> str:
    """When the user-program names were last read from the JD-Xi ('' unknown)."""
    try:
        from jdxi_editor.ui.programs.database import get_database

        with get_database()._get_connection() as connection:
            row = connection.execute(
                "SELECT MAX(updated_at) FROM programs WHERE UPPER(SUBSTR(id, 1, 1)) IN ('E','F','G','H')"
            ).fetchone()
        return str(row[0])[:16] if row and row[0] else ""
    except Exception:
        return ""


def session_for(helper, parent: Optional[QObject] = None) -> WriteSession:
    """A WriteSession on the real JD-Xi of *helper*."""
    from jdxi_editor.midi.io.synth_state import state_of
    from jdxi_editor.midi.sysex.request.read_session import patch_section_requests, start_read_session
    from jdxi_editor.ui.midi.selection_info import send_program_with_expectation
    from jdxi_editor.ui.v2 import history

    state = state_of(helper)

    def read(done) -> None:
        requests = [rq for _label, rq in patch_section_requests()]
        start_read_session(helper, requests, on_finished=lambda result: done(bool(result.complete)), parent=parent)

    def select(slot: str) -> bool:
        with history.paused():  # nothing to ask: after the WRITE it holds the same program
            return bool(send_program_with_expectation(helper, slot, source="write_check"))

    try:
        from jdxi_editor.ui.programs.database import get_database

        db = get_database()
        programs = [p for bank in USER_BANKS for p in db.get_programs_by_bank(bank)]
    except Exception:
        programs = []
    return WriteSession(read, state.snapshot if state is not None else dict,
                        lambda message: bool(helper.send_raw_message(message)), select, programs, parent)


# ------------------------------------------------------------------ the dialog
class WriteDialog(QDialog):
    """The guided save, in three pages: name and slot · on the JD-Xi · the check."""

    def __init__(self, session: WriteSession, current_name: str = "", parent: Optional[QWidget] = None,
                 backup: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.session = session
        self.backup = backup
        self.setWindowTitle(tr("Save on the JD-Xi"))
        self.setMinimumWidth(520)
        self.pages = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)
        self.pages.addWidget(self._first_page(current_name))
        self.pages.addWidget(self._jdxi_page())
        self.pages.addWidget(self._check_page())
        session.finished.connect(self._checked)

    # -- 1: name and slot
    def _first_page(self, current_name: str) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.addWidget(_note(tr("The JD-Xi keeps a program only with its WRITE, in the user banks E–H. "
                               "Here you name it and choose where; then you press WRITE on the JD-Xi "
                               "and the app checks that it is there.")))
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Name:")))
        self.name_edit = QLineEdit(current_name.strip())
        self.name_edit.setMaxLength(NAME_LENGTH)
        row.addWidget(self.name_edit, 1)
        col.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Slot:")))
        self.slot_combo = QComboBox()
        for slot, name, free in self.session.slots():
            label = f"{slot}  {name}" if name else f"{slot}  " + tr("(content not known)")
            if free:
                label += "  — " + tr("probably free")
            self.slot_combo.addItem(label, slot)
        index = self.slot_combo.findData(self.session.proposed())
        self.slot_combo.setCurrentIndex(max(0, index))
        row.addWidget(self.slot_combo, 1)
        col.addLayout(row)
        updated = user_programs_updated()
        col.addWidget(_note(
            (tr("Names as read on {date} (JD-Xi › Read the user programs): they may be old.").format(date=updated)
             if updated else tr("Names as last read from the JD-Xi (JD-Xi › Read the user programs): "
                                "they may be old."))))
        self.prepared = _note("")
        col.addWidget(self.prepared)
        buttons = QHBoxLayout()
        if self.backup is not None:
            backup = QPushButton(tr("Also save a backup file…"))
            backup.clicked.connect(self.backup)
            buttons.addWidget(backup)
        buttons.addStretch()
        cancel = QPushButton(tr("Cancel"))
        cancel.clicked.connect(self.reject)
        self.next_button = QPushButton(tr("Next"))
        self.next_button.setDefault(True)
        self.next_button.clicked.connect(self.prepare)
        buttons.addWidget(cancel)
        buttons.addWidget(self.next_button)
        col.addLayout(buttons)
        return page

    def chosen_slot(self) -> str:
        return self.slot_combo.currentData() or "E01"

    def confirm_overwrite(self, slot: str) -> bool:
        """A slot that holds a program, or whose content is not known: say
        which, and ask (not the default button)."""
        name = self.session.known_name(slot)
        if name:
            text = tr("Replace {slot} «{name}»? The program in it is lost.").format(slot=slot, name=name)
        else:
            text = tr("What {slot} holds is not known (it is not in the user program database): "
                      "if it holds a program, that program is lost. Write in {slot} anyway?").format(slot=slot)
        box = QMessageBox(QMessageBox.Icon.Warning, tr("Replace a program"), text, parent=self)
        replace = box.addButton(tr("Replace {slot}").format(slot=slot), QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is replace

    def prepare(self) -> None:
        slot = self.chosen_slot()
        if self.session.needs_confirmation(slot) and not self.confirm_overwrite(slot):
            return
        self.next_button.setEnabled(False)
        self.prepared.setText(tr("Preparing: sending the name and reading the program…"))
        if not self.session.prepare(self.name_edit.text(), self._prepared):
            self.next_button.setEnabled(True)
            self.prepared.setText(tr("The name could not be sent: is the JD-Xi connected?"))

    def _prepared(self, ok: bool) -> None:
        self.next_button.setEnabled(True)
        if not ok:
            self.prepared.setText(tr("The program could not be read whole: try again."))
            return
        slot = self.chosen_slot()
        self.instructions.setText(tr(
            "Name prepared on the JD-Xi: <b>it is not saved yet</b>.<br><br>"
            "On the JD-Xi:<br>"
            "1. press <b>Shift</b> + <b>Menu/Write</b><br>"
            "2. with Program [-] [+] choose <b>{slot}</b><br>"
            "3. press <b>Enter</b>, then <b>Enter</b> again to confirm<br><br>"
            "Then press Done here: the app selects {slot} and checks it.").format(slot=slot))
        self.pages.setCurrentIndex(1)

    # -- 2: on the JD-Xi
    def _jdxi_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        self.instructions = QLabel()
        self.instructions.setTextFormat(Qt.TextFormat.RichText)
        self.instructions.setWordWrap(True)
        col.addWidget(self.instructions)
        col.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(tr("Cancel"))
        cancel.clicked.connect(self.reject)
        self.done_button = QPushButton(tr("Done"))
        self.done_button.setDefault(True)
        self.done_button.clicked.connect(self.check)
        buttons.addWidget(cancel)
        buttons.addWidget(self.done_button)
        col.addLayout(buttons)
        return page

    def check(self) -> None:
        self.result_label.setText(tr("Checking {slot}…").format(slot=self.chosen_slot()))
        self.pages.setCurrentIndex(2)
        self.session.verify(self.chosen_slot())

    # -- 3: the check
    def _check_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 14px;")
        col.addWidget(self.result_label)
        col.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.again_button = QPushButton(tr("Check again"))
        self.again_button.clicked.connect(self.check)
        self.again_button.hide()
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.accept)
        buttons.addWidget(self.again_button)
        buttons.addWidget(close)
        col.addLayout(buttons)
        return page

    def _checked(self, saved: bool, message: str) -> None:
        colour = "#6fcf97" if saved else "#f2994a"
        self.result_label.setText(f"<span style='color:{colour}'>{message}</span>")
        self.again_button.setVisible(not saved)


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #a3a6ad; font-size: 12px;")
    return label
