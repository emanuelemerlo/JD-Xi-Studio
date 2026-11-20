"""
MIDI connection dialog
======================

Chooses the MIDI ports of the JD-Xi and tests the connection.

The dialog never waits on the user interface thread:

- it opens at once with the ports already known, then lists the ports again
  in the background;
- "Test connection" sends an Identity Request and waits for the reply with a
  timer, not a loop.

The ports chosen apply with OK; the reconnection happens after the dialog has
closed.

Public attributes kept for callers and tests: input_combo, output_combo,
get_input_port(), get_output_port(), get_settings(), refresh_ports().
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import shiboken6
from decologr import Decologr as log
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.i18n import tr
from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.style import JDXiUIDimensions
from jdxi_editor.ui.windows.jdxi.helpers.port import (
    filter_excluded_ports,
    find_jdxi_port,
    is_excluded_port,
)

IDENTITY_REQUEST = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]  # any device ID
IDENTITY_TIMEOUT_MS = 1500
JDXI_FAMILY = (0x0E, 0x03)
ROLAND = 0x41



# --------------------------------------------------------------------- background
class _Relay(QObject):
    """Delivers a background result on the UI thread, if its owner still exists.

    Not a child of the owner: the dialog may be deleted (closed) while the work
    runs, and the worker must never emit on a deleted object.
    """

    finished = Signal(object, object)  # result, exception

    def __init__(self, callback: Callable, owner: QObject):
        super().__init__()
        self._callback = callback
        self._owner = owner
        self.finished.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    @Slot(object, object)
    def _deliver(self, result, error) -> None:
        try:
            if shiboken6.isValid(self._owner):
                self._callback(result, error)
        finally:
            self._owner = self._callback = None
            _RELAYS.discard(self)


_RELAYS: set = set()  # alive until delivered


def run_in_background(fn: Callable, callback: Callable, parent: QObject) -> None:
    """fn() on a worker thread, then callback(result, error) on parent's thread.

    A plain Python thread (not a QRunnable, whose wrapper PySide may free while
    it runs); the result crosses back through a queued Qt signal.
    """
    relay = _Relay(callback, parent)
    _RELAYS.add(relay)

    def work() -> None:
        try:
            result, error = fn(), None
        except Exception as ex:  # reported to the callback
            result, error = None, ex
        relay.finished.emit(result, error)

    threading.Thread(target=work, name="MIDIConfigDialog", daemon=True).start()


# ------------------------------------------------------------------- slow lookups
def list_midi_ports(midi_helper) -> tuple[list[str], list[str]]:
    return (
        filter_excluded_ports(midi_helper.get_input_ports()),
        filter_excluded_ports(midi_helper.get_output_ports()),
    )


def parse_identity_reply(data) -> Optional[dict]:
    """Identity Reply (mido sysex data, without F0/F7) -> details, else None."""
    data = list(data)
    if len(data) < 7 or data[0] != 0x7E or data[2] != 0x06 or data[3] != 0x02:
        return None
    return {
        "manufacturer": data[4],
        "family": tuple(data[5:7]),
        "is_jdxi": data[4] == ROLAND and tuple(data[5:7]) == JDXI_FAMILY,
        "version": ".".join(str(b) for b in data[9:13]) if len(data) >= 13 else "",
    }


class MIDIConfigDialog(QDialog):
    """Ports of the JD-Xi and the connection test."""

    def __init__(self, midi_helper=MidiIOHelper, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("MIDI connection"))
        self.setMinimumWidth(JDXiUIDimensions.Config.WIDTH)
        JDXi.UI.Theme.apply_editor_style(self)
        self.midi_helper = midi_helper
        self.current_in = getattr(midi_helper, "current_in", None)
        self.current_out = getattr(midi_helper, "current_out", None)
        self.input_ports: list[str] = []
        self.output_ports: list[str] = []
        self._identity_timer = QTimer(self)
        self._identity_timer.setSingleShot(True)
        self._identity_timer.timeout.connect(self._identity_timed_out)
        self._listening = False
        self.status_kind = "idle"

        self._build()
        # What is known now, at once; the fresh lists follow from the background
        self._fill_ports(*self._known_ports())
        QTimer.singleShot(0, self, self.refresh_ports)
        if self._ports_open():
            QTimer.singleShot(150, self, self.test_connection)
        else:
            self._set_status("idle", tr("Not connected. Choose the JD-Xi's ports, then Test connection."))

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- JD-Xi
        jdxi_box = QGroupBox(tr("JD-Xi"))
        jdxi_layout = QVBoxLayout(jdxi_box)
        status_row = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(18)
        # as tall as one line of the message and centred in it: the dot sits on its first line
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        # Room for three lines, so a longer message does not get cut
        self.status_label.setMinimumHeight(self.status_label.fontMetrics().lineSpacing() * 3)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.status_dot.setFixedHeight(self.status_label.fontMetrics().lineSpacing())
        status_row.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignTop)
        status_row.addWidget(self.status_label, 1)
        jdxi_layout.addLayout(status_row)

        form = QFormLayout()
        self.input_combo = QComboBox()
        self.output_combo = QComboBox()
        for combo in (self.input_combo, self.output_combo):
            combo.setMinimumContentsLength(28)
            combo.currentIndexChanged.connect(self._on_port_choice_changed)
        form.addRow(tr("From the JD-Xi (MIDI input):"), self.input_combo)
        form.addRow(tr("To the JD-Xi (MIDI output):"), self.output_combo)
        jdxi_layout.addLayout(form)

        buttons = QHBoxLayout()
        self.find_button = QPushButton(tr("Find the JD-Xi"))
        self.find_button.setToolTip(tr("Choose the ports whose name contains JD-Xi"))
        self.find_button.clicked.connect(self.select_jdxi_ports)
        self.refresh = QPushButton(tr("Refresh list"))
        self.refresh.setToolTip(tr("List the MIDI ports again, e.g. after connecting the JD-Xi"))
        self.refresh.clicked.connect(self.refresh_ports)
        self.test_button = QPushButton(tr("Test connection"))
        self.test_button.setToolTip(
            tr("Connect to the chosen ports and ask the instrument who it is")
        )
        self.test_button.clicked.connect(self.test_connection)
        for button in (self.find_button, self.refresh, self.test_button):
            buttons.addWidget(button)
        buttons.addStretch()
        jdxi_layout.addLayout(buttons)
        self.help_label = QLabel(
            tr(
                "No JD-Xi in the list? Connect it by USB, switch it on and press "
                "Refresh list. Without it the editor works offline."
            )
        )
        self.help_label.setWordWrap(True)
        self.help_label.setVisible(False)
        jdxi_layout.addWidget(self.help_label)
        layout.addWidget(jdxi_box)

        # --- OK / Cancel (Qt translates the standard buttons)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)


    # ------------------------------------------------------------------ status
    def _set_status(self, kind: str, text: str) -> None:
        colours = {"ok": "#3cc98a", "busy": "#f2c94c", "error": "#f0483e", "idle": "#8a8d94"}
        self.status_dot.setStyleSheet(f"color: {colours.get(kind, '#8a8d94')}; font-size: 12px;"
                                      " padding: 0; margin: 0;")
        self.status_label.setText(text)
        self.status_kind = kind

    # ------------------------------------------------------------------- ports
    def _ports_open(self) -> bool:
        h = self.midi_helper
        return bool(getattr(h, "is_input_open", False) and getattr(h, "is_output_open", False))

    def _known_ports(self) -> tuple[list[str], list[str]]:
        known_in = [p for p in [self.current_in] if p]
        known_out = [p for p in [self.current_out] if p]
        return known_in, known_out

    def refresh_ports(self) -> None:
        """List the MIDI ports again, in the background."""
        self.refresh.setEnabled(False)
        self.refresh.setText(tr("Listing…"))
        run_in_background(lambda: list_midi_ports(self.midi_helper), self._ports_listed, self)

    def _ports_listed(self, result, error) -> None:
        self.refresh.setEnabled(True)
        self.refresh.setText(tr("Refresh list"))
        if error is not None:
            log.error(f"Listing MIDI ports failed: {error}", scope="MIDIConfigDialog")
            self._set_status("error", tr("Could not list the MIDI ports: {error}").format(error=error))
            return
        self._fill_ports(*result)

    def _fill_ports(self, inputs: list[str], outputs: list[str]) -> None:
        chosen_in = self.input_combo.currentText() or self.current_in
        chosen_out = self.output_combo.currentText() or self.current_out
        self.input_ports, self.output_ports = list(inputs), list(outputs)
        for combo, ports, chosen in (
            (self.input_combo, self.input_ports, chosen_in),
            (self.output_combo, self.output_ports, chosen_out),
        ):
            combo.blockSignals(True)
            combo.clear()
            jdxi = find_jdxi_port(ports)
            # The JD-Xi first, so it is easy to spot
            for port in sorted(ports, key=lambda p: p != jdxi):
                combo.addItem(f"★ {port}" if port == jdxi else port, port)
            index = combo.findData(chosen) if chosen else -1
            if index < 0 and jdxi:
                index = combo.findData(jdxi)
            combo.setCurrentIndex(max(index, 0) if combo.count() else -1)
            combo.blockSignals(False)
        found = bool(find_jdxi_port(self.input_ports) and find_jdxi_port(self.output_ports))
        self.find_button.setEnabled(found)
        self.help_label.setVisible(not found)
        # Only when no test is running or has answered: its result says more
        if not found and self.status_kind == "idle":
            self._set_status("error", tr("No JD-Xi among the MIDI ports."))

    def select_jdxi_ports(self) -> None:
        for combo, ports in ((self.input_combo, self.input_ports), (self.output_combo, self.output_ports)):
            port = find_jdxi_port(ports)
            if port:
                combo.setCurrentIndex(combo.findData(port))

    def _on_port_choice_changed(self, _index: int = 0) -> None:
        if self._ports_changed():
            self._set_status("idle", tr("Ports changed: Test connection, or OK to use them."))

    def _ports_changed(self) -> bool:
        return (self.get_input_port() or None) != (self.current_in or None) or (
            self.get_output_port() or None
        ) != (self.current_out or None)

    def get_input_port(self) -> str:
        return self.input_combo.currentData() or self.input_combo.currentText().removeprefix("★ ")

    def get_output_port(self) -> str:
        return self.output_combo.currentData() or self.output_combo.currentText().removeprefix("★ ")

    def get_settings(self) -> dict:
        return {"input_port": self.get_input_port(), "output_port": self.get_output_port()}

    def _apply_ports(self) -> bool:
        in_port = self.get_input_port()
        out_port = self.get_output_port()
        in_port = "" if is_excluded_port(in_port) else in_port
        out_port = "" if is_excluded_port(out_port) else out_port
        log.message(f"Reconnecting to: Midi In: '{in_port}' Midi Out: '{out_port}'")
        ok = self.midi_helper.reconnect_port_names(in_port, out_port)
        if ok:
            self.current_in, self.current_out = in_port, out_port
        else:
            log.warning("Failed to reopen both MIDI ports", scope="MIDIConfigDialog")
        return ok

    # -------------------------------------------------------- connection test
    def test_connection(self) -> None:
        """Use the chosen ports and send an Identity Request; the reply arrives later."""
        if self._ports_changed() and not self._apply_ports():
            self._set_status("error", tr("Could not open the chosen ports."))
            return
        signal = getattr(self.midi_helper, "midi_message_incoming", None)
        if signal is None or not self._ports_open():
            self._set_status("error", tr("The MIDI ports are not open."))
            return
        if not self._listening:
            signal.connect(self._on_midi_message)
            self._listening = True
        self._set_status("busy", tr("Asking the instrument…"))
        self.test_button.setEnabled(False)
        self._identity_timer.start(IDENTITY_TIMEOUT_MS)
        try:
            self.midi_helper.send_raw_message(IDENTITY_REQUEST)
        except Exception as ex:
            self._identity_timer.stop()
            self.test_button.setEnabled(True)
            self._set_status("error", tr("Could not send to the MIDI output: {error}").format(error=ex))

    @Slot(object)
    def _on_midi_message(self, message) -> None:
        if not self._identity_timer.isActive() or getattr(message, "type", "") != "sysex":
            return
        reply = parse_identity_reply(getattr(message, "data", ()))
        if reply is None:
            return
        self._identity_timer.stop()
        self.test_button.setEnabled(True)
        if reply["is_jdxi"]:
            self._set_status("ok", tr("Connected: the JD-Xi replies."))
        else:
            self._set_status(
                "error",
                tr("A different instrument replied (manufacturer {id}). Choose the JD-Xi's ports.").format(
                    id=f"{reply['manufacturer']:02X}h"
                ),
            )

    def _identity_timed_out(self) -> None:
        self.test_button.setEnabled(True)
        self._set_status(
            "error",
            tr(
                "No reply. Check that the JD-Xi is on and that both ports are the JD-Xi's "
                "(not, e.g., Microsoft GS Wavetable Synth)."
            ),
        )

    # --------------------------------------------------------------- closing
    def _stop_listening(self) -> None:
        self._identity_timer.stop()
        if self._listening:
            try:
                self.midi_helper.midi_message_incoming.disconnect(self._on_midi_message)
            except (RuntimeError, TypeError):
                pass
            self._listening = False

    def accept(self) -> None:
        self._stop_listening()
        changed = self._ports_changed()
        super().accept()
        if changed:
            self._apply_ports()  # after the dialog has closed

    def reject(self) -> None:
        self._stop_listening()
        super().reject()
