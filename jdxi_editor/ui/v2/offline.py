"""
Off-line: how the windows show and use the shared connection (sound-design
spec §2, Phase 1).

- a badge «Off-line» (or «Verifying the JD-Xi…», «Unstable connection») in
  every window: in the main window's status bar, in the corner of the others
- a warning when the session starts without a JD-Xi (once per session)
- the commands that need the JD-Xi are off while it is not there, with the
  reason in their tooltip (require_jdxi)
- when the JD-Xi arrives after changes made without it: they are given up
  (the JD-Xi's settings are read), with «Save as file» to keep them first
"""

from __future__ import annotations

import weakref
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.io import connection as conn

BADGE_NAME = "jdxiConnectionBadge"
OWN_INDICATOR = "jdxiOwnConnectionIndicator"  # a window property: no badge added to it
WARNING_DELAY_MS = 4000  # the JD-Xi gets this long to answer before the start-up warning

_STYLES = {
    conn.OFFLINE: ("#3a1f1f", "#ff8a7a"),
    conn.DETECTED: ("#2f2a1a", "#f2c94c"),
    conn.VERIFYING: ("#2f2a1a", "#f2c94c"),
    conn.UNSTABLE: ("#3a2a14", "#f2994a"),
}


def badge_text(state: str) -> str:
    return {
        conn.OFFLINE: tr("Off-line"),
        conn.DETECTED: tr("Verifying the JD-Xi…"),
        conn.VERIFYING: tr("Verifying the JD-Xi…"),
        conn.UNSTABLE: tr("Unstable connection"),
    }.get(state, "")


def badge_tooltip(state: str) -> str:
    return {
        conn.OFFLINE: tr("The JD-Xi is not connected: you can try everything, but nothing is saved or sent"),
        conn.DETECTED: tr("A MIDI device is connected: checking that it is a JD-Xi"),
        conn.VERIFYING: tr("A MIDI device is connected: checking that it is a JD-Xi"),
        conn.UNSTABLE: tr("The JD-Xi does not answer every request: results are not shown as verified "
                          "until a whole reading succeeds"),
    }.get(state, "")


class ConnectionBadge(QLabel):
    """A small pill with the connection's state; hidden while ONLINE."""

    def __init__(self, parent: Optional[QWidget] = None, floating: bool = False):
        super().__init__(parent)
        self.setObjectName(BADGE_NAME)
        self.floating = floating
        if floating:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.show_state(conn.OFFLINE)

    def show_state(self, state: str) -> None:
        text = badge_text(state)
        self.setVisible(bool(text))
        if not text:
            return
        background, colour = _STYLES.get(state, _STYLES[conn.OFFLINE])
        self.setText(f"● {text}")
        self.setToolTip(badge_tooltip(state))
        self.setStyleSheet(
            f"QLabel#{BADGE_NAME} {{ background: {background}; color: {colour};"
            f" border: 1px solid {colour}; border-radius: 9px; padding: 1px 9px;"
            f" font-size: 11px; font-weight: 600; }}")
        self.adjustSize()
        if self.floating:
            self.place()
            self.raise_()

    def place(self) -> None:
        window = self.parentWidget()
        if window is not None:
            self.move(window.width() - self.width() - 10, window.height() - self.height() - 8)


