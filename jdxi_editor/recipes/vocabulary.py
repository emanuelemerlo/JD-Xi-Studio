"""Vocabolario dei parametri per il modello ricette.

Nomi e intervalli come sul display del JD-Xi, dalla Parameter Guide (e01)
e dal Leaflet v1.50 (side chain del compressore). Ogni voce:
(parte, gruppo, parametro, nome esteso, tipo, min, max, scelte, unità, su, note)
tipo: numero | scelta | numero o scelta | pan | D:W | nota | testo
su:   sì | facoltativo | no
"""

NOTES = "16, 12, 8, 4, 2, 1, 3/4, 2/3, 1/2, 3/8, 1/3, 1/4, 3/16, 1/6, 1/8, 3/32, 1/12, 1/16, 1/24, 1/32"
SW = "OFF, ON"
LFO_SHAPES = "TRI, SIN, SAW, SQR, S&H, RND"
OUT5 = "EFX1, EFX2, DLY, REV, DIR"
VCURVE = "FIXED, 1, 2, 3, 4, 5, 6, 7"

R = []


def add(parte, gruppo, par, lungo="", tipo="numero", lo=None, hi=None, scelte="", unita="", su="no", note=""):
    R.append((parte, gruppo, par, lungo, tipo, lo, hi, scelte, unita, su, note))


def adsr(parte, gruppo, su, prefix=""):
    for p, l in [("Attack", "Attack Time"), ("Decay", "Decay Time"), ("Sustain", "Sustain Level"), ("Release", "Release Time")]:
        add(parte, gruppo, p, f"{prefix} Envelope {l}".strip(), "numero", 0, 127, su=su)


# ---------------- ANALOG ----------------
A = "AN"
add(A, "COMMON", "Porta Sw", "Portamento Switch", "scelta", scelte=SW)
add(A, "COMMON", "Porta Time", "Portamento Time", "numero", 0, 127)
add(A, "COMMON", "Legato Sw", "Legato Switch", "scelta", scelte=SW)
add(A, "COMMON", "Octave Shift", "", "numero", -3, 3)
add(A, "COMMON", "Bend Range U", "Pitch Bend Range Up", "numero", 0, 24, unita="semitoni")
add(A, "COMMON", "Bend Range D", "Pitch Bend Range Down", "numero", -24, 0, unita="semitoni")
add(A, "OSC", "Waveform", "", "scelta", scelte="SAW, TRI, PW-SQR")
add(A, "OSC", "PWM Depth", "Pulse Width Modulation Depth", "numero", 0, 127)
add(A, "OSC", "Pulse Width", "", "numero", 0, 127)
add(A, "OSC", "Sub OSC", "Sub Oscillator", "scelta", scelte="OFF, OCT-1, OCT-2")
add(A, "PITCH", "OSC Pitch", "", "numero", -24, 24, unita="semitoni")
add(A, "PITCH", "OSC Detune", "", "numero", -50, 50, unita="cent")
add(A, "PITCH", "Env Attack", "Pitch Envelope Attack Time", "numero", 0, 127)
add(A, "PITCH", "Env Decay", "Pitch Envelope Decay Time", "numero", 0, 127)
add(A, "PITCH", "Env Depth", "Pitch Envelope Depth", "numero", -63, 63)
add(A, "FILTER", "Type", "Filter Type", "scelta", scelte="BYPASS, LPF")
add(A, "FILTER", "Cutoff", "", "numero", 0, 127)
add(A, "FILTER", "Cutoff KF", "Cutoff Key Follow", "numero", -100, 100)
add(A, "FILTER", "Velo Sens", "Filter Envelope Velocity Sense", "numero", -63, 63)
add(A, "FILTER", "Resonance", "", "numero", 0, 127)
adsr(A, "FILTER", "no", "Filter")
add(A, "FILTER", "Depth", "Filter Envelope Depth", "numero", -63, 63)
add(A, "AMP", "AMP Level", "", "numero", 0, 127)
add(A, "AMP", "Level V-Sens", "Amp Level Velocity Sense", "numero", -63, 63)
add(A, "AMP", "Level KF", "Amp Level Key Follow", "numero", -100, 100)
adsr(A, "AMP", "no", "Amp")
add(A, "LFO", "Shape", "LFO Shape", "scelta", scelte=LFO_SHAPES)
add(A, "LFO", "Rate", "LFO Rate", "numero", 0, 127)
add(A, "LFO", "Tempo Sync", "LFO Tempo Sync Switch", "scelta", scelte=SW)
add(A, "LFO", "Sync Note", "LFO Tempo Sync Note", "scelta", scelte=NOTES)
add(A, "LFO", "Fade Time", "LFO Fade Time", "numero", 0, 127)
add(A, "LFO", "Key Trigger", "LFO Key Trigger", "scelta", scelte=SW)
for p in ["Pitch Depth", "Filter Depth", "Amp Depth"]:
    add(A, "LFO", p, f"LFO {p}", "numero", -63, 63)
