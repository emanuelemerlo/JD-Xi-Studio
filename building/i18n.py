"""
Translation catalogue tools

    python -m building.i18n update    # sources -> jdxi_editor/i18n/*.ts
    python -m building.i18n compile   # *.ts -> *.qm (pyside6-lrelease)
    python -m building.i18n check     # what is missing, unfinished or stale

Strings are collected from every ``tr("...")`` call in jdxi_editor/ (the
function in jdxi_editor.i18n). ``update`` keeps the existing translations,
adds new strings as "unfinished" and marks the ones no longer used as
"vanished". Translate the .ts files with Qt Linguist (``pyside6-linguist``)
or any editor, then run ``compile`` and commit both .ts and .qm.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "jdxi_editor"
I18N = PACKAGE / "i18n"
CONTEXT = "JDXi"
LANGUAGES = {"it": "it_IT"}  # every language but English, the source language
PLACEHOLDER = re.compile(r"\{[^{}]*\}|%[sdif]|%\d|&(?!&)\w")


@dataclass
class Message:
    source: str
    comment: Optional[str] = None
    locations: list[tuple[str, int]] = field(default_factory=list)
    translation: str = ""
    kind: str = "unfinished"  # "", "unfinished", "vanished"

    @property
    def key(self) -> tuple[str, Optional[str]]:
        return self.source, self.comment


def _const_str(node) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def extract(paths: Optional[Iterable[Path]] = None) -> dict:
    """Every tr("literal"[, "disambiguation"]) call, in order of appearance."""
    messages: dict = {}
    files = sorted(paths or PACKAGE.rglob("*.py"))
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name != "tr":
                continue
            source = _const_str(node.args[0])
            if source is None:
                continue
            comment = _const_str(node.args[1]) if len(node.args) > 1 else None
            for kw in node.keywords:
                if kw.arg == "disambiguation":
                    comment = _const_str(kw.value)
            msg = messages.setdefault((source, comment), Message(source, comment))
            msg.locations.append((rel, node.lineno))
    return messages


def ts_path(language: str) -> Path:
    return I18N / f"jdxi_editor_{language}.ts"


def read_ts(path: Path) -> dict:
    messages: dict = {}
    if not path.exists():
        return messages
    for msg in ET.parse(path).getroot().iter("message"):
        source = msg.findtext("source") or ""
        comment = msg.findtext("comment")
        tnode = msg.find("translation")
        m = Message(source, comment)
        m.translation = (tnode.text or "") if tnode is not None else ""
        m.kind = tnode.get("type", "") if tnode is not None else "unfinished"
        messages[m.key] = m
    return messages


def write_ts(path: Path, language: str, messages: Iterable[Message]) -> None:
    root = ET.Element("TS", version="2.1", language=LANGUAGES.get(language, language), sourcelanguage="en")
    ctx = ET.SubElement(root, "context")
    ET.SubElement(ctx, "name").text = CONTEXT
    for m in messages:
        node = ET.SubElement(ctx, "message")
        for filename, line in m.locations:
            rel = Path(filename).as_posix()
            ET.SubElement(node, "location", filename=f"../../{rel}", line=str(line))
        ET.SubElement(node, "source").text = m.source
        if m.comment:
            ET.SubElement(node, "comment").text = m.comment
        t = ET.SubElement(node, "translation")
        if m.kind:
            t.set("type", m.kind)
        t.text = m.translation
    ET.indent(root, space="    ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + body + "\n", encoding="utf-8")


def merge(found: dict, existing: dict) -> list[Message]:
    merged = []
    for key, m in found.items():
        old = existing.get(key)
        if old is not None and old.translation:
            m.translation = old.translation
            m.kind = "" if old.kind in ("", "vanished") else old.kind
        merged.append(m)
    for key, old in existing.items():
        if key not in found and old.translation:
            old.kind, old.locations = "vanished", []
            merged.append(old)
    return merged


def update(languages: Iterable[str] = LANGUAGES) -> None:
    found = extract()
    for language in languages:
        path = ts_path(language)
        fresh = {k: Message(m.source, m.comment, list(m.locations)) for k, m in found.items()}
        write_ts(path, language, merge(fresh, read_ts(path)))
        print(f"{path.relative_to(ROOT)}: {len(found)} strings")


def lrelease() -> Optional[str]:
    return shutil.which("pyside6-lrelease") or shutil.which("lrelease")


def compile_ts(language: str, out: Optional[Path] = None) -> Path:
    tool = lrelease()
    if tool is None:
        raise RuntimeError("pyside6-lrelease not found (pip install PySide6)")
    out = out or I18N / f"jdxi_editor_{language}.qm"
    subprocess.run([tool, "-silent", "-nounfinished", str(ts_path(language)), "-qm", str(out)], check=True)
    return out


def compile_all(languages: Iterable[str] = LANGUAGES) -> None:
    for language in languages:
        print(compile_ts(language).relative_to(ROOT))


def placeholders(text: str) -> list[str]:
    return sorted(p for p in PLACEHOLDER.findall(text) if not p.startswith("&"))


def _stale_qm(language: str, messages: dict) -> list[str]:
    """The committed .qm must give every translation of the .ts.

    Compared through QTranslator rather than byte by byte, so that a
    different lrelease version does not count as a change.
    """
    from PySide6.QtCore import QTranslator

    path = I18N / f"jdxi_editor_{language}.qm"
    translator = QTranslator()
    if not path.exists() or not translator.load(str(path)):
        return [f"{language}: {path.name} is missing (run compile)"]
    for m in messages.values():
        if m.kind or not m.translation:
            continue
        if translator.translate(CONTEXT, m.source, m.comment) != m.translation:
            return [f"{language}: {path.name} is out of date (run compile): {m.source!r}"]
    return []


def check(languages: Iterable[str] = LANGUAGES, qm: bool = True) -> list[str]:
    """Problems that would show English, broken text or an old catalogue."""
    problems = []
    found = extract()
    for language in languages:
        existing = read_ts(ts_path(language))
        for key, m in found.items():
            old = existing.get(key)
            where = f"{m.locations[0][0]}:{m.locations[0][1]}"
            if old is None:
                problems.append(f"{language}: not in the .ts (run update): {m.source!r} ({where})")
            elif old.kind == "unfinished" or not old.translation:
                problems.append(f"{language}: not translated: {m.source!r} ({where})")
            elif placeholders(old.translation) != placeholders(m.source):
                problems.append(f"{language}: placeholders differ: {m.source!r} -> {old.translation!r}")
        if qm:
            problems += _stale_qm(language, existing)
    return problems


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    if command == "update":
        update()
    elif command == "compile":
        compile_all()
    elif command == "check":
        problems = check()
        print("\n".join(problems) or "Translations complete and up to date.")
        return 1 if problems else 0
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
