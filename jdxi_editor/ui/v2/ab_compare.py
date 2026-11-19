"""
A/B compare: two snapshots of one part's Tone, to switch between while playing.

For Digital 1, Digital 2 and Analog, in the tone editors' top bar after
Undo / Redo / Reload:  A  B   📷  ⇄  💾

- A / B choose the slot; a full one is also recalled (the JD-Xi connected).
  Empty: dashed outline; chosen: outline in the part's colour; active (the
  JD-Xi plays it): filled with that colour; modified since: a dot.
- 📷 captures the Tone in the chosen slot. With the JD-Xi connected the Tone is
  read again first (RQ1) and the photo is taken only from a complete answer,
  after the editor's own changes have gone out; without it the editor's
  values are taken and the photo is marked "local". Replacing a photo asks;
  one never saved to a file can be saved first.
- ⇄ (Ctrl+Shift+A) recalls the other photo. A recall sends the photo's DT1s,
  reads the Tone back and makes the photo active only when the JD-Xi holds
  exactly it: a failed send, a missing answer or other values leave nothing
  active and say the JD-Xi's state is uncertain. Only this part's Tone
  blocks are sent: the other parts, the effects and the program stay, and
  so does the channel the keys play on.
- 💾 saves the active photo (or the chosen one) as a .syx of the part, with
  the name given written in the Tone Name; the editors' Import reads it.
- What needs the JD-Xi (recall, ⇄) is disabled while it is not connected;
  the buttons follow it being plugged in or out. Notices float under the
  buttons and never move the bar.
- The photos are copies: editing (here or on the JD-Xi) changes the current
  state only. They are kept per part in ~/.jdxi_studio/ab_compare and come
  back at start, but nothing is sent until a slot is pressed. After a
  program change (or a restart) recalling asks first.

Undo / Redo / Reload are untouched: a recall arrives as values from the
JD-Xi, which the edit history already handles (the steps on them are dropped).
"""

from __future__ import annotations

import json
import weakref
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from decologr import Decologr as log
from PySide6.QtCore import QObject, QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
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
    saved_to: str = ""  # the .syx it was last saved as ("" never saved)
    unknown: list = field(default_factory=list)  # blocks (hex) with bytes not read from the JD-Xi

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
        if self.unknown:
            return tr("it was taken without the JD-Xi and some of its data is not known: capture it again with the JD-Xi connected")
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

    unknown = []
    messages = editor.export_dt1s(unknown=unknown)
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
        unknown=unknown,
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


def save_slots(part: str, slots: dict) -> bool:
    """Keep *part*'s photos on disk; False if they could not be written."""
    path = _store_file(part)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {slot: (asdict(s) if s is not None else None) for slot, s in slots.items()}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(path)
        return True
    except (OSError, TypeError, ValueError) as ex:
        log.warning(f"A/B photos of {part} not kept: {ex}", scope="ABCompare")
        return False


