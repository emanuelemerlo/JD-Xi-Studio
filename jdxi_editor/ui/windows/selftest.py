"""
jdxi_editor.ui.windows.selftest
Self-test with the JD-Xi: the app plays the user.

Help › Self-test with the JD-Xi… runs a sequence of what a user does — load a
program, choose tones, edit a value and undo it, change the octave, play a
note — through the app's own windows and functions, and checks each result:
by reading the value back from the JD-Xi when it can, by asking you when only
ears or eyes can tell (a note heard, a LED on the panel), and by waiting for
the app to follow when you act on the JD-Xi (a tone chosen, OCTAVE, keys).

At the end the program loaded at the start is loaded again, and a report
(Markdown) is saved in ~/.jdxi_studio/reports to be sent with a bug report.

Steps are generators: they yield what they wait for (`Wait`, `Read`, `Ask`,
`Until`) and return (status, detail). The runner drives them with timers, so
the windows stay live (the follower, the editors) while a step waits.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Generator, List, Optional

from decologr import Decologr as log
from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.io.device import device_for
from jdxi_editor.ui.windows.jdxi.follow import parse_dt1

OK, KO, SKIPPED, ASKED = "OK", "KO", "SKIPPED", "ASKED"
READ_TIMEOUT_MS = 1500
REPORTS = Path.home() / ".jdxi_studio" / "reports"

# Addresses read back
PROGRAM_COMMON = (0x18, 0x00, 0x00, 0x00)
ANALOG_TONE = (0x19, 0x42, 0x00, 0x00)
DIGITAL1_COMMON = (0x19, 0x01, 0x00, 0x00)
ANALOG_CUTOFF = (0x19, 0x42, 0x00, 0x21)
ANALOG_OCTAVE = (0x19, 0x42, 0x00, 0x34)
SYSTEM_COMMON = (0x02, 0x00, 0x00, 0x00)


# ---------------------------------------------------------------- what steps wait for
@dataclass
class Wait:
    ms: int


@dataclass
class Read:
    address: tuple
    size: int
    timeout_ms: int = READ_TIMEOUT_MS


@dataclass
class Ask:
    question: str
    hint: str = ""


@dataclass
class Until:
    predicate: Callable[[], bool]
    timeout_ms: int
    prompt: str = ""  # shown while waiting (what to do on the JD-Xi)


@dataclass
class Step:
    title: str
    run: Callable[["SelfTest"], Generator]
    status: str = ""
    detail: str = ""


def rq1(address: tuple, size: int) -> list:
    """A Roland RQ1 (data request) for *size* bytes at *address*."""
    size_bytes = [(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F]
    body = list(address) + size_bytes
    checksum = (128 - sum(body) % 128) % 128
    return [0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x11] + body + [checksum, 0xF7]


def absolute(address) -> int:
    """A 4-byte Roland address as one number (7 bits a byte)."""
    a = list(address)
    return (a[0] << 21) | (a[1] << 14) | (a[2] << 7) | a[3]


def name_of(values: Optional[list]) -> Optional[str]:
    if not values or len(values) < 12:
        return None
    return "".join(chr(v) for v in values[:12]).strip()


def same_name(a: Optional[str], b: Optional[str]) -> bool:
    """Names as the JD-Xi stores them (12 characters) and as the lists write them."""
    if not a or not b:
        return False
    norm = lambda s: "".join(s.lower().split())[:12]  # noqa: E731
    return norm(a)[: len(norm(b))] == norm(b)[: len(norm(a))] and min(len(norm(a)), len(norm(b))) >= 3


# ---------------------------------------------------------------- the runner
class SelfTest(QObject):
    """Runs the steps on a window; tells the dialog what happens."""

    step_started = Signal(int)
    step_finished = Signal(int, str, str)
    asking = Signal(str, str)  # question, hint ("" when the question is over)
    waiting = Signal(str)  # what to do on the JD-Xi ("" when done)
    finished = Signal()

    def __init__(self, window, steps: Optional[List[Step]] = None, parent=None):
        super().__init__(parent)
        self.window = window
        self.helper = window.midi_helper
        self.steps = steps if steps is not None else default_steps()
        self.index = -1
        self.started_at = ""
        self.restore_program_id: Optional[str] = None
        self.notes_seen = 0
        self._gen = None
        self._pending = None  # what the step waits for
        self._reply: Optional[list] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._timeout)
        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._check_until)
        self._until_deadline = 0.0
        self.running = False
        self.sent: dict = {}  # absolute address -> byte, from the DT1s the app sends
        self.helper.midi_message_incoming.connect(self._incoming)
        self.helper.midi_message_outgoing.connect(self._outgoing)

    # --- control
    def start(self) -> None:
        self.running = True
        self.started_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.index = -1
        for step in self.steps:
            step.status, step.detail = "", ""
        self._next_step()

    def stop(self) -> None:
        if not self.running:
            return
        if 0 <= self.index < len(self.steps) and not self.steps[self.index].status:
            self._finish_step(SKIPPED, tr("stopped"))
        self._end()

    def answer(self, value: Optional[bool]) -> None:
        """The user's answer to an Ask: True (yes), False (no), None (skip)."""
        if isinstance(self._pending, Ask):
            self._pending = None
            self.asking.emit("", "")
            self._send(value)

    # --- driving the current step
    def _next_step(self) -> None:
        self.index += 1
        if not self.running or self.index >= len(self.steps):
            self._end()
            return
        step = self.steps[self.index]
        self.step_started.emit(self.index)
        try:
            self._gen = step.run(self)
        except Exception as ex:  # a step that cannot start
            self._finish_step(KO, f"{type(ex).__name__}: {ex}")
            QTimer.singleShot(0, self, self._next_step)
            return
        self._send(None)

    def _send(self, value) -> None:
        if self._gen is None:
            return
        try:
            command = self._gen.send(value)
        except StopIteration as stop:
            status, detail = stop.value if stop.value else (OK, "")
            self._finish_step(status, detail)
            QTimer.singleShot(0, self, self._next_step)
            return
        except Exception as ex:
            log.error(f"Self-test step failed: {ex}", scope="SelfTest")
            self._finish_step(KO, f"{type(ex).__name__}: {ex}")
            QTimer.singleShot(0, self, self._next_step)
            return
        self._pending = command
        if isinstance(command, Wait):
            self._timer.start(max(0, command.ms))
        elif isinstance(command, Read):
            self._reply = None
            try:
                device_for(self.helper).request([rq1(command.address, command.size)])
            except Exception as ex:
                log.error(f"Self-test request failed: {ex}", scope="SelfTest")
            self._timer.start(command.timeout_ms)
        elif isinstance(command, Ask):
            self.asking.emit(command.question, command.hint)
        elif isinstance(command, Until):
            self._until_deadline = time.monotonic() + command.timeout_ms / 1000
            self.waiting.emit(command.prompt)
            self._poll.start()
        else:
            self._pending = None
            self._send(None)

    def _timeout(self) -> None:
        command, self._pending = self._pending, None
        if isinstance(command, Wait):
            self._send(None)
        elif isinstance(command, Read):
            self._send(None)  # no reply

    def _check_until(self) -> None:
        command = self._pending
        if not isinstance(command, Until):
            self._poll.stop()
            return
        try:
            met = bool(command.predicate())
        except Exception:
            met = False
        if met or time.monotonic() >= self._until_deadline:
            self._poll.stop()
            self._pending = None
            self.waiting.emit("")
            self._send(met)

    def _incoming(self, message) -> None:
        kind = getattr(message, "type", None)
        if kind == "note_on" and getattr(message, "velocity", 0) > 0:
            self.notes_seen += 1
        if kind != "sysex" or not isinstance(self._pending, Read):
            return
        parsed = parse_dt1(message.data)
        if parsed is None or parsed[0] != tuple(self._pending.address):
            return
        self._timer.stop()
        self._pending = None
        # later, not inside the delivery of the reply: what the step does next
        # (an edit, an Undo) must not be taken for an echo of received data
        QTimer.singleShot(0, self, lambda values=parsed[1]: self._send(values))

    def _outgoing(self, message) -> None:
        """Record what the app writes to the JD-Xi (to compare with what it then holds)."""
        try:
            data = [int(b) for b in (message.bytes() if hasattr(message, "bytes") else message)]
        except (TypeError, ValueError):
            return
        parsed = parse_dt1(data)
        if parsed is None:
            return
        base = absolute(parsed[0])
        for i, value in enumerate(parsed[1]):
            self.sent[base + i] = value

    def _finish_step(self, status: str, detail: str) -> None:
        step = self.steps[self.index]
        step.status, step.detail = status, detail
        self._gen = None
        self.step_finished.emit(self.index, status, detail)

    def _end(self) -> None:
        self._timer.stop()
        self._poll.stop()
        self._pending = None
        self._gen = None
        if self.running:
            self.running = False
            try:  # the test's edits (undone) are not the user's: no «unsaved» question
                from jdxi_editor.ui.v2.history import mark_all_saved

                mark_all_saved()
            except Exception:
                pass
            self.asking.emit("", "")
            self.waiting.emit("")
            self.finished.emit()

    # --- the report
    def report(self) -> str:
        from jdxi_editor.project import __display_name__, __version__

        counts = {s: sum(1 for st in self.steps if st.status == s) for s in (OK, KO, SKIPPED)}
        lines = [
            f"# {tr('Self-test with the JD-Xi')}",
            "",
            f"{__display_name__} {__version__} · {self.started_at}",
            "",
            f"OK {counts[OK]} · KO {counts[KO]} · {tr('skipped')} {counts[SKIPPED]}",
            "",
            f"| # | {tr('Step')} | {tr('Result')} | {tr('Detail')} |",
            "|---|---|---|---|",
        ]
        for i, step in enumerate(self.steps, 1):
            detail = step.detail.replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {step.title} | {step.status or '—'} | {detail} |")
        return "\n".join(lines) + "\n"

    def save_report(self, folder: Path = REPORTS) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"selftest-{datetime.now():%Y%m%d-%H%M%S}.md"
        path.write_text(self.report(), encoding="utf-8")
        return path


