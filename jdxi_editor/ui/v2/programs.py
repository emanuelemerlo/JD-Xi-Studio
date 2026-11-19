"""
Programs in the new look: one page with the library, the parts of the
program, the mixer and, below, presets, user programs, playlists and system
settings (same editor and engine: the original widgets, laid out anew).

    [ display | load · rename · parts and advanced settings ]
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

    def refresh(self) -> None:
        text = self.search.text().strip().lower()
        genre = self.genre.currentData() or ""
        bank = self.bank()
        selected = self.selected_id()
        rows = [
            p
            for p in self.programs
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
            genre_text = (p.genre or "") + (f" · {tr('user')}" if user else "")
            for c, value in enumerate((p.id, p.name or "", genre_text.strip(" ·"), tones)):
                item = QTableWidgetItem(value)
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
        self.count_label.setText(
            tr("{shown} of {total} programs").format(shown=len(rows), total=len(self.programs)))
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
        self.lcd.setFixedWidth(360)
        self.load_button = QPushButton(tr("Load program"))
        self.load_button.setToolTip(tr("Load the program selected in the library (or double-click it)"))
        self.load_button.clicked.connect(self.load_selected_program)
        self.rename_button = QPushButton(tr("Rename…"))
        self.rename_button.setToolTip(tr("Edit the name of the current program"))
        self.rename_button.clicked.connect(group.edit_program_name)
        self.advanced_button = QPushButton(tr("Parts and advanced settings…"))
        self.advanced_button.setToolTip(
            tr("Every part's level, pan, offsets, scale, receive switches and zones (Program: common and parts)")
        )
        self.advanced_button.clicked.connect(self.open_advanced)
        actions = QVBoxLayout()
        actions.setSpacing(6)
        first = QHBoxLayout()
        first.addWidget(self.rename_button)
        first.addStretch()
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

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(mixer_card)
        right.addStretch()

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(library_card, 3)
        top.addLayout(right, 2)

        # --- below: organize (the playlists and, beside them, the selected one's programs).
        # The tone presets are chosen from each part's strip; the user programs
        # are the E–H banks of the library (their genre from its menu).
        self.more_tabs = QTabWidget()
        self.more_tabs.setDocumentMode(True)
        organize = QWidget()
        row = QHBoxLayout(organize)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        for widget, stretch in ((self.playlist_widget, 2), (self.playlist_editor_widget, 3)):
            if widget is not None:
                _strip_titles(widget)
                row.addWidget(widget, stretch)
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
        self.library.set_loaded(program_id)
        group = self.program_group_widget
        send_program_with_expectation(
            self.midi_helper,
            program_id,
            source="program_library",
            channel=group.channel if group is not None else self.channel,
        )
        self.data_request()

    # --- parts

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

    def open_advanced(self) -> None:
        instrument = self._instrument()
        if instrument is not None:
            instrument.show_editor("program_parts")