# ---------------------------------------------------------------- session
class ABSession(QObject):
    """The two photos of one editor's part, the one recalled last and whether
    the current state differs from it."""

    changed = Signal()  # photos, active slot, modified or busy changed
    message = Signal(str, bool)  # what happened, for the user; True: a problem

    def __init__(self, editor, parent=None):
        super().__init__(parent if parent is not None else editor)
        self.editor = editor
        self.part = part_of(editor)
        self.slots: dict = load_slots(self.part)
        self.active: Optional[str] = None  # the photo the JD-Xi holds (recalled last)
        self.selected: str = SLOTS[0]  # the slot the camera and the disk act on
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

    def connected(self) -> bool:
        return _connected(self.helper)

    def disconnected(self) -> None:
        """The JD-Xi went away: what it plays when it comes back is not known."""
        if self.active is not None:
            self.selected = self.active
            self.active = None
            self.modified = False
            self.changed.emit()

    def other(self, slot: Optional[str] = None) -> str:
        slot = slot or self.active or self.selected
        return SLOTS[1] if slot == SLOTS[0] else SLOTS[0]

    def can_switch(self) -> bool:
        return (not self.busy and self.connected()
                and all(self.slots.get(s) is not None and not self.slots[s].unknown for s in SLOTS))

    def switch(self, confirm_context: Callable[[Snapshot], bool] = lambda s: True) -> bool:
        """Recall the other photo (A after B, B after A)."""
        if not self.can_switch():
            return False
        slot = self.other()
        self.selected = slot
        return self.recall(slot, confirm_context=confirm_context)

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
            snapshot = take_snapshot(self.editor, slot, source="local")
            if self._store(slot, snapshot):
                if snapshot.unknown:
                    self.message.emit(tr("{slot} captured from the editor, without the JD-Xi: some of its data is not known, so it cannot be recalled or saved until captured again with the JD-Xi connected").format(slot=slot), True)
                else:
                    self.message.emit(tr("{slot} captured from the editor: the JD-Xi is not connected (local photo)").format(slot=slot), False)
            return True
        self._set_busy(True)
        self.message.emit(tr("Capturing {slot}: reading the Tone from the JD-Xi…").format(slot=slot), False)
        self._read(lambda result: self._capture_read(slot, result))
        return True

    def _capture_read(self, slot: str, result) -> None:
        self._set_busy(False)
        if not result.complete:
            self.message.emit(
                tr("{slot} not captured: the JD-Xi did not send the whole Tone ({detail}). Try again.").format(
                    slot=slot, detail=result.summary()), True)
            return
        if self._store(slot, take_snapshot(self.editor, slot, source="jdxi")):
            self.message.emit(tr("{slot} captured").format(slot=slot), False)

    def _store(self, slot: str, snapshot: Snapshot) -> bool:
        """Keep the photo; False (and says so) if it could not be written to disk."""
        self.slots[slot] = snapshot
        self.selected = slot
        kept = save_slots(self.part, self.slots)
        if self.active == slot:  # the photo recalled last is this new one now
            self.check_modified()
        self.changed.emit()
        if not kept:
            self.message.emit(tr("{slot} captured, but it could not be written to disk: it will be lost when JD-Xi Studio closes").format(slot=slot), True)
        return kept

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
            self.message.emit(tr("{slot} cannot be recalled: {problem}").format(slot=slot, problem=problem), True)
            return False
        if not _connected(self.helper):
            self.message.emit(tr("{slot} not recalled: connect the JD-Xi to hear it").format(slot=slot), True)
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
                       "read it again or recall {slot} once more.").format(slot=slot), True)
                return True
        self.message.emit(tr("Recalling {slot}…").format(slot=slot), False)
        self._read(lambda result: self._recall_read(slot, snapshot, result, previous))
        return True

    def _recall_read(self, slot: str, snapshot: Snapshot, result, previous) -> None:
        self._set_busy(False)
        if not result.complete:
            self.message.emit(
                tr("{slot} sent, but the JD-Xi did not confirm it ({detail}): its Tone is uncertain. "
                   "Read it again or recall {slot} once more.").format(slot=slot, detail=result.summary()), True)
            return
        differences = self._differences(snapshot)
        if differences:
            self.message.emit(
                tr("{slot} sent, but the JD-Xi holds {n} different values: its Tone is uncertain. "
                   "Recall {slot} once more.").format(slot=slot, n=differences), True)
            return
        self.active = slot
        self.modified = False
        self.changed.emit()
        self.message.emit(tr("{slot} recalled").format(slot=slot), False)

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
        if snapshot.unknown:
            raise ValueError(f"{slot}: data not read from the JD-Xi")
        path = Path(path)
        if path.suffix.lower() != ".syx":
            path = path.with_suffix(".syx")
        path.write_bytes(b"".join(snapshot.with_name(self.editor, name)))
        snapshot.saved_to = str(path)
        save_slots(self.part, self.slots)
        self.changed.emit()
        return path


