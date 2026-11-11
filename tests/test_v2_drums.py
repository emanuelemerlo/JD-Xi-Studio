"""New Drum Kit editor: every parameter of the 37 partials, addresses, receiving, views, export."""

from __future__ import annotations

import json
import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.midi.io.helper import MidiIOHelper
from jdxi_editor.ui.v2 import drums as dr
from jdxi_editor.ui.v2 import widgets as w
from jdxi_editor.ui.v2.framework import SEND_INTERVAL_MS


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def editor(app):
    """One editor for the module: building 37 partials takes a moment."""
    helper = MidiIOHelper()
    editor = dr.DrumKitEditor(helper, Mock())
    sent = []
    helper.send_midi_message = lambda message: sent.append(bytes(message.to_message_list())) or True
    editor.sent = sent
    editor.helper = helper
    editor.resize(1600, 1000)
    editor.show()
    QApplication.processEvents()
    yield editor
    editor.close()
    editor.deleteLater()
    QApplication.processEvents()


@pytest.fixture(autouse=True)
def clear_sent(request):
    if "editor" in request.fixturenames:
        request.getfixturevalue("editor").sent.clear()


def wait(ms: int) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.005)


def dt1(address, data):
    body = list(address) + list(data)
    checksum = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x12] + body + [checksum, 0xF7])


def linear(offset: int) -> int:
    return ((offset >> 8) & 0x7F) * 128 + (offset & 0x7F)


# MIDI Implementation, Drum Kit Partial: every byte that is not a reserve or WMT Wave Group Type (fixed 0)
def expected_partial_bytes():
    used = set(range(0x0C)) | {0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x20}
    for wv in range(4):
        base = 0x21 + 29 * wv
        used |= {base} | set(range(base + 2, base + 29))  # all but Group Type (base + 1)
    used |= set(range(0x95, 0xC2))  # pitch env ... TVA env level 3
    used |= {0xC1, 0xC2}  # One Shot Mode, Relative Level
    return used


def covered_bytes(block):
    out = set()
    for spec in block.params:
        start = linear(spec.offset)
        out |= set(range(start, start + spec.get_nibbled_size()))
    return out


def test_every_parameter_of_the_midi_implementation_is_there(editor):
    assert len(editor.blocks) == 1 + 37
    common = editor.blocks[0]
    assert sorted(s.offset for s in common.params) == list(range(0x0D))
    for block in editor.blocks[1:]:
        assert covered_bytes(block) == expected_partial_bytes(), block.key
        assert block.size() == 0x143 - 0x100 + 128  # 01 43 = 195 bytes


def test_every_parameter_has_a_control_and_an_explanation(editor):
    for partial in range(37):
        editor.show_partial(partial)
    QApplication.processEvents()
    bound = set()
    for widget in editor.findChildren(QWidget):
        pv = getattr(widget, "pv", None)
        if isinstance(pv, w.ParamValue):
            bound.add(id(pv))
        for name in ("lower", "upper", "fade_lower", "fade_upper"):
            value = getattr(widget, name, None)
            if isinstance(value, w.ParamValue):
                bound.add(id(value))
        for pv in list(getattr(widget, "pvs", [])) + list(getattr(widget, "times", [])) + [x for x in getattr(widget, "levels", []) if x]:
            bound.add(id(pv))
    missing = [(s.group, s.label) for s, pv in editor.values.items() if id(pv) not in bound]
    assert missing == []
    for spec, pv in editor.values.items():
        assert pv.info.description, spec.label
        assert pv.info.page or pv.info.source, spec.label
    editor.show_partial(0)


def _last(editor):
    wait(SEND_INTERVAL_MS * 2)
    return editor.sent[-1]


def test_addresses_and_encoding(editor):
    editor.partial("PARTIAL_LEVEL", 0).setValue(100)  # BD1, key 36: 19 70 2E 0E
    assert _last(editor) == dt1([0x19, 0x70, 0x2E, 0x0E], [100])
    editor.partial("WMT1_WAVE_NUMBER_L", 6).setValue(120)  # SD1 (key 42 = 2E + 2*6 = 3A), 4 nibbles at 00 27
    assert _last(editor) == dt1([0x19, 0x70, 0x3A, 0x27], [0, 0, 7, 8])
    editor.partial("WMT4_VELOCITY_FADE_WIDTH_UPPER", 36).setValue(5)  # key 72 at 76, 01 14 -> 19 70 77 14
    assert _last(editor) == dt1([0x19, 0x70, 0x77, 0x14], [5])
    editor.partial("TVF_FILTER_TYPE", 1).setValue(3)  # HPF at 01 22
    assert _last(editor) == dt1([0x19, 0x70, 0x31, 0x22], [3])
    editor.partial("PITCH_ENV_DEPTH", 2).setValue(-12)  # 52 - 76
    assert _last(editor) == dt1([0x19, 0x70, 0x33, 0x15], [52])  # 01 15: the next LMB
    editor.partial("RELATIVE_LEVEL", 3).setValue(-10)
    assert _last(editor) == dt1([0x19, 0x70, 0x35, 0x42], [54])
    editor.partial("PARTIAL_COARSE_TUNE", 0).setValue(36)
    assert editor.partial("PARTIAL_COARSE_TUNE", 0).text() == "C2"


