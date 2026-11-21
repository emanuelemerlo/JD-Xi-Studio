"""
Pattern and MIDI file player in the new look: the same editors (sequencer,
learning, transport, track classification, automation, USB recorder), restyled.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QAbstractButton,
    QPushButton,
    QApplication,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.ui.editors.midi_player import editor as _player
from jdxi_editor.ui.editors.pattern import pattern as _pattern
from jdxi_editor.ui.v2.restyle import flatten_round_buttons, restyle, title_badge
from jdxi_editor.ui.v2 import density

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
    if note and density.compact():
        box.setToolTip(note)  # a low screen: the explanation on the pointer, not under the card
    elif note:
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


class _HelpOnHover(QObject):
    """The control under the pointer is explained in the editor's side panel."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def eventFilter(self, watched, event):  # noqa: N802 (Qt name)
        if event.type() == QEvent.Type.Enter and isinstance(watched, QWidget):
            try:
                if self.editor.isVisible() and self.editor.isAncestorOf(watched):
                    self.editor.explain(watched)
            except RuntimeError:  # the editor is gone
                pass
        return False


class PatternSequenceEditor(_pattern.PatternSequenceEditor):
    ACCENT = PATTERN_ACCENT
    """The pattern sequencer with the new editors' look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pattern_style()
        QTimer.singleShot(0, self, self._pattern_style)  # after the base class's own pass

    def _pattern_style(self) -> None:
        restyle(self, PATTERN_ACCENT)
        # Play, Stop, Pause, Shuffle at one width (they stretched with the
        # window while Tap and the rest kept theirs); after restyle, which
        # sizes every button to its own text
        buttons = [b for b in (getattr(self, name, None) for name in
                               ("play_button", "stop_button", "pause_button", "shuffle_button")) if b]
        if buttons:
            width = max([b.sizeHint().width() for b in buttons] + [96])
            for button in buttons:
                button.setFixedWidth(width)

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
        buttons.setColumnStretch(2, 1)  # the room left goes after them
        self.pattern_transport.hide()  # its buttons are in the card; it keeps their state
        controls = QVBoxLayout()
        controls.setSpacing(8)
        controls.addLayout(buttons)
        controls.addLayout(_line(self.tempo_label, self.tempo_spinbox, tap))
        controls.addLayout(_line(QLabel(tr("Steps:")), self.beats_per_measure_combo))
        self.digital_title.setFixedWidth(240 if density.narrow() else 300)
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
            note=tr("The pattern is saved as a standard MIDI file: open it in the MIDI Player or in a DAW."),
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
        if density.very_narrow():  # a narrow screen: the two small cards one above the other
            column = QVBoxLayout()
            column.setSpacing(12)
            column.addWidget(new_steps)
            column.addWidget(measures)
            first.addLayout(column, 3)
        else:
            first.addWidget(new_steps, 2)
            first.addWidget(measures, 3)
        last = QHBoxLayout()
        last.setSpacing(12)
        last.addWidget(files, 1)
        last.addWidget(recorder, 2)
        self.layout.setSpacing(12)
        badge = QHBoxLayout()
        badge.addWidget(title_badge(tr("Pattern"), PATTERN_ACCENT))
        badge.addStretch()
        self.layout.addLayout(badge)
        self.layout.addLayout(first)
        self.layout.addWidget(self.sequencer_group)
        self.layout.addLayout(last)

        self.row_map = {
            0: self.digital1_selector,
            1: self.digital2_selector,
            2: self.analog_selector,
            3: self.drum_selector,
        }
        # the side panel, as in the other editors: what the control under the pointer does
        from jdxi_editor.ui.v2.widgets import InfoPanel

        self.info_panel = InfoPanel(PATTERN_ACCENT)
        self.info_panel.setFixedWidth(density.side_width(320))
        self.info_panel.show_text(
            tr("Pattern"),
            tr("Point at a control"),
            tr("Its name and what it does appear here."),
        )
        self._help = {}
        helps = (
            (self.play_button, tr("Play"), tr("Plays the pattern from the first measure, over and over; the steps light up as they play.")),
            (self.stop_button, tr("Stop"), tr("Stops and goes back to the first step.")),
            (self.pause_button, tr("Pause"), tr("Stops where it is: Play goes on from there.")),
            (self.shuffle_button, tr("Shuffle"), tr("Plays the measures in a random order.")),
            (self.tempo_spinbox, tr("BPM"), tr("The tempo, in beats per minute.")),
            (tap, tr("Tap"), tr("Click it in time a few times: the tempo follows your clicks.")),
            (self.beats_per_measure_combo, tr("Steps"), tr("Steps per measure: 16 (sixteenths) or 12 (triplets).")),
            (self.velocity_spinbox, tr("Velocity"), tr("How hard the steps you switch on are played (1-127).")),
            (self.duration_combo, tr("Duration"), tr("How long the notes of the steps you switch on last.")),
            (add_measure, tr("Add measure"), tr("Adds a measure after the last one (a copy of the previous one if that box is ticked).")),
            (copy_previous, tr("Copy previous measure"), tr("New measures start as a copy of the one before.")),
            (copy, tr("Copy section"), tr("Copies the steps from..to of the selected measure.")),
            (paste, tr("Paste section"), tr("Pastes the copied steps into the selected measure.")),
            (self.digital1_selector, tr("Digital Synth 1"), tr("The note the steps of this part play.")),
            (self.digital2_selector, tr("Digital Synth 2"), tr("The note the steps of this part play.")),
            (self.analog_selector, tr("Analog Synth"), tr("The note the steps of this part play.")),
            (self.drum_selector, tr("Drums"), tr("The drum sound (kick, snare, hi-hat...) the steps of this part play.")),
        )
        for widget, name, text in helps:
            if widget is not None:
                self._help[id(widget)] = (name, text)
        for button in self.mute_buttons:
            self._help[id(button)] = (tr("Mute"), tr("Silences this part while the pattern plays; its steps stay."))
        self._help_filter = _HelpOnHover(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self._help_filter)

        self.layout.addStretch()
        outer = QWidget()
        row = QHBoxLayout(outer)
        row.setContentsMargins(0, 0, 12, 12)
        row.setSpacing(12)
        row.addWidget(content, 1)
        side = QVBoxLayout()
        side.setContentsMargins(0, 12, 0, 0)
        side.addWidget(self.info_panel, 1)
        row.addLayout(side)
        self._container_layout.addWidget(outer)

    def _init_base_widget(self) -> None:
        """As the base class, but the content takes the whole width (it was centred, with margins)."""
        from jdxi_editor.ui.widgets.editor.base import EditorBaseWidget

        self.base_widget = EditorBaseWidget(parent=self, analog=False)
        self.base_widget.setup_scrollable_content(center_horizontally=False)
        self.base_widget.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._container_layout = self.base_widget.get_container_layout()
        if not hasattr(self, "main_layout") or self.main_layout is None:
            self.main_layout = QVBoxLayout(self)
            self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.base_widget)

    def explain(self, widget: QWidget) -> None:
        """Show in the side panel what *widget* (or the control it belongs to) does."""
        w = widget
        while w is not None and w is not self:
            entry = self._help.get(id(w))
            if entry is not None:
                self.info_panel.show_text(tr("Pattern"), *entry)
                return
            if self.pattern_widget is not None and self.pattern_widget.isAncestorOf(w) and isinstance(w, QAbstractButton) and not w.text():
                self.info_panel.show_text(
                    tr("Pattern"),
                    tr("Step"),
                    tr("Click to switch the step on or off; right-click lists its notes."),
                )
                return
            if w.toolTip():
                name = w.text().replace("&", "") if isinstance(w, QAbstractButton) and w.text() else tr("Control")
                self.info_panel.show_text(tr("Pattern"), name, w.toolTip())
                return
            if isinstance(w, QAbstractButton) and w.text():
                return  # a button with no explanation: keep the last one shown
            w = w.parentWidget()

    # The base class (re)applies its own style in these: the new look instead.
    def _apply_pattern_editor_style(self) -> None:
        restyle(self, PATTERN_ACCENT)

    def _init_style(self) -> None:
        restyle(self, PATTERN_ACCENT)


class MidiFilePlayer(_player.MidiFilePlayer):
    ACCENT = PLAYER_ACCENT
    """The MIDI file player with the new editors' look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_midi_player_style()
        QTimer.singleShot(0, self, self._apply_midi_player_style)

    def _apply_midi_player_style(self) -> None:
        restyle(self, PLAYER_ACCENT)
        self._equal_player_buttons()  # after restyle, which sizes each button to its text

    def _equal_player_buttons(self) -> None:
        """Play, Stop, Pause, Panic, Load, Save: one width, the widest text's."""
        buttons = [b for holder in (getattr(self, "transport", None), getattr(self, "midi_file_group", None))
                   if holder is not None for b in holder.findChildren(QPushButton) if b.text().strip()]
        if not buttons:
            return
        width = max([b.sizeHint().width() for b in buttons] + [96])
        for button in buttons:
            button.setFixedWidth(width)
        # one spacing for both rows, so Load / Save / Close sit under Play / Stop / Pause
        # (the transport's row had 10 px, the file's 5: the columns drifted apart)
        from PySide6.QtWidgets import QHBoxLayout

        for holder in (getattr(self, "transport", None), getattr(self, "midi_file_group", None)):
            if holder is not None:
                for row in holder.findChildren(QHBoxLayout):
                    row.setSpacing(10)

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
        # Play … Panic and Load / Save at one width, left-aligned (see
        # _equal_player_buttons): the transport stretched with the window
        # while Load and Save stayed small
        controls.addWidget(self.transport, 0, Qt.AlignmentFlag.AlignLeft)
        controls.addWidget(self.midi_file_group, 0, Qt.AlignmentFlag.AlignLeft)
        controls.addStretch()
        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.ui.digital_title_file_name, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(controls, 1)
        player = _card(tr("Player"), top)
        mute_label = QLabel(tr("Mute channels"))
        mute_label.setStyleSheet("color: #c9cbd1;")
        # what of the file the JD-Xi plays (the group's own summary line)
        classification = _card(
            tr("Fit to the JD-Xi"),
            self.classification_group,
            mute_label,
            self.mute_channels_group,
        )
        tracks = QGroupBox(tr("Tracks").upper())
        tracks_layout = QVBoxLayout(tracks)
        # more room for the tracks: Expand (hides the cards not needed while
        # listening) and a grip under the card (its height, remembered)
        from jdxi_editor.ui.v2.tracks_space import ExpandButton, TracksGrip

        self.tracks_expand_button = ExpandButton(lambda: self._hidden_while_expanded)
        expand_row = QHBoxLayout()
        expand_row.addStretch()
        expand_row.addWidget(self.tracks_expand_button)
        tracks_layout.addLayout(expand_row)
        tracks_layout.addWidget(self.midi_file)
        tracks_layout.addWidget(self.midi_file.midi_track_viewer, 1)
        tracks.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.midi_file.midi_track_viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tracks_card = tracks
        self.tracks_grip = TracksGrip(tracks)
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
        badge = QHBoxLayout()
        badge.addWidget(title_badge(tr("MIDI Player"), PLAYER_ACCENT))
        badge.addStretch()
        main.addLayout(badge)
        main.addLayout(first)
        main.addWidget(tracks, 1)
        main.addWidget(self.tracks_grip)
        main.addWidget(playback)
        main.addLayout(last)
        self._hidden_while_expanded = [classification, automation, recorder, events]

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
