"""The SysEx of the hardware check script (the script itself needs a JD-Xi)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "hardware_check", Path(__file__).resolve().parents[1] / "scripts" / "hardware_check.py"
)
hc = importlib.util.module_from_spec(spec)
import sys  # noqa: E402

sys.modules["hardware_check"] = hc  # dataclasses look the module up
spec.loader.exec_module(hc)


def test_rq1_of_digital_1_common():
    # F0 41 10 00 00 00 0E 11 19 01 00 00 00 00 00 40 26 F7 (as the editor sends it)
    assert hc.rq1((0x19, 0x01, 0x00, 0x00), 0x40) == [
        0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x11, 0x19, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x26
    ]


def test_dt1_round_trip():
    data = hc.dt1((0x19, 0x42, 0x00, 0x2A), [100])
    assert hc.parse_dt1(data) == ((0x19, 0x42, 0x00, 0x2A), [100])
    broken = data[:-1] + [(data[-1] + 1) % 128]
    assert hc.parse_dt1(broken) is None


def test_offset_carries_over_7_bits():
    assert hc.offset_address((0x19, 0x01, 0x00, 0x7F), 1) == (0x19, 0x01, 0x01, 0x00)
    assert hc.offset_address((0x18, 0x00, 0x00, 0x00), 0x10) == (0x18, 0x00, 0x00, 0x10)


def test_the_same_checksum_as_the_editor():
    from jdxi_editor.midi.sysex.request.midi_requests import MidiRequests

    request = MidiRequests.DIGITAL1_COMMON
    data = list(request) if not isinstance(request, str) else [int(b, 16) for b in request.split()]
    if data and data[0] == 0xF0:
        data = data[1:-1]
    assert data == hc.rq1((0x19, 0x01, 0x00, 0x00), 0x40)
