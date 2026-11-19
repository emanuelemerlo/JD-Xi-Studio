"""A «?» per section (sound-design spec §7, Phase 6): what, how, an example."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.ui.v2 import section_help as sh
from jdxi_editor.ui.v2.widgets import Card


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_every_section_has_three_lines():
    for kind in ("osc", "filter", "amp", "lfo", "mod_lfo", "pitch", "effect", "delay", "reverb"):
        assert all(sh.text(kind)), kind
    assert sh.kind_of("OSC") == "osc" and sh.kind_of("EFFECT 2") == "effect" and sh.kind_of("MISC") is None


def test_the_cards_of_an_editor_show_their_help(app):
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.analog import AnalogToneEditor
    from jdxi_editor.ui.v2.digital import DigitalToneEditor

    for cls in (DigitalToneEditor, AnalogToneEditor):
        editor = cls(MidiIOHelper(), MagicMock())
        cards = [c for c in editor.findChildren(Card) if c.help_button is not None]
        titles = {c.findChild(type(c.help_button)).parent() for c in cards}
        assert len(cards) >= 4 and titles
        cards[0].help_button.click()
        assert editor.info_panel.name.text() == "About this section"
        assert "Example:" in editor.info_panel.description.text()
        editor.close()
        editor.deleteLater()


def test_a_card_without_a_known_section_has_no_button(app):
    assert Card("MISC", "#fff").help_button is None
