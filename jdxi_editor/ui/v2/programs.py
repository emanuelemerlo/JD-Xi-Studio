"""
Programs in the new look: one page with the library, the parts of the
program, the mixer and, below, presets, user programs, playlists and system
settings (same editor and engine: the original widgets, laid out anew).

    [ display | load · rename · program settings ]
    LIBRARY (search, genre, banks A–H, table)  | PARTS OF THE PROGRAM
                                               | MIXER
    PRESETS | USER PROGRAMS | PLAYLIST | PLAYLIST EDITOR | SYSTEM
"""

from __future__ import annotations

from typing import Optional

from dataclasses import replace as _replace

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.i18n import tr
from jdxi_editor.ui.editors.program import editor as _program
from jdxi_editor.ui.v2.restyle import restyle, title_badge
from jdxi_editor.ui.v2 import density

ACCENT = "#6fcf97"  # green, as the Program editor
TONES_ROLE = Qt.ItemDataRole.UserRole + 1  # [(tone name, part colour), ...]
BANKS = "ABCDEFGH"
USER_BANKS = "EFGH"
PARTS = (
    (JDXiSynth.DIGITAL_SYNTH_1, "Digital 1", "digital1", "digital_1", 1),
    (JDXiSynth.DIGITAL_SYNTH_2, "Digital 2", "digital2", "digital_2", 2),
    (JDXiSynth.DRUM_KIT, "Drums", "drums", "drums", 10),
    (JDXiSynth.ANALOG_SYNTH, "Analog", "analog", "analog", 3),
)


def _value_named(editor, name: str):
    """The ParamValue called *name* in *editor* (None: no editor yet, or no such value)."""
    values = getattr(editor, "values", None)
    if not values:
        return None
    for spec, pv in values.items():
        if getattr(spec, "name", None) == name:
            return pv
    return None


def small(knob) -> None:
    """A mixer knob: two side by side in a strip as wide as its tone's name."""
    knob.SIZE = 34
    knob.dial.setFixedSize(34, 34)
    knob.field.setFixedWidth(44)
    knob.setMinimumWidth(48)


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #8b8e96; font-size: 11px;")
    return label


def _card(title: str, note: str = "") -> tuple[QGroupBox, QVBoxLayout]:
    box = QGroupBox(title.upper())
    layout = QVBoxLayout(box)
    layout.setSpacing(8)
    if note:
        layout.addWidget(_note(note))
    return box, layout


def _strip_titles(widget: QWidget) -> None:
    """Inner group boxes without their own frame and title (the card has them)."""
    for group in widget.findChildren(QGroupBox):
        group.setTitle("")
        group.setFlat(True)
        group.setStyleSheet("QGroupBox { background: transparent; border: 0; margin: 0; padding: 0; }")
    if isinstance(widget, QGroupBox):
        widget.setTitle("")
        widget.setFlat(True)
        widget.setStyleSheet("QGroupBox { background: transparent; border: 0; margin: 0; padding: 0; }")


def _part_colours() -> tuple:
    from jdxi_editor.ui.v2.brand import PART_COLOURS

    return PART_COLOURS  # Digital 1, Digital 2, Drums, Analog: the tabs' colours


class TonesDelegate(QStyledItemDelegate):
    """The four tones of a program, each in its part's colour."""

    def paint(self, painter, option, index):
        tones = index.data(TONES_ROLE)
        if not tones:
            return super().paint(painter, option, index)
        self.initStyleOption(option, index)
        option.text = ""
        style = option.widget.style() if option.widget else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget)
        painter.save()
        metrics = option.fontMetrics
        rect = option.rect.adjusted(6, 0, -4, 0)
        x = rect.left()
        separator = " · "
        for i, (name, colour) in enumerate(tones):
            text = name + (separator if i < len(tones) - 1 else "")
            width = metrics.horizontalAdvance(text)
            if x + width > rect.right():
                text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.right() - x)
                width = rect.right() - x
            # on the selection's background the part colours do not read: light text
            painter.setPen(QColor("#f4f4f4") if option.state & QStyle.StateFlag.State_Selected else QColor(colour))
            painter.drawText(QRect(x, rect.top(), width, rect.height()),
                             int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)
            x += width
            if x >= rect.right():
                break
        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        tones = index.data(TONES_ROLE)
        if tones:
            font = QFont(option.font)
            if index.data(Qt.ItemDataRole.FontRole) is not None:
                font = QFont(index.data(Qt.ItemDataRole.FontRole))
            from PySide6.QtGui import QFontMetrics

            width = QFontMetrics(font).horizontalAdvance(" · ".join(n for n, _c in tones)) + 16
            hint.setWidth(max(hint.width(), width))
        return hint


