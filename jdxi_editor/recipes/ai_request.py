"""
A request for an AI (a chat assistant) that writes a recipe.

The recipes are meant to be filled in by an AI from a description of the
sound to reproduce, then fine-tuned by ear: the request says what to write
(the template's columns, one parameter per row, in steps), what may be
written (the parameter list of the chosen parts, with ranges and choices) and
shows an example. The answer — a CSV, pasted or saved to a file — is read and
checked like any other recipe.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from jdxi_editor.resources import resource_path

TEMPLATE_DIR = Path("resources") / "recipes"
PARTS = ("D1", "D2", "AN", "DR")
# what a part always brings along: the program's mix and the effects
ALWAYS = ("PROG", "EFFECTS", "EFFETTI")  # EFFETTI: the Italian list's name
INIT_TONES = {"D1": "D1 256 Init Tone", "D2": "D2 256 Init Tone", "AN": "AN 064 Init Tone", "DR": "DR …"}  # no Init kit: the AI chooses the kit

_FILES = {
    "it": {"parameters": "Parametri ricette JD-Xi.csv", "example": "Ricetta JD-Xi - modello.csv"},
    "en": {"parameters": "JD-Xi recipe parameters.csv", "example": "JD-Xi recipe - example.csv"},
}

_TEXT = {
    "en": {
        "intro": "You are a sound designer who knows the Roland JD-Xi well. Write a recipe that sets the "
                 "JD-Xi to reproduce this sound as closely as it can:",
        "part": "Use the {part} part.",
        "any_part": "Choose the part that suits the sound best: Digital 1 or 2 (D1, D2: three partials, "
                    "polyphonic), Analog (AN: one oscillator, monophonic) or Drums (DR).",
        "format": "Answer with the recipe only, as a CSV with ; as separator, in a code block. First these "
                  "lines, then the header and one row per parameter:",
        "rules": [
            "Part, Group and Parameter only as in the list below: those are the names JD-Xi Studio knows.",
            "Value: a number between Min and Max, or one of the Allowed choices, as written in the list.",
            "Value type: «value» for a value; «range» when the right value depends on taste, with From and "
            "To (Value empty); «by ear» for what can only be judged by listening (Value empty, say what to "
            "listen for in Note).",
            "Target: for the parameters that have Target «yes»: the partial (1, 2, 3) of Digital 1/2, the "
            "drum instrument (BD1, SD1, CHH… or a note C2–C5, with /W1…/W4 for a wave), the part (D1, D2, "
            "AN, DR) for PROG; empty otherwise.",
            "Start from the part's Init Tone (Starting tone line): set every parameter that matters for the "
            "sound, those left out stay as in the Init Tone.",
            "Group the rows in steps, in the order a person would set them on the instrument: structure, "
            "oscillators, pitch, filter, amp, envelopes, LFO and modulation, effects. Step is the number, "
            "Step name a short title.",
            "Note: one short sentence with the reason (what the setting does for this sound).",
        ],
        "example": "An example of the format (another sound):",
        "list": "The parameters (Part;Group;Parameter;Full name;Type;Min;Max;Allowed choices;Unit;Target;Notes):",
        "meta": ["# Title: …", "# Description: …", "# Starting tone: {tone}", "# Template version: 1"],
    },
    "it": {
        "intro": "Sei un sound designer che conosce bene il Roland JD-Xi. Scrivi una ricetta che imposti il "
                 "JD-Xi per riprodurre questo suono il più fedelmente possibile:",
        "part": "Usa la parte {part}.",
        "any_part": "Scegli la parte più adatta al suono: Digital 1 o 2 (D1, D2: tre parziali, polifonica), "
                    "Analog (AN: un oscillatore, monofonica) o Drums (DR).",
        "format": "Rispondi solo con la ricetta, in CSV con ; come separatore, in un blocco di codice. Prima "
                  "queste righe, poi l'intestazione e una riga per parametro:",
        "rules": [
            "Parte, Gruppo e Parametro solo come nell'elenco qui sotto: sono i nomi che JD-Xi Studio conosce.",
            "Valore: un numero tra Min e Max, oppure una delle Scelte ammesse, scritta com'è nell'elenco.",
            "Tipo di valore: «valore» per un valore; «intervallo» quando il valore giusto dipende dal gusto, "
            "con Da e A (Valore vuoto); «a orecchio» per ciò che si giudica solo ascoltando (Valore vuoto, "
            "in Nota cosa ascoltare).",
            "Su: per i parametri con Su «sì»: il parziale (1, 2, 3) di Digital 1/2, lo strumento della "
            "batteria (BD1, SD1, CHH… o una nota C2–C5, con /W1…/W4 per un'onda), la parte (D1, D2, AN, DR) "
            "per PROG; vuoto altrimenti.",
            "Parti dall'Init Tone della parte (riga Tono di partenza): imposta tutti i parametri che contano "
            "per il suono, quelli non scritti restano come nell'Init Tone.",
            "Raggruppa le righe in passi, nell'ordine in cui una persona le imposterebbe sullo strumento: "
            "struttura, oscillatori, intonazione, filtro, volume, inviluppi, LFO e modulazione, effetti. "
            "Passo è il numero, Nome del passo un titolo breve.",
            "Nota: una frase breve con il motivo (cosa fa l'impostazione per questo suono).",
        ],
        "example": "Un esempio del formato (un altro suono):",
        "list": "I parametri (Parte;Gruppo;Parametro;Nome esteso;Tipo;Min;Max;Scelte ammesse;Unità;Su;Note):",
        "meta": ["# Titolo: …", "# Descrizione: …", "# Tono di partenza: {tone}", "# Versione del modello: 1"],
    },
}


def _read(name: str) -> str:
    return Path(resource_path(TEMPLATE_DIR / name)).read_text(encoding="utf-8-sig")


def parameter_lines(parts: tuple[str, ...], language: str = "en") -> list[str]:
    """The parameter list's lines (header first) for *parts* and what they always bring."""
    text = _read(_FILES.get(language, _FILES["en"])["parameters"])
    lines = text.splitlines()
    wanted = set(parts) | set(ALWAYS)
    return [lines[0]] + [line for line in lines[1:] if line.split(";", 1)[0] in wanted]


