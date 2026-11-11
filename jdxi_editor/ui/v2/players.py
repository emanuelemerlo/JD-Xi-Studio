"""
Pattern and MIDI file player in the new look: the same editors (sequencer,
learning, transport, track classification, automation, USB recorder), restyled.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from jdxi_editor.ui.editors.midi_player import editor as _player
from jdxi_editor.ui.editors.pattern import pattern as _pattern
from jdxi_editor.ui.v2.restyle import restyle

PATTERN_ACCENT = "#f2994a"
PLAYER_ACCENT = "#56ccf2"


# Same class names as the editors they restyle: the main window finds open
# editors by class name (get_existing_editor), and isinstance() keeps working.


class PatternSequenceEditor(_pattern.PatternSequenceEditor):
    """The pattern sequencer with the new editors' look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restyle(self, PATTERN_ACCENT)
        QTimer.singleShot(0, self, lambda: restyle(self, PATTERN_ACCENT))  # after the base class's own pass

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


PatternEditor = PatternSequenceEditor
MidiPlayer = MidiFilePlayer