class _WindowWatcher(QObject):
    """Puts a badge on every window as it is shown, and keeps it in its corner."""

    def __init__(self, connection: conn.Connection, main: Optional[QWidget]):
        super().__init__(connection)
        self.connection = connection
        self.main = weakref.ref(main) if main is not None else (lambda: None)
        self.badges: "weakref.WeakSet[ConnectionBadge]" = weakref.WeakSet()
        connection.changed.connect(self._show)

    def add(self, badge: "ConnectionBadge") -> "ConnectionBadge":
        """A badge a window placed itself: it follows the state too."""
        badge.show_state(self.connection.state)
        self.badges.add(badge)
        return badge

    def _show(self, state: str) -> None:
        for badge in list(self.badges):
            try:
                badge.show_state(state)
            except RuntimeError:  # its window is gone
                pass

    @staticmethod
    def _wants_badge(widget: QWidget) -> bool:
        if not widget.isWindow() or widget.objectName() == BADGE_NAME:
            return False
        if isinstance(widget, QDialog):  # short-lived, and the badge would cover their buttons
            return False
        if widget.property(OWN_INDICATOR):  # it shows the connection itself
            return False
        if widget.windowType() in (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.SplashScreen):
            return False
        if isinstance(widget, (QMessageBox,)) or widget.inherits("QMenu"):
            return False
        if widget.width() < 300 or widget.height() < 200:  # toasts, small helpers
            return False
        return isinstance(widget, (QMainWindow, QDialog)) or widget.inherits("QWidget")

    def attach(self, window: QWidget) -> Optional[ConnectionBadge]:
        existing = window.findChild(ConnectionBadge, BADGE_NAME, Qt.FindChildOption.FindDirectChildrenOnly)
        status = window.statusBar() if isinstance(window, QMainWindow) else None
        if existing is not None or (status is not None and status.findChild(ConnectionBadge)):
            return existing
        if status is not None:
            badge = ConnectionBadge(status)
            status.addPermanentWidget(badge)
        else:
            badge = ConnectionBadge(window, floating=True)
        badge.show_state(self.connection.state)
        self.badges.add(badge)
        return badge

    def eventFilter(self, watched, event):  # noqa: N802 (Qt)
        kind = event.type()
        if kind == QEvent.Type.Show and isinstance(watched, QWidget) and self._wants_badge(watched):
            self.attach(watched)
        elif kind == QEvent.Type.Resize and isinstance(watched, QWidget) and watched.isWindow():
            badge = watched.findChild(ConnectionBadge, BADGE_NAME, Qt.FindChildOption.FindDirectChildrenOnly)
            if badge is not None and badge.floating:
                badge.place()
        return False


# ------------------------------------------------------- commands that need it
def require_jdxi(target, connection: conn.Connection, why: str = "") -> None:
    """*target* (a widget or an action) is on only while the JD-Xi can be talked to;
    off, its tooltip says why."""
    ref = weakref.ref(target)
    base_tip = target.toolTip() or ""
    reason = why or tr("Connect the JD-Xi: this needs it")

    def follow(_state: str = "") -> None:
        item = ref()
        if item is None:
            return
        try:
            on = connection.can_talk()
            item.setEnabled(on)
            tip = base_tip if on else (f"{base_tip}\n{reason}" if base_tip else reason)
            item.setToolTip(tip)
            if isinstance(item, QAction):
                item.setStatusTip(tip)
        except RuntimeError:  # deleted
            pass

    connection.changed.connect(follow)
    follow()


# ------------------------------------------------------------------ outcomes
def outcome_text(what: str, done: int, failed: int) -> tuple[str, bool]:
    """What an operation that sends to the JD-Xi achieved: complete, partial or failed.
    Returns (text, problem)."""
    if failed == 0 and done > 0:
        return tr("{what}: complete ({n} sent)").format(what=what, n=done), False
    if done == 0:
        return tr("{what}: failed, nothing reached the JD-Xi").format(what=what), True
    return tr("{what}: partial, {n} of {total} sent: the JD-Xi does not hold everything shown").format(
        what=what, n=done, total=done + failed), True


