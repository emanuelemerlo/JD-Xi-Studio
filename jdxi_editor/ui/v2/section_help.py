"""
A «?» for each section (sound-design spec §7, Phase 6): what it changes, how
the sound changes, an example; the Parameter Guide page stays in the card.

The texts are short on purpose: the information panel already explains each
parameter when it is pointed at; this is the section as a whole.
"""

from __future__ import annotations

from typing import Optional

from jdxi_editor.i18n import tr


def kind_of(title: str) -> Optional[str]:
    """The section a card's title names (the JD-Xi's own panel names)."""
    t = (title or "").upper().strip()
    if t in ("OSC", "OSCILLATOR"):
        return "osc"
    if t in ("FILTER", "TVF ENVELOPE"):
        return "filter"
    if t in ("AMP", "TVA ENVELOPE"):
        return "amp"
    if t == "LFO":
        return "lfo"
    if t == "MOD LFO":
        return "mod_lfo"
    if t in ("PITCH", "PITCH ENVELOPE"):
        return "pitch"
    if t.startswith("EFFECT"):
        return "effect"
    if t == "DELAY":
        return "delay"
    if t == "REVERB":
        return "reverb"
    return None


def text(kind: str) -> tuple[str, str, str]:
    """(what it changes, how the sound changes, an example)."""
    texts = {
        "osc": (
            tr("The raw sound: the waveform and its pitch, before anything shapes it."),
            tr("Sawtooth is bright and full, square hollow, triangle and sine soft; PCM is a sampled sound."),
            tr("A bass: sawtooth one octave down; a soft pad: triangle with a little detune."),
        ),
        "filter": (
            tr("Which frequencies pass: cutoff, resonance, and the envelope that moves the cutoff."),
            tr("Lower cutoff = darker; resonance stresses the cutoff; the envelope makes the «wah» of a note."),
            tr("A plucked bass: cutoff low, envelope depth up, short decay, sustain at zero."),
        ),
        "amp": (
            tr("The volume of each note over time (attack, decay, sustain, release) and its level."),
            tr("Attack slow = it swells; release long = it lingers after the key is let go."),
            tr("A pad: attack around 60, release around 70; an organ: attack 0, sustain max, release short."),
        ),
        "lfo": (
            tr("A slow, repeating movement applied to pitch, filter or volume."),
            tr("On pitch it is vibrato, on the filter a «wah» that comes and goes, on volume tremolo."),
            tr("Vibrato: triangle, rate around 70, a little pitch depth, a fade so it comes in late."),
        ),
        "mod_lfo": (
            tr("A second LFO, brought in by the modulation lever of the JD-Xi."),
            tr("Nothing changes until the lever moves: then the movement grows with it."),
            tr("Vibrato only when wanted: pitch depth here, and the lever up while playing."),
        ),
        "pitch": (
            tr("The pitch of the note and how it moves at its start (pitch envelope)."),
            tr("A short pitch envelope gives the note a «chirp» or a drop at the start."),
            tr("A laser or a tom: pitch envelope depth up, decay short."),
        ),
        "effect": (
            tr("A processor after the parts: distortion, fuzz, compressor, bit crusher, flanger, phaser…"),
            tr("It colours every part sent to it (each part's send level decides how much)."),
            tr("A dirtier lead: distortion on Effect 1, Digital 1's send to Effect 1 up."),
        ),
        "delay": (
            tr("Echoes of the sound: their time, how many (feedback) and their level."),
            tr("Short times thicken the sound; times in step with the tempo make rhythmic echoes."),
            tr("Echoes in time: delay time synced to a dotted eighth, feedback around 30."),
        ),
        "reverb": (
            tr("The room around the sound: its type, its length and its level."),
            tr("More reverb = farther away and wider; too much blurs fast parts."),
            tr("A pad in a hall: hall type, long time, send from the pad's part up."),
        ),
    }
    return texts.get(kind, ("", "", ""))


def help_text(kind: str) -> str:
    what, how, example = text(kind)
    return "\n\n".join((
        tr("What it changes: {text}").format(text=what),
        tr("How the sound changes: {text}").format(text=how),
        tr("Example: {text}").format(text=example),
    ))


def show(card, title: str, source: str = "") -> bool:
    """The section's help in the information panel of the editor *card* is in."""
    kind = kind_of(title)
    widget = card
    while widget is not None and not hasattr(widget, "info_panel"):
        widget = widget.parentWidget()
    panel = getattr(widget, "info_panel", None)
    if kind is None or panel is None:
        return False
    panel.show_text(title, tr("About this section"), help_text(kind), source)
    return True
