"""
The log viewer: this session's log file, followed while it grows.

Two tabs: every line, and only the lines that deserve attention (warnings,
errors and what follows them, e.g. a traceback). Fixed-width text so the
columns line up; the emoji Decologr puts before each message are left out
(the level column already says it).
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.log_files import LOG_KEEP_DAYS, log_dir
from jdxi_editor.project import __data_name__
from jdxi_editor.ui.common import JDXi, QVBoxLayout, QWidget

ATTENTION = ("WARNING", "ERROR", "CRITICAL")
_ENTRY = re.compile(r"^\[\d\d:\d\d:\d\d\]\s+(\w+)")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2139\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+ ?")
MAX_LINES = 20000  # the view keeps the newest lines (the file keeps them all)


def fixed_font() -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setFamilies(["Consolas", "Cascadia Mono", "Menlo", "DejaVu Sans Mono", font.family()])
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFixedPitch(True)
    font.setPointSize(10)
    return font


def clean(line: str) -> str:
    return _EMOJI.sub("", line)


def needs_attention(lines: list[str], following: bool = False) -> tuple[list[str], bool]:
    """The lines with a level from WARNING up, with the lines that continue them."""
    kept = []
    for line in lines:
        match = _ENTRY.match(line)
        if match:
            following = match.group(1).upper() in ATTENTION
        if following and line.strip():
            kept.append(line)
    return kept, following


class LogViewer(QMainWindow):
    def __init__(self, midi_helper=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Log Viewer"))
        self.setMinimumSize(980, 400)
        self.setStyleSheet(JDXi.UI.Style.LOG_VIEWER)

        # Each session writes its own file (~/.jdxi_studio/logs/jdxi_studio-<date>-<time>.log):
        # the newest one is this session's
        self.log_file = self.session_log()
        self.last_position = 0  # bytes already read
        self._partial = b""  # a line still being written
        self._following = False  # the last line read continues a warning or an error
        self._attention_count = 0
        self.fast_refresh_mode = True

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        self.tabs = QTabWidget()
        self.log_text = self._text_view()
        self.attention_text = self._text_view()
        self.tabs.addTab(self.log_text, tr("All"))
        self.tabs.addTab(self.attention_text, "")
        self._update_attention_title()
        layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        clear_button = QPushButton(tr("Clear Log"))
        clear_button.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_button)
        self.refresh_mode_button = QPushButton(tr("Fast Refresh (500ms)"))
        self.refresh_mode_button.setCheckable(True)
        self.refresh_mode_button.setChecked(True)
        self.refresh_mode_button.clicked.connect(self.toggle_refresh_mode)
        button_layout.addWidget(self.refresh_mode_button)
        layout.addLayout(button_layout)

        note = QLabel(
            tr("{file}  •  log files older than {days} days are deleted at start").format(
                file=self.log_file.name, days=LOG_KEEP_DAYS
            )
        )
        note.setStyleSheet("color: #9a9a9a; font-size: 11px;")
        layout.addWidget(note)

        self.setCentralWidget(main_widget)
        self.load_log_file()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_log_file)
        self.refresh_timer.start(500)

    def _text_view(self) -> QPlainTextEdit:
        view = QPlainTextEdit()
        view.setObjectName("logText")
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        view.setMaximumBlockCount(MAX_LINES)
        font = fixed_font()
        view.setFont(font)
        families = ", ".join(f"'{f}'" for f in font.families())
        view.setStyleSheet(
            "QPlainTextEdit#logText { background-color: #1A1A1A; color: #FFFFFF;"
            " border: 1px solid #FF0000; border-radius: 3px; padding: 5px;"
            f" font-family: {families}, monospace; font-size: 10pt; }}"
        )
        return view

    def _update_attention_title(self) -> None:
        self.tabs.setTabText(1, tr("Warnings and errors ({count})").format(count=self._attention_count))

    @staticmethod
    def session_log(folder: Path | None = None) -> Path:
        """The newest log file (this session's); the folder's expected file when there is none."""
        folder = folder or log_dir()
        try:
            logs = sorted(folder.glob("*.log"), key=lambda p: p.stat().st_mtime)
        except OSError:
            logs = []
        return logs[-1] if logs else folder / f"{__data_name__}.log"

    def load_log_file(self):
        """Read the whole file again."""
        self.log_text.clear()
        self.attention_text.clear()
        self.last_position, self._partial, self._following = 0, b"", False
        self._attention_count = 0
        if not self.log_file.exists():
            self.log_text.setPlainText(
                tr("Log file not found.\n\nExpected location: {path}").format(path=self.log_file)
            )
            self._update_attention_title()
            return
        self.refresh_log_file()

    def refresh_log_file(self):
        """Append the complete lines written since the last read."""
        try:
            with open(self.log_file, "rb") as f:  # positions in bytes: the emoji are several bytes
                f.seek(self.last_position)
                data = f.read()
                self.last_position = f.tell()
        except OSError:
            return  # locked or deleted for a moment
        if not data:
            return
        data = self._partial + data
        complete, _, self._partial = data.rpartition(b"\n")
        if not complete and not _:
            self._partial = data
            return
        lines = [clean(line) for line in complete.decode("utf-8", "replace").splitlines()]
        self._append(self.log_text, lines)
        kept, self._following = needs_attention(lines, self._following)
        if kept:
            self._attention_count += sum(1 for line in kept if _ENTRY.match(line))
            self._append(self.attention_text, kept)
            self._update_attention_title()

    @staticmethod
    def _append(view: QPlainTextEdit, lines: list[str]) -> None:
        bar = view.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 2
        view.appendPlainText("\n".join(lines))
        if at_end:  # follow the new lines, unless the user scrolled up to read
            bar.setValue(bar.maximum())

    def toggle_refresh_mode(self):
        """Toggle between fast refresh (500ms) and slow refresh (30s)"""
        self.fast_refresh_mode = not self.fast_refresh_mode
        if self.fast_refresh_mode:
            self.refresh_timer.setInterval(500)
            self.refresh_mode_button.setText(tr("Fast Refresh (500ms)"))
        else:
            self.refresh_timer.setInterval(30000)
            self.refresh_mode_button.setText(tr("Slow Refresh (30s)"))
        self.refresh_timer.start()

    def clear_log(self):
        """Empty the view; only the lines written from now on appear (the file is untouched)."""
        self.log_text.clear()
        self.attention_text.clear()
        self._attention_count = 0
        self._update_attention_title()
        # the position stays where it is: the old lines are not read again

    def closeEvent(self, event):
        """Stop the refresh timer when window is closed"""
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()
        event.accept()
