"""
Pattern and MIDI file player in the new look: the same editors (sequencer,
learning, transport, track classification, automation, USB recorder), restyled.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.ui.editors.midi_player import editor as _player
from jdxi_editor.ui.editors.pattern import pattern as _pattern
from jdxi_editor.ui.v2.restyle import flatten_round_buttons, restyle

PATTERN_ACCENT = "#f2c94c"  # as in the mockup
PLAYER_ACCENT = "#3f8cff"


def _widgets(layout: QLayout) -> list[QWidget]:
    """The widgets of a layout, in order (taken out of it)."""
    out = []
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            out.append(item.widget())
    return out


def _card(title: str, *rows, note: str = "") -> QGroupBox:
    """A card: its rows (widgets or layouts) one under the other, and a note in grey."""
    box = QGroupBox(title.upper())
    layout = QVBoxLayout(box)
    layout.setSpacing(8)
    for row in rows:
        if isinstance(row, QLayout):
            layout.addLayout(row)
        else:
            layout.addWidget(row)
    if note:
        label = QLabel(note)
        label.setWordWrap(True)
        label.setStyleSheet("color: #8b8e96; font-size: 11px;")
        layout.addWidget(label)
    box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    return box


def _line(*widgets, stretch: bool = True) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(6)
    for widget in widgets:
        if isinstance(widget, str):
            label = QLabel(widget)
            label.setStyleSheet("color: #c9cbd1;")
            row.addWidget(label)
        else:
            row.addWidget(widget)
    if stretch:
        row.addStretch()
    return row


# Same class names as the editors they restyle: the main window finds open
# editors by class name (get_existing_editor), and isinstance() keeps working.


class PatternSequenceEditor(_pattern.PatternSequenceEditor):
    """The pattern sequencer with the new editors' look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restyle(self, PATTERN_ACCENT)
        QTimer.singleShot(0, self, lambda: restyle(self, PATTERN_ACCENT))  # after the base class's own pass

    def _setup_ui(self) -> None:
        """
        The cards of the mockup, with the editor's own widgets (same engine):

            TRANSPORT (display, play...)   | NEW STEPS | MEASURES
            STEP SEQUENCER (measures strip, the four parts, the steps)
            FILE                           | USB RECORDER
        """
        from jdxi_editor.ui.editors.pattern.preset_list_provider import (
            get_analog_options,
            get_digital_options,
            get_drum_options,
            get_preset_signals,
        )
        from jdxi_editor.ui.widgets.digital.title import DigitalTitle
        from jdxi_editor.ui.widgets.pattern_file_group import PatternFileGroup
        from jdxi_editor.ui.widgets.pattern.widget import PatternConfig, PatternWidget
        from jdxi_editor.ui.widgets.transport.transport import PatternTransportWidget

        self._init_base_widget()
        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.mute_buttons = []
        self.digital_options = get_digital_options()
        self.analog_options = get_analog_options()
        self.drum_options = get_drum_options()
        get_preset_signals().soundfont_list_changed.connect(self._refresh_preset_options)
        self.specs = self._build_specs()

        # --- the editor's widgets, as the original builds them
        self.pattern_file_group = PatternFileGroup(parent=self)
        self.drum_selector = self.pattern_file_group.drum_selector
        self._create_learn_group()
        self.pattern_transport = PatternTransportWidget(parent=self)
        self.play_button = self.pattern_transport.play_button
        self.stop_button = self.pattern_transport.stop_button
        self.pause_button = self.pattern_transport.pause_button
        self.shuffle_button = self.pattern_transport.shuffle_button
        self.digital_title = DigitalTitle(tone_name="New pattern", show_upper_text=True)
        toolbar = _widgets(self._create_toolbar_row())
        edit = _widgets(self._create_edit_row())
        # toolbar: BPM label, BPM, Tap, Steps label, Steps, Vel label, Vel, Dur label, Dur, USB toggle
        tap = self.tap_tempo_button.parentWidget()
        usb_toggle = self.usb_recorder_toggle.parentWidget()
        usb_toggle.hide()  # the recorder has its own card
        # edit: Add measure, copy previous, from label, from, "to", to, Copy, Paste
        add_measure, copy_previous, from_label, from_spin, to_label, to_spin, copy, paste = edit

        # --- the cards
        for group in (
            self.pattern_transport.findChildren(QGroupBox)
            + self.pattern_file_group.findChildren(QGroupBox)
            + self.usb_recorder.findChildren(QGroupBox)
        ):
            group.setTitle("")
            group.setFlat(True)
            group.setStyleSheet("QGroupBox { background: transparent; border: 0; margin: 0; padding: 0; }")
        # Play, Stop, Pause, Shuffle as flat buttons, two by two
        flatten_round_buttons(self.pattern_transport)
        buttons = QGridLayout()
        buttons.setSpacing(6)
        for i, button in enumerate((self.play_button, self.stop_button, self.pause_button, self.shuffle_button)):
            buttons.addWidget(button, i // 2, i % 2)
        self.pattern_transport.hide()  # its buttons are in the card; it keeps their state
        controls = QVBoxLayout()
        controls.setSpacing(8)
        controls.addLayout(buttons)
        controls.addLayout(_line(self.tempo_label, self.tempo_spinbox, tap))
        controls.addLayout(_line(QLabel(tr("Steps:")), self.beats_per_measure_combo))
        self.digital_title.setFixedWidth(300)
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.digital_title, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(controls)
        transport = _card(tr("Transport"), top)
        new_steps = _card(
            tr("New steps"),
            _line(self.velocity_label, self.velocity_spinbox),
            _line(self.duration_label, self.duration_combo),
            note=tr("Velocity and duration of the steps you switch on; the note is chosen beside each part."),
        )
        measures = _card(
            self.measure_name_plural,
            _line(add_measure, copy_previous),
            _line(from_label, from_spin, to_label, to_spin),
            _line(copy, paste),
            note=tr("Copy and paste a range of steps of the selected measure."),
        )
        files = _card(
            tr("File"),
            self.pattern_file_group,
            note=tr("The pattern is saved as a standard MIDI file: open it in the MIDI file player or in a DAW."),
        )
        self.usb_recorder.setVisible(True)
        recorder = _card(
            tr("USB Recorder"),
            self.usb_recorder,
            note=tr("Records what the JD-Xi plays over USB while you play the pattern."),
        )

        # --- the sequencer (as the original: measures strip, part headers, steps)
        self.pattern_widget = PatternWidget(
            config=PatternConfig(rows=4, steps_per_measure=self.measure_beats, initial_measures=1)
        )
        self.pattern_widget.set_header_widget(self._create_headers_widget())
        self.sequencer_group = QGroupBox(tr("Pattern Sequencer").upper())
        sequencer_layout = QVBoxLayout(self.sequencer_group)
        sequencer_layout.addWidget(self.pattern_widget)
        hint = QLabel(tr("Click a step to switch it on or off; the steps light up while the pattern plays."))
        hint.setStyleSheet("color: #8b8e96; font-size: 11px;")
        hint.setWordWrap(True)
        sequencer_layout.addWidget(hint)

        first = QHBoxLayout()
        first.setSpacing(12)
        first.addWidget(transport, 3)
        first.addWidget(new_steps, 2)
        first.addWidget(measures, 3)
        last = QHBoxLayout()
        last.setSpacing(12)
        last.addWidget(files, 1)
        last.addWidget(recorder, 2)
        self.layout.setSpacing(12)
        self.layout.addLayout(first)
        self.layout.addWidget(self.sequencer_group)
        self.layout.addLayout(last)

        self.row_map = {
            0: self.digital1_selector,
            1: self.digital2_selector,
            2: self.analog_selector,
            3: self.drum_selector,
        }
        self.layout.addStretch()
        self._container_layout.addWidget(content)

    # The base class (re)applies its own style in these: the new look instead.
    def _apply_pattern_editor_style(self) -> None:
        restyle(self, PATTERN_ACCENT)

    def _init_style(self) -> None:
        restyle(self, PATTERN_ACCENT)


class MidiFilePlayer(_player.MidiFilePlayer):
    """The MIDI file player with the new editors' look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restyle(self, PLAYER_ACCENT)
        QTimer.singleShot(0, self, lambda: restyle(self, PLAYER_ACCENT))

    def _apply_midi_player_style(self) -> None:
        restyle(self, PLAYER_ACCENT)

    def ui_init(self) -> None:
        """
        The cards of the mockup, with the player's own widgets (same engine):

            PLAYER (display, transport, file) | CLASSIFICATION (and mute channels)
            TRACKS (position, timeline, track lanes, zoom)
            PLAYBACK (loop, A/B, trim, speed...)
            AUTOMATION | USB RECORDER | EVENT FILTER
        """
        from jdxi_editor.ui.preset.source import PresetSource
        from jdxi_editor.ui.widgets.digital.title import DigitalTitle
        from jdxi_editor.ui.widgets.editor.base import EditorBaseWidget

        self.ui.digital_title_file_name = DigitalTitle(tone_name="No file loaded", show_upper_text=True)
        self.ui.digital_title_file_name.setFixedWidth(320)
        for holder in (
            self.transport,
            self.midi_file_group,
            self.event_suppression_group,
            self.classification_group,
            self.mute_channels_group,
            self.automation,
            self.usb_recorder,
            self.playback_options,
        ):
            for group in holder.findChildren(QGroupBox):
                group.setTitle("")
                group.setFlat(True)
                group.setStyleSheet("QGroupBox { background: transparent; border: 0; margin: 0; padding: 0; }")
        self.automation.populate_automation_programs(PresetSource.DIGITAL)

        controls = QVBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self.transport)
        controls.addWidget(self.midi_file_group)
        controls.addStretch()
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.ui.digital_title_file_name, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(controls, 1)
        player = _card(tr("Player"), top)
        mute_label = QLabel(tr("Mute channels"))
        mute_label.setStyleSheet("color: #c9cbd1;")
        classification = _card(
            tr("Classification"),
            self.classification_group,
            mute_label,
            self.mute_channels_group,
            note=tr("The JD-Xi plays four parts: the editor tells each track's role (drums, bass, keys, "
                    "strings) from its channel and notes and assigns it to a part."),
        )
        tracks = QGroupBox(tr("Tracks").upper())
        tracks_layout = QVBoxLayout(tracks)
        tracks_layout.addWidget(self.midi_file)
        tracks_layout.addWidget(self.midi_file.midi_track_viewer, 1)
        tracks.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.midi_file.midi_track_viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        playback = _card(tr("Playback"), self.playback_options)
        automation = _card(tr("Automation"), self.automation)
        recorder = _card(tr("USB Recorder"), self.usb_recorder)
        events = _card(
            tr("Event filter"),
            self.event_suppression_group,
            note=tr("Program changes (PC) and controllers (CC) of the file not sent to the JD-Xi."),
        )

        first = QHBoxLayout()
        first.setSpacing(12)
        first.addWidget(player, 3)
        first.addWidget(classification, 2)
        last = QHBoxLayout()
        last.setSpacing(12)
        last.addWidget(automation, 3)
        last.addWidget(recorder, 3)
        last.addWidget(events, 1)
        main = QVBoxLayout()
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)
        main.addLayout(first)
        main.addWidget(tracks, 1)
        main.addWidget(playback)
        main.addLayout(last)

        self.base_widget = EditorBaseWidget(parent=self, analog=False)
        self.base_widget.setup_scrollable_content(center_horizontally=False)
        content = QWidget()
        content.setLayout(main)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.base_widget.get_container_layout().addWidget(content, 1)
        self._add_base_widget_to_editor()
        self._apply_midi_player_style()


PatternEditor = PatternSequenceEditor
MidiPlayer = MidiFilePlayer
