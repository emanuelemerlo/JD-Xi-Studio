"""
Checking a recipe row by row: what each row means and whether it can be used.

Statuses:
  OK       name and value are valid (short or long names both work)
  CONFIRM  the checker has a guess: a similar name, a row split in two, a default "Su"
  FIX      out of range, unknown parameter, missing part or "Su": fix or exclude it
  EAR      no value to set: the guided view opens the control and leaves it to you
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from jdxi_editor.i18n import tr
from jdxi_editor.recipes import catalog
from jdxi_editor.recipes.catalog import Proto, Target
from jdxi_editor.recipes.model import EAR, RANGE, Recipe, Row
from jdxi_editor.recipes.reader import RANGE_RE

OK, CONFIRM, FIX, EARS = "ok", "confirm", "fix", "ear"
_UNITS = r"(?:ms|%|hz|khz|db|st|semitoni|semitones|cent|bpm)"
_VALUE_ALIASES = {"super-saw": "sp-saw", "supersaw": "sp-saw", "reverse": "revs", "lpf": "lpf", "c": "c"}
DRUM_NAMES = None


@dataclass
class Parsed:
    kind: str  # "value", "range", "ear"
    value: Optional[int] = None  # display value to set (the middle of a range)
    lo: Optional[int] = None
    hi: Optional[int] = None


@dataclass
class Checked:
    row: Row
    status: str
    message: str = ""
    target: Optional[Target] = None
    parsed: Optional[Parsed] = None
    su: list[int] = field(default_factory=list)  # partials / drum instruments / parts (0-based)
    wave: list[int] = field(default_factory=list)  # drum waves (0-based)
    suggestions: list[str] = field(default_factory=list)
    excluded: bool = False


# --------------------------------------------------------------- values
def _soft(text: str) -> str:
    return re.sub(r"\s+", "", str(text).lower())


def _choice_index(text: str, proto: Proto) -> Optional[int]:
    choices = list(getattr(proto.info, "choices", ()) or ())
    if not choices:
        return None
    t = _soft(text)
    t = _VALUE_ALIASES.get(t, t)
    stripped = re.sub(_UNITS + "$", "", t)
    for i, choice in enumerate(choices):
        c = _soft(choice)
        if t == c or stripped == c or t == re.sub(_UNITS + "$", "", c) or stripped == re.sub(_UNITS + "$", "", c):
            return i + proto.lo if proto.lo else i
    numeric = _numeric_choices(choices)
    m_num = re.match(r"^([+-]?\d+(?:[.,]\d+)?)$", stripped)
    if numeric and m_num:  # "3000" for "3150 Hz": the nearest of the values the JD-Xi offers
        wanted = float(m_num.group(1).replace(",", "."))
        best = min(numeric, key=lambda item: abs(item[1] - wanted))
        return best[0] + proto.lo if proto.lo else best[0]
    m = re.match(r"^(\d+)$", stripped)
    if m and re.match(r"^\d{3}:", choices[0]):  # "001: Basic 1" lists: the number
        number = int(m.group(1))
        for i, choice in enumerate(choices):
            if int(choice[:3]) == number:
                return i
    return None


def _numeric_choices(choices) -> list[tuple[int, float]]:
    """[(index, number)] when the choices are numbers with a unit ("200 Hz", "0.05 ms"), else []."""
    out = []
    for i, choice in enumerate(choices):
        m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(?:hz|ms|db)\s*$", str(choice), re.I)
        if m:
            out.append((i, float(m.group(1))))
    return out if len(out) >= max(2, len(choices) - 1) else []


def _number(text: str, proto: Proto) -> Optional[int]:
    info = proto.info
    parse = getattr(info, "parse", None)
    if parse is not None:
        value = parse(text)
        if value is not None:
            return value
    m = re.match(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*" + _UNITS + r"?\s*$", text.strip(), re.I)
    if not m:
        return None
    number = float(m.group(1).replace(",", "."))
    scale = getattr(info, "scale", 1) or 1
    number *= scale
    if getattr(info, "show_negative", False):
        number = abs(number)
    return int(round(number))


def parse_value(text: str, proto: Proto) -> tuple[Optional[int], str]:
    """(display value, error message)."""
    text = str(text).strip()
    index = _choice_index(text, proto)
    if index is not None:
        return index, ""
    value = _number(text, proto)
    if value is None:
        choices = getattr(proto.info, "choices", ())
        if choices and len(choices) <= 24:
            return None, tr("\"{text}\" is not one of: {choices}").format(text=text, choices=", ".join(choices))
        return None, tr("\"{text}\" is not a value of this parameter").format(text=text)
    if not proto.lo <= value <= proto.hi:
        info = proto.info
        lo, hi = info.format(proto.lo), info.format(proto.hi)
        if getattr(info, "show_negative", False):
            lo, hi = hi, lo
        return value, tr("{text} is out of range: {lo} … {hi}").format(text=text, lo=lo, hi=hi)
    return value, ""


def parse_row_value(row: Row, proto: Proto) -> tuple[Optional[Parsed], str]:
    if row.kind == EAR:
        return Parsed("ear"), ""
    lo_text, hi_text = row.lo, row.hi
    if row.kind == RANGE and not (lo_text and hi_text):
        m = RANGE_RE.match(row.value)
        if m:
            unit = m.group(3) or ""
            lo_text, hi_text = m.group(1) + unit, m.group(2) + unit
    if lo_text and hi_text:
        lo, err1 = parse_value(lo_text, proto)
        hi, err2 = parse_value(hi_text, proto)
        if err1 or err2 or lo is None or hi is None:
            return None, err1 or err2
        lo, hi = min(lo, hi), max(lo, hi)
        return Parsed("range", (lo + hi) // 2, lo, hi), ""
    value, err = parse_value(row.value, proto)
    if err or value is None:
        return None, err
    return Parsed("value", value), ""


# ------------------------------------------------------------------ "Su"
def _drum_index(name: str) -> Optional[int]:
    from jdxi_editor.ui.v2.drums import DRUM_PARTIAL_NAMES, FIRST_KEY, NOTE_NAMES

    n = name.strip().upper().replace("♯", "#")
    names = [x.upper() for x in DRUM_PARTIAL_NAMES[1:]]
    if n in names:
        return names.index(n)
    flats = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
    m = re.match(r"^([A-G]B?#?)(-?\d)$", n)
    if m:
        note = flats.get(m.group(1), m.group(1)) + m.group(2)
        for i in range(37):
            if NOTE_NAMES[FIRST_KEY + i].upper() == note:
                return i
    if n.isdigit() and 36 <= int(n) <= 72:
        return int(n) - 36
    return None


def parse_su(target: Target, su: str) -> tuple[list[int], list[int], str, str]:
    """(indexes, waves, status, message) for the row's "Su"."""
    text = su.strip()
    part = target.part
    if part in ("D1", "D2") and (target.su == "facoltativo" or target.special == "partial_switch"):
        if not text:
            if target.special == "partial_switch":
                return [], [], FIX, tr("Say which partial (1, 2 or 3) in Su.")
            return [0, 1, 2], [], OK, ""
        found = sorted({int(d) - 1 for d in re.findall(r"[123]", text)})
        if not found:
            return [], [], FIX, tr("Su must be a partial: 1, 2 or 3.")
        return found, [], OK, ""
    if part == "DR" and target.su == "sì":
        if not text:
            return [], [], FIX, tr("Say which drum instrument in Su (e.g. SD1 or SD1/W2).")
        inst, _, wave = text.partition("/")
        index = _drum_index(inst)
        if index is None:
            return [], [], FIX, tr("\"{text}\" is not a drum instrument (BD1, SD1, CHH ... or a note C2-C5).").format(text=inst)
        waves = []
        if target.group in ("WAVE", "WMT") and target.label != "WMT Vel Ctrl":
            w = re.findall(r"[1-4]", wave)
            if not w:
                return [index], [0], CONFIRM, tr("No wave in Su: wave 1 is assumed (write e.g. {inst}/W2).").format(inst=inst)
            waves = [int(x) - 1 for x in w]
        return [index], waves, OK, ""
    if part == "PROG" and target.su == "sì":
        parts = [p for p in ("D1", "D2", "AN", "DR") if p in text.upper()]
        if not parts:
            return [], [], FIX, tr("Say which part in Su: D1, D2, AN or DR.")
        return [("D1", "D2", "AN", "DR").index(p) for p in parts], [], OK, ""
    return [], [], OK, ""


