"""The editors window header: the editors as buttons, the program, the connection."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from jdxi_editor.ui.editors.main import MainEditor
from jdxi_editor.ui.v2.names import short_name


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_short_names():
    assert short_name("Digital Synth 1") == "Digital 1"
    assert short_name("Analog Synth") == "Analog"
    assert short_name("Program") == "Programs"
    assert short_name("Something else") == "Something else"


def test_header_program_connection_and_accent(app):
    keyboard = QMainWindow()
    keyboard.midi_helper = MagicMock(is_input_open=True, is_output_open=True)
    editors = MainEditor(keyboard)
    tabs = editors.editor_tab_widget
    assert tabs.cornerWidget(Qt.Corner.TopLeftCorner).text() == "JD-Xi Studio"
    editors.set_program_name("A11 CARONDO")
    editors.set_tone_name("Springer")
    assert editors.program_chip.text() == "A11 CARONDO  ·  Springer"
    from jdxi_editor.midi.io import connection as conn

    # the shared connection: «connected» only once the JD-Xi answered (ports alone are not enough)
    shared = conn.connection_for(keyboard.midi_helper)
    saved = shared.state
    shared.blockSignals(True)  # only this indicator: no «reconnection» for the other windows
    try:
        for state, text in ((conn.VERIFYING, "Verifying"), (conn.ONLINE, "JD-Xi connected"),
                            (conn.OFFLINE, "Off-line")):
            shared.state = state
            editors.update_connection()
            assert text in editors.connection_label.text()
    finally:
        shared.state = saved
        shared.blockSignals(False)

    class Coloured(QWidget):
        ACCENT = "#eb5757"

    tabs.addTab(QWidget(), "A")
    tabs.addTab(Coloured(), "B")
    tabs.setCurrentIndex(1)
    assert "border: 1px solid #eb5757" in tabs.tabBar().styleSheet()
    tabs.setCurrentIndex(0)
    assert "border: 1px solid #3f8cff" in tabs.tabBar().styleSheet()
