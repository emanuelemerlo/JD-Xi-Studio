"""
What a recipe row can name: part, group and parameter, as in the template.

The template's vocabulary (vocabulary.py, the names of the JD-Xi display and
the Parameter Guide) is matched to the parameters of the new editors, which
know addresses, ranges and choices. A Target is one template entry with the
editor parameter(s) it stands for; values() finds the ParamValues in an open
editor ("Su" chooses the partial, drum instrument, wave or part).
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from jdxi_editor.recipes import vocabulary

PARTS = [p for p, _ in vocabulary.PARTS]
EDITOR_KEYS = {
    "AN": "analog", "D1": "digital1", "D2": "digital2", "DR": "drums", "PROG": "program_parts",
    "EFFETTI": "effects", "VOCE": "vocal_fx", "ARP": "arpeggio",
}
PART_ALIASES = {
    "ANALOG": "AN", "ANALOG SYNTH": "AN", "DIGITAL 1": "D1", "DIGITAL1": "D1", "DIGITAL SYNTH 1": "D1",
    "DIGITAL 2": "D2", "DIGITAL2": "D2", "DIGITAL SYNTH 2": "D2", "DRUMS": "DR", "DRUM": "DR", "DRUM KIT": "DR",
    "PROGRAM": "PROG", "PROGRAMMA": "PROG", "EFX": "EFFETTI", "EFFECTS": "EFFETTI", "EFFECT": "EFFETTI",
    "VOCAL": "VOCE", "VOCAL FX": "VOCE", "VOCAL EFFECT": "VOCE", "VFX": "VOCE", "ARPEGGIO": "ARP",
}
# PROG groups are also written as on the display: "PROG: MAIN AN"
DISPLAY_PREFIXES = ("TONE:", "PROG:", "KIT:")


def norm(text: str) -> str:
    """'Cutoff KF' -> 'cutoffkf': names compared without case, spaces or punctuation."""
    return re.sub(r"[^0-9a-z#&]", "", str(text).lower())


@dataclass
class Proto:
    """What the parameter accepts (from the editor's description of it)."""

    lo: int
    hi: int
    info: object  # ParamInfo: choices, scale, fmt, parse, unit, show_negative


@dataclass
class Target:
    part: str
    group: str
    label: str
    long: str
    kind: str  # template "Tipo"
    su: str  # template "Su": "sì", "facoltativo", "no"
    names: list[str] = field(default_factory=list)  # editor parameter names (one per effect type for EFX)
    protos: list[Proto] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)  # editor groups of the names (effect type)
    special: str = ""  # "partial_switch", "delay_time"

    @property
    def proto(self) -> Proto:
        return self.protos[0]

    @property
    def editor_key(self) -> str:
        return EDITOR_KEYS[self.part]

    def key(self) -> tuple[str, str, str]:
        return (self.part, norm(self.group), norm(self.label))


# ---------------------------------------------------------------- slots
@dataclass
class _Slot:
    group: str  # editor group without the partial/part/drum suffix
    label: str
    long: str
    name: str
    proto: Proto


def _slots_from_blocks(blocks, strip: Callable[[str], str]) -> list[_Slot]:
    out = []
    for block in blocks:
        for spec in block.params:
            if spec.name.startswith(("TONE_NAME_", "PROGRAM_NAME_", "KIT_NAME_", "PARTIAL_NAME_")):
                continue
            info = spec.info(block.group)
            out.append(_Slot(strip(spec.group or block.group), spec.label, spec.long, spec.name, Proto(spec.lo, spec.hi, info)))
    return out


