"""
Where a checked row lives in the open editors, what is set there now, and setting it.

``editors(key)`` returns the editor for an editor key ("analog", "digital1",
...), opening it when needed. Setting a value goes through the editor's
ParamValue, so it is sent to the JD-Xi exactly as when the control is moved.
"""

from __future__ import annotations

from typing import Callable, Optional

from jdxi_editor.recipes.check import Checked
from jdxi_editor.ui.v2.params import ParamValue

EditorProvider = Callable[[str], object]


def _v2_value(editor, name: str, group_end: str = "") -> Optional[ParamValue]:
    for spec, pv in editor.values.items():
        if getattr(spec, "name", None) == name and (not group_end or str(spec.group).endswith(group_end)):
            return pv
    return None


def _effect_type(editor, block: str) -> str:
    pv = editor.pv("EFX1_TYPE" if block == "EFFECT1" else "EFX2_TYPE")
    return pv.text().upper()


def values_for(checked: Checked, editors: EditorProvider) -> list[ParamValue]:
    """The ParamValues the row sets (one per partial / instrument / part / wave)."""
    target = checked.target
    if target is None:
        return []
    editor = editors(target.editor_key)
    if editor is None:
        return []
    part, name = target.part, target.names[0]
    if part == "AN":
        from jdxi_editor.midi.data.parameter.analog.address import AnalogParam

        return [editor.values[AnalogParam[name]]]
    if part in ("D1", "D2"):
        if target.special == "partial_switch":
            return [editor.pv(f"PARTIAL{p + 1}_SWITCH") for p in checked.su]
        if checked.su and target.su == "facoltativo":
            return [editor.partial(name, p) for p in checked.su]
        return [editor.pv(name)]
    if part == "DR":
        if name == "KIT_LEVEL":
            return [editor.pv("KIT_LEVEL")]
        out = []
        for index in checked.su:
            if name.startswith("WMT") and name[3].isdigit():
                for w in checked.wave or [0]:
                    out.append(editor.partial(f"WMT{w + 1}{name[4:]}", index))
            else:
                out.append(editor.partial(name, index))
        return out
    if part == "PROG":
        if checked.su:
            return [editor.part(name, p) for p in checked.su]
        return [editor.pv(name, "PROGRAM_COMMON")]
    if part == "EFFETTI":
        if target.special in ("efx2_rate", "delay_time"):
            return [pv for pv in _special_values(checked, editor) if pv is not None]
        if any("·" in g for g in target.groups):
            block = target.group
            current = _effect_type(editor, block)
            for spec_name, group in zip(target.names, target.groups):
                if group.endswith(current):
                    return [_v2_value(editor, spec_name, group)]
            return []  # the parameter does not exist for the selected type
        return [_v2_value(editor, name)]
    return [editor.pv(name)]


def _special_values(checked: Checked, editor) -> list[Optional[ParamValue]]:
    target = checked.target
    is_note = checked.parsed is not None and checked.parsed.kind == "value" and _is_note_value(checked)
    if target.special == "delay_time":
        return [_v2_value(editor, "DELAY_NOTE" if is_note else "DELAY_TIME_MS")]
    current = _effect_type(editor, "EFFECT2")
    group = f"EFFECT2 · {current}"
    if current == "SLICER":
        return [_v2_value(editor, "EFX2_PARAM_2", group)]
    if current in ("FLANGER", "PHASER"):
        return [_v2_value(editor, "EFX2_PARAM_3" if is_note else "EFX2_PARAM_2", group)]
    return []


def _is_note_value(checked: Checked) -> bool:
    return "/" in checked.row.value or checked.row.value.strip() in ("1", "2")


def current_text(checked: Checked, editors: EditorProvider) -> str:
    pvs = values_for(checked, editors)
    texts = []
    for pv in pvs:
        if pv is not None and pv.text() not in texts:
            texts.append(pv.text())
    return " / ".join(texts) if texts else "—"


def is_done(checked: Checked, editors: EditorProvider) -> Optional[bool]:
    """True when every value the row sets is as the recipe says (in the range for ranges); None for 'by ear'."""
    parsed = checked.parsed
    if parsed is None or parsed.kind == "ear":
        return None
    pvs = [pv for pv in values_for(checked, editors) if pv is not None]
    if not pvs:
        return False
    if parsed.kind == "range":
        return all(parsed.lo <= pv.value() <= parsed.hi for pv in pvs)
    return all(pv.value() == parsed.value for pv in pvs)


def apply(checked: Checked, editors: EditorProvider) -> int:
    """Set the row's value (the middle of a range); returns how many values were set."""
    parsed = checked.parsed
    if parsed is None or parsed.kind == "ear" or checked.excluded:
        return 0
    target = checked.target
    editor = editors(target.editor_key)
    if target.special == "delay_time":
        editor.pv("DELAY_TIME_NOTE_MODE").setValue(1 if _is_note_value(checked) else 0)
    if target.special == "efx2_rate" and _effect_type(editor, "EFFECT2") in ("FLANGER", "PHASER"):
        group = f"EFFECT2 · {_effect_type(editor, 'EFFECT2')}"
        switch = _v2_value(editor, "EFX2_PARAM_1", group)
        if switch is not None:
            switch.setValue(1 if _is_note_value(checked) else 0)
    count = 0
    for pv in values_for(checked, editors):
        if pv is None:
            continue
        if parsed.kind == "range" and parsed.lo <= pv.value() <= parsed.hi:
            continue  # already in the range: left as the user tuned it
        pv.setValue(parsed.value)
        count += 1
    return count