# ---------------------------------------------------------------- the steps
def _program_editor(window):
    return window._tab_editor("program")


def _analog_editor(window):
    return window._tab_editor("analog")


def step_connection(test: SelfTest):
    """The JD-Xi answers a data request (the current program's name)."""
    values = yield Read(PROGRAM_COMMON, 0x24)
    name = name_of(values)
    if name is None:
        return KO, tr("no reply: check the MIDI ports (Edit › MIDI Configuration) and the USB cable")
    # the program to load again at the end
    editor = _program_editor(test.window)
    match = next((p for p in getattr(editor.library, "programs", []) if same_name(p.name, name)), None)
    test.restore_program_id = match.id if match else None
    return OK, tr("current program «{name}»").format(name=name)


def step_system(test: SelfTest):
    """SYSTEM › MIDI: where the JD-Xi takes program changes."""
    values = yield Read(SYSTEM_COMMON, 0x2B)
    if not values or len(values) < 0x2B:
        return KO, tr("no reply")
    channel, rx_pc, rx_bank = values[0x11], values[0x29], values[0x2A]
    channel_text = "OFF" if channel >= 16 else str(channel + 1)
    detail = f"Program Ctrl Ch {channel_text}, Rx Program Change {'ON' if rx_pc else 'OFF'}, Rx Bank Select {'ON' if rx_bank else 'OFF'}"
    if channel >= 16 or not rx_pc or not rx_bank:
        return KO, detail + " — " + tr("on the JD-Xi: MENU › SYSTEM › MIDI")
    if channel in (0, 1, 2, 9):
        return OK, detail + " — " + tr("a part's channel too: 16 is safer")
    return OK, detail


