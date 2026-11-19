"""A playlist takes the factory programs (A–D) too, as the library shows them,
and the library still lists each program once."""

from __future__ import annotations

from jdxi_editor.ui.programs.database import ProgramDatabase
from jdxi_editor.ui.programs.programs import JDXiUIProgramList


def test_a_factory_program_in_a_playlist(tmp_path):
    db = ProgramDatabase(tmp_path / "programs.db")
    assert db.get_all_programs() == []  # no user programs read yet
    playlist = db.create_playlist("Live")
    first = JDXiUIProgramList.ROM_PROGRAM_LIST[0]
    assert db.add_program_to_playlist(playlist, first.id)
    items = db.get_playlist_programs(playlist)
    assert [item["program"].id for item in items] == [first.id]
    assert items[0]["program"].name == first.name
    # kept for the playlist, but listed once (the library merges factory and user programs)
    from unittest.mock import patch

    with patch("jdxi_editor.ui.programs.database.get_database", return_value=db):
        listed = JDXiUIProgramList.list_rom_and_user_programs()
    assert [p.id for p in listed].count(first.id) == 1
