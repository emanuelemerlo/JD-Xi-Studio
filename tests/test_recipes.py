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
    w.show_editor_page()
    assert w.ed_table.rowCount() == len(w.recipe.rows)
    w.add_editor_row()
    w.ed_table.item(w.ed_table.rowCount() - 1, 7).setText("") if w.ed_table.item(w.ed_table.rowCount() - 1, 7) else None
    target = w.export_recipe(str(tmp_path / "out.csv"))
    assert target.exists()
    assert w.save_template("Ricetta JD-Xi - vuota.csv", str(tmp_path / "t.csv")).exists()
    w.close()
