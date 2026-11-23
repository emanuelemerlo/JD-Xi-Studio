"""
The recipe editor works by steps: the steps on the left (rename, add,
duplicate, move, delete), the chosen step's rows on the right (add,
duplicate, move, copy and paste, also an AI's rows), the parameter explained
on the right, «not saved» shown, Save as… and Undo changes.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from jdxi_editor.recipes import library
from jdxi_editor.recipes.model import Recipe, Row

_APP = QApplication.instance() or QApplication([])


def _rows():
    return [
        Row(1, "Structure", "D1", "COMMON", "", "Mono/Poly", "valore", "MONO"),
        Row(1, "Structure", "D1", "COMMON", "", "Legato SW", "valore", "ON"),
        Row(2, "Filter", "D1", "FILTER", "1", "Cutoff", "valore", "64"),
        Row(3, "Amp", "D1", "AMP", "1", "Level", "valore", "100"),
    ]


@pytest.fixture
def w(tmp_path, monkeypatch):
    monkeypatch.setenv("JDXI_RECIPES_DIR", str(tmp_path / "recipes"))
    from jdxi_editor.ui.v2.recipes import RecipesEditor

    path = library.save(Recipe(title="Lead", rows=_rows()))
    editor = RecipesEditor()
    editor.resize(1400, 860)
    editor.show()
    editor.refresh_library(path)
    editor.open_selected(edit=True)
    _APP.processEvents()
    yield editor
    editor.close()


def _shown(w):
    return [w._editor_rows()[i].param for i in range(w.ed_table.rowCount()) if not w.ed_table.isRowHidden(i)]


def _steps(w):
    return [w.ed_steps.item(i).text() for i in range(1, w.ed_steps.count())]


def test_the_steps_on_the_left_and_the_chosen_steps_rows(w):
    assert _steps(w) == ["Structure", "Filter", "Amp"]
    assert w.current_step() == 1 and _shown(w) == ["Mono/Poly", "Legato SW"]
    assert w.ed_table.isColumnHidden(0)  # the step's own columns: not needed here
    w.ed_steps.setCurrentRow(0)  # All steps
    assert len(_shown(w)) == 4 and not w.ed_table.isColumnHidden(0)


def test_rename_add_duplicate_move_delete_a_step(w, monkeypatch):
    w.ed_steps.item(2).setText("Dark filter")  # rename «Filter»
    assert [r.step_name for r in w._editor_rows() if r.step == 2] == ["Dark filter"]
    number = w.add_step()
    assert number == 4 and w.current_step() == 4 and len(_shown(w)) == 1
    w._select_step(2)
    copy = w.duplicate_step()
    assert copy == 3 and _steps(w)[2] == "Dark filter (copy)"
    assert [r.step for r in w._editor_rows() if r.param == "Level"] == [4]  # moved down by one
    w._select_step(3)
    w.move_step(-1)
    assert _steps(w)[1] == "Dark filter (copy)" and w.current_step() == 2
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.delete_step()
    assert "Dark filter (copy)" not in _steps(w)
    assert w.editor_has_changes() and "●" in w.where.text()


def test_rows_add_duplicate_move_remove_within_the_step(w):
    w.add_editor_row()
    assert _shown(w) == ["Mono/Poly", "Legato SW", ""]
    w.ed_table.setCurrentCell(0, 7)
    w.duplicate_editor_rows()
    assert _shown(w) == ["Mono/Poly", "Mono/Poly", "Legato SW", ""]
    w.ed_table.setCurrentCell(2, 7)
    w.move_editor_rows(-1)
    assert _shown(w)[:3] == ["Mono/Poly", "Legato SW", "Mono/Poly"]
    w.ed_table.setCurrentCell(3, 7)
    w.remove_editor_row()
    assert _shown(w) == ["Mono/Poly", "Legato SW", "Mono/Poly"]


def test_copy_and_paste_rows_also_from_an_ai(w):
    w._select_step(2)
    w.ed_table.setCurrentCell(2, 7)
    w.copy_editor_rows()
    assert "Cutoff" in QApplication.clipboard().text()
    w._select_step(3)
    w.paste_editor_rows()
    assert _shown(w) == ["Level", "Cutoff"]
    assert {r.step_name for r in w._editor_rows() if r.step == 3} == {"Amp"}
    QApplication.clipboard().setText("```\nPart;Group;Parameter;Value\nD1;FILTER;Resonance;20\n```")
    w.paste_editor_rows()
    assert _shown(w) == ["Level", "Cutoff", "Resonance"]


def test_the_chosen_row_is_explained_on_the_right(w):
    assert not w.info_panel.isVisible()  # the editor needs the width
    w._select_step(2)
    w.ed_table.setCurrentCell(2, 7)
    assert w.info_panel.isVisible() and "Cutoff" in w.info_panel.name.text() + w.info_panel.long.text()


def test_undo_changes_and_save_as(w, monkeypatch, tmp_path):
    assert not w.revert_button.isEnabled()
    w.add_step()
    assert w.revert_button.isEnabled()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.revert_editor()
    assert _steps(w) == ["Structure", "Filter", "Amp"] and not w.editor_has_changes()
    original = w.recipe_path
    w.add_step()
    copy = w.save_as_from_editor("Lead, darker")
    assert copy != original and len(library.load(copy).rows) == 5
    assert len(library.load(original).rows) == 4  # the one opened: as it was
    assert not w.editor_has_changes()