# ---------------------------------------------------------------- the bar
CONNECTION_CHECK_MS = 1000  # the buttons follow the JD-Xi being plugged in or out
TOAST_MS = 3500  # how long a notice stays (a problem stays until clicked)
SWITCH_SHORTCUT = "Ctrl+Shift+A"


def _time(snapshot: Snapshot) -> str:
    try:
        return datetime.fromisoformat(snapshot.taken_at).strftime("%d/%m %H:%M")
    except ValueError:
        return snapshot.taken_at


class SlotButton(QToolButton):
    """A or B. Empty: dashed outline; full: grey; selected: outline in the
    part's colour; active (the JD-Xi holds it): filled with the part's colour;
    modified since: a dot in the corner."""

    EMPTY, FULL = "empty", "full"

    def __init__(self, slot: str, accent: str, parent=None):
        super().__init__(parent)
        self.slot = slot
        self.accent = QColor(accent)
        self.state = self.EMPTY
        self.selected = False
        self.active = False
        self.modified = False
        self.setText(slot)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(38)

    def show_state(self, full: bool, selected: bool, active: bool, modified: bool) -> None:
        self.state = self.FULL if full else self.EMPTY
        self.selected, self.active, self.modified = selected, active, modified
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt name)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = 6
        enabled = self.isEnabled()
        if self.active:
            fill, text, border = self.accent, QColor("#0e0f11"), self.accent
        elif self.state == self.FULL:
            fill, text, border = QColor("#2a2c31"), QColor("#e8e8ea"), QColor("#4a4d55")
        else:
            fill, text, border = QColor("#17181b"), QColor("#5d6068"), QColor("#4a4d55")
        if self.selected and not self.active:
            border = self.accent
        if not enabled:
            text = QColor(text.red(), text.green(), text.blue(), 110)
        pen = QPen(border, 2 if (self.selected or self.active) else 1)
        if self.state == self.EMPTY and not self.selected and not self.active:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(fill)
        p.drawRoundedRect(rect, radius, radius)
        font = p.font()
        font.setBold(True)
        font.setPixelSize(15)
        p.setFont(font)
        p.setPen(text)
        p.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.slot)
        if self.modified and self.active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#0e0f11"))
            p.drawEllipse(QPointF(rect.right() - 7, rect.top() + 7), 3.5, 3.5)
        p.end()


class Toast(QLabel):
    """A notice floating under the A/B buttons: it never moves the bar. It goes
    after a few seconds; a problem stays until clicked."""

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.setWordWrap(True)
        self.setMaximumWidth(420)
        self.setContentsMargins(10, 6, 10, 6)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_text(self, text: str, problem: bool, anchor: QWidget) -> None:
        colour = "#ff6b5e" if problem else "#3a3d44"
        self.setStyleSheet(
            f"QLabel {{ background: #1f2025; color: #e8e8ea; border: 1px solid {colour};"
            " border-radius: 6px; font-size: 12px; }")
        self.setText(text + ("   ✕" if problem else ""))
        self.setToolTip(tr("Click to close") if problem else "")
        self.adjustSize()
        host = self.parentWidget()
        below = anchor.mapTo(host, QPoint(0, anchor.height() + 6))
        x = min(max(4, below.x()), max(4, host.width() - self.width() - 8))
        self.move(x, below.y())
        self.raise_()
        self.show()
        if problem:
            self._timer.stop()
        else:
            self._timer.start(TOAST_MS)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt name)
        self.hide()


