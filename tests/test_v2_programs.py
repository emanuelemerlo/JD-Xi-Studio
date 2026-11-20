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
    from jdxi_editor.midi.io import connection as conn

    ed.connection.set_state_for_tests(conn.ONLINE)  # a JD-Xi there
    yield ed
    ed.close()


def test_same_class_name_and_registered():
    assert programs.ProgramEditor.__name__ == old_program.ProgramEditor.__name__
    from jdxi_editor.ui.windows.jdxi import instrument

    assert instrument.ProgramEditor is programs.ProgramEditor


def test_one_page_with_the_cards(editor):
    assert isinstance(editor, old_program.ProgramEditor)
    titles = {g.title() for g in editor.findChildren(QGroupBox) if g.title()}
    assert {"LIBRARY", "PARTS AND MIXER"} <= titles
    tabs = [editor.more_tabs.tabText(i) for i in range(editor.more_tabs.count())]
    assert tabs == ["Organize: playlists"]  # presets: from each part; user programs: banks E–H
    organize = editor.more_tabs.widget(0)
    assert organize.isAncestorOf(editor.playlist_widget) and organize.isAncestorOf(editor.playlist_editor_widget)
    # moved from the old editor's hidden tabs: not left hidden (the area looked empty)
    assert not editor.playlist_widget.isHidden() and not editor.playlist_editor_widget.isHidden()
    assert editor.mixer_panel.isAncestorOf(editor.mixer_widget.mixer_group)
    assert set(editor.part_tones) == {JDXiSynth.DIGITAL_SYNTH_1, JDXiSynth.DIGITAL_SYNTH_2,
                                      JDXiSynth.DRUM_KIT, JDXiSynth.ANALOG_SYNTH}


def test_library_filters(editor):
    lib = editor.library
    assert lib.visible_ids() == ["A01", "A11", "E01"]
    lib.set_bank("E")
    assert lib.visible_ids() == ["E01"]
    lib.set_bank("")
    lib.search.setText("caron")
    assert lib.visible_ids() == ["A11"]
    lib.search.setText("springer")  # a tone (PR-08)
    assert lib.visible_ids() == ["A11"]
    lib.search.setText("lead")  # name of E01, tone of A11, genre of E01
    assert lib.visible_ids() == ["A11", "E01"]
    lib.search.clear()
    lib.genre.setCurrentIndex(lib.genre.findData("Dubstep"))
    assert lib.visible_ids() == ["A01"]
    assert "TR-909 Kit 4" in lib.table.item(0, 3).text()
    assert lib.count_label.text() == "1 of 3 programs"
    lib.genre.setCurrentIndex(0)
    lib.set_bank("A")
    lib.search.setText("x")  # combined: bank A, text (PR-09)
    assert lib.visible_ids() == ["A01"]
    lib.search.clear()
    lib.set_bank("")


def test_library_sorts_and_colours_the_tones(editor):
    from PySide6.QtCore import Qt

    lib = editor.library
    lib.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)  # by name (PR-10)
    assert lib.visible_ids() == ["A11", "E01", "A01"]
    lib.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    assert lib.visible_ids() == ["E01", "A11", "A01"]
    lib.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    tones = lib.table.item(0, 3).data(programs.TONES_ROLE)
    from jdxi_editor.ui.v2.brand import PART_COLOURS

    assert [c for _n, c in tones] == list(PART_COLOURS) and tones[2][0] == "TR-909 Kit 4"


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
    assert editor.part_tone(JDXiSynth.DRUM_KIT) == "TR-808 Kit 8"
    editor.update_tone_name_for_synth("New Analog", JDXiSynth.ANALOG_SYNTH)
    assert editor.part_tone(JDXiSynth.ANALOG_SYNTH) == "New Analog"
    # the loaded program is marked, apart from the selected one (PR-27)
    lib = editor.library
    assert lib.loaded_id == "A11"
    lib.select("A01")
    row = next(r for r in range(lib.table.rowCount()) if lib.table.item(r, 0).data(256) == "A11")
    assert lib.table.item(row, 0).text().startswith("▶") and lib.table.item(row, 1).font().bold()
    assert lib.selected_id() == "A01"


def test_parts_open_their_editors(editor):
    instrument = MagicMock()
    editor._get_parent_instrument = lambda: instrument
    editor.open_part_editor(2)
    editor.open_advanced()
    assert [c.args[0] for c in instrument.show_editor.call_args_list] == ["drums", "program_parts"]


