"""
Preferences Dialog

Sets settings for various biotoolkit features
"""

import logging

from decologr import Decologr as log
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QSettings, QSize
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
)

from jdxi_editor.project import (
    __display_name__,
    __organization_name__,
    __package_name__,
    __program__,
)
from jdxi_editor.ui.common import JDXi, QVBoxLayout, QWidget
from jdxi_editor.i18n import (
    LANGUAGES,
    SYSTEM,
    language_setting,
    set_language_setting,
    tr,
)


def log_settings() -> None:
    settings = QSettings(__organization_name__, __program__)
    print(f'log_level {settings.value("log_level", logging.DEBUG, type=int)}')
    print(f'logging {settings.value("logging", True, type=bool)}')


class UiPreferencesDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.icon_size = None
        self.settings = QSettings(__organization_name__, __program__)

    def ui_setup(self, parent: QWidget = None):
        """
        ui_setup
        :param parent: QWidget
        :return: None
        """
        self.icon_size = QSize(40, 40)
        """if darkdetect.isLight():
            theme = "light"
        else:
            theme = "dark"""
        log_settings()
        self.resize(508, 400)

        self.setWindowTitle(tr("{program} preferences").format(program=__display_name__))
        main_layout = QVBoxLayout(self)

        # Create a QComboBox
        self.log_level_combo = QComboBox()
        self.log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        self.log_level_combo.addItems(self.log_levels.keys())
        # Load the log level from QSettings
        # self.load_log_level_from_settings()
        log_level = int(self.settings.value("log_level", logging.DEBUG))
        # Reverse lookup: find the key name for the numeric value
        try:
            level_name = next((k for k, v in self.log_levels.items() if v == log_level))
        except StopIteration:
            level_name = "DEBUG"  # default
        index = list(self.log_levels.keys()).index(level_name)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
        # Connect the combo box to a function that updates QSettings
        self.log_level_combo.currentIndexChanged.connect(self.update_log_level)

        self.log_level_layout = QHBoxLayout()
        self.log_icon = QLabel()
        self.log_icon.setPixmap(
            JDXi.UI.Icon.get_icon(JDXi.UI.Icon.REPORT).pixmap(self.icon_size)
        )
        self.log_level_label = QLabel(tr("Log file error reporting level:"))
        self.log_level_layout.addWidget(self.log_icon)
        self.log_level_layout.addWidget(self.log_level_label)
        self.log_level_layout.addWidget(self.log_level_combo)

        self.logging_layout = QHBoxLayout()
        self.logging_icon = QLabel()
        self.logging_checkbox = QCheckBox(tr("Enable Logging?"))
        self.logging_checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.logging_checkbox.setChecked(
            bool(self.settings.value("logging", type=bool))
        )
        self.logging_icon.setPixmap(
            JDXi.UI.Icon.get_icon(JDXi.UI.Icon.REPORT).pixmap(self.icon_size)
        )
        self.logging_label = QLabel(tr("Logging On or Off:"))
        self.logging_layout.addWidget(self.logging_icon)
        self.logging_layout.addWidget(self.logging_label)
        self.logging_layout.addWidget(self.logging_checkbox)

        # Silence MIDI note logging (note on/off only) to reduce log volume
        from jdxi_editor.globals import SILENCE_MIDI_NOTE_LOGGING_KEY

        self.silence_midi_notes_layout = QHBoxLayout()
        self.silence_midi_notes_icon = QLabel()
        self.silence_midi_notes_checkbox = QCheckBox(
            tr("Silence MIDI note logging (note on/off)")
        )
        self.silence_midi_notes_checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
        _val = self.settings.value(SILENCE_MIDI_NOTE_LOGGING_KEY, True)
        _checked = (
            _val
            if isinstance(_val, bool)
            else (str(_val).lower() in ("true", "1", "yes"))
        )
        self.silence_midi_notes_checkbox.setChecked(_checked)
        self.silence_midi_notes_icon.setPixmap(
            JDXi.UI.Icon.get_icon(JDXi.UI.Icon.REPORT).pixmap(self.icon_size)
        )
        self.silence_midi_notes_label = QLabel(tr("Reduce log volume from MIDI notes:"))
        self.silence_midi_notes_layout.addWidget(self.silence_midi_notes_icon)
        self.silence_midi_notes_layout.addWidget(self.silence_midi_notes_label)
        self.silence_midi_notes_layout.addWidget(self.silence_midi_notes_checkbox)

        from jdxi_editor.globals import MIDI_SELECTION_VALIDATION_KEY

        self.midi_validation_layout = QHBoxLayout()
        self.midi_validation_icon = QLabel()
        self.midi_validation_checkbox = QCheckBox(
            tr("Validate MIDI sends against combo selection (log only)")
        )
        self.midi_validation_checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
        _val_mv = self.settings.value(MIDI_SELECTION_VALIDATION_KEY, False)
        _checked_mv = (
            _val_mv
            if isinstance(_val_mv, bool)
            else (str(_val_mv).lower() in ("true", "1", "yes"))
        )
        self.midi_validation_checkbox.setChecked(_checked_mv)
        self.midi_validation_icon.setPixmap(
            JDXi.UI.Icon.get_icon(JDXi.UI.Icon.REPORT).pixmap(self.icon_size)
        )
        self.midi_validation_label = QLabel(tr("MIDI selection cross-validation:"))
        self.midi_validation_layout.addWidget(self.midi_validation_icon)
        self.midi_validation_layout.addWidget(self.midi_validation_label)
        self.midi_validation_layout.addWidget(self.midi_validation_checkbox)

        # --- Automatic update check (on by default)
        from jdxi_editor.update.checker import (
            AUTO_CHECK_DEFAULT,
            AUTO_CHECK_KEY,
            settings_bool,
        )

        self.update_check_layout = QHBoxLayout()
        self.update_check_icon = QLabel()
        self.update_check_icon.setPixmap(
            JDXi.UI.Icon.get_icon(JDXi.UI.Icon.SETTINGS).pixmap(self.icon_size)
        )
        self.update_check_label = QLabel(
            tr("Check GitHub for new releases once a day (on by default):")
        )
        self.update_check_checkbox = QCheckBox(tr("Check for updates automatically"))
        self.update_check_checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.update_check_checkbox.setChecked(
            settings_bool(self.settings, AUTO_CHECK_KEY, AUTO_CHECK_DEFAULT)
        )
        self.update_check_layout.addWidget(self.update_check_icon)
        self.update_check_layout.addWidget(self.update_check_label)
        self.update_check_layout.addWidget(self.update_check_checkbox)

        # --- Interface language: applies at the next start
        self.language_layout = QHBoxLayout()
        self.language_icon = QLabel()
        self.language_icon.setPixmap(
            JDXi.UI.Icon.get_icon(JDXi.UI.Icon.SETTINGS).pixmap(self.icon_size)
        )
        self.language_label = QLabel(tr("Interface language:"))
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("language_combo")
        self.language_combo.addItem(tr("Same as the system"), SYSTEM)
        for code, name in LANGUAGES.items():
            self.language_combo.addItem(name, code)  # each in its own language
        index = self.language_combo.findData(language_setting(self.settings))
        self.language_combo.setCurrentIndex(max(index, 0))
        self.language_note = QLabel(tr("The new language is used from the next start."))
        self.language_note.setVisible(False)
        self.language_combo.currentIndexChanged.connect(
            lambda _: self.language_note.setVisible(
                self.language_combo.currentData() != language_setting(self.settings)
            )
        )
        self.language_layout.addWidget(self.language_icon)
        self.language_layout.addWidget(self.language_label)
        self.language_layout.addWidget(self.language_combo)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(150, 250, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.on_save_settings)
        self.buttonBox.accepted.connect(self.close)
        QtCore.QMetaObject.connectSlotsByName(self)

        # Two cards, as the rest of the app: the interface first, then the logs.
        # A choice: its name and the list side by side; an option: its box, with
        # what it does in grey below (the separate labels and icons only repeated it)
        accent = "#ff2a1a"
        self.setObjectName("preferences")
        self.setStyleSheet(
            "QDialog#preferences { background: #121214; }"
            "QFrame#prefCard { background: #1b1c1f; border: 1px solid #2e3036; border-radius: 10px; }"
            "QLabel { color: #e6e6e6; background: transparent; }"
            f"QLabel#prefHead {{ color: {accent}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}"
            "QLabel#prefHint { color: #8a8d94; font-size: 11px; }"
            "QCheckBox { color: #e6e6e6; spacing: 8px; }"
            "QComboBox { background: #121214; color: #ffffff; border: 1px solid #3a3d44; border-radius: 5px;"
            " padding: 3px 8px; min-width: 170px; }"
        )
        for icon in (self.log_icon, self.logging_icon, self.silence_midi_notes_icon,
                     self.midi_validation_icon, self.update_check_icon, self.language_icon):
            icon.hide()
        for box in (self.logging_checkbox, self.silence_midi_notes_checkbox,
                    self.midi_validation_checkbox, self.update_check_checkbox):
            box.setLayoutDirection(QtCore.Qt.LeftToRight)

        def card(title: str):
            frame = QtWidgets.QFrame()
            frame.setObjectName("prefCard")
            grid = QtWidgets.QGridLayout(frame)
            grid.setContentsMargins(16, 12, 16, 14)
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(4)
            head = QLabel(title.upper())
            head.setObjectName("prefHead")
            grid.addWidget(head, 0, 0, 1, 2)
            grid.setColumnStretch(0, 1)
            return frame, grid

        def choice(grid, label: QLabel, combo: QComboBox) -> None:
            row = grid.rowCount()
            label.setText(label.text().rstrip(":"))
            grid.addWidget(label, row, 0)
            grid.addWidget(combo, row, 1)
            grid.setRowMinimumHeight(row, 34)

        def option(grid, box: QCheckBox, hint: QLabel) -> None:
            row = grid.rowCount()
            grid.addWidget(box, row, 0, 1, 2)
            hint.setText(hint.text().rstrip(":"))
            hint.setObjectName("prefHint")
            hint.setWordWrap(True)
            hint.setContentsMargins(26, 0, 0, 6)  # under the box's text
            grid.addWidget(hint, row + 1, 0, 1, 2)

        interface, grid = card(tr("Interface"))
        choice(grid, self.language_label, self.language_combo)
        self.language_note.setObjectName("prefHint")
        grid.addWidget(self.language_note, grid.rowCount(), 0, 1, 2)
        option(grid, self.update_check_checkbox, self.update_check_label)
        logs, grid = card(tr("Logs"))
        choice(grid, self.log_level_label, self.log_level_combo)
        option(grid, self.logging_checkbox, self.logging_label)
        option(grid, self.silence_midi_notes_checkbox, self.silence_midi_notes_label)
        option(grid, self.midi_validation_checkbox, self.midi_validation_label)
        main_layout.setContentsMargins(16, 16, 16, 12)
        main_layout.setSpacing(12)
        main_layout.addWidget(interface)
        main_layout.addWidget(logs)
        main_layout.addStretch(1)
        main_layout.addWidget(self.buttonBox)
        self.setMinimumWidth(520)
        self.resize(560, self.sizeHint().height())
        self.setLayout(main_layout)

    def load_log_level_from_settings(self):
        """
        Load and migrate log level from settings (handles legacy string values).
        """
        value = self.settings.value("log_level", logging.DEBUG)

        # Case 1: Value already an integer (new style)
        if isinstance(value, int):
            log_level = value

        # Case 2: Legacy value stored as string (e.g., "CRITICAL")
        elif isinstance(value, str):
            # Try to parse as integer first
            try:
                log_level = int(value)
            except ValueError:
                # Convert known string names
                log_level = self.log_levels.get(value.upper(), logging.DEBUG)
                # Migrate: store the numeric version back
                self.settings.setValue("log_level", log_level)

        else:
            # Fallback
            log_level = logging.DEBUG

        # Set combo box to correct index
        level_name = next(
            (k for k, v in self.log_levels.items() if v == log_level), "DEBUG"
        )
        index = list(self.log_levels.keys()).index(level_name)
        self.log_level_combo.setCurrentIndex(index)

        # Set the logger level immediately
        logging.getLogger(__package_name__).setLevel(log_level)

    def update_log_level(self, level):
        """
        Update log level for the current logger and all handlers
        """
        log.parameter("level", level)
        logger = logging.getLogger(__package_name__)
        logger.setLevel(level)

        for handler in logger.handlers:
            handler.setLevel(level)

        # Also apply to root logger and its handlers (optional, if you use root logging)
        logging.root.setLevel(level)
        for handler in logging.root.handlers:
            handler.setLevel(level)

        self.settings.setValue("log_level", level)
        self.settings.sync()
        print(f"✅ Updated log level to {logging.getLevelName(level)}")

    def on_save_settings(self):
        """
        on_save_settings
        :return: None
        """
        from jdxi_editor.globals import (
            MIDI_SELECTION_VALIDATION_KEY,
            SILENCE_MIDI_NOTE_LOGGING_KEY,
        )

        settings = self.settings
        try:
            settings.setValue("logging", bool(self.logging_checkbox.isChecked()))
            settings.setValue(
                SILENCE_MIDI_NOTE_LOGGING_KEY,
                bool(self.silence_midi_notes_checkbox.isChecked()),
            )
            settings.setValue(
                MIDI_SELECTION_VALIDATION_KEY,
                bool(self.midi_validation_checkbox.isChecked()),
            )
            from jdxi_editor.update.checker import AUTO_CHECK_KEY

            settings.setValue(
                AUTO_CHECK_KEY, bool(self.update_check_checkbox.isChecked())
            )
            set_language_setting(self.language_combo.currentData(), settings)
            settings.sync()
            log_settings()
        except Exception as ex:
            print(f"Error {ex} occurred saving settings")