def step_load_program(test: SelfTest):
    """Programs tab: choose a program in the library and Load it."""
    from jdxi_editor.ui.v2.history import paused

    editor = _program_editor(test.window)
    programs = getattr(editor.library, "programs", [])
    target = next((p for p in programs if p.id == "A02"), None) or (programs[1] if len(programs) > 1 else None)
    if target is None:
        return SKIPPED, tr("no program in the library")
    editor.library.select(target.id)
    with paused():  # no «unsaved changes» question: asked at the start
        editor.load_selected_program()
    name = None
    for _ in range(8):  # the JD-Xi needs a moment to load it
        yield Wait(400)
        name = name_of((yield Read(PROGRAM_COMMON, 0x24)))
        if same_name(name, target.name):
            break
    if not same_name(name, target.name):
        return KO, tr("loaded {id} «{expected}», the JD-Xi has «{found}»").format(
            id=target.id, expected=target.name, found=name or "?"
        )
    return OK, f"{target.id} «{name}»"


def step_display_follows_program(test: SelfTest):
    """The keyboard window's display shows the program loaded."""
    yield Wait(1500)
    name = getattr(test.window, "current_program_name", "") or ""
    loaded = name_of((yield Read(PROGRAM_COMMON, 0x24)))
    if same_name(name, loaded):
        return OK, f"«{name}»"
    return KO, tr("display «{shown}», JD-Xi «{loaded}»").format(shown=name, loaded=loaded or "?")


