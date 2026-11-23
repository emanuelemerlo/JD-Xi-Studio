"""
Recipes as one workspace: the library always on the left (search, new, open,
edit, duplicate, export, delete), the work in the middle, the explanation on
the right (closed on the check and the editor, whose tables need the width).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from jdxi_editor.recipes import library
from jdxi_editor.recipes.model import Recipe, Row

_APP = QApplication.instance() or QApplication([])

PASTED = "TONE: FILTER\tCutoff\t60\nTONE: FILTER\tResonance\t20\n"


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setenv("JDXI_RECIPES_DIR", str(tmp_path / "recipes"))
    return tmp_path / "recipes"


def _recipe(title, category="", steps=2):
    rows = [Row(n, f"Step {n}", "D1", "FILTER", "", "Cutoff", "valore", "60") for n in range(1, steps + 1)]
    return Recipe(title=title, category=category, description=f"About {title}", rows=rows)


@pytest.fixture
def editor(lib):
    from jdxi_editor.ui.v2.recipes import RecipesEditor

    library.save(_recipe("Warm pad", "Pad"))
    library.save(_recipe("Saw lead", "Lead", steps=3))
    w = RecipesEditor()
    w.resize(1440, 860)
    w.show()
    _APP.processEvents()
    yield w
    w.close()


def _titles(w):
    return [w.library_list.item(i).text().split("\n")[0] for i in range(w.library_list.count())]


def test_the_library_is_on_the_left_with_dates_and_categories(editor):
    assert _titles(editor) == ["Saw lead", "Warm pad"]
    assert "Lead · " in editor.library_list.item(0).text()  # category · last changed
    assert editor.start_title.text()  # nothing chosen: how to start
    editor.library_list.setCurrentRow(0)
    assert editor.home_stack.currentWidget() is editor.detail_card
    assert editor.detail_title.text() == "Saw lead"
    assert "3" in editor.detail_counts.text() and editor.detail_steps.count() == 3


def test_search(editor):
    editor.search.setText("pad")
    assert _titles(editor) == ["Warm pad"]
    editor.search.setText("nothing like this")
    assert editor.library_list.count() == 1 and editor._selected_path() is None  # «no recipe matches»
    editor.search.clear()
    assert len(_titles(editor)) == 2


def test_duplicate_is_a_recipe_of_its_own(editor, lib):
    editor.library_list.setCurrentRow(1)  # Warm pad
    copy = editor.duplicate_selected()
    assert copy is not None and copy != editor._entries[0][0]
    assert "Warm pad (copy)" in _titles(editor)
    assert editor._selected_recipe().title == "Warm pad (copy)"
    original = [r for _p, r in library.entries() if r.title == "Warm pad"][0]
    assert original.rows == library.load(copy).rows and len(list(lib.glob("*.json"))) == 3


def test_delete_asks_first(editor, monkeypatch):
    editor.library_list.setCurrentRow(0)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    editor.delete_selected()
    assert len(_titles(editor)) == 2
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    editor.delete_selected()
    assert _titles(editor) == ["Warm pad"]


def test_export_from_the_library(editor, tmp_path):
    editor.library_list.setCurrentRow(0)
    target = editor.export_selected(str(tmp_path / "out.csv"))
    assert target.exists() and "Cutoff" in target.read_text(encoding="utf-8-sig")


def test_a_new_recipe_takes_what_was_typed(editor):
    editor.show_create_page()
    assert editor.pages.currentWidget() is editor.create_page
    assert "Pad" in [editor.new_category.itemText(i) for i in range(editor.new_category.count())]
    editor.new_title.setText("My bass")
    editor.new_category.setCurrentText("Bass")
    editor.paste.setPlainText(PASTED)
    editor.import_text()
    assert editor.pages.currentWidget() is editor.check_page
    assert editor.recipe.title == "My bass" and editor.recipe.category == "Bass"
    editor.accept_recipe()
    assert editor._selected_recipe().title == "My bass"  # saved and chosen in the library
    saved = editor._selected_recipe()
    assert saved.category == "Bass" and saved.created and saved.modified


def test_the_name_is_needed_only_to_save(editor):
    editor.show_create_page()
    editor.new_in_editor()
    assert editor.pages.currentWidget() is editor.editor_page
    editor.ed_title.clear()
    editor.save_from_editor()
    assert "name" in editor.ed_status.text().lower()
    assert len(_titles(editor)) == 2  # not saved
    editor.ed_title.setText("From scratch")
    editor.ed_category.setText("FX")
    editor.save_from_editor()
    assert editor._selected_recipe().title == "From scratch" and editor._selected_recipe().category == "FX"


def test_the_right_panel_is_closed_where_the_tables_need_the_width(editor):
    assert editor.info_panel.isVisible() and editor.panel_button.isChecked()
    editor.paste.setPlainText(PASTED)
    editor.show_create_page()
    editor.paste.setPlainText(PASTED)
    editor.import_text()
    assert not editor.info_panel.isVisible()
    editor._explain_row(editor.checked[0])  # a row chosen: its explanation
    assert editor.info_panel.isVisible()
    editor.panel_button.setChecked(False)
    editor.go_back()
    assert editor.info_panel.isVisible()  # the library: open again
    editor.show_create_page()
    editor.paste.setPlainText(PASTED)
    editor.import_text()
    assert not editor.info_panel.isVisible()  # closed, as chosen on this page


def test_opening_another_recipe_from_the_editor_asks_about_unsaved_changes(editor, monkeypatch):
    editor.library_list.setCurrentRow(0)
    editor.open_selected(edit=True)
    editor.add_editor_row()
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.Cancel)
    editor.library_list.setCurrentRow(1)
    editor.open_selected()
    assert asked and editor.pages.currentWidget() is editor.editor_page
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    editor.open_selected()
    assert editor.pages.currentWidget() is editor.guide_page and editor.recipe.title == "Warm pad"


def test_the_title_is_at_the_top_left_as_in_the_other_editors(editor):
    title = editor.title.mapTo(editor, editor.title.rect().topLeft())
    library = editor.sidebar.mapTo(editor, editor.sidebar.rect().topLeft())
    assert title.x() <= library.x() + 2 and title.y() < library.y()


def test_close_goes_back_to_the_start(editor):
    editor.library_list.setCurrentRow(0)
    assert editor.home_stack.currentWidget() is editor.detail_card
    assert tr_texts(editor._recipe_menu())[-1] == "Close"
    editor.close_recipe()
    assert editor._selected_path() is None and editor.home_stack.currentWidget() is editor.start_page
    editor.library_list.setCurrentRow(0)
    editor.open_selected()  # from the guide too
    editor.close_recipe()
    assert editor.pages.currentWidget() is editor.home and editor.home_stack.currentWidget() is editor.start_page


def test_the_menus_highlight_the_item_under_the_mouse(editor):
    menu = editor._recipe_menu()
    assert "QMenu::item:selected" in menu.styleSheet() and "QMenu::item {" in menu.styleSheet()


def test_import_is_the_default_button(editor):
    from jdxi_editor.ui.v2.recipes import PRIMARY

    assert editor.import_button.styleSheet() == PRIMARY and editor.new_button.styleSheet() != PRIMARY
    row = editor.library_buttons
    assert row.indexOf(editor.import_button) < row.indexOf(editor.new_button)  # import first


def tr_texts(menu):
    return [a.text() for a in menu.actions() if not a.isSeparator()]
