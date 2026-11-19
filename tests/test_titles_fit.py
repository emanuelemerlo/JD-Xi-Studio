"""No dialog title cut in the title bar (sound-design register item 25), in Italian."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from jdxi_editor.ui.v2 import restyle


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance() or QApplication([])
    restyle.apply_message_box_style(app)
    return app


def test_a_dialog_grows_to_its_title(app):
    dialog = QDialog()
    dialog.setWindowTitle("Modifica il nome della patch del programma corrente")
    dialog.resize(200, 120)
    dialog.show()
    QApplication.processEvents()
    try:
        needed = dialog.fontMetrics().horizontalAdvance(dialog.windowTitle()) + restyle.TITLE_BAR_EXTRA
        assert dialog.width() >= needed
    finally:
        dialog.close()


def test_the_app_dialogs_fit_their_italian_titles(app):
    from jdxi_editor import i18n
    from jdxi_editor.ui.v2.write_wizard import WriteDialog, WriteSession
    from jdxi_editor.ui.windows.patch.name_editor import PatchNameEditor

    previous = i18n.current_language()
    i18n.set_language("it")
    session = WriteSession(lambda done: done(True), dict, lambda m: True, lambda s: True, [])
    for dialog in (PatchNameEditor("x"), WriteDialog(session, "x")):
        dialog.show()
        QApplication.processEvents()
        needed = dialog.fontMetrics().horizontalAdvance(dialog.windowTitle()) + restyle.TITLE_BAR_EXTRA
        assert dialog.width() >= needed, dialog.windowTitle()
        dialog.close()
    assert "Salva" in WriteDialog(session, "x").windowTitle()  # it really was Italian
    i18n.set_language(previous)
