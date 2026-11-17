"""
message_debug module
====================

MIDIMessageDebug is a Qt-based main window for logging and displaying MIDI messages.
It provides a real-time log view where MIDI messages can be logged with timestamps,
allowing for easy debugging of MIDI communication.

Attributes:
    log_view (QTextEdit): A text edit widget used to digital the MIDI message log.

Methods:
    log.message(message, direction="→"): Logs a MIDI message with a timestamp.
    Optionally, the direction (input or output) of the message can be specified.
    clear_log(): Clears the message log view.
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QMainWindow, QTextEdit, QVBoxLayout, QWidget

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.theme import ThemeManager
from jdxi_editor.i18n import tr


class MIDIMessageMonitor(QMainWindow):
    """MIDIMessageMonitor"""

    def __init__(
        self, midi_helper: MidiIOHelper = None, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("MIDI Message Monitor"))
        self.setMinimumSize(600, 400)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Without the JD-Xi nothing goes out: say so, instead of an empty log
        self.port_notice = QLabel(
            tr("The JD-Xi is not connected: no MIDI message is sent or received, so the monitor stays empty.")
        )
        self.port_notice.setWordWrap(True)
        self.port_notice.setStyleSheet(
            "QLabel { background: #2a2224; color: #f0c7c3; border: 1px solid #6b3a35;"
            " border-radius: 4px; padding: 6px 8px; }"
        )
        layout.addWidget(self.port_notice)

        # Create log view
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.NoWrap)
        ThemeManager.apply_midi_monitor(self.log_view)
        layout.addWidget(self.log_view)
        self.midi_helper = midi_helper
        self.midi_helper.midi_message_incoming.connect(self.process_incoming_message)
        self.midi_helper.midi_message_outgoing.connect(self.process_outgoing_message)
        self._port_timer = QTimer(self)
        self._port_timer.timeout.connect(self._show_port_state)
        self._port_timer.start(1000)
        self._show_port_state()

    def _show_port_state(self) -> None:
        """The notice shows while the output port to the JD-Xi is not open."""
        port = getattr(self.midi_helper, "midi_out", None)
        try:
            is_open = bool(port is not None and port.is_port_open())
        except Exception:
            is_open = False
        self.port_notice.setVisible(not is_open)

    def process_incoming_message(self, message: str) -> None:
        """
        process_incoming_message

        :param message: str
        :return: None
        """
        self.log_message(message, direction="←")

    def process_outgoing_message(self, message: str) -> None:
        """
        process_outgoing_message

        :param message: str
        :return: None
        """
        self.log_message(message)

    def log_message(self, message: str, direction="→"):
        """
        Log address MIDI message with timestamp and hex formatting if possible

        :param message: str
        :param direction: str
        :return: None
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if isinstance(message, (list, bytes)):
            try:
                hex_str = " ".join([f"{int(b):02X}" for b in message])
            except (ValueError, TypeError):
                hex_str = str(message)
            self.log_view.append(f"{timestamp} {direction} {hex_str}")
        else:
            self.log_view.append(f"{timestamp} {direction} {message}")

    def clear_log(self):
        """Clear the log view"""
        self.log_view.clear()
