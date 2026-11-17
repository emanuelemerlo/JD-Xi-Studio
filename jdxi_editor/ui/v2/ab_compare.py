"""
A/B compare: two snapshots of one part's Tone, to switch between while playing.

For Digital 1, Digital 2 and Analog (the tone editors' top bar: A | B ▾):

- Capture A / B takes a photo of the whole Tone (every block of the editor, as
  DT1 messages). With the JD-Xi connected the Tone is read again first (RQ1)
  and the photo is taken only from a complete answer, after the editor's own
  changes have gone out; without it the editor's values are taken and the
  photo is marked "local".
- Recall A / B sends the photo's DT1s, reads the Tone back and shows it only
  when the JD-Xi holds exactly the photo: a failed send, a missing answer or
  other values leave nothing "active" and say the JD-Xi's state is uncertain.
  Only this part's Tone blocks are sent: the other parts, the effects and the
  program stay as they are, and so does the channel the keys play on.
- The photos are copies: editing (here or on the JD-Xi) changes the current
  state only, shown as "modified" against the photo recalled last.
- Save A / B / both writes a .syx of the part (the Import of the editors reads
  it) with the name given, written in the Tone Name.
- The photos are kept per part in ~/.jdxi_studio/ab_compare and come back at
  start, but nothing is sent until A or B is pressed. After a program change
  (or a restart) recalling asks first: the photo was taken with another
  program around this part.

Undo / Redo / Reload are untouched: a recall arrives as values from the
JD-Xi, which the edit history already handles (the steps on them are dropped).
"""

from __future__ import annotations

import json
import weakref
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Sequence

from decologr import Decologr as log
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QToolButton,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.project import __data_name__

SCHEMA_VERSION = 1  # the photo's format; with the blocks' layout it must match the editor's
SLOTS = ("A", "B")
NAME_LENGTH = 12
READ_TIMEOUT_MS = 3000
CHECK_DELAY_MS = 150  # "modified" is worked out this long after the last change
SUPPORTED_PARTS = ("digital_1", "digital_2", "analog")
PART_NAMES = {"digital_1": "Digital 1", "digital_2": "Digital 2", "analog": "Analog"}

_epoch = 0  # program changes seen (on the program channel), sent or received
_watched_helpers: "weakref.WeakSet" = weakref.WeakSet()


def store_dir() -> Path:
    """Where the photos are kept (the tests point it elsewhere)."""
    return Path.home() / f".{__data_name__}" / "ab_compare"


def program_epoch() -> int:
    return _epoch


def program_changed() -> None:
    """Another program around the parts: the photos' recall asks first."""
    global _epoch
    _epoch += 1


def _watch_program_changes(helper) -> None:
    """Count the program changes on the program channel, in and out, once per helper."""
    if helper is None or helper in _watched_helpers:
        return
    try:
        _watched_helpers.add(helper)
    except TypeError:
        return
    from jdxi_editor.midi.io import program_channel

    def is_program_change(message) -> bool:
        if getattr(message, "type", None) == "program_change":
            return message.channel == program_channel.channel()
        try:
            data = list(message)
        except TypeError:
            return False
        return bool(data) and int(data[0]) == 0xC0 | program_channel.channel()

    for name in ("midi_message_incoming", "midi_message_outgoing"):
        signal = getattr(helper, name, None)
        if signal is not None:
            signal.connect(lambda message: program_changed() if is_program_change(message) else None)


def part_of(editor) -> Optional[str]:
    from jdxi_editor.ui.v2.history import part_of_synth

    synth = getattr(editor, "SYNTH_TYPE", None)
    if synth is None:
        return None
    part = part_of_synth(synth)
    return part if part in SUPPORTED_PARTS else None


def supports(editor) -> bool:
    return part_of(editor) is not None


def layout_of(editor) -> list:
    """The editor's blocks: [address hex, size] (what a photo must match)."""
    return [
        [bytes(block.address_bytes()).hex(), block.size()]
        for block in editor.blocks
        if block.size() and block.export
    ]


def _connected(helper) -> bool:
    """Both ports open: a recall needs to send and to read back."""
    for name in ("midi_out", "midi_in"):
        port = getattr(helper, name, None)
        if port is None:
            return False
        is_open = getattr(port, "is_port_open", None)
        try:
            if callable(is_open) and not is_open():
                return False
        except Exception:
            return False
    return True


