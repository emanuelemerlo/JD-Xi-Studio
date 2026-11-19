"""
Preset lists for the Digital, Analog and Drums rows and preset widgets: the
JD-Xi's own (the SoundFont lists went with FluidSynth).
"""

from typing import Any, Dict, List, Union

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.ui.editors.pattern.options import DIGITAL_OPTIONS, DRUM_OPTIONS


def get_digital_options() -> List[str]:
    """Options for Digital Synth 1/2 rows: note names (C4, …)."""
    return list(DIGITAL_OPTIONS)


def get_analog_options() -> List[str]:
    """Options for the Analog Synth row: note names."""
    return list(DIGITAL_OPTIONS)


def get_drum_options() -> List[str]:
    """Options for the Drums row: the JD-Xi's drum names."""
    return list(DRUM_OPTIONS)


def get_preset_list_for_synth_type(
    synth_type: str,
) -> Union[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    """The JD-Xi preset list for "Analog", "Digital" or "Drums"."""
    return _get_jdxi_preset_list(synth_type)


def _get_jdxi_preset_list(synth_type: str) -> Union[Dict, List]:
    """Return built-in JD-Xi preset list for the given synth type."""
    if synth_type == "Analog":
        return JDXi.UI.Preset.Analog.PROGRAM_CHANGE
    if synth_type == "Digital":
        return JDXi.UI.Preset.Digital.PROGRAM_CHANGE
    if synth_type == "Drums":
        return JDXi.UI.Preset.Drum.PROGRAM_CHANGE
    return JDXi.UI.Preset.Digital.PROGRAM_CHANGE
