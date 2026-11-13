"""
The edits made in the editors: undo / redo, and a warning before they are lost.

Each editor keeps an EditHistory of the values changed by the user (the values
read from the JD-Xi arrive with the signals blocked, so they are not edits).
A drag of a slider is one edit. An editor is "modified" while it has edits not
saved to a file; changing its sound from the program (a preset, a program, a
patch file, closing the program) asks first. What is done on the JD-Xi itself
cannot be stopped: the program only learns about it afterwards.
"""

from __future__ import annotations

import itertools
import time
import weakref
from contextlib import contextmanager
from typing import Callable, Iterable, Optional

from PySide6.QtCore import QObject, QSettings, QThread, Signal
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox

from jdxi_editor.i18n import tr

CONFIRM_KEY = "edits/confirm_discard"
MERGE_SECONDS = 1.0  # changes of one value closer than this are one edit (a drag)

# the parts a program change on a MIDI channel replaces
DIGITAL_1, DIGITAL_2, ANALOG, DRUMS, PROGRAM = "digital_1", "digital_2", "analog", "drums", "program"
TONE_PARTS = (DIGITAL_1, DIGITAL_2, ANALOG, DRUMS)
ALL_PARTS = TONE_PARTS + (PROGRAM,)
CHANNEL_PARTS = {0: (DIGITAL_1,), 1: (DIGITAL_2,), 2: (ANALOG,), 9: (DRUMS,), 15: ALL_PARTS}

_histories: "weakref.WeakSet[EditHistory]" = weakref.WeakSet()
_last_edited: Optional[weakref.ref] = None
_ids = itertools.count(1)
_paused = 0
save_callback: Optional[Callable[[], None]] = None  # opens "Save patch" (set by the main window)


def part_of_synth(synth_type) -> str:
    """The part key of a JDXiSynth value (Digital 1 ... Drums); PROGRAM for the rest."""
    text = str(getattr(synth_type, "value", synth_type)).upper()
    if "DIGITAL" in text:
        return DIGITAL_2 if "2" in text else DIGITAL_1
    if "ANALOG" in text:
        return ANALOG
    if "DRUM" in text:
        return DRUMS
    return PROGRAM


class _Edit:
    __slots__ = ("value", "old", "new", "time", "id")

    def __init__(self, value, old: int, new: int):
        self.value, self.old, self.new = value, old, new
        self.time = time.monotonic()
        self.id = next(_ids)


class EditHistory(QObject):
    """The user's changes to one editor's values."""

    modifiedChanged = Signal(bool)
    stateChanged = Signal()  # undo / redo became (un)available

    def __init__(self, part: str, label: str, parent=None):
        super().__init__(parent)
        self.part, self.label = part, label
        self._undo: list[_Edit] = []
        self._redo: list[_Edit] = []
        self._saved_id = 0  # the id of the last edit when saved (0: nothing)
        self._sealed = True  # the last edit is not merged with the next one
        self._replaying = False
        self._modified = False
        _histories.add(self)

    # ------------------------------------------------------------ recording
    def watch(self, values: Iterable) -> None:
        """Record the changes of these ParamValue (they keep their previous value)."""
        for pv in values:
            pv.valueChanged.connect(lambda new, pv=pv: self._record(pv, new))

    def _record(self, pv, new: int) -> None:
        global _last_edited
        if self._replaying:
            return
        old = getattr(pv, "previous", new)
        top = self._undo[-1] if self._undo else None
        if (top is not None and not self._sealed and top.value is pv
                and time.monotonic() - top.time < MERGE_SECONDS):
            top.new, top.time = new, time.monotonic()
            if top.new == top.old:  # back where it started: no edit
                self._undo.pop()
        else:
            self._undo.append(_Edit(pv, old, new))
        self._sealed = False
        self._redo.clear()
        _last_edited = weakref.ref(self)
        self._update()

    # ------------------------------------------------------------ undo / redo
    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        edit = self._undo.pop()
        self._apply(edit.value, edit.old)
        self._redo.append(edit)
        self._sealed = True
        self._update()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        edit = self._redo.pop()
        self._apply(edit.value, edit.new)
        self._undo.append(edit)
        self._sealed = True
        self._update()
        return True

    def _apply(self, pv, value: int) -> None:
        """Set the value as the user would: the controls follow and it is sent to the JD-Xi."""
        self._replaying = True
        try:
            pv.setValue(value)
        finally:
            self._replaying = False

    # ------------------------------------------------------------ state
    @property
    def modified(self) -> bool:
        return self._modified

    def mark_saved(self) -> None:
        """The values are in a file now."""
        self._saved_id = self._undo[-1].id if self._undo else 0
        self._sealed = True
        self._update()

    def reset(self) -> None:
        """A new sound: nothing to undo, nothing modified."""
        self._undo.clear()
        self._redo.clear()
        self._saved_id = 0
        self._sealed = True
        self._update()

    def _update(self) -> None:
        modified = (self._undo[-1].id if self._undo else 0) != self._saved_id
        if modified != self._modified:
            self._modified = modified
            self.modifiedChanged.emit(modified)
        self.stateChanged.emit()


