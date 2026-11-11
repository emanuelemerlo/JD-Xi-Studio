"""
The keyboard window and the editor windows, kept together.

The editor windows stay separate windows, but follow the keyboard window:

- minimising either the keyboard or an editor window minimises all of them,
  and restoring the keyboard (from the taskbar too) brings back the editors
  that were open;
- dragging the keyboard window moves the open editor windows with it (can be
  switched off from the Window menu);
- line_up() places the editors right above the keyboard (or below it when
  there is no room), aligned on its left edge.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import QDialog, QMenu, QWidget


class WindowLink(QObject):
    """Links the editor windows (top-level children of *keyboard*) to it."""

    def __init__(self, keyboard: QWidget):
        super().__init__(keyboard)
        self.keyboard = keyboard
        self.move_together = True
        self._last_pos: Optional[QPoint] = None
        self._hidden: list[QWidget] = []
        self._watched: set[int] = set()
        keyboard.installEventFilter(self)
        self.followers()  # watch the windows already there; new ones on ChildAdded

    # --- which windows follow

    def followers(self) -> list[QWidget]:
        """The keyboard's own windows: editors, the editor tabs, monitors (not menus or modal dialogs)."""
        out = []
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
            elif kind == QEvent.Type.Move:
                self._keyboard_moved()
            elif kind == QEvent.Type.Show and self._hidden and not self.keyboard.isMinimized():
                self._restore_followers()
        elif kind == QEvent.Type.WindowStateChange and isinstance(obj, QWidget) and obj.isMinimized():
            # An editor minimised: everything goes down together
            QTimer.singleShot(0, lambda w=obj: self._follower_minimized(w))
        return False

    def _keyboard_state_changed(self) -> None:
        self._last_pos = None
        if self.keyboard.isMinimized():
            self._hidden = self.visible_followers()
            for widget in self._hidden:
                widget.hide()
        else:
            self._restore_followers()
            QTimer.singleShot(0, self._remember_pos)

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

    def _remember_pos(self) -> None:
        if self._movable():
            self._last_pos = self.keyboard.pos()

    def _movable(self) -> bool:
        state = self.keyboard.windowState()
        return self.keyboard.isVisible() and not (
            state & (Qt.WindowState.WindowMinimized | Qt.WindowState.WindowMaximized | Qt.WindowState.WindowFullScreen)
        )

    def _keyboard_moved(self) -> None:
        if not self._movable():
            self._last_pos = None
            return
        pos = self.keyboard.pos()
        last, self._last_pos = self._last_pos, pos
        if last is None or not self.move_together:
            return
        delta = pos - last
        if delta.isNull():
            return
        for widget in self.visible_followers():
            if widget.isMaximized() or widget.isFullScreen():
                continue
            widget.move(widget.pos() + delta)

    # --- placing

    def line_up(self, editor: QWidget) -> None:
        """Put *editor* right above the keyboard window (below it when there is no room)."""
        if self.keyboard.isMinimized() or self.keyboard.isMaximized():
            return
        frame = self.keyboard.frameGeometry()
        screen = (self.keyboard.screen() or editor.screen()).availableGeometry()
        editor_frame = editor.frameGeometry()
        height = editor_frame.height()
        x = max(screen.left(), min(frame.left(), screen.right() - editor_frame.width()))
        if frame.top() - height >= screen.top():
            y = frame.top() - height
        elif frame.bottom() + height <= screen.bottom():
            y = frame.bottom() + 1
        else:  # no room either side: the editor above, the keyboard below
            y = screen.top()
            self.keyboard.move(frame.left(), min(screen.bottom() - frame.height(), y + height))
            frame = self.keyboard.frameGeometry()
        editor.move(x, y)
        self._last_pos = self.keyboard.pos() if self._movable() else None
