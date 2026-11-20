"""
Fit to the JD-Xi: what of a MIDI file the JD-Xi plays, and a proposal that
puts its tracks on the JD-Xi's four parts.

The JD-Xi plays four parts, each on its own channel: Digital 1 (1), Digital 2
(2), Analog (3), Drums (10). Notes on any other channel are not heard. A file
made for the JD-Xi has nothing to fit; a general file (an orchestra on 16
channels) does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import mido
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.ui.editors.midi_player.track.category import CATEGORY_META, TrackCategory

# 1-based channel -> the part that plays it
JDXI_PARTS: dict[int, str] = {1: "Digital 1", 2: "Digital 2", 3: "Analog", 10: "Drums"}
NOT_PLAYED = 0  # in a proposal: leave the track where it is (not heard)
OFF_CHANNEL = 4  # where «not played» puts a track that was on a part (no JD-Xi part listens to 4)


def part_name(channel: int) -> str:
    """«Digital 1», …; a channel the JD-Xi does not play: «channel 5»."""
    name = JDXI_PARTS.get(channel)
    return tr(name) if name else tr("channel {ch}").format(ch=channel)


@dataclass
class TrackInfo:
    index: int
    name: str
    channel: int  # 1-based, the first one the track uses
    notes: int


def note_tracks(midi_file: mido.MidiFile) -> list[TrackInfo]:
    """The tracks that play notes (tempo and marker tracks have nothing to fit)."""
    infos = []
    for index, track in enumerate(midi_file.tracks):
        notes = 0
        channel = None
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                notes += 1
                if channel is None:
                    channel = msg.channel + 1
        if notes:
            name = (track.name or "").strip() or tr("Track {n}").format(n=index + 1)
            infos.append(TrackInfo(index, name, channel or 1, notes))
    return infos


def summary(midi_file: Optional[mido.MidiFile]) -> tuple[str, bool]:
    """
    One line on what the JD-Xi plays of *midi_file*, and whether it is ready
    (every track that plays notes is on a JD-Xi part).
    """
    if midi_file is None:
        return tr("Load a MIDI file: this says which of its tracks the JD-Xi plays."), False
    tracks = note_tracks(midi_file)
    off = [t for t in tracks if t.channel not in JDXI_PARTS]
    if not tracks:
        return tr("No notes in this file."), False
    if not off:
        return tr("Ready for the JD-Xi: its {n} tracks are on the JD-Xi's parts.").format(n=len(tracks)), True
    return tr(
        "{off} of {tracks} tracks are on channels no JD-Xi part plays: they are not heard."
    ).format(tracks=len(tracks), off=len(off)), False


def propose(tracks: list[TrackInfo], drum_indices: list[int], classifications: dict) -> dict[int, int]:
    """
    Track index -> proposed 1-based channel (NOT_PLAYED: leave it off).

    The drum tracks to Drums (10). Each melodic part takes ONE track, the one
    recognised best for it: the bass to Digital 1, keys or guitars to
    Digital 2, strings to Analog (the Analog part plays one note at a time;
    many tracks on one part would only be a jumble). Every other track is
    not played. A part nothing was recognised for keeps the track already on
    its channel, if any.
    """
    on_channel = {t.channel: t.index for t in tracks}
    proposal = {t.index: NOT_PLAYED for t in tracks}
    for index in drum_indices:
        if index in proposal:
            proposal[index] = 10
    taken = set(drum_indices)
    for category, entries in (classifications or {}).items():
        meta = CATEGORY_META.get(category)
        if meta is None or category == TrackCategory.UNCLASSIFIED:
            continue
        candidates = [(index, analysis) for index, analysis in entries
                      if index in proposal and index not in taken]
        if not candidates:
            continue

        def score(entry):
            scores = getattr(entry[1], "scores", None) or {}
            return scores.get(category, 0.0)

        best, _ = max(candidates, key=score)  # the first of the best on a tie
        proposal[best] = meta.channel
        taken.add(best)
    for channel in (1, 2, 3):
        index = on_channel.get(channel)
        if channel not in proposal.values() and index is not None and index not in taken:
            proposal[index] = channel
    return proposal


class FitDialog(QDialog):
    """One row per track with notes: where it is, and the part proposed for it."""

    CHOICES = [(1, "Digital 1 (channel 1)"), (2, "Digital 2 (channel 2)"),
               (3, "Analog (channel 3)"), (10, "Drums (channel 10)")]

    def __init__(self, tracks: list[TrackInfo], proposal: dict[int, int], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Fit to the JD-Xi"))
        self.resize(720, 520)
        self.tracks = tracks
        layout = QVBoxLayout(self)
        intro = QLabel(tr(
            "The JD-Xi plays four parts: Digital 1, Digital 2, Analog, Drums. Choose the part "
            "for each track; «Not played» leaves it on its channel, silent on the JD-Xi. "
            "Several tracks can share a part. Nothing changes until Apply; the file on disk "
            "changes only when you save."))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.table = QTableWidget(len(tracks), 4)
        self.table.setHorizontalHeaderLabels([tr("Track"), tr("Notes"), tr("Now"), tr("Part on the JD-Xi")])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.combos: dict[int, QComboBox] = {}
        for row, track in enumerate(tracks):
            self._item(row, 0, f"{track.index + 1}  {track.name}")
            self._item(row, 1, str(track.notes), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._item(row, 2, part_name(track.channel))
            combo = QComboBox()
            for channel, label in self.CHOICES:
                combo.addItem(tr(label), channel)
            stay = (tr("Not played (stays on channel {ch})").format(ch=track.channel)
                    if track.channel not in JDXI_PARTS else tr("Not played (to channel {ch})").format(ch=OFF_CHANNEL))
            combo.addItem(stay, NOT_PLAYED)
            wanted = proposal.get(track.index, NOT_PLAYED)
            combo.setCurrentIndex(max(0, combo.findData(wanted)))
            self.table.setCellWidget(row, 3, combo)
            self.combos[track.index] = combo
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText(tr("Apply"))
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _item(self, row: int, column: int, text: str, align=None) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if align is not None:
            item.setTextAlignment(align)
        self.table.setItem(row, column, item)

    def changes(self) -> dict[int, int]:
        """Track index -> new 1-based channel, only for the tracks that move."""
        moves = {}
        for track in self.tracks:
            wanted = self.combos[track.index].currentData()
            if wanted == NOT_PLAYED:
                # off the JD-Xi's parts: a track on one goes to a channel no part plays
                if track.channel in JDXI_PARTS:
                    moves[track.index] = OFF_CHANNEL
                continue
            if wanted != track.channel:
                moves[track.index] = wanted
        return moves
