"""
New Arpeggio editor.

Covers the Parameter Guide's "ARPEGGIO" page (p. 29) and the MIDI
Implementation table Program Controller (18 00 40 00), with the arpeggio
switch of each part (Program Zone, 18 00 30-33 03) and the program tempo.

The timing view draws two beats of the grid: how many notes per beat, the
shuffle, how long each note sounds (Duration) and how the accent and fixed
velocity change their loudness.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.midi.data.arpeggio.data import ARPEGGIO_STYLE
from jdxi_editor.ui.v2.framework import Block, PSpec, V2Editor, rq1
from jdxi_editor.ui.v2.widgets import _Graph

ACCENT = "#f2c94c"
GRIDS = ("1/4", "1/8", "1/8L", "1/8H", "1/12", "1/16", "1/16L", "1/16H", "1/24")
GRID_STEPS = (1, 2, 2, 2, 3, 4, 4, 4, 6)  # grid sections per beat
GRID_SHUFFLE = (0.0, 0.0, 0.12, 0.25, 0.0, 0.0, 0.12, 0.25, 0.0)  # how late the off-beat notes come (drawing only)
DURATIONS = ("30", "40", "50", "60", "70", "80", "90", "100", "120", "Full")
MOTIFS = ("Up (L)", "Up (L&H)", "Up (_)", "Down (L)", "Down (L&H)", "Down (_)",
          "U/D (L)", "U/D (L&H)", "U/D (_)", "Rand (L)", "Rand (_)", "Phrase")
PARTS = ("DIGITAL 1", "DIGITAL 2", "ANALOG", "DRUMS")


def arpeggio_blocks() -> list[Block]:
    S = PSpec
    p29 = 29
    ctrl = Block("PROGRAM_CONTROLLER", "ARPEGGIO", JDXiSysExAddress(0x18, 0x00, 0x40, 0x00), [
        S("ARPEGGIO_SWITCH", 0x03, "Arpeggio", tr("Arpeggio Switch"), tr("Turns the arpeggio on or off (the [Arpeggio] button)."),
          hi=1, choices=("OFF", "ON"), source=tr("MIDI Implementation")),
        S("ARPEGGIO_STYLE", 0x05, "Style", tr("Arpeggio Style"), tr("The arpeggio's performance style."),
          hi=127, choices=tuple(ARPEGGIO_STYLE), kind="list", page=p29),
        S("ARPEGGIO_GRID", 0x01, "Grid", tr("Arpeggio Grid"),
          tr("Note value of one grid unit and its shuffle: 1/8 two per beat, 1/12 eighth-note triplets, 1/16 four per beat, 1/24 sixteenth triplets; L light shuffle, H heavy."),
          hi=8, choices=GRIDS, page=p29),
        S("ARPEGGIO_DURATION", 0x02, "Duration", tr("Arpeggio Duration"),
          tr("How long each note sounds, in % of the grid value: 30 is staccato, 120 tenuto; Full holds each note until the next one."),
          hi=9, choices=DURATIONS, unit="%", page=p29),
        S("ARPEGGIO_MOTIF", 0x06, "Motif", tr("Arpeggio Motif"),
          tr("How the notes are played when you hold more keys than the style has notes: up, down, up and down, random (L: only the lowest key each time, L&H: lowest and highest, _: in order), or Phrase."),
          hi=11, choices=MOTIFS, kind="list", page=p29),
        S("ARPEGGIO_OCTAVE_RANGE", 0x07, "Oct Range", tr("Arpeggio Octave Range"),
          tr("Shifts the arpeggio by an octave at each cycle, up to three octaves up or down."), lo=-3, hi=3, raw_offset=64,
          signed=True, page=p29),
        S("ARPEGGIO_ACCENT_RATE", 0x09, "Accent", tr("Arpeggio Accent Rate"),
          tr("100: the velocities programmed in the style; 0: every note at the same velocity."), hi=100, page=p29),
        S("ARPEGGIO_VELOCITY", 0x0A, "Velocity", tr("Arpeggio Velocity"),
          tr("REAL: as hard as you play; 1-127: always this velocity."), fmt=lambda v: "REAL" if v == 0 else str(v),
          parse=lambda t: 0 if t.strip().upper() == "REAL" else (int(t) if t.strip().isdigit() else None), page=p29),
    ], request=rq1([0x18, 0x00, 0x40, 0x00], 0x0C))
    blocks = [ctrl]
    for part, name in enumerate(PARTS):
        zone = Block(f"ZONE_{part}", name, JDXiSysExAddress(0x18, 0x00, 0x30 + part, 0x00), [
            S("ZONE_ARPEGGIO_SWITCH", 0x03, name, tr("Arpeggio for {part}").format(part=name),
              tr("Whether the arpeggio plays this part."), hi=1, choices=("OFF", "ON"), source=tr("MIDI Implementation"),
              group="PARTS"),
        ], request=rq1([0x18, 0x00, 0x30 + part, 0x00], 0x23))
        zone.export = False  # the Program editor saves the zone blocks
        blocks.append(zone)
    common = Block("PROGRAM_COMMON", "PROGRAM", JDXiSysExAddress(0x18, 0x00, 0x00, 0x00), [
        S("PROGRAM_TEMPO", 0x11, "Tempo", tr("Program Tempo (BPM)"), tr("Tempo of the program, which the arpeggio follows."),
          lo=500, hi=30000, size=4, scale=100, page=10, group="PROGRAM"),
    ], request=rq1([0x18, 0x00, 0x00, 0x00], 0x1F))
    common.export = False
    blocks.append(common)
    return blocks


class TimingView(_Graph):
    """Two beats of the grid: note positions, durations and loudness."""

    def __init__(self, editor: "ArpeggioEditor"):
        super().__init__(ACCENT, editor.info_hub, 110)
        self.grid, self.duration = editor.pv("ARPEGGIO_GRID"), editor.pv("ARPEGGIO_DURATION")
        self.accent, self.velocity = editor.pv("ARPEGGIO_ACCENT_RATE"), editor.pv("ARPEGGIO_VELOCITY")
        for pv in (self.grid, self.duration, self.accent, self.velocity):
            pv.watch(lambda _v: self.update())
        self.setToolTip(tr("Two beats of the arpeggio: where the notes fall, how long and how loud they are"))

    def notes(self) -> list[tuple[float, float, float]]:
        """(start, length, loudness 0-1) of each note, in beats."""
        g = self.grid.value()
        steps, shuffle = GRID_STEPS[g], GRID_SHUFFLE[g]
        unit = 1.0 / steps
        d = self.duration.value()
        out = []
        for i in range(2 * steps):
            start = i * unit + (shuffle * unit if steps in (2, 4) and i % 2 == 1 else 0.0)
            length = unit if d == len(DURATIONS) - 1 else unit * int(DURATIONS[d]) / 100
            fixed = self.velocity.value()
            base = (fixed / 127) if fixed else 0.8
            accent = self.accent.value() / 100
            pattern = 1.0 if i % steps == 0 else (0.75 if i % 2 == 0 else 0.55)  # strong beats louder
            loud = base * (1 - accent + accent * pattern)
            out.append((start, length, max(0.05, min(1.0, loud))))
        return out

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._background(p)
        r = self.plot_rect()
        beat = r.width() / 2
        p.setPen(QPen(QColor("#3a3d44"), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(r.left() + beat, r.top()), QPointF(r.left() + beat, r.bottom()))
        color = QColor(ACCENT)
        for start, length, loud in self.notes():
            x = r.left() + start * beat
            w = max(2.0, min(length * beat, r.right() - x) - 1)
            h = r.height() * loud
            fill = QColor(color)
            fill.setAlpha(170)
            p.fillRect(QRectF(x, r.bottom() - h, w, h), fill)
        p.setPen(QColor("#8a8d94"))
        p.setFont(QFont(self.font().family(), 7))
        p.drawText(QPointF(r.left() + 2, r.bottom() + 11), tr("beat 1"))
        p.drawText(QPointF(r.left() + beat + 2, r.bottom() + 11), tr("beat 2"))
        p.end()


class ArpeggioEditor(V2Editor):
    """The arpeggio of the current program."""

    ACCENT = ACCENT

    def __init__(self, midi_helper=None, preset_helper=None, parent=None):
        super().__init__(arpeggio_blocks(), midi_helper=midi_helper, parent=parent, title=tr("Arpeggio"))
        self.preset_helper = preset_helper

    def build_panels(self) -> None:
        s = self.spec
        main = self.card("ARPEGGIO", tr("Parameter Guide, p. 29"))
        row = QHBoxLayout()
        row.addWidget(self.control(s("ARPEGGIO_SWITCH")), 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.control(s("PROGRAM_TEMPO")), 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch()
        main.body.addLayout(row)
        main.body.addWidget(self.control(s("ARPEGGIO_STYLE")))
        main.body.addWidget(self.control(s("ARPEGGIO_MOTIF")))
        self.motif_text = QLabel()
        self.motif_text.setWordWrap(True)
        self.motif_text.setStyleSheet("color: #c9cbd1; font-size: 12px; background: transparent;")
        main.body.addWidget(self.motif_text)
        self.pv("ARPEGGIO_MOTIF").watch(self._show_motif)
        self.panels_layout.addWidget(main)

        timing = self.card(tr("TIMING"), tr("Parameter Guide, p. 29"))
        timing.body.addWidget(TimingView(self))
        timing.body.addWidget(self.control(s("ARPEGGIO_GRID")))
        timing.body.addWidget(self.control(s("ARPEGGIO_DURATION")))
        timing.body.addLayout(self.knob_row([s("ARPEGGIO_ACCENT_RATE"), s("ARPEGGIO_VELOCITY"), s("ARPEGGIO_OCTAVE_RANGE")]))
        self.panels_layout.addWidget(timing)

        parts = self.card(tr("PARTS THE ARPEGGIO PLAYS"), tr("MIDI Implementation, Program Zone"))
        row = QHBoxLayout()
        for part in range(4):
            row.addWidget(self.control(self.spec("ZONE_ARPEGGIO_SWITCH", f"ZONE_{part}")))
        row.addStretch()
        parts.body.addLayout(row)
        self.panels_layout.addWidget(parts)
        self.panels_layout.addStretch()

    def _show_motif(self, value: int) -> None:
        texts = [
            tr("Only the lowest key each time, upward from the lowest key."),
            tr("The lowest and highest keys each time, upward from the lowest key."),
            tr("The keys in order, upward from the lowest."),
            tr("Only the lowest key each time, downward from the highest key."),
            tr("The lowest and highest keys each time, downward from the highest key."),
            tr("The keys in order, downward from the highest."),
            tr("Up and back down, with only the lowest key each time."),
            tr("Up and back down, with the lowest and highest keys each time."),
            tr("The keys in order, up and back down."),
            tr("The keys at random, with only the lowest key each time."),
            tr("The keys you press at random."),
            tr("One key plays a phrase based on its pitch; with several keys, the last one pressed."),
        ]
        self.motif_text.setText(texts[value] if 0 <= value < len(texts) else "")
