"""
Makes the English recipe files from the Italian ones (resources/recipes):

    python building/recipes/make_english.py

  Ricetta JD-Xi - modello.xlsx  ->  JD-Xi recipe - template.xlsx
  Ricetta JD-Xi - modello.csv   ->  JD-Xi recipe - example.csv
  Ricetta JD-Xi - vuota.csv     ->  JD-Xi recipe - blank.csv
  Parametri ricette JD-Xi.csv   ->  JD-Xi recipe parameters.csv

The workbook keeps its menus and checks: sheets, named ranges, the menus'
sources and every text inside the formulas are translated together, so the
cascading menus and the Check column work as in the Italian one. Part codes
EFFETTI and VOCE become EFFECTS and VOCAL (the editor reads both).
Run it again after changing the Italian files.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "resources" / "recipes"

SHEETS = {"Ricetta": "Recipe", "Istruzioni": "Instructions", "Parametri": "Parameters", "Liste": "Lists"}
PARTS = {"EFFETTI": "EFFECTS", "VOCE": "VOCAL"}

# Whole cell values and whole text literals inside formulas
TEXT = {
    # --- Recipe sheet
    "Ricetta per JD-Xi": "JD-Xi recipe",
    "Compila solo le celle gialle. La colonna Controllo ti dice subito se una riga è a posto. Le righe azzurre sono l'esempio: sovrascrivile o cancellale.":
        "Fill in the yellow cells only. The Check column tells you at once whether a row is right. The light blue rows are the example: overwrite or delete them.",
    "Titolo": "Title", "Descrizione": "Description", "Autore": "Author", "Tono di partenza": "Starting tone",
    "Programma utente": "User program", "Versione del modello": "Template version", "Stato": "Status",
    "Righe compilate": "Rows filled in", "Da correggere (✗)": "To fix (✗)", "A orecchio (~)": "By ear (~)",
    "Il lead di Jungle Gardenia": "The Jungle Gardenia lead",
    "Lead scuro e flautato, legato, vibrato con la modulation wheel": "Dark, flute-like lead, legato, vibrato with the modulation wheel",
    "Es. «AN 064 Init Tone», «D1 001 JP8 Strings1», «DR 001 TR-909». Lascia vuoto per partire dal suono attuale.":
        "E.g. “AN 064 Init Tone”, “D1 001 JP8 Strings1”, “DR 001 TR-909”. Leave empty to start from the current sound.",
    "E01…H64: banchi utente. Il JD-Xi salva solo con [Menu/Write] sullo strumento.":
        "E01…H64: user banks. The JD-Xi saves only with [Menu/Write] on the instrument.",
    "Passo": "Step", "Nome del passo": "Step name", "Parte": "Part", "Gruppo": "Group", "Su": "Target",
    "Parametro": "Parameter", "Tipo di valore": "Value type", "Valore": "Value", "Da": "From", "A": "To",
    "Nota": "Note", "Controllo": "Check", "idx": "idx", "tipo": "type", "min": "min", "max": "max",
    "scelte": "choices", "su richiesto": "target required",
    "Oscillatore": "Oscillator", "Filtro": "Filter", "Ampiezza": "Amplitude", "Vibrato": "Vibrato", "Effetti": "Effects",
    "Triangolare: quasi solo armoniche dispari, come l'originale": "Triangle: almost only odd harmonics, like the original",
    "Portamento corto per le salite di semitono": "Short portamento for the semitone climbs",
    "Parti da 60 sulla nota lunga di 0:10, poi abbassa finché sparisce il ronzio acuto":
        "Start at 60 on the long note at 0:10, then lower it until the high buzz disappears",
    "L'originale non ha picchi di risonanza": "The original has no resonance peaks",
    "Il timbro resta simile tra Si4 e Fa#5": "The tone stays similar between B4 and F#5",
    "Con Depth +5: leggerissimo accento iniziale": "With Depth +5: a very light accent at the start",
    "Se senti ancora un clic, sali a 15": "If you still hear a click, go up to 15",
    "Nota lunga e piena": "Long, full note",
    "Piccola coda, la allungano delay e riverbero": "Short tail: the delay and the reverb lengthen it",
    "Circa 5 Hz: con la mod wheel a metà conta 5 oscillazioni al secondo":
        "About 5 Hz: with the mod wheel halfway, count 5 swings a second",
    "Wheel al massimo: vibrato leggero, circa ±15 cent": "Wheel at maximum: light vibrato, about ±15 cents",
    "Passa per EFX1, EFX2, Delay e Reverb": "Goes through EFX1, EFX2, Delay and Reverb",
    "Solo un po' di calore; se ronza, abbassa": "Just a little warmth; if it buzzes, lower it",
    "Stesso volume con e senza effetto": "Same volume with and without the effect",
    "In serie con Effect 2": "In series with Effect 2",
    "Con Feedback 0 il Flanger fa da chorus": "With Feedback 0 the Flanger works as a chorus",
    "Dà la larghezza stereo": "Gives the stereo width",
    "Tiene scure le code": "Keeps the tails dark",
    "Oppure STAGE1": "Or STAGE1",
    # value types and parameter kinds (data and formula literals alike)
    "valore": "value", "intervallo": "range", "a orecchio": "by ear",
    "scelta": "choice", "numero": "number", "numero o scelta": "number or choice", "nota": "note", "testo": "text",
    "sì": "yes", "no": "no", "facoltativo": "optional",
    # --- formula messages
    "Ricetta vuota": "Empty recipe",
    "✓ Pronta da importare": "✓ Ready to import",
    "✗ Correggi le righe in rosso prima di importare": "✗ Fix the red rows before importing",
    "✗ Scegli la parte": "✗ Choose the part",
    "✗ Parametro non valido per questa parte e gruppo": "✗ Not a parameter of this part and group",
    "✗ Indica in «Su» lo strumento o la parte": "✗ Give the instrument or the part in “Target”",
    "✗ Scegli il tipo di valore": "✗ Choose the value type",
    "~ A orecchio: lo regoli ascoltando": "~ By ear: you set it by listening",
    "✗ Questo parametro non accetta un intervallo: usa «valore»": "✗ This parameter takes no range: use “value”",
    "✗ Scrivi «Da» e «A» come numeri": "✗ Write “From” and “To” as numbers",
    "✗ «Da» deve essere minore di «A»": "✗ “From” must be less than “To”",
    "✗ Fuori dai limiti: da ": "✗ Out of range: from ",
    " a ": " to ",
    "✗ Manca il valore": "✗ The value is missing",
    "✗ Valore non riconosciuto": "✗ Value not recognised",
    ": scegli tra ": ": choose from ",
    ": scrivi come D50:50W": ": write it as D50:50W",
    ": scrivi L15, C, 15R o un numero": ": write L15, C, 15R or a number",
    "? Sarà controllata all'importazione": "? Checked when importing",
    # --- Instructions sheet
    "Come compilare una ricetta": "How to fill in a recipe",
    "Una ricetta è un elenco di impostazioni da fare sul JD-Xi, in ordine. L'editor la importa, la controlla e la applica un passo alla volta. Una riga = un parametro.":
        "A recipe is a list of settings to make on the JD-Xi, in order. The editor imports it, checks it and applies it one step at a time. One row = one parameter.",
    "In breve": "In short",
    "1. Intestazione": "1. Header",
    "Nel foglio Ricetta, in alto: titolo, tono di partenza (es. AN 064 Init Tone) e programma utente da sovrascrivere (E01…H64).":
        "At the top of the Recipe sheet: title, starting tone (e.g. AN 064 Init Tone) and the user program to overwrite (E01…H64).",
    "2. Una riga per parametro": "2. One row per parameter",
    "Scegli dai menu, da sinistra a destra: Parte → Gruppo → Su (se serve) → Parametro. I menu mostrano solo le voci che esistono per quella parte.":
        "Choose from the menus, left to right: Part → Group → Target (if needed) → Parameter. The menus show only what exists for that part.",
    "3. Il valore": "3. The value",
    "Scegli il tipo: «valore» (un numero o una scelta), «intervallo» (Da/A: un punto di partenza da rifinire) o «a orecchio» (nessun numero: spiega in Nota come regolarlo).":
        "Choose the type: “value” (a number or a choice), “range” (From/To: a starting point to refine) or “by ear” (no number: explain in Note how to set it).",
    "4. Guarda Controllo": "4. Look at Check",
    "✓ a posto · ✗ da correggere (il messaggio dice cosa) · ~ a orecchio · ? verrà controllata all'importazione. In alto «Stato» dice se la ricetta è pronta.":
        "✓ right · ✗ to fix (the message says what) · ~ by ear · ? checked when importing. At the top, “Status” says whether the recipe is ready.",
    "5. Passi": "5. Steps",
    "Raggruppa le righe in passi (1, 2, 3…) con un nome breve: Oscillatore, Filtro… L'editor ti guida un passo alla volta.":
        "Group the rows into steps (1, 2, 3…) with a short name: Oscillator, Filter… The editor guides you one step at a time.",
    "Come si scrivono i valori": "How to write the values",
    "Numeri": "Numbers",
    "Come sul display: 60, -2, +50. Niente unità: ms, Hz, % e semitoni sono sottintesi (colonna Unità del foglio Parametri).":
        "As on the display: 60, -2, +50. No units: ms, Hz, % and semitones are implied (Unit column of the Parameters sheet).",
    "Scelte": "Choices",
    "Il testo del display: TRI, LPF, ON, HALL1, Distortion. Maiuscole e minuscole non contano.":
        "The display's text: TRI, LPF, ON, HALL1, Distortion. Upper or lower case does not matter.",
    "Pan": "Pan",
    "L64 … C … 63R, oppure un numero da -64 a 63.": "L64 … C … 63R, or a number from -64 to 63.",
    "Bilanciamento": "Balance",
    "D50:50W (dry:wet), come sul display.": "D50:50W (dry:wet), as on the display.",
    "Note musicali e tempi": "Notes and timings",
    "Note come C4 o C#2; divisioni del tempo come 1/16 (la colonna Valore è testo, quindi 1/16 non diventa una data).":
        "Notes as C4 or C#2; note values as 1/16 (the Value column is text, so 1/16 does not turn into a date).",
    "Intervalli": "Ranges",
    "Due numeri in Da e A, es. Cutoff 55 → 65. L'editor parte dal centro e ti mostra l'intervallo accanto al controllo.":
        "Two numbers in From and To, e.g. Cutoff 55 → 65. The editor starts from the middle and shows the range next to the control.",
    "Più valori insieme": "Several values at once",
    "Non scrivere «0 / 40 / 100 / 30» in una riga: usa una riga per Attack, una per Decay e così via. È il modo per evitare valori assegnati al parametro sbagliato.":
        "Do not write “0 / 40 / 100 / 30” in one row: use one row for Attack, one for Decay and so on. That way no value goes to the wrong parameter.",
    "La colonna «Su»": "The “Target” column",
    "P1, P2 o P3 per un partial; vuoto = tutti i partial accesi.": "P1, P2 or P3 for one partial; empty = all the partials that are on.",
    "DR (Drums)": "DR (Drums)",
    "Lo strumento (BD1, SD1, CHH…). Per i gruppi WAVE e WMT anche l'onda: SD1/W2.":
        "The instrument (BD1, SD1, CHH…). For the WAVE and WMT groups also the wave: SD1/W2.",
    "Per MAIN, PITCH e OFFSET la parte: D1, D2, DR o AN. Per COMMON lascia vuoto.":
        "For MAIN, PITCH and OFFSET the part: D1, D2, DR or AN. For COMMON leave it empty.",
    "Altre parti": "Other parts",
    "Lascia vuoto.": "Leave it empty.",
    "Cosa succede all'importazione": "What happens when importing",
    "Prima": "Before",
    "L'editor ricontrolla ogni riga e propone una correzione per quelle dubbie. Finché c'è una riga ✗ non importa.":
        "The editor checks every row again and suggests a fix for doubtful ones. While a ✗ row is left, it does not import.",
    "Durante": "During",
    "Nulla viene inviato al JD-Xi finché non applichi un passo. Prima del primo passo l'editor salva una copia del suono attuale, per tornare indietro.":
        "Nothing is sent to the JD-Xi until you apply a step. Before the first step the editor keeps a copy of the current sound, to go back.",
    "Salvataggio": "Saving",
    "Il JD-Xi non accetta un comando MIDI di scrittura in memoria: per salvare nel programma scelto (E01…H64) si preme [Menu/Write] sullo strumento. L'editor ti indica quando farlo.":
        "The JD-Xi takes no MIDI command to write its memory: to save into the chosen program (E01…H64) press [Menu/Write] on the instrument. The editor tells you when.",
    "Compatibilità": "Compatibility",
    "Excel, LibreOffice": "Excel, LibreOffice",
    "Menu a cascata e Controllo funzionano.": "The cascading menus and Check work.",
    "Google Fogli, Numbers": "Google Sheets, Numbers",
    "La colonna Controllo funziona; i menu a cascata (Gruppo, Su, Parametro) potrebbero non comparire: copia i nomi dal foglio Parametri.":
        "The Check column works; the cascading menus (Group, Target, Parameter) may not appear: copy the names from the Parameters sheet.",
    "Stesse colonne del foglio Ricetta, separate da punto e virgola. Le righe che iniziano con # sono l'intestazione.":
        "The Recipe sheet's columns, separated by semicolons. Rows starting with # are the header.",
    "Fonti": "Sources",
    "Nomi e intervalli": "Names and ranges",
    "JD-Xi Parameter Guide (e01) e Leaflet v1.50 (side chain del compressore). Il foglio Parametri contiene l'elenco completo.":
        "JD-Xi Parameter Guide (e01) and Leaflet v1.50 (the compressor's side chain). The Parameters sheet has the full list.",
    "Esempio": "Example",
    "Le righe azzurre vengono dalla guida «Il lead di Jungle Gardenia sul JD-Xi».":
        "The light blue rows come from the guide “The Jungle Gardenia lead on the JD-Xi”.",
    # --- Parameters sheet
    "Nome esteso": "Full name", "Tipo": "Type", "Min": "Min", "Max": "Max", "Scelte ammesse": "Allowed choices",
    "Unità": "Unit", "Note": "Notes", "Chiave": "Key",
    "Effetto con la modulation wheel": "Effect with the modulation wheel",
    "Accende/spegne un partial (pulsanti 05–07)": "Switches a partial on/off (buttons 05–07)",
    "Solo con Waveform PCM": "Only with Waveform PCM",
    "L64 … C … 63R oppure -64 … 63": "L64 … C … 63R or -64 … 63",
    "Vale per tutto il kit": "For the whole kit",
    "Nota da C-1 a G9, es. C4": "Note from C-1 to G9, e.g. C4",
    "Vale se la parte Drums ha Part Output = KIT": "When the Drums part has Part Output = KIT",
    "KIT solo per la parte Drums": "KIT only for the Drums part",
    "Per la parte AN solo MONO": "For the AN part MONO only",
    "EFX2 = in serie con Effect 2": "EFX2 = in series with Effect 2",
    "Livello dell'effetto (tutti i tipi)": "The effect's level (every type)",
    "Type di Distortion / Fuzz": "Distortion / Fuzz type",
    "Flanger, Phaser (numero o nota); Slicer (solo nota)": "Flanger, Phaser (number or note); Slicer (note only)",
    "Solo con Type = PAN": "Only with Type = PAN",
    # --- Lists sheet
    "Parti": "Parts", "Parti del programma": "Program parts", "Chiave parte|gruppo": "Part|group key",
    "Strumenti Drums": "Drum instruments", "Strumento/onda": "Instrument/wave", "Nessuno": "None",
    "Lista «Su»": "“Target” list", "No.L (Mono)": "No.L (Mono)", "No.R": "No.R",
    # --- data validation messages
    "Scrivi un programma utente da E01 a H64.": "Write a user program from E01 to H64.",
    "Programma non valido": "Not a user program",
    "Scegli una parte dal menu: AN, D1, D2, DR, PROG, EFFETTI, VOCE, ARP.": "Choose a part from the menu: AN, D1, D2, DR, PROG, EFFECTS, VOCAL, ARP.",
    "Parte non valida": "Not a part",
    "Prima scegli la Parte, poi un gruppo dal menu.": "Choose the Part first, then a group from the menu.",
    "Gruppo non valido": "Not a group",
    "Scegli dal menu: partial (P1–P3), strumento (SD1, SD1/W2) o parte (D1, D2, DR, AN).":
        "Choose from the menu: partial (P1–P3), instrument (SD1, SD1/W2) or part (D1, D2, DR, AN).",
    "Valore non valido": "Not a valid value",
    "Prima scegli Parte e Gruppo, poi un parametro dal menu.": "Choose Part and Group first, then a parameter from the menu.",
    "Parametro non valido": "Not a parameter",
    "Scegli valore, intervallo o a orecchio.": "Choose value, range or by ear.",
    "Tipo non valido": "Not a value type",
    "Il passo è un numero intero da 1 a 30.": "The step is a whole number from 1 to 30.",
    "Passo non valido": "Not a step",
    "«Da» e «A» sono numeri (le unità sono sottintese).": "“From” and “To” are numbers (the units are implied).",
    "Serve un numero": "A number is needed",
}
# The Lists sheet's group headers, "Gruppi AN" ...
for code in ("AN", "D1", "D2", "DR", "PROG", "EFFETTI", "VOCE", "ARP"):
    TEXT[f"Gruppi {code}"] = f"{PARTS.get(code, code)} groups"


def part(value: str) -> str:
    """Part codes inside a value: EFFETTI|DELAY|Level, "EFFETTI · EFFECT1", P_EFFETTI_DELAY ..."""
    for it, en in PARTS.items():
        value = re.sub(rf"(?<![A-Z]){it}(?![A-Z])", en, value)
    return value


def text(value: str) -> str:
    return TEXT.get(value, part(value))


def formula(value: str) -> str:
    for it, en in SHEETS.items():
        value = value.replace(f"{it}!", f"{en}!")
    return re.sub(r'"([^"]*)"', lambda m: '"' + text(m.group(1)) + '"', value)


def english_workbook(source: Path, target: Path) -> None:
    book = openpyxl.load_workbook(source)
    for sheet in book:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    cell.value = formula(cell.value) if cell.value.startswith("=") else text(cell.value)
        for dv in sheet.data_validations.dataValidation:
            dv.formula1 = formula(dv.formula1) if dv.formula1 and not str(dv.formula1).isdigit() and not str(dv.formula1).lstrip("-").isdigit() else dv.formula1
            for attr in ("prompt", "error", "promptTitle", "errorTitle"):
                if getattr(dv, attr):
                    setattr(dv, attr, text(getattr(dv, attr)))
    for it, en in SHEETS.items():
        book[it].title = en
    names = book.defined_names
    for name in list(names):
        defined = names[name]
        defined.attr_text = formula(defined.attr_text)
        new = part(name)
        if new != name:
            del names[name]
            defined.name = new
            names[new] = defined
    book.save(target)


def english_csv(source: Path, target: Path) -> None:
    rows = list(csv.reader(source.open(encoding="utf-8-sig"), delimiter=";"))
    out = []
    for row in rows:
        if row and row[0].startswith("#") and ":" in row[0]:  # "# Titolo: ..."
            key, _, rest = row[0][1:].partition(":")
            out.append([f"# {text(key.strip())}: {text(rest.strip())}".rstrip()] + row[1:])
        else:
            out.append([text(cell) for cell in row])
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, delimiter=";").writerows(out)


def main() -> int:
    english_workbook(DIR / "Ricetta JD-Xi - modello.xlsx", DIR / "JD-Xi recipe - template.xlsx")
    english_csv(DIR / "Ricetta JD-Xi - modello.csv", DIR / "JD-Xi recipe - example.csv")
    english_csv(DIR / "Ricetta JD-Xi - vuota.csv", DIR / "JD-Xi recipe - blank.csv")
    english_csv(DIR / "Parametri ricette JD-Xi.csv", DIR / "JD-Xi recipe parameters.csv")
    print("English recipe files written to", DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