for p, l in [("Mod Pitch", "Modulation Pitch Depth"), ("Mod Filter", "Modulation Filter Depth"), ("Mod Amp", "Modulation Amp Depth"), ("Mod Rate", "Modulation Rate")]:
    add(A, "LFO", p, l, "numero", -63, 63, note="Effetto con la modulation wheel")

# ---------------- DIGITAL 1 / 2 ----------------
for D in ("D1", "D2"):
    f = "facoltativo"
    add(D, "COMMON", "Partial Switch", "Accende/spegne un partial (pulsanti 05–07)", "scelta", scelte=SW, su="sì")
    add(D, "COMMON", "Tone Level", "", "numero", 0, 127)
    add(D, "COMMON", "RING Switch", "Ring Modulator", "scelta", scelte=SW)
    add(D, "COMMON", "Wave Shape", "", "numero", 0, 127)
    add(D, "COMMON", "Analog Feel", "", "numero", 0, 127)
    add(D, "COMMON", "Unison SW", "Unison Switch", "scelta", scelte=SW)
    add(D, "COMMON", "Unison Size", "", "scelta", scelte="2, 4, 6, 8")
    add(D, "COMMON", "Mono/Poly", "", "scelta", scelte="POLY, MONO")
    add(D, "COMMON", "Legato SW", "Legato Switch", "scelta", scelte=SW)
    add(D, "COMMON", "Porta SW", "Portamento Switch", "scelta", scelte=SW)
    add(D, "COMMON", "Porta Time", "Portamento Time", "numero", 0, 127)
    add(D, "COMMON", "Porta Mode", "Portamento Mode", "scelta", scelte="NORMAL, LEGATO")
    add(D, "COMMON", "Octave Shift", "", "numero", -3, 3)
    add(D, "COMMON", "Bend Range U", "Pitch Bend Range Up", "numero", 0, 24, unita="semitoni")
    add(D, "COMMON", "Bend Range D", "Pitch Bend Range Down", "numero", -24, 0, unita="semitoni")
    add(D, "OSC", "Waveform", "", "scelta", scelte="SAW, SQR, PW-SQR, TRI, SINE, NOISE, SUPER-SAW, PCM", su=f)
    add(D, "OSC", "Variation", "Wave Variation", "scelta", scelte="A, B, C", su=f)
    add(D, "OSC", "Wave Number", "PCM Wave Number", "numero", 1, 160, su=f, note="Solo con Waveform PCM")
    add(D, "OSC", "PCM Gain", "Wave Gain", "scelta", scelte="-6, 0, +6, +12", unita="dB", su=f)
    add(D, "OSC", "PWM Depth", "Pulse Width Mod Depth", "numero", 0, 127, su=f)
    add(D, "OSC", "Pulse Width", "", "numero", 0, 127, su=f)
    add(D, "OSC", "PW Shift", "Pulse Width Shift", "numero", 0, 127, su=f)
    add(D, "OSC", "S-Saw Detune", "Super Saw Detune", "numero", 0, 127, su=f)
    add(D, "PITCH", "Pitch", "OSC Pitch", "numero", -24, 24, unita="semitoni", su=f)
    add(D, "PITCH", "Detune", "OSC Detune", "numero", -50, 50, unita="cent", su=f)
    add(D, "PITCH", "Attack", "Pitch Env Attack Time", "numero", 0, 127, su=f)
    add(D, "PITCH", "Decay", "Pitch Env Decay Time", "numero", 0, 127, su=f)
    add(D, "PITCH", "Depth", "Pitch Env Depth", "numero", -63, 63, su=f)
    add(D, "FILTER", "Type", "Filter Mode", "scelta", scelte="BYPASS, LPF1, LPF2, LPF3, LPF4, HPF, BPF, PKG", su=f)
    add(D, "FILTER", "Slope", "Filter Slope", "scelta", scelte="-12, -24", unita="dB", su=f)
    add(D, "FILTER", "Cutoff", "", "numero", 0, 127, su=f)
    add(D, "FILTER", "Cutoff KF", "Cutoff Key Follow", "numero", -100, 100, su=f)
    add(D, "FILTER", "Velo Sens", "Filter Env Velocity Sens", "numero", -63, 63, su=f)
    add(D, "FILTER", "Resonance", "", "numero", 0, 127, su=f)
    adsr(D, "FILTER", f, "Filter")
    add(D, "FILTER", "Depth", "Filter Env Depth", "numero", -63, 63, su=f)
    add(D, "FILTER", "HPF Cutoff", "", "numero", 0, 127, su=f)
    add(D, "AMP", "Level", "Amp Level", "numero", 0, 127, su=f)
    add(D, "AMP", "Level V-Sens", "Amp Level Velocity Sens", "numero", -63, 63, su=f)
    add(D, "AMP", "Pan", "", "pan", -64, 63, su=f, note="L64 … C … 63R oppure -64 … 63")
    add(D, "AMP", "Key Follow", "Amp Level Key Follow", "numero", -100, 100, su=f)
    adsr(D, "AMP", f, "Amp")
    for g in ("LFO", "MOD LFO"):
        add(D, g, "Shape", f"{g} Shape", "scelta", scelte=LFO_SHAPES, su=f)
        add(D, g, "Rate", f"{g} Rate", "numero", 0, 127, su=f)
        add(D, g, "Tempo Sync", f"{g} Tempo Sync", "scelta", scelte=SW, su=f)
        add(D, g, "Sync Note", f"{g} Tempo Sync Note", "scelta", scelte=NOTES, su=f)
        if g == "LFO":
            add(D, g, "Fade Time", "LFO Fade Time", "numero", 0, 127, su=f)
            add(D, g, "Key Trigger", "LFO Key Trigger", "scelta", scelte=SW, su=f)
        for p in ["Pitch Depth", "Filter Depth", "Amp Depth", "Pan Depth"]:
            add(D, g, p, f"{g} {p}", "numero", -63, 63, su=f)
        if g == "MOD LFO":
            add(D, g, "Rate Control", "Mod LFO Rate Control", "numero", -63, 63, su=f, note="Effetto con la modulation wheel")
    add(D, "AFT", "Cutoff Sens", "Cutoff Aftertouch Sens", "numero", -63, 63, su=f)
    add(D, "AFT", "Level Sens", "Level Aftertouch Sens", "numero", -63, 63, su=f)
    add(D, "MISC", "Attack Time", "Attack Time Interval Sens", "numero", 0, 127)
    add(D, "MISC", "Release Time", "Release Time Interval Sens", "numero", 0, 127)
    add(D, "MISC", "Porta Time", "Portamento Time Interval Sens", "numero", 0, 127)
    add(D, "MISC", "Mode", "Envelope Loop Mode", "scelta", scelte="OFF, FREE-RUN, TEMPO-SYNC")
    add(D, "MISC", "Sync Note", "Envelope Loop Sync Note", "scelta", scelte=NOTES)
    add(D, "MISC", "Chroma Porta", "Chromatic Portamento", "scelta", scelte=SW)