# ---------------------------------------------------------------- photos
@dataclass
class Snapshot:
    slot: str
    part: str  # digital_1 / digital_2 / analog: the hardware part
    tone_address: str  # its Temporary Tone, e.g. "19010000"
    layout: list  # [[address hex, size], ...] of the blocks
    blocks: list  # the DT1 messages, hex (F0 ... F7), one per block
    taken_at: str  # local date and time, ISO
    name: str  # the Tone Name in the photo
    source: str = "jdxi"  # "jdxi" (read from it) or "local" (the editor's values)
    schema: int = SCHEMA_VERSION
    epoch: Optional[int] = field(default=None)  # program context; None once reloaded from disk

    def dt1s(self) -> list[bytes]:
        return [bytes.fromhex(b) for b in self.blocks]

    def complete(self) -> bool:
        """Every block of the layout present, whole, with a valid checksum."""
        if len(self.blocks) != len(self.layout):
            return False
        try:
            messages = self.dt1s()
        except ValueError:
            return False
        for message, (address, size) in zip(messages, self.layout):
            if len(message) != 14 + size or message[0] != 0xF0 or message[-1] != 0xF7:
                return False
            if message[7] != 0x12 or message[8:12].hex() != address:
                return False
            body = message[8:-2]
            if (sum(body) + message[-2]) % 128:
                return False
        return True

    def problem_for(self, editor) -> Optional[str]:
        """Why this photo cannot be recalled in *editor*, or None."""
        if self.schema != SCHEMA_VERSION:
            return tr("it was taken with another version of JD-Xi Studio (format {theirs}, this one reads {ours})").format(
                theirs=self.schema, ours=SCHEMA_VERSION)
        if self.part != part_of(editor):
            return tr("it belongs to {part}").format(part=tr(PART_NAMES.get(self.part, self.part)))
        if self.layout != layout_of(editor):
            return tr("its parameters do not match this editor's")
        if not self.complete():
            return tr("it is incomplete or damaged")
        return None

    def raw_values(self, editor) -> dict:
        """spec -> raw MIDI value, as the photo holds them."""
        from jdxi_editor.ui.v2.framework import decode_dt1

        values = {}
        for message in self.dt1s():
            values.update(dict(decode_dt1(editor.blocks, message)))
        return values

    def with_name(self, editor, name: str) -> list[bytes]:
        """The photo's DT1s with *name* as Tone Name (12 characters, spaces after)."""
        from jdxi_editor.midi.io.synth_memory import build_dt1
        from jdxi_editor.ui.v2.framework import seven_bit

        name = clean_name(name).ljust(NAME_LENGTH)
        specs = [editor.spec(f"TONE_NAME_{i + 1}") for i in range(NAME_LENGTH)]
        block = editor.block_of[specs[0]]
        target = bytes(block.address_bytes()).hex()
        out = []
        for message in self.dt1s():
            if message[8:12].hex() == target:
                data = bytearray(message[12:-2])
                for spec, char in zip(specs, name):
                    data[seven_bit(spec.offset)] = ord(char)
                message = build_dt1(list(message[8:12]), data)
            out.append(bytes(message))
        return out


def clean_name(name: str) -> str:
    """A Tone Name: printable ASCII, 12 characters at most."""
    text = "".join(c if 32 <= ord(c) <= 126 else "?" for c in (name or "").strip())
    return text[:NAME_LENGTH]


def name_from_raw(editor, raw: dict) -> str:
    chars = []
    for i in range(NAME_LENGTH):
        try:
            value = raw.get(editor.spec(f"TONE_NAME_{i + 1}"))
        except KeyError:
            return ""
        chars.append(chr(value) if value and 32 <= value <= 126 else " ")
    return "".join(chars).rstrip()