@functools.lru_cache(maxsize=None)
def _editor_slots() -> dict[str, list[_Slot]]:
    from jdxi_editor.ui.v2 import arpeggio, digital, drums, effects, program, vocal
    from jdxi_editor.ui.v2.params import analog_info

    slots: dict[str, list[_Slot]] = {}
    an = []
    from jdxi_editor.midi.data.parameter.analog.address import AnalogParam

    infos = analog_info()
    for param in AnalogParam:
        info = infos.get(param.name)
        if info is None:
            continue
        lo, hi = param.get_display_value()
        an.append(_Slot(info.group, info.label, info.long, param.name, Proto(lo, hi, info)))
    slots["AN"] = an
    dig = [digital.common_block(1), digital.modify_block(1), digital.partial_block(1, 0)]
    slots["D1"] = slots["D2"] = _slots_from_blocks(dig, lambda g: re.sub(r" P\d$", "", g))
    texts = drums._Texts()
    slots["DR"] = _slots_from_blocks([drums.common_block(), drums.partial_block(0, texts)],
                                     lambda g: re.sub(r"^(WAVE) \d", r"\1", g).replace(" BD1", ""))
    slots["PROG"] = _slots_from_blocks([program.common_block(), program.part_block(0), program.zone_block(0)],
                                       lambda g: g.replace(" D1", ""))
    slots["EFFETTI"] = _slots_from_blocks(effects.effect_blocks(), lambda g: g)
    slots["VOCE"] = _slots_from_blocks(vocal.vocal_blocks(), lambda g: g)
    slots["ARP"] = _slots_from_blocks(arpeggio.arpeggio_blocks(), lambda g: g)
    return slots


# Template group -> editor groups it may refer to
GROUPS = {
    "D1": {"PITCH": ["OSC"], "AFT": ["AFTERTOUCH"], "MISC": ["MISC"]},
    "DR": {"PITCH ENV": ["PITCH"], "TVF ENV": ["TVF"], "TVA ENV": ["TVA"], "OUTPUT": ["COMMON"], "WMT": ["WAVE"]},
    "VOCE": {"COMMON": ["PROGRAM"], "AUTO PITCH": ["AUTOPITCH", "OUTPUT"], "VOCODER": ["VOCODER", "OUTPUT"]},
    "ARP": {"ARPEGGIO": ["ARPEGGIO", "PROGRAM"]},
    "PROG": {"COMMON": ["COMMON"]},
}
GROUPS["D2"] = GROUPS["D1"]
# Template names that differ from the editors' (part, group, name) -> editor label
ALIASES = {
    ("D1", "MOD LFO", "Rate Control"): "Rate Ctrl",
    ("DR", "WAVE", "Wave Switch"): "Wave Sw",
    ("DR", "COMMON", "Kit Level"): "Kit Level",
    ("DR", "PITCH", "Coarse Tune"): "Coarse Tune",
    ("VOCE", "VOCODER", "Mic Mix Level"): "Mic Mix",
    ("EFFETTI", "EFFECT1", "Dist Type"): "Type",
    ("EFFETTI", "DELAY", "Level"): "Level",
    ("EFFETTI", "DELAY", "Time"): "Time",
    ("PROG", "COMMON", "Tempo"): "Tempo",
}
ALIASES.update({("D2",) + k[1:]: v for k, v in list(ALIASES.items()) if k[0] == "D1"})


def _candidates(part: str, group: str, label: str, long: str) -> list[_Slot]:
    slots = _editor_slots()[part]
    groups = GROUPS.get(part, {}).get(group, [group])
    wanted = {norm(label), norm(long)} - {""}
    alias = ALIASES.get((part, group, label))
    if alias:
        wanted = {norm(alias)}
    if part == "DR" and label.lower().startswith("env "):
        wanted.add(norm(label[4:]))
    found = []
    for slot in slots:
        if not any(slot.group == g or slot.group.startswith(g + " ·") for g in groups):
            continue
        names = {norm(slot.label), norm(slot.long)} - {""}
        if wanted & names:
            found.append(slot)
    return found