# ---------------- DRUMS ----------------
K = "DR"
s = "sì"
add(K, "COMMON", "Kit Level", "", "numero", 0, 127, note="Vale per tutto il kit")
add(K, "COMMON", "Assign", "Assign Type", "scelta", scelte="MULTI, SINGLE", su=s)
add(K, "COMMON", "Mute Group", "", "numero o scelta", 1, 31, scelte="OFF", su=s)
add(K, "COMMON", "Env Mode", "", "scelta", scelte="NO-SUS, SUSTAIN", su=s)
add(K, "COMMON", "Bend Range", "Pitch Bend Range", "numero", 0, 48, su=s)
add(K, "COMMON", "Rx Expression", "Receive Expression", "scelta", scelte=SW, su=s)
add(K, "COMMON", "Rx Hold-1", "Receive Hold-1", "scelta", scelte=SW, su=s)
add(K, "COMMON", "One Shot Mode", "", "scelta", scelte=SW, su=s)
wn = "Su = strumento/onda, es. SD1/W2"
add(K, "WAVE", "Wave Switch", "Accende l'onda (W1–W4)", "scelta", scelte=SW, su=s, note=wn)
add(K, "WAVE", "No.L (Mono)", "Wave Number L (Mono)", "numero o scelta", 1, 453, scelte="OFF", su=s, note=wn)
add(K, "WAVE", "No.R", "Wave Number R", "numero o scelta", 1, 453, scelte="OFF", su=s, note=wn)
add(K, "WAVE", "Gain", "Wave Gain", "scelta", scelte="-6, 0, +6, +12", unita="dB", su=s, note=wn)
add(K, "WAVE", "FXM Switch", "", "scelta", scelte=SW, su=s, note=wn)
add(K, "WAVE", "FXM Color", "", "numero", 1, 4, su=s, note=wn)
add(K, "WAVE", "FXM Depth", "", "numero", 0, 16, su=s, note=wn)
add(K, "WAVE", "Coarse Tune", "Wave Coarse Tune", "numero", -48, 48, unita="semitoni", su=s, note=wn)
add(K, "WAVE", "Fine Tune", "Wave Fine Tune", "numero", -50, 50, unita="cent", su=s, note=wn)
add(K, "WAVE", "Level", "Wave Level", "numero", 0, 127, su=s, note=wn)
add(K, "WAVE", "Pan", "Wave Pan", "pan", -64, 63, su=s, note=wn)
add(K, "WAVE", "Random Pan Sw", "Random Pan Switch", "scelta", scelte=SW, su=s, note=wn)
add(K, "WAVE", "Alter Pan Sw", "Alternate Pan Switch", "scelta", scelte="OFF, ON, REVERSE", su=s, note=wn)
add(K, "WMT", "WMT Vel Ctrl", "WMT Velocity Control", "scelta", scelte="OFF, ON, RANDOM", su=s, note="Su = strumento")
add(K, "WMT", "Vel Fade L", "Velo Fade Lower", "numero", 0, 127, su=s, note=wn)
add(K, "WMT", "Vel Range L", "Velo Range Lower", "numero", 1, 127, su=s, note=wn)
add(K, "WMT", "Vel Range U", "Velo Range Upper", "numero", 1, 127, su=s, note=wn)
add(K, "WMT", "Vel Fade U", "Velo Fade Upper", "numero", 0, 127, su=s, note=wn)
add(K, "PITCH", "Coarse Tune", "Partial Coarse Tune", "nota", scelte="", su=s, note="Nota da C-1 a G9, es. C4")
add(K, "PITCH", "Fine Tune", "Partial Fine Tune", "numero", -50, 50, unita="cent", su=s)
add(K, "PITCH", "Rnd Pch Dpth", "Random Pitch Depth", "scelta", scelte="0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200", unita="cent", su=s)
add(K, "PITCH ENV", "Env Depth", "Pitch Env Depth", "numero", -12, 12, su=s)
add(K, "PITCH ENV", "Env V-Sens", "Pitch Env Velocity Sens", "numero", -63, 63, su=s)
add(K, "PITCH ENV", "Env T1 V-Sens", "Pitch Env Time 1 Velocity Sens", "numero", -63, 63, su=s)
add(K, "PITCH ENV", "Env T4 V-Sens", "Pitch Env Time 4 Velocity Sens", "numero", -63, 63, su=s)
for i in range(1, 5):
    add(K, "PITCH ENV", f"Env Time {i}", f"Pitch Env Time {i}", "numero", 0, 127, su=s)
