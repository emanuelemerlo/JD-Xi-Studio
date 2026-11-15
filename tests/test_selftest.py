"""Help › Self-test with the JD-Xi: the runner, a few steps against a fake JD-Xi, the report."""

from __future__ import annotations

import mido
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from jdxi_editor.ui.windows import selftest as st


class FakeJDXi:
    """Answers RQ1 from a memory that DT1 messages from the app write to."""

    def __init__(self, helper):
        self.helper = helper
        self.memory = {}

    def write(self, address, values):
        base = (address[0] << 21) | (address[1] << 14) | (address[2] << 7) | address[3]
        for i, v in enumerate(values):
            self.memory[base + i] = v

    def request(self, messages):
        for m in messages:
            m = list(m)
            if len(m) > 15 and m[7] == 0x11:
                address = tuple(m[8:12])
                size = (m[12] << 21) | (m[13] << 14) | (m[14] << 7) | m[15]
                base = (address[0] << 21) | (address[1] << 14) | (address[2] << 7) | address[3]
                values = [self.memory.get(base + i, 0) for i in range(size)]
                checksum = (128 - sum(list(address) + values) % 128) % 128
                reply = mido.Message("sysex", data=[0x41, 0x10, 0, 0, 0, 0x0E, 0x12, *address, *values, checksum])
                QTimer.singleShot(5, lambda r=reply: self.helper._handle_midi_message(r))
        return len(messages)

    keep = True  # False: a JD-Xi that ignores the DT1s

    def sent(self, message):
        m = list(message)
        if self.keep and m and m[0] == 0xF0 and len(m) > 12 and m[7] == 0x12:
            self.write(tuple(m[8:12]), m[12:-2])
        self.helper.midi_message_outgoing.emit(message)  # as the real send_raw_message
        return True


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    w = JDXiInstrument()
    w.show()
    for _ in range(10):
        app.processEvents()
    yield w
    w.close()
    _dispose(w)


@pytest.fixture
def jdxi(window, monkeypatch):
    fake = FakeJDXi(window.midi_helper)
    fake.write(st.PROGRAM_COMMON, list(b"Unleash Xi  "))
    system = [0] * 0x2B
    system[0x11], system[0x29], system[0x2A] = 15, 1, 1
    fake.write(st.SYSTEM_COMMON, system)
    fake.write(st.ANALOG_CUTOFF, [64])
    fake.write(st.ANALOG_OCTAVE, [64])
    monkeypatch.setattr(st, "device_for", lambda helper: fake)
    monkeypatch.setattr(window.midi_helper, "send_raw_message", fake.sent)
    monkeypatch.setattr(window.midi_helper, "midi_out", object(), raising=False)
    return fake


def run(test, answers=(), actions=None, limit_s=20):
    """Run to the end, answering questions in order and doing *actions* while waiting."""
    import time

    answers = list(answers)
    test.asking.connect(lambda q, h: q and QTimer.singleShot(10, lambda: test.answer(answers.pop(0) if answers else None)))
    if actions:
        test.waiting.connect(lambda text: text and QTimer.singleShot(50, actions))
    done = []
    test.finished.connect(lambda: done.append(True))
    test.start()
    deadline = time.monotonic() + limit_s
    while not done and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)
    assert done, "the self-test did not finish"


def test_rq1_checksum():
    assert st.rq1((0x19, 0x42, 0x00, 0x00), 0x40) == [
        0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x11, 0x19, 0x42, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x65, 0xF7,
    ]


def test_same_name():
    assert st.same_name("Fat as That1", "Fat as That 1")
    assert st.same_name("JP8 Strings1", "JP8 Strings1")
    assert not st.same_name("Unleash Xi", "Dist Seq")
    assert not st.same_name(None, "x")


def test_steps_against_a_fake_jdxi(window, jdxi, tmp_path):
    steps = [
        st.Step("connection", st.step_connection),
        st.Step("system", st.step_system),
        st.Step("edit", st.step_edit_and_undo),
        st.Step("octave", st.step_octave),
        st.Step("note", st.step_note),
        st.Step("keys", st.step_keys_on_jdxi),
    ]
    test = st.SelfTest(window, steps)

    def play():
        for _ in range(3):
            window.midi_helper._handle_midi_message(mido.Message("note_on", note=60, velocity=80))

    run(test, answers=[True, True], actions=play)
    results = {s.title: (s.status, s.detail) for s in steps}
    assert results["connection"][0] == st.OK and "Unleash Xi" in results["connection"][1]
    assert results["system"] == (st.OK, "Program Ctrl Ch 16, Rx Program Change ON, Rx Bank Select ON")
    assert results["edit"][0] == st.OK, results["edit"]
    assert results["octave"] == (st.OK, "0 → +1 → 0")
    assert results["note"][0] == st.OK
    assert results["keys"][0] == st.OK
    report = test.save_report(tmp_path).read_text(encoding="utf-8")
    assert "| 3 | edit | OK |" in report


