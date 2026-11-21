"""Core tabs always there; Program settings, Recipes and Settings open and close from the editors window."""

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


def test_program_settings_opens_after_programs(window):
    tabs = window.main_editor.editor_tab_widget
    window.open_tab("program_parts")
    settings = window._tab_editor("program_parts")
    assert tabs.indexOf(settings) == tabs.indexOf(window._tab_editor("program")) + 1
    assert tabs.tabText(tabs.indexOf(settings)) == "Program settings"
    window.close_tab(tabs.indexOf(settings))
    window.open_tab("recipes")  # another tab added at the end meanwhile
    window.open_tab("program_parts")  # back: again right after Programs
    assert tabs.indexOf(settings) == tabs.indexOf(window._tab_editor("program")) + 1
    window.close_tab(tabs.indexOf(settings))


def test_the_programs_mixer_has_pan_and_sends_of_program_settings(window):
    from jdxi_editor.core.synth.type import JDXiSynth

    app = QApplication.instance()
    for _ in range(5):
        app.processEvents()
    programs = window._tab_editor("program")
    settings = window.program_settings_editor()
    tabs = window.main_editor.editor_tab_widget
    assert settings is window._tab_editor("program_parts")  # one editor, made without its tab
    pan, delay, reverb = programs.part_sends[JDXiSynth.ANALOG_SYNTH]
    assert [k.name.text() for k in (pan, delay, reverb)] == ["Pan", "Delay", "Reverb"]
    assert pan.pv is settings.part("PART_PAN", 2)  # Analog is the settings' third part
    pan.pv.setValue(-20)
    assert settings.part("PART_PAN", 2).value() == -20  # the same value
    output = settings.part("PART_OUTPUT_ASSIGN", 2)
    output.setValue(4)  # DIR: no effect, no sends
    assert not delay.isEnabled() and not reverb.isEnabled()
    output.setValue(3)  # REV: the reverb only
    assert not delay.isEnabled() and reverb.isEnabled()
    output.setValue(0)
    # the mixer's read of the program asks for the parts too
    assert len(programs._part_requests()) == 4
    # the faders keep their length: the strips grew by the knobs
    master, analog = programs.mixer_widget.tracks[0].slider, programs.mixer_widget.tracks[4].slider
    assert master.height() == analog.height() > 180


def test_the_faders_are_the_editors_levels_and_programs_undoes_them(window):
    from jdxi_editor.ui.v2 import history

    app = QApplication.instance()
    for _ in range(5):
        app.processEvents()
    programs = window._tab_editor("program")
    digital1 = window._tab_editor("digital1")
    settings = window.program_settings_editor()
    level = next(pv for spec, pv in digital1.values.items() if spec.name == "TONE_LEVEL")
    master = next(pv for spec, pv in settings.values.items() if spec.name == "PROGRAM_LEVEL")
    assert programs.level_links[1] is level and programs.level_links[0] is master
    fader = programs.mixer_widget.tracks[1].slider
    start = level.value()
    fader.setValue(start - 10 if start >= 10 else start + 10)  # as the user does
    moved = fader.value()
    assert level.value() == moved  # the tone's level: an edit of Digital 1
    assert digital1.history.can_undo() and programs.program_history.can_undo()
    assert "Digital 1" in programs.program_history.undo_text()
    level.setValue(start)  # from the Digital 1 tab: the fader follows
    assert fader.value() == start
    level.setValue(moved)
    # Programs' Undo: the last change of the program, whatever the tab
    tabs = window.main_editor.editor_tab_widget
    tabs.setCurrentWidget(programs)
    programs.show()
    assert window.active_history() is programs.program_history
    assert programs.program_history.undo()
    assert level.value() == start and fader.value() == start
    assert programs.program_history.redo()
    assert fader.value() == moved
    # back as it was, nothing left modified for the next tests
    for h in history.histories():
        h.reset()
