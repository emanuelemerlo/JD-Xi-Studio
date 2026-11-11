# Translations (i18n)

The interface is in **English** (the language of the source code) and **Italian**.
The user picks the language in **Help › Preferences › Interface language**
(`ui/language` in the settings: `system`, `en`, `it`); it applies at the next start.
For a quick try without changing the settings, set `JDXI_LANGUAGE=it`.

What is translated, and what is not:

- Menus, dialogs, messages, tooltips and editor titles: yes.
- Qt's own texts (OK/Cancel, file dialogs): yes, from the `qtbase_<lang>.qm` files that ship with Qt.
- **Parameter names** (Cutoff, Resonance, Porta Time, Dly Send Lev…): no. They stay as on the JD-Xi
  display and in Roland's manuals, which use them in every language, so the screen matches the instrument.
- Log messages: no.

## Marking strings

Wrap every user-visible string in `tr()`:

```python
from jdxi_editor.i18n import tr

QPushButton(tr("Save"))
QMessageBox.warning(self, tr("Error"), tr("Could not load pattern: {error}").format(error=ex))
tr("Clear", "pattern")   # second argument: disambiguation, when one English word has two meanings
```

- Use named `{placeholders}` and `.format()`, not f-strings: the whole sentence must be in the catalogue,
  and translators may move the placeholders.
- Keep `&` accelerators (`&File`); in tab titles a literal `&` is written `&&`.
- `tr()` works at import time too (before the QApplication exists).

## Updating the catalogues

From the project root:

```bash
python -m building.i18n update    # collect tr() strings into jdxi_editor/i18n/jdxi_editor_<lang>.ts
pyside6-linguist jdxi_editor/i18n/jdxi_editor_it.ts   # or edit the XML: fill <translation>, remove type="unfinished"
python -m building.i18n compile   # .ts -> .qm (pyside6-lrelease)
python -m building.i18n check     # anything missing, untranslated, with different placeholders, or stale
```

Commit both the `.ts` and the `.qm`. `tests/test_i18n.py` runs `check`, so the tests fail while a string is
untranslated or the `.qm` is older than the `.ts`.

## Adding a language

1. Add it to `LANGUAGES` in `jdxi_editor/i18n/__init__.py` (code → name in that language, e.g. `"de": "Deutsch"`)
   and in `building/i18n.py` (code → Qt locale, e.g. `"de": "de_DE"`).
2. `python -m building.i18n update`, translate `jdxi_editor_de.ts`, `python -m building.i18n compile`.
3. Add the Inno Setup language in `jdxi_editor.iss` if the installer should offer it.

Terms used in Italian follow Roland's Italian manual: *programma*, *tono*, *parte Drums*, *misura*, *pattern*;
*partial*, *preset*, *Program Change*, *SysEx* are kept as they are.
