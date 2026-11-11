"""
Settings: the JD-Xi's System parameters and the editor's own settings, tools
and files on one page.

Covers the MIDI Implementation tables System Common (02 00 00 00) and System
Controller (02 00 03 00); the rest (MIDI ports, preferences, patches, the
MIDI monitor...) opens the editor's existing windows.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QSizePolicy, QWidget

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.ui.v2.framework import Block, PSpec, V2Editor, rq1

ACCENT = "#a3a6ad"  # grey: the instrument and the editor, not a part
MI = tr("MIDI Implementation")


def _channel_text(v: int) -> str:
    return "OFF" if v >= 16 else str(v + 1)


def _channel_parse(text: str) -> Optional[int]:
    t = text.strip().upper()
    if t == "OFF":
        return 16
    return int(t) - 1 if t.isdigit() and 1 <= int(t) <= 16 else None


def settings_blocks() -> list[Block]:
    S = PSpec
    on_off = ("OFF", "ON")
    common = Block("SYSTEM_COMMON", "SYSTEM COMMON", JDXiSysExAddress(0x02, 0x00, 0x00, 0x00), [
        S("MASTER_TUNE", 0x00, "Master Tune", tr("Master Tune"),
          tr("Fine tuning of the whole instrument, in tenths of a cent: 0 is A4 = 440 Hz."),
          lo=-1000, hi=1000, raw_offset=1024, size=4, scale=10, unit="cent", signed=True, source=MI),
        S("MASTER_KEY_SHIFT", 0x04, "Key Shift", tr("Master Key Shift"),
          tr("Transposes the whole instrument by semitones."), lo=-24, hi=24, raw_offset=64, signed=True,
          unit="st", source=MI),
        S("MASTER_LEVEL", 0x05, "Master Level", tr("Master Level"), tr("Overall volume of the JD-Xi."), hi=127,
          source=MI),
        S("PROGRAM_CTRL_CH", 0x11, "Program Ctrl Ch", tr("Program Control Channel"),
          tr("MIDI channel on which program changes select programs (OFF: none)."), hi=16, fmt=_channel_text,
          parse=_channel_parse, source=MI),
        S("RX_PROGRAM_CHANGE", 0x29, "Rx Program Change", tr("Receive Program Change"),
          tr("Whether the JD-Xi follows program changes it receives."), hi=1, choices=on_off, source=MI),
        S("RX_BANK_SELECT", 0x2A, "Rx Bank Select", tr("Receive Bank Select"),
          tr("Whether the JD-Xi follows bank selects it receives."), hi=1, choices=on_off, source=MI),
    ], request=rq1([0x02, 0x00, 0x00, 0x00], 0x2B))
    controller = Block("SYSTEM_CONTROLLER", "CONTROLLER", JDXiSysExAddress(0x02, 0x00, 0x03, 0x00), [
        S("TRANSMIT_PROGRAM_CHANGE", 0x00, "Tx Program Change", tr("Transmit Program Change"),
          tr("Whether the JD-Xi sends a program change when you select a program."), hi=1, choices=on_off,
          source=MI),
        S("TRANSMIT_BANK_SELECT", 0x01, "Tx Bank Select", tr("Transmit Bank Select"),
          tr("Whether the JD-Xi sends a bank select with the program change."), hi=1, choices=on_off, source=MI),
        S("KEYBOARD_VELOCITY", 0x02, "Velocity", tr("Keyboard Velocity"),
          tr("REAL: as hard as you play; 1-127: always this velocity."), hi=127,
          fmt=lambda v: "REAL" if v == 0 else str(v),
          parse=lambda t: 0 if t.strip().upper() == "REAL" else (int(t) if t.strip().isdigit() else None),
          source=MI),
        S("KEYBOARD_VELOCITY_CURVE", 0x03, "Velocity Curve", tr("Keyboard Velocity Curve"),
          tr("How the keyboard responds to how hard you play: LIGHT needs less force for loud notes."),
          hi=2, raw_offset=1, choices=("LIGHT", "MEDIUM", "HEAVY"), source=MI),
        S("KEYBOARD_VELOCITY_CURVE_OFFSET", 0x04, "Curve Offset", tr("Keyboard Velocity Curve Offset"),
          tr("Fine adjustment of the velocity curve."), lo=-10, hi=9, raw_offset=64, signed=True, source=MI),
    ], request=rq1([0x02, 0x00, 0x03, 0x00], 0x11))
    for block in (common, controller):
        block.export = False  # instrument settings, not part of a patch
    return [common, controller]


class SettingsEditor(V2Editor):
    """The JD-Xi's system settings and the editor's settings, files and tools."""

    ACCENT = ACCENT

    def __init__(self, midi_helper=None, preset_helper=None, parent=None, instrument=None):
        self.instrument = instrument if instrument is not None else parent
        super().__init__(settings_blocks(), midi_helper=midi_helper, parent=parent, title=tr("Settings"))
        self.preset_helper = preset_helper
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_connection)
        self._timer.start(2000)
        self.update_connection()

    # --- the instrument's windows and actions

    def _action(self, name: str) -> Optional[Callable]:
        target = getattr(self.instrument, name, None)
        return target if callable(target) else None

    def _buttons(self, card, rows: list[tuple[str, str, str]]) -> dict[str, QPushButton]:
        """Buttons (text, explanation, instrument method) in two columns."""
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        out = {}
        for i, (text, note, method) in enumerate(rows):
            button = QPushButton(text)
            button.setToolTip(note)
            button.setMinimumWidth(170)
            slot = self._action(method)
            button.setEnabled(slot is not None)
            if slot is not None:
                button.clicked.connect(lambda _c=False, s=slot: s())
            label = QLabel(note)
            label.setWordWrap(True)
            label.setStyleSheet("color: #8b8e96; font-size: 11px; background: transparent;")
            grid.addWidget(button, i, 0)
            grid.addWidget(label, i, 1)
            out[method] = button
        grid.setColumnStretch(1, 1)
        card.body.addLayout(grid)
        return out

    def build_panels(self) -> None:
        s = self.spec
        self.panels_layout.setSpacing(12)

        midi = self.card(tr("MIDI CONNECTION"), tr("ports"))
        self.connection_label = QLabel()
        self.connection_label.setWordWrap(True)
        self.connection_label.setStyleSheet("color: #e6e6e6; font-size: 13px; background: transparent;")
        midi.body.addWidget(self.connection_label)
        self.buttons = self._buttons(midi, [
            (tr("MIDI ports…"), tr("Choose the JD-Xi's input and output"), "_show_midi_config"),
        ])
        note = QLabel(tr("Without the JD-Xi the editor works offline: changes are kept in the editor and saved to "
                         "files, and sent when it is connected."))
        note.setWordWrap(True)
        note.setStyleSheet("color: #8b8e96; font-size: 11px; background: transparent;")
        midi.body.addWidget(note)

        system = self.card(tr("SYSTEM COMMON"), tr("instrument · MIDI Implementation"))
        system.body.addLayout(self.knob_row([s("MASTER_TUNE"), s("MASTER_KEY_SHIFT"), s("MASTER_LEVEL")]))
        system.body.addWidget(self.control(s("PROGRAM_CTRL_CH")))
        system.body.addWidget(self.control(s("RX_PROGRAM_CHANGE")))
        system.body.addWidget(self.control(s("RX_BANK_SELECT")))

        controller = self.card(tr("CONTROLLER"), tr("keyboard · MIDI Implementation"))
        controller.body.addWidget(self.control(s("TRANSMIT_PROGRAM_CHANGE")))
        controller.body.addWidget(self.control(s("TRANSMIT_BANK_SELECT")))
        controller.body.addWidget(self.control(s("KEYBOARD_VELOCITY")))
        controller.body.addWidget(self.control(s("KEYBOARD_VELOCITY_CURVE")))
        controller.body.addWidget(self.control(s("KEYBOARD_VELOCITY_CURVE_OFFSET")))

        files = self.card(tr("FILES"), tr("import · export"))
        self.buttons.update(self._buttons(files, [
            (tr("Load patch…"), tr("Programs, tones and kits from a patch file"), "_patch_load"),
            (tr("Save patch…"), tr("The current program and tones to a file"), "_patch_save"),
            (tr("Send all to the JD-Xi"), tr("Every setting of the open editors"), "_dump_settings_to_synth"),
            (tr("Update user programs"), tr("Read the names of the E–H programs into the library"),
             "_update_user_program_database"),
        ]))

        tools = self.card(tr("EDITOR AND TOOLS"), tr("preferences · debug"))
        self.buttons.update(self._buttons(tools, [
            (tr("Preferences…"), tr("Language, startup and the editor's options"), "on_preferences"),
            (tr("Check for updates…"), tr("Look for a newer release on GitHub"), "on_check_for_updates"),
            (tr("MIDI monitor"), tr("Every MIDI message in and out"), "_show_midi_message_monitor"),
            (tr("SysEx debugger"), tr("Decode and send SysEx messages"), "_show_midi_debugger"),
            (tr("Log viewer"), tr("The editor's log"), "_show_log_viewer"),
        ]))

        top = QWidget()
        grid = QGridLayout(top)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        grid.addWidget(midi, 0, 0)
        grid.addWidget(system, 0, 1)
        grid.addWidget(controller, 0, 2)
        grid.addWidget(files, 1, 0, 1, 2)
        grid.addWidget(tools, 1, 2)
        for card in (midi, system, controller, files, tools):
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            card.body.addStretch()  # contents at the top
        for column in range(3):
            grid.setColumnStretch(column, 1)
        self.panels_layout.addWidget(top)
        self.panels_layout.addStretch()

    def update_connection(self) -> None:
        helper = self.midi_helper
        inp = bool(getattr(helper, "is_input_open", False))
        out = bool(getattr(helper, "is_output_open", False))
        in_name = getattr(helper, "in_port_name", "") or "—"
        out_name = getattr(helper, "out_port_name", "") or "—"
        color = "#6fcf97" if inp and out else ("#f2c94c" if inp or out else "#eb5757")
        state = tr("Connected") if inp and out else (tr("Half connected") if inp or out else tr("Offline"))
        label = getattr(self, "connection_label", None)
        if label is not None:
            label.setText(
                f"<span style='color:{color}'>●</span> <b>{state}</b><br>"
                f"{tr('Input')}: {in_name if inp else '—'}<br>{tr('Output')}: {out_name if out else '—'}"
            )