for i in range(0, 5):
    add(K, "PITCH ENV", f"Env Level {i}", f"Pitch Env Level {i}", "numero", -63, 63, su=s)
add(K, "TVF", "Filter Type", "", "scelta", scelte="OFF, LPF, BPF, HPF, PKG, LPF2, LPF3", su=s)
add(K, "TVF", "Cutoff", "TVF Cutoff Frequency", "numero", 0, 127, su=s)
add(K, "TVF", "Resonance", "", "numero", 0, 127, su=s)
add(K, "TVF", "Cutoff V-Crv", "Cutoff Velocity Curve", "scelta", scelte=VCURVE, su=s)
add(K, "TVF", "Cutoff V-Sens", "Cutoff Velocity Sens", "numero", -63, 63, su=s)
add(K, "TVF", "Res V-Sens", "Resonance Velocity Sens", "numero", -63, 63, su=s)
add(K, "TVF ENV", "Env V-Curve", "TVF Env Velocity Curve", "scelta", scelte=VCURVE, su=s)
add(K, "TVF ENV", "Env V-Sens", "TVF Env Velocity Sens", "numero", -63, 63, su=s)
add(K, "TVF ENV", "Env T1 V-Sens", "", "numero", -63, 63, su=s)
add(K, "TVF ENV", "Env T4 V-Sens", "", "numero", -63, 63, su=s)
add(K, "TVF ENV", "Env Depth", "TVF Env Depth", "numero", -63, 63, su=s)
for i in range(1, 5):
    add(K, "TVF ENV", f"Env Time {i}", f"TVF Env Time {i}", "numero", 0, 127, su=s)
