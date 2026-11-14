#!/usr/bin/env python
"""
Verifica guidata con il JD-Xi collegato (parte automatica del piano di test).

    python scripts/hardware_check.py            # tutta la sequenza
    python scripts/hardware_check.py --list     # solo le porte MIDI
    python scripts/hardware_check.py --auto     # solo i controlli automatici, senza domande

Va eseguita con JD-Xi Studio CHIUSO (le porte MIDI su Windows non si condividono).
I controlli automatici scrivono un valore nell'area temporanea e lo rimettono com'era;
il cambio di programma sostituisce il suono corrente: viene chiesto prima.

Il resoconto va in ~/.jdxi_studio/hardware-checks/<data>-<versione>.md: allegalo
alla verifica del rilascio (doc/hardware-test-plan.md, sezione 1).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROLAND, DEVICE, MODEL = 0x41, 0x10, (0x00, 0x00, 0x00, 0x0E)
RQ1, DT1 = 0x11, 0x12
REPLY_TIMEOUT = 1.5  # s: il JD-Xi risponde in qualche decina di ms

# Aree temporanee (MIDI Implementation del JD-Xi) e un parametro "sicuro" per la prova di scrittura
AREAS = {
    # nome: (indirizzo, dimensione, offset del parametro di prova, nome del parametro, offset del nome)
    "Programma": ((0x18, 0x00, 0x00, 0x00), 0x40, 0x10, "Program Level", 0x00),
    "Digital 1": ((0x19, 0x01, 0x00, 0x00), 0x40, 0x0C, "Tone Level", 0x00),
    "Digital 2": ((0x19, 0x21, 0x00, 0x00), 0x40, 0x0C, "Tone Level", 0x00),
    "Analog": ((0x19, 0x42, 0x00, 0x00), 0x40, 0x2A, "Amp Level", 0x00),
    "Drums": ((0x19, 0x70, 0x00, 0x00), 0x12, 0x0C, "Kit Level", 0x00),
}
# Canali delle parti (0 = canale 1)
CHANNELS = {"Digital 1": 0, "Digital 2": 1, "Analog": 2, "Drums": 9}


# ---------------------------------------------------------------- SysEx
def checksum(body: list[int]) -> int:
    return (128 - sum(body) % 128) % 128


def rq1(address: tuple[int, ...], size: int) -> list[int]:
    """Richiesta di dati (senza F0/F7, come li vuole mido)."""
    body = list(address) + [0, 0, (size >> 7) & 0x7F, size & 0x7F]
    return [ROLAND, DEVICE, *MODEL, RQ1, *body, checksum(body)]


def dt1(address: tuple[int, ...], data: list[int]) -> list[int]:
    body = list(address) + list(data)
    return [ROLAND, DEVICE, *MODEL, DT1, *body, checksum(body)]


def offset_address(address: tuple[int, ...], offset: int) -> tuple[int, ...]:
    value = (address[0] << 21) | (address[1] << 14) | (address[2] << 7) | address[3]
    value += offset
    return ((value >> 21) & 0x7F, (value >> 14) & 0x7F, (value >> 7) & 0x7F, value & 0x7F)


def parse_dt1(data: list[int]) -> Optional[tuple[tuple[int, ...], list[int]]]:
    """(indirizzo, dati) di una risposta DT1 del JD-Xi; None se non lo è o il checksum è sbagliato."""
    if len(data) < 12 or data[0] != ROLAND or tuple(data[2:6]) != MODEL or data[6] != DT1:
        return None
    body = data[7:-1]
    if checksum(body) != data[-1]:
        return None
    return tuple(body[:4]), body[4:]


# ---------------------------------------------------------------- the session
@dataclass
class Result:
    step: str
    outcome: str  # OK, KO, SALTATO, INFO
    note: str = ""


@dataclass
class Session:
    auto_only: bool = False
    results: list[Result] = field(default_factory=list)
    inport: object = None
    outport: object = None

    def record(self, step: str, outcome: str, note: str = "") -> None:
        self.results.append(Result(step, outcome, note))
        mark = {"OK": "✔", "KO": "✘", "SALTATO": "–", "INFO": "ℹ"}.get(outcome, "?")
        print(f"   {mark} {outcome:7s} {step}" + (f" — {note}" if note else ""))

    # ------------------------------------------------------------ I/O
    def send(self, msg) -> None:
        self.outport.send(msg)

    def drain(self) -> None:
        for _ in self.inport.iter_pending():
            pass

    def request(self, address, size) -> Optional[list[int]]:
        """I dati di un'area (le risposte possono arrivare in più messaggi)."""
        import mido

        self.drain()
        self.send(mido.Message("sysex", data=rq1(address, size)))
        collected: dict[int, int] = {}
        start = offset_address(address, 0)
        base = (start[0] << 21) | (start[1] << 14) | (start[2] << 7) | start[3]
        deadline = time.monotonic() + REPLY_TIMEOUT
        while time.monotonic() < deadline and len(collected) < size:
            for msg in self.inport.iter_pending():
                if msg.type != "sysex":
                    continue
                parsed = parse_dt1(list(msg.data))
                if parsed is None:
                    continue
                addr, values = parsed
                first = (addr[0] << 21) | (addr[1] << 14) | (addr[2] << 7) | addr[3]
                for i, value in enumerate(values):
                    if 0 <= first + i - base < size:
                        collected[first + i - base] = value
            time.sleep(0.01)
        if not collected:
            return None
        return [collected.get(i, -1) for i in range(size)]

    # ------------------------------------------------------------ human
    def ask(self, question: str, hint: str = "") -> str:
        """s / n / k (salta); in --auto: SALTATO."""
        if self.auto_only:
            return "k"
        if hint:
            print(f"     ({hint})")
        while True:
            answer = input(f"   ? {question} [s = sì / n = no / k = salta] ").strip().lower()
            if answer in ("s", "si", "sì", "y", "n", "k"):
                return {"si": "s", "sì": "s", "y": "s"}.get(answer, answer)

    def pause(self, text: str) -> None:
        if not self.auto_only:
            input(f"   ⏎ {text} — premi Invio quando sei pronto ")

    def human_check(self, step: str, question: str, hint: str = "") -> None:
        answer = self.ask(question, hint)
        if answer == "k":
            self.record(step, "SALTATO")
            return
        note = ""
        if answer == "n" and not self.auto_only:
            note = input("     Cosa hai notato? ").strip()
        self.record(step, "OK" if answer == "s" else "KO", note)


