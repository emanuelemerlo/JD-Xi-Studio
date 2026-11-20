"""
Where the user is working and what is saved where (sound-design spec §4, Phase 3).

One line at the top of the tone editors and of the Programs page:

    Program A11 «CARONDO» › Analog › tone «Springer» · origin: preset A-05 · modified, temporary

- origin: where the part's sound came from (it does not change with edits):
  a program, a preset, a recipe, a file, A/B, Init
- state, against the current reference (the last load or save):
  original / modified, temporary (sent to the JD-Xi, not kept) / modified,
  not sent (Off-line) / saved to file «…» / saved in E-12
"""

from __future__ import annotations

import weakref
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel, QWidget

from jdxi_editor.i18n import tr

PARTS = ("digital_1", "digital_2", "analog", "drums")


class SoundContext(QObject):
    """The program and the parts' origins, for every window (one per app)."""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.program_id = ""
        self.program_name = ""
        self.origins: dict[str, str] = {}  # part -> origin text
        self.saved_file = ""  # the last file loaded or saved (the reference)
        self.saved_slot = ""  # a program slot written and verified (Phase 4)

    # ------------------------------------------------------------- changes
    def program_loaded(self, program_id: str, name: str = "") -> None:
        """A program on the JD-Xi: it is the reference and every part's origin."""
        self.program_id = (program_id or "").upper()
        if name:
            self.program_name = name
        elif program_id:
            self.program_name = ""
        self.origins = {part: tr("program {program}").format(program=self.program_id) for part in PARTS}
        self.saved_file = ""
        self.saved_slot = ""
        self.changed.emit()

    def set_program_name(self, name: str) -> None:
        if name and name != self.program_name:
            self.program_name = name
            self.changed.emit()

    def part_origin(self, part: str, origin: str) -> None:
        """*part*'s sound now comes from *origin* (a preset, a recipe, A/B, Init)."""
        if part in PARTS and origin:
            self.origins[part] = origin
            self.changed.emit()

    def file_saved(self, path: str, loaded: bool = False) -> None:
        """Everything is in *path* now (saved, or loaded from it): the new
        reference, so a slot saved before (maybe with another sound) is not
        shown any more."""
        self.saved_file = str(path)
        self.saved_slot = ""
        if loaded:
            self.origins = {part: tr("file «{name}»").format(name=Path(path).name) for part in PARTS}
        self.changed.emit()

    def slot_saved(self, slot: str) -> None:
        """The program is in *slot* now: the new reference (the last save wins)."""
        self.saved_slot = slot
        self.saved_file = ""
        self.program_id = slot
        self.changed.emit()

    # -------------------------------------------------------------- texts
    def program_text(self) -> str:
        if not self.program_id:
            return tr("No program loaded")
        if self.program_name:
            return tr("Program {program} «{name}»").format(program=self.program_id, name=self.program_name)
        return tr("Program {program}").format(program=self.program_id)

    def state_text(self, modified: bool, online: bool) -> str:
        if modified:
            return tr("modified, temporary") if online else tr("modified, not sent (Off-line)")
        if self.saved_slot:
            return tr("saved in {slot}").format(slot=self.saved_slot)
        if self.saved_file:
            return tr("saved to file «{name}»").format(name=Path(self.saved_file).name)
        return tr("original")


_context: Optional[SoundContext] = None


def sound_context() -> SoundContext:
    global _context
    if _context is None:
        _context = SoundContext()
    return _context


PART_LABELS = {"digital_1": "Digital 1", "digital_2": "Digital 2", "analog": "Analog", "drums": "Drums"}


def part_label(part: str) -> str:
    return {"digital_1": tr("Digital 1"), "digital_2": tr("Digital 2"),
            "analog": tr("Analog"), "drums": tr("Drums")}.get(part, part)


class ContextRow(QLabel):
    """The context line of one editor (*editor* None: the Programs page)."""

    def __init__(self, editor: Optional[QWidget] = None, helper=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("v2ContextRow")
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("QLabel#v2ContextRow { color: #a3a6ad; font-size: 12px; padding: 0 2px; }")
        self._editor = weakref.ref(editor) if editor is not None else (lambda: None)
        self._helper = helper
        context = sound_context()
        context.changed.connect(self.refresh)
        history = getattr(editor, "history", None)
        if history is not None:
            history.modifiedChanged.connect(lambda _m: self.refresh())
        name_field = getattr(editor, "name_field", None)
        if name_field is not None:
            name_field.textChanged.connect(lambda _t: self.refresh())
        self._connection = None
        if helper is not None:
            from jdxi_editor.midi.io.connection import connection_for

            self._connection = connection_for(helper)
            if self._connection is not None:
                self._connection.changed.connect(lambda _s: self.refresh())
        QTimer.singleShot(0, self.refresh)  # the name field is built after the row
        self.refresh()

    def part(self) -> str:
        editor = self._editor()
        history = getattr(editor, "history", None)
        return getattr(history, "part", "") if history is not None else ""

    def _modified(self) -> bool:
        editor = self._editor()
        if editor is not None:
            history = getattr(editor, "history", None)
            return bool(history is not None and history.modified)
        from jdxi_editor.ui.v2 import history

        return any(h.modified for h in history.histories())

    def _online(self) -> bool:
        return self._connection is None or self._connection.can_talk()

    def plain_text(self) -> str:
        """The line without markup (for tests and tooltips)."""
        context = sound_context()
        bits = [context.program_text()]
        part = self.part()
        editor = self._editor()
        if part in PARTS:
            bits[0] += f" › {part_label(part)}"
            name_field = getattr(editor, "name_field", None)
            tone = name_field.text().strip() if name_field is not None else ""
            if tone:
                bits[0] += " › " + tr("tone «{name}»").format(name=tone)
            origin = context.origins.get(part)
            if origin:
                bits.append(tr("origin: {origin}").format(origin=origin))
        bits.append(context.state_text(self._modified(), self._online()))
        return " · ".join(bits)

    def refresh(self) -> None:
        try:
            text = self.plain_text()
        except RuntimeError:  # the editor is gone
            return
        head, _, rest = text.partition(" · ")
        state = text.rsplit(" · ", 1)[-1]
        middle = rest[: -len(state)].rstrip(" ·") if rest.endswith(state) else rest
        colour = "#f2994a" if self._modified() else "#6fcf97"
        html = f"<b style='color:#e6e8eb'>{_esc(head)}</b>"
        if middle:
            html += f" · {_esc(middle)}"
        html += f" · <b style='color:{colour}'>{_esc(state)}</b>"
        self.setText(html)
        self.setToolTip(tr("Where you are working and what is saved where"))


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