for i in range(0, 5):
    add(K, "TVF ENV", f"Env Level {i}", f"TVF Env Level {i}", "numero", 0, 127, su=s)
add(K, "TVA", "Level", "Partial Level", "numero", 0, 127, su=s)
add(K, "TVA", "Level V-Curve", "", "scelta", scelte=VCURVE, su=s)
add(K, "TVA", "Level V-Sens", "", "numero", -63, 63, su=s)
add(K, "TVA", "Pan", "Partial Pan", "pan", -64, 63, su=s)
add(K, "TVA", "Rnd Pan Dpth", "Random Pan Depth", "numero", 0, 63, su=s)
add(K, "TVA", "Alt Pan Dpth", "Alternate Pan Depth", "pan", -63, 63, su=s)
add(K, "TVA", "Relative Level", "", "numero", -64, 63, su=s)
add(K, "TVA ENV", "Env T1 V-Sens", "", "numero", -63, 63, su=s)
add(K, "TVA ENV", "Env T4 V-Sens", "", "numero", -63, 63, su=s)
for i in range(1, 5):
    add(K, "TVA ENV", f"Env Time {i}", f"TVA Env Time {i}", "numero", 0, 127, su=s)
for i in range(1, 4):
    add(K, "TVA ENV", f"Env Level {i}", f"TVA Env Level {i}", "numero", 0, 127, su=s)
add(K, "OUTPUT", "Output Asgn", "Output Assign", "scelta", scelte=OUT5, su=s, note="Vale se la parte Drums ha Part Output = KIT")
add(K, "OUTPUT", "Output Level", "", "numero", 0, 127, su=s)
add(K, "OUTPUT", "Dly Send Lev", "Delay Send Level", "numero", 0, 127, su=s)
add(K, "OUTPUT", "Rev Send Lev", "Reverb Send Level", "numero", 0, 127, su=s)