class ABControl(QWidget):
    """A B  📷 ⇄ 💾 in a tone editor's top bar."""

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        import qtawesome as qta

        self.editor = editor
        self.session = ABSession(editor, self)
        accent = getattr(editor, "ACCENT", "#eb5757")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(4)
        model = (getattr(editor, "edit_buttons", None) or [None])[0]
        height = model.sizeHint().height() if model is not None else 32
        self.buttons = {}
        for slot in SLOTS:
            button = SlotButton(slot, accent)
            button.setFixedHeight(height)
            button.clicked.connect(lambda _=False, slot=slot: self.pressed(slot))
            layout.addWidget(button)
            self.buttons[slot] = button
        layout.addSpacing(6)

        def tool(icon: str, slot) -> QToolButton:
            b = QToolButton()
            if model is not None:  # as Undo / Redo / Reload next to them
                b.setObjectName(model.objectName())
                b.setAutoRaise(model.autoRaise())
                b.setStyleSheet(model.styleSheet())
            b.setIcon(qta.icon(icon, color="#e6e6e6", color_disabled="#55585f"))
            b.setIconSize(QSize(20, 20))
            b.setFixedSize(model.sizeHint() if model is not None else QSize(height, height))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            layout.addWidget(b)
            return b

        self.camera = tool("mdi.camera", self.capture)
        self.swap = tool("mdi.swap-horizontal", self.switch)
        self.disk = tool("mdi.content-save", self.save)
        self.toast = Toast(editor)
        self.shortcut = QShortcut(QKeySequence(SWITCH_SHORTCUT), editor)
        self.shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut.activated.connect(self.switch)
        self._connected = None
        self._poll = QTimer(self)
        self._poll.setInterval(CONNECTION_CHECK_MS)
        self._poll.timeout.connect(self._connection_check)
        self._poll.start()
        self.session.changed.connect(self.refresh)
        self.session.message.connect(self.show_message)
        self.refresh()

    # ------------------------------------------------------------ actions
    def pressed(self, slot: str) -> None:
        """Choose a slot; a full one is recalled too (with the JD-Xi connected)."""
        session = self.session
        if session.busy:
            return
        session.selected = slot
        if session.slots.get(slot) is not None and session.connected() and session.active != slot:
            session.recall(slot, confirm_context=self._confirm_context)
        self.refresh()

    def capture(self) -> None:
        self.session.capture(self.session.selected, confirm_overwrite=self._confirm_overwrite)
        self.refresh()

    def switch(self) -> None:
        if self.session.can_switch():
            self.session.switch(confirm_context=self._confirm_context)
        self.refresh()

    def target(self) -> str:
        """The slot the disk saves: the active one, else the one chosen."""
        return self.session.active or self.session.selected

    def _confirm_overwrite(self, snapshot: Snapshot) -> bool:
        """Replacing a photo: one never saved to a file can be saved first."""
        text = tr("{slot} already holds «{name}» ({time}). Replace it with the current Tone?").format(
            slot=snapshot.slot, name=snapshot.name or tr("no name"), time=_time(snapshot))
        if snapshot.saved_to:
            return QMessageBox.question(self, tr("A/B compare"), text) == QMessageBox.StandardButton.Yes
        box = QMessageBox(QMessageBox.Icon.Question, tr("A/B compare"),
                          text + "\n" + tr("It has not been saved to a file."), parent=self)
        save = box.addButton(tr("Save first…"), QMessageBox.ButtonRole.AcceptRole)
        replace = box.addButton(tr("Replace"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is replace:
            return True
        if box.clickedButton() is save:
            return bool(self.save(snapshot.slot))
        return False

    def _confirm_context(self, snapshot: Snapshot) -> bool:
        part = tr(PART_NAMES.get(snapshot.part, snapshot.part))
        return QMessageBox.question(
            self, tr("A/B compare"),
            tr("{slot} («{name}», {time}) was taken with another program, or before JD-Xi Studio was "
               "restarted. Send it to the {part} part of the current program?").format(
                slot=snapshot.slot, name=snapshot.name or tr("no name"), time=_time(snapshot), part=part),
        ) == QMessageBox.StandardButton.Yes

    def save(self, slot: Optional[str] = None) -> Optional[Path]:
        """Save a photo (the active one) as a .syx: its name, then where."""
        slot = slot or self.target()
        snapshot = self.session.slots.get(slot)
        if snapshot is None:
            return None
        if snapshot.unknown:
            self.show_message(tr("{slot} cannot be saved: it was taken without the JD-Xi and some of its data is not known").format(slot=slot), True)
            return None
        name, ok = QInputDialog.getText(
            self, tr("Save {slot}").format(slot=slot),
            tr("Name of {slot} (12 characters, written as Tone Name):").format(slot=slot),
            text=snapshot.name)
        if not ok:
            return None
        name = clean_name(name) or snapshot.name or slot
        start = snapshot.saved_to or getattr(self.editor, "_part_syx_path", "") or str(Path.home())
        start_dir = Path(start).parent if Path(start).suffix else Path(start)
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save {slot}").format(slot=slot), str(start_dir / f"{_file_stem(name)}.syx"),
            tr("SysEx Files (*.syx);;All Files (*)"))
        if not path:
            return None
        written = self.session.write_syx(slot, name, Path(path))
        self.editor._part_syx_path = str(written)
        self.show_message(tr("{slot} saved: {file}").format(slot=slot, file=written.name), False)
        return written

    # ------------------------------------------------------------ display
    def show_message(self, text: str, problem: bool = False) -> None:
        log.message(text, scope="ABCompare")
        if self.isVisible():
            self.toast.show_text(text, problem, self)

    def _connection_check(self) -> None:
        connected = self.session.connected()
        if connected != self._connected:
            if not connected:
                self.session.disconnected()
            self.refresh()

    def refresh(self) -> None:
        session = self.session
        connected = session.connected()
        self._connected = connected
        for slot, button in self.buttons.items():
            snapshot = session.slots.get(slot)
            button.show_state(full=snapshot is not None, selected=session.selected == slot,
                              active=session.active == slot,
                              modified=session.active == slot and session.modified)
            button.setEnabled(not session.busy)
            if snapshot is None:
                button.setToolTip(tr("{slot} is empty: choose it and press the camera to capture the current Tone").format(slot=slot))
                continue
            where = tr("read from the JD-Xi") if snapshot.source == "jdxi" else tr("local: taken from the editor")
            saved = (tr("saved as {file}").format(file=Path(snapshot.saved_to).name) if snapshot.saved_to
                     else tr("not saved to a file"))
            tip = tr("{slot}: «{name}», {time}, {where}, {saved}.").format(
                slot=slot, name=snapshot.name or tr("no name"), time=_time(snapshot), where=where, saved=saved)
            if session.active == slot:
                tip += " " + (tr("The JD-Xi plays it, with changes since.") if session.modified
                              else tr("The JD-Xi plays it."))
            elif connected:
                tip += " " + tr("Press to recall it.")
            else:
                tip += " " + tr("Connect the JD-Xi to recall it.")
            button.setToolTip(tip)
        selected = session.selected
        self.camera.setEnabled(not session.busy)
        self.camera.setToolTip(
            (tr("Capture the current Tone in {slot} (read from the JD-Xi)") if connected
             else tr("Capture the editor's values in {slot} (JD-Xi not connected: a local photo)")).format(slot=selected))
        self.swap.setEnabled(session.can_switch())
        if not connected:
            self.swap.setToolTip(tr("Switch between A and B: connect the JD-Xi"))
        elif not all(session.slots.get(s) is not None for s in SLOTS):
            self.swap.setToolTip(tr("Switch between A and B: capture both first"))
        elif any(session.slots[s].unknown for s in SLOTS):
            self.swap.setToolTip(tr("Switch between A and B: capture again with the JD-Xi connected the photo taken without it"))
        else:
            self.swap.setToolTip(tr("Switch between A and B ({keys})").format(keys=SWITCH_SHORTCUT))
        target = self.target()
        photo = session.slots.get(target)
        self.disk.setEnabled(not session.busy and photo is not None and not photo.unknown)
        if photo is not None and photo.unknown:
            self.disk.setToolTip(tr("{slot} cannot be saved: it was taken without the JD-Xi and some of its data is not known").format(slot=target))
        else:
            self.disk.setToolTip(tr("Save {slot} as a .syx file, with a name").format(slot=target))


def _file_stem(name: str) -> str:
    stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()
    return stem.replace(" ", "_") or "tone"
