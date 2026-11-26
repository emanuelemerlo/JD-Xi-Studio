"""
Playback options for the MIDI file player: loop (whole song or A–B),
playback speed, MIDI clock out and snap-to-bar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
)

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.ui.editors.helpers.widgets import (
    create_jdxi_button_from_spec,
    create_jdxi_row,
)
from jdxi_editor.ui.editors.midi_player.keyboard_feed import KEYBOARD_PARTS
from jdxi_editor.ui.editors.midi_player.keyboard_feed import SETTING as KEYBOARD_SETTING
from jdxi_editor.ui.editors.midi_player.utils import format_time
from jdxi_editor.ui.widgets.editor.helper import create_group_with_layout
from jdxi_editor.ui.widgets.jdxi.midi_group import JDXiMidiGroup
from picomidi.ui.widget.transport.spec import TransportSpec
from jdxi_editor.i18n import tr

if TYPE_CHECKING:
    from jdxi_editor.ui.editors.midi_player.editor import MidiFilePlayer

def _saved_keyboard_channel() -> Optional[int]:
    from jdxi_editor.project import __organization_name__, __program__

    try:
        value = int(QSettings(__organization_name__, __program__).value(KEYBOARD_SETTING, -1))
    except (TypeError, ValueError):
        return None
    return value if value in KEYBOARD_PARTS else None


SPEED_PERCENT_MIN = 25
SPEED_PERCENT_MAX = 200
SPEED_PERCENT_STEP = 5


class PlaybackOptionsWidget(JDXiMidiGroup):
    """Loop, A–B points, speed, MIDI clock and snap controls."""

    def __init__(self, parent: "MidiFilePlayer"):
        super().__init__(parent=parent, midi_state=None)
        self.loop_button: Optional[QPushButton] = None
        self.loop_label: Optional[QLabel] = None
        self.speed_spin: Optional[QSpinBox] = None
        self.clock_checkbox: Optional[QCheckBox] = None
        self.snap_checkbox: Optional[QCheckBox] = None
        self.keyboard_combo: Optional[QComboBox] = None
        self.setup_ui()

    def _build_button_specs(self) -> dict:
        return {}

    def _build_transport_specs(self) -> dict[str, TransportSpec]:
        return {
            "loop": TransportSpec(
                label="Loop",
                icon="mdi.repeat",
                tooltip=tr("Loop the A–B range, or the whole song if none is set (L)"),
                slot=self.parent.midi_loop_toggled,
                name="loop",
                text="Loop",
            ),
            "loop_a": TransportSpec(
                label="Set A",
                icon="mdi.alpha-a-box-outline",
                tooltip=tr("Set the loop start to the playback position"),
                slot=self.parent.midi_loop_set_a,
                checkable=False,
                name="loop_a",
                text="A",
            ),
            "loop_b": TransportSpec(
                label="Set B",
                icon="mdi.alpha-b-box-outline",
                tooltip=tr("Set the loop end to the playback position (turns Loop on)"),
                slot=self.parent.midi_loop_set_b,
                checkable=False,
                name="loop_b",
                text="B",
            ),
            "loop_clear": TransportSpec(
                label="Clear A–B",
                icon="mdi.repeat-off",
                tooltip=tr("Clear the A–B range so Loop repeats the whole song"),
                slot=self.parent.midi_loop_clear,
                checkable=False,
                name="loop_clear",
                text="Clear",
            ),
            "trim": TransportSpec(
                label="Trim",
                icon="mdi.content-cut",
                tooltip=tr("Keep only part of the file (the A–B range, if set); "
                "right-click a track to trim just that track"),
                slot=self.parent.midi_trim_file,
                checkable=False,
                name="trim",
                text="Trim",
            ),
        }

    def _build_group(self) -> QGroupBox:
        group, layout = create_group_with_layout("Playback", vertical=False)
        for spec in self.specs["transport"].values():
            button = create_jdxi_button_from_spec(spec, checkable=spec.checkable)
            setattr(self, f"{spec.name}_button", button)
            layout.addWidget(button)
            pixmap = JDXi.UI.Icon.get_icon_pixmap(
                spec.icon, color=JDXi.UI.Style.FOREGROUND, size=20
            )
            label_row, _ = create_jdxi_row(spec.text, icon_pixmap=pixmap)
            layout.addWidget(label_row)

        self.loop_label = QLabel()
        self.loop_label.setStyleSheet(JDXi.UI.Style.STYLE_FOREGROUND)
        layout.addWidget(self.loop_label)
        self.set_loop_points(None, None)

        options = QHBoxLayout()
        speed_label = QLabel(tr("Speed"))
        speed_label.setStyleSheet(JDXi.UI.Style.STYLE_FOREGROUND)
        options.addWidget(speed_label)
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(SPEED_PERCENT_MIN, SPEED_PERCENT_MAX)
        self.speed_spin.setSingleStep(SPEED_PERCENT_STEP)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix(" %")
        self.speed_spin.setToolTip(tr("Playback speed (pitch is unchanged)"))
        self.speed_spin.valueChanged.connect(self.parent.on_playback_speed_changed)
        options.addWidget(self.speed_spin)

        self.snap_checkbox = QCheckBox(tr("Snap to bar"))
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.setToolTip(
            tr("Snap loop points and inserted or moved Program Changes to the nearest bar line")
        )
        JDXi.UI.Theme.apply_button_mini_style(self.snap_checkbox)
        options.addWidget(self.snap_checkbox)

        self.clock_checkbox = QCheckBox(tr("Send MIDI Clock"))
        self.clock_checkbox.setChecked(False)
        self.clock_checkbox.setToolTip(
            tr("Send MIDI Clock, Start/Stop/Continue and Song Position so the JD-Xi "
            "arpeggio and tempo-synced effects follow the file.\n"
            "Note: if the JD-Xi Sync setting is MIDI or AUTO, Start also starts "
            "its pattern sequencer.")
        )
        JDXi.UI.Theme.apply_button_mini_style(self.clock_checkbox)
        self.clock_checkbox.toggled.connect(self.parent.on_send_clock_toggled)
        options.addWidget(self.clock_checkbox)

        # the notes of a part of the file on the main window's keyboard
        keyboard_label = QLabel(tr("Keyboard"))
        keyboard_label.setStyleSheet(JDXi.UI.Style.STYLE_FOREGROUND)
        options.addWidget(keyboard_label)
        self.keyboard_combo = QComboBox()
        self.keyboard_combo.addItem(tr("Off"), -1)
        for channel, name in KEYBOARD_PARTS.items():
            self.keyboard_combo.addItem(tr(name), channel)
        self.keyboard_combo.setToolTip(
            tr("Show the notes this part of the file plays on the keyboard of the main window, "
               "in the part's colour (the keys that play them at the part's octave; a triangle on "
               "the first or last key: notes beyond the 37 keys)")
        )
        saved = _saved_keyboard_channel()
        index = self.keyboard_combo.findData(-1 if saved is None else saved)
        self.keyboard_combo.setCurrentIndex(max(0, index))
        self.keyboard_combo.currentIndexChanged.connect(
            lambda _i: self.parent.on_keyboard_part_changed(self.keyboard_channel)
        )
        options.addWidget(self.keyboard_combo)
        layout.addLayout(options)
        return group

    @property
    def keyboard_channel(self) -> Optional[int]:
        """The part shown on the keyboard (0-based channel), or None."""
        if self.keyboard_combo is None:
            return None
        data = self.keyboard_combo.currentData()
        return None if data is None or int(data) < 0 else int(data)

    @property
    def snap_to_bar(self) -> bool:
        return bool(self.snap_checkbox and self.snap_checkbox.isChecked())

    def set_loop_checked(self, enabled: bool) -> None:
        """Show the loop state without triggering the button's slot."""
        self.loop_button.blockSignals(True)
        self.loop_button.setChecked(enabled)
        self.loop_button.blockSignals(False)

    def set_loop_points(self, a: Optional[float], b: Optional[float]) -> None:
        """Describe the current A/B points."""
        if a is not None and b is not None:
            text = f"A–B {format_time(a)}–{format_time(b)}"
        elif a is not None:
            text = f"A {format_time(a)} (set B)"
        elif b is not None:
            text = f"B {format_time(b)} (set A)"
        else:
            text = tr("Whole song")
        self.loop_label.setText(text)
