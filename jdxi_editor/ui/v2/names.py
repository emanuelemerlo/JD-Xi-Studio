"""Short, translated names of the editors (tabs, badges), as in the mockups."""

from __future__ import annotations

from jdxi_editor.i18n import tr


def short_name(title: str) -> str:
    """The editor's short name for a tab or badge ("Digital Synth 1" -> "Digital 1")."""
    names = {
        "Digital Synth 1": tr("Digital 1"),
        "Digital Synth 2": tr("Digital 2"),
        "Analog Synth": tr("Analog"),
        "Drums": tr("Drums"),
        "Arpeggiator": tr("Arpeggio"),
        "Effects": tr("Effects"),
        "Vocal Effects": tr("Vocal FX"),
        "Program": tr("Programs"),
        "Program: common and parts": tr("Program parts"),
        "Preset": tr("Presets"),
        "Pattern": tr("Pattern"),
        "MIDI File": tr("MIDI file"),
        "Recipes": tr("Recipes"),
        "Settings": tr("Settings"),
    }
    return names.get(title, tr(title) if title else title)