def test_no_reply_and_a_no_answer(window, monkeypatch):
    silent = type("Silent", (), {"request": lambda self, m: len(m)})()
    monkeypatch.setattr(st, "device_for", lambda helper: silent)
    monkeypatch.setattr(st, "READ_TIMEOUT_MS", 50)
    monkeypatch.setattr(st.Read, "__init__", lambda self, address, size, timeout_ms=50: (
        setattr(self, "address", address), setattr(self, "size", size), setattr(self, "timeout_ms", timeout_ms))[-1])
    steps = [st.Step("connection", st.step_connection), st.Step("note", st.step_note)]
    test = st.SelfTest(window, steps)
    monkeypatch.setattr(window, "handle_piano_note_on", lambda n: None)
    monkeypatch.setattr(window, "handle_piano_note_off", lambda n: None)
    run(test, answers=[False])
    assert steps[0].status == st.KO and "no reply" in steps[0].detail
    assert steps[1].status == st.KO


def test_a_step_that_raises_is_ko_and_the_test_goes_on(window, jdxi):
    def broken(test):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    steps = [st.Step("broken", broken), st.Step("system", st.step_system)]
    test = st.SelfTest(window, steps)
    run(test)
    assert steps[0].status == st.KO and "boom" in steps[0].detail
    assert steps[1].status == st.OK


def test_dialog_opens_from_the_help_menu(window):
    window.show_self_test()
    dialog = window.self_test_dialog
    assert dialog.isVisible()
    assert dialog.table.rowCount() == len(dialog.test.steps) >= 10
    dialog.close()


def test_init_tone_edits_and_undo_on_a_fake_jdxi(window, jdxi):
    """Analog and Digital 1: edits to an Init Tone reach the JD-Xi, Undo brings every value back."""
    jdxi.write(st.ANALOG_TONE, valid_analog_tone())
    for block in window._tab_editor("digital1").blocks:  # every byte a value the parameter can have
        values = [0] * block.size()
        for spec in block.params:
            offset = spec.offset & 0x7F
            if offset < len(values) and not spec.nibbled:
                values[offset] = int(spec.convert_to_midi(min(max(0, spec.lo), spec.hi)))
        jdxi.write(tuple(block.address_bytes()), values)
    jdxi.write(st.DIGITAL1_COMMON, list(b"Init Tone   "))
    steps = [
        st.Step("analog", st.tone_edits("ANALOG_SYNTH", "analog", "ANALOG")),
        st.Step("digital", st.tone_edits("DIGITAL_SYNTH_1", "digital1", "DIGITAL 1")),
    ]
    test = st.SelfTest(window, steps)
    run(test, limit_s=40)
    for step in steps:
        assert step.status == st.OK, (step.title, step.detail)
        assert "Init Tone" in step.detail and "all undone" in step.detail


def valid_analog_tone() -> list:
    from jdxi_editor.midi.data.parameter.analog.address import AnalogParam

    values = [0] * 0x40
    for param in AnalogParam:
        if param.address < 0x40:
            values[param.address] = 64 if param.min_val <= 64 <= param.max_val else param.min_val
    values[:12] = list(b"Init Tone   ")
    return values


def test_edits_the_jdxi_does_not_keep_are_ko(window, jdxi, monkeypatch):
    jdxi.write(st.ANALOG_TONE, valid_analog_tone())
    jdxi.keep = False  # the JD-Xi ignores the DT1s
    steps = [st.Step("analog", st.tone_edits("ANALOG_SYNTH", "analog", "ANALOG"))]
    test = st.SelfTest(window, steps)
    run(test, limit_s=30)
    assert steps[0].status == st.KO and "not on the JD-Xi" in steps[0].detail


def _dispose(window) -> None:
    """Delete the window and the message boxes it opened (offline: «MIDI not available»):
    left alive, their timers slow the next tests and their boxes are counted there."""
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication, QMessageBox

    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, QMessageBox):
            widget.close()
            widget.deleteLater()
    for name in ("main_editor", "self_test_dialog"):
        other = getattr(window, name, None)
        if other is not None:
            other.close()
            other.deleteLater()
    window.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
