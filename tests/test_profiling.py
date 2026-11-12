"""main() is profiled only on request, and never crashes when another profiler is active."""

from __future__ import annotations

import cProfile

from jdxi_editor.utils.profiling_decorator import profiling_decorator


@profiling_decorator()
def _work(x):
    return x * 2


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("JDXI_PROFILE", raising=False)
    outer = cProfile.Profile()
    outer.enable()  # as a debugger or "python -m cProfile" would be
    try:
        assert _work(21) == 42
    finally:
        outer.disable()


def test_on_request_and_another_profiler_active(monkeypatch, capsys):
    monkeypatch.setenv("JDXI_PROFILE", "1")
    assert _work(2) == 4
    assert "Profiling results for _work" in capsys.readouterr().out
    outer = cProfile.Profile()
    outer.enable()
    try:
        assert _work(3) == 6  # skipped, not crashed
    finally:
        outer.disable()
