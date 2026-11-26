"""Core tabs always there; Program settings, Recipes and Settings always there too,
reduced to a bar or expanded, from the editors window."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QTabBar

from jdxi_editor.ui.editors.collapsible_tabs import COLLAPSED_WIDTH


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


def _bar(window):
    return window.main_editor.editor_tab_widget.tabBar()


def test_core_tabs_cannot_be_reduced(window):
    tabs = window.main_editor.editor_tab_widget
    program = window._tab_editor("program")
    index = tabs.indexOf(program)
    assert index >= 0
    assert tabs.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide) is None
    window.collapse_tab("program")  # ignored
    assert not _bar(window).is_collapsed(index) and tabs.tabText(index)


def test_the_optional_tabs_are_always_in_the_bar(window):
    tabs = window.main_editor.editor_tab_widget
    for name in window.OPTIONAL_TABS:
        assert tabs.indexOf(window._tab_editor(name)) >= 0, name
    assert not hasattr(window.main_editor, "tab_menu_button")  # no "+" any more


def test_reduce_and_expand_keeps_the_editor(window):
    tabs = window.main_editor.editor_tab_widget
    bar = _bar(window)
    window.open_tab("recipes")
    recipes = window._tab_editor("recipes")
    index = tabs.indexOf(recipes)
    assert tabs.currentWidget() is recipes and not bar.is_collapsed(index)
    assert "recipes" in window.open_optional_tabs()
    reduce = bar.tabButton(index, QTabBar.ButtonPosition.RightSide)
    assert reduce is not None and reduce.text() == "◂"
    reduce.click()
    assert bar.is_collapsed(index) and tabs.indexOf(recipes) == index  # still there, as a bar
    assert tabs.tabText(index) == "" and bar.tabSizeHint(index).width() == COLLAPSED_WIDTH
    assert tabs.currentWidget() is not recipes  # the window moved off it
    assert "Recipes" in tabs.tabToolTip(index)  # its name when the mouse is on the bar
    assert "recipes" not in window.open_optional_tabs()
    tabs.setCurrentIndex(index)  # a click on the bar
    assert not bar.is_collapsed(index) and tabs.tabText(index) == "Recipes"
    assert window._tab_editor("recipes") is recipes and tabs.currentWidget() is recipes


def test_the_state_is_remembered(window):
    window.open_tab("program_parts")
    assert "program_parts" in window._saved_optional_tabs()
    window.collapse_tab("program_parts")
    assert "program_parts" not in window._saved_optional_tabs()


def test_program_settings_sits_after_programs(window):
    tabs = window.main_editor.editor_tab_widget
    settings = window._tab_editor("program_parts")
    assert tabs.indexOf(settings) == tabs.indexOf(window._tab_editor("program")) + 1
    window.open_tab("program_parts")
    assert tabs.tabText(tabs.indexOf(settings)) == "Program settings"
    window.collapse_tab("program_parts")


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


def test_the_mixer_card_is_level_with_the_library(window):
    app = QApplication.instance()
    programs = window._tab_editor("program")
    window._show_main_editor()
    window.main_editor.editor_tab_widget.setCurrentWidget(programs)
    for _ in range(10):
        app.processEvents()
    library, mixer = programs._library_card, programs._mixer_card
    top = lambda w: w.mapTo(programs, w.rect().topLeft()).y()  # noqa: E731
    assert top(library) == top(mixer)
