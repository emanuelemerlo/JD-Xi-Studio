"""
A recipe: steps of rows, each row a parameter to set (or to tune by ear).

The columns are the template's: Passo, Nome del passo, Parte, Gruppo, Su,
Parametro, Tipo di valore, Valore, Da, A, Nota. The header lines ("# Titolo:
...") carry the title, description, author, starting tone and user program.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

COLUMNS = ["Passo", "Nome del passo", "Parte", "Gruppo", "Su", "Parametro", "Tipo di valore", "Valore", "Da", "A", "Nota"]
META = {"titolo": "title", "descrizione": "description", "autore": "author", "tono di partenza": "base_tone",
        "programma utente": "user_program", "title": "title", "description": "description", "author": "author",
        "starting tone": "base_tone", "base tone": "base_tone", "user program": "user_program"}
VALUE, RANGE, EAR = "valore", "intervallo", "a orecchio"


@dataclass
class Row:
    step: int = 1
    step_name: str = ""
    part: str = ""
    group: str = ""
    su: str = ""
    param: str = ""
    kind: str = VALUE  # valore | intervallo | a orecchio
    value: str = ""
    lo: str = ""
    hi: str = ""
    note: str = ""
    source: str = ""  # where it was read: "riga 12", "p. 3"

    def cells(self) -> list[str]:
        return [str(self.step), self.step_name, self.part, self.group, self.su, self.param, self.kind,
                self.value, self.lo, self.hi, self.note]


@dataclass
class Recipe:
    title: str = ""
    description: str = ""
    author: str = ""
    base_tone: str = ""
    user_program: str = ""
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # text that is not a row

    def steps(self) -> list[tuple[int, str, list[Row]]]:
        """(number, name, rows) in order."""
        out: dict[int, tuple[str, list[Row]]] = {}
        for row in self.rows:
            name, rows = out.setdefault(row.step, (row.step_name, []))
            if not name and row.step_name:
                out[row.step] = (row.step_name, rows)
            rows.append(row)
        return [(n, out[n][0], out[n][1]) for n in sorted(out)]

    # ------------------------------------------------------------- files
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Recipe":
        data = json.loads(text)
        rows = [Row(**r) for r in data.pop("rows", [])]
        return cls(rows=rows, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def header_lines(self) -> list[str]:
        out = []
        for label, attr in (("Titolo", "title"), ("Descrizione", "description"), ("Autore", "author"),
                            ("Tono di partenza", "base_tone"), ("Programma utente", "user_program")):
            if getattr(self, attr):
                out.append(f"# {label}: {getattr(self, attr)}")
        out.append("# Versione del modello: 1")
        return out

    def to_csv(self, path: Path) -> None:
        import csv

        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            for line in self.header_lines():
                fh.write(line + "\n")
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(COLUMNS)
            for row in self.rows:
                writer.writerow(row.cells())

    def to_markdown(self) -> str:
        lines = [f"# {self.title or 'Ricetta JD-Xi'}", ""]
        if self.description:
            lines += [self.description, ""]
        for label, attr in (("Tono di partenza", "base_tone"), ("Programma utente", "user_program"), ("Autore", "author")):
            if getattr(self, attr):
                lines.append(f"- **{label}:** {getattr(self, attr)}")
        lines += ["", "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
        for row in self.rows:
            lines.append("| " + " | ".join(c.replace("|", "/") for c in row.cells()) + " |")
        return "\n".join(lines) + "\n"

    def to_xlsx(self, path: Path, template: Optional[Path] = None) -> None:
        """Into the template's "Ricetta" sheet when given (menus kept), otherwise a plain sheet."""
        import openpyxl

        if template is not None and Path(template).is_file():
            book = openpyxl.load_workbook(template)
            sheet = book["Ricetta"] if "Ricetta" in book.sheetnames else book.active
            header_row = _find_header_row(sheet)
            # header values in column C of the lines above the table, as in the template
            meta = {"titolo": self.title, "descrizione": self.description, "autore": self.author,
                    "tono di partenza": self.base_tone, "programma utente": self.user_program}
            for r in range(1, header_row):
                key = str(sheet.cell(r, 1).value or "").strip().rstrip(":").lower()
                if key in meta:
                    sheet.cell(r, 3).value = meta[key] or None
            for r in range(header_row + 1, sheet.max_row + 1):  # the example rows go
                for c in range(1, len(COLUMNS) + 1):
                    sheet.cell(r, c).value = None
            for i, row in enumerate(self.rows):
                for c, value in enumerate(row.cells(), start=1):
                    sheet.cell(header_row + 1 + i, c).value = int(value) if c == 1 and value.isdigit() else (value or None)
        else:
            book = openpyxl.Workbook()
            sheet = book.active
            sheet.title = "Ricetta"
            for line in self.header_lines():
                sheet.append([line])
            sheet.append(COLUMNS)
            for row in self.rows:
                sheet.append(row.cells())
        book.save(path)


def _find_header_row(sheet) -> int:
    for r in range(1, min(sheet.max_row, 40) + 1):
        values = [str(sheet.cell(r, c).value or "").strip().lower() for c in range(1, 12)]
        if "parametro" in values and "parte" in values:
            return r
    return 1