def example_lines(language: str = "en", rows: int = 14) -> list[str]:
    """The example recipe: its header line and first rows (the format, not the sound)."""
    lines = [l for l in _read(_FILES.get(language, _FILES["en"])["example"]).splitlines() if l.strip()]
    body = [l for l in lines if not l.startswith("#")]
    return body[: rows + 1]


def header_line(language: str = "en") -> str:
    return example_lines(language, rows=0)[0]


def build(sound: str, part: str = "", language: str = "en") -> str:
    """
    The request: the sound, the part (one of PARTS, or "" to let the AI choose),
    the format, the rules, an example and the parameter list.
    """
    t = _TEXT.get(language, _TEXT["en"])
    parts = (part,) if part in PARTS else PARTS
    tone = INIT_TONES.get(part, "…")
    out = [t["intro"], "", sound.strip() or "…", ""]
    out.append(t["part"].format(part=part) if part in PARTS else t["any_part"])
    out += ["", t["format"], "", "```"]
    out += [line.format(tone=tone) for line in t["meta"]]
    out += [header_line(language), "…", "```", ""]
    out += [f"- {rule}" for rule in t["rules"]]
    out += ["", t["example"], "", "```"] + example_lines(language) + ["```", ""]
    out += [t["list"], "", "```"] + parameter_lines(parts, language) + ["```"]
    return "\n".join(out) + "\n"


def csv_in_answer(text: str) -> tuple[str, str] | None:
    """
    The CSV of an AI's answer and its separator: the code block (or the lines)
    with the template's header and ; or , between the cells; None if there is none.
    """
    from jdxi_editor.recipes.reader import _header_map

    lines = text.splitlines()
    blocks, inside, current = [], False, []
    for line in lines:
        if line.strip().startswith("```"):
            if inside:
                blocks.append(current)
                current = []
            inside = not inside
            continue
        if inside:
            current.append(line)
    candidates = blocks + [lines]
    for block in candidates:
        for delimiter in (";", ","):
            for i, line in enumerate(block):
                if line.startswith("#"):
                    continue
                cells = next(csv.reader(io.StringIO(line), delimiter=delimiter), [])
                if len(cells) > 3 and _header_map(cells):
                    head = [l for l in block[:i] if l.startswith("#")]
                    body = [l for l in block[i:] if l.strip() and not l.strip().startswith("```")]
                    return "\n".join(head + body), delimiter
    return None
