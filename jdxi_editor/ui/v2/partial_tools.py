"""
Working on the three partials of a SuperNATURAL synth tone together.

- **Link partials**: a change to a parameter of the partial shown goes to the
  other partials that are on (the value set, not a shift). The oscillator's
  identity — waveform, variation, PCM wave and gain, pitch, detune, Super Saw
  detune — stays each partial's own.
- **Copy / paste / swap** a whole partial or one section of it (OSC, FILTER,
  AMP, LFO, MOD LFO), also between Digital 1 and Digital 2: the clipboard is
  shared by the editors.
- **Randomize** a section, a partial or the whole tone by a chosen amount,
  keeping it playable.

Every action is one Undo step and goes to the JD-Xi as if the knobs were turned.
"""

from __future__ import annotations

import random
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from jdxi_editor.i18n import tr

PARTIALS = 3

# the sections of a partial, as the cards show them, and their parameters
SECTIONS: dict[str, tuple[str, ...]] = {
    "OSC": (
        "OSC_WAVE", "OSC_WAVE_VARIATION", "WAVE_NUMBER", "WAVE_GAIN", "OSC_PITCH", "OSC_DETUNE",
        "OSC_PULSE_WIDTH", "OSC_PULSE_WIDTH_MOD_DEPTH", "OSC_PULSE_WIDTH_SHIFT", "SUPER_SAW_DETUNE",
        "OSC_PITCH_ENV_ATTACK_TIME", "OSC_PITCH_ENV_DECAY", "OSC_PITCH_ENV_DEPTH",
    ),
    "FILTER": (
        "FILTER_MODE", "FILTER_SLOPE", "FILTER_CUTOFF", "FILTER_RESONANCE", "FILTER_CUTOFF_KEYFOLLOW",
        "FILTER_ENV_VELOCITY_SENS", "HPF_CUTOFF", "FILTER_ENV_ATTACK_TIME", "FILTER_ENV_DECAY_TIME",
        "FILTER_ENV_SUSTAIN_LEVEL", "FILTER_ENV_RELEASE_TIME", "FILTER_ENV_DEPTH",
    ),
    "AMP": (
        "AMP_LEVEL", "AMP_VELOCITY", "AMP_PAN", "AMP_LEVEL_KEYFOLLOW", "AMP_ENV_ATTACK_TIME",
        "AMP_ENV_DECAY_TIME", "AMP_ENV_SUSTAIN_LEVEL", "AMP_ENV_RELEASE_TIME",
        "CUTOFF_AFTERTOUCH_SENS", "LEVEL_AFTERTOUCH_SENS",
    ),
    "LFO": (
        "LFO_SHAPE", "LFO_RATE", "LFO_TEMPO_SYNC_SWITCH", "LFO_TEMPO_SYNC_NOTE", "LFO_FADE_TIME",
        "LFO_KEY_TRIGGER", "LFO_PITCH_DEPTH", "LFO_FILTER_DEPTH", "LFO_AMP_DEPTH", "LFO_PAN_DEPTH",
    ),
    "MOD LFO": (
        "MOD_LFO_SHAPE", "MOD_LFO_RATE", "MOD_LFO_TEMPO_SYNC_SWITCH", "MOD_LFO_TEMPO_SYNC_NOTE",
        "MOD_LFO_PITCH_DEPTH", "MOD_LFO_FILTER_DEPTH", "MOD_LFO_AMP_DEPTH", "MOD_LFO_PAN_DEPTH",
        "MOD_LFO_RATE_CONTROL",
    ),
}
PARTIAL_PARAMS: tuple[str, ...] = tuple(name for names in SECTIONS.values() for name in names)

# what makes each partial a different oscillator: not linked
OWN = frozenset((
    "OSC_WAVE", "OSC_WAVE_VARIATION", "WAVE_NUMBER", "WAVE_GAIN", "OSC_PITCH", "OSC_DETUNE", "SUPER_SAW_DETUNE",
))
LINKED = frozenset(PARTIAL_PARAMS) - OWN

# Randomize: amounts (share of each range a value may move), and what it leaves alone
AMOUNTS = {"little": 0.10, "medium": 0.30, "much": 1.0}
# in the tone's common settings, the ones that change its sound (not its name, category,
# playing style or bend range)
COMMON_RANDOM = ("WAVE_SHAPE", "ANALOG_FEEL")
# lists and switches change only with "much": a new waveform or filter type is a new sound
STEADY_BELOW_MUCH = frozenset((
    "OSC_WAVE", "OSC_WAVE_VARIATION", "WAVE_NUMBER", "WAVE_GAIN", "FILTER_MODE", "FILTER_SLOPE",
    "LFO_SHAPE", "MOD_LFO_SHAPE", "LFO_TEMPO_SYNC_SWITCH", "MOD_LFO_TEMPO_SYNC_SWITCH",
    "LFO_TEMPO_SYNC_NOTE", "MOD_LFO_TEMPO_SYNC_NOTE", "LFO_KEY_TRIGGER", "OSC_PITCH",
))
MIN_LEVEL = 70  # a partial randomized stays audible
NO_SILENT_FILTER = 30  # nor closed by its filter


def section_name(section: str) -> str:
    return {"OSC": tr("Oscillator"), "FILTER": tr("Filter"), "AMP": tr("Amplifier"),
            "LFO": tr("LFO"), "MOD LFO": tr("Modulation LFO")}.get(section, section)


# ------------------------------------------------------------------- clipboard
@dataclass
class Clip:
    """What was copied: a partial (section "") or one section, with its values."""

    section: str
    values: dict = field(default_factory=dict)  # parameter name -> display value
    source: str = ""  # "Digital 1 · partial 2", for the menu

    def describe(self) -> str:
        what = section_name(self.section) if self.section else tr("Partial")
        return tr("{what} of {source}").format(what=what, source=self.source)