@functools.lru_cache(maxsize=None)
def targets() -> dict[tuple[str, str, str], Target]:
    """Every template entry with the editor parameters it stands for."""
    out: dict[tuple[str, str, str], Target] = {}
    for part, group, label, long, kind, lo, hi, choices, unit, su, note in vocabulary.R:
        t = Target(part, group, label, long, kind, su)
        if part in ("D1", "D2") and label == "Partial Switch":
            t.special = "partial_switch"
            t.names = ["PARTIAL1_SWITCH"]
            slot = next(s for s in _editor_slots()[part] if s.name == "PARTIAL1_SWITCH")
            t.protos = [slot.proto]
            t.groups = ["COMMON"]
        elif part == "EFFETTI" and group == "EFFECT2" and label == "Rate":
            t.special = "efx2_rate"  # Flanger/Phaser: a rate or a note (Rate/Note switch); Slicer: a note
            slots = [s for s in _editor_slots()[part] if s.group.startswith("EFFECT2 ·") and s.label in ("Rate", "Note")]
            t.names = [s.name for s in slots]
            t.protos = [s.proto for s in slots]
            t.groups = [s.group for s in slots]
        elif part == "EFFETTI" and group == "DELAY" and label == "Time":
            t.special = "delay_time"
            slots = [s for s in _editor_slots()[part] if s.name in ("DELAY_TIME_MS", "DELAY_NOTE")]
            t.names = [s.name for s in slots]
            t.protos = [s.proto for s in slots]
            t.groups = [s.group for s in slots]
        else:
            found = _candidates(part, group, label, long)
            if part == "EFFETTI" and label == "Level" and group in ("EFFECT1", "EFFECT2"):
                found = [s for s in found if "·" in s.group]  # the selected type's Level, not the block level
            if part == "EFFETTI" and label == "Dist Type":
                found = [s for s in found if s.group.endswith(("DISTORTION", "FUZZ"))]
            elif part == "EFFETTI" and group == "EFFECT1" and label == "Type":
                found = [s for s in found if s.group == "EFFECT1"]
            if part == "EFFETTI" and group in ("DELAY", "REVERB") and label == "Level":
                found = [s for s in found if s.name.endswith("EFFECT_LEVEL")]
            t.names = [s.name for s in found]
            t.protos = [s.proto for s in found]
            t.groups = [s.group for s in found]
        out[t.key()] = t
    return out


def unmatched() -> list[Target]:
    """Template entries with no editor parameter (should be none)."""
    return [t for t in targets().values() if not t.names]


# ------------------------------------------------------------ lookups
def find_part(text: str) -> Optional[str]:
    t = str(text).strip().upper()
    if t in PARTS:
        return t
    return PART_ALIASES.get(t)


def groups_of(part: str) -> list[str]:
    seen = []
    for (p, _g, _l), t in targets().items():
        if p == part and t.group not in seen:
            seen.append(t.group)
    return seen


def labels_of(part: str, group: str) -> list[str]:
    return [t.label for (p, g, _l), t in targets().items() if p == part and g == norm(group)]


def find(part: str, group: str, label: str) -> Optional[Target]:
    return targets().get((part, norm(group), norm(label)))


def find_loose(part: str, group: str, label: str) -> tuple[Optional[Target], list[Target]]:
    """
    The target, also when written differently: by its long name, without the
    group, or with a small spelling mistake. Returns (sure match, guesses).
    """
    import difflib

    exact = find(part, group, label)
    if exact is not None:
        return exact, []
    in_part = [t for (p, _g, _l), t in targets().items() if p == part]
    n = norm(label)
    by_long = [t for t in in_part if n and (n == norm(t.long) or n == norm(t.label))]
    same_group = [t for t in by_long if norm(t.group) == norm(group)]
    if len(same_group) == 1:
        return same_group[0], []
    if len(by_long) == 1:
        return by_long[0], []
    if by_long:
        return None, by_long
    pool = [t for t in in_part if norm(t.group) == norm(group)] or in_part
    names = {norm(t.label): t for t in pool}
    close = difflib.get_close_matches(n, list(names), n=3, cutoff=0.6)
    return None, [names[c] for c in close]