# ---------------------------------------------------------------- steps
def open_ports(session: Session, wanted: str) -> bool:
    import mido

    inputs, outputs = mido.get_input_names(), mido.get_output_names()
    inp = next((n for n in inputs if wanted.lower() in n.lower()), None)
    out = next((n for n in outputs if wanted.lower() in n.lower()), None)
    if not inp or not out:
        session.record("Porte MIDI del JD-Xi", "KO", f"ingressi {inputs}, uscite {outputs}")
        return False
    session.inport, session.outport = mido.open_input(inp), mido.open_output(out)
    session.record("Porte MIDI del JD-Xi", "OK", f"in «{inp}», out «{out}»")
    return True


def identity(session: Session) -> None:
    import mido

    session.drain()
    session.send(mido.Message("sysex", data=[0x7E, 0x7F, 0x06, 0x01]))
    deadline = time.monotonic() + REPLY_TIMEOUT
    while time.monotonic() < deadline:
        for msg in session.inport.iter_pending():
            data = list(getattr(msg, "data", []))
            if msg.type == "sysex" and data[:4] in ([0x7E, DEVICE, 0x06, 0x02], [0x7E, 0x7F, 0x06, 0x02]):
                ok = len(data) > 6 and data[4] == ROLAND and data[5:7] == [0x0E, 0x03]
                version = ".".join(str(b) for b in data[9:13]) if len(data) >= 13 else "?"
                session.record("Identity Request", "OK" if ok else "KO", f"risposta {data[4:9]}, firmware {version}")
                return
        time.sleep(0.01)
    session.record("Identity Request", "KO", "nessuna risposta (cavo USB? driver Roland?)")


def tone_name(values: list[int], offset: int, length: int = 12) -> str:
    chars = values[offset:offset + length]
    return "".join(chr(c) if 32 <= c < 127 else "·" for c in chars).rstrip()


def read_areas(session: Session) -> dict[str, list[int]]:
    found = {}
    for name, (address, size, _off, _p, name_off) in AREAS.items():
        values = session.request(address, size)
        if values is None:
            session.record(f"Lettura area {name}", "KO", "nessuna risposta all'RQ1")
            continue
        missing = values.count(-1)
        found[name] = values
        session.record(
            f"Lettura area {name}",
            "OK" if missing == 0 else "KO",
            f"«{tone_name(values, name_off)}»" + (f", {missing} byte mancanti" if missing else ""),
        )
    return found


def write_read_back(session: Session, found: dict[str, list[int]]) -> None:
    import mido

    for name, (address, _size, off, param, _n) in AREAS.items():
        if name not in found:
            session.record(f"Scrittura {name} › {param}", "SALTATO", "area non letta")
            continue
        original = found[name][off]
        trial = original - 5 if original >= 5 else original + 5
        target = offset_address(address, off)
        session.send(mido.Message("sysex", data=dt1(target, [trial])))
        time.sleep(0.08)
        got = session.request(target, 1)
        session.send(mido.Message("sysex", data=dt1(target, [original])))  # com'era
        time.sleep(0.08)
        back = session.request(target, 1)
        ok = got == [trial] and back == [original]
        session.record(
            f"Scrittura {name} › {param}",
            "OK" if ok else "KO",
            f"{original} → {trial}: letto {got}; ripristino letto {back}",
        )


def play(session: Session, channel: int, notes=(60, 64, 67), velocity=100, length=0.35) -> None:
    import mido

    for note in notes:
        session.send(mido.Message("note_on", channel=channel, note=note, velocity=velocity))
        time.sleep(length)
        session.send(mido.Message("note_off", channel=channel, note=note, velocity=0))
        time.sleep(0.05)


