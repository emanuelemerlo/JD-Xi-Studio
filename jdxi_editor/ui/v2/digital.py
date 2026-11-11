"""
New Digital Synth editor (SuperNATURAL synth tone), for Digital 1 and Digital 2.

Covers the Parameter Guide's "Digital Synth Tone" pages (p. 15-19) and every
parameter of the MIDI Implementation tables SuperNATURAL Synth Tone Common,
Modify and Partial (19 01/21 00 00, 19 01/21 50 00, 19 01/21 20-22 00).

The tone's common settings stay on top; the three partials are switched on
and off in a strip, like the [05]-[07] buttons, and edited one at a time, like
[01]-[03], with the oscillator, filter, amplifier and both LFOs drawn.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.address.address import JDXiSysExAddress
from jdxi_editor.midi.data.pcm.waves import PCM_WAVES
from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.ui.v2.framework import Block, NameField, PSpec, rq1, tone_editor_base
from jdxi_editor.ui.v2.params import SYNC_NOTES, ParamValue
from jdxi_editor.ui.v2.program import pan_parse, pan_text
from jdxi_editor.ui.v2.widgets import (
    ChoiceButtons,
    EnvelopeView,
    FilterCurveView,
    LfoView,
    WaveButtons,
)

ACCENT = "#eb5757"  # Digital 1 red, as on the JD-Xi panel
ACCENT_2 = "#f2994a"  # Digital 2 orange
NAME_LENGTH = 12
WAVES = ("SAW", "SQR", "PW-SQR", "TRI", "SINE", "NOISE", "SP-SAW", "PCM")  # SP-SAW: SUPER SAW
FILTERS = ("BYPASS", "LPF1", "HPF", "BPF", "PKG", "LPF2", "LPF3", "LPF4")  # as sent (MIDI Implementation)
LFO_SHAPES = ("TRI", "SIN", "SAW", "SQR", "S&H", "RND")
UMB = {1: 0x01, 2: 0x21}  # Temporary Tone: Digital Synth Part 1 / 2


def _address(synth: int, lmb: int) -> JDXiSysExAddress:
    return JDXiSysExAddress(0x19, UMB[synth], lmb, 0x00)


def _bytes(synth: int, lmb: int) -> list[int]:
    return [0x19, UMB[synth], lmb, 0x00]


def common_block(synth: int) -> Block:
    S = PSpec
    on_off = ("OFF", "ON")
    params = [
        S(f"TONE_NAME_{i + 1}", i, f"Name {i + 1}", lo=32, hi=127, description=tr("Name of the tone (12 characters)."), page=15)
        for i in range(NAME_LENGTH)
    ]
    params += [
        S("TONE_LEVEL", 0x0C, "Tone Level", description=tr("Overall volume of the tone."), page=15),
        S("TONE_CATEGORY", 0x36, "Category", tr("Tone Category"),
          tr("Category of the tone, as a number (the JD-Xi shows its name; the list of names is not in the MIDI Implementation)."), page=15),
        S("MONO_SWITCH", 0x14, "Mono/Poly", description=tr("POLY: chords; MONO: one note at a time."), hi=1, choices=("POLY", "MONO"), page=15),
        S("LEGATO_SWITCH", 0x32, "Legato SW", tr("Legato Switch"),
          tr("ON: a key pressed while the previous one is held changes the pitch without restarting the note, like hammering-on on a guitar."),
          hi=1, choices=on_off, depends=tr("Only with Mono/Poly set to MONO."), page=15),
        S("PORTAMENTO_SWITCH", 0x12, "Porta SW", tr("Portamento Switch"), tr("ON: the pitch glides from one note to the next."),
          hi=1, choices=on_off, page=15),
        S("PORTAMENTO_TIME", 0x13, "Porta Time", tr("Portamento Time"),
          tr("Time the pitch takes to glide to the next note; higher values are slower."), depends=tr("Only with Porta SW ON."), page=15),
        S("PORTAMENTO_MODE", 0x31, "Porta Mode", tr("Portamento Mode"),
          tr("NORMAL: portamento always. LEGATO: only when the next key is pressed before releasing the previous one."),
          hi=1, choices=("NORMAL", "LEGATO"), depends=tr("Only with Porta SW ON."), page=15),
        S("OCTAVE_SHIFT", 0x15, "Octave Shift", description=tr("Octave of the tone (±3)."), lo=-3, hi=3, raw_offset=64, signed=True, page=15),
        S("PITCH_BEND_RANGE_UP", 0x16, "Bend Range U", tr("Pitch Bend Range Up"),
          tr("Pitch change in semitones with the lever all the way to the right."), hi=24, unit="st", page=15),
        S("PITCH_BEND_RANGE_DOWN", 0x17, "Bend Range D", tr("Pitch Bend Range Down"),
          tr("Pitch change in semitones with the lever all the way to the left."), hi=24, unit="st", page=15),
        S("UNISON_SWITCH", 0x2E, "Unison SW", tr("Unison Switch"),
          tr("Layers one sound several times; the number of layers per key changes with the number of keys you play."),
          hi=1, choices=on_off, page=15),
        S("UNISON_SIZE", 0x3C, "Unison Size", description=tr("Notes layered on one key with Unison ON (with 8: one key 8, two keys 4 each, 3-4 keys 2 each, 5-8 keys 1 each)."),
          hi=3, choices=("2", "4", "6", "8"), depends=tr("Only with Unison SW ON."), page=15),
        S("RING_SWITCH", 0x1F, "RING Switch", tr("Ring Modulator"),
          tr("Multiplies partial 1's and partial 2's oscillators, for metallic, bell-like sounds; different pitches on the two partials make it clearer."),
          hi=1, choices=on_off, values=(0, 2), page=15),
        S("WAVE_SHAPE", 0x35, "Wave Shape", description=tr("Partial 1 is modulated by the pitch of partial 2; higher values give a greater effect."),
          depends=tr("No effect when partial 1's waveform is PW-SQR or SUPER-SAW."), page=15),
        S("ANALOG_FEEL", 0x34, "Analog Feel", description=tr("Adds \"1/f fluctuation\", the natural instability of an analog synthesizer."), page=15),
    ]
    for p in range(3):
        params.append(S(f"PARTIAL{p + 1}_SWITCH", 0x19 + 2 * p, f"P{p + 1} ON", tr("Partial {n} Switch").format(n=p + 1),
                        tr("Turns the partial on or off (the [05]-[07] buttons)."), hi=1, choices=on_off, page=16))
        params.append(S(f"PARTIAL{p + 1}_SELECT", 0x1A + 2 * p, f"P{p + 1} SEL", tr("Partial {n} Select").format(n=p + 1),
                        tr("Whether the panel knobs edit this partial (the [01]-[03] buttons; several can be selected)."),
                        hi=1, choices=on_off, page=16))
    return Block("COMMON", "COMMON", _address(synth, 0x00), params, request=rq1(_bytes(synth, 0x00), 0x40))


def modify_block(synth: int) -> Block:
    S = PSpec
    params = [
        S("ATTACK_TIME_INTERVAL_SENS", 0x01, "Attack Time", tr("Attack Time Interval Sens"),
          tr("Shortens the filter and amp Attack Time when notes follow each other quickly; 0 has no effect."), page=19),
        S("RELEASE_TIME_INTERVAL_SENS", 0x02, "Release Time", tr("Release Time Interval Sens"),
          tr("Shortens the filter and amp Release Time when a note is short; 0 has no effect."), page=19),
        S("PORTAMENTO_TIME_INTERVAL_SENS", 0x03, "Porta Time", tr("Portamento Time Interval Sens"),
          tr("Shortens the Portamento Time when notes follow each other quickly; 0 has no effect."), page=19),
        S("ENVELOPE_LOOP_MODE", 0x04, "Loop Mode", tr("Envelope Loop Mode"),
          tr("OFF: normal envelope. FREE-RUN: after the Decay it goes back to the Attack until note-off. TEMPO-SYNC: it goes back to the Attack at the Sync Note rate."),
          hi=2, choices=("OFF", "FREE-RUN", "TEMPO-SYNC"), page=19),
        S("ENVELOPE_LOOP_SYNC_NOTE", 0x05, "Sync Note", tr("Envelope Loop Sync Note"),
          tr("Loop rate as a note value."), hi=19, choices=tuple(SYNC_NOTES), kind="list",
          depends=tr("Only with Loop Mode TEMPO-SYNC."), page=19),
        S("CHROMATIC_PORTAMENTO", 0x06, "Chroma Porta", tr("Chromatic Portamento"),
          tr("ON: portamento moves in semitone steps."), hi=1, choices=("OFF", "ON"), page=19),
    ]
    return Block("MODIFY", "MISC", _address(synth, 0x50), params, request=rq1(_bytes(synth, 0x50), 0x25))


def partial_block(synth: int, partial: int) -> Block:
    """Partial 1-3 (*partial* 0-2)."""
    S = PSpec
    n = partial + 1
    signed = dict(lo=-63, hi=63, raw_offset=64, signed=True)
    ring = tr("With the RING Switch ON it has no effect on partials 1 and 2.") if partial < 2 else ""
    pw_only = tr("Only with waveform PW-SQR.")
    pcm_only = tr("Only with waveform PCM.")
    sync_off, sync_on = tr("Used when Tempo Sync is OFF."), tr("Used when Tempo Sync is ON.")

    def p(name, offset, label, group, **kw):
        return S(name, offset, label, group=f"{group} P{n}", page=kw.pop("page", 16), **kw)

    params = [
        # OSC (p. 16)
        p("OSC_WAVE", 0x00, "Waveform", "OSC", hi=7, choices=WAVES,
          description=tr("SAW, SQR, TRI and SINE: basic waveforms; PW-SQR: square with variable width; NOISE: all frequencies; SUPER-SAW: seven detuned saws; PCM: a sampled waveform.")),
        p("OSC_WAVE_VARIATION", 0x01, "Variation", "OSC", hi=2, choices=("A", "B", "C"),
          description=tr("Variations of the selected waveform."), depends=tr("No effect with SUPER-SAW or PCM.")),
        p("WAVE_NUMBER", 0x35, "Wave Number", "OSC", hi=160, size=4, choices=tuple(PCM_WAVES), kind="list",
          description=tr("The PCM waveform."), depends=pcm_only),
        p("WAVE_GAIN", 0x34, "PCM Gain", "OSC", hi=3, choices=("-6 dB", "0 dB", "+6 dB", "+12 dB"), long=tr("Wave Gain"),
          description=tr("Gain of the PCM waveform; each 6 dB step doubles it."), depends=pcm_only),
        p("OSC_PITCH", 0x03, "Pitch", "OSC", lo=-24, hi=24, raw_offset=64, signed=True, unit="st",
          description=tr("Pitch in semitones."), page=17),
        p("OSC_DETUNE", 0x04, "Detune", "OSC", lo=-50, hi=50, raw_offset=64, signed=True, unit="cent",
          description=tr("Pitch in cents."), page=17),
        p("OSC_PULSE_WIDTH", 0x06, "Pulse Width", "OSC",
          description=tr("Width of the upper part of the square wave; higher values give a narrower, more distinctive pulse.") + " " + ring, depends=pw_only),
        p("OSC_PULSE_WIDTH_MOD_DEPTH", 0x05, "PWM Depth", "OSC", long=tr("Pulse Width Mod Depth"),
          description=tr("How much the LFO modulates the pulse width.") + " " + ring, depends=pw_only),
        p("OSC_PULSE_WIDTH_SHIFT", 0x2A, "PW Shift", "OSC", long=tr("Pulse Width Shift"),
          description=tr("Shifts the range of change; normally 127.") + " " + ring, depends=pw_only),
        p("SUPER_SAW_DETUNE", 0x3A, "S-Saw Detune", "OSC", long=tr("Super Saw Detune"),
          description=tr("Pitch difference between the seven saw waves; higher values spread them more.") + " " + ring,
          depends=tr("Only with waveform SUPER-SAW.")),
        p("OSC_PITCH_ENV_ATTACK_TIME", 0x07, "Attack", "OSC", long=tr("Pitch Env Attack Time"),
          description=tr("Time from the key press until the pitch reaches its highest (or lowest) point."), page=17),
        p("OSC_PITCH_ENV_DECAY", 0x08, "Decay", "OSC", long=tr("Pitch Env Decay Time"),
          description=tr("Time from that point until the pitch returns to the key's pitch."), page=17),
        p("OSC_PITCH_ENV_DEPTH", 0x09, "Depth", "OSC", long=tr("Pitch Env Depth"),
          description=tr("How much the pitch envelope changes the pitch."), page=17, **signed),
        # FILTER (p. 17)
        p("FILTER_MODE", 0x0A, "Type", "FILTER", hi=7, choices=FILTERS, kind="list", long=tr("Filter Type"),
          description=tr("Type of filter: low-pass (LPF1-4, different characters), high-pass, band-pass, peaking; BYPASS: none."), page=17),
        p("FILTER_SLOPE", 0x0B, "Slope", "FILTER", hi=1, choices=("-12 dB", "-24 dB"), long=tr("Filter Slope"),
          description=tr("Steepness of the filter."), page=17),
        p("FILTER_CUTOFF", 0x0C, "Cutoff", "FILTER", description=tr("Cutoff frequency."), page=17),
        p("FILTER_RESONANCE", 0x0F, "Resonance", "FILTER", description=tr("Emphasizes the sound around the cutoff frequency."), page=17),
        p("FILTER_CUTOFF_KEYFOLLOW", 0x0D, "Cutoff KF", "FILTER", lo=-100, hi=100, raw_offset=64, factor=10, step=10, signed=True,
          long=tr("Cutoff Key Follow"), description=tr("How the cutoff follows the key played: +100 raises it one octave per octave from C4."), page=17),
        p("FILTER_ENV_VELOCITY_SENS", 0x0E, "Velo Sens", "FILTER", long=tr("Filter Env Velocity Sens"),
          description=tr("How the filter envelope depth changes with how hard you play."), page=17, **signed),
        p("HPF_CUTOFF", 0x39, "HPF Cutoff", "FILTER", long=tr("-6 dB HPF Cutoff"),
          description=tr("Cutoff of an independent -6 dB high-pass filter, after the main filter."), page=18),
        p("FILTER_ENV_ATTACK_TIME", 0x10, "Attack", "FILTER", long=tr("Filter Env Attack"),
          description=tr("Time from the key press until the cutoff reaches its highest (or lowest) point."), page=17),
        p("FILTER_ENV_DECAY_TIME", 0x11, "Decay", "FILTER", long=tr("Filter Env Decay"),
          description=tr("Time from that point until the cutoff reaches the sustain level."), page=17),
        p("FILTER_ENV_SUSTAIN_LEVEL", 0x12, "Sustain", "FILTER", long=tr("Filter Env Sustain"),
          description=tr("Cutoff kept while the key is held after the decay."), page=17),
        p("FILTER_ENV_RELEASE_TIME", 0x13, "Release", "FILTER", long=tr("Filter Env Release"),
          description=tr("Time from the key release until the cutoff reaches its minimum."), page=17),
        p("FILTER_ENV_DEPTH", 0x14, "Depth", "FILTER", long=tr("Filter Env Depth"),
          description=tr("Direction and amount of the cutoff change made by the envelope."), page=17, **signed),
        # AMP (p. 18)
        p("AMP_LEVEL", 0x15, "Level", "AMP", description=tr("Volume of the partial."), page=18),
        p("AMP_VELOCITY", 0x16, "Level V-Sens", "AMP", long=tr("Amp Level Velocity Sens"),
          description=tr("How the volume changes with how hard you play."), page=18, **signed),
        p("AMP_PAN", 0x1B, "Pan", "AMP", lo=-64, hi=63, raw_offset=64, fmt=pan_text, parse=pan_parse,
          description=tr("Stereo position of the partial."), page=18),
        p("AMP_LEVEL_KEYFOLLOW", 0x3C, "Key Follow", "AMP", lo=-100, hi=100, raw_offset=64, factor=10, step=10, signed=True,
          long=tr("Amp Level Key Follow"), description=tr("Positive: louder as you play higher than C4; negative: softer."), page=18),
        p("AMP_ENV_ATTACK_TIME", 0x17, "Attack", "AMP", long=tr("Amp Env Attack"),
          description=tr("Time from the key press until the maximum volume."), page=18),
        p("AMP_ENV_DECAY_TIME", 0x18, "Decay", "AMP", long=tr("Amp Env Decay"),
          description=tr("Time from the maximum volume until the sustain level."), page=18),
        p("AMP_ENV_SUSTAIN_LEVEL", 0x19, "Sustain", "AMP", long=tr("Amp Env Sustain"),
          description=tr("Volume kept while the key is held."), page=18),
        p("AMP_ENV_RELEASE_TIME", 0x1A, "Release", "AMP", long=tr("Amp Env Release"),
          description=tr("Time from the key release until silence."), page=18),
        # LFO (p. 18)
        p("LFO_SHAPE", 0x1C, "Shape", "LFO", hi=5, choices=LFO_SHAPES, description=tr("LFO waveform; S&H changes once per cycle, RND is random."), page=18),
        p("LFO_RATE", 0x1D, "Rate", "LFO", description=tr("LFO speed."), depends=sync_off, page=18),
        p("LFO_TEMPO_SYNC_SWITCH", 0x1E, "Tempo Sync", "LFO", hi=1, choices=("OFF", "ON"),
          description=tr("ON: the LFO speed is a note value relative to the tempo."), page=18),
        p("LFO_TEMPO_SYNC_NOTE", 0x1F, "Sync Note", "LFO", hi=19, choices=tuple(SYNC_NOTES), kind="list",
          description=tr("LFO speed as a note value."), depends=sync_on, page=18),
        p("LFO_FADE_TIME", 0x20, "Fade Time", "LFO", description=tr("Time from when the partial sounds until the LFO reaches its full amplitude."), page=18),
        p("LFO_KEY_TRIGGER", 0x21, "Key Trigger", "LFO", hi=1, choices=("OFF", "ON"),
          description=tr("ON: the LFO cycle restarts at each key press."), page=18),
        p("LFO_PITCH_DEPTH", 0x22, "Pitch", "LFO", long=tr("LFO Pitch Depth"), description=tr("Vibrato: the LFO modulates the pitch."), page=18, **signed),
        p("LFO_FILTER_DEPTH", 0x23, "Filter", "LFO", long=tr("LFO Filter Depth"), description=tr("Wah: the LFO modulates the cutoff."), page=18, **signed),
        p("LFO_AMP_DEPTH", 0x24, "Amp", "LFO", long=tr("LFO Amp Depth"), description=tr("Tremolo: the LFO modulates the volume."), page=18, **signed),
        p("LFO_PAN_DEPTH", 0x25, "Pan", "LFO", long=tr("LFO Pan Depth"), description=tr("Auto-pan: the LFO modulates the stereo position."), page=18, **signed),
        # MODULATION LFO (p. 19), applied with the modulation lever (CC01)
        p("MOD_LFO_SHAPE", 0x26, "Shape", "MOD LFO", hi=5, choices=LFO_SHAPES,
          description=tr("Waveform of the Modulation LFO, applied with the modulation lever (CC01)."), page=19),
        p("MOD_LFO_RATE", 0x27, "Rate", "MOD LFO", description=tr("Modulation LFO speed."), depends=sync_off, page=19),
        p("MOD_LFO_TEMPO_SYNC_SWITCH", 0x28, "TempoSync", "MOD LFO", hi=1, choices=("OFF", "ON"),
          description=tr("ON: the Modulation LFO speed is a note value relative to the tempo."), page=19),
        p("MOD_LFO_TEMPO_SYNC_NOTE", 0x29, "Sync Note", "MOD LFO", hi=19, choices=tuple(SYNC_NOTES), kind="list",
          description=tr("Modulation LFO speed as a note value."), depends=sync_on, page=19),
        p("MOD_LFO_PITCH_DEPTH", 0x2C, "Pitch", "MOD LFO", long=tr("Mod LFO Pitch Depth"), description=tr("Vibrato: the LFO modulates the pitch."), page=19, **signed),
        p("MOD_LFO_FILTER_DEPTH", 0x2D, "Filter", "MOD LFO", long=tr("Mod LFO Filter Depth"), description=tr("Wah: the LFO modulates the cutoff."), page=19, **signed),
        p("MOD_LFO_AMP_DEPTH", 0x2E, "Amp", "MOD LFO", long=tr("Mod LFO Amp Depth"), description=tr("Tremolo: the LFO modulates the volume."), page=19, **signed),
        p("MOD_LFO_PAN_DEPTH", 0x2F, "Pan", "MOD LFO", long=tr("Mod LFO Pan Depth"), description=tr("Auto-pan: the LFO modulates the stereo position."), page=19, **signed),
        p("MOD_LFO_RATE_CONTROL", 0x3B, "Rate Ctrl", "MOD LFO", long=tr("Mod LFO Rate Control"),
          description=tr("Positive: the Modulation LFO gets faster as you raise the modulation lever; negative: slower."), page=19, **signed),
        # AFTERTOUCH (p. 19)
        p("CUTOFF_AFTERTOUCH_SENS", 0x30, "Cutoff Sens", "AFTERTOUCH", long=tr("Cutoff Aftertouch Sens"),
          description=tr("Positive: the cutoff rises with aftertouch pressure; negative: it falls."), page=19, **signed),
        p("LEVEL_AFTERTOUCH_SENS", 0x31, "Level Sens", "AFTERTOUCH", long=tr("Level Aftertouch Sens"),
          description=tr("Positive: the volume rises with aftertouch pressure; negative: it falls."), page=19, **signed),
    ]
    return Block(f"PARTIAL_{n}", f"PARTIAL {n}", _address(synth, 0x20 + partial), params,
                 request=rq1(_bytes(synth, 0x20 + partial), 0x3D))


class DigitalFilterView(FilterCurveView):
    """The filter response for every type of the digital partial: LPF, HPF, BPF, peaking; -12 or -24 dB."""

    def __init__(self, accent, hub, cutoff, resonance, mode, slope):
        self.slope = slope
        super().__init__(accent, hub, cutoff, resonance, mode)
        slope.watch(lambda _v: self.update())

    def _response_db(self, f: float) -> float:
        kind = FILTERS[self.mode.value()]
        fc = self.frequency(self.cutoff.value())
        q = 0.7 + self.resonance.value() / 127.0 * 8.0
        u = f / fc
        order = 2 if self.slope.value() else 1
        if kind == "HPF":
            h = u * u / math.sqrt((1 - u * u) ** 2 + (u / q) ** 2)
        elif kind == "BPF":
            h = (u / q) / math.sqrt((1 - u * u) ** 2 + (u / q) ** 2)
        elif kind == "PKG":
            peak = 1 + q
            return 20 * math.log10(1 + (peak - 1) / (1 + ((u - 1 / u) * q) ** 2))
        else:  # the low-pass types
            h = 1.0 / math.sqrt((1 - u * u) ** 2 + (u / q) ** 2)
        return 20 * math.log10(max(h ** order, 1e-6))


class DigitalToneEditor(tone_editor_base()):
    """Digital Synth 1 or 2: common, the three partials and the modifiers."""

    ACCENT = ACCENT

    def __init__(self, midi_helper=None, preset_helper=None, parent=None, synth_number: int = 1):
        self.SYNTH_TYPE = JDXiSynth.DIGITAL_SYNTH_1 if synth_number == 1 else JDXiSynth.DIGITAL_SYNTH_2
        self.synth_number = synth_number  # before the frame: the preset panel shows it
        blocks = [common_block(synth_number), modify_block(synth_number)] + [partial_block(synth_number, i) for i in range(3)]
        super().__init__(blocks, midi_helper=midi_helper, parent=parent,
                         title=tr("Digital Synth {n}").format(n=synth_number))
        self.synth_number = synth_number
        self.preset_helper = preset_helper
        self._link_dependencies()

    def partial(self, name: str, partial: int) -> ParamValue:
        return self.pv(name, f"PARTIAL_{partial + 1}")

    # --- layout
    def build_panels(self) -> None:
        self.panels_layout.addWidget(self._common_card())
        self.panels_layout.addLayout(self._partial_strip())
        self.partial_pages = QStackedWidget()
        for partial in range(3):
            self.partial_pages.addWidget(self._partial_page(partial))
        self.panels_layout.addWidget(self.partial_pages)
        self.show_partial(0)
        self.panels_layout.addWidget(self.note(
            tr("Changes are heard at once and kept in the current program until another one is selected. "
               "To keep them, save the program on the JD-Xi with [Menu/Write]: the JD-Xi cannot be written to its memory via MIDI.")
        ))
        self.panels_layout.addStretch()

    def _common_card(self):
        card = self.card("TONE: COMMON", tr("Parameter Guide, p. 15"))
        top = QHBoxLayout()
        box = QVBoxLayout()
        label = QLabel(tr("Tone Name"))
        label.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        box.addWidget(label)
        names = [self.values[s] for s in self.blocks[0].params[:NAME_LENGTH]]
        self.name_field = NameField(self, names, self.blocks[0].address, tr("Name of the tone (12 characters)."))
        box.addWidget(self.name_field)
        box.addStretch()
        top.addLayout(box)
        s = self.spec
        for name in ("TONE_LEVEL", "TONE_CATEGORY", "OCTAVE_SHIFT", "PITCH_BEND_RANGE_UP", "PITCH_BEND_RANGE_DOWN",
                     "PORTAMENTO_TIME", "WAVE_SHAPE", "ANALOG_FEEL"):
            top.addWidget(self.control(s(name)))
        top.addStretch()
        card.body.addLayout(top)
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        switches = ["MONO_SWITCH", "LEGATO_SWITCH", "PORTAMENTO_SWITCH", "PORTAMENTO_MODE", "UNISON_SWITCH", "UNISON_SIZE", "RING_SWITCH"]
        for i, name in enumerate(switches):
            grid.addWidget(self.control(s(name)), i // 4, i % 4)
        card.body.addLayout(grid)
        return card

    def _partial_strip(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.partial_buttons = QButtonGroup(self)
        for partial in range(3):
            n = partial + 1
            box = QVBoxLayout()
            button = QPushButton(tr("PARTIAL {n}").format(n=n))
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { background: #1b1c1f; color: #c9cbd1; border: 1px solid #3a3d44; border-radius: 6px;"
                " padding: 6px 18px; font-weight: 700; letter-spacing: 1px; }"
                f"QPushButton:checked {{ background: {self.ACCENT}; color: #0e0f11; border-color: {self.ACCENT}; }}"
            )
            button.setToolTip(tr("Edit partial {n}").format(n=n))
            self.partial_buttons.addButton(button, partial)
            box.addWidget(button)
            line = QHBoxLayout()
            line.addWidget(ChoiceButtons(self.pv(f"PARTIAL{n}_SWITCH"), self.ACCENT, self.info_hub))
            line.addWidget(ChoiceButtons(self.pv(f"PARTIAL{n}_SELECT"), self.ACCENT, self.info_hub))
            line.addStretch()
            box.addLayout(line)
            row.addLayout(box)
            switch = self.pv(f"PARTIAL{n}_SWITCH")
            switch.watch(lambda v, b=button, n=n: b.setText(tr("PARTIAL {n}").format(n=n) + ("" if v else "  ·  OFF")))
        row.addStretch()
        self.partial_buttons.idClicked.connect(self.show_partial)
        return row

    def show_partial(self, index: int) -> None:
        for i in range(self.partial_pages.count()):
            policy = QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored
            self.partial_pages.widget(i).setSizePolicy(policy, policy)
        self.partial_pages.setCurrentIndex(index)
        button = self.partial_buttons.button(index)
        if not button.isChecked():
            button.setChecked(True)
        self.partial_pages.adjustSize()

    def _partial_page(self, partial: int) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)
        v = lambda name: self.partial(name, partial)  # noqa: E731
        s = lambda name: v(name).param  # noqa: E731
        top = Qt.AlignmentFlag.AlignTop

        osc = self.card("OSC", tr("Parameter Guide, p. 16-17"))
        osc.body.addWidget(WaveButtons(v("OSC_WAVE"), self.ACCENT, self.info_hub, pulse_width=v("OSC_PULSE_WIDTH"), button_width=44))
        osc.body.addWidget(self.control(s("OSC_WAVE_VARIATION")))
        osc.body.addWidget(self.control(s("WAVE_NUMBER")))
        osc.body.addWidget(self.control(s("WAVE_GAIN")))
        osc.body.addLayout(self.knob_row([s("OSC_PITCH"), s("OSC_DETUNE"), s("SUPER_SAW_DETUNE")]))
        osc.body.addLayout(self.knob_row([s("OSC_PULSE_WIDTH"), s("OSC_PULSE_WIDTH_MOD_DEPTH"), s("OSC_PULSE_WIDTH_SHIFT")]))
        osc.body.addWidget(EnvelopeView(self.ACCENT, self.info_hub, v("OSC_PITCH_ENV_ATTACK_TIME"), v("OSC_PITCH_ENV_DECAY"),
                                        depth=v("OSC_PITCH_ENV_DEPTH")))
        osc.body.addLayout(self.knob_row([s("OSC_PITCH_ENV_ATTACK_TIME"), s("OSC_PITCH_ENV_DECAY"), s("OSC_PITCH_ENV_DEPTH")]))
        grid.addWidget(osc, 0, 0, top)

        flt = self.card("FILTER", tr("Parameter Guide, p. 17-18"))
        flt.body.addWidget(self.control(s("FILTER_MODE")))
        flt.body.addWidget(self.control(s("FILTER_SLOPE")))
        flt.body.addWidget(DigitalFilterView(self.ACCENT, self.info_hub, v("FILTER_CUTOFF"), v("FILTER_RESONANCE"), v("FILTER_MODE"), v("FILTER_SLOPE")))
        flt.body.addLayout(self.knob_row([s("FILTER_CUTOFF"), s("FILTER_RESONANCE"), s("FILTER_CUTOFF_KEYFOLLOW"), s("HPF_CUTOFF")]))
        flt.body.addWidget(EnvelopeView(self.ACCENT, self.info_hub, v("FILTER_ENV_ATTACK_TIME"), v("FILTER_ENV_DECAY_TIME"),
                                        v("FILTER_ENV_SUSTAIN_LEVEL"), v("FILTER_ENV_RELEASE_TIME")))
        flt.body.addLayout(self.knob_row([s("FILTER_ENV_ATTACK_TIME"), s("FILTER_ENV_DECAY_TIME"), s("FILTER_ENV_SUSTAIN_LEVEL"),
                                          s("FILTER_ENV_RELEASE_TIME")]))
        flt.body.addLayout(self.knob_row([s("FILTER_ENV_DEPTH"), s("FILTER_ENV_VELOCITY_SENS")]))
        grid.addWidget(flt, 0, 1, top)

        amp = self.card("AMP", tr("Parameter Guide, p. 18"))
        amp.body.addWidget(EnvelopeView(self.ACCENT, self.info_hub, v("AMP_ENV_ATTACK_TIME"), v("AMP_ENV_DECAY_TIME"),
                                        v("AMP_ENV_SUSTAIN_LEVEL"), v("AMP_ENV_RELEASE_TIME")))
        amp.body.addLayout(self.knob_row([s("AMP_ENV_ATTACK_TIME"), s("AMP_ENV_DECAY_TIME"), s("AMP_ENV_SUSTAIN_LEVEL"),
                                          s("AMP_ENV_RELEASE_TIME")]))
        amp.body.addLayout(self.knob_row([s("AMP_LEVEL"), s("AMP_VELOCITY"), s("AMP_PAN"), s("AMP_LEVEL_KEYFOLLOW")]))
        at = QLabel(tr("AFTERTOUCH"))
        at.setStyleSheet(f"color: {self.ACCENT}; font-size: 10px; letter-spacing: 1px; background: transparent;")
        amp.body.addWidget(at)
        amp.body.addLayout(self.knob_row([s("CUTOFF_AFTERTOUCH_SENS"), s("LEVEL_AFTERTOUCH_SENS")]))
        grid.addWidget(amp, 0, 2, top)

        for col, (title, prefix, fade) in enumerate((("LFO", "LFO_", True), ("MOD LFO", "MOD_LFO_", False))):
            card = self.card(title, tr("Parameter Guide, p. 18") if fade else tr("Parameter Guide, p. 19 (modulation lever)"))
            card.body.addWidget(LfoView(self.ACCENT, self.info_hub, v(prefix + "SHAPE"), v(prefix + "RATE"),
                                        v("LFO_FADE_TIME") if fade else None, v(prefix + "TEMPO_SYNC_SWITCH"), v(prefix + "TEMPO_SYNC_NOTE")))
            card.body.addWidget(WaveButtons(v(prefix + "SHAPE"), self.ACCENT, self.info_hub, button_width=44))
            card.body.addWidget(self.control(s(prefix + "TEMPO_SYNC_SWITCH")))
            card.body.addWidget(self.control(s(prefix + "TEMPO_SYNC_NOTE")))
            if fade:
                card.body.addWidget(self.control(s("LFO_KEY_TRIGGER")))
                card.body.addLayout(self.knob_row([s("LFO_RATE"), s("LFO_FADE_TIME")]))
            else:
                card.body.addLayout(self.knob_row([s("MOD_LFO_RATE"), s("MOD_LFO_RATE_CONTROL")]))
            card.body.addLayout(self.knob_row([s(prefix + "PITCH_DEPTH"), s(prefix + "FILTER_DEPTH"), s(prefix + "AMP_DEPTH"),
                                               s(prefix + "PAN_DEPTH")]))
            grid.addWidget(card, 1, col, top)

        misc = self.card("MISC", tr("Parameter Guide, p. 19 (whole tone)"))
        for name in ("ENVELOPE_LOOP_MODE", "ENVELOPE_LOOP_SYNC_NOTE", "CHROMATIC_PORTAMENTO"):
            misc.body.addWidget(self.control(self.spec(name)))
        misc.body.addLayout(self.knob_row([self.spec("ATTACK_TIME_INTERVAL_SENS"), self.spec("RELEASE_TIME_INTERVAL_SENS"),
                                           self.spec("PORTAMENTO_TIME_INTERVAL_SENS")]))
        grid.addWidget(misc, 1, 2, top)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        return page

    # --- which controls have an effect
    def _link_dependencies(self) -> None:
        def link(sources: list[ParamValue], rule, targets: list[ParamValue]):
            def apply(_v=None):
                on = rule(*(src.value() for src in sources))
                for t in targets:
                    t.set_enabled(on)
            for src in sources:
                src.watch(apply)

        mono, porta = self.pv("MONO_SWITCH"), self.pv("PORTAMENTO_SWITCH")
        link([mono], lambda m: m == 1, [self.pv("LEGATO_SWITCH")])
        link([porta], lambda p: p == 1, [self.pv("PORTAMENTO_TIME"), self.pv("PORTAMENTO_MODE")])
        link([self.pv("UNISON_SWITCH")], lambda u: u == 1, [self.pv("UNISON_SIZE")])
        link([self.pv("ENVELOPE_LOOP_MODE")], lambda m: m == 2, [self.pv("ENVELOPE_LOOP_SYNC_NOTE")])
        link([self.partial("OSC_WAVE", 0)], lambda w: WAVES[w] not in ("PW-SQR", "SP-SAW"), [self.pv("WAVE_SHAPE")])
        ring = self.pv("RING_SWITCH")
        for partial in range(3):
            v = lambda name, partial=partial: self.partial(name, partial)  # noqa: E731
            wave = v("OSC_WAVE")
            ringed = partial < 2

            def pw_rule(w, r, ringed=ringed):
                return WAVES[w] == "PW-SQR" and not (ringed and r == 1)

            def saw_rule(w, r, ringed=ringed):
                return WAVES[w] == "SP-SAW" and not (ringed and r == 1)

            link([wave, ring], pw_rule, [v("OSC_PULSE_WIDTH"), v("OSC_PULSE_WIDTH_MOD_DEPTH"), v("OSC_PULSE_WIDTH_SHIFT")])
            link([wave, ring], saw_rule, [v("SUPER_SAW_DETUNE")])
            link([wave], lambda w: WAVES[w] == "PCM", [v("WAVE_NUMBER"), v("WAVE_GAIN")])
            link([wave], lambda w: WAVES[w] not in ("SP-SAW", "PCM"), [v("OSC_WAVE_VARIATION")])
            link([v("FILTER_MODE")], lambda m: m != 0,
                 [v("FILTER_CUTOFF"), v("FILTER_RESONANCE"), v("FILTER_CUTOFF_KEYFOLLOW"), v("FILTER_SLOPE"),
                  v("FILTER_ENV_DEPTH"), v("FILTER_ENV_VELOCITY_SENS")])
            for prefix in ("LFO_", "MOD_LFO_"):
                sync = v(prefix + "TEMPO_SYNC_SWITCH")
                link([sync], lambda x: x == 0, [v(prefix + "RATE")])
                link([sync], lambda x: x == 1, [v(prefix + "TEMPO_SYNC_NOTE")])


class Digital2ToneEditor(DigitalToneEditor):
    ACCENT = ACCENT_2

    def __init__(self, midi_helper=None, preset_helper=None, parent=None, synth_number: int = 2):
        super().__init__(midi_helper, preset_helper, parent, synth_number=2)
