"""Core tabs always there; Program parts, Recipes and Settings open and close from the editors window."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QTabBar


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    w = JDXiInstrument()
    w.show()
    for _ in range(20):
        app.processEvents()
    yield w
    w.close()


def _names(window):
    tabs = window.main_editor.editor_tab_widget
    return [tabs.tabToolTip(i) for i in range(tabs.count())]


def test_core_tabs_have_no_close_button(window):
    tabs = window.main_editor.editor_tab_widget
    program = window._tab_editor("program")
    index = tabs.indexOf(program)
    assert index >= 0
    assert tabs.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide) is None
    window.close_tab(index)  # ignored
    assert tabs.indexOf(program) == index


def test_open_close_and_reopen_keeps_the_editor(window):
    tabs = window.main_editor.editor_tab_widget
    window.open_tab("recipes")
    recipes = window._tab_editor("recipes")
    index = tabs.indexOf(recipes)
    assert index >= 0 and "recipes" in window.open_optional_tabs()
    close = tabs.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide)
    assert close is not None
    close.click()  # the × on the tab
    assert tabs.indexOf(recipes) == -1 and "recipes" not in window.open_optional_tabs()
    window.open_tab("recipes")
    assert window._tab_editor("recipes") is recipes and tabs.indexOf(recipes) >= 0  # the same editor
    assert tabs.currentWidget() is recipes


def test_the_plus_menu_lists_the_optional_tabs(window):
    from PySide6.QtWidgets import QMenu

    menu = QMenu()
    window._fill_tab_menu(menu)
    actions = menu.actions()
    assert len(actions) == len(window.OPTIONAL_TABS)
    ticked = {a.text() for a in actions if a.isChecked()}
    assert ticked  # recipes is open (previous test) at least
    assert window.main_editor.tab_menu_button.isVisibleTo(window.main_editor)


def test_open_tabs_are_remembered(window):
    window.open_tab("program_parts")
    assert "program_parts" in window._saved_optional_tabs()
    tabs = window.main_editor.editor_tab_widget
    window.close_tab(tabs.indexOf(window._tab_editor("program_parts")))
    assert "program_parts" not in window._saved_optional_tabs()