def take_snapshot(editor, slot: str, source: str) -> Snapshot:
    """A copy of the editor's whole Tone now (its blocks as DT1s)."""
    from jdxi_editor.ui.v2.framework import decode_dt1

    messages = editor.export_dt1s()
    raw = {}
    for message in messages:
        raw.update(dict(decode_dt1(editor.blocks, message)))
    part = part_of(editor)
    layout = layout_of(editor)
    return Snapshot(
        slot=slot,
        part=part,
        tone_address=layout[0][0] if layout else "",
        layout=layout,
        blocks=[bytes(m).hex() for m in messages],
        taken_at=datetime.now().isoformat(timespec="seconds"),
        name=name_from_raw(editor, raw),
        source=source,
        epoch=program_epoch(),
    )


# ---------------------------------------------------------------- store
def _store_file(part: str) -> Path:
    return store_dir() / f"{part}.json"


def load_slots(part: str) -> dict:
    """The photos kept for *part* (an unreadable file gives none)."""
    slots = {slot: None for slot in SLOTS}
    path = _store_file(part)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return slots
    except (OSError, ValueError) as ex:
        log.warning(f"A/B photos of {part} not read: {ex}", scope="ABCompare")
        return slots
    for slot in SLOTS:
        item = data.get(slot)
        if not isinstance(item, dict):
            continue
        try:
            item = dict(item, epoch=None)  # taken in another session
            slots[slot] = Snapshot(**item)
        except TypeError as ex:
            log.warning(f"A/B photo {slot} of {part} not read: {ex}", scope="ABCompare")
    return slots


def save_slots(part: str, slots: dict) -> None:
    path = _store_file(part)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {slot: (asdict(s) if s is not None else None) for slot, s in slots.items()}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(path)
    except OSError as ex:
        log.warning(f"A/B photos of {part} not kept: {ex}", scope="ABCompare")


