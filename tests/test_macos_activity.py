"""
macOS: a latency-critical activity while playing (no App Nap, no timer
coalescing); elsewhere nothing. On the macOS runner it is really begun and ended.
"""

import sys

import pytest

from jdxi_editor.midi.playback import transport as tp
from jdxi_editor.utils import macos_activity


@pytest.mark.skipif(sys.platform == "darwin", reason="elsewhere than macOS")
def test_nothing_happens_elsewhere():
    assert macos_activity.begin("test") is None
    macos_activity.end(None)


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_on_macos_the_activity_begins_and_ends():
    token = macos_activity.begin("JD-Xi Studio test")
    assert token
    macos_activity.end(token)


def test_playing_holds_it_and_stopping_ends_it(monkeypatch):
    calls = []
    monkeypatch.setattr(tp.sys, "platform", "darwin")
    monkeypatch.setattr(macos_activity, "begin", lambda reason: calls.append(("begin", reason)) or 42)
    monkeypatch.setattr(macos_activity, "end", lambda token: calls.append(("end", token)))
    timers = tp._WindowsTimerResolution()
    timers.set(True)
    timers.set(True)  # once
    timers.set(False)
    assert [c[0] for c in calls] == ["begin", "end"] and calls[1] == ("end", 42)