# ---------------------------------------------------------------- all editors
def _alive(history) -> bool:
    """Its editor not deleted (a signal of a deleted QObject would crash)."""
    try:
        from shiboken6 import isValid
    except ImportError:  # pragma: no cover
        return True
    return history is not None and isValid(history)


def histories(parts: Iterable[str] = ALL_PARTS) -> list[EditHistory]:
    parts = set(parts)
    return [h for h in list(_histories) if _alive(h) and h.part in parts]


def last_edited() -> Optional[EditHistory]:
    found = _last_edited() if _last_edited is not None else None
    return found if _alive(found) else None


def mark_all_saved() -> None:
    for history in histories():
        history.mark_saved()


def asks_before_discarding(settings: Optional[QSettings] = None) -> bool:
    from jdxi_editor.project import __organization_name__, __program__

    settings = settings or QSettings(__organization_name__, __program__)
    return bool(settings.value(CONFIRM_KEY, True, type=bool))


def set_asks_before_discarding(on: bool, settings: Optional[QSettings] = None) -> None:
    from jdxi_editor.project import __organization_name__, __program__

    settings = settings or QSettings(__organization_name__, __program__)
    settings.setValue(CONFIRM_KEY, bool(on))


def ask(labels: list[str], action: str, parent=None) -> str:
    """'discard', 'save' or 'cancel' (a dialog; replaced in the tests)."""
    box = QMessageBox(parent or QApplication.activeWindow())
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("Unsaved changes"))
    box.setText(tr("{parts}: the changes are not saved.").format(parts=", ".join(labels)))
    box.setInformativeText(action)
    save = box.addButton(tr("Save to file…"), QMessageBox.ButtonRole.AcceptRole)
    discard = box.addButton(tr("Discard the changes"), QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    again = QCheckBox(tr("Do not ask again (Preferences can turn it back on)"))
    box.setCheckBox(again)
    box.exec()
    if again.isChecked():
        set_asks_before_discarding(False)
    clicked = box.clickedButton()
    if clicked is save:
        return "save"
    if clicked is discard:
        return "discard"
    return "cancel"


def confirm_discard(parts: Iterable[str], action: str, parent=None) -> bool:
    """Before replacing these parts' sound: True to go on (their histories start again)."""
    affected = histories(parts)
    modified = [h for h in affected if h.modified]
    if modified and asks_before_discarding():
        answer = ask([h.label for h in modified], action, parent)
        if answer == "save":
            if save_callback is not None:
                save_callback()  # the action is not done: once saved, it can be repeated
            return False
        if answer != "discard":
            return False
    for history in affected:
        history.reset()
    return True


# ---------------------------------------------------------------- program changes
@contextmanager
def paused():
    """Program changes sent without asking (e.g. by the MIDI file player)."""
    global _paused
    _paused += 1
    try:
        yield
    finally:
        _paused -= 1


def program_change_allowed(channel: int) -> bool:
    """Asked before a program change goes out on `channel` (0-15)."""
    parts = CHANNEL_PARTS.get(int(channel))
    if not parts or _paused:
        return True
    app = QApplication.instance()
    if app is None or QThread.currentThread() is not app.thread():
        return True  # not from the interface: nobody to ask
    action = (
        tr("Changing the program replaces every part's sound.")
        if parts == ALL_PARTS
        else tr("Changing the sound replaces them.")
    )
    return confirm_discard(parts, action)
