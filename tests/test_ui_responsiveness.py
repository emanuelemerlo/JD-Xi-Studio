"""
Controls send each change once, labels click their buttons, layouts build cleanly.
"""

import sys
import time

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget

from jdxi_editor.ui.editors.helpers.widgets import create_round_button_with_label
from jdxi_editor.ui.widgets.editor.helper import create_centered_layout_with_widgets
from jdxi_editor.ui.widgets.label_click import find_round_button_for, make_label_clickable
from jdxi_editor.ui.widgets.slider.slider import Slider

_APP = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def slider():
    s = Slider("Cutoff", 0, 127, midi_helper=None)
    received = []
    s.valueChanged.connect(received.append)
    s.received = received
    yield s
    s.deleteLater()


def test_slider_emits_each_change_once(slider):
    """valueChanged was connected twice, so every move sent its MIDI message twice."""
    for value in (10, 11, 12):
        slider.slider.setValue(value)
    assert slider.received == [10, 11, 12]


def test_slider_drag_is_throttled_and_the_release_value_is_sent(slider):
    slider.slider.setSliderDown(True)
    for value in range(1, 60):
        slider.slider.setValue(value)
    # First move at once, the rest coalesced while the interval runs
    assert slider.received == [1]
    # The throttle timer then sends the latest value; under load it can fire
    # well after DRAG_EMIT_INTERVAL_MS, so wait for the result (up to 5 s)
    deadline = time.monotonic() + 5
    while slider.received[-1] != 59 and time.monotonic() < deadline:
        QTest.qWait(10)
    assert slider.received[-1] == 59
    slider.slider.setValue(64)
    slider.slider.setSliderDown(False)  # release
    slider.slider.sliderReleased.emit()
    assert slider.received[-1] == 64
    assert len(slider.received) < 10


def test_slider_silent_update_does_not_resend(slider):
    slider.setValueSilently(90)
    slider.slider.sliderReleased.emit()
    assert slider.received == []


def _click(widget):
    pos = QPointF(widget.width() / 2, widget.height() / 2)
    for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        event = QMouseEvent(
            kind, pos, widget.mapToGlobal(pos), Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(widget, event)


def test_clicking_the_label_of_a_round_button_clicks_it():
    clicks = []
    item, button = create_round_button_with_label("Load", "mdi.folder", slot=lambda: clicks.append(1))
    item.resize(200, 40)
    item.show()
    label_rows = [w for w in item.findChildren(QWidget) if w.property("jdxiClickForwarder")]
    assert label_rows, "the label row has no click forwarder"
    _click(label_rows[0])
    assert clicks == [1]
    assert not button.isChecked()  # action buttons do not stay lit
    item.close()


def test_label_finds_the_round_button_next_to_it_in_the_layout():
    host = QWidget()
    layout = QHBoxLayout(host)
    button = QPushButton()
    button.setFixedSize(30, 30)
    label = QLabel("Read from JD-Xi")
    layout.addWidget(button)
    layout.addWidget(label)
    make_label_clickable(label)
    assert find_round_button_for(label) is button
    clicks = []
    button.clicked.connect(lambda: clicks.append(1))
    host.show()
    _click(label)
    assert clicks == [1]
    host.close()


def test_centered_layout_holds_its_widgets_without_adding_itself():
    widgets = [QLabel("a"), QLabel("b")]
    layout = create_centered_layout_with_widgets(widgets)
    host = QWidget()
    host.setLayout(layout)
    assert all(w.parentWidget() is host for w in widgets)
    assert layout.itemAt(1).layout() is not layout


def test_mode_button_group_sends_once_per_click():
    from jdxi_editor.ui.widgets.editor.mode_button_group import ModeButtonGroup, ModeButtonSpec

    sent = []

    class Mode:
        def __init__(self, value):
            self.value = value

    modes = [Mode(0), Mode(1), Mode(2)]
    group = ModeButtonGroup(
        [ModeButtonSpec(mode=m, label=str(m.value)) for m in modes],
        send_midi_parameter=lambda param, value: sent.append(value),
        midi_param="OSC_WAVEFORM",
    )
    group.buttons[modes[2]].click()
    assert sent == [2]
    assert group.buttons[modes[2]].isChecked()
    group.deleteLater()
