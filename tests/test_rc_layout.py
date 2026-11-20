"""Layout fixes found trying the release candidate."""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from jdxi_editor.midi.io.helper import MidiIOHelper


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _helper():
    helper = Mock(spec=MidiIOHelper)
    helper.midi_out = Mock()
    return helper


def test_message_box_buttons_show_their_whole_text(app):
    """«Scarta le modifiche» was cut: the buttons' width came before the
    style sheet's padding."""
    from jdxi_editor.ui.v2.restyle import MESSAGE_BOX_STYLE, fit_buttons

    box = QMessageBox()
    long = box.addButton("Scarta le modifiche al programma", QMessageBox.ButtonRole.DestructiveRole)
    box.setStyleSheet(MESSAGE_BOX_STYLE)
    fit_buttons(box)
    assert long.minimumWidth() >= long.fontMetrics().horizontalAdvance(long.text()) + 28


def test_spin_boxes_have_buttons_to_hit(app):
    """The up / down buttons were thin slits with tiny dots."""
    from pathlib import Path

    from jdxi_editor.ui.v2.restyle import spin_arrow, stylesheet

    sheet = stylesheet("X", "#3f8cff")
    assert "QSpinBox::up-button" in sheet and "width: 22px" in sheet
    assert sheet.index("padding-right: 24px") > sheet.index("padding: 2px 6px")  # not overridden
    assert Path(spin_arrow("up")).is_file() and Path(spin_arrow("down")).is_file()


def test_pattern_transport_one_width(app):
    """Play, Stop, Pause, Shuffle stretched with the window, Tap did not."""
    from jdxi_editor.ui.v2 import players

    editor = players.PatternSequenceEditor(midi_helper=_helper(), preset_helper=Mock())
    buttons = (editor.play_button, editor.stop_button, editor.pause_button, editor.shuffle_button)
    for width in (1400, 2400):
        editor.resize(width, 900)
        editor.show()
        app.processEvents()
        assert len({b.width() for b in buttons}) == 1
    first = buttons[0].width()
    editor.resize(1400, 900)
    app.processEvents()
    assert buttons[0].width() == first  # the window's width does not change them
    editor.close()


def test_automation_label_stays_by_its_controls(app):
    """«Automation:» drifted away from its combos as the window grew."""
    from jdxi_editor.ui.v2 import players

    editor = players.MidiFilePlayer(midi_helper=_helper())
    editor.resize(2400, 950)
    editor.show()
    app.processEvents()
    combo = editor.automation.automation_channel_combo
    from PySide6.QtWidgets import QLabel

    label = next(l for l in editor.automation.findChildren(QLabel) if l.text().startswith("Automation"))
    gap = combo.mapTo(editor, combo.rect().topLeft()).x() - label.mapTo(editor, label.rect().topRight()).x()
    assert gap < 40, gap
    editor.transport_controller.shutdown()
    editor.close()
