"""
Off-line in the windows (sound-design spec §2, Phase 1).

- every window gets the connection badge; all follow the same state (SD-01, SD-13)
- the commands that need the JD-Xi are off without it, with the reason (SD-01)
- the start-up warning comes once, only while the JD-Xi has not answered
- the JD-Xi arriving after changes made without it: a warning with «Save as
  file», then the histories start again and everything is read (SD-03)
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox, QPushButton

from jdxi_editor.midi.io import connection as conn
from jdxi_editor.ui.v2 import offline


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def connection(app):
    helper = Mock()
    c = conn.Connection(helper, poll_ms=0)
    yield c
    c.deleteLater()


def test_every_window_gets_the_badge_and_follows_the_state(connection):
    main = QMainWindow()
    main.resize(600, 400)
    watcher = offline.install(connection, main)
    dialog = QDialog()
    dialog.resize(500, 300)
    dialog.show()
    QApplication.processEvents()
    try:
        badges = list(watcher.badges)
        assert len(badges) == 2
        assert all(b.isVisibleTo(b.parentWidget()) and "Off-line" in b.text() for b in badges)
        connection.set_state_for_tests(conn.VERIFYING)
        assert all("Verifying" in b.text() for b in badges)
        connection.set_state_for_tests(conn.ONLINE)
        assert not any(b.isVisibleTo(b.parentWidget()) for b in badges)
        connection.set_state_for_tests(conn.UNSTABLE)
        assert all("Unstable" in b.text() for b in badges)
    finally:
        QApplication.instance().removeEventFilter(watcher)
        dialog.close()
        main.close()


def test_commands_that_need_the_jdxi_are_off_with_the_reason(connection):
    action = QAction("Save Patch")
    button = QPushButton("Load")
    button.setToolTip("Load the program")
    offline.require_jdxi(action, connection, "Connect the JD-Xi to save")
    offline.require_jdxi(button, connection)
    assert not action.isEnabled() and "Connect the JD-Xi to save" in action.toolTip()
    assert not button.isEnabled() and button.toolTip().startswith("Load the program\n")
    connection.set_state_for_tests(conn.ONLINE)
    assert action.isEnabled() and button.isEnabled() and button.toolTip() == "Load the program"
    connection.set_state_for_tests(conn.OFFLINE)
    assert not action.isEnabled()


def test_the_start_up_warning_comes_once_and_not_once_the_jdxi_answered(connection):
    window = QMainWindow()
    session = offline.OfflineSession(connection, window, warn_at_start=False)
    session.warn_if_offline()
    assert session.warned and session.last_box is not None
    session.last_box.close()
    first = session.last_box
    session.warn_if_offline()
    assert session.last_box is first  # once per session
    other = offline.OfflineSession(connection, window, warn_at_start=False)
    connection.set_state_for_tests(conn.ONLINE)
    other.warn_if_offline()
    assert not other.warned


def test_changes_made_without_the_jdxi_are_given_up_with_save_as_file(connection, monkeypatch):
    from jdxi_editor.ui.v2 import history

    changed = Mock(modified=True)
    untouched = Mock(modified=False)
    monkeypatch.setattr(history, "histories", lambda *a, **k: [changed, untouched])
    saved, read = [], []
    window = QMainWindow()
    session = offline.OfflineSession(connection, window, save_as_file=lambda: saved.append(1),
                                     read_all=lambda: read.append(1), warn_at_start=False)
    connection.set_state_for_tests(conn.VERIFYING)
    connection.set_state_for_tests(conn.ONLINE)  # the JD-Xi arrives
    box = session.last_box
    assert isinstance(box, QMessageBox) and "given up" in box.text()
    save = next(b for b in box.buttons() if "Save as file" in b.text())
    assert read == []  # nothing read before the answer
    save.click()
    QApplication.processEvents()
    assert saved == [1] and read == [1]
    assert changed.reset.called and untouched.reset.called


def test_without_changes_the_jdxi_is_simply_read(connection, monkeypatch):
    from jdxi_editor.ui.v2 import history

    monkeypatch.setattr(history, "histories", lambda *a, **k: [Mock(modified=False)])
    read = []
    window = QMainWindow()
    session = offline.OfflineSession(connection, window, read_all=lambda: read.append(1),
                                     warn_at_start=False)
    connection.set_state_for_tests(conn.ONLINE)
    assert read == [1] and session.last_box is None
