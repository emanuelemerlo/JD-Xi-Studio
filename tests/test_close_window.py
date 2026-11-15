"""Closing the keyboard window ends the program, also after «Discard the changes»."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.data.parameter.analog.address import AnalogParam as P
from jdxi_editor.ui.v2 import history


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    w = JDXiInstrument()
    w.show()
    for _ in range(10):
        app.processEvents()
    yield w
    w.on_closed = None
    w.close()


def settle():
    for _ in range(10):
        QApplication.processEvents()


def modify(window):
    editor = window._tab_editor("analog")
    pv = editor.values[P.FILTER_CUTOFF]
    pv.setValue(17 if pv.value() != 17 else 18)
    settle()
    assert any(h.modified for h in history.histories())


def test_discard_closes_and_quits(window, monkeypatch):
    modify(window)
    monkeypatch.setattr(history, "ask", lambda labels, action, parent=None: "discard")
    window.on_closed = quit_app = Mock()
    assert window.close()
    settle()
    assert not window.isVisible()
    quit_app.assert_called_once()
    assert not any(h.modified for h in history.histories())


def test_cancel_keeps_the_window(window, monkeypatch):
    modify(window)
    monkeypatch.setattr(history, "ask", lambda labels, action, parent=None: "cancel")
    window.on_closed = quit_app = Mock()
    assert not window.close()
    settle()
    assert window.isVisible()
    quit_app.assert_not_called()
    monkeypatch.setattr(history, "ask", lambda labels, action, parent=None: "discard")


def test_a_failing_step_does_not_keep_the_window_open(window, monkeypatch):
    monkeypatch.setattr(window.midi_helper, "close_ports", Mock(side_effect=RuntimeError("port")))
    window.on_closed = quit_app = Mock()
    assert window.close()
    settle()
    assert not window.isVisible()
    quit_app.assert_called_once()