# ---------------- PROGRAM ----------------
P = "PROG"
add(P, "COMMON", "Tempo", "Program Tempo", "numero o scelta", 5, 300, scelte="MIDI", unita="BPM")
add(P, "COMMON", "ProgramLevel", "Program Level", "numero", 0, 127)
add(P, "MAIN", "Level", "Part Level", "numero", 0, 127, su=s)
add(P, "MAIN", "Sound Mute", "", "scelta", scelte="OFF, MUTE", su=s)
add(P, "MAIN", "Pan", "Part Pan", "pan", -64, 63, su=s)
add(P, "MAIN", "Part Output", "Part Output Assign", "scelta", scelte="EFX1, EFX2, DLY, REV, DIR, KIT", su=s, note="KIT solo per la parte Drums")
add(P, "MAIN", "Dly Send Lev", "Part Delay Send Level", "numero", 0, 127, su=s)
add(P, "MAIN", "Rev Send Lev", "Part Reverb Send Level", "numero", 0, 127, su=s)
add(P, "MAIN", "Mono/Poly", "", "scelta", scelte="MONO, POLY, TONE", su=s, note="Per la parte AN solo MONO")
add(P, "MAIN", "Legato Sw", "Legato Switch", "scelta", scelte="OFF, ON, TONE", su=s)
add(P, "PITCH", "Octave Shift", "", "numero", -3, 3, su=s)
add(P, "PITCH", "Coarse Tune", "", "numero", -48, 48, unita="semitoni", su=s)
add(P, "PITCH", "Fine Tune", "", "numero", -50, 50, unita="cent", su=s)
add(P, "PITCH", "Bend Range", "Pitch Bend Range", "numero o scelta", 0, 24, scelte="TONE", su=s)
add(P, "PITCH", "Porta Sw", "Portamento Switch", "scelta", scelte="OFF, ON, TONE", su=s)
add(P, "PITCH", "Porta Time", "Portamento Time", "numero o scelta", 0, 127, scelte="TONE", su=s)
for p, l in [("Cutoff Ofst", "Cutoff Offset"), ("Reso Offset", "Resonance Offset"), ("Attack Ofst", "Attack Offset"), ("Decay Offset", ""), ("Release Ofst", "Release Offset"), ("Vibrato Rate", ""), ("Vibrato Depth", ""), ("Vibrato Delay", "")]:
    add(P, "OFFSET", p, l, "numero", -64, 63, su=s)