def test_a_part_tone_opens_that_part_s_presets(editor):
    preset = editor.program_group_widget.preset
    dialog = editor.choose_tone(2)  # Drums (PR-25)
    assert dialog is not None and dialog.isAncestorOf(preset)
    assert preset.digital_preset_type_combo.currentIndex() == 2
    assert not preset.digital_preset_type_combo.isEnabled()
    dialog.reject()
    assert not dialog.isAncestorOf(preset) and preset.digital_preset_type_combo.isEnabled()


def test_library_menu_only_offers_what_the_program_allows(editor, monkeypatch):
    lib = editor.library
    lib.set_loaded("A11")

    def actions(program_id):
        menu = lib.build_menu(program_id)
        return {a.text(): a.isEnabled() for a in menu.actions() if a.text()}

    a01 = actions("A01")  # PR-28: not loaded, preset bank
    assert a01["Load A01"] and not a01["Rename…"] and not a01["Export…"] and not a01["Genre…"]
    assert "Delete" not in a01
    a11 = actions("A11")
    assert a11["Rename…"] and a11["Export…"]
    assert actions("E01")["Genre…"]  # a user program: its genre (PR-24)
    saved = []
    monkeypatch.setattr("jdxi_editor.midi.io.input_handler.add_or_replace_program_and_save",
                        lambda p: saved.append(p) or True)
    assert lib.edit_genre("E01", "Ambient")
    assert saved[0].genre == "Ambient" and lib.program("E01").genre == "Ambient"
    assert not lib.edit_genre("A01", "Pop")  # presets keep theirs (PR-23)
    added = []
    monkeypatch.setattr("jdxi_editor.ui.programs.database.get_database",
                        lambda: MagicMock(add_program_to_playlist=lambda pl, pid, *a: added.append((pl, pid)) or True))
    assert lib.add_to_playlist(3, "A01") and added == [(3, "A01")]


def test_without_the_jdxi_nothing_is_loaded_and_says_why(editor):
    from jdxi_editor.midi.io import connection as conn

    sent = []
    with patch("jdxi_editor.ui.midi.selection_info.send_program_with_expectation",
               side_effect=lambda helper, pid, **kw: sent.append(pid)):
        editor.library.select("A11")
        editor.connection.set_state_for_tests(conn.OFFLINE)
        assert not editor.load_button.isEnabled() and "Connect" in editor.load_button.toolTip()
        assert not any(b.isEnabled() for b in editor.part_tones.values())
        menu = editor.library.build_menu("A11")
        assert not next(a for a in menu.actions() if a.text() == "Load A11").isEnabled()
        editor.load_program_by_id("A11")
        assert sent == []
        editor.connection.set_state_for_tests(conn.ONLINE)
        assert editor.load_button.isEnabled() and all(b.isEnabled() for b in editor.part_tones.values())



def test_playlist_commands_apart_from_the_playback(editor):
    """Add / Remove act on the songs: just above their table. Play, Stop,
    Pause, Mix in a compact row of their own with the now-playing line, not
    stretched wider than the songs' commands."""
    playlist = editor.playlist_editor_widget
    select = playlist.playlist_select_layout
    in_select_row = [select.itemAt(i).widget() for i in range(select.count())]
    assert playlist.playlist_actions not in in_select_row
    assert playlist.playlist_actions.isAncestorOf(playlist.add_to_playlist_button)
    assert playlist.playlist_actions.isAncestorOf(playlist.delete_from_playlist_button)
    layout = playlist.layout()
    order = [layout.itemAt(i).widget() for i in range(layout.count())]
    table_at = order.index(playlist.playlist_programs_table)
    assert order[table_at - 1] is playlist.playlist_actions  # right over the songs

    transport = playlist.playlist_transport
    assert transport.shuffle_button.text() == "Mix"
    assert "random order" in transport.shuffle_button.toolTip()
    editor.resize(1400, 900)
    editor.show()
    QApplication.processEvents()
    buttons = (transport.play_button, transport.stop_button, transport.pause_button, transport.shuffle_button)
    for button in buttons:
        assert button.width() <= button.sizeHint().width() + 2  # its own width, not a quarter of the row
    assert max(b.width() for b in buttons) <= playlist.add_to_playlist_button.width()
    # the now-playing line beside the transport
    row_y = transport.mapTo(playlist, transport.rect().center()).y()
    line = playlist.playlist_progress.display
    assert abs(line.mapTo(playlist, line.rect().center()).y() - row_y) < transport.height()
