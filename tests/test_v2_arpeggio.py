"""New Arpeggio editor: every Program Controller parameter, addresses, receiving, timing view."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget

from jdxi_editor.ui.v2 import arpeggio as ar
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
    editor = ar.ArpeggioEditor(helper, Mock())
    editor.helper = helper
    editor.resize(1400, 900)
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


def test_every_parameter_is_there_with_a_control(editor):
    ctrl = editor.blocks[0]
    assert sorted(s.offset for s in ctrl.params) == [0x01, 0x02, 0x03, 0x05, 0x06, 0x07, 0x09, 0x0A]
    assert [b.address.lmb for b in editor.blocks[1:5]] == [0x30, 0x31, 0x32, 0x33]
    bound = {id(getattr(x, "pv")) for x in editor.findChildren(QWidget) if isinstance(getattr(x, "pv", None), w.ParamValue)}
    for spec, pv in editor.values.items():
        assert id(pv) in bound, spec.label
        assert pv.info.description and (pv.info.page or pv.info.source), spec.label


def test_addresses_and_encoding(editor):
    editor.pv("ARPEGGIO_OCTAVE_RANGE").setValue(-2)
    assert _last(editor) == dt1([0x18, 0x00, 0x40, 0x07], [62])
    editor.pv("ARPEGGIO_STYLE").setValue(12)
    assert _last(editor) == dt1([0x18, 0x00, 0x40, 0x05], [12])
    editor.pv("ZONE_ARPEGGIO_SWITCH", "ZONE_3").setValue(1)  # drums
    assert _last(editor) == dt1([0x18, 0x00, 0x33, 0x03], [1])


def test_a_dump_is_shown_and_not_sent_back(editor):
    editor.receive_dt1(dt1([0x18, 0x00, 0x40, 0x00], [0, 7, 9, 1, 0, 40, 11, 66, 0, 70, 0, 0]))
    assert editor.pv("ARPEGGIO_GRID").text() == "1/16H" and editor.pv("ARPEGGIO_DURATION").text() == "Full"
    assert editor.pv("ARPEGGIO_SWITCH").text() == "ON" and editor.pv("ARPEGGIO_STYLE").text() == "041: " + ar.ARPEGGIO_STYLE[40][5:]
    assert editor.pv("ARPEGGIO_MOTIF").text() == "Phrase" and editor.pv("ARPEGGIO_OCTAVE_RANGE").value() == 2
    assert editor.pv("ARPEGGIO_ACCENT_RATE").value() == 70 and editor.pv("ARPEGGIO_VELOCITY").text() == "REAL"
    assert "phrase" in editor.motif_text.text()
    assert editor.helper.sent == []


def test_timing_view_follows_grid_and_duration(editor):
    view = editor.findChildren(ar.TimingView)[0]
    editor.pv("ARPEGGIO_GRID").setValue(5)  # 1/16
    editor.pv("ARPEGGIO_DURATION").setValue(2)  # 50 %
    notes = view.notes()
    assert len(notes) == 8 and abs(notes[0][1] - 0.125) < 1e-9
    editor.pv("ARPEGGIO_GRID").setValue(4)  # 1/12: triplets
    assert len(view.notes()) == 6
    editor.pv("ARPEGGIO_GRID").setValue(3)  # 1/8H: the off-beat comes late
    assert view.notes()[1][0] > 0.5
    editor.pv("ARPEGGIO_ACCENT_RATE").setValue(0)
    assert len({round(n[2], 3) for n in view.notes()}) == 1  # no accent: all the same


def test_export_gives_only_the_controller_block(editor):
    messages = editor.export_dt1s()
    assert len(messages) == 1 and messages[0][8:12] == bytes([0x18, 0x00, 0x40, 0x00])
