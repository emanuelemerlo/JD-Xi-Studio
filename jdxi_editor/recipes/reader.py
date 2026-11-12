"""
Reading recipes: the template (.xlsx, .csv), a Markdown or text table, a
table pasted from a document or web page, or a PDF.

Files with the template's columns are read column by column. Free text (a
PDF, a pasted page) is read line by line: lines that look like
"Group · Parameter · Value" become rows, everything else is kept as notes.
Nothing is checked here: check.py says what each row means.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Iterable, Optional

from jdxi_editor.recipes import catalog
from jdxi_editor.recipes.model import COLUMNS, EAR, META, RANGE, VALUE, Recipe, Row

_HEADER_ALIASES = {
    "passo": "Passo", "step": "Passo", "nome del passo": "Nome del passo", "step name": "Nome del passo",
    "parte": "Parte", "part": "Parte", "gruppo": "Gruppo", "group": "Gruppo", "su": "Su", "on": "Su",
    "parametro": "Parametro", "parameter": "Parametro", "tipo di valore": "Tipo di valore", "value type": "Tipo di valore",
    "valore": "Valore", "value": "Valore", "da": "Da", "from": "Da", "a": "A", "to": "A", "nota": "Nota", "note": "Nota",
    "notes": "Nota", "note/commenti": "Nota", "target": "Su",
}
# The English template's value types
KIND_ALIASES = {"value": VALUE, "range": RANGE, "by ear": EAR}
RANGE_RE = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(?:–|—|-|…|\.\.\.?|to|a)\s*([+-]?\d+(?:[.,]\d+)?)\s*([a-z%]*)\s*$", re.I)
EAR_WORDS = ("a orecchio", "orecchio", "by ear", "to taste", "ear")


def read_file(path: str | Path) -> Recipe:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if suffix == ".pdf":
        return read_text(_pdf_text(path), source_prefix="p.")
    if suffix == ".json":
        return Recipe.from_json(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if suffix == ".csv":
        return read_csv_text(text)
    return read_text(text)


# ------------------------------------------------------------ tables
def _header_map(cells: list[str]) -> Optional[dict[str, int]]:
    found = {}
    for i, cell in enumerate(cells):
        name = _HEADER_ALIASES.get(str(cell or "").strip().lower())
        if name and name not in found:
            found[name] = i
    return found if "Parametro" in found and ("Valore" in found or "Da" in found) else None


def _row_from(cells: list[str], columns: dict[str, int], source: str) -> Optional[Row]:
    def get(name):
        i = columns.get(name)
        return "" if i is None or i >= len(cells) or cells[i] is None else str(cells[i]).strip()

    if not get("Parametro"):
        return None
    step_text = get("Passo")
    step_match = re.match(r"\s*(\d+)\s*(.*)", step_text)
    step = int(step_match.group(1)) if step_match else 1
    step_name = get("Nome del passo") or (step_match.group(2).strip(" ·.-") if step_match else "")
    row = Row(step, step_name, get("Parte"), get("Gruppo"), get("Su"), get("Parametro"),
              (get("Tipo di valore") or "").lower(), get("Valore"), get("Da"), get("A"), get("Nota"), source)
    row.kind = KIND_ALIASES.get(row.kind, row.kind)  # the English template's words
    if row.kind not in (VALUE, RANGE, EAR):
        row.kind = classify_value(row.value, row.lo, row.hi)
    return row


def classify_value(value: str, lo: str = "", hi: str = "") -> str:
    v = value.strip().lower()
    if any(re.search(r"\b" + w + r"\b", v) for w in EAR_WORDS) or (not v and not lo and not hi):
        return EAR
    if (lo and hi) or RANGE_RE.match(value or ""):
        return RANGE
    return VALUE


def _meta(recipe: Recipe, key: str, value: str) -> bool:
    attr = META.get(key.strip().rstrip(":").lower())
    if attr and value:
        setattr(recipe, attr, value.strip())
        return True
    return attr is not None


def _read_rows(rows: Iterable[list], source_label: str = "riga") -> Recipe:
    recipe = Recipe()
    columns = None
    for number, cells in enumerate(rows, start=1):
        cells = ["" if c is None else str(c) for c in cells]
        first = cells[0].strip() if cells else ""
        if columns is None:
            if first.startswith("#") and ":" in first:  # "# Titolo: ..."
                key, _, value = first.lstrip("# ").partition(":")
                _meta(recipe, key, value)
                continue
            if first and not first.startswith("#"):  # "Titolo | | Il lead ..." as in the .xlsx
                values = [c for c in cells[1:] if c.strip()]
                if _meta(recipe, first, values[0] if values else ""):
                    continue
            columns = _header_map(cells)
            continue
        row = _row_from(cells, columns, f"{source_label} {number}")
        if row is not None:
            recipe.rows.append(row)
    return recipe


def read_xlsx(path: Path) -> Recipe:
    import openpyxl

    book = openpyxl.load_workbook(path, data_only=True, read_only=True)
    names = [n for n in ("Ricetta", "Recipe") if n in book.sheetnames]
    sheet = book[names[0]] if names else book.active
    return _read_rows(sheet.iter_rows(values_only=True))


def read_csv_text(text: str) -> Recipe:
    lines = text.splitlines()
    body = "\n".join(lines)
    sample = "\n".join(line for line in lines if not line.startswith("#"))[:4000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"
    return _read_rows(csv.reader(io.StringIO(body), delimiter=delimiter))


# ------------------------------------------------------------ free text
def _markdown_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_text(text: str, source_prefix: str = "riga") -> Recipe:
    """A Markdown/tab table with the template's columns, or free text read line by line."""
    lines = text.splitlines()
    table = [_markdown_cells(l) for l in lines if l.strip().startswith("|") and not re.match(r"^\s*\|[\s:|-]+\|\s*$", l)]
    if table and _header_map(table[0]):
        recipe = _read_rows(table)
        _read_title(recipe, lines)
        return recipe
    tabbed = [l.split("\t") for l in lines if "\t" in l]
    if tabbed and _header_map(tabbed[0]):
        return _read_rows(tabbed)
    return read_free_text(lines, source_prefix)