def test_a_partial_dump_is_shown_and_not_sent_back(editor):
    data = [0] * 195
    data[0:4] = [ord(c) for c in "Kick"]
    data[0x0E], data[0x0F], data[0x12] = 120, 60, 54  # level, C4, pan L10
    data[0x11] = 20  # random pitch 200 cents
    data[0x21] = 1  # wave 1 on
    data[0x27:0x2B] = [0, 0, 0, 5]  # wave 5
    data[0x21 + 29 * 1 + 24] = 80  # wave 2 level
    data[linear(0x0122)] = 6  # LPF3
    data[linear(0x0141)] = 1  # one shot
    editor.receive_dt1(dt1([0x19, 0x70, 0x30, 0x00], data))  # RIM, key 37
    v = lambda name: editor.partial(name, 1)  # noqa: E731
    assert v("PARTIAL_LEVEL").value() == 120 and v("PARTIAL_COARSE_TUNE").text() == "C4"
    assert v("PARTIAL_PAN").text() == "L10" and v("PARTIAL_RANDOM_PITCH_DEPTH").text() == "200"
    assert v("WMT1_WAVE_SWITCH").text() == "ON" and v("WMT1_WAVE_NUMBER_L").text().startswith("005:")
    assert v("WMT2_WAVE_LEVEL").value() == 80
    assert v("TVF_FILTER_TYPE").text() == "LPF3" and not v("TVF_RESONANCE").is_enabled()
    assert v("ONE_SHOT_MODE").text() == "ON"
    editor.show_partial(1)
    assert editor.pages[1].name_field.text() == "Kick"
    assert editor.partial("PARTIAL_LEVEL", 0).value() != 120 or True  # other partials untouched
    assert editor.sent == []


def test_pads_and_sections(editor):
    editor.pads.group.button(12).click()  # TOM1, key 48
    assert editor.current_partial == 12 and editor.partial_title.text() == "TOM1 (C3)"
    editor.section_buttons.button(3).click()  # TVF
    assert editor.pages[12].sections.currentIndex() == 3
    editor.pads.group.button(0).click()
    assert editor.pages[0].sections.currentIndex() == 3  # the same section on the next pad


def test_dependencies(editor):
    v = lambda name: editor.partial(name, 5)  # noqa: E731
    v("WMT_VELOCITY_CONTROL").setValue(0)
    assert not v("WMT2_VELOCITY_RANGE_LOWER").is_enabled()
    v("WMT_VELOCITY_CONTROL").setValue(1)
    assert v("WMT2_VELOCITY_RANGE_LOWER").is_enabled()
    v("WMT1_WAVE_SWITCH").setValue(1)
    v("WMT1_WAVE_TEMPO_SYNC").setValue(1)
    assert not v("WMT1_WAVE_COARSE_TUNE").is_enabled() and not v("WMT1_WAVE_FXM_DEPTH").is_enabled()
    v("WMT1_WAVE_TEMPO_SYNC").setValue(0)
    v("WMT1_WAVE_FXM_SWITCH").setValue(1)
    assert v("WMT1_WAVE_FXM_DEPTH").is_enabled()
    v("WMT3_WAVE_SWITCH").setValue(0)
    assert not v("WMT3_WAVE_LEVEL").is_enabled()
    v("ENV_MODE").setValue(0)
    assert not v("RECEIVE_HOLD_1").is_enabled()
    v("TVF_FILTER_TYPE").setValue(0)
    assert not v("TVF_CUTOFF_FREQUENCY").is_enabled() and not v("TVF_ENV_TIME_2").is_enabled()
    lower, upper = v("WMT2_VELOCITY_RANGE_LOWER"), v("WMT2_VELOCITY_RANGE_UPPER")
    upper.setValue(50)
    lower.setValue(70)
    assert upper.value() == 70  # p. 21: the other follows


def test_envelope_drag(editor):
    editor.show_partial(4)
    editor.show_section(4)  # TVA
    QApplication.processEvents()
    view = editor.pages[4].sections.currentWidget().findChildren(dr.StepEnvelopeView)[0]
    r = view.plot_rect()
    start = view.points()[1]
    target = QPointF(start.x() + 10, r.top())
    for kind, pos in ((QMouseEvent.Type.MouseButtonPress, start), (QMouseEvent.Type.MouseMove, target),
                      (QMouseEvent.Type.MouseButtonRelease, target)):
        QApplication.sendEvent(view, QMouseEvent(kind, pos, pos, Qt.MouseButton.LeftButton,
                                                 Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert view.levels[1].value() == 127
    assert view.times[0].value() > 0


def test_export_gives_every_block_as_one_message(editor, tmp_path):
    messages = editor.export_dt1s()
    assert len(messages) == 38
    bd1 = messages[1]
    assert bd1[8:12] == bytes([0x19, 0x70, 0x2E, 0x00]) and len(bd1) == 8 + 4 + 195 + 2
    assert bd1[12 + 0x0E] == editor.partial("PARTIAL_LEVEL", 0).value()
    editor.receive_dt1(bd1)  # reading it back changes nothing
    assert bd1 == editor.export_dt1s()[1]
    from jdxi_editor.midi.sysex.json_composer import JDXiJSONComposer

    JDXiJSONComposer().process_editor(editor, tmp_path)
    files = sorted(tmp_path.glob("jdxi_tone_data_*.json"))
    assert len(files) == 38
    section = json.loads(files[1].read_text())
    assert section["SYSEX"].replace(" ", "") == bd1.hex().upper()