# ---------------- EFFECTS ----------------
E = "EFFETTI"
add(E, "EFFECT1", "Type", "Effect 1 Type", "scelta", scelte="Thru, Distortion, Fuzz, Compressor, Bit Crusher")
add(E, "EFFECT1", "Output Asgn", "Effect 1 Output Assign", "scelta", scelte="DIR, EFX2", note="EFX2 = in serie con Effect 2")
add(E, "EFFECT1", "Dly Send Lev", "Effect 1 Delay Send Level", "numero", 0, 127)
add(E, "EFFECT1", "Rev Send Lev", "Effect 1 Reverb Send Level", "numero", 0, 127)
add(E, "EFFECT1", "Level", "Livello dell'effetto (tutti i tipi)", "numero", 0, 127)
add(E, "EFFECT1", "Dist Type", "Type di Distortion / Fuzz", "numero", 0, 5, note="Distortion, Fuzz")
add(E, "EFFECT1", "Drive", "", "numero", 0, 127, note="Distortion, Fuzz")
add(E, "EFFECT1", "Presence", "", "numero", 0, 127, note="Distortion, Fuzz")
add(E, "EFFECT1", "Threshold", "", "numero", 0, 127, note="Compressor")
add(E, "EFFECT1", "Ratio", "", "testo", note="Compressor · 1:1 … inf:1")
add(E, "EFFECT1", "Attack", "Compressor Attack", "numero", 0.05, 50, unita="ms", note="Compressor")
add(E, "EFFECT1", "Release", "Compressor Release", "numero", 0.05, 2000, unita="ms", note="Compressor")
add(E, "EFFECT1", "Side Switch", "Side Chain Switch", "scelta", scelte=SW, note="Compressor · firmware 1.50")
add(E, "EFFECT1", "Side Level", "Side Chain Level", "numero", 0, 127, note="Compressor · firmware 1.50")
add(E, "EFFECT1", "Side Note", "Side Chain Note", "nota", note="Compressor · strumento Drums, es. C2")
add(E, "EFFECT1", "Side Time", "", "numero", 60, 1000, unita="ms", note="Compressor · firmware 1.50")
add(E, "EFFECT1", "Side Release", "", "numero", 0, 127, note="Compressor · firmware 1.50")
add(E, "EFFECT1", "Side Sync Sw", "Side Chain Tempo Sync", "scelta", scelte=SW, note="Compressor · firmware 1.50")
add(E, "EFFECT1", "Rate", "Sampling rate", "numero", 0, 127, note="Bit Crusher")
add(E, "EFFECT1", "Bit", "Bit depth", "numero", 0, 127, note="Bit Crusher")
add(E, "EFFECT1", "Filter", "", "numero", 0, 127, note="Bit Crusher")
add(E, "EFFECT2", "Type", "Effect 2 Type", "scelta", scelte="Thru, Flanger, Phaser, Ring Mod, Slicer")
add(E, "EFFECT2", "Dly Send Lev", "Effect 2 Delay Send Level", "numero", 0, 127)
add(E, "EFFECT2", "Rev Send Lev", "Effect 2 Reverb Send Level", "numero", 0, 127)
add(E, "EFFECT2", "Level", "Livello dell'effetto (tutti i tipi)", "numero", 0, 127)
add(E, "EFFECT2", "Rate", "", "numero o scelta", 0, 127, scelte=NOTES, note="Flanger, Phaser (numero o nota); Slicer (solo nota)")
add(E, "EFFECT2", "Depth", "", "numero", 0, 127, note="Flanger, Phaser")
add(E, "EFFECT2", "Feedback", "", "numero", 0, 127, note="Flanger · 0 = chorus")
add(E, "EFFECT2", "Manual", "", "numero", 0, 127, note="Flanger, Phaser")
add(E, "EFFECT2", "Balance", "Dry/Wet Balance", "D:W", note="Flanger, Ring Mod · es. D50:50W")
add(E, "EFFECT2", "Resonance", "", "numero", 0, 127, note="Phaser")
add(E, "EFFECT2", "Frequency", "", "numero", 0, 127, note="Ring Mod")
add(E, "EFFECT2", "Sens", "", "numero", 0, 127, note="Ring Mod")
add(E, "EFFECT2", "Timing Ptn", "Timing Pattern", "numero", 0, 15, note="Slicer")
add(E, "EFFECT2", "Attack", "", "numero", 0, 127, note="Slicer")
add(E, "EFFECT2", "Trigger Level", "", "numero", 0, 127, note="Slicer")
add(E, "DELAY", "Type", "Delay Type", "scelta", scelte="SINGLE, PAN")
add(E, "DELAY", "Time", "Delay Time", "numero o scelta", 0, 2600, scelte=NOTES, unita="ms")
add(E, "DELAY", "Tap Time", "", "numero", 0, 100, unita="%", note="Solo con Type = PAN")
add(E, "DELAY", "Feedback", "", "numero", 0, 98, unita="%")
add(E, "DELAY", "HF Damp", "High Frequency Damp", "numero o scelta", 200, 8000, scelte="BYPASS", unita="Hz")
add(E, "DELAY", "Level", "Delay Level", "numero", 0, 127)
add(E, "DELAY", "Rev Send Lev", "Delay to Reverb Send Level", "numero", 0, 127)
add(E, "REVERB", "Type", "Reverb Type", "scelta", scelte="ROOM1, ROOM2, STAGE1, STAGE2, HALL1, HALL2")
add(E, "REVERB", "Time", "Reverb Time", "numero", 0, 127)
add(E, "REVERB", "HF Damp", "High Frequency Damp", "numero o scelta", 200, 8000, scelte="BYPASS", unita="Hz")
add(E, "REVERB", "Level", "Reverb Level", "numero", 0, 127)