def _read_title(recipe: Recipe, lines: list[str]) -> None:
    for line in lines:
        if line.startswith("# ") and not recipe.title:
            recipe.title = line[2:].strip()
        m = re.match(r"-\s*\*\*(.+?):\*\*\s*(.+)", line.strip())
        if m:
            _meta(recipe, m.group(1), m.group(2))


_PAGE_RE = re.compile(r"^\f|^\s*---\s*page\s+(\d+)", re.I)
_SPLIT_RE = re.compile(r"\s*(?:\t|·|\||;|\s{2,})\s*")


def read_free_text(lines: list[str], source_prefix: str = "riga") -> Recipe:
    """
    Rows from lines such as "TONE: FILTER  Cutoff  55–65" or "AN FILTER Cutoff 60 (start here)".
    The part comes from "TONE"/"PROG" prefixes or from the last part named in a heading.
    """
    recipe = Recipe()
    part = ""
    step, step_name = 1, ""
    page = 1
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"\s*---\s*page\s+(\d+)", line, re.I)
        if m:
            page = int(m.group(1))
            continue
        source = f"p. {page}" if source_prefix == "p." else f"{source_prefix} {number}"
        if not recipe.title and line.startswith("#"):
            recipe.title = line.lstrip("# ").strip()
            continue
        heading = re.match(r"^(?:#+\s*)?(?:passo|step)\s*(\d+)\s*[:.\-–·]?\s*(.*)$", line, re.I)
        if heading:
            step, step_name = int(heading.group(1)), heading.group(2).strip()
            continue
        named = catalog.find_part(line.split()[0]) if line.split() else None
        row = _row_from_free_line(line, part, step, step_name, source)
        if row is not None:
            recipe.rows.append(row)
            part = row.part or part
        else:
            if named and len(line.split()) <= 3:
                part = named
            recipe.notes.append(f"{source}: {line}")
    return recipe


def _row_from_free_line(line: str, part: str, step: int, step_name: str, source: str) -> Optional[Row]:
    note = ""
    paren = re.search(r"\(([^)]*)\)\s*$", line)
    if paren:
        note, line = paren.group(1).strip(), line[: paren.start()].strip()
    text = line
    group = ""
    prefix = re.match(r"^(TONE|PROG|KIT)\s*:\s*([A-Z0-9 &]+?)(?:\s+(D1|D2|AN|DR))?\s*(?:·|\t|\s{2,}|$)", text)
    su = ""
    if prefix:
        group = prefix.group(2).strip()
        su = prefix.group(3) or ""
        if prefix.group(1) == "PROG":
            part = "PROG"
        text = text[prefix.end():].strip()
    pieces = [p for p in _SPLIT_RE.split(text) if p]
    if not group and len(pieces) >= 3:
        maybe_part = catalog.find_part(pieces[0])
        if maybe_part:
            part, pieces = maybe_part, pieces[1:]
        if pieces and pieces[0].upper() in {g.upper() for p in catalog.PARTS for g in catalog.groups_of(p)}:
            group, pieces = pieces[0].upper(), pieces[1:]
    if not group or len(pieces) < 2:
        return None
    param, value = pieces[0], " ".join(pieces[1:])
    if not catalog.labels_of(part, group) and part not in ("", "PROG"):
        pass
    kind = classify_value(value)
    if kind == EAR:
        extra = re.sub(r"(?i)[, ]*\b(a orecchio|by ear)\b[, ]*", " ", value).strip(" ,;")
        note = "; ".join(x for x in (extra, note) if x)
        value = ""
    return Row(step, step_name, part, group, su, param, kind, value, "", "", note, source)


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as ex:  # pragma: no cover - pypdf is a dependency
        raise RuntimeError("Reading PDF files needs the pypdf package") from ex
    reader = PdfReader(str(path))
    parts = []
    for number, page in enumerate(reader.pages, start=1):
        parts.append(f"--- page {number}")
        parts.append(page.extract_text() or "")
    return "\n".join(parts)
