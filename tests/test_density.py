"""The compact layout for low screens (1080p at 125%: 1536x864; 2496x1664 at 175%: 1426x951)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QScrollArea, QTabWidget

from jdxi_editor.ui.v2 import density


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def compact(monkeypatch):
    monkeypatch.setenv("JDXI_COMPACT", "1")
    monkeypatch.setenv("JDXI_NARROW", "1")


def _overflow(editor, width, height, app):
    editor.resize(width, height)
    editor.show()
    for _ in range(5):
        app.processEvents()
    worst = 0, 0
    for area in editor.findChildren(QScrollArea):
        content = area.widget()
        if content is None or not area.isVisible():
            continue
        vw, vh = area.viewport().width(), area.viewport().height()
        h = content.heightForWidth(vw) if content.hasHeightForWidth() else content.sizeHint().height()
        h = max(h, content.minimumSizeHint().height())
        worst = max(worst[0], content.minimumSizeHint().width() - vw), max(worst[1], h - vh)
    return worst


def test_switches(monkeypatch):
    monkeypatch.setenv("JDXI_COMPACT", "1")
    assert density.compact() and density.px(100) < 100
    monkeypatch.setenv("JDXI_COMPACT", "0")
    assert not density.compact() and density.px(100) == 100


def test_digital_compact_has_section_tabs_and_little_scroll(app, compact):
    from unittest.mock import Mock

    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.digital import DigitalToneEditor

    editor = DigitalToneEditor(MidiIOHelper(), Mock())
    try:
        tabs = [t for t in editor.findChildren(QTabWidget) if t.count() == 2]
        assert len(tabs) == 3  # one per partial
        tabs[0].setCurrentIndex(1)
        assert all(t.currentIndex() == 1 for t in tabs)  # every partial on the same tab
        horizontal, vertical = _overflow(editor, 1536 - 40, 760, app)
        assert horizontal <= 0 and vertical < 200
    finally:
        editor.close()


def test_effects_cards_are_as_tall_as_the_type_shown(app):
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.effects import EffectsEditor

    editor = EffectsEditor(midi_helper=MidiIOHelper())
    try:
        editor.resize(1400, 900)
        editor.show()
        app.processEvents()
        thru = editor.cards["EFX1"].sizeHint().height()
        editor.pv("EFX1_TYPE").setValue(3)  # Compressor: the most controls
        app.processEvents()
        assert editor.cards["EFX1"].sizeHint().height() > thru + 100
        assert editor.pages["EFX1"].currentIndex() == 3
    finally:
        editor.close()


def test_programs_compact_puts_the_library_in_the_tabs(app, compact):
    from jdxi_editor.midi.io.helper import MidiIOHelper
    from jdxi_editor.ui.v2.programs import ProgramEditor

    editor = ProgramEditor(midi_helper=MidiIOHelper())
    try:
        assert editor.more_tabs.count() >= 5 and editor.more_tabs.currentIndex() == 0
        horizontal, vertical = _overflow(editor, 1496, 760, app)
        assert horizontal <= 0 and vertical <= 40
    finally:
        editor.close()