def step_analog_tone(test: SelfTest):
    """Analog tab: choose the 4th preset and Load it."""
    from jdxi_editor.ui.v2.history import paused

    window = test.window
    window._select_synth(window_synth("ANALOG_SYNTH"))
    editor = _analog_editor(window)
    panel = editor.instrument_preset
    combo = panel.instrument_selection_combo.combo_box
    if combo.count() < 4:
        return SKIPPED, tr("no Analog presets")
    combo.setCurrentIndex(3)
    expected = combo.currentText().split(" - ", 1)[-1]
    with paused():
        panel._on_load_preset()
    name = None
    for _ in range(6):
        yield Wait(400)
        name = name_of((yield Read(ANALOG_TONE, 0x40)))
        if same_name(name, expected):
            break
    if not same_name(name, expected):
        return KO, tr("loaded «{expected}», the JD-Xi has «{found}»").format(expected=expected, found=name or "?")
    return OK, f"«{name}»"


def step_digital_tone_arrows(test: SelfTest):
    """Keyboard window: Digital 1, then the tone › arrow."""
    from jdxi_editor.ui.v2.history import paused

    window = test.window
    window._select_synth(window_synth("DIGITAL_SYNTH_1"))
    presets = window.preset_manager.get_presets_for_synth(window.current_synth_type)
    window.current_preset_index = 0
    with paused():
        window._preset_next()
    expected = str(presets[1]).split(":", 1)[-1].strip()
    name = None
    for _ in range(6):
        yield Wait(400)
        name = name_of((yield Read(DIGITAL1_COMMON, 0x40)))
        if same_name(name, expected):
            break
    if not same_name(name, expected):
        return KO, tr("shown «{expected}», the JD-Xi has «{found}»").format(expected=expected, found=name or "?")
    return OK, f"«{name}»"


def step_edit_and_undo(test: SelfTest):
    """Analog editor: change Cutoff, then Undo; the JD-Xi follows both."""
    from jdxi_editor.midi.data.parameter.analog.address import AnalogParam

    window = test.window
    window._select_synth(window_synth("ANALOG_SYNTH"))
    editor = _analog_editor(window)
    pv = editor.values[AnalogParam.FILTER_CUTOFF]
    before = pv.value()
    target = 20 if before > 64 else 110
    pv.setValue(target)
    yield Wait(400)
    sent = yield Read(ANALOG_CUTOFF, 1)
    if not sent or sent[0] != target:
        return KO, tr("Cutoff set to {value}, the JD-Xi has {found}").format(value=target, found=sent[0] if sent else "?")
    if not editor.history.undo():
        return KO, tr("Undo did nothing")
    yield Wait(400)
    back = yield Read(ANALOG_CUTOFF, 1)
    if not back or back[0] != before:
        return KO, tr("after Undo the JD-Xi has {found}, expected {value}").format(found=back[0] if back else "?", value=before)
    return OK, f"Cutoff {before} → {target} → {before}"