# ---------------------------------------------------------------- rows
def _split_multi(row: Row) -> list[Row]:
    """'Attack / Decay / Sustain / Release' = '0 / 40 / 100 / 30' -> four rows."""
    names = [n.strip() for n in row.param.split("/")]
    if len(names) < 2 or row.kind == "a orecchio":
        return [row]
    values = [v.strip() for v in row.value.split("/")]
    if len(values) != len(names):
        values = [row.value] * len(names) if len(values) == 1 else values
        if len(values) != len(names):
            return [row]
    out = []
    for name, value in zip(names, values):
        r = Row(**{**row.__dict__})
        r.param, r.value = name, value
        from jdxi_editor.recipes.reader import classify_value

        r.kind = classify_value(value)
        out.append(r)
    return out


def _part_from_group(row: Row) -> tuple[str, str, str]:
    """'TONE: FILTER' -> group FILTER; 'PROG: MAIN AN' -> part PROG, group MAIN, Su AN."""
    group = row.group.strip()
    part = row.part.strip()
    su = row.su
    m = re.match(r"^(TONE|PROG|KIT)\s*:\s*(.+)$", group, re.I)
    if m:
        group = m.group(2).strip()
        if m.group(1).upper() == "PROG":
            words = group.split()
            if len(words) > 1 and words[-1].upper() in ("D1", "D2", "AN", "DR"):
                su = su or words[-1].upper()
                group = " ".join(words[:-1])
            part = "PROG"
    return part, group, su


