"""
The notes a part of the MIDI file plays, shown on the keyboard of the main
window (its 37 keys, as the JD-Xi's).

The player's transport knows what it sends to the JD-Xi (``notes_on``); a
timer in the main thread looks ~30 times a second and lights the keys that
would play those notes at the part's octave, in the part's colour. Notes
beyond the 37 keys mark the edge key. Nothing is drawn from the playback
thread.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QTimer

from jdxi_editor.ui.editors.midi_player.fit_jdxi import PART_COLORS

# the parts that can be shown: 0-based MIDI channel -> name (translated where shown)
KEYBOARD_PARTS = {0: "Digital 1", 1: "Digital 2", 2: "Analog", 9: "Drums"}
SETTING = "midi_player/keyboard_part"
LOOK_MS = 33


class KeyboardFeed(QObject):
    """Shows on *keyboard* the notes *notes_on(channel)* returns for the chosen part."""

    def __init__(
        self,
        notes_on: Callable[[int], set[int]],
        keyboard: Callable[[], Optional[object]],
        octave: Callable[[int], int],
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._notes_on = notes_on
        self._keyboard = keyboard
        self._octave = octave
        self.channel: Optional[int] = None
        self._shown: tuple = (None, frozenset())
        self._timer = QTimer(self)
        self._timer.setInterval(LOOK_MS)
        self._timer.timeout.connect(self.look)

    def set_channel(self, channel: Optional[int]) -> None:
        """The part to show (0-based channel), or None for none."""
        self.channel = channel if channel in KEYBOARD_PARTS else None
        if self.channel is None:
            self._timer.stop()
            self.clear()
        else:
            self._timer.start()
            self.look()

    def look(self) -> None:
        keyboard = self._keyboard()
        if keyboard is None or self.channel is None:
            return
        try:
            shift = 12 * int(self._octave(self.channel) or 0)
        except Exception:
            shift = 0
        notes = frozenset(n - shift for n in self._notes_on(self.channel))
        if (self.channel, notes) == self._shown:
            return
        self._shown = (self.channel, notes)
        keyboard.show_file_notes(set(notes), PART_COLORS.get(self.channel + 1))

    def clear(self) -> None:
        keyboard = self._keyboard()
        self._shown = (None, frozenset())
        if keyboard is not None:
            keyboard.show_file_notes(set())