def step_octave(test: SelfTest):
    """Keyboard window: Octave + on Analog, then back."""
    window = test.window
    window._select_synth(window_synth("ANALOG_SYNTH"))
    start = getattr(window, "current_octave", 0)
    window.current_octave = 0
    window._midi_send_octave(+1)
    yield Wait(300)
    up = yield Read(ANALOG_OCTAVE, 1)
    window._midi_send_octave(-1)
    yield Wait(300)
    back = yield Read(ANALOG_OCTAVE, 1)
    window.current_octave = start
    window._ui_update_octave()
    if not up or up[0] != 0x41:
        return KO, tr("Octave + : the JD-Xi has {found}").format(found=(up[0] - 0x40) if up else "?")
    if not back or back[0] != 0x40:
        return KO, tr("Octave back: the JD-Xi has {found}").format(found=(back[0] - 0x40) if back else "?")
    return OK, "0 → +1 → 0"


def step_note(test: SelfTest):
    """The on-screen keyboard plays a note (you listen)."""
    window = test.window
    window._select_synth(window_synth("ANALOG_SYNTH"))
    window.handle_piano_note_on(60)
    yield Wait(600)
    window.handle_piano_note_off(60)
    heard = yield Ask(tr("Did the JD-Xi play a note (middle C, Analog)?"), tr("turn the volume up"))
    if heard is None:
        return SKIPPED, ""
    return (OK, "") if heard else (KO, tr("no sound"))


def step_tone_on_jdxi(test: SelfTest):
    """You choose a tone on the JD-Xi: the display follows."""
    window = test.window
    window._select_synth(window_synth("ANALOG_SYNTH"))
    synth = window.current_synth_type
    before = window.preset_manager.current_preset_names.get(synth)
    changed = yield Until(
        lambda: window.preset_manager.current_preset_names.get(synth) != before,
        20000,
        tr("On the JD-Xi: select ANALOG and turn the TONE knob (20 seconds)"),
    )
    after = window.preset_manager.current_preset_names.get(synth)
    if changed:
        return OK, f"«{before}» → «{after}»"
    return KO, tr("the display still shows «{name}»").format(name=before)


def step_octave_on_jdxi(test: SelfTest):
    """You press OCTAVE on the JD-Xi: the window's Octave buttons follow."""
    window = test.window
    before = getattr(window, "current_octave", 0)
    changed = yield Until(
        lambda: getattr(window, "current_octave", 0) != before,
        15000,
        tr("On the JD-Xi: press OCTAVE + or − (15 seconds)"),
    )
    after = getattr(window, "current_octave", 0)
    if changed:
        return OK, f"{before:+d} → {after:+d}"
    return KO, tr("the window still shows {octave:+d}").format(octave=before)


def step_keys_on_jdxi(test: SelfTest):
    """You play on the JD-Xi: the notes arrive and the window's keys light."""
    test.notes_seen = 0
    played = yield Until(
        lambda: test.notes_seen >= 3,
        15000,
        tr("On the JD-Xi: play a few notes (15 seconds)"),
    )
    if not played:
        return KO, tr("no notes received: on the JD-Xi, MENU › SYSTEM › MIDI › Tx")
    lit = yield Ask(tr("Did the keys you played light up in the keyboard window?"))
    if lit is None:
        return OK, tr("{n} notes received").format(n=test.notes_seen)
    return (OK, tr("{n} notes received").format(n=test.notes_seen)) if lit else (KO, tr("notes received, keys not lit"))


def step_restore(test: SelfTest):
    """The program from the start loaded again."""
    from jdxi_editor.ui.v2.history import mark_all_saved, paused

    program_id = test.restore_program_id
    if not program_id:
        return SKIPPED, tr("the starting program is not in the library: choose it on the JD-Xi")
    editor = _program_editor(test.window)
    editor.library.select(program_id)
    with paused():
        editor.load_selected_program()
    yield Wait(1500)
    mark_all_saved()  # the test's edits are not the user's
    return OK, program_id


