"""Programs on one page: library, parts, mixer, and the rest below (same engine)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QGroupBox

from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.midi.program.program import JDXiProgram
from jdxi_editor.ui.editors.program import editor as old_program
from jdxi_editor.ui.v2 import programs

PROGRAMS = [
    JDXiProgram(id="A01", name="Unleash Xi", genre="Dubstep", digital_1="Ah Super Saw", digital_2="Scream",
                drums="TR-909 Kit 4", analog="We'reGoingDn"),
    JDXiProgram(id="A11", name="CARONDO", genre="Trap", digital_1="Tekno Lead 5", digital_2="WaveShapeLd2",
                drums="TR-808 Kit 8", analog="Springer"),
    JDXiProgram(id="E01", name="JG Lead", genre="Lead"),
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app):
    with patch.object(old_program.JDXiUIProgramList, "list_rom_and_user_programs", return_value=list(PROGRAMS)):
        ed = programs.ProgramEditor(midi_helper=MagicMock(), preset_helper=MagicMock())
    yield ed
    ed.close()


def test_same_class_name_and_registered():
    assert programs.ProgramEditor.__name__ == old_program.ProgramEditor.__name__
    from jdxi_editor.ui.windows.jdxi import instrument

    assert instrument.ProgramEditor is programs.ProgramEditor


def test_one_page_with_the_cards(editor):
    assert isinstance(editor, old_program.ProgramEditor)
    titles = {g.title() for g in editor.findChildren(QGroupBox) if g.title()}
    assert {"LIBRARY", "PARTS OF THE PROGRAM", "MIXER"} <= titles
    tabs = [editor.more_tabs.tabText(i) for i in range(editor.more_tabs.count())]
    assert tabs == ["Presets", "User Programs", "Playlist", "Playlist Editor", "System Settings"]
    assert editor.more_tabs.widget(0) is editor.program_group_widget.preset
    assert editor.more_tabs.widget(4) is editor.program_group_widget.system_settings_widget
    assert editor.mixer_panel.isAncestorOf(editor.mixer_widget.mixer_group)


def test_library_filters(editor):
    lib = editor.library
    assert lib.visible_ids() == ["A01", "A11", "E01"]
    lib.set_bank("E")
    assert lib.visible_ids() == ["E01"]
    lib.set_bank("")
    lib.search.setText("caron")
    assert lib.visible_ids() == ["A11"]
    lib.search.clear()
    lib.genre.setCurrentIndex(lib.genre.findData("Dubstep"))
    assert lib.visible_ids() == ["A01"]
    assert "TR-909 Kit 4" in lib.table.item(0, 3).text()


def test_loading_sends_the_program_and_shows_its_parts(editor):
    sent = []
    with patch("jdxi_editor.ui.midi.selection_info.send_program_with_expectation",
               side_effect=lambda helper, pid, **kw: sent.append(pid)):
        editor.data_request = MagicMock()
        editor.library.select("A11")
        assert editor.load_button.isEnabled()
        editor.load_selected_program()
    assert sent == ["A11"] and editor.data_request.called
    assert editor.program_name == "CARONDO" and editor.program_group_widget.program_name == "CARONDO"
    row = editor.part_rows[JDXiSynth.DRUM_KIT]
    assert editor.part_tables.item(row, 1).text() == "TR-808 Kit 8"
    editor.update_tone_name_for_synth("New Analog", JDXiSynth.ANALOG_SYNTH)
    assert editor.part_tables.item(editor.part_rows[JDXiSynth.ANALOG_SYNTH], 1).text() == "New Analog"


def test_parts_open_their_editors(editor):
    instrument = MagicMock()
    editor._get_parent_instrument = lambda: instrument
    editor.open_part_editor(2)
    editor.open_advanced()
    assert [c.args[0] for c in instrument.show_editor.call_args_list] == ["drums", "program_parts"]