_clip: Optional[Clip] = None  # shared by Digital 1 and Digital 2


def clip() -> Optional[Clip]:
    return _clip


def clear_clip() -> None:
    global _clip
    _clip = None


def _names(section: str) -> tuple[str, ...]:
    return SECTIONS[section] if section else PARTIAL_PARAMS


def _source(editor, partial: int) -> str:
    return tr("Digital {n} · partial {p}").format(n=getattr(editor, "synth_number", 1), p=partial + 1)


def copy(editor, partial: int, section: str = "") -> Clip:
    """Copy partial *partial* (0-2), or one *section* of it."""
    global _clip
    _clip = Clip(section, {name: editor.partial(name, partial).value() for name in _names(section)},
                 _source(editor, partial))
    return _clip


@contextmanager
def one_step(editor):
    """The changes made inside are one Undo step."""
    history = getattr(editor, "history", None)
    if history is not None:
        history.begin_group()
    try:
        yield
    finally:
        if history is not None:
            history.end_group()


def set_values(editor, partial: int, values: dict) -> int:
    """Set these values on partial *partial*; how many changed."""
    changed = 0
    for name, value in values.items():
        pv = editor.partial(name, partial)
        if pv.value() != pv.clamp(value):
            pv.setValue(value)
            changed += 1
    return changed


def paste(editor, partial: int) -> int:
    """Paste the clipboard into partial *partial* (the same section, or the whole partial)."""
    if _clip is None:
        return 0
    with one_step(editor), unlinked(editor):
        return set_values(editor, partial, _clip.values)


def swap(editor, first: int, second: int, section: str = "") -> int:
    """Swap two partials (or one section of them)."""
    if first == second:
        return 0
    names = _names(section)
    a = {name: editor.partial(name, first).value() for name in names}
    b = {name: editor.partial(name, second).value() for name in names}
    with one_step(editor), unlinked(editor):
        return set_values(editor, first, b) + set_values(editor, second, a)


# ------------------------------------------------------------------- linking
class PartialLink:
    """«Link partials» for one editor: a change on one partial is set on the
    other partials that are on, in the same Undo step."""

    def __init__(self, editor):
        self.editor = editor
        self.enabled = False
        self._busy = False
        self.suspended = 0
        for partial in range(PARTIALS):
            for name in LINKED:
                pv = editor.partial(name, partial)
                # valueChanged: the user's changes only (values from the JD-Xi arrive
                # with the signals blocked)
                pv.valueChanged.connect(lambda value, name=name, partial=partial: self._follow(name, partial, value))

    def _partial_on(self, partial: int) -> bool:
        try:
            return bool(self.editor.pv(f"PARTIAL{partial + 1}_SWITCH").value())
        except KeyError:
            return True

    def _follow(self, name: str, partial: int, value: int) -> None:
        history = getattr(self.editor, "history", None)
        if (not self.enabled or self._busy or self.suspended
                or (history is not None and history._replaying)):
            return
        self._busy = True
        try:
            context = history.attached() if history is not None and not history._group_depth else _nothing()
            with context:
                for other in range(PARTIALS):
                    if other != partial and self._partial_on(other):
                        self.editor.partial(name, other).setValue(value)
        finally:
            self._busy = False


@contextmanager
def _nothing():
    yield


@contextmanager
def unlinked(editor):
    """Pasting, swapping, randomizing: each partial as asked, not linked."""
    link = getattr(editor, "partial_link", None)
    if link is not None:
        link.suspended += 1
    try:
        yield
    finally:
        if link is not None:
            link.suspended -= 1


# ------------------------------------------------------------------- randomize
def _random_value(pv, amount: float, rng: random.Random) -> int:
    lo, hi = pv.minimum, pv.maximum
    if pv.info.choices or hi - lo <= 3:
        return rng.randint(lo, hi)
    span = (hi - lo) * amount
    return pv.clamp(pv.value() + rng.uniform(-span, span))


def randomize(editor, scope: str, amount: str = "medium", partial: int = 0, section: str = "",
              rng: Optional[random.Random] = None) -> int:
    """Randomize: *scope* "section" (of *partial*), "partial" or "tone" (the three
    partials, Wave Shape and Analog Feel). *amount*: "little", "medium" or "much".
    One Undo step; how many values changed."""
    rng = rng or random.Random()
    share = AMOUNTS[amount]
    much = amount == "much"
    if scope == "section":
        targets = [(partial, name) for name in SECTIONS[section]]
    elif scope == "partial":
        targets = [(partial, name) for name in PARTIAL_PARAMS]
    else:
        targets = [(p, name) for p in range(PARTIALS) for name in PARTIAL_PARAMS]
    changed = 0
    with one_step(editor), unlinked(editor):
        for p, name in targets:
            if name in STEADY_BELOW_MUCH and not much:
                continue
            pv = editor.partial(name, p)
            value = _random_value(pv, share, rng)
            if name == "AMP_LEVEL":
                value = max(value, MIN_LEVEL)
            elif name == "FILTER_CUTOFF":
                value = max(value, NO_SILENT_FILTER)
            elif name == "AMP_ENV_SUSTAIN_LEVEL" and much:
                value = max(value, 40)
            if pv.value() != value:
                pv.setValue(value)
                changed += 1
        if scope == "tone":
            for name in COMMON_RANDOM:
                pv = editor.pv(name)
                value = _random_value(pv, share, rng)
                if pv.value() != value:
                    pv.setValue(value)
                    changed += 1
    return changed
