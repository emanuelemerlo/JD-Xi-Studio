"""
Recipes: step-by-step instructions to make a sound on the JD-Xi.

One workspace in three areas: the library on the left (always there: search,
new, open, edit, duplicate, export, delete), the work in the middle, and on the
right the panel that explains what is chosen (it can be closed).

The middle shows one of:
  LIBRARY   the recipe chosen on the left (or, with none, how to start)
  NEW       name, description, category; from scratch, from a document or a text
  CHECK     what the checker understood of each row, and what to fix
  GUIDE     step by step: the recipe's value next to the JD-Xi's, set one or all
  EDITOR    write or change a recipe with menus that only offer valid names

Nothing is sent to the JD-Xi until you set a value in the guide.
"""

from __future__ import annotations

from contextlib import contextmanager
import shutil
from pathlib import Path
from typing import Callable, Optional

from decologr import Decologr as log
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
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
CAPTURE_DELAY_MS = 800  # the editors read the JD-Xi before the values are taken
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


def _date(iso: str) -> str:
    """«2026-11-23T00:15:00» -> «23/11/2026» (empty if not a date)."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return ""


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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)
        from jdxi_editor.ui.v2 import density
        from jdxi_editor.ui.v2.restyle import title_badge
        from jdxi_editor.ui.v2.widgets import InfoPanel

        # the title at the top left, as in the other editors; under it the workspace
        self.title = title_badge(tr("Recipes"), ACCENT)
        bar = QHBoxLayout()
        bar.addWidget(self.title)
        # Where you are and the way back, always in the same place (the way
        # back was a «Recipes» button among the page's own buttons)
        self.back_button = _button("‹  " + tr("All recipes"))
        self.back_button.setToolTip(tr("Back to the library of recipes (Esc)"))
        self.back_button.clicked.connect(self.go_back)
        self.back_button.hide()
        self.where = _label("", 13, "#a3a6ad")
        bar.addSpacing(10)
        bar.addWidget(self.back_button)
        bar.addWidget(self.where, 1)
        self.panel_button = _button(tr("Details"))
        self.panel_button.setCheckable(True)
        self.panel_button.setToolTip(tr("Show or hide the panel on the right, that explains what is chosen"))
        self.panel_button.toggled.connect(self._panel_toggled)
        bar.addWidget(self.panel_button)
        outer.addLayout(bar)
        # library | work | explanation: one workspace, the sides can be resized or closed
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        self.splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        outer.addWidget(self.splitter, 1)
        self.sidebar = self._library_sidebar()
        self.splitter.addWidget(self.sidebar)
        center = QWidget()
        root = QVBoxLayout(center)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        self.splitter.addWidget(center)
        from PySide6.QtGui import QKeySequence, QShortcut

        self.back_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.back_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.back_shortcut.activated.connect(self.go_back)
        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        # the side panel of the other editors: what the row under the cursor is and says
        self.info_panel = InfoPanel(ACCENT)
        self.info_panel.setMinimumWidth(density.side_width(240))
        self.info_panel.setMaximumWidth(density.side_width(420))
        self.info_panel.head.setText(tr("RECIPE"))
        self.splitter.addWidget(self.info_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([density.side_width(260), 900, density.side_width(300)])
        self._panel_choice: dict[QWidget, bool] = {}  # the user's choice, per page
        self.pages.currentChanged.connect(lambda _i: self._explain_page())
        self.pages.currentChanged.connect(lambda _i: self._show_where())
        self.pages.currentChanged.connect(lambda _i: self._panel_for_page())
        self.home = self._home_page()
        self.create_page = self._create_page()
        self.check_page = self._check_page()
        self.guide_page = self._guide_page()
        self.editor_page = self._editor_page()
        for page in (self.home, self.create_page, self.check_page, self.guide_page, self.editor_page):
            self.pages.addWidget(page)
        self.refresh_library()
        self._explain_page()
        self._panel_for_page()

    # ------------------------------------------------------------ right panel
    # Open on the library and the guide; closed on a new recipe, the check and
    # the editor, which need the width (it opens when a row is chosen).
    PANEL_CLOSED_ON = ("create_page", "check_page", "editor_page")

    def _panel_default(self, page: QWidget) -> bool:
        return not any(page is getattr(self, name, None) for name in self.PANEL_CLOSED_ON)

    def _panel_for_page(self) -> None:
        page = self.pages.currentWidget()
        self._set_panel(self._panel_choice.get(page, self._panel_default(page)), remember=False)

    def _set_panel(self, visible: bool, remember: bool = True) -> None:
        self.panel_button.blockSignals(True)
        self.panel_button.setChecked(visible)
        self.panel_button.blockSignals(False)
        self.info_panel.setVisible(visible)
        if remember:
            self._panel_choice[self.pages.currentWidget()] = visible

    def _panel_toggled(self, visible: bool) -> None:
        self._set_panel(visible)

    # ------------------------------------------------------------ side panel
    def _explain_page(self) -> None:
        """What the page shown is for, until a row is chosen."""
        page = self.pages.currentWidget()
        if page is self.check_page:
            self.info_panel.show_text(
                tr("Check"), tr("What the editor understood"),
                tr("Each row of the file, as read and as understood. Recognized: ready. To confirm: a "
                   "likely meaning, choose it. To fix: not understood, correct it or exclude it. By ear: "
                   "the recipe says to tune it listening. Choose a row to see its explanation here."))
        elif page is self.guide_page:
            self.info_panel.show_text(
                tr("Guide"), tr("Step by step"),
                tr("Set the values of each step (one by one or all the missing ones), listen, then go "
                   "to the next step. Choose a row to see the recipe's note for it."))
        elif page is getattr(self, "create_page", None):
            self.info_panel.show_text(
                tr("New recipe"), tr("Three ways to start"),
                tr("From scratch: the editor, with menus that offer only what exists. From a document: a "
                   "filled-in template, a .csv, a text or a PDF. From a text: a table copied from a page. "
                   "Whichever you choose, every row is checked before the recipe is kept; the name can wait "
                   "until it is saved."))
        elif page is self.editor_page:
            self.info_panel.show_text(
                tr("Editor"), tr("Write or correct a recipe"),
                tr("The menus offer only the parts, groups and parameters that exist; the Check column "
                   "says at once if a row is understood."))
        else:
            self.info_panel.show_text(
                tr("Recipes"), tr("Sounds as lists of steps"),
                tr("A recipe says, step by step, which parameters to set and to what value. Fill in the "
                   "template, import a file or a pasted text, or write one in the editor: it is checked "
                   "row by row, and nothing goes to the JD-Xi until you decide."))

    def _explain_row(self, c: "check.Checked", current: str = "", state: str = "") -> None:
        if not self.info_panel.isVisible():
            self._set_panel(True)  # a row chosen: its explanation
        t = c.target
        group = f"{t.part}: {t.group}" if t is not None else (c.row.group or tr("Not understood"))
        name = (t.label if t is not None else c.row.param) or c.row.source or "—"
        note = c.row.note or (c.message if c.status != check.OK else "")
        if c.status == check.EARS:
            note = (note + " — " if note else "") + tr(
                "Values \"by ear\" are not set automatically: the editor opens the control and leaves the tuning to you.")
        self.info_panel.show_text(group, name, note or status_text(c.status), c.row.source or "")
        self.info_panel.value.setText(recipe_value_text(c.row))
        details = [tr("Recipe: {value}").format(value=recipe_value_text(c.row))]
        if current:
            details.append(tr("On the JD-Xi: {value}").format(value=current))
        if state:
            details.append(state)
        self.info_panel.range.setText(" · ".join(details))

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
    # ------------------------------------------------------------ library
    def _library_sidebar(self) -> QWidget:
        """On the left, always: the saved recipes, a search, and what can be done with the chosen one."""
        from jdxi_editor.ui.v2 import density

        side = QFrame()
        side.setObjectName("recipeLibrary")
        side.setStyleSheet("#recipeLibrary { background: #17181b; border: 1px solid #2a2d33; border-radius: 8px; }")
        side.setMinimumWidth(density.side_width(220))
        side.setMaximumWidth(density.side_width(420))
        col = QVBoxLayout(side)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(8)
        col.addWidget(_label(tr("MY RECIPES"), 12, ACCENT, True))
        self.new_button = _button("+  " + tr("New recipe"), True)
        self.new_button.setToolTip(tr("From scratch, from a document or from a pasted text"))
        self.new_button.clicked.connect(self.show_create_page)
        col.addWidget(self.new_button)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search…"))
        self.search.setClearButtonEnabled(True)
        self.search.setStyleSheet("QLineEdit { background: #121214; color: #e6e6e6; border: 1px solid #3a3d44; "
                                  "border-radius: 5px; padding: 4px 6px; }")
        self.search.textChanged.connect(lambda _t: self.refresh_library())
        col.addWidget(self.search)
        self.library_list = QListWidget()
        self.library_list.setStyleSheet("QListWidget { background: #121214; color: #e6e6e6; border: 1px solid #2a2d33; }"
                                        "QListWidget::item { padding: 6px; border-bottom: 1px solid #1f2125; }"
                                        "QListWidget::item:selected { background: #2a3a30; }")
        self.library_list.setWordWrap(True)
        self.library_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.library_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.library_list.itemDoubleClicked.connect(lambda _i: self.open_selected())
        self.library_list.currentItemChanged.connect(lambda _c, _p: self._library_selection_changed())
        self.library_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.library_list.customContextMenuRequested.connect(
            lambda pos: self._recipe_menu().exec(self.library_list.viewport().mapToGlobal(pos)))
        col.addWidget(self.library_list, 1)
        buttons = QHBoxLayout()
        self.open_button = _button(tr("Open"), True)
        self.open_button.setToolTip(tr("The guide: step by step on the JD-Xi"))
        self.open_button.clicked.connect(self.open_selected)
        self.edit_button = _button(tr("Edit"))
        self.edit_button.clicked.connect(lambda: self.open_selected(edit=True))
        self.more_button = _button("⋯")
        self.more_button.setToolTip(tr("Duplicate, export, delete"))
        self.more_button.clicked.connect(
            lambda: self._recipe_menu().exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft())))
        for b in (self.open_button, self.edit_button, self.more_button):
            buttons.addWidget(b)
        buttons.addStretch()
        col.addLayout(buttons)
        return side

    def _recipe_menu(self) -> QMenu:
        """Duplicate, Export…, Delete: for the recipe chosen in the library."""
        menu = QMenu(self)
        chosen = self._selected_path() is not None
        for text, slot in ((tr("Open"), self.open_selected), (tr("Edit"), lambda: self.open_selected(edit=True)),
                           (None, None), (tr("Duplicate"), self.duplicate_selected),
                           (tr("Export…"), self.export_selected), (None, None), (tr("Delete…"), self.delete_selected)):
            if text is None:
                menu.addSeparator()
                continue
            action = menu.addAction(text)
            action.setEnabled(chosen)
            action.triggered.connect(lambda _c=False, slot=slot: slot())
        return menu

    def _home_page(self) -> QWidget:
        """The middle with the library shown: the chosen recipe, or how to start."""
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        self.home_stack = QStackedWidget()
        col.addWidget(self.home_stack, 1)

        # nothing chosen (or nothing saved yet): how to start
        start = QWidget()
        sc = QVBoxLayout(start)
        sc.addStretch(1)
        self.start_title = _label("", 20, "#ffffff", True)
        self.start_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_text = _label("", 13, "#a3a6ad")
        self.start_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sc.addWidget(self.start_title)
        sc.addWidget(self.start_text)
        line = QHBoxLayout()
        line.addStretch()
        create = _button(tr("Create a new recipe"), True)
        create.clicked.connect(self.show_create_page)
        imp = _button(tr("Import a recipe…"))
        imp.clicked.connect(lambda: self.import_file())
        line.addWidget(create)
        line.addWidget(imp)
        line.addStretch()
        sc.addSpacing(12)
        sc.addLayout(line)
        sc.addStretch(2)
        self.home_stack.addWidget(start)
        self.start_page = start

        # a recipe chosen: what it is, its steps, what to do with it
        detail = Card(tr("RECIPE"), ACCENT)
        self.detail_title = _label("", 20, "#ffffff", True)
        self.detail_meta = _label("", 12, "#8a8d94")
        self.detail_description = _label("", 13)
        self.detail_counts = _label("", 12, ACCENT, True)
        for w in (self.detail_title, self.detail_meta, self.detail_description, self.detail_counts):
            detail.body.addWidget(w)
        self.detail_steps = QListWidget()
        self.detail_steps.setStyleSheet("QListWidget { background: #121214; color: #c9cbd1; border: 1px solid #2a2d33; }"
                                        "QListWidget::item { padding: 5px; }")
        self.detail_steps.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        detail.body.addWidget(self.detail_steps, 1)
        line = QHBoxLayout()
        use = _button(tr("Open the guide"), True)
        use.setToolTip(tr("Step by step: the recipe's values next to the JD-Xi's; nothing is sent until you set it"))
        use.clicked.connect(self.open_selected)
        edit = _button(tr("Edit"))
        edit.clicked.connect(lambda: self.open_selected(edit=True))
        dup = _button(tr("Duplicate"))
        dup.clicked.connect(self.duplicate_selected)
        exp = _button(tr("Export…"))
        exp.clicked.connect(self.export_selected)
        delete = _button(tr("Delete…"))
        delete.clicked.connect(self.delete_selected)
        for b in (use, edit, dup, exp):
            line.addWidget(b)
        line.addStretch()
        line.addWidget(delete)
        detail.body.addLayout(line)
        self.home_stack.addWidget(detail)
        self.detail_card = detail
        return page

    def _create_page(self) -> QWidget:
        """New recipe: its name (needed only to save it); with an AI, or three other ways to start."""
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        field_style = ("QLineEdit, QComboBox { background: #121214; color: #e6e6e6; border: 1px solid #3a3d44; "
                       "border-radius: 5px; padding: 4px 6px; }")
        info = Card(tr("NEW RECIPE"), ACCENT)
        grid = QHBoxLayout()
        self.new_title = QLineEdit()
        self.new_title.setPlaceholderText(tr("Needed to save it; an imported file brings its own"))
        self.new_category = QComboBox()
        self.new_category.setEditable(True)
        self.new_description = QLineEdit()
        for w in (self.new_title, self.new_category, self.new_description):
            w.setStyleSheet(field_style)
        for label, widget, stretch in ((tr("Name"), self.new_title, 3), (tr("Category"), self.new_category, 1)):
            grid.addWidget(_label(label, 12))
            grid.addWidget(widget, stretch)
        info.body.addLayout(grid)
        line = QHBoxLayout()
        line.addWidget(_label(tr("Description"), 12))
        line.addWidget(self.new_description, 1)
        info.body.addLayout(line)
        col.addWidget(info)

        col.addWidget(self._ai_card())
        ways = QHBoxLayout()
        ways.setSpacing(12)
        scratch = Card(tr("FROM SCRATCH"), ACCENT)
        scratch.body.addWidget(_label(tr("The editor: Part, Group and Parameter have menus with only the names "
                                         "that exist, and every row is checked while you write."), 12))
        write = _button(tr("Continue in the editor"), True)
        write.clicked.connect(self.new_in_editor)
        scratch.body.addWidget(write, 0, Qt.AlignmentFlag.AlignLeft)
        scratch.body.addStretch()
        ways.addWidget(scratch, 1)

        document = Card(tr("FROM A DOCUMENT"), ACCENT)
        document.body.addWidget(_label(tr("A filled-in template, a .csv, a Markdown or text file, a PDF: "
                                          "each row is read and checked before it becomes the recipe."), 12))
        choose = _button(tr("Choose a file…"), True)
        choose.clicked.connect(lambda: self.import_file())
        document.body.addWidget(choose, 0, Qt.AlignmentFlag.AlignLeft)
        document.body.addWidget(_label(".xlsx · .csv · .md · .txt · .pdf", 11, "#8a8d94"))
        document.body.addSpacing(6)
        document.body.addWidget(_label(tr("No document yet? The template: menus with the valid names, a sheet "
                                          "with every parameter and the Jungle Gardenia lead as an example."),
                                       11, "#a3a6ad"))
        line = QVBoxLayout()  # one under the other: the three cards share the width
        xlsx = _button(tr("Template .xlsx…"))
        xlsx.clicked.connect(lambda: self.save_template(template_name("xlsx")))
        csv_b = _button(tr("Template .csv…"))
        csv_b.clicked.connect(lambda: self.save_template(template_name("csv")))
        params = _button(tr("Parameter list .csv…"))
        params.clicked.connect(lambda: self.save_template(template_name("parameters")))
        for b in (xlsx, csv_b, params):
            line.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        document.body.addLayout(line)
        document.body.addStretch()
        ways.addWidget(document, 1)

        text = Card(tr("FROM A TEXT"), ACCENT)
        self.paste = QPlainTextEdit()
        self.paste.setPlaceholderText(tr("…or paste a table copied from a document or a web page, e.g.\nTONE: FILTER\tCutoff\t55–65\nTONE: FILTER\tCutoff KF\t+50"))
        self.paste.setStyleSheet("QPlainTextEdit { background: #121214; color: #e6e6e6; border: 1px solid #2a2d33; font-family: monospace; }")
        text.body.addWidget(self.paste, 1)
        read = _button(tr("Read the text"), True)
        read.clicked.connect(self.import_text)
        text.body.addWidget(read, 0, Qt.AlignmentFlag.AlignLeft)
        text.body.addWidget(_label(tr("From PDFs and texts only the lines that look like Group · Parameter · Value are taken; the rest is kept as notes."), 11, "#8a8d94"))
        ways.addWidget(text, 1)
        from PySide6.QtWidgets import QSizePolicy

        for card in (scratch, document, text):  # side by side, as wide and as tall as each other
            card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
            card.setMinimumWidth(200)
        col.addLayout(ways, 1)

        bottom = QHBoxLayout()
        cancel = _button(tr("Cancel"))
        cancel.clicked.connect(self.show_home)
        bottom.addWidget(cancel)
        bottom.addStretch()
        col.addLayout(bottom)
        return page

    def _ai_card(self) -> QWidget:
        """
        With an AI: the way the recipes are meant to be made. The request (the
        sound, the part, the format, the rules and the parameter list) is copied
        for a chat; its answer is pasted back and checked like any recipe.
        """
        card = Card(tr("WITH AN AI"), ACCENT)
        line = QHBoxLayout()
        line.setSpacing(12)
        left = QVBoxLayout()
        left.addWidget(_label(tr("Which sound should the JD-Xi reproduce?"), 12, "#ffffff", True))
        self.ai_sound = QPlainTextEdit()
        self.ai_sound.setPlaceholderText(tr("e.g. the lead of «Jungle Gardenia» by Peter Gabriel: soft, "
                                            "flute-like, legato, with vibrato"))
        self.ai_sound.setFixedHeight(66)
        self.ai_sound.setStyleSheet("QPlainTextEdit { background: #121214; color: #e6e6e6; "
                                    "border: 1px solid #3a3d44; border-radius: 5px; }")
        left.addWidget(self.ai_sound)
        part_line = QHBoxLayout()
        part_line.addWidget(_label(tr("Part"), 12))
        self.ai_part = QComboBox()
        for text, code in ((tr("as the AI chooses"), ""), ("Digital 1", "D1"), ("Digital 2", "D2"),
                           ("Analog", "AN"), ("Drums", "DR")):
            self.ai_part.addItem(text, code)
        self.ai_part.setStyleSheet("QComboBox { background: #121214; color: #e6e6e6; border: 1px solid #3a3d44; "
                                   "border-radius: 5px; padding: 3px 6px; }")
        part_line.addWidget(self.ai_part)
        part_line.addStretch()
        left.addLayout(part_line)
        line.addLayout(left, 3)
        right = QVBoxLayout()
        right.addWidget(_label(tr("1. Copy the request and paste it into an AI's chat (Claude, ChatGPT…).\n"
                                  "2. Copy its answer and paste it here: every row is checked.\n"
                                  "3. Import, then fine-tune by ear with the guide and save."), 12, "#c9cbd1"))
        buttons = QHBoxLayout()
        self.ai_copy_button = _button(tr("Copy the request"), True)
        self.ai_copy_button.setToolTip(tr("The sound, the part, the format, the rules and the list of the "
                                          "parameters the AI may set"))
        self.ai_copy_button.clicked.connect(self.copy_ai_request)
        save = _button(tr("Save the request…"))
        save.setToolTip(tr("As a text file, to attach to the chat"))
        save.clicked.connect(lambda: self.save_ai_request())
        self.ai_paste_button = _button(tr("Paste the answer"), True)
        self.ai_paste_button.setToolTip(tr("Reads the AI's answer from the clipboard (the CSV in it)"))
        self.ai_paste_button.clicked.connect(self.paste_ai_answer)
        for b in (self.ai_copy_button, save, self.ai_paste_button):
            buttons.addWidget(b)
        buttons.addStretch()
        right.addLayout(buttons)
        self.ai_status = _label("", 11, "#8a8d94")
        right.addWidget(self.ai_status)
        right.addStretch()
        line.addLayout(right, 4)
        card.body.addLayout(line)
        return card

    def ai_request(self) -> str:
        from jdxi_editor.i18n import current_language
        from jdxi_editor.recipes import ai_request

        return ai_request.build(self.ai_sound.toPlainText(), self.ai_part.currentData() or "", current_language())

    def copy_ai_request(self) -> None:
        QApplication.clipboard().setText(self.ai_request())
        self.ai_status.setText(tr("Request copied: paste it into the AI's chat."))

    def save_ai_request(self, target: Optional[str] = None) -> Optional[Path]:
        if target is None:
            target, _ = QFileDialog.getSaveFileName(self, tr("Save the request"),
                                                    str(Path.home() / tr("JD-Xi recipe request.txt")),
                                                    tr("Text (*.txt *.md)"))
        if not target:
            return None
        Path(target).write_text(self.ai_request(), encoding="utf-8")
        self.ai_status.setText(tr("Request saved in {path}.").format(path=target))
        return Path(target)

    def paste_ai_answer(self) -> None:
        """The AI's answer from the clipboard: read and checked as a pasted text."""
        text = QApplication.clipboard().text()
        if not text.strip():
            self.ai_status.setText(tr("The clipboard is empty: copy the AI's answer first."))
            return
        sound = self.ai_sound.toPlainText().strip()
        self.paste.setPlainText(text)
        recipe = reader.read_text(text)
        if not recipe.rows:
            self.ai_status.setText(tr("No recipe in the clipboard: copy the AI's whole answer (the CSV in it)."))
            return
        self.import_text()
        if sound and not self.recipe.description:  # what was asked: the recipe's description
            self.recipe.description = sound

    def show_create_page(self) -> None:
        """+ New recipe: the fields empty, the categories already used offered."""
        if not self._may_leave():
            return
        for w in (self.new_title, self.new_description):
            w.clear()
        self.ai_status.setText("")
        self.new_category.clear()
        used = sorted({r.category for _p, r in library.entries() if r.category}, key=str.lower)
        self.new_category.addItems([""] + used)
        self.paste.clear()
        self.pages.setCurrentWidget(self.create_page)
        self.new_title.setFocus()

    def _new_metadata(self, recipe: Recipe) -> Recipe:
        """What was typed on the New recipe page goes into *recipe* (the name only if typed)."""
        if self.pages.currentWidget() is not self.create_page:
            return recipe
        title = self.new_title.text().strip()
        if title:
            recipe.title = title
        if self.new_description.text().strip():
            recipe.description = self.new_description.text().strip()
        if self.new_category.currentText().strip():
            recipe.category = self.new_category.currentText().strip()
        return recipe

    def refresh_library(self, select: Optional[Path] = None) -> None:
        """The library again (after a save, a delete, a search), *select* chosen if given."""
        chosen = select or self._selected_path()
        self._refresh_library(chosen)
        empty = self.library_list.count() == 0
        if empty:  # say what goes here, not an empty box
            text = (tr("No recipe matches «{text}».").format(text=self.search.text().strip())
                    if self.search.text().strip() else
                    tr("No recipes yet: import one or fill in the template (on the right)."))
            item = QListWidgetItem(text)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.library_list.addItem(item)
        self._library_selection_changed()

    def _refresh_library(self, chosen: Optional[Path] = None) -> None:
        self.library_list.blockSignals(True)
        self.library_list.clear()
        self._entries = library.entries()
        wanted = self.search.text().strip().lower() if hasattr(self, "search") else ""
        for path, recipe in self._entries:
            title = recipe.title or path.stem
            if wanted and wanted not in " ".join((title, recipe.category, recipe.description)).lower():
                continue
            second = " · ".join(x for x in (recipe.category, _date(recipe.modified)) if x)
            item = QListWidgetItem(title + (f"\n{second}" if second else ""))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(recipe.description or title)
            self.library_list.addItem(item)
            if chosen is not None and path == chosen:
                self.library_list.setCurrentItem(item)
        self.library_list.blockSignals(False)

    def _selected_path(self) -> Optional[Path]:
        item = self.library_list.currentItem() if hasattr(self, "library_list") else None
        data = item.data(Qt.ItemDataRole.UserRole) if item else None
        return Path(data) if data else None  # not the "no recipes yet" line

    def _selected_recipe(self) -> Optional[Recipe]:
        path = self._selected_path()
        for p, recipe in getattr(self, "_entries", []):
            if p == path:
                return recipe
        return None

    def _library_selection_changed(self) -> None:
        """The middle shows the recipe chosen in the library (when the library is what it shows)."""
        if not hasattr(self, "home_stack"):
            return
        chosen = self._selected_path() is not None
        for b in (self.open_button, self.edit_button):
            b.setEnabled(chosen)
        recipe = self._selected_recipe()
        if recipe is None:
            nothing_saved = not getattr(self, "_entries", [])
            self.start_title.setText(tr("No recipes yet") if nothing_saved else tr("Choose a recipe"))
            self.start_text.setText(
                tr("A recipe says, step by step, which parameters to set and to what value. Create one from "
                   "scratch, from a document or from a pasted text.") if nothing_saved else
                tr("The recipes are on the left: choose one to see it here, or create a new one."))
            self.home_stack.setCurrentWidget(self.start_page)
            return
        self.detail_title.setText(recipe.title or self._selected_path().stem)
        meta = [recipe.category] if recipe.category else []
        if recipe.created:
            meta.append(tr("created {date}").format(date=_date(recipe.created)))
        if recipe.modified:
            meta.append(tr("changed {date}").format(date=_date(recipe.modified)))
        if recipe.base_tone:
            meta.append(tr("from {tone}").format(tone=recipe.base_tone))
        self.detail_meta.setText(" · ".join(meta))
        self.detail_description.setText(recipe.description)
        self.detail_description.setVisible(bool(recipe.description))
        steps = recipe.steps()
        self.detail_counts.setText(tr("{steps} steps · {rows} parameters").format(steps=len(steps), rows=len(recipe.rows)))
        self.detail_steps.clear()
        for number, name, rows in steps:
            groups = ", ".join(dict.fromkeys(f"{r.part} {r.group}".strip() for r in rows))
            self.detail_steps.addItem(f"{number} · {name or tr('Step {n}').format(n=number)}   —   "
                                      + tr("{n} parameters").format(n=len(rows)) + (f"   ({groups})" if groups else ""))
        self.home_stack.setCurrentWidget(self.detail_card)

    def open_selected(self, edit: bool = False) -> None:
        path = self._selected_path()
        if path is None or not self._may_leave():
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
        recipe = self._selected_recipe()
        name = (recipe.title if recipe else "") or path.stem
        if QMessageBox.question(self, tr("Delete recipe"), tr("Delete \"{name}\"?").format(name=name)) \
                == QMessageBox.StandardButton.Yes:
            library.delete(path)
            if self.recipe_path == path:
                self.recipe_path = None
            self.library_list.setCurrentItem(None)
            self.refresh_library()

    def duplicate_selected(self) -> Optional[Path]:
        """A copy of the chosen recipe, a recipe of its own, chosen in the library."""
        path = self._selected_path()
        if path is None:
            return None
        recipe = self._selected_recipe()
        copy = library.duplicate(path, tr("{title} (copy)").format(title=(recipe.title if recipe else "") or path.stem))
        self._refresh_library(copy)
        self.refresh_library()
        return copy

    def export_selected(self, target: Optional[str] = None) -> Optional[Path]:
        path = self._selected_path()
        if path is None:
            return None
        return self.export_recipe(target, recipe=library.load(path))

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
        if not path or not self._may_leave():
            return
        try:
            recipe = reader.read_file(path)
        except Exception as ex:  # a damaged or unreadable file
            log.warning(f"Recipes: could not read {path}: {ex}", scope="RecipesEditor")
            QMessageBox.warning(self, tr("Import a recipe"), tr("Could not read the file: {error}").format(error=ex))
            return
        log.message(f"Recipes: read {path}: {len(recipe.rows)} rows", scope="RecipesEditor")
        self._new_metadata(recipe)
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
        self._new_metadata(recipe)
        recipe.title = recipe.title or tr("Pasted recipe")
        self.recipe_path = None
        self.set_recipe(recipe, source=tr("pasted text"))
        self.show_check()

    def new_in_editor(self) -> None:
        if not self._may_leave():
            return
        self.recipe_path = None
        recipe = self._new_metadata(Recipe(rows=[Row(1, tr("Step 1"), "AN", "FILTER", "", "Cutoff", VALUE, "64")]))
        recipe.title = recipe.title or tr("New recipe")
        self.set_recipe(recipe)
        self.show_editor_page()

    def set_recipe(self, recipe: Recipe, source: str = "") -> None:
        self.recipe = recipe
        self.source = source
        self.checked = check.check(recipe)
        self.step_index = 0
        from collections import Counter

        counts = Counter(c.status for c in self.checked)
        log.message(f"Recipes: «{recipe.title}» checked: {dict(counts)}", scope="RecipesEditor")
        for c in self.checked:
            if c.status in (check.FIX, check.CONFIRM):
                log.message(f"Recipes: {c.row.source} {c.row.part} {c.row.group} {c.row.param} = "
                            f"{c.row.value}: {c.status} — {c.message}", scope="RecipesEditor")

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
        self.check_table.verticalHeader().setDefaultSectionSize(34)
        self.check_table.setWordWrap(False)
        self.check_table.currentCellChanged.connect(
            lambda row, *_: self._explain_row(self.checked[row]) if 0 <= row < len(self.checked) else None
        )
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
        header = table.horizontalHeader()
        for column, mode in enumerate((
            QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.ResizeToContents,
            QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.Stretch,
            QHeaderView.ResizeMode.ResizeToContents,
        )):
            header.setSectionResizeMode(column, mode)
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
        try:
            self.recipe_path = library.save(self.recipe, self.recipe_path)
        except OSError as ex:  # the folder cannot be written
            log.warning(f"Recipes: saving «{self.recipe.title}» failed: {ex}", scope="RecipesEditor")
            QMessageBox.warning(self, tr("Recipes"), tr("Could not save the recipe: {error}").format(error=ex))
            return
        log.message(f"Recipes: «{self.recipe.title}» saved in {self.recipe_path}", scope="RecipesEditor")
        self.refresh_library(self.recipe_path)
        self.show_guide()

    # -------------------------------------------------------------- guide
    def _guide_page(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        top = QHBoxLayout()
        self.guide_title = _label("", 16, "#ffffff", True)
        top.addWidget(self.guide_title, 1)
        edit = _button(tr("Edit the recipe"))
        edit.clicked.connect(self.show_editor_page)
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
        self.guide_table.verticalHeader().setDefaultSectionSize(36)
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
            line.addStretch()  # the buttons at the left of the column
            table.setCellWidget(i, 5, box)
        header = table.horizontalHeader()
        for column in range(5):  # the columns as wide as their text, the actions take the rest
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
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
            self.guide_note.setVisible(False)  # shown in the side panel, with the values
            item = self.guide_table.item(row, 3)
            state = self.guide_table.item(row, 4)
            self._explain_row(c, item.text() if item else "", state.text() if state else "")

    @contextmanager
    def _one_undo(self, rows):
        """The values set for *rows* as one Undo step in each editor they touch."""
        histories = []
        for key in {c.target.editor_key for c in rows if c.target is not None}:
            history = getattr(self.editors(key), "history", None)
            if history is not None and history not in histories:
                histories.append(history)
        from jdxi_editor.ui.v2.history import transaction

        with transaction():  # one Undo for all the editors the step touches
            for history in histories:
                history.begin_group()
            try:
                yield
            finally:
                for history in histories:
                    history.end_group()

    def set_row(self, c: check.Checked) -> None:
        with self._one_undo([c]):
            recipe_apply.apply(c, self.editors)
        self._fill_guide()

    def set_step(self) -> int:
        count = 0
        rows = [c for c in self._step_checked() if c.status != check.EARS]
        with self._one_undo(rows):
            for c in rows:
                count += recipe_apply.apply(c, self.editors)
        if count and self.recipe is not None:
            self._recipe_origin(rows)
        self._fill_guide()
        return count

    def _recipe_origin(self, rows) -> None:
        """The parts a recipe step set: their origin in the context line."""
        from jdxi_editor.ui.v2.context import sound_context

        title = getattr(self.recipe, "title", "") or tr("recipe")
        for key in {c.target.editor_key for c in rows if c.target is not None}:
            history = getattr(self.editors(key), "history", None)
            part = getattr(history, "part", "")
            sound_context().part_origin(part, tr("recipe «{title}»").format(title=title))

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
        line.addWidget(self.ed_description, 3)
        self.ed_category = QLineEdit()
        self.ed_category.setStyleSheet(self.ed_title.styleSheet())
        self.ed_category.setPlaceholderText(tr("Lead, Pad, Bass…"))
        line.addWidget(_label(tr("Category"), 12))
        line.addWidget(self.ed_category, 1)
        col.addLayout(line)
        # the steps on the left (the recipe's order), the chosen step's rows on the right
        work = QHBoxLayout()
        steps_col = QVBoxLayout()
        steps_col.addWidget(_label(tr("STEPS"), 11, ACCENT, True))
        self.ed_steps = QListWidget()
        self.ed_steps.setStyleSheet("QListWidget { background: #121214; color: #e6e6e6; border: 1px solid #2a2d33; }"
                                    "QListWidget::item { padding: 5px; } QListWidget::item:selected { background: #2a3a30; }")
        self.ed_steps.setFixedWidth(200)
        self.ed_steps.setToolTip(tr("Double-click a step to rename it"))
        self.ed_steps.currentItemChanged.connect(lambda _c, _p: self._show_step())
        self.ed_steps.itemChanged.connect(self._step_renamed)
        steps_col.addWidget(self.ed_steps, 1)
        step_buttons = QHBoxLayout()
        step_buttons.setSpacing(4)
        import qtawesome as qta

        for icon, tip, slot in (("mdi.plus", tr("Add a step"), self.add_step),
                                ("mdi.content-copy", tr("Duplicate the step"), self.duplicate_step),
                                ("mdi.arrow-up", tr("Move the step up"), lambda: self.move_step(-1)),
                                ("mdi.arrow-down", tr("Move the step down"), lambda: self.move_step(1)),
                                ("mdi.delete-outline", tr("Delete the step and its rows"), self.delete_step)):
            b = _button("")
            b.setIcon(qta.icon(icon, color="#e6e6e6"))
            b.setToolTip(tip)
            b.setFixedWidth(36)
            b.clicked.connect(lambda _c=False, slot=slot: slot())
            step_buttons.addWidget(b)
        step_buttons.addStretch()
        steps_col.addLayout(step_buttons)
        work.addLayout(steps_col)
        self.ed_table = QTableWidget(0, len(COLUMNS) + 1)
        self.ed_table.setHorizontalHeaderLabels(COLUMNS + [tr("Check")])
        self.ed_table.setStyleSheet(TABLE)
        self.ed_table.verticalHeader().setVisible(False)
        self.ed_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ed_table.itemChanged.connect(lambda _item: self._editor_changed())
        self.ed_table.currentCellChanged.connect(lambda r, _c, _pr, _pc: self._explain_editor_row(r))
        work.addWidget(self.ed_table, 1)
        col.addLayout(work, 1)
        from PySide6.QtGui import QKeySequence, QShortcut

        for keys, slot in ((QKeySequence.StandardKey.Copy, self.copy_editor_rows),
                           (QKeySequence.StandardKey.Paste, self.paste_editor_rows)):
            shortcut = QShortcut(QKeySequence(keys), self.ed_table)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)
        self.ed_status = _label("", 12)
        col.addWidget(self.ed_status)
        col.addWidget(_label(tr("The menus show only what exists: choosing the part AN, the group offers COMMON, OSC, PITCH, FILTER, AMP, LFO, "
                                "and the parameter shows its range. The check is the same as for imported files, while you write."), 11, "#8a8d94"))
        bottom = QHBoxLayout()
        add = _button(tr("Add row"))
        add.clicked.connect(self.add_editor_row)
        remove = _button(tr("Remove row"))
        remove.clicked.connect(self.remove_editor_row)
        rows_menu = _button(tr("Rows") + "  ▾")
        menu = QMenu(rows_menu)
        for text, slot in ((tr("Duplicate the rows"), self.duplicate_editor_rows),
                           (tr("Move up"), lambda: self.move_editor_rows(-1)),
                           (tr("Move down"), lambda: self.move_editor_rows(1)),
                           (None, None),
                           (tr("Copy the rows (Ctrl+C)"), self.copy_editor_rows),
                           (tr("Paste rows (Ctrl+V)"), self.paste_editor_rows)):
            if text is None:
                menu.addSeparator()
            else:
                menu.addAction(text).triggered.connect(lambda _c=False, slot=slot: slot())
        rows_menu.setMenu(menu)
        capture = _button(tr("Take the values from the JD-Xi"))
        capture.setToolTip(tr("Writes in each row the value the parameter has now"))
        capture.clicked.connect(self.capture_current)
        export = _button(tr("Export…"))
        export.clicked.connect(self.export_recipe)
        try_b = _button(tr("Try the recipe"))
        try_b.clicked.connect(lambda: (self._editor_to_recipe(), self.show_check()))
        save = _button(tr("Save recipe"), True)
        save.clicked.connect(self.save_from_editor)
        save_as = _button(tr("Save as…"))
        save_as.setToolTip(tr("Save as a new recipe, the original as it was"))
        save_as.clicked.connect(lambda: self.save_as_from_editor())
        self.revert_button = _button(tr("Undo changes"))
        self.revert_button.setToolTip(tr("Back to the recipe as it was saved"))
        self.revert_button.clicked.connect(self.revert_editor)
        # two rows: the rows' tools, then what is done with the recipe (one row did not fit at 1280 px)
        for b in (add, remove, rows_menu, capture):
            bottom.addWidget(b)
        bottom.addStretch()
        col.addLayout(bottom)
        bottom = QHBoxLayout()
        bottom.addStretch()
        for b in (export, try_b, self.revert_button, save_as, save):
            bottom.addWidget(b)
        col.addLayout(bottom)
        return page

    def show_editor_page(self) -> None:
        r = self.recipe or Recipe()
        self.ed_title.setText(r.title)
        self.ed_base.setText(r.base_tone)
        self.ed_program.setText(r.user_program)
        self.ed_description.setText(r.description)
        self.ed_category.setText(r.category)
        table = self.ed_table
        for col, width in enumerate((48, 110, 64, 100, 48, 150, 96, 80, 44, 44)):
            table.setColumnWidth(col, width)
        table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(11, 220)
        self._set_editor_rows(r.rows, step=None)
        if self.ed_steps.count() > 1:
            self.ed_steps.setCurrentRow(1)  # the first step (row 0: all of them)
        self._editor_snapshot = self._editor_state()
        import copy

        self._snapshot_recipe = copy.deepcopy(r)  # «Undo changes» of a recipe not saved yet
        self.revert_button.setEnabled(False)
        self.pages.setCurrentWidget(self.editor_page)

    def _editor_state(self) -> tuple:
        """What the editor holds (to tell unsaved changes)."""
        fields = tuple(f.text() for f in (self.ed_title, self.ed_base, self.ed_program, self.ed_description,
                                          self.ed_category))
        return fields, tuple(repr(row) for row in self._editor_rows())

    def editor_has_changes(self) -> bool:
        return self._editor_state() != getattr(self, "_editor_snapshot", None)

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
        r.category = self.ed_category.text().strip()
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
        self._refresh_steps(rows)
        self._show_step()  # a row moved to another step by its Step cell
        self._show_where()  # «not saved» in the breadcrumb
        if hasattr(self, "revert_button"):
            self.revert_button.setEnabled(self.editor_has_changes())
        if not rows:
            self.ed_status.setText(tr("No rows yet: «Add row» to start"))
            return
        self.ed_status.setText(tr("All {n} rows are valid").format(n=len(rows)) if not bad
                               else tr("{bad} of {n} rows to fix").format(bad=bad, n=len(rows)))

    # ------------------------------------------------------------ editor: steps
    ALL_STEPS = -1  # the steps list's first line: every row

    def _set_editor_rows(self, rows: list[Row], step: Optional[int] = None, select: Optional[int] = None) -> None:
        """The table filled again with *rows* (in step order), *step* shown, row *select* chosen."""
        table = self.ed_table
        table.blockSignals(True)
        table.setRowCount(0)
        for row in sorted(rows, key=lambda r: r.step):  # stable: a step's rows keep their order
            self._add_editor_row(row)
        table.blockSignals(False)
        self._editor_changed()
        if step is not None:
            self._select_step(step)
        self._show_step()
        if select is not None and 0 <= select < table.rowCount():
            table.setCurrentCell(select, 7)

    def _refresh_steps(self, rows: list[Row]) -> None:
        """The steps list from the rows: «n · name (rows)»; the chosen one kept."""
        if not hasattr(self, "ed_steps"):
            return
        chosen = self.current_step()
        steps = Recipe(rows=rows).steps()
        self.ed_steps.blockSignals(True)
        self.ed_steps.clear()
        every = QListWidgetItem(tr("All steps ({n})").format(n=len(rows)))
        every.setData(Qt.ItemDataRole.UserRole, self.ALL_STEPS)
        self.ed_steps.addItem(every)
        for number, name, step_rows in steps:
            item = QListWidgetItem(name or tr("Step {n}").format(n=number))
            item.setData(Qt.ItemDataRole.UserRole, number)
            item.setToolTip(tr("Step {n} · {rows} rows").format(n=number, rows=len(step_rows)))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.ed_steps.addItem(item)
        self.ed_steps.blockSignals(False)
        self._select_step(chosen if chosen is not None else self.ALL_STEPS, show=False)

    def current_step(self) -> Optional[int]:
        item = self.ed_steps.currentItem() if hasattr(self, "ed_steps") else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _select_step(self, number: int, show: bool = True) -> None:
        for i in range(self.ed_steps.count()):
            if self.ed_steps.item(i).data(Qt.ItemDataRole.UserRole) == number:
                self.ed_steps.blockSignals(not show)
                self.ed_steps.setCurrentRow(i)
                self.ed_steps.blockSignals(False)
                return
        if self.ed_steps.count():
            self.ed_steps.blockSignals(not show)
            self.ed_steps.setCurrentRow(0)
            self.ed_steps.blockSignals(False)

    def _show_step(self) -> None:
        """Only the chosen step's rows (all with «All steps»); its Step columns hidden then."""
        step = self.current_step()
        every = step in (None, self.ALL_STEPS)
        rows = self._editor_rows()
        for i, row in enumerate(rows):
            self.ed_table.setRowHidden(i, not every and row.step != step)
        self.ed_table.setColumnHidden(0, not every)
        self.ed_table.setColumnHidden(1, not every)

    def _step_renamed(self, item: QListWidgetItem) -> None:
        """A step renamed in the list: the name of each of its rows."""
        number = item.data(Qt.ItemDataRole.UserRole)
        if number == self.ALL_STEPS:
            return
        name = item.text().strip()
        rows = [Row(**{**r.__dict__, "step_name": name}) if r.step == number else r for r in self._editor_rows()]
        self._set_editor_rows(rows, step=number)

    def add_step(self) -> int:
        """A new step at the end, with an empty row like the last one."""
        rows = self._editor_rows()
        number = max((r.step for r in rows), default=0) + 1
        last = rows[-1] if rows else Row(1, "", "AN", "FILTER")
        rows.append(Row(number, tr("Step {n}").format(n=number), last.part, last.group, "", "", VALUE))
        self._set_editor_rows(rows, step=number, select=len(rows) - 1)
        return number

    def duplicate_step(self) -> Optional[int]:
        """A copy of the chosen step, right after it (the following steps move down by one)."""
        step = self.current_step()
        if step in (None, self.ALL_STEPS):
            return None
        rows = [Row(**{**r.__dict__, "step": r.step + 1}) if r.step > step else r for r in self._editor_rows()]
        copies = [Row(**{**r.__dict__, "step": step + 1, "step_name": tr("{name} (copy)").format(name=r.step_name)
                         if r.step_name else r.step_name}) for r in rows if r.step == step]
        self._set_editor_rows(rows + copies, step=step + 1)
        return step + 1

    def move_step(self, delta: int) -> None:
        """The chosen step one place up (-1) or down (+1): it swaps with its neighbour."""
        step = self.current_step()
        numbers = sorted({r.step for r in self._editor_rows()})
        if step not in numbers:
            return
        i = numbers.index(step) + delta
        if not 0 <= i < len(numbers):
            return
        other = numbers[i]
        swap = {step: other, other: step}
        rows = [Row(**{**r.__dict__, "step": swap.get(r.step, r.step)}) for r in self._editor_rows()]
        self._set_editor_rows(rows, step=other)

    def delete_step(self) -> None:
        step = self.current_step()
        if step in (None, self.ALL_STEPS):
            return
        rows = self._editor_rows()
        count = sum(1 for r in rows if r.step == step)
        if count and QMessageBox.question(
                self, tr("Delete step"), tr("Delete the step and its {n} rows?").format(n=count)) \
                != QMessageBox.StandardButton.Yes:
            return
        kept = [r for r in rows if r.step != step]
        self._set_editor_rows(kept, step=max([r.step for r in kept if r.step < step], default=self.ALL_STEPS))

    # ------------------------------------------------------------ editor: rows
    def _chosen_rows(self) -> list[int]:
        rows = sorted({i.row() for i in self.ed_table.selectionModel().selectedRows()})
        if not rows and self.ed_table.currentRow() >= 0:
            rows = [self.ed_table.currentRow()]
        return [r for r in rows if not self.ed_table.isRowHidden(r)]

    def duplicate_editor_rows(self) -> None:
        chosen = self._chosen_rows()
        if not chosen:
            return
        rows = self._editor_rows()
        out = []
        for i, row in enumerate(rows):
            out.append(row)
            if i == chosen[-1]:
                out += [Row(**rows[j].__dict__) for j in chosen]
        self._set_editor_rows(out, step=self.current_step(), select=chosen[-1] + 1)

    def move_editor_rows(self, delta: int) -> None:
        """The chosen row one place up or down among the rows shown (within its step)."""
        chosen = self._chosen_rows()
        if len(chosen) != 1:
            return
        i = chosen[0]
        shown = [r for r in range(self.ed_table.rowCount()) if not self.ed_table.isRowHidden(r)]
        k = shown.index(i) + delta
        if not 0 <= k < len(shown):
            return
        j = shown[k]
        rows = self._editor_rows()
        if rows[i].step != rows[j].step:
            return  # across steps: change the row's Step instead
        rows[i], rows[j] = rows[j], rows[i]
        self._set_editor_rows(rows, step=self.current_step(), select=j)

    def copy_editor_rows(self) -> None:
        """The chosen rows to the clipboard, as the template's columns separated by tabs."""
        rows = self._editor_rows()
        chosen = self._chosen_rows() or range(len(rows))
        lines = ["\t".join(COLUMNS)] + ["\t".join(rows[i].cells()) for i in chosen]
        QApplication.clipboard().setText("\n".join(lines) + "\n")
        self.ed_status.setText(tr("{n} rows copied").format(n=len(lines) - 1))

    def paste_editor_rows(self) -> None:
        """Rows from the clipboard (copied here, from a sheet or an AI's answer) into the chosen step."""
        recipe = reader.read_text(QApplication.clipboard().text())
        if not recipe.rows:
            self.ed_status.setText(tr("No rows in the clipboard"))
            return
        step = self.current_step()
        rows = self._editor_rows()
        if step not in (None, self.ALL_STEPS):
            name = next((r.step_name for r in rows if r.step == step), "")
            pasted = [Row(**{**r.__dict__, "step": step, "step_name": name}) for r in recipe.rows]
        else:
            pasted = recipe.rows
        self._set_editor_rows(rows + pasted, step=step, select=len(rows))
        self.ed_status.setText(tr("{n} rows pasted").format(n=len(pasted)))

    def _explain_editor_row(self, index: int) -> None:
        """The chosen row's parameter in the panel on the right: what it is, its range, the note."""
        rows = self._editor_rows()
        if not 0 <= index < len(rows):
            return
        row = rows[index]
        c = check.check_row(row)
        if c.target is None:
            return
        self._explain_row(c)

    def revert_editor(self) -> None:
        """Back to the recipe as saved (or as imported), after asking."""
        if not self.editor_has_changes():
            return
        if QMessageBox.question(self, tr("Undo changes"), tr("Undo the changes not saved?")) \
                != QMessageBox.StandardButton.Yes:
            return
        if self.recipe_path is not None:
            self.recipe = library.load(self.recipe_path)
        else:
            import copy

            self.recipe = copy.deepcopy(self._snapshot_recipe)
        self.show_editor_page()

    def save_as_from_editor(self, title: Optional[str] = None) -> Optional[Path]:
        """Save as a new recipe (named by the user); the one opened stays as it was."""
        if title is None:
            from PySide6.QtWidgets import QInputDialog

            title, ok = QInputDialog.getText(self, tr("Save as…"), tr("Name of the new recipe:"),
                                             text=tr("{title} (copy)").format(title=self.ed_title.text().strip()))
            if not ok:
                return None
        title = title.strip()
        if not title:
            return None
        self.ed_title.setText(title)
        recipe = self._editor_to_recipe()
        recipe.created = ""
        self.recipe_path = library.save(recipe, None)
        self.refresh_library(self.recipe_path)
        self._editor_snapshot = self._editor_state()
        self._editor_changed()
        self.ed_status.setText(tr("Saved as «{title}»").format(title=title))
        return self.recipe_path

    def add_editor_row(self) -> None:
        """An empty row like the last of the chosen step (of the recipe with «All steps»), after it."""
        rows = self._editor_rows()
        step = self.current_step()
        in_step = [i for i, r in enumerate(rows) if r.step == step] if step not in (None, self.ALL_STEPS) else []
        at = (in_step[-1] if in_step else len(rows) - 1)
        last = rows[at] if rows else Row(1, "", "AN", "FILTER")
        new = Row(last.step, last.step_name, last.part, last.group, last.su, "", VALUE, "", "", "", "")
        rows.insert(at + 1, new)
        self._set_editor_rows(rows, step=step, select=at + 1)

    def remove_editor_row(self) -> None:
        chosen = self._chosen_rows()
        if not chosen:
            return
        rows = [r for i, r in enumerate(self._editor_rows()) if i not in chosen]
        self._set_editor_rows(rows, step=self.current_step(), select=min(chosen[0], len(rows) - 1))

    def capture_current(self) -> None:
        """Each row's value as the JD-Xi has it now (to write a recipe from a sound).

        The editors of the rows' parts read the JD-Xi first, so the values are
        the instrument's and not what an editor showed before.
        """
        rows = self._editor_rows()
        targets = []
        for row in rows:
            c = check.check_row(Row(**{**row.__dict__, "kind": VALUE, "value": "0"}))
            if c.target is not None:
                targets.append(c.target)
        if not targets:
            # An empty editor: a whole part as it is on the JD-Xi (it used to
            # fill only the rows there were, and with none it did nothing)
            part = self.ask_capture_part()
            if not part:
                self.ed_status.setText(tr(
                    "No row to fill: add rows with Part, Group and Parameter, or choose a part to take whole."))
                return
            self.add_part_rows(part)
            self.capture_current()
            return
        requested = set()
        for target in targets:
            key = getattr(target, "editor_key", None)
            if key in requested:
                continue
            requested.add(key)
            editor = self.editors(key) if key else None
            request = getattr(editor, "data_request", None)
            if callable(request):
                try:
                    request()
                except Exception as ex:  # reading again is a nicety: the values shown are used
                    log.warning(f"Recipes: reading {key} failed: {ex}", scope="RecipesEditor")
        self.ed_status.setText(tr("Reading the JD-Xi…"))
        QTimer.singleShot(CAPTURE_DELAY_MS, self, self._capture_now)

    CAPTURE_PARTS = ("AN", "D1", "D2", "DR", "PROG", "EFFETTI", "ARP")

    def ask_capture_part(self) -> str:
        """Which part to take whole from the JD-Xi ("" if none)."""
        from PySide6.QtWidgets import QInputDialog

        names = {code: name for code, name in catalog.vocabulary.PARTS}
        items = [f"{code} · {names.get(code, code)}" for code in self.CAPTURE_PARTS]
        item, ok = QInputDialog.getItem(
            self, tr("Take the values from the JD-Xi"),
            tr("The editor is empty: which part do you want to take whole, every parameter with its value?"),
            items, 0, False,
        )
        return item.split(" · ")[0] if ok and item else ""

    def add_part_rows(self, part: str) -> int:
        """A row for every parameter of *part* (partial 1, drum BD1 where one must be chosen)."""
        su_default = {"D1": "1", "D2": "1", "DR": "BD1"}.get(part, "")
        targets = [t for (p, _g, _l), t in catalog.targets().items() if p == part]
        table = self.ed_table
        table.blockSignals(True)
        step = 1
        for group in dict.fromkeys(t.group for t in targets):
            for t in (t for t in targets if t.group == group):
                su = su_default if t.su in ("sì", "si", "yes") else ""
                self._add_editor_row(Row(step, group, part, group, su, t.label, VALUE, "", "", "", ""))
            step += 1
        table.blockSignals(False)
        self._editor_changed()
        return len(targets)

    def _capture_now(self) -> None:
        rows = self._editor_rows()
        filled = 0
        table = self.ed_table
        table.blockSignals(True)
        for i, row in enumerate(rows):
            c = check.check_row(Row(**{**row.__dict__, "kind": VALUE, "value": "0"}))
            if c.target is None:
                continue
            text = recipe_apply.current_text(c, self.editors)
            if text and text != "—":
                filled += 1
                table.setItem(i, 7, QTableWidgetItem(text.split(" / ")[0]))
                kind = table.cellWidget(i, 6)
                if isinstance(kind, QComboBox):
                    kind.setCurrentText(VALUE)
        table.blockSignals(False)
        self._editor_changed()
        self.ed_status.setText(tr("Values taken from the JD-Xi: {n}").format(n=filled))

    def save_from_editor(self) -> None:
        if not self.ed_title.text().strip():  # the name is needed now, to find it in the library
            self.ed_status.setText(tr("A name is needed to save the recipe."))
            self.ed_title.setFocus()
            return
        recipe = self._editor_to_recipe()
        self.recipe_path = library.save(recipe, self.recipe_path)
        self.refresh_library(self.recipe_path)
        self._editor_snapshot = self._editor_state()
        self.ed_status.setText(tr("Saved in the library: {path}").format(path=self.recipe_path.name))

    def export_recipe(self, path: Optional[str] = None, recipe: Optional[Recipe] = None) -> Optional[Path]:
        if recipe is None:
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
        self._library_selection_changed()

    def _show_where(self) -> None:
        """The breadcrumb: › the recipe's title › New / Check / Guide / Editor."""
        page = self.pages.currentWidget()
        names = {
            self.create_page: tr("New recipe"),
            self.check_page: tr("Check before importing"),
            self.guide_page: tr("Guide"),
            self.editor_page: tr("Editor"),
        }
        if page is self.home or page not in names:
            self.back_button.hide()
            self.where.setText("")
            return
        title = (self.recipe.title if self.recipe is not None and page is not self.create_page else "") or ""
        self.back_button.show()
        dirty = page is self.editor_page and hasattr(self, "_editor_snapshot") and self.editor_has_changes()
        self.where.setText((f"›  {title}  " if title else "") + f"›  {names[page]}"
                           + ("   ●  " + tr("not saved") if dirty else ""))

    def _may_leave(self) -> bool:
        """Leaving the editor with changes not saved: Save, Discard or stay (Cancel)."""
        if self.pages.currentWidget() is not self.editor_page or not self.editor_has_changes():
            return True
        answer = QMessageBox.question(
            self,
            tr("Recipe not saved"),
            tr("The changes to this recipe are not saved. Leave the editor anyway?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            self.save_from_editor()
        self._editor_snapshot = self._editor_state()  # left: not asked again
        return True

    def go_back(self) -> None:
        """‹ All recipes (or Esc): the library, after asking if the editor has unsaved rows."""
        if self.pages.currentWidget() is self.home or not self._may_leave():
            return
        self.show_home()