# The edits a user makes to a free user tone (Init Tone): parameters of the
# oscillator, filter, amp, envelopes and LFO, each set to another value.
ANALOG_EDITS = (
    "OSC_WAVEFORM", "OSC_PITCH_COARSE", "OSC_PULSE_WIDTH", "FILTER_CUTOFF", "FILTER_RESONANCE",
    "FILTER_ENV_DEPTH", "FILTER_ENV_DECAY_TIME", "AMP_LEVEL", "AMP_ENV_ATTACK_TIME",
    "AMP_ENV_RELEASE_TIME", "LFO_RATE", "LFO_PITCH_DEPTH",
)
DIGITAL_EDITS = (
    ("PARTIAL_1", "OSC_WAVE"), ("PARTIAL_1", "OSC_PITCH"), ("PARTIAL_1", "FILTER_MODE"),
    ("PARTIAL_1", "FILTER_CUTOFF"), ("PARTIAL_1", "FILTER_RESONANCE"), ("PARTIAL_1", "FILTER_ENV_DEPTH"),
    ("PARTIAL_1", "AMP_LEVEL"), ("PARTIAL_1", "AMP_ENV_ATTACK_TIME"), ("PARTIAL_1", "AMP_ENV_RELEASE_TIME"),
    ("PARTIAL_1", "LFO_RATE"), ("PARTIAL_1", "LFO_PITCH_DEPTH"), ("COMMON", "PORTAMENTO_SWITCH"),
    ("COMMON", "PARTIAL2_SWITCH"),
)
INIT_TONE = "Init Tone"


def another_value(pv) -> int:
    """A value a user would choose: inside the range, not the one it has."""
    lo, hi, current = pv.minimum, pv.maximum, pv.value()
    for fraction in (0.3, 0.7, 0.5, 0.1, 0.9):
        value = lo + round((hi - lo) * fraction)
        if value != current:
            return value
    return hi if current != hi else lo


def _edits_of(part: str, editor) -> tuple[list, list]:
    """(the ParamValues to edit, the blocks (address, size) that hold them)."""
    if part == "ANALOG_SYNTH":
        from jdxi_editor.midi.data.parameter.analog.address import AnalogParam

        pvs = [editor.values[getattr(AnalogParam, n)] for n in ANALOG_EDITS
               if getattr(AnalogParam, n, None) in editor.values]
        return pvs, [(ANALOG_TONE, 0x40)]
    pvs, blocks = [], []
    for key, name in DIGITAL_EDITS:
        try:
            pvs.append(editor.pv(name, key))
        except KeyError:
            continue
    for block in editor.blocks:
        if block.key in {key for key, _ in DIGITAL_EDITS}:
            blocks.append((tuple(block.address_bytes()), block.size()))
    return pvs, blocks


def tone_edits(part: str, editor_key: str, panel_name: str):
    """A free user tone (Init Tone) of *part*: edits through its editor, checked on the
    JD-Xi; then Undo of every edit, checked too."""

    def step(test: SelfTest):
        window = test.window
        synth = window_synth(part)
        window._select_synth(synth)
        editor = window._tab_editor(editor_key)
        pvs, blocks = _edits_of(part, editor)
        if not pvs:
            return SKIPPED, tr("no parameters to edit")
        common = blocks[0] if part == "ANALOG_SYNTH" else (DIGITAL1_COMMON, 0x40)

        # 1. a free user tone, chosen on the JD-Xi (the user tones are where Init Tone is)
        name = name_of((yield Read(*common)))
        on_init = same_name(name, INIT_TONE)
        if not on_init:
            current = {"name": name}

            def chosen():
                return same_name(window.preset_manager.current_preset_names.get(synth), INIT_TONE)

            on_init = yield Until(
                chosen, 40000,
                tr("On the JD-Xi: select {part} and choose a free user tone («Init Tone») "
                   "with the TONE knob (40 seconds)").format(part=panel_name),
            )
            if on_init:
                yield Wait(800)
            name = name_of((yield Read(*common))) or current["name"]
        # 2. the tone as it is
        before = {}
        for address, size in blocks:
            values = yield Read(address, size)
            if not values:
                return KO, tr("no reply")
            base = absolute(address)
            before.update({base + i: v for i, v in enumerate(values)})
        # 3. the edits, one by one as by hand
        test.sent.clear()
        history = editor.history
        made = 0
        for pv in pvs:
            pv.setValue(another_value(pv))
            made += 1
            yield Wait(150)
        yield Wait(500)
        sent = dict(test.sent)
        if not sent:
            return KO, tr("the edits sent nothing to the JD-Xi")
        after = {}
        for address, size in blocks:
            values = yield Read(address, size)
            base = absolute(address)
            after.update({base + i: v for i, v in enumerate(values or [])})
        wrong = [f"{a:07X}: {v}/{after.get(a, '?')}" for a, v in sent.items() if after.get(a) != v]
        if wrong:
            return KO, tr("{n} of {total} values not on the JD-Xi (sent/read): {list}").format(
                n=len(wrong), total=len(sent), list=", ".join(wrong[:6]))
        # 4. Undo every edit
        undone = 0
        while undone < made and history.undo():
            undone += 1
            yield Wait(120)
        yield Wait(500)
        restored = {}
        for address, size in blocks:
            values = yield Read(address, size)
            base = absolute(address)
            restored.update({base + i: v for i, v in enumerate(values or [])})
        back = [f"{a:07X}: {before.get(a)}/{restored.get(a, '?')}" for a in sent if restored.get(a) != before.get(a)]
        where = f"«{name}»" if name else "?"
        if not on_init:
            where += " — " + tr("not a free user tone")
        if undone < made:
            return KO, tr("{where}: {n} edits checked; Undo undid {u} of {made}").format(
                where=where, n=len(sent), u=undone, made=made)
        if back:
            return KO, tr("{where}: {n} edits checked; after Undo {k} values differ (before/now): {list}").format(
                where=where, n=len(sent), k=len(back), list=", ".join(back[:6]))
        return OK, tr("{where}: {made} edits ({n} values) on the JD-Xi, all undone").format(
            where=where, made=made, n=len(sent))

    return step