class ProgramLibrary(QWidget):
    """Every program (A–D preset, E–H user) as a table: search, genre, bank; a double click loads it."""

    load_requested = Signal(str)  # program id, e.g. "E01"
    rename_requested = Signal(str)  # the loaded program's id
    export_requested = Signal(str)  # the loaded program's id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.programs: list = []
        self.connection = None  # set by the editor: Load needs the JD-Xi
        self.loaded_id = ""  # the program on the JD-Xi (not just selected)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search number, name, genre or tone…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        self.genre = QComboBox()
        self.genre.addItem(tr("All genres"), "")
        self.genre.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search, 3)
        filters.addWidget(self.genre, 1)
        layout.addLayout(filters)

        banks = QHBoxLayout()
        banks.setSpacing(4)
        self.bank_group = QButtonGroup(self)
        self.bank_group.setExclusive(True)
        self.bank_buttons: dict[str, QPushButton] = {}
        for bank in ("",) + tuple(BANKS):
            button = QPushButton(bank or tr("All"))
            button.setCheckable(True)
            button.setFixedWidth(34 if bank else 52)
            button.setToolTip(tr("User bank (yours, E–H)") if bank in USER_BANKS and bank
                              else (tr("Preset bank (factory, A–D)") if bank else tr("Every bank")))
            self.bank_group.addButton(button)
            self.bank_buttons[bank] = button
            banks.addWidget(button)
        self.bank_buttons[""].setChecked(True)
        self.bank_group.buttonClicked.connect(lambda _b: self.refresh())
        banks.addSpacing(8)
        banks.addWidget(_note(tr("A–D preset · E–H user")))
        banks.addStretch()
        layout.addLayout(banks)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr("No."), tr("Name"), tr("Genre"), tr("Tones (D1 · D2 · DR · AN)")])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setItemDelegateForColumn(3, TonesDelegate(self.table))
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        header = self.table.horizontalHeader()
        # every column can be resized by hand; the tones as wide as the longest
        # list, with a scroll bar when they do not fit
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._widths_set = False
        self.table.setMinimumHeight(density.px(320, 200))
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.cellDoubleClicked.connect(lambda row, _c: self._load_row(row))
        layout.addWidget(self.table, 1)

        self.count_label = _note("")
        layout.addWidget(self.count_label)

    # --- data

    def set_programs(self, programs: list) -> None:
        self.programs = list(programs)
        current = self.genre.currentData()
        genres = sorted({p.genre for p in self.programs if getattr(p, "genre", None)})
        self.genre.blockSignals(True)
        self.genre.clear()
        self.genre.addItem(tr("All genres"), "")
        for genre in genres:
            self.genre.addItem(genre, genre)
        index = self.genre.findData(current)
        self.genre.setCurrentIndex(max(0, index))
        self.genre.blockSignals(False)
        self.refresh()

    def bank(self) -> str:
        for bank, button in self.bank_buttons.items():
            if button.isChecked():
                return bank
        return ""

    def set_bank(self, bank: str) -> None:
        self.bank_buttons[bank].setChecked(True)
        self.refresh()

    def visible_ids(self) -> list[str]:
        return [self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) for r in range(self.table.rowCount())]

    @staticmethod
    def matches(program, text: str) -> bool:
        """*text* (lower case) in the number, name, genre or one of the four tones."""
        fields = (program.id, program.name, program.genre,
                  program.digital_1, program.digital_2, program.drums, program.analog)
        return any(text in (f or "").lower() for f in fields)

    def _with_unknown_slots(self, bank: str = "") -> list:
        """The programs and, for a user bank (E–H) chosen, its slots not known
        yet: the database has only the user programs read from the JD-Xi, so
        a bank never loaded (G, H) looked empty, as if it had no slots."""
        from types import SimpleNamespace

        if not bank or bank not in USER_BANKS:
            return list(self.programs)
        known = {p.id.upper() for p in self.programs if p.id}
        missing = [
            SimpleNamespace(id=f"{bank}{n:02d}", name="", genre="", digital_1=None, digital_2=None,
                            drums=None, analog=None, unknown_slot=True)
            for n in range(1, 65) if f"{bank}{n:02d}" not in known
        ]
        return list(self.programs) + missing

    def refresh(self) -> None:
        text = self.search.text().strip().lower()
        genre = self.genre.currentData() or ""
        bank = self.bank()
        selected = self.selected_id()
        rows = [
            p
            for p in self._with_unknown_slots(bank)
            if p.id
            and (not bank or p.id[0].upper() == bank)
            and (not genre or (p.genre or "") == genre)
            and (not text or self.matches(p, text))
        ]
        colours = _part_colours()
        sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)  # filled unsorted, sorted once at the end
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            parts = [(t, c) for t, c in zip((p.digital_1, p.digital_2, p.drums, p.analog), colours) if t]
            tones = " · ".join(t for t, _c in parts)
            user = p.id[0].upper() in USER_BANKS
            unknown = getattr(p, "unknown_slot", False)
            genre_text = (p.genre or "") + (f" · {tr('user')}" if user else "")
            name = tr("(not read yet)") if unknown else (p.name or "")
            for c, value in enumerate((p.id, name, genre_text.strip(" ·"), tones)):
                item = QTableWidgetItem(value)
                if unknown and c == 1:
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setToolTip(tr("JD-Xi Studio has not read this slot yet: load it to see its "
                                       "program (its name is kept from then on)"))
                item.setData(Qt.ItemDataRole.UserRole, p.id)
                if c == 3:
                    item.setData(TONES_ROLE, parts)
                    item.setToolTip("\n".join(
                        f"{tr(label)}: {name}" for (_s, label, _k, field, _ch) in PARTS
                        if (name := getattr(p, field, None))))
                if c == 0:
                    item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(sorting)
        self._mark_loaded()
        self._fit_columns(rows)
        unknown = sum(1 for p in rows if getattr(p, "unknown_slot", False))
        text = tr("{shown} of {total} programs").format(shown=len(rows) - unknown, total=len(self.programs))
        if unknown:
            text += " · " + tr("{n} slots not read yet").format(n=unknown)
        self.count_label.setText(text)
        if selected:
            self.select(selected)

    def _fit_columns(self, rows=None) -> None:
        """Once shown (with the page's font): number, name and genre to their text,
        the name at most 220 px; then they are the user's to resize."""
        if self._widths_set or not self.table.isVisible() or self.table.rowCount() == 0:
            return
        for column, cap in ((0, 90), (1, 220), (2, 170)):
            self.table.resizeColumnToContents(column)
            self.table.setColumnWidth(column, min(cap, self.table.columnWidth(column) + 12))
        self._widths_set = True

    def showEvent(self, event) -> None:
        super().showEvent(event)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._fit_columns)

    def set_loaded(self, program_id: str) -> None:
        """*program_id* is now on the JD-Xi: marked in the list (bold, ▶)."""
        self.loaded_id = (program_id or "").upper()
        self._mark_loaded()

    def _mark_loaded(self) -> None:
        for r in range(self.table.rowCount()):
            first = self.table.item(r, 0)
            if first is None:
                continue
            program_id = first.data(Qt.ItemDataRole.UserRole) or ""
            loaded = bool(program_id) and program_id == self.loaded_id
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item is None:
                    continue
                font = QFont(item.font())
                font.setBold(loaded)
                item.setFont(font)
            first.setText(f"▶ {program_id}" if loaded else program_id)
            first.setForeground(QColor(ACCENT) if loaded else QColor("gray"))
            first.setToolTip(tr("Loaded on the JD-Xi") if loaded else "")

    def selected_id(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return (item.data(Qt.ItemDataRole.UserRole) or "") if item else ""

    def program(self, program_id: str):
        return next((p for p in self.programs if p.id == program_id), None)

    def select(self, program_id: str) -> bool:
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).data(Qt.ItemDataRole.UserRole) == program_id:
                self.table.selectRow(r)
                self.table.scrollToItem(self.table.item(r, 0))
                return True
        return False

    def _load_row(self, row: int) -> None:
        item = self.table.item(row, 0)
        if item:
            self.load_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    # --- context menu: what can be done with one program

    def _context_menu(self, pos) -> None:
        item = self.table.itemAt(pos)
        if item is None:
            return
        program_id = item.data(Qt.ItemDataRole.UserRole) or ""
        self.select(program_id)
        menu = self.build_menu(program_id)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def build_menu(self, program_id: str) -> QMenu:
        """The actions for *program_id*; those it cannot have are off, with the reason."""
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        loaded = program_id == self.loaded_id
        user = program_id[:1].upper() in USER_BANKS
        load = menu.addAction(tr("Load {program}").format(program=program_id))
        connection = getattr(self, "connection", None)
        if connection is not None and not connection.can_talk():
            load.setEnabled(False)
            load.setToolTip(tr("Connect the JD-Xi to load a program"))
        load.triggered.connect(lambda: self.load_requested.emit(program_id))
        rename = menu.addAction(tr("Rename…"))
        rename.setEnabled(loaded)
        rename.setToolTip(tr("Rename the loaded program (kept on the JD-Xi with WRITE)") if loaded
                          else tr("Load the program first: only the loaded program can be renamed"))
        rename.triggered.connect(lambda: self.rename_requested.emit(program_id))
        genre = menu.addAction(tr("Genre…"))
        genre.setEnabled(user)
        genre.setToolTip(tr("Your label for this program, kept by JD-Xi Studio") if user
                         else tr("Preset programs keep their genre"))
        genre.triggered.connect(lambda: self.edit_genre(program_id))
        playlists = menu.addMenu(tr("Add to playlist"))
        self._fill_playlists(playlists, program_id)
        export = menu.addAction(tr("Export…"))
        export.setEnabled(loaded)
        export.setToolTip(tr("Save the loaded program as a file") if loaded
                          else tr("Load the program first: what is exported is what the JD-Xi holds"))
        export.triggered.connect(lambda: self.export_requested.emit(program_id))
        return menu

    def _fill_playlists(self, menu: QMenu, program_id: str) -> None:
        try:
            from jdxi_editor.ui.programs.database import get_database

            playlists = get_database().get_all_playlists()
        except Exception:
            playlists = []
        if not playlists:
            none = menu.addAction(tr("No playlists: create one in Organize"))
            none.setEnabled(False)
            return
        for playlist in playlists:
            action = menu.addAction(playlist.get("name") or str(playlist["id"]))
            action.triggered.connect(
                lambda _c=False, pid=playlist["id"]: self.add_to_playlist(pid, program_id))

    playlists_changed = Signal()

    def add_to_playlist(self, playlist_id: int, program_id: str) -> bool:
        from jdxi_editor.ui.programs.database import get_database

        ok = bool(get_database().add_program_to_playlist(playlist_id, program_id))
        if ok:
            self.playlists_changed.emit()
        return ok

    def edit_genre(self, program_id: str, genre: Optional[str] = None) -> bool:
        """Set a user program's genre (asked when not given); kept in JD-Xi Studio's library."""
        program = self.program(program_id)
        if program is None or program_id[:1].upper() not in USER_BANKS:
            return False
        if genre is None:
            genre, ok = QInputDialog.getText(
                self, tr("Genre of {program}").format(program=program_id), tr("Genre:"),
                text=program.genre or "")
            if not ok:
                return False
        from jdxi_editor.midi.io.input_handler import add_or_replace_program_and_save

        updated = _replace(program, genre=genre.strip() or None)
        if not add_or_replace_program_and_save(updated):
            return False
        self.programs = [updated if p.id == program_id else p for p in self.programs]
        self.set_programs(self.programs)
        return True


