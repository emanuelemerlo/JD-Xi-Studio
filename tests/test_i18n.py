"""Interface language: catalogue complete, Italian loaded, choice in Preferences."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from building import i18n as catalogue
from jdxi_editor import i18n


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def italian():
    i18n.set_language("it")
    yield
    i18n.set_language("en")  # the other tests check English texts


@pytest.fixture
def user_settings(tmp_path):
    """Preferences in a temporary file, not the real user settings."""
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


def test_every_string_is_translated_and_the_qm_is_current():
    problems = catalogue.check()
    assert problems == [], "\n".join(problems[:20])


def test_tr_finds_strings_in_the_sources():
    found = catalogue.extract()
    assert ("&Edit", None) in found
    assert ("Interface language:", None) in found
    assert len(found) > 300


def test_italian_texts(italian):
    assert i18n.current_language() == "it"
    assert i18n.tr("&Edit") == "&Modifica"
    assert i18n.tr("MIDI connection") == "Collegamento MIDI"
    text = i18n.tr("Loading {partial_name} ({count} of {total})")
    assert text.format(partial_name="SD1", count=6, total=37) == "Caricamento di SD1 (6 di 37)"
    # anything without a translation stays in English
    assert i18n.tr("Cutoff") == "Cutoff"


def test_english_is_the_source_language():
    i18n.set_language("en")
    assert i18n.tr("&Edit") == "&Edit"


@pytest.mark.parametrize(
    "setting, system, expected",
    [
        ("system", "it_IT", "it"),
        ("system", "it_CH", "it"),
        ("system", "de_DE", "en"),  # no German catalogue yet
        ("it", "en_US", "it"),
        ("en", "it_IT", "en"),
        ("xx", "it_IT", "en"),
        (None, "it_IT", "it"),
    ],
)
def test_language_resolution(setting, system, expected):
    assert i18n.resolve_language(setting, system) == expected


def test_qt_dialogs_are_translated_too(app, italian):
    installed = i18n.install_qt_translators(app)
    try:
        if not installed:
            pytest.skip("Qt's Italian catalogue is not installed")
        assert app.translate("QPlatformTheme", "Cancel") == "Annulla"
    finally:
        for translator in installed:
            app.removeTranslator(translator)


def test_preferences_store_the_language(app, user_settings):
    from jdxi_editor.ui.dialogs.settings import UiPreferencesDialog

    dialog = UiPreferencesDialog(None)
    dialog.settings = user_settings  # before the widgets read it
    dialog.ui_setup(dialog)
    combo = dialog.language_combo
    assert combo.itemData(0) == i18n.SYSTEM
    assert [combo.itemText(i) for i in range(1, combo.count())] == ["English", "Italiano"]
    assert combo.currentData() == i18n.SYSTEM  # nothing chosen yet
    assert not dialog.language_note.isVisibleTo(dialog)
    combo.setCurrentIndex(combo.findData("it"))
    assert dialog.language_note.isVisibleTo(dialog)  # "from the next start"
    dialog.on_save_settings()
    assert i18n.language_setting(user_settings) == "it"
    dialog.deleteLater()


def test_translations_keep_placeholders():
    for message in catalogue.read_ts(catalogue.ts_path("it")).values():
        if message.kind == "vanished":
            continue
        assert catalogue.placeholders(message.translation) == catalogue.placeholders(
            message.source
        ), message.source
