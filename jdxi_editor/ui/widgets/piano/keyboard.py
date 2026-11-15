"""
Piano keyboard widget for JD-Xi Manager.

This module defines address PianoKeyboard widget, address custom QWidget that arranges and displays
address set of piano keys styled like those on address JD-Xi synthesizer. The widget combines both
white and black keys to form address complete piano keyboard, along with labels representing
drum pad names.

Key Features:
- **Custom Key Dimensions:** White and black keys are sized and positioned appropriately,
    with configurable widths and heights.
- **Dynamic Key Creation:** White keys are created first in address horizontal layout,
    while black keys are overlaid at specific positions.
- **Drum Pad Labels:** A row of labels is displayed above the keyboard to denote
    corresponding drum pad names.
- **Signal Integration:** Each key emits custom signals (noteOn and noteOff) to notify
    parent widgets of key events.
- **MIDI Channel Configuration:** The widget supports setting address MIDI channel for outgoing
    note messages.
- **Styling and Layout:** Uses QHBoxLayout and QVBoxLayout to manage key and label placement,
    ensuring address neat appearance.

Usage Example:
    from jdxi_editor.ui.widgets.piano.keyboard import PianoKeyboard
    keyboard = PianoKeyboard(parent=main_window)
    keyboard.set_midi_channel(1)
    main_window.setCentralWidget(keyboard)

This module requires PySide6 and proper integration with the JD-Xi Manager's signal handling for note events.
"""

from decologr import Decologr as log
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel

from jdxi_editor.midi.data.piano.keyboard import (
    DRUM_LABELS,
    KEYBOARD_BLACK_NOTES,
    KEYBOARD_WHITE_NOTES,
)
from jdxi_editor.ui.common import JDXi, QVBoxLayout, QWidget
from jdxi_editor.ui.widgets.piano.key import PianoKey


