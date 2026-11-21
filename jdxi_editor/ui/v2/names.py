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
        "Program settings": tr("Program settings"),
        "Preset": tr("Presets"),
        "Pattern": tr("Pattern"),
        "MIDI File": tr("MIDI Player"),
        "MIDI Player": tr("MIDI Player"),
        "Recipes": tr("Recipes"),
        "Settings": tr("Settings"),
    }
    return names.get(title, tr(title) if title else title)


def tab_tip(title: str) -> str:
    """The tab's tooltip: what the editor is, in the language of the app
    (it showed the internal English title, "Arpeggiator", "Program")."""
    tips = {
        "Program": tr("Programs: the library of the JD-Xi's programs, the parts and the mixer"),
        "Program settings": tr("Program settings: what the program keeps besides its tones"),
        "Digital Synth 1": tr("Digital 1: the tone of the first digital part"),
        "Digital Synth 2": tr("Digital 2: the tone of the second digital part"),
        "Analog Synth": tr("Analog: the tone of the analog part"),
        "Drums": tr("Drums: the drum kit"),
        "Arpeggiator": tr("Arpeggio: the arpeggiator of the program"),
        "Effects": tr("Effects: EFX1, EFX2, Delay and Reverb of the program"),
        "Vocal Effects": tr("Vocal FX: the vocoder and Auto-Pitch"),
        "Pattern": tr("Pattern: the pattern sequencer"),
        "MIDI Player": tr("MIDI Player: MIDI files played on the JD-Xi"),
        "Recipes": tr("Recipes: a sound made step by step on the JD-Xi"),
        "Settings": tr("Settings: the JD-Xi's system settings and the editor's"),
    }
    return tips.get(title, short_name(title))
