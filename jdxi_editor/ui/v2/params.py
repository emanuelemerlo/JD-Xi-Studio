"""
Parameter values and the information shown about them.

ParamValue holds one parameter's display value (the value of the JD-Xi
display, e.g. -24..+24 for OSC Pitch). It is what the editor registers in
``self.controls``: the existing MIDI code reads ``value()``, sets
``setValue()`` with signals blocked when a reply arrives, and listens to
``valueChanged`` to send. Widgets subscribe with ``watch()``, which is called
even while signals are blocked, so every view of a value stays in step.

ParamInfo is what the information panel shows: the name on the display, the
long name, range and unit, a short explanation (from the Parameter Guide, in
the interface language) and what the parameter depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from PySide6.QtCore import QObject, Signal

from jdxi_editor.i18n import tr

SYNC_NOTES = [
    "16", "12", "8", "4", "2", "1", "3/4", "2/3", "1/2", "3/8",
    "1/3", "1/4", "3/16", "1/6", "1/8", "3/32", "1/12", "1/16", "1/24", "1/32",
]


@dataclass
class ParamInfo:
    group: str  # as on the display: COMMON, OSC, PITCH, FILTER, AMP, LFO
    label: str  # name on the display
    long: str = ""  # long name, from the Parameter Guide
    description: str = ""
    unit: str = ""
    depends: str = ""  # when the parameter has an effect
    choices: Sequence[str] = ()  # labels of the values, for switches and lists
    step: int = 1
    page: int = 0  # page of the Parameter Guide
    signed: bool = False  # show "+" before positive values
    show_negative: bool = False  # the display shows the value as negative (Bend Range Down)

    def format(self, value: int) -> str:
        if self.choices and 0 <= value < len(self.choices):
            return self.choices[value]
        if self.show_negative:
            text = f"-{value}" if value else "0"
        elif self.signed:
            text = f"{value:+d}" if value else "0"
        else:
            text = str(value)
        return f"{text} {self.unit}".strip() if self.unit else text


class ParamValue(QObject):
    """One parameter's display value; registered in the editor's controls."""

    valueChanged = Signal(int)

    def __init__(self, param, info: ParamInfo, minimum: int, maximum: int, parent=None):
        super().__init__(parent)
        self.param = param
        self.info = info
        self.minimum = minimum
        self.maximum = maximum
        self._value = 0 if minimum <= 0 <= maximum else minimum
        self._watchers: list[Callable[[int], None]] = []
        self._enabled = True
        self._enabled_watchers: list[Callable[[bool], None]] = []

    # --- the interface the existing editor code uses
    def value(self) -> int:
        return self._value

    def setValue(self, value) -> None:
        value = self.clamp(value)
        if value == self._value:
            return
        self._value = value
        for watcher in list(self._watchers):
            watcher(value)
        self.valueChanged.emit(value)  # silent while signals are blocked

    # --- for widgets
    def clamp(self, value) -> int:
        try:
            value = int(round(float(value)))
        except (TypeError, ValueError):
            value = self._value
        step = max(1, self.info.step)
        if step > 1:
            value = int(round(value / step) * step)
        return max(self.minimum, min(self.maximum, value))

    def watch(self, callback: Callable[[int], None]) -> None:
        self._watchers.append(callback)
        callback(self._value)

    def text(self, value: Optional[int] = None) -> str:
        return self.info.format(self._value if value is None else value)

    @property
    def range_text(self) -> str:
        info = self.info
        if info.choices:
            return ", ".join(info.choices)
        lo, hi = info.format(self.minimum), info.format(self.maximum)
        if info.show_negative:
            lo, hi = info.format(self.maximum), info.format(self.minimum)
        return f"{lo} … {hi}"

    def is_enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        if enabled != self._enabled:
            self._enabled = enabled
            for watcher in list(self._enabled_watchers):
                watcher(enabled)

    def watch_enabled(self, callback: Callable[[bool], None]) -> None:
        self._enabled_watchers.append(callback)
        callback(self._enabled)


def analog_info() -> dict[str, ParamInfo]:
    """Information for every Analog parameter (Parameter Guide pp. 12–14)."""
    on_off = (tr("OFF"), tr("ON"))
    st, ct = tr("st"), tr("cent")
    pw_only = tr("Only with Waveform PW-SQR.")
    lpf_only = tr("Only with Filter Type LPF.")
    rate_dep = tr("Used when Tempo Sync is OFF.")
    wheel = tr("Applied with the modulation wheel (CC01).")
    return {
        # --- COMMON
        "PORTAMENTO_SWITCH": ParamInfo(
            "COMMON", "Porta Sw", "Portamento Switch",
            tr("Glides the pitch from one note to the next."), choices=on_off, page=12,
        ),
        "PORTAMENTO_TIME": ParamInfo(
            "COMMON", "Porta Time", "Portamento Time",
            tr("How long the glide to the next note takes: higher is slower."),
            depends=tr("Has an effect with Porta Sw ON."), page=12,
        ),
        "LEGATO_SWITCH": ParamInfo(
            "COMMON", "Legato Sw", "Legato Switch",
            tr("Playing a key while the previous one is held changes the pitch without restarting the note."),
            choices=on_off, page=12,
        ),
        "OCTAVE_SHIFT": ParamInfo(
            "COMMON", "Octave Shift", "Octave Shift",
            tr("Moves the tone up or down by octaves."), unit=tr("oct"), signed=True, page=12,
        ),
        "PITCH_BEND_UP": ParamInfo(
            "COMMON", "Bend Range U", "Pitch Bend Range Up",
            tr("How far the pitch rises with the bend lever all the way up."), unit=st, page=12,
        ),
        "PITCH_BEND_DOWN": ParamInfo(
            "COMMON", "Bend Range D", "Pitch Bend Range Down",
            tr("How far the pitch falls with the bend lever all the way down."),
            unit=st, show_negative=True, page=12,
        ),
        # --- OSC
        "OSC_WAVEFORM": ParamInfo(
            "OSC", "Waveform", "Waveform",
            tr("The oscillator's waveform: SAW bright and full, TRI soft and hollow, PW-SQR hollow and nasal, with a variable pulse width."),
            choices=("SAW", "TRI", "PW-SQR"), page=12,
        ),
        "OSC_PULSE_WIDTH_MOD_DEPTH": ParamInfo(
            "OSC", "PWM Depth", "Pulse Width Modulation Depth",
            tr("How much the LFO moves the pulse width (PWM)."), depends=pw_only, page=12,
        ),
        "OSC_PULSE_WIDTH": ParamInfo(
            "OSC", "Pulse Width", "Pulse Width",
            tr("Width of the top of the square wave: small values are close to a square wave (50%), larger values sound thinner."),
            depends=pw_only, page=12,
        ),
        "SUB_OSCILLATOR_TYPE": ParamInfo(
            "OSC", "Sub OSC", "Sub Oscillator",
            tr("Adds a square wave one (OCT-1) or two (OCT-2) octaves below."),
            choices=("OFF", "OCT-1", "OCT-2"), page=12,
        ),
        # --- PITCH
        "OSC_PITCH_COARSE": ParamInfo(
            "PITCH", "OSC Pitch", "OSC Pitch",
            tr("Pitch in semitones."), unit=st, signed=True, page=12,
        ),
        "OSC_PITCH_FINE": ParamInfo(
            "PITCH", "OSC Detune", "OSC Detune",
            tr("Pitch in cents (hundredths of a semitone)."), unit=ct, signed=True, page=12,
        ),
        "OSC_PITCH_ENV_ATTACK_TIME": ParamInfo(
            "PITCH", "Env Attack", "Pitch Envelope Attack Time",
            tr("Time from the key press until the pitch reaches its highest (or lowest) point."), page=12,
        ),
        "OSC_PITCH_ENV_DECAY_TIME": ParamInfo(
            "PITCH", "Env Decay", "Pitch Envelope Decay Time",
            tr("Time for the pitch to come back to the note played."), page=12,
        ),
        "OSC_PITCH_ENV_DEPTH": ParamInfo(
            "PITCH", "Env Depth", "Pitch Envelope Depth",
            tr("How much, and in which direction, the pitch envelope moves the pitch. 0: no effect."),
            signed=True, page=12,
        ),
        "OSC_PITCH_ENV_VELOCITY_SENSITIVITY": ParamInfo(
            "PITCH", "Env V-Sens", "Pitch Envelope Velocity Sens",
            tr("How much the pitch envelope depth follows how hard you play."),
            depends=tr("In the MIDI Implementation; the JD-Xi display does not show it."),
            signed=True,
        ),
        # --- FILTER
        "FILTER_MODE_SWITCH": ParamInfo(
            "FILTER", "Type", "Filter Type",
            tr("LPF uses the analog low-pass filter; BYPASS leaves the sound unfiltered."),
            choices=("BYPASS", "LPF"), page=12,
        ),
        "FILTER_CUTOFF": ParamInfo(
            "FILTER", "Cutoff", "Cutoff Frequency",
            tr("Frequency above which the filter cuts: lower is darker. Drag the curve sideways."),
            depends=lpf_only, page=12,
        ),
        "FILTER_RESONANCE": ParamInfo(
            "FILTER", "Resonance", "Resonance",
            tr("Emphasises the frequencies around the cutoff. Drag the curve up or down."),
            depends=lpf_only, page=13,
        ),
        "FILTER_CUTOFF_KEYFOLLOW": ParamInfo(
            "FILTER", "Cutoff KF", "Cutoff Key Follow",
            tr("How the cutoff follows the keys: at +100 it rises one octave per octave played above C4; at -100 it falls."),
            signed=True, step=10, depends=lpf_only, page=13,
        ),
        "FILTER_ENV_VELOCITY_SENSITIVITY": ParamInfo(
            "FILTER", "Velo Sens", "Filter Envelope Velocity Sense",
            tr("How much the filter envelope depth follows how hard you play."),
            signed=True, depends=lpf_only, page=13,
        ),
        "FILTER_ENV_ATTACK_TIME": ParamInfo(
            "FILTER", "Attack", "Filter Envelope Attack Time",
            tr("Time from the key press until the cutoff reaches its highest (or lowest) point."),
            depends=lpf_only, page=13,
        ),
        "FILTER_ENV_DECAY_TIME": ParamInfo(
            "FILTER", "Decay", "Filter Envelope Decay Time",
            tr("Time for the cutoff to go from that point to the sustain level."),
            depends=lpf_only, page=13,
        ),
        "FILTER_ENV_SUSTAIN_LEVEL": ParamInfo(
            "FILTER", "Sustain", "Filter Envelope Sustain Level",
            tr("Cutoff held while the key stays down."), depends=lpf_only, page=13,
        ),
        "FILTER_ENV_RELEASE_TIME": ParamInfo(
            "FILTER", "Release", "Filter Envelope Release Time",
            tr("Time for the cutoff to reach its minimum after the key is released."),
            depends=lpf_only, page=13,
        ),
        "FILTER_ENV_DEPTH": ParamInfo(
            "FILTER", "Depth", "Filter Envelope Depth",
            tr("How much, and in which direction, the envelope moves the cutoff. 0: the envelope has no effect."),
            signed=True, depends=lpf_only, page=13,
        ),
        # --- AMP
        "AMP_LEVEL": ParamInfo(
            "AMP", "AMP Level", "Amp Level", tr("Volume of the tone."), page=13,
        ),
        "AMP_LEVEL_VELOCITY_SENSITIVITY": ParamInfo(
            "AMP", "Level V-Sens", "Amp Level Velocity Sense",
            tr("How much the volume follows how hard you play."), signed=True, page=13,
        ),
        "AMP_LEVEL_KEYFOLLOW": ParamInfo(
            "AMP", "Level KF", "Amp Level Key Follow",
            tr("Positive: louder as you play above C4; negative: softer."),
            signed=True, step=10, page=13,
        ),
        "AMP_ENV_ATTACK_TIME": ParamInfo(
            "AMP", "Attack", "Amp Envelope Attack Time",
            tr("Time from the key press to full volume. A little attack removes the click."), page=13,
        ),
        "AMP_ENV_DECAY_TIME": ParamInfo(
            "AMP", "Decay", "Amp Envelope Decay Time",
            tr("Time from full volume down to the sustain level."), page=13,
        ),
        "AMP_ENV_SUSTAIN_LEVEL": ParamInfo(
            "AMP", "Sustain", "Amp Envelope Sustain Level",
            tr("Volume held while the key stays down."), page=13,
        ),
        "AMP_ENV_RELEASE_TIME": ParamInfo(
            "AMP", "Release", "Amp Envelope Release Time",
            tr("Time for the sound to fade out after the key is released."), page=13,
        ),
        # --- LFO
        "LFO_SHAPE": ParamInfo(
            "LFO", "Shape", "LFO Shape",
            tr("Waveform of the LFO: TRI, SIN, SAW, SQR, S&H (steps at random levels) or RND (random, smooth)."),
            choices=("TRI", "SIN", "SAW", "SQR", "S&H", "RND"), page=14,
        ),
        "LFO_RATE": ParamInfo(
            "LFO", "Rate", "LFO Rate", tr("Speed of the LFO."), depends=rate_dep, page=14,
        ),
        "LFO_TEMPO_SYNC_SWITCH": ParamInfo(
            "LFO", "Tempo Sync", "LFO Tempo Sync Switch",
            tr("ON: the speed is a note value of the tempo (Sync Note) instead of Rate."),
            choices=on_off, page=14,
        ),
        "LFO_TEMPO_SYNC_NOTE": ParamInfo(
            "LFO", "Sync Note", "LFO Tempo Sync Note",
            tr("Length of one LFO cycle as a note value of the tempo."),
            choices=SYNC_NOTES, depends=tr("Used when Tempo Sync is ON."), page=14,
        ),
        "LFO_FADE_TIME": ParamInfo(
            "LFO", "Fade Time", "LFO Fade Time",
            tr("Time from the note start until the LFO reaches its full depth: a delayed vibrato."), page=14,
        ),
        "LFO_KEY_TRIGGER": ParamInfo(
            "LFO", "Key Trigger", "LFO Key Trigger",
            tr("ON: the LFO cycle restarts at every key press."), choices=on_off, page=14,
        ),
        "LFO_PITCH_DEPTH": ParamInfo(
            "LFO", "Pitch Depth", "LFO Pitch Depth",
            tr("The LFO moves the pitch: vibrato."), signed=True, page=14,
        ),
        "LFO_FILTER_DEPTH": ParamInfo(
            "LFO", "Filter Depth", "LFO Filter Depth",
            tr("The LFO moves the cutoff: wah."), signed=True, page=14,
        ),
        "LFO_AMP_DEPTH": ParamInfo(
            "LFO", "Amp Depth", "LFO Amp Depth",
            tr("The LFO moves the volume: tremolo."), signed=True, page=14,
        ),
        "LFO_PITCH_MODULATION_CONTROL": ParamInfo(
            "LFO", "Mod Pitch", "Modulation Pitch Depth",
            tr("Vibrato added by the modulation wheel."), depends=wheel, signed=True, page=14,
        ),
        "LFO_FILTER_MODULATION_CONTROL": ParamInfo(
            "LFO", "Mod Filter", "Modulation Filter Depth",
            tr("Wah added by the modulation wheel."), depends=wheel, signed=True, page=14,
        ),
        "LFO_AMP_MODULATION_CONTROL": ParamInfo(
            "LFO", "Mod Amp", "Modulation Amp Depth",
            tr("Tremolo added by the modulation wheel."), depends=wheel, signed=True, page=14,
        ),
        "LFO_RATE_MODULATION_CONTROL": ParamInfo(
            "LFO", "Mod Rate", "Modulation Rate",
            tr("Positive: the wheel speeds the LFO up; negative: it slows it down."),
            depends=wheel, signed=True, page=14,
        ),
    }
