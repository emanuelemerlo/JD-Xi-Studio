"""New Vocal Effect editor: AutoPitch and Vocoder parameters, addresses, receiving."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.ui.v2 import vocal as vc
from jdxi_editor.ui.v2 import widgets as w
from jdxi_editor.ui.v2.framework import SEND_INTERVAL_MS


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


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
    editor = vc.VocalEffectEditor(helper, Mock())
    editor.helper = helper
    editor.resize(1500, 900)
    editor.show()
    QApplication.processEvents()
    helper.sent.clear()
    yield editor
    editor.close()
    editor.deleteLater()
    QApplication.processEvents()


def dt1(address, data):
    body = list(address) + list(data)
    checksum = (128 - sum(body) % 128) % 128
    return bytes([0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x12] + body + [checksum, 0xF7])


def _last(editor):
    deadline = time.monotonic() + SEND_INTERVAL_MS * 2 / 1000
    while time.monotonic() < deadline:
        QApplication.processEvents()
    return editor.helper.sent[-1]


def test_every_parameter_of_the_midi_implementation_is_there(editor):
    vfx = editor.blocks[1]
    assert sorted(s.offset for s in vfx.params) == list(range(0x14))  # 00 00 - 00 13
    assert sorted(s.offset for s in editor.blocks[0].params) == [0x16, 0x1C, 0x1D, 0x1E]
    bound = set()
    for widget in editor.findChildren(QWidget):
        pv = getattr(widget, "pv", None)
        if isinstance(pv, w.ParamValue):
            bound.add(id(pv))
    for spec, pv in editor.values.items():
        assert id(pv) in bound, spec.label
        assert pv.info.description and (pv.info.page or pv.info.source), spec.label


def test_addresses_and_encoding(editor):
    editor.pv("AUTO_PITCH_GENDER").setValue(-4)  # 0 - 20, 10 = 0
    assert _last(editor) == dt1([0x18, 0x00, 0x01, 0x0A], [6])
    editor.pv("AUTO_PITCH_OCTAVE").setValue(1)
    assert _last(editor) == dt1([0x18, 0x00, 0x01, 0x0B], [2])
    editor.pv("VOCAL_EFFECT").setValue(1)  # Program Common 00 16
    assert _last(editor) == dt1([0x18, 0x00, 0x00, 0x16], [1])
    editor.pv("PAN").setValue(20)
    assert _last(editor) == dt1([0x18, 0x00, 0x01, 0x01], [84])


def test_a_dump_is_shown_and_not_sent_back(editor):
    data = [110, 44, 10, 20, 4, 1, 3, 1, 21, 9, 15, 0, 100, 0, 2, 0, 90, 80, 70, 5, 0, 0, 0, 0]
    editor.receive_dt1(dt1([0x18, 0x00, 0x01, 0x00], data))
    assert editor.pv("LEVEL").value() == 110 and editor.pv("PAN").text() == "L20"
    assert editor.pv("OUTPUT_ASSIGN").text() == "DIR" and editor.pv("AUTO_PITCH_TYPE").text() == "ELECTRIC2"
    assert editor.pv("AUTO_PITCH_KEY").text() == "Am" and editor.pv("AUTO_PITCH_NOTE").text() == "A"
    assert editor.pv("AUTO_PITCH_GENDER").value() == 5 and editor.pv("AUTO_PITCH_OCTAVE").value() == -1
    assert editor.pv("AUTO_PITCH_BALANCE").text() == "D0:100W"
    assert editor.pv("VOCODER_ENVELOPE").text() == "LONG" and editor.pv("VOCODER_MIC_HPF").text() == "2500 Hz"
    assert editor.helper.sent == []


def test_only_the_selected_effect_is_active(editor):
    effect = editor.pv("VOCAL_EFFECT")
    effect.setValue(1)  # VOCODER
    assert editor.pv("VOCODER_MIC_SENS").is_enabled() and not editor.pv("AUTO_PITCH_TYPE").is_enabled()
    effect.setValue(2)  # AUTO-PITCH
    editor.pv("AUTO_PITCH_SCALE").setValue(0)
    assert editor.pv("AUTO_PITCH_TYPE").is_enabled() and not editor.pv("AUTO_PITCH_KEY").is_enabled()
    editor.pv("AUTO_PITCH_SCALE").setValue(1)
    assert editor.pv("AUTO_PITCH_KEY").is_enabled()
    keys = editor.findChildren(vc.KeyButtons)[0]
    keys.group.button(14).click()  # Dm
    assert editor.pv("AUTO_PITCH_KEY").text() == "Dm"


def test_export_leaves_program_common_to_the_program_editor(editor):
    messages = editor.export_dt1s()
    assert len(messages) == 1 and messages[0][8:12] == bytes([0x18, 0x00, 0x01, 0x00])