# ------------------------------------------------------------------ messages
class OfflineSession(QObject):
    """The start-up warning and the arrival of the JD-Xi, for the main window."""

    def __init__(self, connection: conn.Connection, window: QWidget,
                 save_as_file: Optional[Callable[[], None]] = None,
                 read_all: Optional[Callable[[], None]] = None,
                 warn_at_start: bool = True):
        super().__init__(window)
        self.connection = connection
        self.window = weakref.ref(window)
        self.save_as_file = save_as_file
        self.read_all = read_all
        self.warned = False
        self.last_box: Optional[QMessageBox] = None
        self._previous = connection.state
        self._was_online = connection.can_talk()  # online once: a later arrival is a reconnection
        import time

        self._started = time.monotonic()
        self.safety_net = None
        connection.changed.connect(self._changed)
        if warn_at_start:
            QTimer.singleShot(WARNING_DELAY_MS, self.warn_if_offline)

    def warn_if_offline(self) -> None:
        """Once per session, if the JD-Xi has not answered: what Off-line means."""
        if self.warned or self.connection.ever_online or self.connection.can_talk():
            return
        if QApplication.activeModalWidget() is not None:  # e.g. the MIDI configuration: later
            QTimer.singleShot(2000, self.warn_if_offline)
            return
        self.warned = True
        box = QMessageBox(
            QMessageBox.Icon.Information,
            tr("JD-Xi not connected"),
            tr("The JD-Xi is not connected: you can try everything, but nothing is saved or sent.\n\n"
               "When you connect it, its settings are read and shown in place of the changes made "
               "without it (you can save those as a file first)."),
            QMessageBox.StandardButton.Ok,
            self.window(),
        )
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.last_box = box
        box.open()

    def _changed(self, state: str) -> None:
        previous, self._previous = self._previous, state
        if state == conn.ONLINE and previous in (conn.OFFLINE, conn.DETECTED, conn.VERIFYING):
            if self._was_online:
                self.jdxi_back()
            else:
                self.jdxi_arrived()
        if state == conn.ONLINE:
            self._was_online = True

    def jdxi_back(self) -> None:
        """After a disconnection: read everything and compare (the safety net)."""
        from jdxi_editor.midi.io.synth_memory import build_dt1
        from jdxi_editor.midi.io.synth_state import state_of
        from jdxi_editor.ui.v2 import history
        from jdxi_editor.ui.v2.safety_net import SafetyNet

        helper = self.connection.helper
        state = state_of(helper)
        if helper is None or state is None:
            return

        def read(done) -> None:
            from jdxi_editor.midi.sysex.request.read_session import patch_section_requests, start_read_session

            requests = [rq for _label, rq in patch_section_requests()]
            start_read_session(helper, requests, on_finished=lambda result: done(bool(result.complete)),
                               parent=self)

        def send(key: str, data: bytes) -> bool:
            return bool(helper.send_raw_message(list(build_dt1(bytes.fromhex(key), list(data)))))

        def notify(text: str, problem: bool) -> None:
            window = self.window()
            status = window.statusBar() if hasattr(window, "statusBar") else None
            if status is not None:
                status.showMessage(text, 0 if problem else 10000)

        self.safety_net = SafetyNet(read, state.snapshot, send,
                                    lambda: any(h.modified for h in history.histories()),
                                    parent=self.window(), notify=notify)
        self.safety_net.start()

    def jdxi_arrived(self) -> None:
        """Changes made without the JD-Xi are given up for what it holds."""
        from jdxi_editor.ui.v2 import history

        changed = [h for h in history.histories() if h.modified]
        if changed:
            box = QMessageBox(
                QMessageBox.Icon.Information,
                tr("JD-Xi connected"),
                tr("The changes made without the JD-Xi are given up: the settings read from the "
                   "JD-Xi are shown.\n\nTo keep them, save them as a file now: you can load it and "
                   "send it to the JD-Xi later."),
                QMessageBox.StandardButton.Ok,
                self.window(),
            )
            save: Optional[QPushButton] = None
            if self.save_as_file is not None:
                save = box.addButton(tr("Save as file…"), QMessageBox.ButtonRole.ActionRole)
            box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.last_box = box

            def done(_result: int) -> None:
                if save is not None and box.clickedButton() is save and self.save_as_file is not None:
                    self.save_as_file()
                self._read_and_reset()

            box.finished.connect(done)
            box.open()
        else:
            self._read_and_reset()

    STARTUP_SECONDS = 6.0  # a JD-Xi there from the start: the editors read it as they open

    def _read_and_reset(self) -> None:
        import time

        from jdxi_editor.ui.v2 import history

        for h in history.histories():
            h.reset()  # what the JD-Xi holds is the new starting point
        if self.read_all is not None and time.monotonic() - self._started > self.STARTUP_SECONDS:
            self.read_all()


def install(connection: conn.Connection, main: Optional[QWidget] = None) -> _WindowWatcher:
    """Badges on the main window and every window shown from now on."""
    watcher = _WindowWatcher(connection, main)
    app = QApplication.instance()
    if app is not None:
        app.installEventFilter(watcher)
    if main is not None and not main.property(OWN_INDICATOR):
        watcher.attach(main)
    for widget in QApplication.topLevelWidgets():
        if widget.isVisible() and watcher._wants_badge(widget):
            watcher.attach(widget)
    return watcher