def check_row(row: Row, default_part: str = "") -> Checked:
    part_text, group, su = _part_from_group(row)
    if not part_text and default_part:
        part_text = default_part
    part = catalog.find_part(part_text) if part_text else None
    if part is None:
        return Checked(row, FIX, tr("Unknown part \"{part}\": use AN, D1, D2, DR, PROG, EFFETTI, VOCE or ARP.").format(part=part_text)
                       if part_text else tr("The part is missing."))
    target, guesses = catalog.find_loose(part, group, row.param)
    status, message = OK, ""
    suggestions = []
    if target is None:
        import difflib

        if guesses and len(guesses) > 1:
            first = difflib.SequenceMatcher(None, catalog.norm(row.param), catalog.norm(guesses[0].label)).ratio()
            if first >= 0.85:
                guesses = guesses[:1]
        if len(guesses) == 1:
            target = guesses[0]
            status, message = CONFIRM, tr("\"{name}\" is not a parameter of {part} {group}: the closest is {guess}.").format(
                name=row.param, part=part, group=group, guess=target.label)
        else:
            suggestions = [g.label for g in guesses]
            msg = tr("\"{name}\" is not a parameter of {part} {group}.").format(name=row.param, part=part, group=group)
            if suggestions:
                msg += " " + tr("Similar: {names}.").format(names=", ".join(suggestions))
            return Checked(row, FIX, msg, suggestions=suggestions)
    elif norm_differs(target, group):
        status, message = CONFIRM, tr("Found in group {group}.").format(group=target.group)
    indexes, waves, su_status, su_message = parse_su(target, su)
    if su_status == FIX:
        return Checked(row, FIX, su_message, target)
    if su_status == CONFIRM and status == OK:
        status, message = CONFIRM, su_message
    parsed, error = parse_row_value(row, target.proto) if target.special not in ("delay_time", "efx2_rate") else _special_value(row, target)
    if error:
        clamp = None
        if parsed is None:
            value, _ = parse_value(row.value, target.proto)
            if value is not None:
                clamp = max(target.proto.lo, min(target.proto.hi, value))
        checked = Checked(row, FIX, error, target, None, indexes, waves)
        if clamp is not None:
            checked.suggestions = [target.proto.info.format(clamp)]
        return checked
    if parsed.kind == "ear":
        return Checked(row, EARS, row.note or tr("To be set by ear."), target, parsed, indexes, waves)
    return Checked(row, status, message, target, parsed, indexes, waves)


def norm_differs(target: Target, group: str) -> bool:
    return bool(group) and catalog.norm(group) != catalog.norm(target.group)


def _special_value(row: Row, target: Target) -> tuple[Optional[Parsed], str]:
    """Delay Time and Effect 2 Rate take a number (ms / rate) or a note."""
    for proto in target.protos:
        if getattr(proto.info, "choices", ()):
            index = _choice_index(row.value, proto)
            if index is not None:
                return Parsed("value", index, None, None), ""
    for proto in target.protos:
        if not getattr(proto.info, "choices", ()):
            return parse_row_value(row, proto)
    return None, tr("\"{text}\" is not a value of this parameter").format(text=row.value)


def default_part(recipe: Recipe) -> str:
    """The part of the starting tone ("AN 064 Init Tone" -> AN), for rows that do not name one."""
    words = recipe.base_tone.split()
    return catalog.find_part(words[0]) or "" if words else ""


def check(recipe: Recipe, part: str = "") -> list[Checked]:
    """Each row checked; *part* is used for rows that name none (default: the starting tone's)."""
    part = part or default_part(recipe)
    out = []
    for row in recipe.rows:
        rows = _split_multi(row)
        for r in rows:
            c = check_row(r, part)
            if len(rows) > 1 and c.status == OK:
                c.status = CONFIRM
                c.message = tr("A row with {n} parameters was split: check that each value went to the right place.").format(n=len(rows))
            out.append(c)
    return out


def summary(checked: list[Checked]) -> dict[str, int]:
    counts = {OK: 0, CONFIRM: 0, FIX: 0, EARS: 0}
    for c in checked:
        if not c.excluded:
            counts[c.status] += 1
    return counts
