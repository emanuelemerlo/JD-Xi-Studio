"""
Interface language

Every user-visible string goes through ``tr()``::

    from jdxi_editor.i18n import tr

    button = QPushButton(tr("Save"))
    label.setText(tr("Loaded {name}").format(name=name))

``tr()`` looks the text up in ``jdxi_editor_<lang>.qm`` (compiled from the Qt
Linguist ``.ts`` files in this folder) and returns the English text when there
is no translation. It works before the QApplication exists, so strings built
at import time are translated too.

The language comes from Preferences (``ui/language``): "system" follows the
operating system, or a code from ``LANGUAGES``. A change applies at the next
start. Qt's own texts (OK/Cancel buttons, file dialogs) are translated by the
``qtbase_<lang>.qm`` files that ship with Qt, installed by
``install_qt_translators()``.

Parameter names (Cutoff, Resonance, Porta Time...) are not translated: they
stay as on the JD-Xi display and in Roland's manuals, in every language.

To add or update strings, see ``building/i18n.py`` and README.md here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator

from jdxi_editor.project import __organization_name__, __program__

CONTEXT = "JDXi"
LANGUAGE_KEY = "ui/language"
SYSTEM = "system"
DEFAULT_LANGUAGE = "en"  # the language of the source strings
# Code -> name of the language in that language, as shown in Preferences
LANGUAGES: dict[str, str] = {"en": "English", "it": "Italiano"}
I18N_DIR = Path(__file__).resolve().parent

_translator: Optional[QTranslator] = None
_language: Optional[str] = None


def resolve_language(setting: Optional[str], system_locale: Optional[str] = None) -> str:
    """The language to use for a Preferences value ("system", "it", ...)."""
    setting = (setting or SYSTEM).strip()
    if setting != SYSTEM:
        return setting if setting in LANGUAGES else DEFAULT_LANGUAGE
    locale = system_locale or QLocale.system().name()  # "it_IT", "en_GB"
    code = locale.split("_")[0].split("-")[0].lower()
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def _settings() -> QSettings:
    return QSettings(__organization_name__, __program__)


def language_setting(settings: Optional[QSettings] = None) -> str:
    value = (settings or _settings()).value(LANGUAGE_KEY, SYSTEM)
    return str(value or SYSTEM)


def set_language_setting(value: str, settings: Optional[QSettings] = None) -> None:
    """Store the Preferences choice; it takes effect at the next start."""
    (settings or _settings()).setValue(LANGUAGE_KEY, value)


def qm_path(language: str) -> Path:
    return I18N_DIR / f"jdxi_editor_{language}.qm"


def set_language(language: Optional[str] = None) -> str:
    """Load the catalogue for language (default: from Preferences)."""
    global _translator, _language
    if language is None:
        language = resolve_language(
            os.environ.get("JDXI_LANGUAGE") or language_setting()
        )
    translator = None
    if language != DEFAULT_LANGUAGE:
        candidate = QTranslator()
        if candidate.load(str(qm_path(language))):
            translator = candidate
    _translator, _language = translator, language
    return language


def current_language() -> str:
    if _language is None:
        set_language()
    return _language or DEFAULT_LANGUAGE


def tr(text: str, disambiguation: Optional[str] = None) -> str:
    """The translation of an English interface string."""
    if _language is None:
        set_language()
    if _translator is None or not text:
        return text
    translated = _translator.translate(CONTEXT, text, disambiguation)
    return translated or text


def install_qt_translators(app) -> list[QTranslator]:
    """Translate Qt's own dialogs and buttons into the current language."""
    language = current_language()
    installed = []
    if language == DEFAULT_LANGUAGE:
        return installed
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in ("qtbase", "qt"):
        translator = QTranslator(app)
        if translator.load(f"{name}_{language}", folder):
            app.installTranslator(translator)
            installed.append(translator)
            break  # qt_<lang> only wraps qtbase_<lang>
    return installed
