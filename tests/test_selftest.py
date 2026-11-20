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
    import time

    deadline = time.monotonic() + 0.5  # what earlier tests left on its way arrives first
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    fake = FakeJDXi(window.midi_helper)
    fake.write(st.PROGRAM_COMMON, list(b"Unleash Xi  "))
    system = [0] * 0x2B
    system[0x11], system[0x29], system[0x2A] = 15, 1, 1
    fake.write(st.SYSTEM_COMMON, system)
    fake.write(st.ANALOG_CUTOFF, [64])
    fake.write(st.ANALOG_OCTAVE, [64])
    for name in ("send_midi_message", "send_raw_message"):  # left by other modules' fixtures
        if name in window.midi_helper.__dict__:
            monkeypatch.delitem(window.midi_helper.__dict__, name)
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
        assert "all undone" in step.detail


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


def test_the_main_menus_match_the_app(window, monkeypatch):
    """The menus as the app is now: no Digital 3 (the JD-Xi has two Digital
    parts) nor sheet music; the parts named as their tabs; what talks to the
    JD-Xi in a JD-Xi menu; every shortcut once; every item says what it does."""
    from PySide6.QtWidgets import QMessageBox

    bar = {a.text().replace("&", ""): a for a in window.menuBar().actions() if a.menu() is not None}
    assert list(bar) == ["File", "Editor", "JD-Xi", "Tools", "Window", "Help"]

    def items(title):
        return bar[title].menu().actions()

    texts, shortcuts = [], []

    def walk(actions):
        for action in actions:
            if action.isSeparator() or not action.text():  # separators, section headings
                continue
            if action.menu() is not None:
                walk(action.menu().actions())
                continue
            texts.append(action.text().replace("&", ""))
            if action.shortcut().toString():
                shortcuts.append(action.shortcut().toString())

    for title in bar:
        walk(items(title))
    assert not [t for t in texts if "Synth 3" in t or "PDF" in t]
    assert len(shortcuts) == len(set(shortcuts)), sorted(shortcuts)
    editor = [a.text().replace("&", "") for a in items("Editor") if a.text()]
    assert editor[:5] == ["Programs", "Digital 1", "Digital 2", "Analog", "Drums"]
    # what opens a tab has no «…» nor icon; what opens a dialog ends in «…»
    assert not [a.text() for a in items("Editor") if a.text().endswith("…") or not a.icon().isNull()]
    assert all(a.text().endswith("…") for a in items("JD-Xi") if a.text())
    assert not [a.text() for a in items("JD-Xi") if "JD-Xi" in a.text()]  # the menu says it
    file_menu = {a.text().replace("&", ""): a for a in items("File") if a.text()}
    assert list(file_menu) == ["Patch", "MIDI Player", "Preferences…", "Quit"]
    # Ctrl+O / Ctrl+S are the patch's (the sound), not the MIDI Player's file
    from PySide6.QtGui import QKeySequence

    assert window.save_patch_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Save)
    assert [a.shortcut().toString() for a in window.midi_save_actions] == ["Ctrl+Alt+S", "Ctrl+Alt+Shift+S"]
    # an item that is off looks off
    assert "QMenu::item:disabled" in window.menuBar().styleSheet()
    assert not [a.text() for a in items("Tools") if "Preferences" in a.text()]
    # Save / Save as only with a file in the MIDI Player (none here)
    assert window.midi_save_actions and not [a for a in window.midi_save_actions if a.isEnabled()]
    assert all("Open a MIDI file" in a.toolTip() for a in window.midi_save_actions)
    from types import SimpleNamespace

    monkeypatch.setattr(window, "midifileplayer_instance",
                        SimpleNamespace(midi_state=SimpleNamespace(file=object())), raising=False)
    window._refresh_menu_state()  # what the player calls once a file is loaded
    assert all(a.isEnabled() and "Open a MIDI file" not in a.toolTip() for a in window.midi_save_actions)
    # what needs the JD-Xi is off offline, the tooltip saying why
    if not window.connection.can_talk():
        for action in (window.save_on_jdxi_action, window.dump_settings_action,
                       window.update_user_programs_action, window.self_test_action,
                       window.save_patch_action):
            assert not action.isEnabled() and "Connect the JD-Xi" in action.toolTip(), action.text()
    window_menu = [a.text().replace("&", "") for a in items("Window") if a.text()]
    assert not [t for t in window_menu if "Line up" in t]
    # a button on each window brings the other one in front
    assert window.editors_button.text() == "Editors"
    window._show_main_editor()
    assert window.main_editor.keyboard_button.text() == "Keyboard"
    window.main_editor.keyboard_button.click()
    window.set_keyboard_on_top(True)
    assert "always on top" in window.editors_button.toolTip()
    window.set_keyboard_on_top(False)
    assert "always on top" not in window.editors_button.toolTip()
    for sub in ("Patch", "MIDI Player"):
        for action in file_menu[sub].menu().actions():
            if action.text() and action.menu() is None:
                assert action.toolTip() and action.toolTip() != action.text().replace("&", ""), action.text()
    midi = [a.text().replace("&", "") for a in file_menu["MIDI Player"].menu().actions() if a.text()]
    assert midi[-1] == "Recent"
    # Send all asks first, naming the editors, and does nothing on No
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.StandardButton.No)
    monkeypatch.setattr(window.midi_helper, "midi_out",
                        type("Out", (), {"is_port_open": lambda self: True, "close_port": lambda self: None})())
    sent = []
    monkeypatch.setattr(window.midi_helper, "send_raw_message", lambda m: sent.append(m) or True)
    window._dump_settings_to_synth()
    assert asked and "current program" in asked[0] and sent == []
