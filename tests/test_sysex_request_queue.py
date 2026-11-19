"""
SysEx request pacing and echo suppression (no MIDI hardware).

- the shared queue sends one RQ1 at a time, waits for its reply, and drops
  duplicates
- data received from the JD-Xi is not written back to it
"""

import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication

from jdxi_editor.midi.io.echo_guard import applying_device_data, is_device_echo
from jdxi_editor.midi.io.device import device_for
from jdxi_editor.midi.io.request_queue import SysExRequestQueue

_RQ1_ANALOG = "F0 41 10 00 00 00 0E 11 19 42 00 00 00 00 00 40 65 F7"
_RQ1_DIGITAL1 = "F0 41 10 00 00 00 0E 11 19 01 00 00 00 00 00 40 26 F7"
_DT1_ANALOG = bytes.fromhex("F0 41 10 00 00 00 0E 12 19 42 00 00 01 25 F7")
_DT1_DIGITAL1 = bytes.fromhex("F0 41 10 00 00 00 0E 12 19 01 00 00 01 66 F7")
_CC = bytes([0xB0, 7, 100])

# Digital 1 partial 3 as sent by the JD-Xi: Pitch Env Attack/Decay (07/08) = 10
def _hex(data) -> str:
    return " ".join(f"{b:02X}" for b in data)


def _wait_for(predicate, timeout=1.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class TestRequestQueue(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self.queue = SysExRequestQueue(
            lambda data: self.sent.append(_hex(data)),
            reply_timeout=2.0,
            reply_gap=0.0,
            message_gap=0.0,
        )

    def test_duplicate_requests_are_sent_once(self):
        self.assertEqual(self.queue.submit([_RQ1_ANALOG, _RQ1_ANALOG, _RQ1_ANALOG]), 1)
        self.assertTrue(_wait_for(lambda: len(self.sent) == 1))
        self.queue.submit([_RQ1_ANALOG])  # from another editor, still awaiting reply
        self.queue.notify_reply(_DT1_ANALOG)
        self.assertTrue(self.queue.wait_idle(1.0))
        self.assertEqual(self.sent, [_RQ1_ANALOG])

    def test_a_request_after_the_reply_is_sent_again(self):
        """A read starting just after the reply (the queue still pausing) gets its own reply."""
        self.queue._reply_gap = 0.3
        self.queue.submit([_RQ1_ANALOG])
        self.assertTrue(_wait_for(lambda: len(self.sent) == 1))
        self.queue.notify_reply(_DT1_ANALOG)  # answered: the queue pauses 0.3 s
        self.assertEqual(self.queue.submit([_RQ1_ANALOG]), 1)
        self.assertTrue(_wait_for(lambda: len(self.sent) == 2))
        self.queue.notify_reply(_DT1_ANALOG)
        self.assertTrue(self.queue.wait_idle(2.0))

    def test_next_request_waits_for_the_reply(self):
        self.queue.submit([_RQ1_ANALOG, _RQ1_DIGITAL1])
        self.assertTrue(_wait_for(lambda: len(self.sent) == 1))
        time.sleep(0.05)
        self.assertEqual(len(self.sent), 1)  # JD-Xi still answering the first
        self.queue.notify_reply(_DT1_DIGITAL1)  # reply for another address
        time.sleep(0.05)
        self.assertEqual(len(self.sent), 1)
        self.queue.notify_reply(_DT1_ANALOG)
        self.assertTrue(_wait_for(lambda: len(self.sent) == 2))
        self.assertEqual(self.sent, [_RQ1_ANALOG, _RQ1_DIGITAL1])

    def test_request_can_be_sent_again_after_its_reply(self):
        self.queue.submit([_RQ1_ANALOG])
        self.assertTrue(_wait_for(lambda: len(self.sent) == 1))
        self.queue.notify_reply(_DT1_ANALOG)
        self.assertTrue(self.queue.wait_idle(1.0))
        self.queue.submit([_RQ1_ANALOG])
        self.assertTrue(_wait_for(lambda: len(self.sent) == 2))

    def test_unanswered_request_times_out(self):
        queue = SysExRequestQueue(
            lambda data: self.sent.append(_hex(data)), reply_timeout=0.05, reply_gap=0.0
        )
        queue.submit([_RQ1_ANALOG, _RQ1_DIGITAL1])
        self.assertTrue(_wait_for(lambda: len(self.sent) == 2))

    def test_other_messages_are_sent_in_order_without_deduplication(self):
        self.queue.submit([_CC, _CC, _DT1_ANALOG])
        self.assertTrue(self.queue.wait_idle(1.0))
        self.assertEqual(self.sent, [_hex(_CC), _hex(_CC), _hex(_DT1_ANALOG)])

    def test_clear_drops_unsent_requests(self):
        self.queue.submit([_RQ1_ANALOG, _CC, _DT1_ANALOG])
        self.queue.clear()
        self.assertTrue(self.queue.wait_idle(1.0))
        self.assertLessEqual(len(self.sent), 1)  # at most the one already sent
        self.assertEqual(self.queue.submit([_RQ1_ANALOG]), 1)  # can queue it again

    def test_helper_shares_one_queue(self):
        helper = Mock(spec=["send_raw_message"])
        self.assertIs(device_for(helper).requests, device_for(helper).requests)


class TestEchoGuard(unittest.TestCase):
    def test_only_dt1_inside_the_scope_is_an_echo(self):
        self.assertFalse(is_device_echo(_DT1_ANALOG))
        with applying_device_data():
            self.assertTrue(is_device_echo(_DT1_ANALOG))
            self.assertFalse(is_device_echo(bytes.fromhex(_RQ1_ANALOG)))
            self.assertFalse(is_device_echo(_CC))
        self.assertFalse(is_device_echo(_DT1_ANALOG))

    def test_scope_is_per_thread(self):
        results = []
        with applying_device_data():
            worker = threading.Thread(target=lambda: results.append(is_device_echo(_DT1_ANALOG)))
            worker.start()
            worker.join()
        self.assertEqual(results, [False])


class TestDeviceDataNotWrittenBack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from jdxi_editor.midi.io.helper import MidiIOHelper

        cls.helper = MidiIOHelper()

    def setUp(self):
        self.out = Mock()
        self.out.is_port_open = Mock(return_value=True)
        self._saved_out = self.helper.midi_out
        self.helper.midi_out = self.out

    def tearDown(self):
        self.helper.midi_out = self._saved_out

    def test_dt1_sent_by_a_sysex_listener_is_dropped(self):
        def listener(_payload):
            self.helper.send_raw_message(_DT1_ANALOG)

        self.helper.midi_sysex_json.connect(listener)
        try:
            self.helper._device_sysex_json.emit(json.dumps({"ADDRESS": "12194200"}))
            self.app.processEvents()
        finally:
            self.helper.midi_sysex_json.disconnect(listener)
        # (the shared connection may ask the JD-Xi who it is meanwhile: not data written back)
        written = [c for c in self.out.send_message.call_args_list  # DT1 only (requests are not writes)
                   if len(c.args[0]) > 7 and list(c.args[0])[:2] == [0xF0, 0x41] and c.args[0][7] == 0x12]
        self.assertEqual(written, [])

    def test_user_edits_are_still_sent(self):
        self.assertTrue(self.helper.send_raw_message(_DT1_ANALOG))
        self.out.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
