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
    assert project.__program__ == "JD-Xi Studio"  # its own settings key (not the original program's)
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


def test_old_settings_and_files_are_copied_once(tmp_path, monkeypatch):
    """Up to 1.0.0a2 the settings and the folder were the original program's: copied once."""
    from PySide6.QtCore import QSettings

    from jdxi_editor import migrate, project

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    old = QSettings(project.LEGACY_ORGANIZATION, project.LEGACY_PROGRAM)
    old.setValue("midi/input_port", "JD-Xi")
    old.sync()
    legacy = tmp_path / f".{project.LEGACY_DATA_NAME}"
    (legacy / "recipes").mkdir(parents=True)
    (legacy / "recipes" / "one.json").write_text("{}")
    (legacy / "logs").mkdir()
    (legacy / "logs" / "old.log").write_text("old")
    try:
        copied = migrate.migrate(home=tmp_path)
        new = QSettings(project.__organization_name__, project.__program__)
        assert new.value("midi/input_port") == "JD-Xi" and copied["settings"] >= 1
        target = tmp_path / f".{project.__data_name__}"
        assert (target / "recipes" / "one.json").exists()
        assert not (target / "logs").exists()  # the old program's logs stay where they are
        new.setValue("midi/input_port", "changed")
        assert migrate.migrate(home=tmp_path) == {"settings": 0, "files": 0}  # only once
        assert new.value("midi/input_port") == "changed"
    finally:
        QSettings.setDefaultFormat(QSettings.Format.NativeFormat)


def test_log_viewer_reads_the_newest_session_log(tmp_path):
    import os
    import time

    from jdxi_editor.ui.widgets.viewer.log import LogViewer

    (tmp_path / "jdxi_studio-11Nov2026-08-00-00.log").write_text("old")
    newest = tmp_path / "jdxi_studio-12Nov2026-20-13-24.log"
    newest.write_text("new")
    later = time.time() + 5
    os.utime(newest, (later, later))
    assert LogViewer.session_log(tmp_path) == newest
    assert LogViewer.session_log(tmp_path / "none").name == "jdxi_studio.log"
