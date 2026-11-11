"""New Program editor: common settings and the four parts, addresses, receiving, views."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.ui.v2 import program as pg
from jdxi_editor.ui.v2 import widgets as w
from jdxi_editor.ui.v2.framework import SEND_INTERVAL_MS, rq1


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Sysex:
    type = "sysex"

    def __init__(self, data):
        self.data = data


class FakeHelper(QObject):
    midi_sysex_json = Signal(str)
    midi_message_incoming = Signal(object)

    def __init__(self):
        super().__init__()
        self.sent = []

    def send_midi_message(self, message):
        self.sent.append(bytes(message.to_message_list()))
        return True

    def send_raw_message(self, message):
        return True


@pytest.fixture
def editor(app):
    helper = FakeHelper()
    editor = pg.ProgramPartsEditor(helper, Mock())
    editor.helper = helper
    editor.resize(1600, 1000)
    editor.show()
    QApplication.processEvents()
    helper.sent.clear()
    yield editor
    editor.close()
    editor.deleteLater()
    QApplication.processEvents()


def wait(ms: int) -> None:
    # At least half a second: slow CI machines (macOS runners) fire the send
    # timer late; waiting longer changes nothing, nothing else is pending
    deadline = time.monotonic() + max(ms, 500) / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)


def dt1(address, data):
    body = list(address) + list(data)
    checksum = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x12] + body + [checksum, 0xF7])


# Every parameter of Program Part / Zone / Common in the MIDI Implementation (reserves left out)
PART_OFFSETS = (
    [0x00, 0x01, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11]
    + list(range(0x13, 0x1D)) + [0x21, 0x22, 0x23, 0x24, 0x25, 0x2B, 0x2C, 0x2D]
    + list(range(0x2F, 0x47))
)
COMMON_OFFSETS = list(range(0x0C)) + [0x10, 0x11, 0x16, 0x1C, 0x1D, 0x1E]


def test_every_parameter_of_the_midi_implementation_is_there(editor):
    blocks = {b.key: b for b in editor.blocks}
    assert sorted(s.offset for s in blocks["PROGRAM_COMMON"].params) == COMMON_OFFSETS
    for short, _ in pg.PARTS:
        assert sorted(s.offset for s in blocks[f"PART_{short}"].params) == PART_OFFSETS, short
        assert sorted(s.offset for s in blocks[f"ZONE_{short}"].params) == [0x03, 0x19]
    assert len(editor.values) == len(COMMON_OFFSETS) + 4 * (len(PART_OFFSETS) + 2)


def test_every_parameter_has_a_control_and_an_explanation(editor):
    bound = set()
    for widget in editor.findChildren(QWidget):
        pv = getattr(widget, "pv", None)
        if isinstance(pv, w.ParamValue):
            bound.add(id(pv))
        for pv in getattr(widget, "pvs", []):
            bound.add(id(pv))
    for spec, pv in editor.values.items():
        assert id(pv) in bound, (spec.group, spec.label)
        assert pv.info.description, spec.label
        assert pv.info.page or pv.info.source, spec.label


def _last(editor):
    wait(SEND_INTERVAL_MS * 2)
    return editor.helper.sent[-1]


def test_addresses_and_encoding(editor):
    editor.part("PART_PAN", 1).setValue(-20)  # D2 Pan L20 = 44 at 18 00 21 0A
    assert _last(editor) == dt1([0x18, 0x00, 0x21, 0x0A], [44])
    editor.part("PART_COARSE_TUNE", 2).setValue(-12)  # AN, 64 = 0
    assert _last(editor) == dt1([0x18, 0x00, 0x22, 0x0B], [52])
    editor.part("PART_PORTAMENTO_TIME", 3).setValue(128)  # TONE, 2 nibbles
    assert _last(editor) == dt1([0x18, 0x00, 0x23, 0x11], [0x08, 0x00])
    editor.part("ZONE_OCTAVE_SHIFT", 0).setValue(-1)
    assert _last(editor) == dt1([0x18, 0x00, 0x30, 0x19], [63])
    editor.part("PART_SCALE_TUNE_B", 0).setValue(-12)
    assert _last(editor) == dt1([0x18, 0x00, 0x20, 0x3C], [52])
    editor.pv("PROGRAM_TEMPO").setValue(12050)  # 120.50 BPM, 4 nibbles as is
    assert _last(editor) == dt1([0x18, 0x00, 0x00, 0x11], [0x02, 0x0F, 0x01, 0x02])


def test_the_name_is_sent_as_one_message(editor):
    editor.name_field.setText("My Bass")
    editor.name_field.editingFinished.emit()
    assert editor.helper.sent == [dt1([0x18, 0x00, 0x00, 0x00], [ord(c) for c in "My Bass".ljust(12)])]


def test_a_part_dump_from_the_jdxi_is_shown_not_sent_back(editor):
    data = [0] * 0x4C
    data[0x00], data[0x01], data[0x09], data[0x0A] = 9, 1, 110, 74  # channel 10, on, level, pan 10R
    data[0x11], data[0x12] = 0x04, 0x00  # Portamento Time 64
    data[0x2D], data[0x2F], data[0x30] = 5, 1, 4  # KIT, EQUAL, key E
    data[0x35] = 50  # Scale Tune for E: -14
    editor.helper.midi_message_incoming.emit(_Sysex(dt1([0x18, 0x00, 0x23, 0x00], data)[1:-1]))
    p = lambda name: editor.part(name, 3)  # noqa: E731
    assert p("RECEIVE_CHANNEL").text() == "10" and p("PART_SWITCH").text() == "ON"
    assert p("PART_LEVEL").value() == 110 and p("PART_PAN").text() == "10R"
    assert p("PART_PORTAMENTO_TIME").text() == "64"
    assert p("PART_OUTPUT_ASSIGN").text() == "KIT"
    assert p("PART_SCALE_TUNE_TYPE").text() == "EQUAL" and p("PART_SCALE_TUNE_KEY").text() == "E"
    assert p("PART_SCALE_TUNE_E").value() == -14
    assert not p("PART_DELAY_SEND_LEVEL").is_enabled() and not p("PART_REVERB_SEND_LEVEL").is_enabled()
    assert editor.part("PART_LEVEL", 0).value() == 0  # other parts untouched
    assert editor.helper.sent == []


def test_a_single_parameter_and_the_common_block(editor):
    editor.receive_dt1(dt1([0x18, 0x00, 0x31, 0x03], [1]))  # D2 zone arpeggio ON
    assert editor.part("ARPEGGIO_SWITCH", 1).text() == "ON"
    common = [ord(c) for c in "Saw Lead    "] + [0] * 4 + [100] + [0x02, 0x0E, 0x0E, 0x00] + [0, 1] + [0] * 5 + [7, 1, 1]
    editor.receive_dt1(dt1([0x18, 0x00, 0x00, 0x00], common))
    assert editor.name_field.text() == "Saw Lead"
    assert editor.pv("PROGRAM_LEVEL").value() == 100
    assert editor.pv("PROGRAM_TEMPO").text() == "120.00"
    assert editor.pv("VOCAL_EFFECT").text() == "VOCODER"
    assert editor.pv("VOCAL_EFFECT_NUMBER").text() == "8" and editor.pv("VOCAL_EFFECT_PART").text() == "2"
    assert editor.helper.sent == []


def test_other_messages_are_ignored(editor):
    assert editor.receive_dt1(dt1([0x19, 0x42, 0x00, 0x00], [1, 2, 3])) == 0  # an Analog tone
    assert editor.receive_dt1([0xF0, 0x7E, 0x10, 0x06, 0x02, 0xF7]) == 0


def test_requests_read_every_block(editor):
    assert len(editor.midi_requests) == 9
    assert rq1([0x18, 0x00, 0x20, 0x00], 0x4C) in editor.midi_requests
    assert rq1([0x18, 0x00, 0x00, 0x00], 0x1F) == "F0 41 10 00 00 00 0E 11 18 00 00 00 00 00 00 1F 49 F7"


def test_sends_depend_on_part_output(editor):
    out = editor.part("PART_OUTPUT_ASSIGN", 0)
    out.setValue(3)  # REV
    assert not editor.part("PART_DELAY_SEND_LEVEL", 0).is_enabled()
    assert editor.part("PART_REVERB_SEND_LEVEL", 0).is_enabled()
    out.setValue(4)  # DIR
    assert not editor.part("PART_REVERB_SEND_LEVEL", 0).is_enabled()
    assert editor.part("PART_OUTPUT_ASSIGN", 0).maximum == 4  # KIT only for drums
    assert editor.part("PART_OUTPUT_ASSIGN", 3).maximum == 5


def test_velocity_range_stays_ordered(editor):
    lower, upper = editor.part("VELOCITY_RANGE_LOWER", 1), editor.part("VELOCITY_RANGE_UPPER", 1)
    upper.setValue(60)
    lower.setValue(80)
    assert upper.value() == 80
    upper.setValue(30)
    assert lower.value() == 30


def test_sections_show_one_at_a_time(editor):
    assert editor.sections.currentIndex() == 0
    editor.section_buttons.button(4).click()
    assert editor.sections.currentIndex() == 4
    views = editor.sections.currentWidget().findChildren(pg.ScaleView)
    assert len(views) == 4


def test_pan_and_tempo_typing(editor):
    knob = next(k for k in editor.findChildren(w.Knob) if k.pv is editor.part("PART_PAN", 0))
    knob.field.setText("L32")
    knob.field.editingFinished.emit()
    assert knob.pv.value() == -32 and knob.field.text() == "L32"
    tempo = next(k for k in editor.findChildren(w.Knob) if k.pv is editor.pv("PROGRAM_TEMPO"))
    tempo.field.setText("98,5")
    tempo.field.editingFinished.emit()
    assert tempo.pv.value() == 9850 and tempo.field.text() == "98.50"


def test_scale_view_drag_retunes_a_note(editor):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    editor.show_section(4)
    QApplication.processEvents()
    view = editor.sections.currentWidget().findChildren(pg.ScaleView)[0]
    slot = view._slot(4)  # E
    pos = QPointF(slot.center().x(), slot.top())
    for kind in (QMouseEvent.Type.MouseButtonPress, QMouseEvent.Type.MouseButtonRelease):
        QApplication.sendEvent(view, QMouseEvent(kind, pos, pos, Qt.MouseButton.LeftButton,
                                                 Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert view.notes[4].value() == 63