class ProgramEditor(_program.ProgramEditor):
    """The Program editor with everything on one page (same class name: found by name)."""

    def setup_ui(self) -> None:
        super().setup_ui()  # the original widgets (and engine), laid out below
        group = self.program_group_widget

        # --- the header: display, actions
        self.lcd = group.file_label
        self.lcd.setText(tr("No program loaded"))  # it shows the program, not a file
        self.lcd.setFixedWidth(360)
        self.load_button = QPushButton(tr("Load program"))
        self.load_button.setToolTip(tr("Load the program selected in the library (or double-click it)"))
        self.load_button.clicked.connect(self.load_selected_program)
        self.rename_button = QPushButton(tr("Rename…"))
        self.rename_button.setToolTip(tr("Edit the name of the current program"))
        self.rename_button.clicked.connect(group.edit_program_name)
        self.advanced_button = QPushButton(tr("Program settings"))
        self.advanced_button.setToolTip(
            tr("Every part's level, pan, effects, pitch, offsets, zones, scale and MIDI (the Program settings tab)")
        )
        self.advanced_button.clicked.connect(self.open_advanced)
        actions = QVBoxLayout()
        actions.setSpacing(6)
        self.write_button = QPushButton(tr("Save on the JD-Xi…"))
        self.write_button.setToolTip(tr("Keep the program in the JD-Xi (WRITE in E–H), guided and checked"))
        self.write_button.clicked.connect(self.save_on_jdxi)
        first = QHBoxLayout()
        first.addWidget(self.write_button)
        first.addWidget(self.rename_button)
        first.addStretch()
        # Undo / Redo of the whole program: the last change in any tab (the mixer's
        # Pan, sends and faders are values of Program settings and of the parts)
        self.edit_buttons = self._program_undo_buttons()
        for button in self.edit_buttons:
            first.addWidget(button)
        actions.addLayout(first)
        second = QHBoxLayout()
        second.addWidget(self.advanced_button)
        second.addStretch()
        actions.addLayout(second)
        actions.addWidget(group.program_midi_info_bar)
        header = QHBoxLayout()
        header.setSpacing(16)
        header.addWidget(self.lcd, 0, Qt.AlignmentFlag.AlignTop)
        header.addLayout(actions, 1)

        # --- library
        self.library = ProgramLibrary()
        self.library.load_requested.connect(self.load_program_by_id)
        self.library.rename_requested.connect(lambda _id: group.edit_program_name())
        self.library.export_requested.connect(lambda _id: self.export_program())
        self.library.table.itemSelectionChanged.connect(self._library_selection_changed)
        library_card, library_layout = _card(tr("Library"))
        library_layout.addWidget(self.library, 1)
        # Load under the list it loads from (it was in the header, far from it)
        load_row = QHBoxLayout()
        load_row.addStretch()
        self.load_button.setMinimumWidth(220)
        self.load_button.setEnabled(False)
        load_row.addWidget(self.load_button)
        library_layout.addLayout(load_row)
        library_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # --- parts and mixer: each part's strip says its tone and channel and
        # opens its editor (no second list of the same four parts)
        mixer_card, mixer_layout = _card(tr("Parts and mixer"))
        _strip_titles(self.mixer_panel)
        for label in self.mixer_widget.label_widgets._labels.values():
            label.hide()
        mixer_layout.addWidget(self.mixer_panel)
        mixer_layout.addWidget(_note(tr("Click a tone to choose another for that part; Edit opens the part's editor.")))
        self.part_tones: dict[str, QPushButton] = {}
        self._add_part_controls()
        self._dress_strips()
        # Pan, Delay, Reverb above each fader: the values of Program settings
        # (made when the instrument is there, once its editors are)
        self.part_sends: dict = {}
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._add_part_sends)

        right = QVBoxLayout()
        right.setSpacing(0)
        # its top level with the library card's (on a low screen the library sits in a
        # tab, under the tab bar): set from the cards' places, see _align_mixer
        self._mixer_top = QWidget()
        self._mixer_top.setFixedHeight(0)
        right.addWidget(self._mixer_top)
        right.addWidget(mixer_card)
        right.addStretch()
        self._library_card, self._mixer_card = library_card, mixer_card

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(library_card, 3)
        top.addLayout(right, 2)

        # --- below: organize (the playlists and, under them, the selected one's programs).
        # The tone presets are chosen from each part's strip; the user programs
        # are the E–H banks of the library (their genre from its menu).
        self.more_tabs = QTabWidget()
        self.more_tabs.setDocumentMode(True)
        organize = QWidget()
        row = QVBoxLayout(organize)  # the playlists above, the chosen one's programs below
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        for widget, stretch in ((self.playlist_widget, 2), (self.playlist_editor_widget, 5)):
            if widget is not None:
                _strip_titles(widget)
                row.addWidget(widget, stretch)
                widget.show()  # it comes from a hidden tab of the old editor: hidden with it
        self.more_tabs.addTab(organize, tr("Organize: playlists"))
        self._link_playlists()
        self.library.playlists_changed.connect(self._playlists_changed)
        for widget in (group.preset, self.user_programs_widget):
            if widget is not None:
                widget.hide()
        tallest = organize.sizeHint().height()
        if density.compact():
            # a low screen: the library is the first of these tabs, beside the parts and the
            # mixer, instead of the tabs under it
            top.replaceWidget(library_card, self.more_tabs)
            self.more_tabs.insertTab(0, library_card, tr("Library"))
            self.more_tabs.setCurrentIndex(0)
        else:
            self.more_tabs.setFixedHeight(max(360, tallest + self.more_tabs.tabBar().sizeHint().height() + 12))
        # the decorative icon rows of the old pages say nothing: hidden
        for label in self.more_tabs.findChildren(QLabel, "decorIcon"):
            label.hide()

        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(12, 12, 12, 12)
        page.setSpacing(12)
        badge = QHBoxLayout()
        badge.addWidget(title_badge(tr("Programs"), ACCENT))
        badge.addStretch()
        page.addLayout(badge)
        page.addLayout(header)
        from jdxi_editor.ui.v2.context import ContextRow

        self.context_row = ContextRow(None, self.midi_helper)
        page.addWidget(self.context_row)
        page.addLayout(top, 1)
        if not density.compact():
            page.addWidget(self.more_tabs)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)

        # The original tabs are emptied into the page; they stay (hidden) for references
        self.main_tab_widget.hide()
        group.hide()
        root = QWidget.layout(self)  # (self.layout is an attribute of the original editor)
        root.addWidget(scroll)
        root.setContentsMargins(0, 0, 0, 0)

        self.library.set_programs(getattr(group, "_program_list_data", []))
        restyle(self, ACCENT)
        self._follow_connection()

    # --- the library

    def _update_program_combo_box(self) -> None:
        super()._update_program_combo_box()
        library = getattr(self, "library", None)
        if library is not None and self.program_group_widget is not None:
            library.set_programs(self.program_group_widget._program_list_data)

    def _follow_connection(self) -> None:
        """Loading a program and choosing a tone need the JD-Xi."""
        from jdxi_editor.midi.io.connection import connection_for
        from jdxi_editor.ui.v2.offline import require_jdxi

        self.connection = connection_for(self.midi_helper)
        self.library.connection = self.connection
        if self.connection is None:
            return
        self.connection.changed.connect(lambda _s: self._library_selection_changed())
        for button in self.part_tones.values():
            require_jdxi(button, self.connection, tr("Connect the JD-Xi to choose a tone"))
        require_jdxi(self.write_button, self.connection, tr("Connect the JD-Xi to save on it"))
        self._library_selection_changed()

    def _can_talk(self) -> bool:
        connection = getattr(self, "connection", None)
        return connection is None or connection.can_talk()

    def _library_selection_changed(self) -> None:
        program_id = self.library.selected_id()
        online = self._can_talk()
        self.load_button.setEnabled(bool(program_id) and online)
        self.load_button.setToolTip(
            tr("Load the program selected in the library (or double-click it)") if online
            else tr("Connect the JD-Xi to load a program"))
        self.load_button.setText(
            tr("Load {program}").format(program=program_id) if program_id else tr("Load program")
        )
        # the MIDI line (bank select, program change) follows the selection
        group = self.program_group_widget
        combo = getattr(getattr(group, "program_number_combo_box", None), "combo_box", None)
        if program_id and combo is not None:
            for i in range(combo.count()):
                if combo.itemText(i).startswith(f"{program_id} "):
                    combo.setCurrentIndex(i)
                    break

    def load_selected_program(self) -> None:
        program_id = self.library.selected_id()
        if program_id:
            self.load_program_by_id(program_id)

    def load_program_by_id(self, program_id: str) -> None:
        """Load a program (as the original Load Program button does) and show its parts."""
        from jdxi_editor.ui.editors.helpers.program import get_program_by_id
        from jdxi_editor.ui.midi.selection_info import send_program_with_expectation

        program_id = program_id.strip().upper()
        if not self._can_talk():
            return  # the JD-Xi is not there: nothing would be loaded
        details = next((p for p in self.library.programs if p.id == program_id), None)
        if details is None and program_id[:1] in "ABCD":
            details = get_program_by_id(program_id)
        if details is not None:
            self.update_current_synths(details)
            self.set_current_program_name(details.name)
            self.lcd.setText(f"{program_id}  {details.name or ''}".strip())
        from jdxi_editor.ui.v2.context import sound_context

        sound_context().program_loaded(program_id, details.name if details is not None else "")
        self.library.set_loaded(program_id)
        group = self.program_group_widget
        send_program_with_expectation(
            self.midi_helper,
            program_id,
            source="program_library",
            channel=group.channel if group is not None else self.channel,
        )
        self.data_request()

    def set_current_program_name(self, program_name: str, synth_type: str = None) -> None:
        super().set_current_program_name(program_name, synth_type)
        from jdxi_editor.ui.v2.context import sound_context

        context = sound_context()
        context.set_program_name(program_name)
        lcd = getattr(self, "lcd", None)
        if lcd is not None and context.program_id and program_name:
            lcd.setText(f"{context.program_id}  {program_name}")

    # --- parts

    def _dress_strips(self) -> None:
        """
        Each strip a column of its own: a light line between the parts (the knobs
        above the faders ran into one another), the same width for all, and the
        part's name at the bottom, over its tone, instead of at the top.
        """
        tracks = self.mixer_widget.tracks
        self.strip_names = []
        for index, track in enumerate(tracks):
            strip = track.slider.parentWidget()
            layout = strip.layout() if strip is not None else None
            if layout is None:
                continue
            label = getattr(track.slider, "label", None)
            text, colour = (label.text(), "#e6e8eb") if label is not None else ("", "#e6e8eb")
            if label is not None:
                colour = track.slider.property("strip_colour") or colour
                taken = label.sizeHint().height() + track.slider.layout().spacing()
                label.setVisible(False)
                track.slider.setFixedHeight(track.slider.maximumHeight() - taken)
            name = QLabel(text)
            name.setObjectName("mixerStripName")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet(f"QLabel#mixerStripName {{ color: {colour}; font-size: 13px; font-weight: 700;"
                               " background: transparent; }")
            mute = getattr(strip, "mute", None)
            at = layout.indexOf(mute) + 1 if mute is not None else layout.count()
            layout.insertWidget(at, name, 0, Qt.AlignmentFlag.AlignHCenter)
            self.strip_names.append(name)
            strip.setObjectName("mixerStrip")
            strip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            line = "border-left: 1px solid #2e3138;" if index else "border: 0;"
            strip.setStyleSheet(f"QWidget#mixerStrip {{ {line} background: transparent; }}")
        self._equal_strips()

    def _equal_strips(self) -> None:
        """Every strip as wide as the widest (its content, not a set number: 130 px each made
        the compact page too wide with Windows' fonts), so the lines between them are even."""
        strips = [t.slider.parentWidget() for t in self.mixer_widget.tracks]
        strips = [s for s in strips if s is not None]
        for strip in strips:
            strip.setMinimumWidth(0)
        width = max((s.sizeHint().width() for s in strips), default=0)
        for strip in strips:
            strip.setMinimumWidth(width)

    def _program_undo_buttons(self) -> list:
        from jdxi_editor.ui.v2.history import ProgramHistory

        self.program_history = history = ProgramHistory(self)
        holder = QWidget()  # edit_controls reads editor.history
        holder.history = history
        from jdxi_editor.ui.v2.restyle import edit_controls

        _mark, buttons = edit_controls(holder)  # the context line already says «modified»
        undo, redo = buttons

        def tips() -> None:
            what = history.undo_text()
            undo.setToolTip(tr("Undo: {what} (Ctrl+Z)").format(what=what) if what
                            else tr("Undo the last change to the program, in any tab (Ctrl+Z)"))
            what = history.redo_text()
            redo.setToolTip(tr("Redo: {what} (Ctrl+Y)").format(what=what) if what
                            else tr("Redo the last change taken back (Ctrl+Y)"))

        history.stateChanged.connect(tips)
        tips()
        return buttons

    def _add_part_controls(self) -> None:
        """Under each part's strip: its tone (click: choose another), channel and Edit."""
        colours = _part_colours()
        tracks = self.mixer_widget.tracks[1:]  # after the Master: Digital 1, Digital 2, Drums, Analog
        for row, ((synth, label, key, _field, channel), track, colour) in enumerate(zip(PARTS, tracks, colours)):
            strip = track.slider.parentWidget()
            layout = strip.layout() if strip is not None else None
            if layout is None:
                continue
            tone = QPushButton("—")
            tone.setFlat(True)
            tone.setFixedWidth(96)
            tone.setCursor(Qt.CursorShape.PointingHandCursor)
            tone.setToolTip(tr("Choose another tone for {part}").format(part=tr(label)))
            tone.setStyleSheet(f"QPushButton {{ color: {colour}; border: 0; padding: 2px; text-align: center; }}"
                               f" QPushButton:hover {{ text-decoration: underline; }}")
            tone.clicked.connect(lambda _c=False, r=row: self.choose_tone(r))
            ch = _note(tr("Ch. {n}").format(n=channel))
            ch.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit = QPushButton(tr("Edit"))
            edit.setToolTip(tr("Open the {part} editor").format(part=tr(label)))
            edit.clicked.connect(lambda _c=False, r=row: self.open_part_editor(r))
            for widget in (tone, ch, edit):
                layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignHCenter)
            self.part_tones[synth] = tone
        master = self.mixer_widget.tracks[0].slider.parentWidget()
        if master is not None and master.layout() is not None:
            master.layout().addStretch()  # the Master has no tone: its strip ends with the mute

    # the part's number in the Program settings (Digital 1, Digital 2, Analog, Drums)
    SETTINGS_PART = {
        JDXiSynth.DIGITAL_SYNTH_1: 0, JDXiSynth.DIGITAL_SYNTH_2: 1,
        JDXiSynth.ANALOG_SYNTH: 2, JDXiSynth.DRUM_KIT: 3,
    }

    def _add_part_sends(self) -> None:
        """
        Above each part's fader: Pan, Delay send and Reverb send, so the mixer is
        the program's console. They are the Program settings' own values (one
        set: what changes here changes there, with its undo, and the sends are off
        where the part's output skips that effect).
        """
        instrument = self._instrument()
        make = getattr(instrument, "program_settings_editor", None)
        if self.part_sends or not callable(make):
            return
        settings = make()
        if settings is None or not hasattr(settings, "part"):
            return
        from jdxi_editor.ui.v2.widgets import Knob

        self.program_settings = settings
        tallest = 0
        for (synth, label, *_rest), track, colour in zip(PARTS, self.mixer_widget.tracks[1:], _part_colours()):
            part = self.SETTINGS_PART[synth]
            box = QWidget()
            box.setStyleSheet("background: transparent;")
            grid = QGridLayout(box)
            grid.setContentsMargins(0, 0, 0, 6)
            grid.setHorizontalSpacing(0)
            grid.setVerticalSpacing(4)
            knobs = []
            for name, text, row, column, span in (
                ("PART_PAN", tr("Pan"), 0, 0, 2),
                ("PART_DELAY_SEND_LEVEL", tr("Delay"), 1, 0, 1),
                ("PART_REVERB_SEND_LEVEL", tr("Reverb"), 1, 1, 1),
            ):
                knob = Knob(settings.part(name, part), colour, settings.info_hub)
                knob.name.setText(text)
                small(knob)
                grid.addWidget(knob, row, column, 1, span, Qt.AlignmentFlag.AlignHCenter)
                knobs.append(knob)
            self._above_level(track, box)
            self.part_sends[synth] = knobs
            tallest = max(tallest, box.sizeHint().height())
        spacer = QWidget()  # the Master has no pan or sends: its fader level with the others
        spacer.setFixedHeight(tallest)
        self._above_level(self.mixer_widget.tracks[0], spacer)
        self._equal_strips()  # the knobs made the parts' strips wider than the Master's
        self._read_parts()  # the current program's pan and sends
        self._link_levels()

    # the faders, Master first: whose value each one is
    LEVELS = ((None, "PROGRAM_LEVEL"), ("digital1", "TONE_LEVEL"), ("digital2", "TONE_LEVEL"),
              ("drums", "KIT_LEVEL"), ("analog", "AMP_LEVEL"))

    def _link_levels(self, tries: int = 0) -> None:
        """
        Each fader is the level of its editor (Digital 1's Tone Level…; the Master:
        Program settings' Program Level): moving it changes that value, so it is
        an edit with its Undo and «modified», and the knob in the part's tab
        moves with it. (The faders sent the level on their own: nothing knew.)
        """
        instrument = self._instrument()
        if instrument is None:
            return
        links = self.__dict__.setdefault("level_links", {})
        missing = False
        for index, (key, name) in enumerate(self.LEVELS):
            if index in links or index >= len(self.mixer_widget.tracks):
                continue
            editor = getattr(self, "program_settings", None) if key is None else instrument._tab_editor(key)
            pv = _value_named(editor, name)
            if pv is None:
                missing = True  # its editor is still being made at startup
                continue
            slider = self.mixer_widget.tracks[index].slider
            inner = getattr(slider, "slider", None)
            if inner is not None and (inner.minimum(), inner.maximum()) != (pv.minimum, pv.maximum):
                from decologr import Decologr as log

                log.warning(f"mixer: {name} range differs from the fader's, not linked", scope="Programs")
                links[index] = None
                continue
            try:
                slider.valueChanged.disconnect()  # it sent the level by itself
            except (RuntimeError, TypeError):
                pass
            slider.valueChanged.connect(pv.setValue)
            pv.watch(lambda value, slider=slider: slider.value() != value and slider.setValueSilently(value),
                     now=False)
            links[index] = pv
        if missing and tries < 20:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(500, lambda: self._link_levels(tries + 1))

    def _part_requests(self) -> list:
        settings = getattr(self, "program_settings", None)
        return [b.request for b in getattr(settings, "blocks", []) if b.key.startswith("PART_") and b.request]

    def _read_parts(self) -> None:
        helper = getattr(self, "_midi_helper", None)
        requests = self._part_requests()
        if helper is None or not requests or not hasattr(helper, "send_raw_message"):
            return
        import threading

        from jdxi_editor.midi.io.delay import send_with_delay

        threading.Thread(target=send_with_delay, args=(helper, requests), daemon=True).start()

    @staticmethod
    def _above_level(track, widget: QWidget) -> None:
        """*widget* between the strip's name and its level box."""
        layout = track.slider.layout()
        box = getattr(track.slider, "level_box", None)
        index = layout.indexOf(box) if box is not None else 1
        layout.insertWidget(max(index, 0), widget, 0, Qt.AlignmentFlag.AlignHCenter)
        # the fader keeps its length: the strip (a fixed height) grows by the widget
        height = widget.minimumHeight() or widget.sizeHint().height()
        track.slider.setFixedHeight(track.slider.maximumHeight() + height + layout.spacing())

    def data_request(self, channel=None, program=None):
        """The program's values; with the mixer's Pan and sends, its parts too."""
        extra = self._part_requests()
        if not extra:
            return super().data_request(channel, program)
        requests = self.midi_requests
        self.midi_requests = list(requests) + extra
        try:
            return super().data_request(channel, program)
        finally:
            self.midi_requests = requests

    def _set_part_tone(self, synth_type, tone_name: str) -> None:
        button = getattr(self, "part_tones", {}).get(synth_type)
        if button is not None:
            name = tone_name or "—"
            button.setText(button.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, 90))
            button.setProperty("tone_name", name)

    def part_tone(self, synth_type) -> str:
        button = getattr(self, "part_tones", {}).get(synth_type)
        return (button.property("tone_name") or "") if button is not None else ""

    def choose_tone(self, row: int) -> Optional[QDialog]:
        """The tone presets of one part (the original preset chooser), in a small window."""
        preset = getattr(self.program_group_widget, "preset", None)
        if preset is None or not 0 <= row < len(PARTS):
            return None
        label = PARTS[row][1]
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Tone of {part}").format(part=tr(label)))
        layout = QVBoxLayout(dialog)
        layout.addWidget(preset)
        preset.digital_preset_type_combo.setCurrentIndex(row)  # D1, D2, Drums, Analog: same order
        preset.digital_preset_type_combo.setEnabled(False)  # this part only
        preset.show()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def put_back() -> None:
            preset.digital_preset_type_combo.setEnabled(True)
            preset.hide()
            preset.setParent(self.program_group_widget)

        dialog.finished.connect(lambda _r: put_back())
        dialog.resize(560, dialog.sizeHint().height())
        dialog.open()
        return dialog

    # --- organize

    def _link_playlists(self) -> None:
        """Choosing a playlist on the left shows its programs on the right."""
        table = getattr(self.playlist_widget, "playlist_table", None)
        if table is None or self.playlist_editor_widget is None:
            return

        def show_selected() -> None:
            row = table.currentRow()
            item = table.item(row, 0) if row >= 0 else None
            data = item.data(Qt.ItemDataRole.UserRole) if item else None
            combo = getattr(self.playlist_editor_widget, "playlist_editor_combo", None)
            if isinstance(data, dict) and combo is not None:
                combo.setValue(int(data["id"]))

        table.itemSelectionChanged.connect(show_selected)

    def _playlists_changed(self) -> None:
        for widget, method in ((self.playlist_widget, "refresh_playlists"),
                               (self.playlist_editor_widget, "populate_playlist_combo")):
            refresh = getattr(widget, method, None)
            if callable(refresh):
                refresh()

    def save_on_jdxi(self):
        """The guided WRITE (sound-design Phase 4)."""
        from jdxi_editor.ui.v2.context import sound_context
        from jdxi_editor.ui.v2.write_wizard import WriteDialog, session_for

        session = session_for(self.midi_helper, self)
        instrument = self._instrument()
        backup = getattr(instrument, "_patch_save", None)
        dialog = WriteDialog(session, sound_context().program_name or getattr(self, "program_name", "") or "",
                             self, backup=backup if callable(backup) else None)
        session.finished.connect(lambda saved, _m: saved and self.library.set_loaded(session.slot))
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()
        return dialog

    def export_program(self) -> None:
        """Save the loaded program as a file (the main window's Save, which knows the format)."""
        instrument = self._instrument()
        save = getattr(instrument, "_patch_save", None)
        if callable(save):
            save()

    def update_tone_name_for_synth(self, tone_name: str, synth_type: str) -> None:
        super().update_tone_name_for_synth(tone_name, synth_type)
        self._set_part_tone(synth_type, tone_name)

    def update_current_synths(self, program_details) -> None:
        super().update_current_synths(program_details)
        for synth, _label, _key, field, _ch in PARTS:
            self._set_part_tone(synth, getattr(program_details, field, None) or "—")

    def _instrument(self):
        return self._get_parent_instrument()

    def open_part_editor(self, row: int) -> None:
        instrument = self._instrument()
        if instrument is not None and 0 <= row < len(PARTS):
            instrument.show_editor(PARTS[row][2])

    def _align_mixer(self) -> None:
        """The mixer card's top level with the library card's."""
        library, mixer = getattr(self, "_library_card", None), getattr(self, "_mixer_card", None)
        spacer = getattr(self, "_mixer_top", None)
        if library is None or mixer is None or spacer is None or not library.isVisible():
            return
        try:
            delta = library.mapTo(self, library.rect().topLeft()).y() - mixer.mapTo(self, mixer.rect().topLeft()).y()
        except RuntimeError:
            return
        height = max(0, spacer.height() + delta)
        if height != spacer.height():
            spacer.setFixedHeight(height)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._align_mixer)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._align_mixer)

    def open_advanced(self) -> None:
        instrument = self._instrument()
        if instrument is not None:
            instrument.show_editor("program_parts")
