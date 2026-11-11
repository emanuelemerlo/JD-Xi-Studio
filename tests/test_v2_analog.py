"""New Analog editor: every parameter on screen, sending, receiving, graphs, information."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.midi.data.parameter.analog.address import AnalogParam as P
from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.v2 import widgets as w
from jdxi_editor.ui.v2.analog import SEND_INTERVAL_MS, AnalogToneEditor


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app):
    editor = AnalogToneEditor(MidiIOHelper(), Mock())
    sent = []
    editor.send_midi_parameter = lambda param, value, address=None: sent.append((param, value)) or True
    editor.sent = sent
    editor.resize(1500, 950)
    editor.show()
    QApplication.processEvents()
    yield editor
    editor.close()
    editor.deleteLater()
    QApplication.processEvents()


def wait(ms: int) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)


def _bound(widget: QWidget):
    pv = getattr(widget, "pv", None)
    found = {pv.param} if pv is not None else set()
    for name in ("a", "d", "s", "r", "depth", "cutoff", "resonance", "mode", "shape", "rate", "fade", "sync", "note"):
        value = getattr(widget, name, None)
        if isinstance(value, w.ParamValue):
            found.add(value.param)
    return found


def test_every_analog_parameter_has_a_control_on_screen(editor):
    """Principle 1: nothing of the Parameter Guide is left out."""
    expected = {p for p in P if not p.name.startswith("TONE_NAME")}
    assert set(editor.controls) == expected
    on_screen = set()
    for widget in editor.findChildren(QWidget):
        on_screen |= _bound(widget)
    assert on_screen == expected, sorted(p.name for p in expected - on_screen)


def test_panels_are_named_and_ordered_as_on_the_display(editor):
    assert list(editor.panels) == ["OSC", "PITCH", "FILTER", "AMP", "LFO", "COMMON"]
    for param, pv in editor.values.items():
        assert pv.info.group in editor.panels, param.name


def test_a_change_is_sent_once_in_display_units(editor):
    editor.values[P.OSC_PITCH_COARSE].setValue(12)
    assert editor.sent == [(P.OSC_PITCH_COARSE, 12)]  # the composer converts it to 76 (64 = 0)


def test_dragging_sends_at_most_every_interval_and_the_last_value(editor):
    cutoff = editor.values[P.FILTER_CUTOFF]
    for value in range(10, 60):
        cutoff.setValue(value)
    assert editor.sent == [(P.FILTER_CUTOFF, 10)]  # first at once, the rest waits
    wait(SEND_INTERVAL_MS * 3)
    assert editor.sent[-1] == (P.FILTER_CUTOFF, 59)
    assert len(editor.sent) == 2


def test_values_from_the_jdxi_are_shown_not_sent_back(editor):
    ok, failed = [], []
    editor._update_controls(0, {"OSC_PITCH_COARSE": 76, "FILTER_CUTOFF_KEYFOLLOW": 69, "LFO_SHAPE": 3}, ok, failed)
    assert editor.values[P.OSC_PITCH_COARSE].value() == 12
    assert editor.values[P.FILTER_CUTOFF_KEYFOLLOW].value() == 50
    assert editor.values[P.LFO_SHAPE].value() == 3
    assert editor.sent == [] and failed == []
    data = editor.get_controls_as_dict()
    assert data["OSC_PITCH_COARSE"] == 12 and len(data) == 46


def test_controls_without_effect_are_greyed_out(editor):
    v = editor.values
    v[P.OSC_WAVEFORM].setValue(1)  # TRI
    assert not v[P.OSC_PULSE_WIDTH].is_enabled()
    v[P.OSC_WAVEFORM].setValue(2)  # PW-SQR
    assert v[P.OSC_PULSE_WIDTH].is_enabled()
    v[P.FILTER_MODE_SWITCH].setValue(0)  # BYPASS
    assert not v[P.FILTER_CUTOFF].is_enabled() and not v[P.FILTER_ENV_DEPTH].is_enabled()
    v[P.LFO_TEMPO_SYNC_SWITCH].setValue(1)
    assert not v[P.LFO_RATE].is_enabled() and v[P.LFO_TEMPO_SYNC_NOTE].is_enabled()
    knob = next(k for k in editor.findChildren(w.Knob) if k.pv is v[P.LFO_RATE])
    assert not knob.isEnabled()


def _press(widget, pos, kind=QMouseEvent.Type.MouseButtonPress):
    event = QMouseEvent(kind, QPointF(pos), QPointF(pos), Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, event)


def test_knob_keys_and_typing(editor):
    knob = next(k for k in editor.findChildren(w.Knob) if k.pv.param is P.FILTER_CUTOFF_KEYFOLLOW)
    knob.setFocus()
    QApplication.processEvents()
    knob.keyPressEvent(_key(Qt.Key.Key_Up))
    assert knob.pv.value() == 10  # Key Follow moves in steps of 10
    knob.field.setText("+70")
    knob.field.editingFinished.emit()
    assert knob.pv.value() == 70 and knob.field.text() == "+70"
    bend = next(k for k in editor.findChildren(w.Knob) if k.pv.param is P.PITCH_BEND_DOWN)
    bend.field.setText("-12")
    bend.field.editingFinished.emit()
    assert bend.pv.value() == 12 and bend.field.text() == "-12 st"  # shown as on the display


def _key(key):
    from PySide6.QtGui import QKeyEvent

    return QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)


def test_envelope_points_can_be_dragged(editor):
    view = next(
        e for e in editor.findChildren(w.EnvelopeView) if e.a.param is P.AMP_ENV_ATTACK_TIME
    )
    r = view.plot_rect()
    target = QPointF(r.left() + r.width() * 0.27 * 0.5, r.top())  # half of the attack slot
    _press(view, view.handles()[0][0])
    _press(view, target, QMouseEvent.Type.MouseMove)
    _press(view, target, QMouseEvent.Type.MouseButtonRelease)
    assert abs(view.a.value() - 64) <= 2


def test_filter_curve_drag_sets_cutoff_and_resonance(editor):
    editor.values[P.FILTER_MODE_SWITCH].setValue(1)
    view = editor.findChildren(w.FilterCurveView)[0]
    r = view.plot_rect()
    target = QPointF(r.left() + r.width() * 0.75, r.top())  # right and high
    _press(view, target)
    _press(view, target, QMouseEvent.Type.MouseButtonRelease)
    assert abs(editor.values[P.FILTER_CUTOFF].value() - 95) <= 2
    assert editor.values[P.FILTER_RESONANCE].value() == 127


def test_the_information_panel_explains_the_parameter_under_the_pointer(editor):
    pv = editor.values[P.FILTER_CUTOFF]
    editor.values[P.FILTER_MODE_SWITCH].setValue(0)
    editor.info_hub.shown.emit(pv)
    panel = editor.info_panel
    assert panel.name.text() == "Cutoff"
    assert "Range: 0 … 127" == panel.range.text()
    assert "Parameter Guide, p. 12" == panel.source.text()
    assert panel.depends.text().startswith("Inactive now.")
    pv.setValue(80)
    assert panel.value.text() == "80"


def test_every_parameter_has_an_explanation(editor):
    for param, pv in editor.values.items():
        assert pv.info.description, param.name
        assert pv.info.page or "MIDI" in pv.info.depends, param.name


def test_two_columns_on_a_small_screen(editor):
    editor.resize(1280, 760)
    QApplication.processEvents()
    assert editor._columns == 2
    editor.resize(1600, 960)
    QApplication.processEvents()
    assert editor._columns == 3


def test_the_main_window_has_window_buttons(app):
    from PySide6.QtWidgets import QMainWindow

    from jdxi_editor.ui.windows.jdxi.window_buttons import add_window_buttons

    window = QMainWindow()
    window.menuBar().addMenu("File")
    buttons = add_window_buttons(window)
    window.show()
    QApplication.processEvents()
    assert window.menuBar().cornerWidget(Qt.Corner.TopRightCorner) is buttons
    buttons.maximize_button.click()
    QApplication.processEvents()
    assert window.isMaximized() and buttons.maximize_button.toolTip() == "Restore"
    buttons.maximize_button.click()
    QApplication.processEvents()
    assert not window.isMaximized()
    buttons.close_button.click()
    QApplication.processEvents()
    assert not window.isVisible()