class PianoKeyboard(QWidget):
    """Widget containing a row of piano keys styled like JD-Xi"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.current_channel = 0  # Default to analog synth channel

        # Set keyboard dimensions
        self.white_key_width = 35
        # The keyboard is about 43 % of the JD-Xi's depth (InstrumentDimensions)
        self.white_key_height = 145
        self.black_key_width = int(self.white_key_width * 0.6)
        self.black_key_height = 90  # ~62 % of a white key, as on the JD-Xi

        # Define note patterns
        self.white_notes = KEYBOARD_WHITE_NOTES
        self.black_notes = KEYBOARD_BLACK_NOTES

        # Calculate total width
        total_width = len(self.white_notes) * self.white_key_width
        self.setFixedSize(
            total_width + 2, self.white_key_height + 30
        )  # Added height for labels

        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Drum names over their keys: each label centred on its key (black keys' names on the
        # upper line, white keys' on the lower one, so neighbours never overlap)
        main_layout.addWidget(self._drum_label_strip(total_width + 2))

        # Create keyboard container widget
        keyboard_widget = QWidget()
        keyboard_widget.setFixedSize(total_width + 2, self.white_key_height + 2)
        keyboard_layout = QHBoxLayout(keyboard_widget)
        keyboard_layout.setSpacing(0)
        keyboard_layout.setContentsMargins(1, 1, 1, 1)

        # Add shadow effect to keyboard widget
        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(10)
        shadow_effect.setOffset(5, 5)
        shadow_effect.setColor(QColor(0, 0, 0, 50))
        keyboard_widget.setGraphicsEffect(shadow_effect)

        # Create keys
        self._create_keys(keyboard_widget)

        main_layout.addWidget(keyboard_widget)

    BLACK_POSITIONS = [0, 1, 3, 4, 5, 7, 8, 10, 11, 12, 14, 15, 17, 18, 19]
    LABEL_WIDTH = 30

    def key_centres(self) -> dict[int, float]:
        """The x of each key's centre (MIDI note -> x), as the keys are laid out (1 px margin)."""
        centres = {}
        for index, note in enumerate(self.white_notes):
            centres[note] = 1 + index * self.white_key_width + self.white_key_width / 2
        for pos, note in zip(self.BLACK_POSITIONS, [n for n in KEYBOARD_BLACK_NOTES if n is not None]):
            centres[note] = 1 + pos * self.white_key_width + self.white_key_width
        return centres

    def _drum_label_strip(self, width: int) -> QWidget:
        strip = QWidget()
        strip.setFixedSize(width, 30)
        centres = self.key_centres()
        black = {n for n in KEYBOARD_BLACK_NOTES if n is not None}
        first = self.white_notes[0]  # BD1 is the first key (C1, note 36)
        self.drum_labels = {}
        for offset, text in enumerate(DRUM_LABELS):
            note = first + offset
            if not text.strip() or note not in centres:
                continue
            label = QLabel(text, strip)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(JDXi.UI.Style.KEYBOARD_DRUM_LABELS)
            label.setFixedSize(self.LABEL_WIDTH, 14)
            label.move(round(centres[note] - self.LABEL_WIDTH / 2), 1 if note in black else 15)
            self.drum_labels[note] = label
        self._label_strip = strip
        return strip

    def place_drum_labels(self) -> None:
        """Each name centred on its key as laid out (the layout can move the keys a little)."""
        strip = getattr(self, "_label_strip", None)
        if strip is None:
            return
        for note, label in self.drum_labels.items():
            key = self._keys_by_note.get(note)
            if key is None or key.width() <= 0:
                continue
            centre = key.mapTo(self, key.rect().center()).x() + 0.5
            x = strip.mapFrom(self, QPoint(round(centre), 0)).x()
            label.move(round(x - self.LABEL_WIDTH / 2), label.y())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.place_drum_labels()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.place_drum_labels()

    def _create_keys(self, keyboard_widget: QWidget) -> None:
        """
        Create piano keys with individual shadows

        :param keyboard_widget: QWidget
        """

        def apply_shadow(widget):
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setOffset(3, 3)
            shadow.setColor(QColor(0, 0, 0, 80))
            widget.setGraphicsEffect(shadow)

        self._keys_by_note = {}
        # First create all white keys
        for _, note in enumerate(self.white_notes):
            key = PianoKey(
                note,
                is_black=False,
                width=self.white_key_width,
                height=self.white_key_height,
            )
            apply_shadow(key)
            keyboard_widget.layout().addWidget(key)
            self._keys_by_note[note] = key

            if hasattr(self.parent(), "handle_piano_note_on"):
                key.noteOn.connect(self.parent().handle_piano_note_on)
            if hasattr(self.parent(), "handle_piano_note_off"):
                key.noteOff.connect(self.parent().handle_piano_note_off)

        # Add black keys
        black_positions = self.BLACK_POSITIONS

        for pos, note in zip(
            black_positions, [n for n in KEYBOARD_BLACK_NOTES if n is not None]
        ):
            black_key = PianoKey(
                note,
                is_black=True,
                width=self.black_key_width,
                height=self.black_key_height,
            )
            black_key.setParent(keyboard_widget)
            self._keys_by_note[note] = black_key
            apply_shadow(black_key)

            x_pos = (pos * self.white_key_width) + (
                self.white_key_width - self.black_key_width // 2
            )
            black_key.move(x_pos, 0)
            black_key.show()

            if hasattr(self.parent(), "handle_piano_note_on"):
                black_key.noteOn.connect(self.parent().handle_piano_note_on)
            if hasattr(self.parent(), "handle_piano_note_off"):
                black_key.noteOff.connect(self.parent().handle_piano_note_off)

    def set_midi_channel(self, channel: int) -> None:
        """Set MIDI channel for note messages

        :param channel: int
        """
        self.current_channel = channel
        log.message(f"Piano keyboard set to channel {channel}")