# ---------------- VOCAL ----------------
V = "VOCE"
add(V, "COMMON", "Vocal Effect", "", "scelta", scelte="OFF, VOCODER, AUTO-PITCH")
add(V, "COMMON", "Auto Note", "Auto Note Switch", "scelta", scelte=SW)
KEYS = "C, Db, D, Eb, E, F, F#, G, Ab, A, Bb, B, Cm, C#m, Dm, D#m, Em, Fm, F#m, Gm, G#m, Am, Bbm, Bm"
for g in ("AUTO PITCH", "VOCODER"):
    add(V, g, "Level", "", "numero", 0, 127)
    add(V, g, "Pan", "", "pan", -64, 63)
    add(V, g, "Output Asgn", "Output Assign", "scelta", scelte=OUT5)
    add(V, g, "Dly Send Lev", "Delay Send Level", "numero", 0, 127)
    add(V, g, "Rev Send Lev", "Reverb Send Level", "numero", 0, 127)
add(V, "AUTO PITCH", "Type", "", "scelta", scelte="Soft, Hard, Electric1, Electric2")
add(V, "AUTO PITCH", "Scale", "", "scelta", scelte="Chromatic, Maj(Min)")
add(V, "AUTO PITCH", "Key", "", "scelta", scelte=KEYS)
add(V, "AUTO PITCH", "Gender", "", "numero", -10, 10)
add(V, "AUTO PITCH", "Octave", "", "numero", -1, 1)
add(V, "AUTO PITCH", "Balance", "Dry/Wet Balance", "D:W", note="es. D30:70W")
add(V, "VOCODER", "Envelope", "", "scelta", scelte="Sharp, Soft, Long")
add(V, "VOCODER", "Mic Sens", "", "numero", 0, 127)
add(V, "VOCODER", "Synth Level", "", "numero", 0, 127)
add(V, "VOCODER", "Mic Mix Level", "", "numero", 0, 127)
add(V, "VOCODER", "Mic HPF", "Mic High Pass Filter", "numero o scelta", 1000, 16000, scelte="BYPASS", unita="Hz")

# ---------------- ARPEGGIO ----------------
G = "ARP"
add(G, "ARPEGGIO", "Arpeggio", "Arpeggio Switch", "scelta", scelte=SW)
add(G, "ARPEGGIO", "Style", "Arpeggio Style", "numero", 1, 128)
add(G, "ARPEGGIO", "Grid", "", "scelta", scelte="1/4, 1/8, 1/8L, 1/8H, 1/12, 1/16, 1/16L, 1/16H, 1/24")
add(G, "ARPEGGIO", "Duration", "", "numero o scelta", 30, 120, scelte="FULL", unita="%")
add(G, "ARPEGGIO", "Motif", "", "scelta", scelte="Up(L), Up(L&H), Up(_), Down(L), Down(L&H), Down(_), U/D(L), U/D(L&H), U/D(_), Rand(L), Rand(_), Phrase")
add(G, "ARPEGGIO", "Velocity", "", "numero o scelta", 1, 127, scelte="REAL")
add(G, "ARPEGGIO", "Oct Range", "Octave Range", "numero", -3, 3)
add(G, "ARPEGGIO", "Accent", "Accent Rate", "numero", 0, 100, unita="%")

PARTS = [
    ("AN", "Analog Synth"),
    ("D1", "Digital Synth 1"),
    ("D2", "Digital Synth 2"),
    ("DR", "Drums"),
    ("PROG", "Programma (PROG: COMMON, MAIN, PITCH, OFFSET)"),
    ("EFFETTI", "Effetti (Effect 1, Effect 2, Delay, Reverb)"),
    ("VOCE", "Effetto voce (Auto Pitch, Vocoder)"),
    ("ARP", "Arpeggio"),
]

DRUM_INST = ["BD1", "RIM", "BD2", "CLAP", "BD3", "SD1", "CHH", "SD2", "PHH", "SD3", "OHH", "SD4", "TOM1", "PRC1", "TOM2", "PRC2", "TOM3", "PRC3", "CYM1", "PRC4", "CYM2", "PRC5", "CYM3", "HIT", "OTH1", "OTH2", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4", "C5"]
