"""
Mute Channels group - 16 channel mute buttons and, under them, 16 solo buttons.

Solo is the other way round from mute: with one or more channels soloed only
those play. A channel silenced by another one's solo is dimmed without being
muted itself, so un-soloing restores the mutes as they were.

Each channel is a narrow column, as on a mixer: its number, M, S.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QPushButton

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.midi.playback.state import MidiPlaybackState
from jdxi_editor.ui.editors.helpers.widgets import create_small_sequencer_square_for_channel
from jdxi_editor.ui.widgets.editor.helper import create_group_with_layout
from jdxi_editor.ui.widgets.jdxi.midi_group import JDXiMidiGroup
from picoui.specs.widgets import ButtonSpec
from jdxi_editor.i18n import tr
from jdxi_editor.ui.style.editor_style import repolish

# the channels the JD-Xi's parts play (1-based)
JDXI_PART_CHANNELS = {1: "Digital 1", 2: "Digital 2", 3: "Analog", 10: "Drums"}

if TYPE_CHECKING:
    from jdxi_editor.ui.editors.midi_player.editor import MidiFilePlayer


class MuteChannelsGroup(JDXiMidiGroup):
    """Mute Channels group: 16 channel mute buttons and 16 solo buttons."""

    def __init__(
        self,
        parent: "MidiFilePlayer",
        midi_state: MidiPlaybackState | None = None,
    ):
        super().__init__(parent=parent, midi_state=midi_state)
        self.mute_channel_buttons: dict[int, QPushButton] = {}
        self.solo_channel_buttons: dict[int, QPushButton] = {}
        self.setup_ui()

    def _build_group(self) -> QGroupBox:
        """Build the group: per channel a column with its number, Mute (M) and Solo (S)."""
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        mute_style = JDXi.UI.MidiPlayer.channel_mute_stylesheet()
        solo_style = JDXi.UI.MidiPlayer.channel_solo_stylesheet()
        number_style = JDXi.UI.MidiPlayer.channel_number_stylesheet()
        self.channel_labels: dict[int, QLabel] = {}
        for ch in range(1, 17):
            part = ch in JDXI_PART_CHANNELS  # the channels the JD-Xi plays
            label = QLabel(str(ch))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setProperty("part", part)
            label.setStyleSheet(number_style)
            mute = create_small_sequencer_square_for_channel(ch)
            mute.setText("M")
            mute.setCheckable(True)
            mute.setChecked(False)
            mute.setToolTip(self._tooltip(ch, unused=False))
            mute.setProperty("part", part)
            mute.setProperty("silenced", False)
            mute.setStyleSheet(mute_style)
            mute.toggled.connect(
                lambda checked, c=ch, b=mute: self._on_mute_toggled(c, checked, b)
            )
            solo = create_small_sequencer_square_for_channel(ch)
            solo.setText("S")
            solo.setCheckable(True)
            solo.setChecked(False)
            solo.setToolTip(self._solo_tooltip(ch))
            solo.setProperty("part", part)
            solo.setStyleSheet(solo_style)
            solo.toggled.connect(lambda checked, c=ch: self._on_solo_toggled(c, checked))
            label.setToolTip(self._tooltip(ch, unused=False).split(":", 1)[-1].strip())
            self.channel_labels[ch] = label
            self.mute_channel_buttons[ch] = mute
            self.solo_channel_buttons[ch] = solo
            column = ch - 1
            grid.addWidget(label, 0, column, Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(mute, 1, column, Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(solo, 2, column, Qt.AlignmentFlag.AlignCenter)
        grid.setColumnStretch(16, 1)  # the columns side by side, on the left
        group, _ = create_group_with_layout(label="Mute Channels", layout=grid)
        return group

    def _on_mute_toggled(self, channel: int, checked: bool, button: QPushButton) -> None:
        self.parent._toggle_channel_mute(channel, checked, button)
        self.show_silenced()

    def _on_solo_toggled(self, channel: int, checked: bool) -> None:
        self.parent._toggle_channel_solo(channel, checked)
        self.show_silenced()

    def soloed_channels(self) -> set[int]:
        """The channels whose Solo is on (1-16)."""
        return {ch for ch, btn in self.solo_channel_buttons.items() if btn.isChecked()}

    def set_soloed_channels(self, channels: set[int]) -> None:
        """Show *channels* as soloed without telling the player (it already knows)."""
        for ch, btn in self.solo_channel_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(ch in channels)
            btn.blockSignals(False)
        self.show_silenced()

    def show_silenced(self) -> None:
        """Dim the channels another channel's solo silences (their own mute stays as it was)."""
        soloed = self.soloed_channels()
        for ch, btn in self.mute_channel_buttons.items():
            silenced = bool(soloed) and ch not in soloed and not btn.isChecked()
            for widget in (btn, self.channel_labels[ch]):
                if widget.property("silenced") != silenced:
                    widget.setProperty("silenced", silenced)
                    repolish(widget)

    def set_used_channels(self, channels: set[int]) -> None:
        """
        Dim the buttons of channels the file has no notes or controllers on.

        :param channels: 1-16 channels that are used
        """
        for ch, btn in self.mute_channel_buttons.items():
            unused = ch not in channels
            btn.setProperty("unused", unused)
            btn.setToolTip(self._tooltip(ch, unused))
            repolish(btn)
            label = self.channel_labels[ch]
            label.setProperty("unused", unused)
            repolish(label)
            solo = self.solo_channel_buttons[ch]
            solo.setProperty("unused", unused)
            solo.setToolTip(self._solo_tooltip(ch) + (" " + tr("(not used in this file)") if unused else ""))
            repolish(solo)

    @staticmethod
    def _tooltip(ch: int, unused: bool) -> str:
        part = JDXI_PART_CHANNELS.get(ch)
        text = (tr("Mute channel {ch}: {part}").format(ch=ch, part=tr(part)) if part
                else tr("Mute channel {ch}: no JD-Xi part plays it").format(ch=ch))
        return text + (" " + tr("(not used in this file)") if unused else "")

    @staticmethod
    def _solo_tooltip(ch: int) -> str:
        part = JDXI_PART_CHANNELS.get(ch)
        name = tr(part) if part else tr("no JD-Xi part plays it")
        return tr("Solo channel {ch} ({part}): only the soloed channels play, the others are silenced").format(
            ch=ch, part=name)

    def _build_button_specs(self) -> dict[str, ButtonSpec]:
        """No buttons in this group (uses dynamic channel buttons)."""
        return {}
