"""
A/B compare (ui/v2/ab_compare.py) with a simulated JD-Xi: the validation matrix
TC-01 ... TC-18 of the proposal, plus incomplete and incompatible photos.

The simulated JD-Xi keeps a memory of its Temporary areas: DT1 writes change
it, RQ1 requests are answered from it through the helper's real input path
(as a reply from the port would be), unless it is told to stay silent.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import Mock

import mido
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.midi.io.synth_memory import build_dt1
from jdxi_editor.midi.sysex.part_syx import expected_address_prefix, validate_part_syx
from jdxi_editor.ui.v2 import ab_compare as ab

APP = QApplication.instance() or QApplication([])


class FakeJDXi(QObject):
    """The JD-Xi on the other end of a MidiIOHelper."""

    reply = Signal(object)

    def __init__(self, helper: MidiIOHelper):
        super().__init__()
        self.helper = helper
        self.memory: dict[tuple, int] = {}  # 4-byte address (as a number) -> byte
        self.writes: list[bytes] = []
        self.silent = False
        self.refuse_sends = False
        self._lock = threading.Lock()
        self.reply.connect(lambda data: helper._handle_midi_message(mido.Message("sysex", data=data)))
        for name in ("midi_out", "midi_in"):
            port = Mock()
            port.is_port_open.return_value = True
            setattr(helper, name, port)
        helper.send_raw_message = self.send
        helper.send_midi_message = lambda message: self.send(list(message.to_message_list()))

    @staticmethod
    def _number(address) -> int:
        a = list(address)
        return a[0] << 21 | a[1] << 14 | a[2] << 7 | a[3]

    @staticmethod
    def _address(number: int) -> list:
        return [(number >> 21) & 0x7F, (number >> 14) & 0x7F, (number >> 7) & 0x7F, number & 0x7F]

    def load(self, messages) -> None:
        for message in messages:
            self._write(bytes(message))

    def _write(self, data: bytes) -> None:
        start = self._number(data[8:12])
        with self._lock:
            for i, byte in enumerate(data[12:-2]):
                self.memory[start + i] = byte

    def read(self, address, size: int) -> bytes:
        start = self._number(address)
        with self._lock:
            return bytes(self.memory.get(start + i, 0) for i in range(size))

    def send(self, message) -> bool:
        data = bytes(int(b) for b in message)
        if self.refuse_sends:
            return False
        if data[:7] != bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E]):
            return True
        if data[7] == 0x12:
            self.writes.append(data)
            self._write(data)
        elif data[7] == 0x11 and not self.silent:
            size = self._number(data[12:16])
            reply = build_dt1(list(data[8:12]), self.read(data[8:12], size))
            self.reply.emit(list(bytes(reply)[1:-1]))  # queued to the main thread
        return True


def pump(until, seconds: float = 8.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QApplication.processEvents()
        if until():
            return True
        time.sleep(0.005)
    return until()


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ab, "store_dir", lambda: tmp_path / "ab")
    return tmp_path / "ab"


@pytest.fixture
def rig():
    """One helper and JD-Xi, the three synth editors (and Drums) on it."""
    from jdxi_editor.ui.v2.analog import AnalogToneEditor
    from jdxi_editor.ui.v2.digital import Digital2ToneEditor, DigitalToneEditor

    helper = MidiIOHelper()
    jdxi = FakeJDXi(helper)
    editors = {
        "digital_1": DigitalToneEditor(helper, Mock()),
        "digital_2": Digital2ToneEditor(helper, Mock()),
        "analog": AnalogToneEditor(helper, Mock()),
    }
    for editor in editors.values():
        jdxi.load(editor.export_dt1s())  # a valid Tone in every part
    yield helper, jdxi, editors
    for editor in editors.values():
        editor.close()
        editor.deleteLater()
    QApplication.processEvents()


def session_of(editor) -> ab.ABSession:
    return editor.ab_control.session


def capture(session: ab.ABSession, slot: str, **kw) -> ab.Snapshot:
    assert session.capture(slot, **kw)
    assert pump(lambda: not session.busy)
    return session.slots[slot]


def recall(session: ab.ABSession, slot: str, **kw) -> bool:
    started = session.recall(slot, **kw)
    assert pump(lambda: not session.busy)
    return started


def edit(editor, name: str, value: int, block_key=None) -> None:
    pv = editor.pv(name, block_key)
    pv.setValue(value)
    editor._flush_pending()
    QApplication.processEvents()


def part_bytes(jdxi: FakeJDXi, editor) -> list:
    return [jdxi.read(bytes.fromhex(address), size) for address, size in ab.layout_of(editor)]


def snapshot_bytes(snapshot: ab.Snapshot) -> list:
    return [m[12:-2] for m in snapshot.dt1s()]


# ------------------------------------------------------------------ TC-01..07
def test_tc01_capture_a_is_a_complete_photo_read_from_the_jdxi(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    a = capture(session_of(editor), "A")
    assert a.complete() and a.source == "jdxi" and a.part == "digital_1"
    assert a.tone_address == "19010000" and a.schema == ab.SCHEMA_VERSION
    assert snapshot_bytes(a) == part_bytes(jdxi, editor)  # the whole Tone, as the JD-Xi holds it
    assert len(a.blocks) == len(ab.layout_of(editor)) == 5  # Common, 3 partials, Modify


def test_tc02_tc06_tc07_photos_are_independent_copies(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    a = capture(session, "A")
    a_blocks = list(a.blocks)
    edit(editor, "FILTER_CUTOFF", 30, "PARTIAL_1") if _has(editor, "FILTER_CUTOFF") else None
    edit(editor, "TONE_LEVEL", 50)
    b = capture(session, "B")
    assert b.blocks != a.blocks
    assert session.slots["A"].blocks == a_blocks  # TC-02 / TC-06: A unchanged by the edits and by B
    b_blocks = list(b.blocks)
    edit(editor, "TONE_LEVEL", 90)
    assert session.slots["B"].blocks == b_blocks  # TC-07


def _has(editor, name) -> bool:
    try:
        editor.spec(name)
        return True
    except KeyError:
        return False


def test_tc03_tc04_tc05_recall_restores_every_parameter(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    edit(editor, "TONE_LEVEL", 40)
    a = capture(session, "A")
    edit(editor, "TONE_LEVEL", 110)
    edit(editor, "TONE_NAME_1", ord("Z"))
    b = capture(session, "B")
    messages = []
    session.message.connect(lambda text, problem: messages.append(text))
    for slot, photo in [("A", a), ("B", b)] * 3:  # TC-05: back and forth
        assert recall(session, slot)
        assert session.active == slot, messages[-1]
        assert session.active == slot and not session.modified
        assert part_bytes(jdxi, editor) == snapshot_bytes(photo)  # the JD-Xi holds the photo
        assert session._differences(photo) == 0  # and the editor shows it
    assert editor.pv("TONE_LEVEL").value() == 110 and editor.pv("TONE_NAME_1").value() == ord("Z")


def test_after_a_recall_an_edit_shows_modified_and_leaves_the_photos(rig):
    helper, jdxi, eds = rig
    editor = eds["analog"]
    session = session_of(editor)
    a = capture(session, "A")
    assert recall(session, "A")
    edit(editor, "AMP_LEVEL", 3)
    assert pump(lambda: session.modified)
    assert editor.ab_control.buttons["A"].modified  # the dot on A
    assert session.slots["A"].blocks == a.blocks
    edit(editor, "AMP_LEVEL", ab.Snapshot.raw_values(a, editor)[editor.spec("AMP_LEVEL")])
    assert pump(lambda: not session.modified)  # back to A's value: not modified


def test_a_change_made_on_the_jdxi_shows_modified(rig):
    helper, jdxi, eds = rig
    editor = eds["analog"]
    session = session_of(editor)
    capture(session, "A")
    assert recall(session, "A")
    spec = editor.spec("AMP_LEVEL")
    address = list(editor.block_of[spec].address_bytes())
    address[3] += spec.offset & 0x7F
    helper._handle_midi_message(mido.Message("sysex", data=list(build_dt1(address, [7]))[1:-1]))
    assert pump(lambda: session.modified)


# ------------------------------------------------------------------ TC-08..10
def test_tc08_tc09_tc10_save_writes_each_photo_with_its_name(rig, tmp_path):
    helper, jdxi, eds = rig
    editor = eds["digital_2"]
    session = session_of(editor)
    a = capture(session, "A")
    edit(editor, "TONE_LEVEL", 12)
    b = capture(session, "B")
    path_a = session.write_syx("A", "Warm Pad", tmp_path / "a")
    path_b = session.write_syx("B", "Bright Pad", tmp_path / "b.syx")
    assert path_a.suffix == ".syx" and path_b.name == "b.syx"
    prefix = expected_address_prefix(editor)
    for path, photo, name in ((path_a, a, "Warm Pad"), (path_b, b, "Bright Pad")):
        data = path.read_bytes()
        ok, _msg, messages = validate_part_syx(data, expected_prefix=prefix)
        assert ok and len(messages) == len(photo.blocks)  # the editors' Import reads it
        saved = ab.Snapshot(**{**photo.__dict__, "blocks": [bytes(m).hex() for m in messages]})
        assert saved.complete()
        assert ab.name_from_raw(editor, saved.raw_values(editor)) == name
        # only the name differs from the photo
        diff = {s.name for s, v in saved.raw_values(editor).items() if photo.raw_values(editor)[s] != v}
        assert diff <= {f"TONE_NAME_{i}" for i in range(1, 13)}
    assert a.name != "Warm Pad"  # the photo itself is not renamed


def test_the_disk_saves_the_active_photo(rig, tmp_path, monkeypatch):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    control = editor.ab_control
    session = control.session
    capture(session, "A")
    edit(editor, "TONE_LEVEL", 5)
    capture(session, "B")
    assert recall(session, "B")
    monkeypatch.setattr(ab.QInputDialog, "getText", lambda *a, **k: ("Beta", True))
    monkeypatch.setattr(ab.QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "beta.syx"), ""))
    assert control.target() == "B"
    written = control.save()
    assert written.name == "beta.syx" and session.slots["B"].saved_to == str(written)
    assert session.slots["A"].saved_to == ""
    assert ab.load_slots("digital_1")["B"].saved_to == str(written)  # kept


def test_replacing_a_photo_never_saved_offers_to_save_it_first(rig, tmp_path, monkeypatch):
    helper, jdxi, eds = rig
    editor = eds["analog"]
    control = editor.ab_control
    session = control.session
    first = capture(session, "A")
    choices = []

    class Box:  # the three-way question: Save first… / Replace / Cancel
        Icon = ab.QMessageBox.Icon
        ButtonRole = ab.QMessageBox.ButtonRole
        StandardButton = ab.QMessageBox.StandardButton

        def __init__(self, *a, **k):
            self.buttons = []

        def addButton(self, button, role=None):  # noqa: N802
            self.buttons.append(button)
            return button

        def exec(self):
            choices.append(self.buttons[:2])

        def clickedButton(self):  # noqa: N802
            return self.buttons[0]  # "Save first…"

    monkeypatch.setattr(ab, "QMessageBox", Box)
    monkeypatch.setattr(ab.QInputDialog, "getText", lambda *a, **k: ("First", True))
    monkeypatch.setattr(ab.QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "first.syx"), ""))
    edit(editor, "AMP_LEVEL", 11)
    session.selected = "A"
    control.capture()
    assert pump(lambda: not session.busy)
    assert choices and (tmp_path / "first.syx").exists()  # saved first, then replaced
    assert session.slots["A"].blocks != first.blocks and session.slots["A"].saved_to == ""


# ------------------------------------------------------------------ TC-11..13
@pytest.mark.parametrize("part", ["digital_1", "digital_2", "analog"])
def test_tc11_tc12_tc13_a_recall_leaves_the_other_parts(rig, part):
    helper, jdxi, eds = rig
    editor = eds[part]
    session = session_of(editor)
    capture(session, "A")
    edit(editor, "TONE_NAME_2", ord("Q"))
    others = {p: part_bytes(jdxi, e) for p, e in eds.items() if p != part}
    program = jdxi.read([0x18, 0x00, 0x00, 0x00], 0x20)
    jdxi.writes.clear()
    assert recall(session, "A")
    prefix = bytes.fromhex(ab.layout_of(editor)[0][0])[:2]
    assert jdxi.writes and all(w[8:10] == prefix for w in jdxi.writes)  # only this part's Tone
    assert {p: part_bytes(jdxi, e) for p, e in eds.items() if p != part} == others
    assert jdxi.read([0x18, 0x00, 0x00, 0x00], 0x20) == program


# ------------------------------------------------------------------ TC-14
def test_tc14_no_answer_after_a_recall_leaves_the_state_uncertain(rig, monkeypatch):
    monkeypatch.setattr(ab, "READ_TIMEOUT_MS", 300)
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    capture(session, "A")
    messages = []
    session.message.connect(lambda text, problem: messages.append(text))
    jdxi.silent = True  # unplugged after the send
    assert recall(session, "A")
    assert session.active is None and "uncertain" in messages[-1]


def test_tc14_a_send_that_fails_is_not_a_recall(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    capture(session, "A")
    messages = []
    session.message.connect(lambda text, problem: messages.append(text))
    jdxi.refuse_sends = True
    assert recall(session, "A")
    assert session.active is None and "failed" in messages[-1]


def test_tc14_disconnected_capture_is_local_and_recall_is_refused(rig):
    helper, jdxi, eds = rig
    editor = eds["analog"]
    session = session_of(editor)
    helper.midi_out.is_port_open.return_value = False
    messages = []
    session.message.connect(lambda text, problem: messages.append(text))
    a = capture(session, "A")
    assert a.source == "local" and a.complete()
    jdxi.writes.clear()
    assert not session.recall("A")
    assert jdxi.writes == [] and "connect" in messages[-1]
    helper.midi_out.is_port_open.return_value = True
    assert recall(session, "A") and session.active == "A"  # kept through the disconnection


def test_a_capture_without_a_whole_answer_takes_nothing(rig, monkeypatch):
    monkeypatch.setattr(ab, "READ_TIMEOUT_MS", 300)
    helper, jdxi, eds = rig
    session = session_of(eds["digital_2"])
    jdxi.silent = True
    assert session.capture("A")
    assert pump(lambda: not session.busy)
    assert session.slots["A"] is None


# ------------------------------------------------------------------ TC-15..17
def test_tc15_after_a_program_change_a_recall_asks_first(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    capture(session, "A")
    helper._handle_midi_message(mido.Message("program_change", channel=15, program=4))
    jdxi.writes.clear()
    asked = []
    assert not session.recall("A", confirm_context=lambda s: asked.append(s.slot) or False)
    assert asked == ["A"] and jdxi.writes == []  # nothing sent without a yes
    assert recall(session, "A", confirm_context=lambda s: True) and session.active == "A"
    assert recall(session, "A", confirm_context=lambda s: pytest.fail("asked twice"))


def test_a_tone_change_on_the_part_does_not_ask(rig):
    helper, jdxi, eds = rig
    session = session_of(eds["digital_1"])
    capture(session, "A")
    helper._handle_midi_message(mido.Message("program_change", channel=0, program=4))  # a Tone
    assert recall(session, "A", confirm_context=lambda s: pytest.fail("asked for a Tone change"))


def test_tc16_replacing_a_photo_asks(rig):
    helper, jdxi, eds = rig
    editor = eds["analog"]
    session = session_of(editor)
    a = capture(session, "A")
    edit(editor, "AMP_LEVEL", 9)
    assert not session.capture("A", confirm_overwrite=lambda s: False)
    assert session.slots["A"].blocks == a.blocks
    replaced = capture(session, "A", confirm_overwrite=lambda s: True)
    assert replaced.blocks != a.blocks


def test_tc17_photos_stay_with_their_part_and_come_back(rig, store):
    from jdxi_editor.ui.v2.digital import Digital2ToneEditor, DigitalToneEditor

    helper, jdxi, eds = rig
    a1 = capture(session_of(eds["digital_1"]), "A")
    edit(eds["analog"], "AMP_LEVEL", 20)
    b_analog = capture(session_of(eds["analog"]), "B")
    assert session_of(eds["digital_2"]).slots == {"A": None, "B": None}
    assert session_of(eds["analog"]).slots["A"] is None
    assert sorted(p.name for p in store.iterdir()) == ["analog.json", "digital_1.json"]
    again = DigitalToneEditor(helper, Mock())  # a new editor (or a restart)
    try:
        kept = session_of(again).slots["A"]
        assert kept.blocks == a1.blocks and kept.epoch is None and session_of(again).slots["B"] is None
        assert recall(session_of(again), "A", confirm_context=lambda s: True)
    finally:
        again.close()
        again.deleteLater()
    assert session_of(eds["analog"]).slots["B"].blocks == b_analog.blocks


# ------------------------------------------------------------------ TC-18
def test_tc18_undo_redo_and_reload_are_untouched(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    history = editor.history
    edit(editor, "TONE_LEVEL", 33)
    steps = len(history._undo)
    capture(session, "A")
    assert len(history._undo) == steps  # capturing is not an edit
    edit(editor, "TONE_LEVEL", 66)
    assert recall(session, "A")
    assert editor.pv("TONE_LEVEL").value() == 33
    edit(editor, "TONE_LEVEL", 99)
    assert history.undo() and editor.pv("TONE_LEVEL").value() == 33  # the edit after the recall
    assert history.redo() and editor.pv("TONE_LEVEL").value() == 99
    assert callable(editor.reload_sound) and editor.CAN_RELOAD


# ------------------------------------------------------------------ the rest
def test_an_incompatible_photo_is_not_recalled(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    session = session_of(editor)
    capture(session, "A")
    messages = []
    session.message.connect(lambda text, problem: messages.append(text))
    session.slots["A"].schema = ab.SCHEMA_VERSION + 1
    assert not session.recall("A") and "version" in messages[-1]
    session.slots["A"].schema = ab.SCHEMA_VERSION
    session.slots["A"].part = "analog"
    assert not session.recall("A") and "Analog" in messages[-1]
    session.slots["A"].part = "digital_1"
    session.slots["A"].blocks[1] = session.slots["A"].blocks[1][:-6] + "00f7"  # bad checksum
    assert not session.recall("A") and "incomplete" in messages[-1]


def test_the_ab_bar_is_on_the_synth_editors_only(rig):
    from jdxi_editor.ui.v2.drums import DrumKitEditor

    helper, jdxi, eds = rig
    for editor in eds.values():
        assert editor.ab_control.isVisibleTo(editor) or editor.ab_control.parent() is not None
    drums = DrumKitEditor(helper, Mock())
    try:
        assert getattr(drums, "ab_control", None) is None
    finally:
        drums.close()
        drums.deleteLater()


def test_choose_a_slot_and_capture_then_recall_and_switch(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_2"]
    control = editor.ab_control
    session = control.session
    control.buttons["A"].click()  # empty: only chosen
    assert session.selected == "A" and session.slots["A"] is None
    control.camera.click()
    assert pump(lambda: session.slots["A"] is not None and not session.busy)
    assert not control.swap.isEnabled()  # B still empty
    control.buttons["B"].click()
    edit(editor, "TONE_LEVEL", 7)
    control.camera.click()
    assert pump(lambda: session.slots["B"] is not None and not session.busy)
    assert control.swap.isEnabled() and session.active is None
    control.buttons["A"].click()  # full: recalled
    assert pump(lambda: session.active == "A")
    assert control.buttons["A"].active and not control.buttons["B"].active
    control.swap.click()
    assert pump(lambda: session.active == "B")
    control.shortcut.activated.emit()  # Ctrl+Shift+A
    assert pump(lambda: session.active == "A")
    assert control.disk.isEnabled() and control.target() == "A"


def test_without_the_jdxi_what_needs_it_is_disabled(rig):
    helper, jdxi, eds = rig
    editor = eds["analog"]
    control = editor.ab_control
    session = control.session
    capture(session, "A")
    capture(session, "B")
    assert recall(session, "A") and session.active == "A"
    helper.midi_out.is_port_open.return_value = False
    control._connection_check()
    assert session.active is None  # what the JD-Xi plays when back is not known
    assert not control.swap.isEnabled()
    assert control.camera.isEnabled() and control.disk.isEnabled()
    assert "Connect the JD-Xi" in control.buttons["A"].toolTip()
    jdxi.writes.clear()
    control.buttons["A"].click()  # chosen, not recalled
    assert session.selected == "A" and session.active is None and jdxi.writes == []
    assert control.buttons["A"].selected and not control.buttons["A"].active
    helper.midi_out.is_port_open.return_value = True
    control._connection_check()
    assert control.swap.isEnabled()


def test_a_notice_does_not_move_the_bar(rig):
    helper, jdxi, eds = rig
    editor = eds["digital_1"]
    editor.resize(1400, 800)
    editor.show()
    QApplication.processEvents()
    control = editor.ab_control
    where = {name: b.mapTo(editor, b.rect().topLeft()) for name, b in control.buttons.items()}
    control.show_message("A long notice " * 6, True)
    QApplication.processEvents()
    assert control.toast.isVisible()
    assert {name: b.mapTo(editor, b.rect().topLeft()) for name, b in control.buttons.items()} == where
    control.toast.mousePressEvent(None)  # a problem goes when clicked
    assert not control.toast.isVisible()
    editor.hide()