def listening(session: Session, found: dict[str, list[int]]) -> None:
    import mido

    session.pause("Alza il volume del JD-Xi (o le cuffie) a un livello comodo")
    for name, channel in CHANNELS.items():
        notes = (36, 38, 42, 46) if name == "Drums" else (60, 64, 67)
        play(session, channel, notes)
        session.human_check(
            f"Suono {name} (canale {channel + 1})",
            f"Hai sentito {name} suonare {'kick, snare e charleston' if name == 'Drums' else 'tre note (do, mi, sol)'}?",
        )
    # volume: the level written, then put back
    address, _size, off, _param, _n = AREAS["Digital 1"]
    if "Digital 1" in found:
        original = found["Digital 1"][off]
        target = offset_address(address, off)
        session.send(mido.Message("sysex", data=dt1(target, [max(0, original // 4)])))
        time.sleep(0.1)
        play(session, CHANNELS["Digital 1"])
        session.send(mido.Message("sysex", data=dt1(target, [original])))
        time.sleep(0.1)
        play(session, CHANNELS["Digital 1"])
        session.human_check(
            "Livello Digital 1 via SysEx",
            "La prima volta più piano, la seconda al volume normale?",
        )
    # controller: cutoff via CC 74 on Digital 1, then back
    session.send(mido.Message("control_change", channel=0, control=74, value=20))
    play(session, 0)
    session.send(mido.Message("control_change", channel=0, control=74, value=64))
    play(session, 0)
    session.human_check(
        "Cutoff Digital 1 via CC 74",
        "La prima volta più cupo, la seconda più brillante?",
        "se il suono ha il filtro aperto al massimo la differenza può essere piccola",
    )


def program_change(session: Session) -> None:
    import mido

    answer = session.ask(
        "Provo un cambio di programma (A01, poi A02)? Il suono corrente non salvato si perde",
        "rispondi n se sul JD-Xi c'è qualcosa da salvare con WRITE",
    )
    if answer != "s":
        session.record("Cambio di programma", "SALTATO")
        return
    names = []
    for program in (0, 1):  # A01, A02 (banco preset: MSB 85, LSB 64)
        session.send(mido.Message("control_change", channel=15, control=0, value=85))
        session.send(mido.Message("control_change", channel=15, control=32, value=64))
        session.send(mido.Message("program_change", channel=15, program=program))
        time.sleep(0.6)
        values = session.request(AREAS["Programma"][0], AREAS["Programma"][1])
        names.append(tone_name(values, 0) if values else None)
    ok = all(names) and names[0] != names[1]
    session.record("Cambio di programma (A01 → A02)", "OK" if ok else "KO", f"nomi letti {names}")
    session.human_check("Display del JD-Xi", "Il display del JD-Xi mostra il programma A02?")


# ---------------------------------------------------------------- report
def write_report(session: Session) -> Path:
    from jdxi_editor.project import __data_name__, release_name

    folder = Path.home() / f".{__data_name__}" / "hardware-checks"
    folder.mkdir(parents=True, exist_ok=True)
    now = _dt.datetime.now()
    path = folder / f"{now:%Y-%m-%d-%H%M}-{release_name()}.md"
    counts = {k: sum(1 for r in session.results if r.outcome == k) for k in ("OK", "KO", "SALTATO")}
    lines = [
        f"# Verifica hardware automatica — {release_name()}",
        "",
        f"{now:%d/%m/%Y %H:%M} · OK {counts['OK']} · KO {counts['KO']} · saltati {counts['SALTATO']}",
        "",
        "| Passo | Esito | Note |",
        "|---|---|---|",
    ]
    lines += [f"| {r.step} | {r.outcome} | {r.note.replace('|', '/')} |" for r in session.results]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="mostra le porte MIDI ed esci")
    parser.add_argument("--auto", action="store_true", help="solo i controlli automatici")
    parser.add_argument("--port", default="JD-Xi", help="parte del nome delle porte (default JD-Xi)")
    args = parser.parse_args(argv)

    import mido

    if args.list:
        print("Ingressi:", mido.get_input_names())
        print("Uscite:  ", mido.get_output_names())
        return 0

    session = Session(auto_only=args.auto)
    print("\nJD-Xi Studio — verifica con lo strumento collegato")
    print("Chiudi JD-Xi Studio prima di continuare: le porte MIDI non si condividono.\n")
    print("1. Collegamento")
    if not open_ports(session, args.port):
        print(f"\nResoconto: {write_report(session)}")
        return 1
    try:
        identity(session)
        print("\n2. Lettura delle aree temporanee (RQ1 → DT1)")
        found = read_areas(session)
        print("\n3. Scrittura e rilettura (il valore viene poi rimesso com'era)")
        write_read_back(session, found)
        if not args.auto:
            print("\n4. Ascolto (le note le manda questo script)")
            listening(session, found)
            print("\n5. Cambio di programma")
            program_change(session)
    finally:
        for port in (session.inport, session.outport):
            try:
                port.close()
            except Exception:
                pass
    path = write_report(session)
    ko = sum(1 for r in session.results if r.outcome == "KO")
    print(f"\n{'Tutto a posto' if not ko else f'{ko} controlli KO'}. Resoconto: {path}")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())
