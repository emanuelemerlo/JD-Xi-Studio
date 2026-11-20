"""
The keyboard window and the editor windows, kept together.

The editor windows stay separate windows, but follow the keyboard window:

- minimising either the keyboard or an editor window minimises all of them,
  and restoring the keyboard (from the taskbar too) brings back the editors
  that were open;
- each window is moved on its own (working on two screens, say), and the
  editors window is not owned by the keyboard window, so clicking either
  brings it in front (the keyboard can also be kept always on top);
- closing the keyboard window closes the linked windows.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QDialog, QMenu, QWidget


class WindowLink(QObject):
    """Links the editor windows (top-level children of *keyboard*) to it."""

    def __init__(self, keyboard: QWidget):
        super().__init__(keyboard)
        self.keyboard = keyboard
        self._hidden: list[QWidget] = []
        self._extra: list[QWidget] = []  # windows of their own (not owned by the keyboard)
        self._watched: set[int] = set()
        keyboard.installEventFilter(self)
        self.followers()  # watch the windows already there; new ones on ChildAdded

    # --- which windows follow

    def add(self, window: QWidget) -> None:
        """Link a window that is not the keyboard's child (so the keyboard can come in front of it)."""
        if window not in self._extra:
            self._extra.append(window)
            window.installEventFilter(self)
            self._watched.add(id(window))

    def close_all(self) -> None:
        """Close the linked windows (the keyboard window is closing)."""
        for widget in self._extra + self.followers():
            widget.hide()

    def followers(self) -> list[QWidget]:
        """The linked windows and the keyboard's own windows (not menus or modal dialogs)."""
        out = [w for w in self._extra if w is not None]
        for widget in self.keyboard.findChildren(QWidget):
            if not widget.isWindow() or isinstance(widget, QMenu):
                continue
            if widget.windowType() not in (Qt.WindowType.Window, Qt.WindowType.Dialog):
                continue
            if isinstance(widget, QDialog) and widget.isModal():
                continue
            out.append(widget)
        for widget in out:
            if id(widget) not in self._watched:
                widget.installEventFilter(self)
                self._watched.add(id(widget))
        return out

    def visible_followers(self) -> list[QWidget]:
        return [w for w in self.followers() if w.isVisible() and not w.isMinimized()]

    # --- events

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt name)
        keyboard = getattr(self, "keyboard", None)
        if keyboard is None:  # being torn down
            return False
        kind = event.type()
        if obj is keyboard:
            if kind == QEvent.Type.ChildAdded:
                QTimer.singleShot(0, self, self.followers)
            elif kind == QEvent.Type.WindowStateChange:
                self._keyboard_state_changed()
            elif kind == QEvent.Type.Show and self._hidden and not self.keyboard.isMinimized():
                self._restore_followers()
        elif kind == QEvent.Type.WindowStateChange and isinstance(obj, QWidget) and obj.isMinimized():
            # An editor minimised: everything goes down together
            QTimer.singleShot(0, lambda w=obj: self._follower_minimized(w))
        return False

    def _keyboard_state_changed(self) -> None:
        if self.keyboard.isMinimized():
            self._hidden = self.visible_followers()
            for widget in self._hidden:
                widget.hide()
        else:
            self._restore_followers()

    def _restore_followers(self) -> None:
        hidden, self._hidden = self._hidden, []
        for widget in hidden:
            widget.show()
        if hidden:
            self.keyboard.raise_()

    def _follower_minimized(self, widget: QWidget) -> None:
        widget.setWindowState(widget.windowState() & ~Qt.WindowState.WindowMinimized)
        if self.keyboard.isMinimized():  # already down: comes back with the keyboard
            widget.hide()
            if widget not in self._hidden:
                self._hidden.append(widget)
            return
        self.keyboard.showMinimized()  # hides and remembers the open editors, this one too


class DialogsInFront(QObject):
    """While the keyboard is kept always on top, every dialog comes up above it.

    A dialog of the editors window (or one with no parent) would open behind
    the keyboard window; when it is modal it blocks the keyboard, which then
    seems frozen. Installed on the application by the keyboard window.
    """

    def __init__(self, keyboard: QWidget):
        super().__init__(keyboard)
        self.keyboard = keyboard

    @staticmethod
    def is_dialog(widget) -> bool:
        if not isinstance(widget, QWidget) or not widget.isWindow() or isinstance(widget, QMenu):
            return False
        return isinstance(widget, QDialog) or widget.windowModality() != Qt.WindowModality.NonModal

    def eventFilter(self, watched, event):  # noqa: N802 (Qt name)
        kind = event.type()
        if kind not in (QEvent.Type.Polish, QEvent.Type.Show) or watched is self.keyboard:
            return False
        if not self.is_dialog(watched) or watched.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
            return False
        if kind == QEvent.Type.Polish and not watched.isVisible():
            # before it is first shown: the flag costs nothing yet
            watched.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        elif watched.isModal() or watched.windowModality() != Qt.WindowModality.NonModal:
            # shown again, and modal: changing its flags would hide it, and
            # hiding a dialog ends its exec() as if cancelled (the «Discard
            # the changes» of the close dialog did nothing); raised instead
            QTimer.singleShot(0, watched, lambda w=watched: self._raise(w))
        else:
            QTimer.singleShot(0, watched, lambda w=watched: self._to_front(w))
        return False

    @staticmethod
    def _raise(widget: QWidget) -> None:
        if widget.isVisible():
            widget.raise_()
            widget.activateWindow()

    @staticmethod
    def _to_front(widget: QWidget) -> None:
        if not widget.isVisible():
            return
        geometry = widget.geometry()
        widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        widget.setGeometry(geometry)
        widget.show()  # changing the flags hides the window
        widget.raise_()
        widget.activateWindow()



class PanelFollowsEditors(QObject):
    """When the editors window is shown or closed, the panel lights what it shows (or nothing)."""

    def __init__(self, keyboard):
        super().__init__(keyboard)
        self.keyboard = keyboard

    def eventFilter(self, watched, event):  # noqa: N802 (Qt name)
        if event.type() in (QEvent.Type.Show, QEvent.Type.Hide):
            QTimer.singleShot(0, self.keyboard, self.keyboard.resync_panel)
        return False
