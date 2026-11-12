"""JD-Xi Studio: its own name and mark in the interface, the origin always shown, settings kept."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from jdxi_editor import project
from jdxi_editor.ui.v2.brand import draw_mark, origin_line


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_names():
    assert project.__display_name__ == "JD-Xi Studio"
    assert project.__program__ == "JD-Xi Editor"  # the settings key and the installer keep it
    assert "Mark Brooks" in project.__origin__ and "JDXI-Editor" in project.__origin__
    assert origin_line() == "based on JDXI-Editor by Mark Brooks"


def test_mark(app):
    mark = draw_mark(64)
    assert mark.width() == 64 and not mark.isNull()


def test_splash_shows_the_name_and_the_origin(app):
    from jdxi_editor.main import setup_splash_screen

    splash, _bar, _status = setup_splash_screen(app)
    try:
        texts = [label.text() for label in splash.findChildren(QLabel)]
        assert "JD-Xi Studio" in texts
        assert origin_line() in texts
        assert any("independent edition of JDXI-Editor by Mark Brooks" in t for t in texts)
    finally:
        splash.close()


def test_about_names_both_authors():
    from PySide6.QtWidgets import QApplication, QLabel

    from jdxi_editor.ui.dialogs.about import UiAboutDialog

    app = QApplication.instance() or QApplication([])  # noqa: F841
    dialog = UiAboutDialog()
    dialog.setup_ui(dialog)
    text = " ".join(label.text() for label in dialog.findChildren(QLabel))
    assert "Emanuele Merlo" in text and "Mark Brooks" in text
    assert "1.0.0" in dialog.version_label.text()
    dialog.close()