# ---------------------------------------------------------------- session
class ABSession(QObject):
    """The two photos of one editor's part, the one recalled last and whether
    the current state differs from it."""

    changed = Signal()  # photos, active slot, modified or busy changed
    message = Signal(str)  # what happened, for the user

    def __init__(self, editor, parent=None):
        super().__init__(parent if parent is not None else editor)
        self.editor = editor
        self.part = part_of(editor)
        self.slots: dict = load_slots(self.part)
        self.active: Optional[str] = None
        self.modified = False
        self.busy = False
        self._accepted_epoch: Optional[int] = None
        self._check_timer = QTimer(self)
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(CHECK_DELAY_MS)
        self._check_timer.timeout.connect(self.check_modified)
        for pv in editor.values.values():
            pv.valueChanged.connect(self._schedule_check)
        helper = self.helper
        _watch_program_changes(helper)
        signal = getattr(helper, "midi_message_incoming", None)
        if signal is not None:  # values from the JD-Xi arrive with the signals blocked
            signal.connect(self._schedule_check)

    @property
    def helper(self):
        return getattr(self.editor, "_midi_helper", None) or getattr(self.editor, "midi_helper", None)

    def _schedule_check(self, *_args) -> None:
        if self.active is not None:
            self._check_timer.start()

    def check_modified(self) -> None:
        """The current state against the photo recalled last."""
        snapshot = self.slots.get(self.active) if self.active else None
        modified = False
        if snapshot is not None:
            modified = self._differences(snapshot) > 0
        if modified != self.modified:
            self.modified = modified
            self.changed.emit()

    def _differences(self, snapshot: Snapshot) -> int:
        raw = snapshot.raw_values(self.editor)
        return sum(
            1 for spec, value in raw.items()
            if spec.convert_to_midi(self.editor.values[spec].value()) != value
        )

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.changed.emit()

    # ------------------------------------------------------------ capture
    def capture(self, slot: str, confirm_overwrite: Callable[[Snapshot], bool] = lambda s: True) -> bool:
        """Take the photo for *slot*. False if not started (busy, or kept the old one)."""
        if self.busy:
            return False
        if self.slots.get(slot) is not None and not confirm_overwrite(self.slots[slot]):
            return False
        flush = getattr(self.editor, "_flush_pending", None)
        if callable(flush):
            flush()  # the editor's last changes go out before the reading
        if not _connected(self.helper):
            self._store(slot, take_snapshot(self.editor, slot, source="local"))
            self.message.emit(tr("{slot} captured from the editor: the JD-Xi is not connected (local photo)").format(slot=slot))
            return True
        self._set_busy(True)
        self.message.emit(tr("Capturing {slot}: reading the Tone from the JD-Xi…").format(slot=slot))
        self._read(lambda result: self._capture_read(slot, result))
        return True

    def _capture_read(self, slot: str, result) -> None:
        self._set_busy(False)
        if not result.complete:
            self.message.emit(
                tr("{slot} not captured: the JD-Xi did not send the whole Tone ({detail}). Try again.").format(
                    slot=slot, detail=result.summary()))
            return
        self._store(slot, take_snapshot(self.editor, slot, source="jdxi"))
        self.message.emit(tr("{slot} captured").format(slot=slot))

    def _store(self, slot: str, snapshot: Snapshot) -> None:
        self.slots[slot] = snapshot
        save_slots(self.part, self.slots)
        if self.active == slot:  # the photo recalled last is this new one now
            self.check_modified()
        self.changed.emit()

    def _read(self, on_finished) -> None:
        from jdxi_editor.midi.sysex.request.read_session import start_read_session

        start_read_session(self.helper, list(self.editor.midi_requests), timeout_ms=READ_TIMEOUT_MS,
                           parent=self, on_finished=on_finished)

    # ------------------------------------------------------------ recall
    def recall(self, slot: str, confirm_context: Callable[[Snapshot], bool] = lambda s: True) -> bool:
        """Send *slot*'s photo to the JD-Xi and show it once read back. False if not started."""
        snapshot = self.slots.get(slot)
        if self.busy or snapshot is None:
            return False
        problem = snapshot.problem_for(self.editor)
        if problem:
            self.message.emit(tr("{slot} cannot be recalled: {problem}").format(slot=slot, problem=problem))
            return False
        if not _connected(self.helper):
            self.message.emit(tr("{slot} not recalled: connect the JD-Xi to hear it").format(slot=slot))
            return False
        epoch = program_epoch()
        if snapshot.epoch != epoch and self._accepted_epoch != epoch:
            if not confirm_context(snapshot):
                return False
            self._accepted_epoch = epoch
        flush = getattr(self.editor, "_flush_pending", None)
        if callable(flush):
            flush()
        self._set_busy(True)
        previous, self.active = self.active, None
        for message in snapshot.dt1s():
            try:
                sent = self.helper.send_raw_message(list(message))
            except Exception as ex:  # a port that went away
                log.error(f"A/B recall of {slot}: {ex}", scope="ABCompare")
                sent = False
            if sent is False:
                self._set_busy(False)
                self.message.emit(
                    tr("{slot} not recalled: sending to the JD-Xi failed. Its Tone may be partly changed: "
                       "read it again or recall {slot} once more.").format(slot=slot))
                return True
        self.message.emit(tr("Recalling {slot}…").format(slot=slot))
        self._read(lambda result: self._recall_read(slot, snapshot, result, previous))
        return True

    def _recall_read(self, slot: str, snapshot: Snapshot, result, previous) -> None:
        self._set_busy(False)
        if not result.complete:
            self.message.emit(
                tr("{slot} sent, but the JD-Xi did not confirm it ({detail}): its Tone is uncertain. "
                   "Read it again or recall {slot} once more.").format(slot=slot, detail=result.summary()))
            return
        differences = self._differences(snapshot)
        if differences:
            self.message.emit(
                tr("{slot} sent, but the JD-Xi holds {n} different values: its Tone is uncertain. "
                   "Recall {slot} once more.").format(slot=slot, n=differences))
            return
        self.active = slot
        self.modified = False
        self.changed.emit()
        self.message.emit(tr("{slot} recalled").format(slot=slot))

    # ------------------------------------------------------------ the rest
    def clear(self) -> None:
        self.slots = {slot: None for slot in SLOTS}
        self.active = None
        self.modified = False
        save_slots(self.part, self.slots)
        self.changed.emit()

    def write_syx(self, slot: str, name: str, path: Path) -> Path:
        """*slot*'s photo as a .syx of the part, *name* as its Tone Name."""
        snapshot = self.slots[slot]
        path = Path(path)
        if path.suffix.lower() != ".syx":
            path = path.with_suffix(".syx")
        path.write_bytes(b"".join(snapshot.with_name(self.editor, name)))
        return path


