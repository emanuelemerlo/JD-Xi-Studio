"""The editor windows follow the keyboard window: minimise and restore together, move on their own."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMenu, QWidget

from jdxi_editor.ui.windows.jdxi.linked import WindowLink


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _spin(app, n=5):
    for _ in range(n):
        app.processEvents()


@pytest.fixture
def windows(app):
    keyboard = QMainWindow()
    keyboard.setGeometry(100, 500, 400, 200)
    editors = QMainWindow(keyboard)  # top-level window owned by the keyboard
    editors.setGeometry(100, 100, 400, 300)
    monitor = QWidget(keyboard, Qt.WindowType.Window)
    monitor.setGeometry(600, 100, 200, 200)
    closed = QWidget(keyboard, Qt.WindowType.Window)
    QMenu(keyboard)
    link = WindowLink(keyboard)
    keyboard.show()
    editors.show()
    monitor.show()
    _spin(app)
    yield link, keyboard, editors, monitor, closed
    for w in (monitor, closed, editors, keyboard):
        w.close()


def test_followers_are_the_keyboard_windows(windows, app):
    link, keyboard, editors, monitor, closed = windows
    modal = QDialog(keyboard)
    modal.setModal(True)
    followers = link.followers()
    assert editors in followers and monitor in followers and closed in followers
    assert modal not in followers and not any(isinstance(w, QMenu) for w in followers)
    assert link.visible_followers() == [w for w in followers if w.isVisible()]
    assert closed not in link.visible_followers()


def test_minimising_the_keyboard_takes_the_open_editors_along(windows, app):
    link, keyboard, editors, monitor, closed = windows
    keyboard.showMinimized()
    _spin(app)
    assert not editors.isVisible() and not monitor.isVisible() and not closed.isVisible()
    keyboard.showNormal()
    _spin(app)
    assert editors.isVisible() and monitor.isVisible()
    assert not closed.isVisible()  # was not open: stays closed


def test_minimising_an_editor_minimises_everything(windows, app):
    link, keyboard, editors, monitor, closed = windows
    editors.showMinimized()
    _spin(app, 10)
    assert keyboard.isMinimized() and not editors.isVisible() and not monitor.isVisible()
    keyboard.showNormal()
    _spin(app)
    assert editors.isVisible() and not editors.isMinimized() and monitor.isVisible()


def test_each_window_moves_on_its_own(windows, app):
    link, keyboard, editors, monitor, closed = windows
    start = editors.pos()
    keyboard.move(keyboard.pos() + QPoint(40, -20))  # to the other screen, say
    _spin(app)
    assert editors.pos() == start


def test_line_up_puts_the_editors_above_the_keyboard(windows, app):
    link, keyboard, editors, monitor, closed = windows
    editors.move(700, 50)
    link.line_up(editors)
    _spin(app)
    assert editors.frameGeometry().bottom() + 1 == keyboard.frameGeometry().top()
    assert editors.frameGeometry().left() == keyboard.frameGeometry().left()


def test_a_window_of_its_own_is_linked_too(app):
    keyboard = QMainWindow()
    editors = QMainWindow()  # not owned: the keyboard can come in front of it
    link = WindowLink(keyboard)
    link.add(editors)
    keyboard.show()
    editors.show()
    _spin(app)
    assert editors.parent() is None and editors in link.followers()
    keyboard.showMinimized()
    _spin(app)
    assert not editors.isVisible()
    keyboard.showNormal()
    _spin(app)
    assert editors.isVisible()
    editors.showMinimized()
    _spin(app, 10)
    assert keyboard.isMinimized() and not editors.isVisible()
    keyboard.showNormal()
    _spin(app)
    link.close_all()
    assert not editors.isVisible()
    keyboard.close()


def test_the_editors_window_is_not_owned_by_the_keyboard(app):
    from jdxi_editor.ui.editors.main import MainEditor

    keyboard = QMainWindow()
    editors = MainEditor(keyboard)
    assert editors.parent() is None and editors.jdxi_main_window is keyboard


def test_dialogs_come_up_above_a_keyboard_kept_on_top(app):
    from PySide6.QtWidgets import QMessageBox

    from jdxi_editor.ui.windows.jdxi.linked import DialogsInFront

    keyboard = QMainWindow()
    keyboard.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    keyboard.show()
    front = DialogsInFront(keyboard)
    app.installEventFilter(front)
    try:
        editors = QMainWindow()  # a window of its own: its dialogs are not owned by the keyboard
        box = QMessageBox(QMessageBox.Icon.Information, "MIDI", "ports", QMessageBox.StandardButton.Ok, editors)
        box.open()  # window-modal, as the MIDI ports dialog
        loose = QDialog()
        loose.show()
        plain = QWidget(None, Qt.WindowType.Window)  # a tool window, not a dialog: left alone
        plain.show()
        _spin(app, 10)
        assert box.isVisible() and box.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
        assert loose.isVisible() and loose.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
        assert not plain.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
        for w in (box, loose, plain, editors):
            w.close()
    finally:
        app.removeEventFilter(front)
        keyboard.close()


def test_keyboard_on_top_installs_the_dialog_filter_and_removes_it(app, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from jdxi_editor.ui.windows.jdxi.instrument import JDXiInstrument

    window = JDXiInstrument()
    try:
        assert not window.on_top_action.isChecked()  # always off at start
        window.on_top_pin.click()
        assert window._dialogs_in_front is not None and window.on_top_action.isChecked()
        assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
        assert window.settings.value("window/keyboard_on_top") is None  # not saved
        window.set_keyboard_on_top(False)
        assert window._dialogs_in_front is None and not window.on_top_pin.isChecked()
    finally:
        window.close()
