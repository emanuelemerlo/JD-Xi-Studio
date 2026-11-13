"""Undo / redo of the user's changes, the Modified mark and the warning before they are lost."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from jdxi_editor.ui.v2 import history as h


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def asks(monkeypatch, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(h, "asks_before_discarding", lambda settings_=None: settings.value(h.CONFIRM_KEY, True, type=bool))
    monkeypatch.setattr(h, "_paused", 0)
    for other in h.histories():  # editors of earlier tests: nothing modified
        other.reset()
    return settings


def _pv(app, value=0):
    from jdxi_editor.ui.v2.params import ParamInfo, ParamValue

    info = Mock(spec=ParamInfo)
    info.step = 1
    pv = ParamValue(Mock(), info, 0, 127)
    pv.setValue(value)
    return pv


def _history(app, part=h.DIGITAL_1, *values):
    history = h.EditHistory(part, "Digital 1")
    history.watch(values)
    return history


def test_undo_redo_and_modified(app, monkeypatch):
    a, b = _pv(app, 10), _pv(app, 20)
    history = _history(app, h.DIGITAL_1, a, b)
    assert not history.modified and not history.can_undo()
    a.setValue(30)
    monkeypatch.setattr(h, "MERGE_SECONDS", 0)  # separate edits
    b.setValue(40)
    assert history.modified
    assert history.undo() and b.value() == 20
    assert history.undo() and a.value() == 10
    assert not history.modified and not history.can_undo()
    assert history.redo() and a.value() == 30 and history.modified
    a.setValue(31)  # a new edit: nothing left to redo
    assert not history.can_redo()


def test_a_drag_is_one_edit(app):
    a = _pv(app, 0)
    history = _history(app, h.DIGITAL_1, a)
    for value in range(1, 60):
        a.setValue(value)
    assert history.undo() and a.value() == 0
    assert not history.can_undo()


def test_grouped_edit_is_one_undo_redo(app):
    a, b = _pv(app, 10), _pv(app, 20)
    history = _history(app, h.ANALOG, a, b)
    history.begin_group()
    a.setValue(30)
    a.setValue(40)
    b.setValue(50)
    history.end_group()

    assert history.undo() and (a.value(), b.value()) == (10, 20)
    assert not history.can_undo() and history.can_redo()
    assert history.redo() and (a.value(), b.value()) == (40, 50)


def test_revert_restores_values_and_clears_history(app, monkeypatch):
    from types import SimpleNamespace

    from jdxi_editor.ui.v2.framework import restore_sound

    a, b = _pv(app, 10), _pv(app, 20)
    history = _history(app, h.ANALOG, a, b)
    a.setValue(30)
    b.setValue(50)
    monkeypatch.setattr(h, "ask", lambda *args, **kwargs: "discard")

    restore_sound(SimpleNamespace(history=history))
    assert (a.value(), b.value()) == (10, 20)
    assert not history.modified and not history.can_undo() and not history.can_redo()


def test_values_from_the_jdxi_are_not_edits(app):
    a = _pv(app, 0)
    history = _history(app, h.DIGITAL_1, a)
    a.blockSignals(True)
    a.setValue(99)
    a.blockSignals(False)
    assert not history.modified and not history.can_undo()


def test_saved_then_changed(app):
    a = _pv(app, 0)
    history = _history(app, h.DIGITAL_1, a)
    a.setValue(5)
    history.mark_saved()
    assert not history.modified
    a.setValue(6)  # right after: not merged into the saved edit
    assert history.modified
    history.undo()
    assert not history.modified and a.value() == 5


def test_confirm_discard(app, monkeypatch, asks):
    a = _pv(app, 0)
    history = _history(app, h.ANALOG, a)
    other = _history(app, h.DIGITAL_2, _pv(app))
    a.setValue(3)
    answers = []
    monkeypatch.setattr(h, "ask", lambda labels, action, parent=None: answers.pop(0))
    assert h.confirm_discard([h.DIGITAL_2], "x")  # another part: not asked
    answers.append("cancel")
    assert not h.confirm_discard([h.ANALOG], "x") and history.modified
    saved = []
    monkeypatch.setattr(h, "save_callback", lambda: saved.append(1))
    answers.append("save")
    assert not h.confirm_discard([h.ANALOG], "x") and saved == [1] and history.modified
    answers.append("discard")
    assert h.confirm_discard([h.ANALOG], "x")
    assert not history.modified and not history.can_undo()
    a.setValue(4)
    asks.setValue(h.CONFIRM_KEY, False)  # Preferences: do not ask
    assert h.confirm_discard([h.ANALOG], "x") and not history.modified
    del other


def test_program_change_guard(app, monkeypatch):
    from jdxi_editor.midi.io import output_handler
    from jdxi_editor.midi.io.output_handler import MidiOutHandler

    handler = MidiOutHandler.__new__(MidiOutHandler)
    sent = []
    handler._send_bank_select_and_program_change = lambda *args: sent.append(args) or True
    handler._send_program_change = lambda *args: sent.append(args) or True
    asked = []
    monkeypatch.setattr(output_handler, "PROGRAM_CHANGE_GUARD", lambda channel: asked.append(channel) or channel != 2)
    assert handler.send_bank_select_and_program_change(0, 87, 64, 1)
    assert not handler.send_bank_select_and_program_change(2, 87, 64, 1)
    assert not handler.send_program_change(5, 2)
    assert asked == [0, 2, 2] and len(sent) == 1
    with h.paused():
        assert h.program_change_allowed(15)
    assert h.part_of_synth("DIGITAL_SYNTH_2") == h.DIGITAL_2 and h.part_of_synth("VOCAL_FX") == h.PROGRAM


def test_editors_record_and_undo(app, monkeypatch):
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.analog import AnalogToneEditor
    from jdxi_editor.ui.v2.digital import Digital2ToneEditor

    for cls, part in ((Digital2ToneEditor, h.DIGITAL_2), (AnalogToneEditor, h.ANALOG)):
        helper = MidiIOHelper()
        helper.send_midi_message = lambda message: True
        editor = cls(helper, Mock())
        try:
            assert editor.history.part == part
            pv = next(iter(editor.values.values()))
            start = pv.value()
            pv.setValue(pv.minimum if start != pv.minimum else pv.maximum)
            assert editor.history.modified and editor.edit_buttons[0].isEnabled()
            assert len(editor.edit_buttons) == 3  # undo, redo, reload
            assert editor.edit_buttons[2].isEnabled()
            assert not editor.modified_label.isHidden()
            editor.history.undo()
            assert pv.value() == start and editor.modified_label.isHidden()
            assert not editor.edit_buttons[2].isEnabled()  # nothing to restore
        finally:
            editor.close()
            editor.deleteLater()


def test_program_editors_have_undo_but_no_reload(app):
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.effects import EffectsEditor

    editor = EffectsEditor(midi_helper=MidiIOHelper())
    try:
        assert editor.history.part == h.PROGRAM and len(editor.edit_buttons) == 2
    finally:
        editor.close()
        editor.deleteLater()


def test_deleted_editors_are_left_out(app):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QWidget

    owner = QWidget()
    a = _pv(app, 0)
    history = h.EditHistory(h.DRUMS, "Drums", owner)
    history.watch([a])
    a.setValue(9)
    owner.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert history not in h.histories([h.DRUMS])
    assert h.confirm_discard([h.DRUMS], "x")  # no crash on the deleted one


def test_a_press_without_release_does_not_leave_a_group_open(app):
    a = _pv(app, 10)
    history = _history(app, h.ANALOG, a)
    history.begin_group()  # pressed, no release
    a.setValue(20)
    history.end_group()  # what the next press does first
    a.setValue(30)
    assert history._group_depth == 0 and history.undo() and a.value() == 20
