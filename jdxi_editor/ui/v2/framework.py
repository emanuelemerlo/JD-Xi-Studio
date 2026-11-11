"""
A small framework for the new editors: parameters described once, as data.

PSpec describes one parameter of a SysEx block: its name (the one the SysEx
parser uses for incoming data), offset, display range or choices, how the
display value is encoded (plain, +offset, 4 nibbles around 32768) and what
the information panel says about it. It is also a parameter object the
existing JDXiSysExComposer accepts (get_offset, get_nibbled_size,
convert_to_midi), so sending goes through the same code as everywhere else.

Block groups the PSpecs of one SysEx area (e.g. Program Effect 1 at
18 00 02 00) under the name the parser gives that area ("EFFECT_1").

V2Editor builds a ParamValue for every PSpec, sends changes (at most every
SEND_INTERVAL_MS while dragging), shows values read from the JD-Xi without
sending them back, offers "Read from JD-Xi", and connects every control to
the information panel. Subclasses lay out the panels.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.ui.editors.synth.base import SynthBase
from jdxi_editor.ui.v2.params import ParamInfo, ParamValue
from jdxi_editor.ui.v2.widgets import (
    Card,
    ChoiceButtons,
    InfoHub,
    InfoPanel,
    Knob,
    NoteCombo,
)

SEND_INTERVAL_MS = 25
ROLAND_DT1 = (0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x12)  # after F0: Roland, device 10h, JD-Xi, DT1


def seven_bit(value: int) -> int:
    """01 0D (written 0x010D) -> 141: Roland addresses use 7 bits per byte."""
    return ((value >> 8) & 0x7F) * 128 + (value & 0x7F)


def address_number(address: Sequence[int]) -> int:
    number = 0
    for byte in address:
        number = number * 128 + (byte & 0x7F)
    return number


def rq1(address: Sequence[int], size: int) -> str:
    """The RQ1 message (as the request queue takes it) that reads *size* bytes from *address*."""
    size_bytes = [(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F]
    body = list(address) + size_bytes
    checksum = (128 - sum(body) % 128) % 128
    data = [0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x0E, 0x11] + body + [checksum, 0xF7]
    return " ".join(f"{b:02X}" for b in data)
NIBBLE_ZERO = 32768  # 4-nibble parameters: 32768 is 0


@dataclass(eq=False)  # identity: two effect types may share one address
class PSpec:
    """One parameter: address, encoding, range and what to say about it."""

    name: str  # as the SysEx parser names it (incoming data)
    offset: int  # within the block, as written in the MIDI Implementation (0x010D = 01 0D)
    label: str  # on the display
    long: str = ""
    description: str = ""
    lo: int = 0  # display range
    hi: int = 127
    raw_offset: int = 0  # raw = display + raw_offset (e.g. 64 for -63..+63)
    nibbled: bool = False  # 4 nibbles, raw = 32768 + display
    size: int = 0  # bytes it takes when not 1 or "nibbled": 2 or 4 nibbles, raw as is
    choices: Sequence[str] = ()  # labels for display values lo..hi
    values: Optional[Sequence[int]] = None  # raw values of the choices, when not lo..hi
    unit: str = ""
    signed: bool = False
    step: int = 1
    page: int = 0
    depends: str = ""
    group: str = ""
    kind: str = ""  # "knob", "buttons", "list"; chosen from the data when empty
    source: str = ""  # shown instead of the Parameter Guide page
    scale: int = 1  # shown divided by this
    fmt: Optional[Callable[[int], str]] = None
    parse: Optional[Callable[[str], Optional[int]]] = None

    # --- what the composer and the parser need
    @property
    def address(self) -> int:
        return self.offset

    @property
    def min_val(self) -> int:
        return self.convert_to_midi(self.lo)

    @property
    def max_val(self) -> int:
        return self.convert_to_midi(self.hi)

    def get_offset(self) -> tuple[int, int, int]:
        return 0, (self.offset >> 8) & 0xFF, self.offset & 0xFF

    def get_nibbled_size(self) -> int:
        return 4 if self.nibbled else (self.size or 1)

    def convert_to_midi(self, display: int) -> int:
        display = int(display)
        if self.values is not None:
            index = max(0, min(len(self.values) - 1, display - self.lo))
            return int(self.values[index])
        raw = display + self.raw_offset
        return raw + NIBBLE_ZERO if self.nibbled else raw

    def convert_from_midi(self, raw: int) -> int:
        raw = int(raw)
        if self.values is not None:
            values = list(self.values)
            return self.lo + (values.index(raw) if raw in values else 0)
        if self.nibbled:
            raw -= NIBBLE_ZERO
        return raw - self.raw_offset

    def info(self, group: str, area: str = "PROGRAM") -> ParamInfo:
        return ParamInfo(
            group=self.group or group,
            label=self.label,
            long=self.long,
            description=self.description,
            unit=self.unit,
            depends=self.depends,
            choices=tuple(self.choices),
            step=self.step,
            page=self.page,
            signed=self.signed,
            area=area,
            source=self.source,
            scale=self.scale,
            fmt=self.fmt,
            parse=self.parse,
        )

    def widget_kind(self) -> str:
        if self.kind:
            return self.kind
        if self.choices:
            return "buttons" if len(self.choices) <= 6 else "list"
        return "knob"


@dataclass
class Block:
    """The parameters of one SysEx area."""

    key: str  # the parser's SYNTH_TONE for this area ("EFFECT_1", "DELAY", ...)
    group: str  # name shown as the panel group ("EFFECT1")
    address: object  # JDXiSysExAddress of the block
    params: list[PSpec] = field(default_factory=list)
    request: object = None  # the RQ1 that reads the block

    def address_bytes(self) -> list[int]:
        a = self.address
        return [a.msb, a.umb, a.lmb, a.lsb]


class V2Editor(SynthBase):
    """Base of the new editors: values, sending, receiving, information."""

    ACCENT = "#f2994a"
    TEMPORARY_AREA = "TEMPORARY_PROGRAM"
    AREA = "PROGRAM"  # shown before the group in the information panel

    def __init__(self, blocks: list[Block], midi_helper=None, parent=None, title: str = ""):
        super().__init__(midi_helper=midi_helper, parent=parent)
        self.blocks = blocks
        self.values: dict[PSpec, ParamValue] = {}
        self.block_of: dict[PSpec, Block] = {}
        self._pending: dict = {}
        self._send_timer = QTimer(self)
        self._send_timer.setInterval(SEND_INTERVAL_MS)
        self._send_timer.timeout.connect(self._flush_pending)
        self.info_hub = InfoHub(self)
        if title:
            self.setWindowTitle(title)
        for block in blocks:
            for spec in block.params:
                pv = ParamValue(spec, spec.info(block.group, self.AREA), spec.lo, spec.hi, self)
                pv.valueChanged.connect(lambda v, spec=spec: self._queue_send(spec, v))
                self.values[spec] = pv
                self.block_of[spec] = block
        # a plain dict: the registry would merge parameters that share a name
        self.controls = dict(self.values)
        self.midi_requests = [b.request for b in blocks if b.request is not None]
        self._build_frame()
        self.build_panels()
        if midi_helper is not None and hasattr(midi_helper, "midi_sysex_json"):
            midi_helper.midi_sysex_json.connect(self.dispatch_sysex_to_area)
        if midi_helper is not None and hasattr(midi_helper, "midi_message_incoming"):
            midi_helper.midi_message_incoming.connect(self.receive_message)

    # ------------------------------------------------------------- lookups
    def spec(self, name: str, block_key: Optional[str] = None) -> PSpec:
        for block in self.blocks:
            if block_key and block.key != block_key:
                continue
            for spec in block.params:
                if spec.name == name:
                    return spec
        raise KeyError(name)

    def pv(self, name: str, block_key: Optional[str] = None) -> ParamValue:
        return self.values[self.spec(name, block_key)]

    # -------------------------------------------------------------- layout
    def _build_frame(self) -> None:
        self.setMinimumSize(960, 600)
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(10)
        bar = QHBoxLayout()
        self.title_label = QLabel(self.windowTitle())
        self.title_label.setStyleSheet(
            f"color: {self.ACCENT}; font-size: 15px; font-weight: 700; letter-spacing: 1px;"
        )
        bar.addWidget(self.title_label)
        bar.addStretch()
        self.read_status = QLabel("")
        self.read_status.setStyleSheet("color: #a3a6ad; font-size: 11px;")
        bar.addWidget(self.read_status)
        self.read_button = QPushButton(tr("Read from JD-Xi"))
        self.read_button.setToolTip(tr("Request current parameters from the synthesizer (RQ1)"))
        self.read_button.clicked.connect(self._read)
        bar.addWidget(self.read_button)
        left.addLayout(bar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.scroll.viewport().setAutoFillBackground(False)
        host = QWidget()
        host.setStyleSheet("background: transparent;")
        self.panels_layout = QVBoxLayout(host)
        self.panels_layout.setContentsMargins(0, 0, 0, 0)
        self.panels_layout.setSpacing(12)
        self.scroll.setWidget(host)
        left.addWidget(self.scroll, 1)
        root.addLayout(left, 1)
        self.info_panel = InfoPanel(self.ACCENT)
        self.info_panel.setFixedWidth(320)
        self.info_hub.shown.connect(self.info_panel.show_param)
        root.addWidget(self.info_panel)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"{type(self).__name__} {{ background: #121214; }}")

    def build_panels(self) -> None:
        """Subclasses add their panels to self.panels_layout."""

    # --- helpers for subclasses
    def control(self, spec: PSpec, **kwargs) -> QWidget:
        """The usual widget for a parameter."""
        pv = self.values[spec]
        kind = spec.widget_kind()
        if kind == "buttons":
            return ChoiceButtons(pv, self.ACCENT, self.info_hub, **kwargs)
        if kind == "list":
            return NoteCombo(pv, self.info_hub)
        return Knob(pv, self.ACCENT, self.info_hub)

    def knob_row(self, specs: Sequence[PSpec]) -> QHBoxLayout:
        row = QHBoxLayout()
        for spec in specs:
            row.addWidget(self.control(spec))
        row.addStretch()
        return row

    def card(self, title: str, subtitle: str = "") -> Card:
        return Card(title, self.ACCENT, subtitle)

    def auto_card(self, title: str, specs: Sequence[PSpec], subtitle: str = "", per_row: int = 5) -> Card:
        """A panel with switches/lists first, then knobs in rows."""
        card = self.card(title, subtitle)
        knobs = [s for s in specs if s.widget_kind() == "knob"]
        for spec in specs:
            if spec.widget_kind() != "knob":
                card.body.addWidget(self.control(spec))
        for i in range(0, len(knobs), per_row):
            card.body.addLayout(self.knob_row(knobs[i : i + per_row]))
        return card

    def note(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #8a8d94; font-size: 11px; background: transparent;")
        return label

    # ------------------------------------------------------------- sending
    def _queue_send(self, spec: PSpec, value: int) -> None:
        self._pending[spec] = value
        if not self._send_timer.isActive():
            self._flush_pending()
            self._send_timer.start()

    def _flush_pending(self) -> None:
        if not self._pending:
            self._send_timer.stop()
            return
        pending, self._pending = self._pending, {}
        for spec, value in pending.items():
            self.send_midi_parameter(spec, value, self.block_of[spec].address)

    # ----------------------------------------------------------- receiving
    def dispatch_sysex_to_area(self, json_sysex_data: str) -> None:
        try:
            data = json.loads(json_sysex_data) if isinstance(json_sysex_data, str) else dict(json_sysex_data)
        except (TypeError, ValueError):
            return
        if data.get("TEMPORARY_AREA") != self.TEMPORARY_AREA:
            return
        tone = data.get("SYNTH_TONE")
        for block in self.blocks:
            if block.key != tone:
                continue
            self.apply_values(block, data)

    def receive_message(self, message) -> int:
        """A DT1 from the JD-Xi (a whole block or one parameter): show the values it carries."""
        if getattr(message, "type", None) != "sysex":
            return 0
        return self.receive_dt1(list(message.data))

    def receive_dt1(self, data: Sequence[int]) -> int:
        """*data*: the bytes between F0 and F7."""
        data = list(data)
        if data[:1] == [0xF0]:
            data = data[1:]
        if data[-1:] == [0xF7]:
            data = data[:-1]
        if tuple(data[:7]) != ROLAND_DT1 or len(data) < 13:
            return 0
        start = address_number(data[7:11])
        payload = data[11:-1]  # without the checksum
        shown = 0
        for block in self.blocks:
            first = start - address_number(block.address_bytes())
            if first < 0 or first > 0x3FF:
                continue
            for spec in block.params:
                pos = seven_bit(spec.offset) - first
                size = spec.get_nibbled_size()
                if pos < 0 or pos + size > len(payload):
                    continue
                raw = 0
                for byte in payload[pos : pos + size]:
                    raw = (raw << 4 | (byte & 0x0F)) if size > 1 else byte
                self._show_raw(spec, raw)
                shown += 1
        return shown

    def _show_raw(self, spec: PSpec, raw: int) -> None:
        pv = self.values[spec]
        pv.blockSignals(True)
        pv.setValue(spec.convert_from_midi(raw))
        pv.blockSignals(False)

    def apply_values(self, block: Block, data: dict) -> int:
        """Show the values of *block* found in *data* (raw MIDI), without sending."""
        shown = 0
        for spec in block.params:
            if spec.name not in data:
                continue
            try:
                display = spec.convert_from_midi(int(data[spec.name]))
            except (TypeError, ValueError):
                continue
            pv = self.values[spec]
            pv.blockSignals(True)
            pv.setValue(display)
            pv.blockSignals(False)
            shown += 1
        return shown

    def _read(self) -> None:
        if not self.midi_requests:
            return
        known = {
            "Reading from JD-Xi…": tr("Reading from JD-Xi…"),
            "Read complete": tr("Read complete"),
        }
        self.read_from_jdxi(status_callback=lambda text: self.read_status.setText(known.get(text, text)))

    def read_block(self, block: Block) -> None:
        """Ask the JD-Xi for one block again (e.g. after a type change)."""
        helper = getattr(self, "_midi_helper", None)
        if block.request is None or helper is None or not hasattr(helper, "send_raw_message"):
            return
        from jdxi_editor.midi.sysex.request.read_session import start_read_session

        start_read_session(helper, [block.request], timeout_ms=3000, parent=self)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.midi_requests and getattr(self, "_midi_helper", None) is not None:
            self.data_request()

    def get_controls_as_dict(self) -> dict:
        return {spec.name: pv.value() for spec, pv in self.values.items()}
