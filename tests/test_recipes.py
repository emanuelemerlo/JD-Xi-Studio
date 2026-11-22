"""Recipes: every template name has a parameter, reading, checking, guide, editor, export."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.recipes import apply as rapply
from jdxi_editor.recipes import catalog, check, library, reader
from jdxi_editor.recipes.model import Recipe, Row

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "resources" / "recipes" / "Ricetta JD-Xi - modello.xlsx"
CSV = ROOT / "resources" / "recipes" / "Ricetta JD-Xi - modello.csv"
PASTED = """# Il lead
Passo 3 Filtro
TONE: FILTER\tCutoff\t55–65
TONE: FILTER  Cutof  55-65 (parti da 60)
TONE: FILTER\tResonance\t140
TONE: FILTER\tAttack / Decay / Sustain / Release\t0 / 40 / 100 / 30
TONE: LFO\tRate\tcirca 5 Hz, a orecchio
PROG: MAIN AN\tPart Output\tEFX1 (passa per EFX1, EFX2, Delay e Reverb)
Una riga di testo qualsiasi
"""


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def recipes_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JDXI_RECIPES_DIR", str(tmp_path / "recipes"))


class Editors:
    """The new editors, opened on demand like the main window does."""

    def __init__(self):
        self.open = {}
        self.sent = []

    def __call__(self, key):
        if key not in self.open:
            from jdxi_editor.midi.io.helper import MidiIOHelper
            from jdxi_editor.ui.v2.analog import AnalogToneEditor
            from jdxi_editor.ui.v2.digital import DigitalToneEditor
            from jdxi_editor.ui.v2.effects import EffectsEditor
            from jdxi_editor.ui.v2.program import ProgramPartsEditor

            helper = MidiIOHelper()
            helper.send_midi_message = lambda m: self.sent.append(bytes(m.to_message_list())) or True
            cls = {"analog": AnalogToneEditor, "effects": EffectsEditor, "program_parts": ProgramPartsEditor,
                   "digital1": DigitalToneEditor}[key]
            editor = cls(helper, Mock())
            if key == "analog":  # its own sending (not the v2 framework)
                editor.send_midi_parameter = lambda p, v, a=None: self.sent.append((p.name, v)) or True
            self.open[key] = editor
        return self.open[key]


def test_every_template_name_has_an_editor_parameter():
    assert catalog.unmatched() == []
    assert len(catalog.targets()) == len(catalog.vocabulary.R)


def test_the_template_reads_and_checks_clean():
    for path in (TEMPLATE, CSV):
        recipe = reader.read_file(path)
        assert recipe.title == "Il lead di Jungle Gardenia" and recipe.base_tone == "AN 064 Init Tone"
        assert recipe.user_program == "E01" and len(recipe.rows) == 58
        result = check.check(recipe)
        assert check.summary(result) == {check.OK: 56, check.CONFIRM: 0, check.FIX: 0, check.EARS: 2}


def test_free_text_rows_statuses_and_notes():
    recipe = reader.read_text(PASTED)
    result = check.check(recipe, "AN")
    by = {(c.row.param, c.row.value): c for c in result}
    assert by[("Cutoff", "55–65")].status == check.OK
    assert (by[("Cutoff", "55–65")].parsed.lo, by[("Cutoff", "55–65")].parsed.hi) == (55, 65)
    cutof = by[("Cutof", "55-65")]
    assert cutof.status == check.CONFIRM and cutof.target.label == "Cutoff"
    reso = by[("Resonance", "140")]
    assert reso.status == check.FIX and reso.suggestions == ["127"]
    split = [c for c in result if c.row.param in ("Attack", "Decay", "Sustain", "Release")]
    assert [c.parsed.value for c in split] == [0, 40, 100, 30] and all(c.status == check.CONFIRM for c in split)
    ear = by[("Rate", "")]
    assert ear.status == check.EARS and "5 Hz" in ear.row.note
    out = by[("Part Output", "EFX1")]
    assert out.status == check.OK and out.su == [2] and "Delay" in out.row.note
    assert recipe.notes and "testo qualsiasi" in recipe.notes[0]


@pytest.mark.parametrize("part, group, su, param, value, expected", [
    ("EFFETTI", "DELAY", "", "HF Damp", "3000", "3150 Hz"),  # nearest of the JD-Xi's values
    ("EFFETTI", "DELAY", "", "Time", "1/8", "1/8"),
    ("EFFETTI", "DELAY", "", "Time", "375 ms", "375 ms"),
    ("ARP", "ARPEGGIO", "", "Style", "12", "012"),
    ("ARP", "ARPEGGIO", "", "Velocity", "REAL", "REAL"),
    ("PROG", "COMMON", "", "Tempo", "120.5", "120.50"),
    ("PROG", "MAIN", "DR", "Pan", "L20", "L20"),
    ("D1", "OSC", "2", "Waveform", "SUPER-SAW", "SP-SAW"),
    ("DR", "WAVE", "SD1/W2", "Level", "100", "100"),
    ("AN", "COMMON", "", "Bend Range D", "-2", "-2 st"),
    ("VOCE", "AUTO PITCH", "", "Key", "Am", "Am"),
])
def test_values_are_understood(part, group, su, param, value, expected):
    c = check.check_row(Row(1, "", part, group, su, param, "valore", value))
    assert c.status == check.OK, c.message
    proto = c.target.proto if c.target.special != "delay_time" else c.target.protos[1 if "/" in value else 0]
    assert proto.info.format(c.parsed.value).startswith(expected)


def test_su_problems_are_reported():
    assert check.check_row(Row(1, "", "DR", "TVA", "", "Level", "valore", "100")).status == check.FIX
    assert check.check_row(Row(1, "", "DR", "TVA", "XYZ", "Level", "valore", "100")).status == check.FIX
    no_wave = check.check_row(Row(1, "", "DR", "WAVE", "SD1", "Level", "valore", "100"))
    assert no_wave.status == check.CONFIRM and no_wave.wave == [0]
    assert check.check_row(Row(1, "", "PROG", "MAIN", "", "Level", "valore", "100")).status == check.FIX
    assert check.check_row(Row(1, "", "XX", "MAIN", "", "Level", "valore", "100")).status == check.FIX


def test_apply_sets_the_editor_values(app):
    editors = Editors()
    recipe = reader.read_file(TEMPLATE)
    result = check.check(recipe)
    cutoff = next(c for c in result if c.row.param == "Cutoff")
    assert rapply.is_done(cutoff, editors) is False
    assert rapply.apply(cutoff, editors) == 1
    assert rapply.current_text(cutoff, editors) == "60" and rapply.is_done(cutoff, editors)
    assert ("FILTER_CUTOFF", 60) in editors.sent
    delay = Row(1, "", "EFFETTI", "DELAY", "", "Time", "valore", "1/8")
    c = check.check_row(delay)
    rapply.apply(c, editors)
    fx = editors("effects")
    assert fx.pv("DELAY_TIME_NOTE_MODE").text() == "NOTE" and fx.pv("DELAY_NOTE").text() == "1/8"
    drive = check.check_row(Row(1, "", "EFFETTI", "EFFECT1", "", "Drive", "valore", "90"))
    assert rapply.values_for(drive, editors) == []  # Thru: no Drive
    fx.pv("EFX1_TYPE").setValue(2)  # Fuzz
    rapply.apply(drive, editors)
    assert [pv.value() for pv in rapply.values_for(drive, editors)] == [90]
    part = check.check_row(Row(1, "", "PROG", "MAIN", "D1, AN", "Level", "valore", "90"))
    rapply.apply(part, editors)
    prog = editors("program_parts")
    assert prog.part("PART_LEVEL", 0).value() == 90 and prog.part("PART_LEVEL", 2).value() == 90
    partials = check.check_row(Row(1, "", "D1", "FILTER", "", "Cutoff", "valore", "70"))  # no Su: all three
    rapply.apply(partials, editors)
    assert [editors("digital1").partial("FILTER_CUTOFF", p).value() for p in range(3)] == [70, 70, 70]


def test_library_and_export(tmp_path):
    recipe = reader.read_file(TEMPLATE)
    path = library.save(recipe)
    assert library.saved()[0][0] == recipe.title
    assert library.load(path).rows == recipe.rows
    recipe.to_csv(tmp_path / "r.csv")
    assert len(reader.read_file(tmp_path / "r.csv").rows) == 58
    (tmp_path / "r.md").write_text(recipe.to_markdown(), encoding="utf-8")
    back = reader.read_file(tmp_path / "r.md")
    assert len(back.rows) == 58 and back.title == recipe.title and back.base_tone == recipe.base_tone
    recipe.to_xlsx(tmp_path / "r.xlsx", TEMPLATE)
    again = reader.read_file(tmp_path / "r.xlsx")
    assert len(again.rows) == 58 and again.title == recipe.title
    assert check.summary(check.check(again))[check.FIX] == 0


def test_the_window_imports_checks_guides_and_edits(app, tmp_path):
    from jdxi_editor.ui.v2.recipes import RecipesEditor

    editors = Editors()
    w = RecipesEditor(editors=editors)
    w.resize(1400, 900)
    w.show()
    w.paste.setPlainText(PASTED)
    w.import_text()
    assert w.pages.currentWidget() is w.check_page
    w.default_part.setCurrentIndex(w.default_part.findData("AN"))
    assert not w.import_button.isEnabled()  # Resonance 140 to fix
    reso = next(i for i, c in enumerate(w.checked) if c.row.param == "Resonance")
    w.use_suggestion(reso, "127")
    assert w.import_button.isEnabled()
    w.accept_recipe()
    assert w.pages.currentWidget() is w.guide_page and library.saved()
    count = w.set_step()
    assert count >= 6 and not w.set_all_button.isEnabled()
    assert editors("analog").values[next(p for p in editors("analog").values if p.name == "FILTER_RESONANCE")].value() == 127
    # HIST-01: the whole step is one Undo, whichever editor it is pressed in
    touched = [editors(k).history for k in editors.open
               if getattr(editors(k), "history", None) is not None and editors(k).history.can_undo()]
    assert touched  # (one editor here; several: test_edit_history, one transaction)
    assert touched[-1].undo()
    assert not any(h.can_undo() for h in touched)  # all of them, together
    assert editors("analog").values[next(p for p in editors("analog").values if p.name == "FILTER_RESONANCE")].value() != 127
    assert touched[0].redo() and all(h.can_undo() and not h.can_redo() for h in touched)  # and back
    w.show_editor_page()
    assert w.ed_table.rowCount() == len(w.recipe.rows)
    w.add_editor_row()
    w.ed_table.item(w.ed_table.rowCount() - 1, 7).setText("") if w.ed_table.item(w.ed_table.rowCount() - 1, 7) else None
    target = w.export_recipe(str(tmp_path / "out.csv"))
    assert target.exists()
    assert w.save_template("Ricetta JD-Xi - vuota.csv", str(tmp_path / "t.csv")).exists()
    w.close()


EN = ROOT / "resources" / "recipes"


def test_english_template_reads_like_the_italian_one():
    """The English files are the Italian ones translated: the same recipe comes out."""
    from jdxi_editor.recipes.reader import read_file

    it_xlsx, en_xlsx = read_file(TEMPLATE), read_file(EN / "JD-Xi recipe - template.xlsx")
    it_csv, en_csv = read_file(CSV), read_file(EN / "JD-Xi recipe - example.csv")
    for it, en in ((it_xlsx, en_xlsx), (it_csv, en_csv)):
        assert len(en.rows) == len(it.rows) > 0
        assert [(r.part.replace("EFFECTS", "EFFETTI"), r.group, r.param, r.kind, r.value, r.lo, r.hi) for r in en.rows] == \
               [(r.part, r.group, r.param, r.kind, r.value, r.lo, r.hi) for r in it.rows]
        assert en.title == "The Jungle Gardenia lead" and en.base_tone == it.base_tone
    assert (EN / "JD-Xi recipe - blank.csv").exists() and (EN / "JD-Xi recipe parameters.csv").exists()


def test_templates_follow_the_interface_language(monkeypatch):
    import jdxi_editor.i18n as i18n
    from jdxi_editor.ui.v2 import recipes

    monkeypatch.setattr(i18n, "current_language", lambda: "en")
    assert recipes.template_name("xlsx") == "JD-Xi recipe - template.xlsx"
    monkeypatch.setattr(i18n, "current_language", lambda: "it")
    assert recipes.template_name("csv") == "Ricetta JD-Xi - vuota.csv"


def test_export_into_the_english_template_uses_its_words(tmp_path):
    import openpyxl

    from jdxi_editor.recipes.reader import read_file

    recipe = read_file(CSV)
    out = tmp_path / "out.xlsx"
    recipe.to_xlsx(out, EN / "JD-Xi recipe - template.xlsx")
    sheet = openpyxl.load_workbook(out)["Recipe"]
    kinds = {sheet.cell(r, 7).value for r in range(12, 12 + len(recipe.rows))}
    assert kinds <= {"value", "range", "by ear"} and "EFFETTI" not in {sheet.cell(r, 3).value for r in range(12, 80)}
    assert len(read_file(out).rows) == len(recipe.rows)


def test_recipes_tab_has_the_side_panel():
    from PySide6.QtWidgets import QApplication

    from jdxi_editor.ui.v2.recipes import RecipesEditor

    app = QApplication.instance() or QApplication([])  # noqa: F841
    editor = RecipesEditor()
    editor.resize(1600, 900)
    editor.show()
    app.processEvents()
    assert editor.info_panel.isVisible()
    assert editor.info_panel.name.text()  # the home page explained
    assert editor.library_list.count() >= 1  # a line saying what goes there, when empty
    assert editor._selected_path() is None or editor._selected_path().exists()
    editor.close()


def test_the_way_back_is_always_at_the_top(app, monkeypatch):
    """‹ All recipes (and Esc) next to the title on every page but the library; the breadcrumb says where."""
    from PySide6.QtWidgets import QMessageBox

    from jdxi_editor.ui.v2.recipes import RecipesEditor

    w = RecipesEditor(editors=Editors())
    w.resize(1400, 900)
    w.show()
    app.processEvents()
    assert not w.back_button.isVisible()
    w.paste.setPlainText(PASTED)
    w.import_text()
    assert w.back_button.isVisible() and "Check" in w.where.text()
    w.go_back()
    assert w.pages.currentWidget() is w.home and not w.back_button.isVisible()
    w.show_editor_page()
    assert "Editor" in w.where.text()
    w.add_editor_row()  # an unsaved change: asked before leaving
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.Cancel)
    w.go_back()
    assert asked and w.pages.currentWidget() is w.editor_page
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    w.back_shortcut.activated.emit()  # Esc
    assert w.pages.currentWidget() is w.home
    w.close()


def test_take_the_values_from_the_jdxi(app, monkeypatch):
    """With no rows it says what to do; with rows it reads the parts and fills each value."""
    import time

    from jdxi_editor.ui.v2 import recipes as module
    from jdxi_editor.ui.v2.recipes import RecipesEditor

    monkeypatch.setattr(module, "CAPTURE_DELAY_MS", 10)
    editors = Editors()
    w = RecipesEditor(editors=editors)
    w.show_editor_page()
    monkeypatch.setattr(w, "ask_capture_part", lambda: "")  # no part chosen
    w.capture_current()
    assert "add rows" in w.ed_status.text()
    w.add_editor_row()  # AN · FILTER
    param = w.ed_table.cellWidget(0, 5)
    param.setCurrentIndex(param.findText("Cutoff"))
    cutoff = next(p for p in editors("analog").values if p.name == "FILTER_CUTOFF")
    editors("analog").values[cutoff].setValue(77)
    w.capture_current()
    deadline = time.monotonic() + 2
    while "taken" not in w.ed_status.text().lower() and time.monotonic() < deadline:
        app.processEvents()
    assert w.ed_table.item(0, 7).text() == "77"
    assert "taken from the JD-Xi: 1" in w.ed_status.text()
    w.close()


def test_an_empty_editor_takes_a_whole_part(app, monkeypatch):
    """Empty editor: «Take the values from the JD-Xi» makes a row for every parameter of the part chosen."""
    import time

    from jdxi_editor.recipes import catalog
    from jdxi_editor.ui.v2 import recipes as module
    from jdxi_editor.ui.v2.recipes import RecipesEditor

    monkeypatch.setattr(module, "CAPTURE_DELAY_MS", 10)
    w = RecipesEditor(editors=Editors())
    w.show_editor_page()
    monkeypatch.setattr(w, "ask_capture_part", lambda: "AN")
    w.capture_current()
    deadline = time.monotonic() + 3
    while "taken" not in w.ed_status.text().lower() and time.monotonic() < deadline:
        app.processEvents()
    count = sum(1 for (p, _g, _l) in catalog.targets() if p == "AN")
    assert w.ed_table.rowCount() == count > 20
    assert "to fix" not in w.ed_status.text()
    filled = sum(1 for r in range(w.ed_table.rowCount()) if w.ed_table.item(r, 7) and w.ed_table.item(r, 7).text())
    assert filled >= count - 2
    w.close()


def test_rows_a_recipe_writes_the_way_the_jdxi_shows_them():
    """«Jungle Gardenia lead»: three rows to fix or confirm blocked «Import the recipe»."""
    from jdxi_editor.recipes import check as rcheck
    from jdxi_editor.recipes.model import Recipe, Row

    def one(param, value, group="COMMON", su=""):
        row = Row(1, "Step", "D1", group, su, param, "valore", value)
        [c] = rcheck.check(Recipe(title="t", rows=[row]))
        return c

    mono = one("Mono/Poly", "MONO")  # one parameter with a slash in its name, not two
    assert mono.status == "ok" and mono.parsed.value == 1
    bend = one("Bend Range D", "-2")  # two semitones down, as the JD-Xi stores it
    assert bend.status == "ok" and bend.parsed.value == 2
    for text, value in (("C", 0), ("L40", -40), ("40R", 40), ("R12", 12), ("12L", -12)):
        pan = one("Pan", text, group="AMP", su="P3")
        assert pan.status == "ok" and pan.parsed.value == value, text
    # «Attack / Decay» is still two rows
    split = rcheck.check(Recipe(title="t", rows=[Row(1, "S", "D1", "AMP", "P1", "Attack / Decay", "valore", "0 / 40")]))
    assert [c.parsed.value for c in split] == [0, 40]
