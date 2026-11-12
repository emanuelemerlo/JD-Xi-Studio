"""
Recipes: step-by-step instructions to make a sound on the JD-Xi.

Pages:
  RECIPES   the saved recipes; new recipe: template, import a file or text, or the editor
  CHECK     what the checker understood of each row, and what to fix
  GUIDE     step by step: the recipe's value next to the JD-Xi's, set one or all
  EDITOR    write or change a recipe with menus that only offer valid names

Nothing is sent to the JD-Xi until you set a value in the guide.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.recipes import apply as recipe_apply
from jdxi_editor.recipes import catalog, check, library, reader
from jdxi_editor.recipes.model import COLUMNS, EAR, RANGE, VALUE, Recipe, Row
from jdxi_editor.resources import resource_path
from jdxi_editor.ui.v2.widgets import Card

ACCENT = "#27ae60"
TEMPLATE_DIR = Path("resources") / "recipes"
# The template files in the interface's language (Italian, or English for any other)
TEMPLATES = {
    "it": {"xlsx": "Ricetta JD-Xi - modello.xlsx", "csv": "Ricetta JD-Xi - vuota.csv",
           "parameters": "Parametri ricette JD-Xi.csv", "example": "Ricetta JD-Xi - modello.csv"},
    "en": {"xlsx": "JD-Xi recipe - template.xlsx", "csv": "JD-Xi recipe - blank.csv",
           "parameters": "JD-Xi recipe parameters.csv", "example": "JD-Xi recipe - example.csv"},
}


def template_name(kind: str) -> str:
    from jdxi_editor.i18n import current_language

    return TEMPLATES.get(current_language(), TEMPLATES["en"])[kind]
STATUS_COLORS = {check.OK: "#27ae60", check.CONFIRM: "#f2c94c", check.FIX: "#eb5757", check.EARS: "#56ccf2"}
BUTTON = (
    "QPushButton { background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px; padding: 6px 14px; }"
    "QPushButton:hover { border-color: #6b6e75; } QPushButton:disabled { color: #5a5d64; }"
)
PRIMARY = (
    f"QPushButton {{ background: {ACCENT}; color: #0e0f11; border: 0; border-radius: 6px; padding: 7px 16px; font-weight: 700; }}"
    "QPushButton:disabled { background: #2a2d33; color: #6b6e75; }"
)
TABLE = (
    "QTableWidget { background: #121214; color: #e6e6e6; gridline-color: #2a2d33; border: 1px solid #2a2d33; }"
    "QHeaderView::section { background: #1b1c1f; color: #a3a6ad; border: 0; padding: 4px; }"
    "QTableWidget::item:selected { background: #2a3a30; }"
)


def status_text(status: str) -> str:
    return {check.OK: tr("recognized"), check.CONFIRM: tr("to confirm"), check.FIX: tr("to fix"),
            check.EARS: tr("by ear")}.get(status, status)


def _button(text: str, primary: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setStyleSheet(PRIMARY if primary else BUTTON)
    return b


def _label(text: str, size: int = 12, color: str = "#c9cbd1", bold: bool = False) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setStyleSheet(f"color: {color}; font-size: {size}px; {'font-weight: 700;' if bold else ''} background: transparent;")
    return lab


def recipe_value_text(row: Row) -> str:
    if row.kind == EAR:
        return tr("by ear")
    if row.lo and row.hi:
        return f"{row.lo}–{row.hi}"
    return row.value


class RecipesEditor(QWidget):
    """Recipe library, import, check, guide and editor."""

    recipe_changed = Signal()

    def __init__(self, midi_out=None, parent=None, editors: Optional[Callable[[str], object]] = None, **_kwargs):
        super().__init__(parent)
        self.setWindowTitle(tr("Recipes"))
        self.instrument = parent
        self._editors = editors
        self.recipe: Optional[Recipe] = None
        self.recipe_path: Optional[Path] = None
        self.checked: list[check.Checked] = []
        self.step_index = 0
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("RecipesEditor { background: #121214; } QLabel { color: #c9cbd1; }")
        self.setMinimumSize(1000, 640)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        from jdxi_editor.ui.v2.restyle import title_badge

        self.title = title_badge(tr("Recipes"), ACCENT)  # as at the top of the other editors
        bar = QHBoxLayout()
        bar.addWidget(self.title)
        bar.addStretch()
        root.addLayout(bar)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        self.home = self._home_page()
        self.check_page = self._check_page()
        self.guide_page = self._guide_page()
        self.editor_page = self._editor_page()
        for page in (self.home, self.check_page, self.guide_page, self.editor_page):
            self.pages.addWidget(page)
        self.refresh_library()

    # ------------------------------------------------------------ editors
    def editors(self, key: str):
        """The (new) editor for *key*, opened when needed."""
        if self._editors is not None:
            return self._editors(key)
        inst = self.instrument
        if inst is None or not hasattr(inst, "editor_registry"):
            return None
        config = inst.editor_registry.get(key)
        if config is None:
            return None
        editor = inst.get_existing_editor(config.editor_class)
        if editor is None:
            inst.show_editor(key)
            editor = inst.get_existing_editor(config.editor_class)
            self.raise_()
        return editor

    # --------------------------------------------------------------- home
    def _home_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setSpacing(14)
        lib = Card(tr("MY RECIPES"), ACCENT)
        self.library_list = QListWidget()
        self.library_list.setStyleSheet("QListWidget { background: #121214; color: #e6e6e6; border: 1px solid #2a2d33; }"
                                        "QListWidget::item { padding: 6px; } QListWidget::item:selected { background: #2a3a30; }")
        self.library_list.itemDoubleClicked.connect(lambda _i: self.open_selected())
        self.library_list.setMinimumHeight(420)
        lib.body.addWidget(self.library_list, 1)
        buttons = QHBoxLayout()
        open_b = _button(tr("Open"), True)
        open_b.clicked.connect(self.open_selected)
        edit_b = _button(tr("Edit"))
        edit_b.clicked.connect(lambda: self.open_selected(edit=True))
        del_b = _button(tr("Delete"))
        del_b.clicked.connect(self.delete_selected)
        for b in (open_b, edit_b, del_b):
            buttons.addWidget(b)
        buttons.addStretch()
        lib.body.addLayout(buttons)
        lib.body.addWidget(_label(tr("Saved recipes stay in the library and can be used again on another program."), 11, "#8a8d94"))
        row.addWidget(lib, 2, Qt.AlignmentFlag.AlignTop)

        new = Card(tr("NEW RECIPE"), ACCENT)
        new.body.addWidget(_label(tr("A recipe is a list of steps: for each step, which parameters to set and to what value. "
                                     "Before using it the editor checks it row by row and shows what it understood: "
                                     "nothing is sent to the JD-Xi until you decide."), 12))
        new.body.addWidget(_label(tr("1 · Fill in the template"), 13, "#ffffff", True))
        new.body.addWidget(_label(tr("A ready sheet: Part, Group and Parameter have menus with the valid names only; a second sheet lists "
                                     "every parameter with its allowed values. It contains the Jungle Gardenia lead as an example."), 11, "#a3a6ad"))
        line = QHBoxLayout()
        xlsx = _button(tr("Save template .xlsx…"))
        xlsx.clicked.connect(lambda: self.save_template(template_name("xlsx")))
        csv_b = _button(tr("Template .csv…"))
        csv_b.clicked.connect(lambda: self.save_template(template_name("csv")))
        params = _button(tr("Parameter list .csv…"))
        params.clicked.connect(lambda: self.save_template(template_name("parameters")))
        for b in (xlsx, csv_b, params):
            line.addWidget(b)
        line.addStretch()
        new.body.addLayout(line)
        new.body.addWidget(_label(tr("2 · Import a file or a text"), 13, "#ffffff", True))
        line = QHBoxLayout()
        choose = _button(tr("Choose a file…"), True)
        choose.clicked.connect(self.import_file)
        line.addWidget(choose)
        line.addWidget(_label(".xlsx · .csv · .md · .txt · .pdf", 11, "#8a8d94"))
        line.addStretch()
        new.body.addLayout(line)
        self.paste = QPlainTextEdit()
        self.paste.setPlaceholderText(tr("…or paste a table copied from a document or a web page, e.g.\nTONE: FILTER\tCutoff\t55–65\nTONE: FILTER\tCutoff KF\t+50"))
        self.paste.setStyleSheet("QPlainTextEdit { background: #121214; color: #e6e6e6; border: 1px solid #2a2d33; font-family: monospace; }")
        self.paste.setFixedHeight(110)
        new.body.addWidget(self.paste)
        line = QHBoxLayout()
        read = _button(tr("Read the text"))
        read.clicked.connect(self.import_text)
        line.addWidget(read)
        line.addWidget(_label(tr("From PDFs and texts only the lines that look like Group · Parameter · Value are taken; the rest is kept as notes."), 11, "#8a8d94"))
        new.body.addLayout(line)
        new.body.addWidget(_label(tr("3 · Write it in the editor"), 13, "#ffffff", True))
        line = QHBoxLayout()
        write = _button(tr("Open the recipe editor"))
        write.clicked.connect(self.new_in_editor)
        line.addWidget(write)
        line.addStretch()
        new.body.addLayout(line)
        new.body.addStretch()
        row.addWidget(new, 3, Qt.AlignmentFlag.AlignTop)
        return page

    def refresh_library(self) -> None:
        self.library_list.clear()
        for title, path in library.saved():
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.library_list.addItem(item)

    def _selected_path(self) -> Optional[Path]:
        item = self.library_list.currentItem()
        return Path(item.data(Qt.ItemDataRole.UserRole)) if item else None

    def open_selected(self, edit: bool = False) -> None:
        path = self._selected_path()
        if path is None:
            return
        self.recipe_path = path
        self.set_recipe(library.load(path))
        if edit:
            self.show_editor_page()
        else:
            self.show_guide()

    def delete_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        if QMessageBox.question(self, tr("Delete recipe"), tr("Delete \"{name}\"?").format(name=self.library_list.currentItem().text())) \
                == QMessageBox.StandardButton.Yes:
            library.delete(path)
            self.refresh_library()

    def save_template(self, name: str, target: Optional[str] = None) -> Optional[Path]:
        source = Path(resource_path(TEMPLATE_DIR / name))
        if target is None:
            target, _ = QFileDialog.getSaveFileName(self, tr("Save template"), str(Path.home() / name))
        if not target:
            return None
        shutil.copyfile(source, target)
        return Path(target)

    def import_file(self, path: Optional[str] = None) -> None:
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("Import a recipe"), str(Path.home()),
                                                  tr("Recipes (*.xlsx *.csv *.md *.txt *.pdf *.json)"))
        if not path:
            return
        try:
            recipe = reader.read_file(path)
        except Exception as ex:  # a damaged or unreadable file
            QMessageBox.warning(self, tr("Import a recipe"), tr("Could not read the file: {error}").format(error=ex))
            return
        if not recipe.title:
            recipe.title = Path(path).stem
        self.recipe_path = None
        self.set_recipe(recipe, source=Path(path).name)
        self.show_check()

    def import_text(self) -> None:
        text = self.paste.toPlainText().strip()
        if not text:
            return
        recipe = reader.read_text(text)
        recipe.title = recipe.title or tr("Pasted recipe")
        self.recipe_path = None
        self.set_recipe(recipe, source=tr("pasted text"))
        self.show_check()

    def new_in_editor(self) -> None:
        self.recipe_path = None
        self.set_recipe(Recipe(title=tr("New recipe"), rows=[Row(1, tr("Step 1"), "AN", "FILTER", "", "Cutoff", VALUE, "64")]))
        self.show_editor_page()

    def set_recipe(self, recipe: Recipe, source: str = "") -> None:
        self.recipe = recipe
        self.source = source
        self.checked = check.check(recipe)
        self.step_index = 0

    # -------------------------------------------------------------- check
    def _check_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        self.check_title = _label("", 15, "#ffffff", True)
        col.addWidget(self.check_title)
        line = QHBoxLayout()
        line.addWidget(_label(tr("Rows without a part are for:"), 12))
        self.default_part = QComboBox()
        self.default_part.addItem(tr("(none)"), "")
        for code, name in catalog.vocabulary.PARTS:
            self.default_part.addItem(f"{code} · {name}", code)
        self.default_part.currentIndexChanged.connect(self._recheck)
        line.addWidget(self.default_part)
        line.addStretch()
        self.check_counts = _label("", 12)
        line.addWidget(self.check_counts)
        col.addLayout(line)
        self.base_warning = _label("", 12, "#f2c94c")
        col.addWidget(self.base_warning)
        self.check_table = QTableWidget(0, 5)
        self.check_table.setHorizontalHeaderLabels([tr("Row read in the file"), tr("Understood"), tr("Status"), tr("Explanation"), tr("Action")])
        self.check_table.setStyleSheet(TABLE)
        self.check_table.verticalHeader().setVisible(False)
        self.check_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.check_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.check_table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        col.addWidget(self.check_table, 1)
        self.notes_label = _label("", 11, "#8a8d94")
        col.addWidget(self.notes_label)
        bottom = QHBoxLayout()
        cancel = _button(tr("Cancel"))
        cancel.clicked.connect(self.show_home)
        edit = _button(tr("Correct in the editor"))
        edit.clicked.connect(self.show_editor_page)
        self.exclude_fix = _button(tr("Exclude the rows to fix and import"))
        self.exclude_fix.clicked.connect(self.exclude_rows_to_fix)
        self.import_button = _button(tr("Import the recipe"), True)
        self.import_button.clicked.connect(self.accept_recipe)
        for b in (cancel, edit):
            bottom.addWidget(b)
        bottom.addStretch()
        bottom.addWidget(self.exclude_fix)
        bottom.addWidget(self.import_button)
        col.addLayout(bottom)
        return page

    def _recheck(self) -> None:
        if self.recipe is None:
            return
        self.checked = check.check(self.recipe, self.default_part.currentData() or "")
        self._fill_check()

    def show_check(self) -> None:
        part = check.default_part(self.recipe)
        index = self.default_part.findData(part)
        self.default_part.blockSignals(True)
        self.default_part.setCurrentIndex(max(0, index))
        self.default_part.blockSignals(False)
        self._fill_check()
        self.pages.setCurrentWidget(self.check_page)

    def _fill_check(self) -> None:
        recipe = self.recipe
        self.check_title.setText(tr("Check of \"{name}\"").format(name=getattr(self, "source", "") or recipe.title))
        counts = check.summary(self.checked)
        self.check_counts.setText(tr("{ok} recognized · {confirm} to confirm · {fix} to fix · {ear} by ear · {notes} lines kept as notes").format(
            ok=counts[check.OK], confirm=counts[check.CONFIRM], fix=counts[check.FIX], ear=counts[check.EARS], notes=len(recipe.notes)))
        self.base_warning.setText(tr("The recipe starts from {tone}: load it on the JD-Xi first to get the same result.").format(tone=recipe.base_tone)
                                  if recipe.base_tone else "")
        table = self.check_table
        table.clearContents()
        table.setRowCount(0)
        table.setRowCount(len(self.checked))
        for i, c in enumerate(self.checked):
            r = c.row
            read = " · ".join(x for x in (r.source, r.part, r.group, r.su, r.param, recipe_value_text(r)) if x)
            understood = ""
            if c.target is not None:
                t = c.target
                value = c.target.proto.info.format(c.parsed.value) if c.parsed and c.parsed.kind == "value" and c.target.proto else recipe_value_text(r)
                if c.parsed and c.parsed.kind == "range":
                    value = f"{t.proto.info.format(c.parsed.lo)}–{t.proto.info.format(c.parsed.hi)}"
                understood = " · ".join(x for x in (t.part, t.group, r.su, t.label, value) if x)
            items = [read, understood, status_text(c.status) if not c.excluded else tr("excluded"), c.message]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 2:
                    item.setForeground(QColor(STATUS_COLORS.get(c.status, "#e6e6e6") if not c.excluded else "#6b6e75"))
                table.setItem(i, col, item)
            table.setCellWidget(i, 4, self._row_action(i, c))
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.notes_label.setText(tr("Notes: {notes}").format(notes=" · ".join(recipe.notes[:6]) + (" …" if len(recipe.notes) > 6 else ""))
                                 if recipe.notes else "")
        blocking = any(c.status == check.FIX and not c.excluded for c in self.checked)
        self.import_button.setEnabled(not blocking and bool(self.checked))
        self.exclude_fix.setEnabled(blocking)

    def _row_action(self, index: int, c: check.Checked) -> QWidget:
        box = QWidget()
        line = QHBoxLayout(box)
        line.setContentsMargins(2, 0, 2, 0)
        if c.status == check.FIX and c.suggestions and not c.excluded:
            combo = QComboBox()
            combo.addItems(c.suggestions)
            use = _button(tr("Use"))
            use.clicked.connect(lambda _=False, i=index, combo=combo: self.use_suggestion(i, combo.currentText()))
            line.addWidget(combo)
            line.addWidget(use)
        if c.status == check.CONFIRM and not c.excluded:
            ok = _button(tr("Fine"))
            ok.clicked.connect(lambda _=False, i=index: self.confirm_row(i))
            line.addWidget(ok)
        toggle = _button(tr("Include") if c.excluded else tr("Exclude"))
        toggle.clicked.connect(lambda _=False, i=index: self.toggle_excluded(i))
        line.addWidget(toggle)
        return box

    def use_suggestion(self, index: int, text: str) -> None:
        c = self.checked[index]
        if c.target is not None and c.status == check.FIX and c.parsed is None:  # a value out of range
            c.row.value, c.row.lo, c.row.hi, c.row.kind = text, "", "", VALUE
        else:  # a parameter name
            c.row.param = text
        self.checked[index] = check.check_row(c.row, self.default_part.currentData() or "")
        self._fill_check()

    def confirm_row(self, index: int) -> None:
        c = self.checked[index]
        if c.target is not None:
            c.row.param, c.row.group = c.target.label, c.target.group
        c.status, c.message = check.OK, ""
        self._fill_check()

    def toggle_excluded(self, index: int) -> None:
        self.checked[index].excluded = not self.checked[index].excluded
        self._fill_check()

    def exclude_rows_to_fix(self) -> None:
        for c in self.checked:
            if c.status == check.FIX:
                c.excluded = True
        self.accept_recipe()

    def accept_recipe(self) -> None:
        """Keep the checked rows (split rows, corrected names) as the recipe and open the guide."""
        rows = []
        for c in self.checked:
            if c.excluded:
                continue
            if not c.row.part and c.target is not None:
                c.row.part = c.target.part
            rows.append(c.row)
        self.recipe.rows = rows
        self.checked = [c for c in self.checked if not c.excluded]
        self.recipe_path = library.save(self.recipe, self.recipe_path)
        self.refresh_library()
        self.show_guide()

    # -------------------------------------------------------------- guide
    def _guide_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        top = QHBoxLayout()
        self.guide_title = _label("", 16, "#ffffff", True)
        top.addWidget(self.guide_title, 1)
        back = _button(tr("Recipes"))
        back.clicked.connect(self.show_home)
        edit = _button(tr("Edit the recipe"))
        edit.clicked.connect(self.show_editor_page)
        top.addWidget(back)
        top.addWidget(edit)
        col.addLayout(top)
        self.guide_sub = _label("", 12, "#a3a6ad")
        col.addWidget(self.guide_sub)
        self.step_bar = QHBoxLayout()
        self.step_bar.setSpacing(4)
        col.addLayout(self.step_bar)
        self.step_title = _label("", 13, ACCENT, True)
        col.addWidget(self.step_title)
        self.guide_table = QTableWidget(0, 6)
        self.guide_table.setHorizontalHeaderLabels([tr("Group"), tr("Parameter"), tr("Recipe"), tr("On the JD-Xi"), tr("Status"), tr("Actions")])
        self.guide_table.setStyleSheet(TABLE)
        self.guide_table.verticalHeader().setVisible(False)
        self.guide_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.guide_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.guide_table.currentCellChanged.connect(lambda row, *_: self._show_note(row))
        col.addWidget(self.guide_table, 1)
        self.guide_note = _label("", 12, "#e6e6e6")
        self.guide_note.setStyleSheet("color: #e6e6e6; background: #1b1c1f; border-radius: 6px; padding: 8px; font-size: 12px;")
        col.addWidget(self.guide_note)
        bottom = QHBoxLayout()
        self.set_all_button = _button(tr("Set the missing values of the step"), True)
        self.set_all_button.clicked.connect(self.set_step)
        self.refresh_button = _button(tr("Read the JD-Xi again"))
        self.refresh_button.clicked.connect(self.read_again)
        self.next_button = _button(tr("Next step"))
        self.next_button.clicked.connect(lambda: self.go_step(self.step_index + 1))
        bottom.addWidget(self.set_all_button)
        bottom.addWidget(self.refresh_button)
        bottom.addStretch()
        bottom.addWidget(self.next_button)
        col.addLayout(bottom)
        self.save_hint = _label(tr("To keep the sound, save the program on the JD-Xi with [Menu/Write] (the JD-Xi cannot be written to via MIDI); "
                                   "the recipe suggests user program {program}."), 11, "#8a8d94")
        col.addWidget(self.save_hint)
        return page

    def show_guide(self) -> None:
        if self.recipe is None:
            return
        r = self.recipe
        self.guide_title.setText(r.title)
        parts = sorted({c.target.part for c in self.checked if c.target is not None})
        self.guide_sub.setText(" · ".join(x for x in (
            r.description,
            tr("starting tone {tone}").format(tone=r.base_tone) if r.base_tone else "",
            tr("{n} parameters in {steps} steps").format(n=len(self.checked), steps=len(r.steps())),
            ", ".join(parts)) if x))
        self.save_hint.setText(tr("To keep the sound, save the program on the JD-Xi with [Menu/Write] (the JD-Xi cannot be written to via MIDI).")
                               + (" " + tr("The recipe suggests user program {program}.").format(program=r.user_program) if r.user_program else ""))
        while self.step_bar.count():
            item = self.step_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.step_buttons = []
        for i, (number, name, _rows) in enumerate(r.steps()):
            b = QPushButton(f"{number} · {name}" if name else str(number))
            b.setCheckable(True)
            b.setStyleSheet(BUTTON + f"QPushButton:checked {{ background: {ACCENT}; color: #0e0f11; border-color: {ACCENT}; }}")
            b.clicked.connect(lambda _=False, i=i: self.go_step(i))
            self.step_bar.addWidget(b)
            self.step_buttons.append(b)
        self.step_bar.addStretch()
        self.pages.setCurrentWidget(self.guide_page)
        self.go_step(min(self.step_index, max(0, len(self.step_buttons) - 1)))

    def _step_checked(self) -> list[check.Checked]:
        steps = self.recipe.steps()
        if not steps:
            return []
        number = steps[self.step_index][0]
        return [c for c in self.checked if c.row.step == number]

    def go_step(self, index: int) -> None:
        steps = self.recipe.steps() if self.recipe else []
        if not steps:
            return
        self.step_index = max(0, min(index, len(steps) - 1))
        for i, b in enumerate(self.step_buttons):
            b.setChecked(i == self.step_index)
        number, name, _rows = steps[self.step_index]
        self.step_title.setText(tr("STEP {n}").format(n=number) + (f" · {name.upper()}" if name else ""))
        self.next_button.setEnabled(self.step_index < len(steps) - 1)
        self._fill_guide()

    def _fill_guide(self) -> None:
        rows = self._step_checked()
        table = self.guide_table
        table.clearContents()
        table.setRowCount(0)  # the old buttons go with their rows
        table.setRowCount(len(rows))
        for i, c in enumerate(rows):
            t = c.target
            done = recipe_apply.is_done(c, self.editors) if t is not None else None
            if c.status == check.EARS:
                state = tr("by ear")
            elif done:
                state = tr("in range") if c.parsed and c.parsed.kind == "range" else tr("done")
            else:
                state = tr("to set")
            su = f" ({c.row.su})" if c.row.su else ""
            current = recipe_apply.current_text(c, self.editors) if t is not None else "—"
            recipe_text = recipe_value_text(c.row)
            cells = [f"{t.part}: {t.group}" if t else c.row.group, (t.label if t else c.row.param) + su, recipe_text, current, state]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col == 4:
                    item.setForeground(QColor(ACCENT if done else ("#56ccf2" if c.status == check.EARS else "#f2c94c")))
                table.setItem(i, col, item)
            box = QWidget()
            line = QHBoxLayout(box)
            line.setContentsMargins(2, 0, 2, 0)
            if c.status != check.EARS and not done:
                set_b = _button(tr("Set"))
                set_b.clicked.connect(lambda _=False, c=c: self.set_row(c))
                line.addWidget(set_b)
            go = _button(tr("Go to the control"))
            go.clicked.connect(lambda _=False, c=c: self.go_to_control(c))
            line.addWidget(go)
            table.setCellWidget(i, 5, box)
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        missing = [c for c in rows if c.status != check.EARS and not recipe_apply.is_done(c, self.editors)]
        self.set_all_button.setEnabled(bool(missing))
        self.set_all_button.setText(tr("Set the {n} missing values of the step").format(n=len(missing)) if missing
                                    else tr("All values of the step are set"))
        if rows:
            self._show_note(0)

    def _show_note(self, row: int) -> None:
        rows = self._step_checked()
        if 0 <= row < len(rows):
            c = rows[row]
            text = c.row.note or (c.message if c.status != check.OK else "")
            if c.status == check.EARS:
                text = (text + " — " if text else "") + tr("Values \"by ear\" are not set automatically: the editor opens the control and leaves the tuning to you.")
            self.guide_note.setText(text)
            self.guide_note.setVisible(bool(text))

    def set_row(self, c: check.Checked) -> None:
        recipe_apply.apply(c, self.editors)
        self._fill_guide()

    def set_step(self) -> int:
        count = 0
        for c in self._step_checked():
            if c.status != check.EARS:
                count += recipe_apply.apply(c, self.editors)
        self._fill_guide()
        return count

    def read_again(self) -> None:
        keys = {c.target.editor_key for c in self.checked if c.target is not None}
        for key in keys:
            editor = self.editors(key)
            if editor is not None and hasattr(editor, "data_request"):
                editor.data_request()
        self._fill_guide()

    def go_to_control(self, c: check.Checked) -> None:
        pvs = [pv for pv in recipe_apply.values_for(c, self.editors) if pv is not None]
        editor = self.editors(c.target.editor_key) if c.target else None
        if editor is None:
            return
        if self.instrument is not None and hasattr(self.instrument, "show_editor"):
            self.instrument.show_editor(c.target.editor_key)
        if pvs and hasattr(editor, "info_hub") and editor.info_hub is not None:
            editor.info_hub.shown.emit(pvs[0])
        for name in ("show_partial", "show_section"):
            pass  # the editors show the panel; the information panel names the parameter

    # ------------------------------------------------------------- editor
    def _editor_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        meta = QHBoxLayout()
        self.ed_title = QLineEdit()
        self.ed_base = QLineEdit()
        self.ed_program = QLineEdit()
        self.ed_description = QLineEdit()
        for label, field in ((tr("Title"), self.ed_title), (tr("Starting tone"), self.ed_base), (tr("User program"), self.ed_program)):
            meta.addWidget(_label(label, 12))
            field.setStyleSheet("QLineEdit { background: #121214; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 5px; padding: 3px 6px; }")
            meta.addWidget(field, 2 if field is self.ed_title else 1)
        col.addLayout(meta)
        line = QHBoxLayout()
        line.addWidget(_label(tr("Description"), 12))
        self.ed_description.setStyleSheet(self.ed_title.styleSheet())
        line.addWidget(self.ed_description, 1)
        col.addLayout(line)
        self.ed_table = QTableWidget(0, len(COLUMNS) + 1)
        self.ed_table.setHorizontalHeaderLabels(COLUMNS + [tr("Check")])
        self.ed_table.setStyleSheet(TABLE)
        self.ed_table.verticalHeader().setVisible(False)
        self.ed_table.itemChanged.connect(lambda _item: self._editor_changed())
        col.addWidget(self.ed_table, 1)
        self.ed_status = _label("", 12)
        col.addWidget(self.ed_status)
        col.addWidget(_label(tr("The menus show only what exists: choosing the part AN, the group offers COMMON, OSC, PITCH, FILTER, AMP, LFO, "
                                "and the parameter shows its range. The check is the same as for imported files, while you write."), 11, "#8a8d94"))
        bottom = QHBoxLayout()
        add = _button(tr("Add row"))
        add.clicked.connect(self.add_editor_row)
        remove = _button(tr("Remove row"))
        remove.clicked.connect(self.remove_editor_row)
        capture = _button(tr("Take the values from the JD-Xi"))
        capture.setToolTip(tr("Writes in each row the value the parameter has now"))
        capture.clicked.connect(self.capture_current)
        export = _button(tr("Export…"))
        export.clicked.connect(self.export_recipe)
        try_b = _button(tr("Try the recipe"))
        try_b.clicked.connect(lambda: (self._editor_to_recipe(), self.show_check()))
        save = _button(tr("Save recipe"), True)
        save.clicked.connect(self.save_from_editor)
        back = _button(tr("Recipes"))
        back.clicked.connect(self.show_home)
        for b in (add, remove, capture):
            bottom.addWidget(b)
        bottom.addStretch()
        for b in (back, export, try_b, save):
            bottom.addWidget(b)
        col.addLayout(bottom)
        return page

    def show_editor_page(self) -> None:
        r = self.recipe or Recipe()
        self.ed_title.setText(r.title)
        self.ed_base.setText(r.base_tone)
        self.ed_program.setText(r.user_program)
        self.ed_description.setText(r.description)
        table = self.ed_table
        table.blockSignals(True)
        table.setRowCount(0)
        for row in r.rows:
            self._add_editor_row(row)
        table.blockSignals(False)
        for col, width in enumerate((48, 110, 80, 110, 70, 170, 110, 90, 56, 56)):
            table.setColumnWidth(col, width)
        table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(11, 220)
        self._editor_changed()
        self.pages.setCurrentWidget(self.editor_page)

    def _combo(self, items: list[str], current: str, editable: bool = False) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(editable)
        combo.addItems(items)
        if current and current not in items:
            combo.addItem(current)
        combo.setCurrentText(current)
        return combo

    def _add_editor_row(self, row: Row) -> None:
        table = self.ed_table
        i = table.rowCount()
        table.insertRow(i)
        for col, value in enumerate(row.cells()):
            if col in (2, 3, 5, 6):
                continue
            table.setItem(i, col, QTableWidgetItem(value))
        part = self._combo(list(catalog.PARTS), row.part)
        group = self._combo(catalog.groups_of(row.part) if row.part in catalog.PARTS else [], row.group)
        param = self._combo(catalog.labels_of(row.part, row.group) if row.part in catalog.PARTS else [], row.param, editable=True)
        kind = self._combo([VALUE, RANGE, EAR], row.kind)
        table.setCellWidget(i, 2, part)
        table.setCellWidget(i, 3, group)
        table.setCellWidget(i, 5, param)
        table.setCellWidget(i, 6, kind)

        def part_changed(_=None, part=part, group=group, param=param):
            group.blockSignals(True)
            group.clear()
            group.addItems(catalog.groups_of(part.currentText()))
            group.blockSignals(False)
            group_changed(group=group, param=param, part=part)

        def group_changed(_=None, part=part, group=group, param=param):
            current = param.currentText()
            param.blockSignals(True)
            param.clear()
            param.addItems(catalog.labels_of(part.currentText(), group.currentText()))
            if current in catalog.labels_of(part.currentText(), group.currentText()):
                param.setCurrentText(current)
            param.blockSignals(False)
            self._editor_changed()

        part.currentIndexChanged.connect(part_changed)
        group.currentIndexChanged.connect(group_changed)
        param.currentTextChanged.connect(lambda _t: self._editor_changed())
        kind.currentIndexChanged.connect(lambda _i: self._editor_changed())

    def _editor_rows(self) -> list[Row]:
        table = self.ed_table
        rows = []
        for i in range(table.rowCount()):
            def text(col):
                widget = table.cellWidget(i, col)
                if isinstance(widget, QComboBox):
                    return widget.currentText().strip()
                item = table.item(i, col)
                return item.text().strip() if item else ""

            step = text(0)
            rows.append(Row(int(step) if step.isdigit() else 1, text(1), text(2), text(3), text(4), text(5), text(6) or VALUE,
                            text(7), text(8), text(9), text(10)))
        return rows

    def _editor_to_recipe(self) -> Recipe:
        r = self.recipe or Recipe()
        r.title, r.base_tone = self.ed_title.text().strip(), self.ed_base.text().strip()
        r.user_program, r.description = self.ed_program.text().strip(), self.ed_description.text().strip()
        r.rows = self._editor_rows()
        self.recipe = r
        self.checked = check.check(r)
        return r

    def _editor_changed(self) -> None:
        if not hasattr(self, "ed_table"):
            return
        rows = self._editor_rows()
        table = self.ed_table
        table.blockSignals(True)
        bad = 0
        for i, row in enumerate(rows):
            c = check.check_row(row)
            item = QTableWidgetItem(status_text(c.status) + (f": {c.message}" if c.message else ""))
            item.setForeground(QColor(STATUS_COLORS.get(c.status, "#e6e6e6")))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if c.target is not None and c.status != check.FIX:
                info = c.target.proto.info
                lo, hi = info.format(c.target.proto.lo), info.format(c.target.proto.hi)
                item.setToolTip(tr("Range: {lo} … {hi}").format(lo=lo, hi=hi) if not getattr(info, "choices", ()) else ", ".join(info.choices[:40]))
            table.setItem(i, len(COLUMNS), item)
            bad += c.status == check.FIX
        table.blockSignals(False)
        self.ed_status.setText(tr("All {n} rows are valid").format(n=len(rows)) if not bad
                               else tr("{bad} of {n} rows to fix").format(bad=bad, n=len(rows)))

    def add_editor_row(self) -> None:
        rows = self._editor_rows()
        last = rows[-1] if rows else Row(1, "", "AN", "FILTER")
        self.ed_table.blockSignals(True)
        self._add_editor_row(Row(last.step, last.step_name, last.part, last.group, last.su, "", VALUE, "", "", "", ""))
        self.ed_table.blockSignals(False)
        self._editor_changed()

    def remove_editor_row(self) -> None:
        row = self.ed_table.currentRow()
        if row >= 0:
            self.ed_table.removeRow(row)
            self._editor_changed()

    def capture_current(self) -> None:
        """Each row's value as the JD-Xi has it now (to write a recipe from a sound)."""
        rows = self._editor_rows()
        table = self.ed_table
        table.blockSignals(True)
        for i, row in enumerate(rows):
            c = check.check_row(Row(**{**row.__dict__, "kind": VALUE, "value": "0"}))
            if c.target is None:
                continue
            text = recipe_apply.current_text(c, self.editors)
            if text and text != "—":
                table.setItem(i, 7, QTableWidgetItem(text.split(" / ")[0]))
                kind = table.cellWidget(i, 6)
                if isinstance(kind, QComboBox):
                    kind.setCurrentText(VALUE)
        table.blockSignals(False)
        self._editor_changed()

    def save_from_editor(self) -> None:
        recipe = self._editor_to_recipe()
        self.recipe_path = library.save(recipe, self.recipe_path)
        self.refresh_library()
        self.ed_status.setText(tr("Saved in the library: {path}").format(path=self.recipe_path.name))

    def export_recipe(self, path: Optional[str] = None) -> Optional[Path]:
        recipe = self._editor_to_recipe() if self.pages.currentWidget() is self.editor_page else self.recipe
        if recipe is None:
            return None
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, tr("Export the recipe"), str(Path.home() / f"{library.slug(recipe.title)}.xlsx"),
                                                  tr("Excel (*.xlsx);;CSV (*.csv);;Markdown (*.md)"))
        if not path:
            return None
        target = Path(path)
        if target.suffix.lower() == ".csv":
            recipe.to_csv(target)
        elif target.suffix.lower() == ".md":
            target.write_text(recipe.to_markdown(), encoding="utf-8")
        else:
            recipe.to_xlsx(target, Path(resource_path(TEMPLATE_DIR / template_name("xlsx"))))
        return target

    # ------------------------------------------------------------- pages
    def show_home(self) -> None:
        self.refresh_library()
        self.pages.setCurrentWidget(self.home)
