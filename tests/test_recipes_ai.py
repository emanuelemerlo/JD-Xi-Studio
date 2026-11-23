"""
Recipes are meant to be written by an AI from a description of the sound,
then fine-tuned: the request it gets, and its answer read back.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.recipes import ai_request, check, reader

_APP = QApplication.instance() or QApplication([])

ANSWER = """Here is a recipe for that lead.

```csv
# Title: Breathy flute lead
# Description: soft, legato
# Starting tone: D1 256 Init Tone
Step;Step name;Part;Group;Target;Parameter;Value type;Value;From;To;Note
1;Structure;D1;COMMON;;Mono/Poly;value;MONO;;;one note at a time
2;Filter;D1;FILTER;1;Cutoff;range;;60;72;dark but open
3;Amp;D1;AMP;1;Level;value;110;;;
4;Vibrato;D1;MOD LFO;;Pitch Depth;value;10;;;vibrato with the wheel
```

Adjust the cutoff by ear.
"""


@pytest.mark.parametrize("language", ["en", "it"])
def test_the_request_has_the_sound_the_format_and_only_the_parts_parameters(language):
    text = ai_request.build("the lead of Jungle Gardenia", "AN", language)
    assert "the lead of Jungle Gardenia" in text
    assert ai_request.header_line(language) in text
    assert "AN 064 Init Tone" in text
    listed = [l.split(";", 1)[0] for l in text.split("```")[-2].strip().splitlines()[1:]]
    effects = "EFFETTI" if language == "it" else "EFFECTS"
    assert set(listed) == {"AN", "PROG", effects}  # the part and what it always brings
    assert "ARP" not in listed and "D1" not in listed


def test_letting_the_ai_choose_the_part_lists_all_four():
    text = ai_request.build("a 909 groove", "", "en")
    listed = {l.split(";", 1)[0] for l in text.split("```")[-2].strip().splitlines()[1:]}
    assert {"D1", "D2", "AN", "DR"} <= listed


def test_every_parameter_in_the_request_is_one_the_checker_knows():
    """What the AI is told it may write is what JD-Xi Studio understands."""
    from jdxi_editor.recipes.model import Recipe, Row

    lines = ai_request.parameter_lines(("D1", "D2", "AN", "DR"), "en")[1:]
    rows = [Row(1, "s", *l.split(";")[:2], "", l.split(";")[2], "a orecchio", "") for l in lines]
    unknown = [c.row.param for c in check.check(Recipe(title="t", rows=rows)) if c.target is None]
    assert unknown == []


def test_an_ai_answer_is_read_from_its_code_block():
    recipe = reader.read_text(ANSWER)
    assert recipe.title == "Breathy flute lead" and recipe.base_tone == "D1 256 Init Tone"
    assert [r.param for r in recipe.rows] == ["Mono/Poly", "Cutoff", "Level", "Pitch Depth"]
    statuses = {c.row.param: c.status for c in check.check(recipe)}
    assert statuses["Cutoff"] in (check.OK, check.CONFIRM) and statuses["Mono/Poly"] == check.OK


def test_without_a_code_block_and_with_commas():
    text = ANSWER.replace("```csv", "").replace("```", "").replace(";", ",")
    recipe = reader.read_text(text)
    assert len(recipe.rows) == 4


def test_the_new_recipe_page_copies_the_request_and_reads_the_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("JDXI_RECIPES_DIR", str(tmp_path / "recipes"))
    from jdxi_editor.ui.v2.recipes import RecipesEditor

    w = RecipesEditor()
    w.show_create_page()
    w.ai_sound.setPlainText("a breathy flute lead")
    w.ai_part.setCurrentIndex(w.ai_part.findData("D1"))
    w.copy_ai_request()
    copied = QApplication.clipboard().text()
    assert "a breathy flute lead" in copied and "Usa la parte D1" not in copied or "D1" in copied
    saved = w.save_ai_request(str(tmp_path / "request.txt"))
    assert saved.read_text(encoding="utf-8") == w.ai_request()
    QApplication.clipboard().setText("nothing useful")
    w.paste_ai_answer()
    assert w.pages.currentWidget() is w.create_page and w.ai_status.text()
    QApplication.clipboard().setText(ANSWER.replace("# Description: soft, legato\n", ""))
    w.paste_ai_answer()
    assert w.pages.currentWidget() is w.check_page
    assert w.recipe.title == "Breathy flute lead" and w.recipe.description == "a breathy flute lead"
    w.close()
