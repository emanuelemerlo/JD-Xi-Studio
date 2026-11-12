"""
JD-Xi Editor UI setup.

This class defines the main user interface for the JD-Xi Editor application, inheriting from QMainWindow.
Key Features:
- Initializes the main window with a tabbed editor interface.

Methods:
    - __init__: Initializes the UI adds elements and sets up the main layout.
    - _close_editor_tab: Handles the closing of editor tabs.

"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QTabWidget, QWidget

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.project import __display_name__, __program__, __version__


class MainEditor(QMainWindow):
    """JD-Xi UI setup, with as little as possible functionality, which is to be super-classed"""

    def __init__(self, parent: QMainWindow = None):
        """
        Constructor for the MainEditor class. Initializes the main layout and sets up the editor tab widget.

        :param parent: JDXiInstrument
        """
        # A window of its own, not owned by the keyboard window: Windows keeps
        # owned windows above their owner, so the keyboard could never come in
        # front of the editors. The keyboard window links them (minimise, close).
        super().__init__(parent=None)
        self.jdxi_main_window = parent
        self.editor_registry = None
        self.editors = []
        self.editor_tab_widget = QTabWidget()
        self.editor_tab_widget.setTabsClosable(False)
        self.setCentralWidget(self.editor_tab_widget)  # if this is a QMainWindow
        JDXi.UI.Theme.apply_editor_style(self)
        self.setWindowTitle(f"{__display_name__} {__version__}")
        # Hide status bar to maximize editor space
        self.statusBar().hide()
        self._build_header()

    # --- the header: name, the editors as buttons, the program and the connection

    # The pane once, on the tab widget; the buttons on the tab bar alone, so changing
    # their colour does not restyle every editor (that took most of a second)
    PANE_STYLE = """
        QTabWidget::pane { border: 0; border-top: 1px solid #23252a; background: #121214; top: -1px; }
        QTabWidget::tab-bar { left: 0; }
    """
    BAR_STYLE = """
        QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
        QTabBar::tab {{
            background: #1b1c1f; color: #c9cbd1; border: 1px solid #2a2d33; border-radius: 8px;
            padding: 5px 10px; margin: 8px 2px 8px 2px; font-size: 12px; font-weight: 600;
        }}
        QTabBar::tab:hover {{ border-color: #4a4d55; color: #ffffff; }}
        QTabBar::tab:selected {{ background: {bg}; color: #ffffff; border: 1px solid {accent}; }}
        QTabBar QToolButton {{ background: #1b1c1f; border: 1px solid #2a2d33; border-radius: 6px; color: #ffffff; }}
    """

    def _build_header(self) -> None:
        from jdxi_editor.i18n import tr

        title = QLabel(__display_name__)
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 800; padding: 0 14px 6px 16px;")
        self.editor_tab_widget.setCornerWidget(title, Qt.Corner.TopLeftCorner)

        right = QWidget()
        row = QHBoxLayout(right)
        row.setContentsMargins(8, 6, 12, 6)
        row.setSpacing(10)
        self.program_chip = QLabel(tr("No program"))
        self.program_chip.setStyleSheet(
            "QLabel { background: #1a1408; color: #f2a23c; border: 1px solid #4a3410; border-radius: 6px;"
            " padding: 4px 10px; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }"
        )
        self.program_chip.setToolTip(tr("The program and the tone last received from the JD-Xi"))
        self.connection_label = QLabel()
        self.connection_label.setStyleSheet("color: #a3a6ad; font-size: 12px;")
        row.addWidget(self.program_chip)
        row.addWidget(self.connection_label)
        self.editor_tab_widget.setCornerWidget(right, Qt.Corner.TopRightCorner)

        self._program_name = ""
        self._tone_name = ""
        self.editor_tab_widget.setIconSize(self.editor_tab_widget.iconSize().scaled(14, 14, Qt.AspectRatioMode.KeepAspectRatio))
        self.editor_tab_widget.tabBar().setElideMode(Qt.TextElideMode.ElideNone)
        self.editor_tab_widget.currentChanged.connect(self._tab_changed)
        self.editor_tab_widget.setStyleSheet(self.PANE_STYLE)
        self._apply_bar_style("#3f8cff")
        helper = getattr(self.jdxi_main_window, "midi_helper", None)
        if helper is not None:
            try:
                helper.update_program_name.connect(self.set_program_name)
                helper.update_tone_name.connect(lambda name, _synth: self.set_tone_name(name))
            except (AttributeError, RuntimeError, TypeError):
                pass
        self._connection_timer = QTimer(self)
        self._connection_timer.timeout.connect(self.update_connection)
        self._connection_timer.start(2000)
        self.update_connection()

    def _apply_bar_style(self, accent: str) -> None:
        from PySide6.QtGui import QColor

        color = QColor(accent)
        bg = f"rgba({color.red()}, {color.green()}, {color.blue()}, 60)"
        self.editor_tab_widget.tabBar().setStyleSheet(self.BAR_STYLE.format(accent=accent, bg=bg))

    def _tab_changed(self, index: int) -> None:
        """The selected editor's button in its own colour."""
        widget = self.editor_tab_widget.widget(index)
        accent = getattr(widget, "ACCENT", None)
        if not accent:
            accent = getattr(__import__(type(widget).__module__, fromlist=["x"]), "ACCENT", None) if widget else None
        self._apply_bar_style(accent if isinstance(accent, str) and accent.startswith("#") else "#3f8cff")

    def set_program_name(self, name: str) -> None:
        self._program_name = (name or "").strip()
        self._update_chip()

    def set_tone_name(self, name: str) -> None:
        self._tone_name = (name or "").strip()
        self._update_chip()

    def _update_chip(self) -> None:
        from jdxi_editor.i18n import tr

        lines = [self._program_name or tr("No program")]
        if self._tone_name:
            lines.append(self._tone_name)
        self.program_chip.setText("  ·  ".join(lines))

    def update_connection(self) -> None:
        from jdxi_editor.i18n import tr

        helper = getattr(self.jdxi_main_window, "midi_helper", None)
        inp = bool(getattr(helper, "is_input_open", False))
        out = bool(getattr(helper, "is_output_open", False))
        if inp and out:
            text, color = tr("JD-Xi connected"), "#6fcf97"
        elif inp or out:
            text, color = tr("MIDI half connected"), "#f2c94c"
        else:
            text, color = tr("Offline"), "#eb5757"
        self.connection_label.setText(f"<span style='color:{color}'>●</span> {text}")

    def closeEvent(self, event) -> None:  # pylint: disable=unused-argument
        """
        close the editor tab widget, but dont delete it

        :param event: QEvent
        """
        self.hide()
