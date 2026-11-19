"""
The connection to the JD-Xi, in one place (sound-design spec §1.1, Phase 1).

Every window asks this object whether the JD-Xi can be talked to, instead
of looking at the MIDI ports on its own:

    OFFLINE    no ports open, or the JD-Xi is not there
    DETECTED   both ports open: not yet known to be a JD-Xi
    VERIFYING  Identity Request sent, waiting for the reply
    ONLINE     a Roland JD-Xi answered: reading and writing allowed
    UNSTABLE   ONLINE, but requests went unanswered: writes still go out,
               nothing is shown as verified until a whole reading succeeds

A port merely named "JD-Xi" is not enough: the device has to answer the
Identity Request as a Roland JD-Xi (manufacturer 41h, family 0Eh).
"""

from __future__ import annotations

import weakref
from typing import Optional, Sequence

from PySide6.QtCore import QObject, QTimer, Signal

OFFLINE = "offline"
DETECTED = "detected"
VERIFYING = "verifying"
ONLINE = "online"
UNSTABLE = "unstable"
STATES = (OFFLINE, DETECTED, VERIFYING, ONLINE, UNSTABLE)

ROLAND = 0x41
JDXI_FAMILY = 0x0E
POLL_MS = 1000
VERIFY_RETRY_MS = 3000  # a device that does not answer is asked again this often
UNSTABLE_AFTER = 2  # unanswered requests in a row


def ports_open(helper) -> bool:
    """Both MIDI ports of *helper* open (a reading needs to send and to receive)."""
    if helper is None:
        return False
    for name in ("midi_out", "midi_in"):
        port = getattr(helper, name, None)
        if port is None:
            return False
        is_open = getattr(port, "is_port_open", None)
        try:
            if callable(is_open) and not is_open():
                return False
        except Exception:
            return False
    return True


def is_jdxi_identity(data: Sequence[int]) -> bool:
    """An Identity Reply from a Roland JD-Xi (*data* with or without F0/F7)."""
    data = [int(b) for b in data]
    if data[:1] == [0xF0]:
        data = data[1:]
    # 7E dev 06 02 41 0E 03 ...
    return (len(data) >= 6 and data[0] == 0x7E and data[2] == 0x06 and data[3] == 0x02
            and data[4] == ROLAND and data[5] == JDXI_FAMILY)


class Connection(QObject):
    """The state of the connection to one JD-Xi (one MIDI helper)."""

    changed = Signal(str)  # the new state

    def __init__(self, helper, poll_ms: int = POLL_MS, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._helper = weakref.ref(helper) if helper is not None else (lambda: None)
        self.state = OFFLINE
        self.ever_online = False  # this session: the start-up warning is shown once
        self._unanswered = 0
        self._last_ask = None
        self._timer = QTimer(self)
        self._timer.setInterval(poll_ms)
        self._timer.timeout.connect(self.poll)
        if poll_ms > 0:
            self._timer.start()

    # ------------------------------------------------------------- queries
    @property
    def helper(self):
        return self._helper()

    def can_talk(self) -> bool:
        """The JD-Xi answered and is still there: reading and writing allowed."""
        return self.state in (ONLINE, UNSTABLE)

    def verified(self) -> bool:
        """Results can be shown as verified (not while answers go missing)."""
        return self.state == ONLINE

    # ------------------------------------------------------------- changes
    def _set(self, state: str) -> None:
        if state == self.state:
            return
        self.state = state
        if state == ONLINE:
            self.ever_online = True
        self.changed.emit(state)

    def poll(self) -> None:
        """Follow the ports; ask a newly found device who it is."""
        if not ports_open(self.helper):
            self._unanswered = 0
            self._set(OFFLINE)
            return
        if self.state == OFFLINE:
            self._set(DETECTED)
        if self.state in (DETECTED, VERIFYING):
            self._ask_identity()

    def _ask_identity(self) -> None:
        import time

        now = time.monotonic()
        if self.state == VERIFYING and self._last_ask is not None \
                and (now - self._last_ask) * 1000 < VERIFY_RETRY_MS:
            return
        self._last_ask = now
        helper = self.helper
        send = getattr(helper, "send_identity_request", None)
        if callable(send) and send():
            self._set(VERIFYING)

    def identity_reply(self, data: Sequence[int]) -> None:
        """An Identity Reply came in: a JD-Xi makes the connection ONLINE."""
        if is_jdxi_identity(data) and self.state in (DETECTED, VERIFYING, OFFLINE) \
                and ports_open(self.helper):
            self._unanswered = 0
            self._set(ONLINE)

    def request_unanswered(self) -> None:
        """A request to the JD-Xi got no answer in time."""
        if self.state not in (ONLINE, UNSTABLE):
            return
        self._unanswered += 1
        if self._unanswered >= UNSTABLE_AFTER:
            self._set(UNSTABLE)

    def request_answered(self) -> None:
        self._unanswered = 0

    def reading_complete(self) -> None:
        """A whole reading succeeded: answers arrive again."""
        self._unanswered = 0
        if self.state == UNSTABLE:
            self._set(ONLINE)

    def set_state_for_tests(self, state: str) -> None:
        assert state in STATES
        self._set(state)


def connection_for(helper) -> Optional[Connection]:
    """The Connection of *helper* (made the first time; None without a helper)."""
    if helper is None:
        return None
    existing = getattr(helper, "_jdxi_connection", None)
    if isinstance(existing, Connection):
        return existing
    try:
        connection = Connection(helper)
        helper._jdxi_connection = connection
    except Exception:  # a test double that takes no attributes
        return None
    return connection


def can_talk(helper) -> bool:
    """For the windows: the JD-Xi can be read and written through *helper*."""
    connection = connection_for(helper)
    return connection.can_talk() if connection is not None else False