def window_synth(name: str):
    from jdxi_editor.core.synth.type import JDXiSynth

    return getattr(JDXiSynth, name)


def default_steps() -> List[Step]:
    return [
        Step(tr("Connection: the JD-Xi answers"), step_connection),
        Step(tr("SYSTEM › MIDI settings"), step_system),
        Step(tr("Programs: load a program"), step_load_program),
        Step(tr("Display: shows the program"), step_display_follows_program),
        Step(tr("Analog: load a preset"), step_analog_tone),
        Step(tr("Keyboard window: tone arrow (Digital 1)"), step_digital_tone_arrows),
        Step(tr("Analog editor: edit and Undo"), step_edit_and_undo),
        Step(tr("Analog: edits to an Init Tone, then Undo"), tone_edits("ANALOG_SYNTH", "analog", "ANALOG")),
        Step(tr("Digital 1: edits to an Init Tone, then Undo"), tone_edits("DIGITAL_SYNTH_1", "digital1", "DIGITAL 1")),
        Step(tr("Octave + and back"), step_octave),
        Step(tr("On-screen keyboard: a note"), step_note),
        Step(tr("JD-Xi → app: a tone chosen on the JD-Xi"), step_tone_on_jdxi),
        Step(tr("JD-Xi → app: OCTAVE"), step_octave_on_jdxi),
        Step(tr("JD-Xi → app: notes and keys"), step_keys_on_jdxi),
        Step(tr("The starting program again"), step_restore),
    ]


# ---------------------------------------------------------------- the dialog
STATUS_TEXT = {OK: "✔ OK", KO: "✖ KO", SKIPPED: "– ", ASKED: "?"}
STATUS_COLOUR = {OK: "#6fcf97", KO: "#eb5757", SKIPPED: "#9aa0a6"}


