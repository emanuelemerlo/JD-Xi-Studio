"""
Minimise, maximise and close for the frameless instrument window.

The instrument window draws its own frame (it looks like the JD-Xi panel), so
it has no title bar. WindowButtons sits at the right end of its menu bar, in
the panel's colours; the empty part of the menu bar moves the window when
dragged and maximises/restores it on double-click, as a title bar would.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, QEvent, QObject, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QMenuBar, QToolButton, QWidget

from jdxi_editor.i18n import tr

MENU_BAR_STYLE = (
    "QMenuBar { background: #111111; color: #e6e6e6; border-bottom: 1px solid #2a2a2a; }"
    "QMenuBar::item { background: transparent; }"
    "QMenuBar::item:selected { background: #333333; }"
    "QMenu { background: #111111; color: #e6e6e6; border: 1px solid #333333; }"
    "QMenu::item:selected { background: #333333; }"
)


class _WindowButton(QToolButton):
    """A flat button with its symbol drawn, so it looks the same everywhere."""

    def __init__(self, kind: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.maximized = False
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        # no taller than the menu bar: the panel's proportions stay as on the JD-Xi
        self.setFixedSize(QSize(40, 20))
        self.setCursor(Qt.CursorShape.ArrowCursor)
        hover = "#e0443a" if kind == "close" else "#333333"
        self.setStyleSheet(
            "QToolButton { background: transparent; border: 0; }"
            f"QToolButton:hover {{ background: {hover}; }}"
            f"QToolButton:pressed {{ background: {'#b8352d' if kind == 'close' else '#444444'}; }}"
            "QToolButton:checked { background: #2a1410; }"
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#e6e6e6"), 1.3))
        c = QPointF(self.width() / 2, self.height() / 2)
        s = 5.0
        if self.kind == "pin":  # a drawing pin, red while the window is kept on top
            colour = QColor("#ff3b1f") if self.isChecked() else QColor("#9a9da4")
            p.translate(c)
            p.rotate(45)
            p.setPen(QPen(colour, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(0, 2), QPointF(0, 7))  # the needle
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(colour)
            p.drawRoundedRect(QRectF(-2.6, -7, 5.2, 7), 1.2, 1.2)  # the body
            p.drawRoundedRect(QRectF(-5, -0.5, 10, 2.5), 1, 1)  # the collar
        elif self.kind == "minimize":
            p.drawLine(QPointF(c.x() - s, c.y()), QPointF(c.x() + s, c.y()))
        elif self.kind == "maximize":
            if self.maximized:  # two overlapping squares: restore
                p.drawRect(QRectF(c.x() - s, c.y() - s + 2, 2 * s - 2, 2 * s - 2))
                p.drawPolyline([QPointF(c.x() - s + 2, c.y() - s), QPointF(c.x() + s, c.y() - s), QPointF(c.x() + s, c.y() + s - 2)])
            else:
                p.drawRect(QRectF(c.x() - s, c.y() - s, 2 * s, 2 * s))
        else:
            p.drawLine(QPointF(c.x() - s, c.y() - s), QPointF(c.x() + s, c.y() + s))
            p.drawLine(QPointF(c.x() - s, c.y() + s), QPointF(c.x() + s, c.y() - s))
        p.end()


class WindowButtons(QWidget):
    """Minimise, maximise/restore and close, for window()."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # keep the window in front of the others: not saved, off at every start
        self.pin_button = _WindowButton(
            "pin", tr("Keep the keyboard in front of the other windows (until the next start)")
        )
        self.pin_button.setCheckable(True)
        layout.addWidget(self.pin_button)
        self.minimize_button = _WindowButton("minimize", tr("Minimize"))
        self.maximize_button = _WindowButton("maximize", tr("Maximize"))
        self.close_button = _WindowButton("close", tr("Close"))
        self.minimize_button.clicked.connect(lambda: self.window().showMinimized())
        self.maximize_button.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(lambda: self.window().close())
        for button in (self.minimize_button, self.maximize_button, self.close_button):
            layout.addWidget(button)

    def toggle_maximized(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
            fit = getattr(window, "fit_to_instrument", None)
            if fit is not None:  # back to the instrument's size, not the old maximised one
                QTimer.singleShot(0, fit)
        else:
            window.showMaximized()

    def sync(self) -> None:
        """Show restore or maximise to match the window's state."""
        maximized = self.window().isMaximized()
        self.maximize_button.maximized = maximized
        self.maximize_button.setToolTip(tr("Restore") if maximized else tr("Maximize"))
        self.maximize_button.update()


class _MenuBarAsTitleBar(QObject):
    """Drag the empty part of the menu bar to move the window; double-click it to maximise."""

    def __init__(self, menubar: QMenuBar, buttons: WindowButtons):
        super().__init__(menubar)
        self.menubar, self.buttons = menubar, buttons

    def _on_empty_part(self, event) -> bool:
        return self.menubar.actionAt(event.position().toPoint()) is None

    def eventFilter(self, obj, event) -> bool:
        t = event.type()
        if t == QEvent.Type.MouseButtonDblClick and self._on_empty_part(event):
            self.buttons.toggle_maximized()
            return True
        if (
            t == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
            and self._on_empty_part(event)
        ):
            handle = self.menubar.window().windowHandle()
            if handle is not None and handle.startSystemMove():
                return True
        return False


class _WatchState(QObject):
    def __init__(self, window, buttons: WindowButtons):
        super().__init__(window)
        self.buttons = buttons

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.WindowStateChange:
            self.buttons.sync()
        return False


def add_window_buttons(window) -> WindowButtons:
    """Give a frameless QMainWindow minimise/maximise/close and a draggable menu bar."""
    menubar = window.menuBar()
    menubar.setStyleSheet(MENU_BAR_STYLE)
    buttons = WindowButtons(menubar)
    menubar.setCornerWidget(buttons, Qt.Corner.TopRightCorner)
    menubar.installEventFilter(_MenuBarAsTitleBar(menubar, buttons))
    window.installEventFilter(_WatchState(window, buttons))
    buttons.sync()
    return buttons
