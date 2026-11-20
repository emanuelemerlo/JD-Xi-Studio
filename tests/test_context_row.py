"""
The context line (sound-design spec §4, Phase 3): program › part › tone ·
origin · state, the same in every editor and on the Programs page.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from jdxi_editor.midi.io import connection as conn
from jdxi_editor.ui.v2 import context as ctx


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class History(QObject):
    modifiedChanged = Signal(bool)

    def __init__(self, part):
        super().__init__()
        self.part = part
        self.modified = False

    def set_modified(self, value):
        self.modified = value
        self.modifiedChanged.emit(value)


class Editor(QWidget):
    def __init__(self, part):
        super().__init__()
        self.history = History(part)
        self.name_field = QLineEdit()


@pytest.fixture
def fresh(monkeypatch):
    monkeypatch.setattr(ctx, "_context", None)
    return ctx.sound_context()


def test_a_tone_editor_says_where_and_what(app, fresh):
    editor = Editor("analog")
    editor.name_field.setText("Springer")
    helper = Mock()
    row = ctx.ContextRow(editor, helper)
    connection = conn.connection_for(helper)
    connection.set_state_for_tests(conn.ONLINE)
    assert row.plain_text() == "No program loaded › Analog › tone «Springer» · original"
    fresh.program_loaded("A11", "CARONDO")
    assert row.plain_text() == ("Program A11 «CARONDO» › Analog › tone «Springer» · origin: program A11 · original")
    fresh.part_origin("analog", "preset A-05")
    editor.history.set_modified(True)
    assert row.plain_text().endswith("origin: preset A-05 · modified, temporary")
    connection.set_state_for_tests(conn.OFFLINE)
    assert row.plain_text().endswith("modified, not sent (Off-line)")
    assert "modified" in row.text() and "<b" in row.text()


def test_the_reference_follows_loads_and_saves(app, fresh):
    editor = Editor("digital_1")
    row = ctx.ContextRow(editor)
    fresh.program_loaded("E12", "My Bass")
    fresh.file_saved("/x/My Bass.msz")
    assert row.plain_text().endswith("saved to file «My Bass.msz»")
    fresh.file_saved("/x/Other.msz", loaded=True)
    assert "origin: file «Other.msz»" in row.plain_text()
    fresh.slot_saved("E14")
    assert row.plain_text().startswith("Program E14") and row.plain_text().endswith("saved in E14")
    editor.history.set_modified(True)
    # no connection known (no MIDI helper): not sent, never «temporary» (review 4.1)
    assert row.plain_text().endswith("modified, not sent (Off-line)")


def test_a_file_saved_after_a_slot_is_the_reference(app, fresh):
    """Saved in E14, changed, then saved to a file: E14 no longer holds the
    sound, the state is the file's (the last save wins)."""
    editor = Editor("digital_1")
    row = ctx.ContextRow(editor)
    fresh.program_loaded("E12", "My Bass")
    fresh.slot_saved("E14")
    assert row.plain_text().endswith("saved in E14")
    editor.history.set_modified(True)
    fresh.file_saved("/x/My Bass 2.msz")
    editor.history.set_modified(False)
    assert row.plain_text().endswith("saved to file «My Bass 2.msz»")
    fresh.slot_saved("E15")
    assert row.plain_text().endswith("saved in E15")


def test_the_programs_page_shows_the_program_and_any_modified_part(app, fresh, monkeypatch):
    from jdxi_editor.ui.v2 import history

    changed = Mock(modified=False)
    monkeypatch.setattr(history, "histories", lambda *a, **k: [changed])
    row = ctx.ContextRow(None)
    fresh.program_loaded("B03", "CLUBBIN'")
    assert row.plain_text() == "Program B03 «CLUBBIN'» · original"
    changed.modified = True
    assert row.plain_text() == "Program B03 «CLUBBIN'» · modified, not sent (Off-line)"