class SelfTestDialog(QDialog):
    """Help › Self-test with the JD-Xi…"""

    def __init__(self, window, parent: Optional[QWidget] = None):
        super().__init__(parent or window)
        self.setWindowTitle(tr("Self-test with the JD-Xi"))
        self.resize(820, 620)
        self.test = SelfTest(window, parent=self)
        self.report_path: Optional[Path] = None

        intro = QLabel(
            tr(
                "The app does what a user does — loads a program and tones, edits a value "
                "and undoes it, changes the octave, plays a note — and checks each result "
                "on the JD-Xi. Some steps ask you to listen, look or act on the JD-Xi.\n"
                "The sound on the JD-Xi is replaced: save it there first (WRITE) if you "
                "want to keep it. The starting program is loaded again at the end."
            )
        )
        intro.setWordWrap(True)

        self.table = QTableWidget(len(self.test.steps), 3)
        self.table.setHorizontalHeaderLabels([tr("Step"), tr("Result"), tr("Detail")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        head.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for row, step in enumerate(self.test.steps):
            self.table.setItem(row, 0, QTableWidgetItem(step.title))
            self.table.setItem(row, 1, QTableWidgetItem(""))
            self.table.setItem(row, 2, QTableWidgetItem(""))

        # the question (or what to do on the JD-Xi) and its answers
        self.prompt = QLabel()
        self.prompt.setWordWrap(True)
        self.prompt.setStyleSheet("font-weight: bold; padding: 6px;")
        self.prompt.hide()
        self.yes_button = QPushButton(tr("Yes"))
        self.no_button = QPushButton(tr("No"))
        self.skip_button = QPushButton(tr("Skip"))
        self.yes_button.clicked.connect(lambda: self.test.answer(True))
        self.no_button.clicked.connect(lambda: self.test.answer(False))
        self.skip_button.clicked.connect(lambda: self.test.answer(None))
        answers = QHBoxLayout()
        answers.addStretch()
        for button in (self.yes_button, self.no_button, self.skip_button):
            button.hide()
            answers.addWidget(button)

        self.summary = QLabel()
        self.start_button = QPushButton(tr("Start"))
        self.stop_button = QPushButton(tr("Stop"))
        self.report_button = QPushButton(tr("Open the report"))
        self.close_button = QPushButton(tr("Close"))
        self.stop_button.setEnabled(False)
        self.report_button.setEnabled(False)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.test.stop)
        self.report_button.clicked.connect(self.open_report)
        self.close_button.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addWidget(self.summary, 1)
        for button in (self.start_button, self.stop_button, self.report_button, self.close_button):
            buttons.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.prompt)
        layout.addLayout(answers)
        layout.addLayout(buttons)

        self.test.step_started.connect(self._started)
        self.test.step_finished.connect(self._finished)
        self.test.asking.connect(self._asking)
        self.test.waiting.connect(self._waiting)
        self.test.finished.connect(self._done)

    def start(self) -> None:
        if getattr(self.test.helper, "midi_out", None) is None:
            self.summary.setText(tr("No MIDI output: connect the JD-Xi first."))
            return
        for row in range(self.table.rowCount()):
            self.table.item(row, 1).setText("")
            self.table.item(row, 2).setText("")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.report_button.setEnabled(False)
        self.summary.setText("")
        self.test.start()

    def _started(self, row: int) -> None:
        self.table.item(row, 1).setText("…")
        self.table.scrollToItem(self.table.item(row, 0))

    def _finished(self, row: int, status: str, detail: str) -> None:
        item = self.table.item(row, 1)
        item.setText(STATUS_TEXT.get(status, status))
        colour = STATUS_COLOUR.get(status)
        if colour:
            item.setForeground(_colour(colour))
        self.table.item(row, 2).setText(detail)

    def _asking(self, question: str, hint: str) -> None:
        shown = bool(question)
        self.prompt.setText(question + (f"\n{hint}" if hint else ""))
        self.prompt.setVisible(shown)
        for button in (self.yes_button, self.no_button, self.skip_button):
            button.setVisible(shown)
        if shown:
            self.raise_()
            self.activateWindow()

    def _waiting(self, text: str) -> None:
        if isinstance(self.test._pending, Ask):
            return
        self.prompt.setText(text)
        self.prompt.setVisible(bool(text))

    def _done(self) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        steps = self.test.steps
        ok = sum(1 for s in steps if s.status == OK)
        ko = sum(1 for s in steps if s.status == KO)
        try:
            self.report_path = self.test.save_report()
            self.report_button.setEnabled(True)
            saved = tr("report: {path}").format(path=self.report_path)
        except OSError as ex:
            saved = tr("report not saved: {error}").format(error=ex)
        self.summary.setText(f"OK {ok} · KO {ko} · {saved}")
        log.message(f"Self-test finished: OK {ok}, KO {ko}", scope="SelfTest")

    def open_report(self) -> None:
        if self.report_path is None:
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.report_path)))

    def closeEvent(self, event) -> None:
        self.test.stop()
        super().closeEvent(event)


def _colour(hex_colour: str):
    from PySide6.QtGui import QColor

    return QColor(hex_colour)
