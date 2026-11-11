"""
MIDI connection dialog
======================

Chooses the MIDI ports of the JD-Xi and, optionally, the FluidSynth software
synth used to listen without the instrument.

The dialog never waits on the user interface thread:

- it opens at once with the ports already known, then lists the ports again
  in the background;
- the audio devices and the SoundFonts are listed only when the FluidSynth
  section is opened, in the background (PortAudio can take seconds);
- FluidSynth starts and loads its SoundFont in the background, only when
  asked (it used to start, and load a 140 MB SoundFont, as the dialog opened);
- "Test connection" sends an Identity Request and waits for the reply with a
  timer, not a loop.

The ports chosen apply with OK; the reconnection happens after the dialog has
closed.

Public attributes kept for callers and tests: input_combo, output_combo,
get_input_port(), get_output_port(), get_settings(), refresh_ports().
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Callable, Optional

import shiboken6
from decologr import Decologr as log
from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.i18n import tr
from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.editors.pattern.preset_list_provider import (
    get_hardware_interface,
    get_sf2_path,
    get_use_soundfont_list,
    set_hardware_interface,
    set_sf2_path,
    set_use_soundfont_list,
    soundfont_list_problem,
)
from jdxi_editor.ui.style import JDXiUIDimensions
from jdxi_editor.ui.windows.jdxi.helpers.port import (
    filter_excluded_ports,
    find_jdxi_port,
    is_excluded_port,
)

SF2_DIR = os.path.expanduser("~/SoundFonts")
SF2_PATH = os.path.join(SF2_DIR, "FluidR3_GM.sf2")
IDENTITY_REQUEST = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]  # any device ID
IDENTITY_TIMEOUT_MS = 1500
JDXI_FAMILY = (0x0E, 0x03)
ROLAND = 0x41

from jdxi_editor.midi.fluidsynth_library import (  # noqa: E402
    import_error_message,
    prepare_fluidsynth_library,
)

_fluidsynth_err_msg = ""
prepare_fluidsynth_library()  # Windows: point the DLL search at FluidSynth
try:
    import fluidsynth as _fluidsynth_module
except Exception as _fluidsynth_err:  # pragma: no cover - depends on the system
    _fluidsynth_module = None
    _fluidsynth_err_msg = str(_fluidsynth_err)


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


def list_audio_outputs() -> list[tuple[str, str]]:
    """(name, device spec) of the audio outputs; sounddevice imported only here."""
    try:
        import sounddevice
    except Exception:
        return []
    devices = sounddevice.query_devices()
    hostapis = sounddevice.query_hostapis()
    result = []
    for index, device in enumerate(devices):
        if device["max_output_channels"] <= 0:
            continue
        name = device["name"]
        if sys.platform == "darwin":
            result.append((name, name))
        else:
            api = hostapis[device.get("hostapi", 0)].get("name", "Unknown")
            result.append((f"{name} ({api})", f"{index}:{api}:{name}"))
    return result


def find_soundfonts(folder: str = SF2_DIR) -> list[str]:
    found = []
    if os.path.isdir(folder):
        for root, _dirs, files in os.walk(folder):
            found += [os.path.join(root, f) for f in files if f.lower().endswith((".sf2", ".sf3"))]
    return sorted(found)


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
    """Ports of the JD-Xi, connection test, and the optional FluidSynth."""

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
        self.fs = getattr(midi_helper, "soundfont_synth", None)
        self.sfid = getattr(midi_helper, "soundfont_sfid", None)
        self._identity_timer = QTimer(self)
        self._identity_timer.setSingleShot(True)
        self._identity_timer.timeout.connect(self._identity_timed_out)
        self._listening = False
        self._synth_loaded = False
        self._busy_synth = False
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
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        # Room for three lines, so a longer message does not get cut
        self.status_label.setMinimumHeight(self.status_label.fontMetrics().lineSpacing() * 3)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
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

        # --- FluidSynth, closed unless already in use
        self.synth_box = QGroupBox(tr("Listen without the JD-Xi (FluidSynth)"))
        self.synth_box.setCheckable(True)
        self.synth_box.setChecked(self.fs is not None)
        self.synth_box.toggled.connect(self._on_synth_box_toggled)
        synth_outer = QVBoxLayout(self.synth_box)
        self.synth_panel = QWidget()
        synth_layout = QFormLayout(self.synth_panel)
        synth_layout.setContentsMargins(0, 0, 0, 0)

        self.hardware_interface_combo = QComboBox()
        self.hardware_interface_combo.addItem(tr("Default output"), "")
        self.hardware_interface_combo.setToolTip(
            tr("Audio output for FluidSynth (needs the sounddevice package)")
        )
        synth_layout.addRow(tr("Audio output:"), self.hardware_interface_combo)

        sf_row = QHBoxLayout()
        self.sf2_combo = QComboBox()
        self.sf2_combo.setToolTip(tr("SoundFonts found in {folder}").format(folder=SF2_DIR))
        self.sf2_combo.currentIndexChanged.connect(self._on_sf2_combo_changed)
        self.browse_button = QPushButton(tr("Choose…"))
        self.browse_button.clicked.connect(self._browse_sf2)
        sf_row.addWidget(self.sf2_combo, 1)
        sf_row.addWidget(self.browse_button)
        synth_layout.addRow(tr("SoundFont:"), sf_row)
        self.sf2_edit = QLineEdit()  # the chosen file; shown as the combo's text
        self.sf2_edit.setVisible(False)

        self.use_soundfont_list = QCheckBox(tr("Show the SoundFont's presets in the preset lists"))
        self.use_soundfont_list.setToolTip(
            tr(
                "List the SoundFont's presets in the Digital, Analog and Drums preset "
                "lists (and GM percussion names in the Pattern editor) instead of the "
                "JD-Xi presets. Needs the sf2utils package."
            )
        )
        JDXi.UI.Theme.apply_button_mini_style(self.use_soundfont_list)  # visible tick box
        self.use_soundfont_list.setChecked(get_use_soundfont_list())
        self.use_soundfont_list.toggled.connect(self._on_soundfont_list_toggled)
        synth_layout.addRow("", self.use_soundfont_list)

        synth_buttons = QHBoxLayout()
        self.fs_start_btn = QPushButton(tr("Start"))
        self.fs_start_btn.clicked.connect(self._start_fluidsynth)
        self.fs_stop_btn = QPushButton(tr("Stop"))
        self.fs_stop_btn.clicked.connect(self._stop_fluidsynth)
        self.fs_test_btn = QPushButton(tr("Test note"))
        self.fs_test_btn.clicked.connect(self._test_fluidsynth)
        for button in (self.fs_start_btn, self.fs_stop_btn, self.fs_test_btn):
            synth_buttons.addWidget(button)
        synth_buttons.addStretch()
        synth_layout.addRow("", synth_buttons)
        self.fs_status = QLabel("")
        self.fs_status.setWordWrap(True)
        synth_layout.addRow("", self.fs_status)
        synth_outer.addWidget(self.synth_panel)
        self.synth_panel.setVisible(self.synth_box.isChecked())
        layout.addWidget(self.synth_box)

        # --- OK / Cancel (Qt translates the standard buttons)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)

        self._update_synth_buttons()
        if self.synth_box.isChecked():
            QTimer.singleShot(0, self, self._load_synth_choices)

    # ------------------------------------------------------------------ status
    def _set_status(self, kind: str, text: str) -> None:
        colours = {"ok": "#3cc98a", "busy": "#f2c94c", "error": "#f0483e", "idle": "#8a8d94"}
        self.status_dot.setStyleSheet(f"color: {colours.get(kind, '#8a8d94')}; font-size: 16px;")
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

    # -------------------------------------------------------------- FluidSynth
    def _on_synth_box_toggled(self, checked: bool) -> None:
        self.synth_panel.setVisible(checked)
        self.adjustSize()
        if checked and not self._synth_loaded:
            self._load_synth_choices()

    def _load_synth_choices(self) -> None:
        """Audio outputs and SoundFonts, listed in the background once."""
        self._synth_loaded = True
        self.fs_status.setText(tr("Looking for audio outputs and SoundFonts…"))
        run_in_background(
            lambda: (list_audio_outputs(), find_soundfonts()), self._synth_choices_loaded, self
        )

    def _synth_choices_loaded(self, result, error) -> None:
        self.fs_status.setText("")
        if error is not None:
            self.fs_status.setText(tr("Could not list the audio outputs: {error}").format(error=error))
            return
        outputs, soundfonts = result
        saved = get_hardware_interface()
        for name, spec in outputs:
            self.hardware_interface_combo.addItem(name, spec)
        index = self.hardware_interface_combo.findText(saved) if saved else -1
        self.hardware_interface_combo.setCurrentIndex(max(index, 0))
        if not outputs:
            self.hardware_interface_combo.setToolTip(
                tr("No audio outputs listed: install sounddevice (pip install sounddevice)")
            )
        chosen = get_sf2_path() or (SF2_PATH if os.path.isfile(SF2_PATH) else "")
        self.sf2_combo.blockSignals(True)
        for path in soundfonts:
            self.sf2_combo.addItem(os.path.basename(path), path)
        if chosen and self.sf2_combo.findData(chosen) < 0:
            self.sf2_combo.addItem(os.path.basename(chosen), chosen)
        if not self.sf2_combo.count():
            self.sf2_combo.addItem(tr("None found: Choose… a .sf2 file"), "")
        self.sf2_combo.setCurrentIndex(max(self.sf2_combo.findData(chosen), 0))
        self.sf2_combo.blockSignals(False)
        self.sf2_edit.setText(self.sf2_combo.currentData() or "")
        self._update_synth_buttons()

    def _on_sf2_combo_changed(self, _index: int) -> None:
        path = self.sf2_combo.currentData() or ""
        self.sf2_edit.setText(path)
        if path:
            set_sf2_path(path)
        self._update_synth_buttons()

    def _browse_sf2(self) -> None:
        start = SF2_DIR if os.path.isdir(SF2_DIR) else ""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Select SoundFont"), start, tr("SoundFonts (*.sf2 *.sf3)")
        )
        if not path:
            return
        if self.sf2_combo.findData(path) < 0:
            self.sf2_combo.addItem(os.path.basename(path), path)
        self.sf2_combo.setCurrentIndex(self.sf2_combo.findData(path))

    def _update_synth_buttons(self) -> None:
        running = getattr(self.midi_helper, "soundfont_synth", None) is not None
        has_file = bool(self.sf2_edit.text().strip())
        self.fs_start_btn.setEnabled(not self._busy_synth and not running and has_file)
        self.fs_stop_btn.setEnabled(not self._busy_synth and running)
        self.fs_test_btn.setEnabled(not self._busy_synth and running)

    def _start_fluidsynth(self) -> None:
        if _fluidsynth_module is None:
            self.fs_status.setText(import_error_message(_fluidsynth_err_msg))
            return
        sf_path = self.sf2_edit.text().strip()
        if not sf_path or not os.path.isfile(sf_path):
            self.fs_status.setText(tr("Please select a SoundFont first."))
            return
        device = self.hardware_interface_combo.currentData() or ""
        self._busy_synth = True
        self._update_synth_buttons()
        self.fs_status.setText(tr("Starting FluidSynth and loading the SoundFont…"))

        def start():
            fs = _fluidsynth_module.Synth()
            if sys.platform == "darwin":
                if device:
                    fs.setting("audio.coreaudio.device", device)
                fs.start(driver="coreaudio")
            elif device and ":" in device:
                fs.setting("audio.portaudio.device", device)
                fs.start(driver="portaudio")
            else:
                fs.start()
            sfid = fs.sfload(sf_path)
            fs.program_select(0, sfid, 0, 0)
            return fs, sfid

        run_in_background(start, self._fluidsynth_started, self)

    def _fluidsynth_started(self, result, error) -> None:
        self._busy_synth = False
        if error is not None:
            log.error(f"FluidSynth error: {error}", scope="MIDIConfigDialog")
            self.fs_status.setText(tr("FluidSynth error: {ex}").format(ex=error))
        else:
            self.fs, self.sfid = result
            self.midi_helper.soundfont_synth = self.fs
            self.midi_helper.soundfont_sfid = self.sfid
            self.fs_status.setText(tr("FluidSynth: started"))
        self._update_synth_buttons()

    def _stop_fluidsynth(self) -> None:
        fs = getattr(self.midi_helper, "soundfont_synth", None)
        try:
            if fs is not None:
                fs.delete()
            self.fs_status.setText(tr("FluidSynth: stopped"))
        except Exception as ex:
            self.fs_status.setText(tr("Stop error: {ex}").format(ex=ex))
        self.midi_helper.soundfont_synth = None
        self.midi_helper.soundfont_sfid = None
        self.fs = self.sfid = None
        self._update_synth_buttons()

    def _test_fluidsynth(self) -> None:
        fs = getattr(self.midi_helper, "soundfont_synth", None)
        if fs is None:
            self.fs_status.setText(tr("Start FluidSynth first."))
            return
        fs.noteon(0, 60, 110)
        QTimer.singleShot(400, self, lambda: fs.noteoff(0, 60))  # a short note, no wait
        self.fs_status.setText(tr("Test note triggered."))

    def _on_soundfont_list_toggled(self, checked: bool) -> None:
        set_use_soundfont_list(checked)
        problem = soundfont_list_problem() if checked else None
        if problem:
            log.warning(scope="MIDIConfigDialog", message=f"SoundFont list unavailable: {problem}")
            QMessageBox.warning(
                self,
                tr("SoundFont List"),
                tr("{problem}\n\nThe preset lists will stay as JD-Xi until this is fixed.").format(
                    problem=problem
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
        set_use_soundfont_list(self.use_soundfont_list.isChecked())
        if self.sf2_edit.text().strip():
            set_sf2_path(self.sf2_edit.text().strip())
        if self._synth_loaded:
            index = self.hardware_interface_combo.currentIndex()
            set_hardware_interface(self.hardware_interface_combo.currentText() if index > 0 else "")
        self._stop_listening()
        changed = self._ports_changed()
        super().accept()
        if changed:
            self._apply_ports()  # after the dialog has closed

    def reject(self) -> None:
        self._stop_listening()
        super().reject()
