"""The preset lists: the JD-Xi's own (no SoundFont lists any more)."""

from jdxi_editor.ui.editors.pattern import preset_list_provider as provider


def test_the_lists_are_the_jdxis():
    from jdxi_editor.core.jdxi import JDXi
    from jdxi_editor.ui.editors.pattern.options import DRUM_OPTIONS

    assert provider.get_drum_options() == list(DRUM_OPTIONS)
    assert provider.get_preset_list_for_synth_type("Analog") is JDXi.UI.Preset.Analog.PROGRAM_CHANGE
    assert provider.get_preset_list_for_synth_type("Drums") is JDXi.UI.Preset.Drum.PROGRAM_CHANGE


def test_an_out_of_range_bank_gives_no_info_instead_of_an_error():
    from jdxi_editor.ui.midi.selection_info import resolve_tone_midi

    bad = [{"id": "001", "name": "Kit", "category": "SoundFont", "msb": "128", "lsb": "0", "pc": "1"}]
    assert resolve_tone_midi(1, bad, channel=9) is None
