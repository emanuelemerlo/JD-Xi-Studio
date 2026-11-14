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

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
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


class ProgramLibrary(QWidget):
    """Every program (A–D preset, E–H user) as a table: search, genre, bank; a double click loads it."""

    load_requested = Signal(str)  # program id, e.g. "E01"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.programs: list = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search name…"))
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
            button.setToolTip(tr("User bank") if bank in USER_BANKS and bank else (tr("Preset bank") if bank else ""))
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
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
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
        return [self.table.item(r, 0).text() for r in range(self.table.rowCount())]

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
            and (not text or text in (p.name or "").lower() or text in p.id.lower())
        ]
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            tones = " · ".join(t for t in (p.digital_1, p.digital_2, p.drums, p.analog) if t)
            user = p.id[0].upper() in USER_BANKS
            genre_text = (p.genre or "") + (f" · {tr('user')}" if user else "")
            for c, value in enumerate((p.id, p.name or "", genre_text.strip(" ·"), tones)):
                item = QTableWidgetItem(value)
                item.setToolTip(value if c == 3 else "")
                if c == 0:
                    item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(r, c, item)
        self.count_label.setText(tr("{n} programs").replace("{n}", str(len(rows))))
        if selected:
            self.select(selected)

    def selected_id(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.text() if item else ""

    def select(self, program_id: str) -> bool:
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).text() == program_id:
                self.table.selectRow(r)
                self.table.scrollToItem(self.table.item(r, 0))
                return True
        return False

    def _load_row(self, row: int) -> None:
        item = self.table.item(row, 0)
        if item:
            self.load_requested.emit(item.text())


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
        first.addWidget(self.load_button)
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
        self.library.table.itemSelectionChanged.connect(self._library_selection_changed)
        library_card, library_layout = _card(tr("Library"))
        library_layout.addWidget(self.library, 1)
        library_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # --- parts of the program
        parts_card, parts_layout = _card(tr("Parts of the program"))
        self.part_tables = QTableWidget(len(PARTS), 3)
        self.part_tables.setHorizontalHeaderLabels([tr("Part"), tr("Tone"), tr("Ch.")])
        self.part_tables.verticalHeader().setVisible(False)
        self.part_tables.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.part_tables.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.part_tables.setShowGrid(False)
        head = self.part_tables.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.part_rows: dict[str, int] = {}
        for row, (synth, label, _key, _field, channel) in enumerate(PARTS):
            self.part_rows[synth] = row
            self.part_tables.setItem(row, 0, QTableWidgetItem(tr(label)))
            self.part_tables.setItem(row, 1, QTableWidgetItem("—"))
            self.part_tables.setItem(row, 2, QTableWidgetItem(str(channel)))
        self.part_tables.setFixedHeight(32 + 30 * len(PARTS))
        self.part_tables.cellDoubleClicked.connect(lambda row, _c: self.open_part_editor(row))
        parts_layout.addWidget(self.part_tables)
        parts_layout.addWidget(_note(tr("Double-click a part to open its editor.")))

        # --- mixer (the original strips)
        mixer_card, mixer_layout = _card(tr("Mixer"))
        _strip_titles(self.mixer_panel)
        # The tone names are in PARTS OF THE PROGRAM, the program name on the display
        for label in self.mixer_widget.label_widgets._labels.values():
            label.hide()
        mixer_layout.addWidget(self.mixer_panel)

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(parts_card)
        right.addWidget(mixer_card)
        right.addStretch()

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(library_card, 3)
        top.addLayout(right, 2)

        # --- below: presets, user programs, playlists, system settings
        self.more_tabs = QTabWidget()
        self.more_tabs.setDocumentMode(True)
        for widget, title in (
            (group.preset, tr("Presets")),
            (self.user_programs_widget, tr("User Programs")),
            (self.playlist_widget, tr("Playlist")),
            (self.playlist_editor_widget, tr("Playlist Editor")),
        ):  # the system settings are in Settings
            if widget is not None:
                _strip_titles(widget)
                self.more_tabs.addTab(widget, title)
        # one height for all four (the tallest page's): the area no longer
        # grows and shrinks as the tabs change
        pages = [self.more_tabs.widget(i) for i in range(self.more_tabs.count())]
        tallest = max((page.sizeHint().height() for page in pages), default=320)
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
        group.preset.setMaximumWidth(760)  # a form, not a full-width strip

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

    # --- the library

    def _update_program_combo_box(self) -> None:
        super()._update_program_combo_box()
        library = getattr(self, "library", None)
        if library is not None and self.program_group_widget is not None:
            library.set_programs(self.program_group_widget._program_list_data)

    def _library_selection_changed(self) -> None:
        program_id = self.library.selected_id()
        self.load_button.setEnabled(bool(program_id))
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
        details = next((p for p in self.library.programs if p.id == program_id), None)
        if details is None and program_id[:1] in "ABCD":
            details = get_program_by_id(program_id)
        if details is not None:
            self.update_current_synths(details)
            self.set_current_program_name(details.name)
        group = self.program_group_widget
        send_program_with_expectation(
            self.midi_helper,
            program_id,
            source="program_library",
            channel=group.channel if group is not None else self.channel,
        )
        self.data_request()

    # --- parts

    def _set_part_tone(self, synth_type, tone_name: str) -> None:
        row = getattr(self, "part_rows", {}).get(synth_type)
        if row is not None:
            self.part_tables.item(row, 1).setText(tone_name or "—")

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