# ---------------------------------------------------------------- the bar
def _time(snapshot: Snapshot) -> str:
    try:
        return datetime.fromisoformat(snapshot.taken_at).strftime("%d/%m %H:%M")
    except ValueError:
        return snapshot.taken_at


class ABControl(QWidget):
    """A | B ▾ in a tone editor's top bar."""

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.session = ABSession(editor, self)
        accent = getattr(editor, "ACCENT", "#eb5757")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)
        self.buttons = {}
        for i, slot in enumerate(SLOTS):
            button = QToolButton()
            button.setText(slot)
            button.setObjectName("abSlot")
            button.setCheckable(True)
            button.setMinimumWidth(30)
            button.clicked.connect(lambda _=False, slot=slot: self.pressed(slot))
            layout.addWidget(button)
            self.buttons[slot] = button
        self.menu_button = QToolButton()
        self.menu_button.setText("▾")
        self.menu_button.setObjectName("abMenu")
        self.menu_button.setToolTip(tr("A/B compare: capture, save, clear"))
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.menu_button)
        self.actions = {
            "capture_A": menu.addAction(tr("Capture A"), lambda: self.capture("A")),
            "capture_B": menu.addAction(tr("Capture B"), lambda: self.capture("B")),
        }
        menu.addSeparator()
        self.actions["save_A"] = menu.addAction(tr("Save A…"), lambda: self.save(["A"]))
        self.actions["save_B"] = menu.addAction(tr("Save B…"), lambda: self.save(["B"]))
        self.actions["save_AB"] = menu.addAction(tr("Save A and B…"), lambda: self.save(["A", "B"]))
        menu.addSeparator()
        self.actions["clear"] = menu.addAction(tr("Clear A/B"), self.clear)
        self.menu_button.setMenu(menu)
        layout.addWidget(self.menu_button)
        buttons = getattr(editor, "edit_buttons", None) or []
        if buttons:  # as tall as Undo / Redo / Reload next to them
            height = buttons[0].sizeHint().height()
            for button in (*self.buttons.values(), self.menu_button):
                button.setFixedHeight(height)
        self.state_label = QLabel("")
        self.state_label.setObjectName("abState")
        layout.addSpacing(6)
        layout.addWidget(self.state_label)
        self.setStyleSheet(
            "QToolButton#abSlot, QToolButton#abMenu { background: #1b1c20; color: #6f727a;"
            " border: 1px solid #34363c; padding: 3px 9px; font-weight: 800; }"
            "QToolButton#abSlot[filled=\"true\"] { color: #e8e8ea; border-color: #55585f; }"
            f"QToolButton#abSlot:checked {{ background: {accent}; color: #0e0f11; border-color: {accent}; }}"
            "QToolButton#abSlot:disabled, QToolButton#abMenu:disabled { color: #45474d; }"
            "QToolButton#abMenu::menu-indicator { image: none; }"
            "QLabel#abState { color: #a3a6ad; font-size: 11px; }"
        )
        self.session.changed.connect(self.refresh)
        self.session.message.connect(self.show_message)
        self.refresh()

    # ------------------------------------------------------------ actions
    def pressed(self, slot: str) -> None:
        """An empty slot captures, a full one recalls."""
        if self.session.slots.get(slot) is None:
            self.capture(slot)
        else:
            self.session.recall(slot, confirm_context=self._confirm_context)
        self.refresh()

    def capture(self, slot: str) -> None:
        self.session.capture(slot, confirm_overwrite=self._confirm_overwrite)
        self.refresh()

    def _confirm_overwrite(self, snapshot: Snapshot) -> bool:
        return QMessageBox.question(
            self, tr("A/B compare"),
            tr("{slot} already holds «{name}» ({time}). Replace it with the current Tone?").format(
                slot=snapshot.slot, name=snapshot.name or tr("no name"), time=_time(snapshot)),
        ) == QMessageBox.StandardButton.Yes

    def _confirm_context(self, snapshot: Snapshot) -> bool:
        part = tr(PART_NAMES.get(snapshot.part, snapshot.part))
        return QMessageBox.question(
            self, tr("A/B compare"),
            tr("{slot} («{name}», {time}) was taken with another program, or before JD-Xi Studio was "
               "restarted. Send it to the {part} part of the current program?").format(
                slot=snapshot.slot, name=snapshot.name or tr("no name"), time=_time(snapshot), part=part),
        ) == QMessageBox.StandardButton.Yes

    def save(self, slots: Sequence[str]) -> list[Path]:
        """Ask a name for each photo and where to write it; the .syx files written."""
        names = {}
        for slot in slots:
            snapshot = self.session.slots.get(slot)
            if snapshot is None:
                continue
            name, ok = QInputDialog.getText(
                self, tr("Save {slot}").format(slot=slot),
                tr("Name of {slot} (12 characters, written as Tone Name):").format(slot=slot),
                text=snapshot.name)
            if not ok:
                return []
            names[slot] = clean_name(name) or snapshot.name or slot
        if not names:
            return []
        start = getattr(self.editor, "_part_syx_path", "") or str(Path.home())
        start_dir = Path(start).parent if Path(start).suffix else Path(start)
        written = []
        if len(names) == 1:
            slot, name = next(iter(names.items()))
            path, _ = QFileDialog.getSaveFileName(
                self, tr("Save {slot}").format(slot=slot), str(start_dir / f"{_file_stem(name)}.syx"),
                tr("SysEx Files (*.syx);;All Files (*)"))
            if not path:
                return []
            written.append(self.session.write_syx(slot, name, Path(path)))
        else:
            folder = QFileDialog.getExistingDirectory(self, tr("Save A and B in"), str(start_dir))
            if not folder:
                return []
            targets = {slot: Path(folder) / f"{_file_stem(name)}.syx" for slot, name in names.items()}
            if len({str(p) for p in targets.values()}) < len(targets):  # same name: tell them apart
                targets = {slot: Path(folder) / f"{_file_stem(name)}_{slot}.syx" for slot, name in names.items()}
            existing = [p.name for p in targets.values() if p.exists()]
            if existing and QMessageBox.question(
                    self, tr("Save A and B"), tr("Replace {files}?").format(files=", ".join(existing)),
            ) != QMessageBox.StandardButton.Yes:
                return []
            for slot, path in targets.items():
                written.append(self.session.write_syx(slot, names[slot], path))
        if written:
            self.editor._part_syx_path = str(written[-1])
            self.show_message(tr("Saved: {files}").format(files=", ".join(p.name for p in written)))
        return written

    def clear(self) -> None:
        if any(self.session.slots.values()) and QMessageBox.question(
                self, tr("A/B compare"), tr("Clear the photos A and B of this part?"),
        ) != QMessageBox.StandardButton.Yes:
            return
        self.session.clear()

    # ------------------------------------------------------------ display
    def show_message(self, text: str) -> None:
        status = getattr(self.editor, "read_status", None)
        if status is not None:
            status.setText(text)
        log.message(text, scope="ABCompare")

    def refresh(self) -> None:
        session = self.session
        for slot, button in self.buttons.items():
            snapshot = session.slots.get(slot)
            button.setProperty("filled", snapshot is not None)
            button.setChecked(session.active == slot)
            button.setEnabled(not session.busy)
            button.style().unpolish(button)
            button.style().polish(button)
            if snapshot is None:
                button.setToolTip(tr("{slot} is empty: press to capture the current Tone").format(slot=slot))
            else:
                where = tr("read from the JD-Xi") if snapshot.source == "jdxi" else tr("local: taken from the editor")
                button.setToolTip(tr("{slot}: «{name}», {time}, {where}. Press to recall it.").format(
                    slot=slot, name=snapshot.name or tr("no name"), time=_time(snapshot), where=where))
        self.menu_button.setEnabled(not session.busy)
        for slot in SLOTS:
            self.actions[f"save_{slot}"].setEnabled(session.slots.get(slot) is not None)
        self.actions["save_AB"].setEnabled(all(session.slots.get(s) is not None for s in SLOTS))
        self.actions["clear"].setEnabled(any(session.slots.values()))
        if session.active and session.modified:
            self.state_label.setText(tr("● modified from {slot}").format(slot=session.active))
        else:
            self.state_label.setText("")


def _file_stem(name: str) -> str:
    stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()
    return stem.replace(" ", "_") or "tone"
