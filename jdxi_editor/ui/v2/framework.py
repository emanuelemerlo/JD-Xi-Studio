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

import functools
import json
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
    report_to,
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
    factor: int = 1  # display = (raw - raw_offset) * factor (Key Follow: -100..+100 in steps of 10)
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
        raw = int(round(display / self.factor)) + self.raw_offset
        return raw + NIBBLE_ZERO if self.nibbled else raw

    def convert_from_midi(self, raw: int) -> int:
        raw = int(raw)
        if self.values is not None:
            values = list(self.values)
            return self.lo + (values.index(raw) if raw in values else 0)
        if self.nibbled:
            raw -= NIBBLE_ZERO
        return (raw - self.raw_offset) * self.factor

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
    export: bool = True  # whether the editor gives the whole block for patches and .syx

    def address_bytes(self) -> list[int]:
        a = self.address
        return [a.msb, a.umb, a.lmb, a.lsb]

    def size(self) -> int:
        """Bytes in the block, from its RQ1 (0 when it has none)."""
        if not self.request:
            return 0
        tokens = str(self.request).split()
        return address_number([int(t, 16) for t in tokens[12:16]])


class NameField(QLineEdit):
    """A program or tone name: 12 ASCII characters, sent as one message when edited."""

    def __init__(self, editor: "V2Editor", pvs: list[ParamValue], address, tooltip: str = ""):
        super().__init__()
        self.editor, self.pvs, self.address = editor, pvs, address
        self.setMaxLength(12)
        self.setFixedWidth(170)
        self.setStyleSheet(
            "QLineEdit { background: #121214; color: #ffffff; border: 1px solid #3a3d44; border-radius: 5px;"
            " padding: 3px 6px; font-family: monospace; font-size: 13px; }"
        )
        self.setToolTip(tooltip)
        for pv in pvs:
            pv.watch(lambda _v: self._show())
        report_to(editor.info_hub, self, pvs[0])
        self.editingFinished.connect(self._send)

    def text_from_values(self) -> str:
        return "".join(chr(pv.value()) if 32 <= pv.value() <= 126 else " " for pv in self.pvs).rstrip()

    def _show(self) -> None:
        if not self.hasFocus():
            self.setText(self.text_from_values())

    def _send(self) -> None:
        text = "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in self.text())[:12].ljust(12)
        if text.rstrip() == self.text_from_values():
            return
        codes = [ord(ch) for ch in text]
        for pv, code in zip(self.pvs, codes):
            pv.blockSignals(True)
            pv.setValue(code)
            pv.blockSignals(False)
        self.editor.send_bytes(self.address, codes)



class V2Editor(SynthBase):
    """Base of the new editors: values, sending, receiving, information."""

    ACCENT = "#f2994a"
    TEMPORARY_AREA = "TEMPORARY_PROGRAM"
    AREA = "PROGRAM"  # shown before the group in the information panel

    def __init__(self, blocks: list[Block], midi_helper=None, parent=None, title: str = ""):
        super().__init__(midi_helper=midi_helper, parent=parent)
        self.before_frame()
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
        helper = midi_helper if midi_helper is not None else getattr(self, "midi_helper", None)
        if helper is not None and hasattr(helper, "midi_sysex_json"):
            helper.midi_sysex_json.connect(self.dispatch_sysex_to_area)
        if helper is not None and hasattr(helper, "midi_message_incoming"):
            helper.midi_message_incoming.connect(self.receive_message)

    def before_frame(self) -> None:
        """Called after the base class is set up, before the panels are built."""

    def side_widgets(self) -> list:
        """Widgets shown above the information panel (e.g. the tone presets)."""
        return []

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

    def setWindowTitle(self, title: str) -> None:  # noqa: N802 (Qt name)
        super().setWindowTitle(title)
        label = getattr(self, "title_label", None)
        if label is not None:
            from jdxi_editor.ui.v2.names import short_name

            label.setText(short_name(title).upper())  # as on its tab, translated
            label.setVisible(bool(title))

    # -------------------------------------------------------------- layout
    def _build_frame(self) -> None:
        self.setMinimumSize(960, 600)
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)
        left = QVBoxLayout()
        left.setSpacing(10)
        bar = QHBoxLayout()
        # The editor's name as a badge in its colour: Digital 1 and 2, say, tell apart at a glance
        self.title_label = QLabel(self.windowTitle().upper())
        self.title_label.setObjectName("v2Title")
        self.title_label.setStyleSheet(
            f"QLabel#v2Title {{ background: {self.ACCENT}; color: #0e0f11; border-radius: 6px;"
            " padding: 3px 12px; font-size: 16px; font-weight: 800; letter-spacing: 2px; }"
        )
        self.title_label.setVisible(bool(self.windowTitle()))
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
        self.info_hub.shown.connect(self.info_panel.show_param)
        above = self.side_widgets()
        if not above:
            self.info_panel.setFixedWidth(320)
            root.addWidget(self.info_panel)
        else:  # presets and information, scrolling on short screens
            side_host = QWidget()
            side_host.setStyleSheet("background: transparent;")
            side = QVBoxLayout(side_host)
            side.setContentsMargins(0, 0, 0, 0)
            side.setSpacing(12)
            for widget in above:
                side.addWidget(widget)
            self.info_panel.setFixedWidth(340)
            self.info_panel.setMinimumHeight(260)
            side.addWidget(self.info_panel, 1)
            side_scroll = QScrollArea()
            side_scroll.setWidgetResizable(True)
            side_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            side_scroll.setFixedWidth(356)
            side_scroll.setWidget(side_host)
            root.addWidget(side_scroll)
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

    def send_bytes(self, address, data: Sequence[int]) -> bool:
        """Send several bytes in one DT1 (a name)."""
        helper = getattr(self, "_midi_helper", None)
        if helper is None:
            return False
        from jdxi_editor.midi.message.roland import JDXiSysEx

        return bool(helper.send_midi_message(JDXiSysEx(sysex_address=address, value=list(data))))

    # ------------------------------------------------------- whole blocks
    def export_dt1s(self) -> list[bytes]:
        """
        Every block as one DT1 with the values shown (for patches and .syx).

        Bytes the editor has no control for (reserves) come from the copy of
        the JD-Xi's memory when it holds them, otherwise they are 0.
        """
        from jdxi_editor.midi.io.synth_memory import build_dt1

        memory = None
        helper = getattr(self, "_midi_helper", None) or getattr(self, "midi_helper", None)
        if helper is not None:
            try:
                from jdxi_editor.midi.io.device import device_for

                memory = device_for(helper).memory
            except Exception:  # a test double without a device
                memory = None
        messages = []
        for block in self.blocks:
            size = block.size()
            if not size or not block.export:
                continue
            address = block.address_bytes()
            known = memory.read(address, size) if memory is not None else None
            data = bytearray(known if known is not None else bytes(size))
            for spec in block.params:
                pos, width = seven_bit(spec.offset), spec.get_nibbled_size()
                if pos + width > size:
                    continue
                raw = spec.convert_to_midi(self.values[spec].value())
                if width == 1:
                    data[pos] = raw & 0x7F
                else:
                    for i in range(width):
                        data[pos + i] = (raw >> (4 * (width - 1 - i))) & 0x0F
            messages.append(build_dt1(address, data))
        return messages


@functools.lru_cache(maxsize=None)
def tone_editor_base():
    """V2Editor with the tone machinery of the existing editors (presets, tone name, .syx)."""
    from jdxi_editor.ui.editors.synth.editor import SynthEditor

    class V2ToneEditor(V2Editor, SynthEditor):
        """A tone editor (Digital, Drums): adds the existing tone preset panel on the side."""

        AREA = "TONE"
        TEMPORARY_AREA = None  # values come from the DT1 messages
        SYNTH_TYPE = None  # JDXiSynth.DIGITAL_SYNTH_1 ...
        PRESET_KIND = "Digital"  # the preset panel's list: "Digital", "Drums"

        def before_frame(self) -> None:
            if self.SYNTH_TYPE is not None:
                self._init_synth_data(self.SYNTH_TYPE)

        def update_instrument_image(self) -> None:
            """The preset's category as a card: its icon and name, the same for every sound of it.

            (The editors used to show a photo or drawing of the synth a preset
            imitates, picked from its name: poor at this size, and it suggested
            compatibility with instruments the JD-Xi only imitates.)
            """
            label = getattr(self, "instrument_image_label", None)
            if label is None:
                return
            label.setPixmap(sound_card(self._selected_category(), self.ACCENT))

        def _selected_category(self) -> str:
            combo = getattr(getattr(self, "instrument_preset", None), "instrument_selection_combo", None)
            presets = getattr(self, "preset_preset_list", None) or []
            if combo is None:
                return ""
            text = combo.combo_box.currentText()
            preset_id = text.split(" - ")[0].strip() if " - " in text else ""
            for preset in presets:
                if str(preset.get("id")) == preset_id:
                    return str(preset.get("category", ""))
            return ""

        def side_widgets(self) -> list:
            from jdxi_editor.core.jdxi import JDXi
            from jdxi_editor.ui.preset.widget import InstrumentPresetWidget

            self.instrument_preset = InstrumentPresetWidget(parent=self)
            self.instrument_preset.setup_header_layout()
            self.instrument_preset.setup()
            self.instrument_preset_group = self.instrument_preset.create_instrument_preset_group(
                synth_type=self.PRESET_KIND
            )
            self.instrument_preset.add_preset_group(self.instrument_preset_group)
            (
                self.instrument_image_group,
                self.instrument_image_label,
                self.instrument_group_layout,
            ) = self.instrument_preset.create_instrument_image_group()
            self.instrument_preset.add_image_group(self.instrument_image_group)
            self.instrument_preset.setFixedWidth(340)
            JDXi.UI.Theme.apply_editor_style(self.instrument_preset)
            # The new look: a card in the editor's colour, flat buttons with icon and name
            from jdxi_editor.ui.v2.restyle import restyle

            restyle(self.instrument_preset, self.ACCENT)
            tidy_preset_card(self.instrument_preset)
            self.update_instrument_image()
            self.read_button.hide()  # the preset panel has its own "Read from JD-Xi"
            return [self.instrument_preset]

    return V2ToneEditor


# The preset categories' icons (MDI / Font Awesome through qtawesome)
CATEGORY_ICONS = (
    ("bass", "mdi.music-clef-bass"),
    ("string", "mdi.violin"),
    ("pad", "mdi.violin"),
    ("lead", "mdi.music-note"),
    ("brass", "mdi.trumpet"),
    ("keyboard", "mdi.piano"),
    ("piano", "mdi.piano"),
    ("seq", "mdi.dots-grid"),
    ("fx", "mdi.creation"),
    ("drum", "fa5s.drum"),
    ("percussion", "fa5s.drum"),
    ("kit", "fa5s.drum"),
    ("dance", "fa5s.drum"),
    ("hip-hop", "fa5s.drum"),
    ("decade", "fa5s.drum"),
    ("experimental", "fa5s.drum"),
    ("init", "mdi.restart"),
    ("synth", "mdi.sine-wave"),
)


def category_icon(category: str) -> str:
    name = category.lower()
    for word, icon in CATEGORY_ICONS:
        if word in name:
            return icon
    return "mdi.sine-wave"


def sound_card(category: str, accent: str, width: int = 268, height: int = 96):
    """A card with the category's icon in the editor's colour and its name."""
    import qtawesome as qta
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap

    from jdxi_editor.i18n import tr

    ratio = 2  # drawn at twice the size: sharp on scaled screens
    pixmap = QPixmap(width * ratio, height * ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(ratio, ratio)
    card = QPainterPath()
    card.addRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), 10, 10)
    p.fillPath(card, QColor("#16171a"))
    p.setPen(QColor("#2e3036"))
    p.drawPath(card)
    tile = QRectF(14, (height - 64) / 2, 64, 64)
    tint = QColor(accent)
    tint.setAlpha(40)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(tint)
    p.drawRoundedRect(tile, 14, 14)
    icon = qta.icon(category_icon(category), color=accent)
    icon.paint(p, tile.adjusted(12, 12, -12, -12).toRect())
    text_left = tile.right() + 16
    small = QFont()
    small.setPixelSize(11)
    small.setBold(True)
    small.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
    p.setFont(small)
    p.setPen(QColor(accent))
    p.drawText(QRectF(text_left, 22, width - text_left - 10, 16), Qt.AlignmentFlag.AlignLeft, tr("CATEGORY"))
    big = QFont()
    big.setBold(True)
    p.setPen(QColor("#f2f2f2"))
    name = category or tr("All sounds")
    room = QRectF(text_left, 40, width - text_left - 10, 44)
    flags = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap)
    for px in (19, 17, 15, 13):  # long names (drum kit groups) on two lines, a little smaller
        big.setPixelSize(px)
        p.setFont(big)
        if room.contains(p.fontMetrics().boundingRect(room.toRect(), flags, name).toRectF()):
            break
    p.drawText(room, flags, name)
    p.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def tidy_preset_card(panel: QWidget) -> None:
    """The preset card in columns: every row as wide as the card, nothing cut or sticking out.

    The card is 340 px wide; with large Windows text the buttons' natural
    widths added up to more, so the display and the rows overflowed it.
    Previous / Next become arrows (named in their tooltips), every row of
    buttons shares the card's width, the display fits the card.
    """
    from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLayout, QPushButton, QSizePolicy, QSpacerItem

    preset = getattr(panel, "_preset_prev_button", None), getattr(panel, "_preset_next_button", None)
    for button, arrow in zip(preset, ("‹", "›")):
        if button is not None:
            button.setToolTip(button.text().strip() or button.toolTip())
            button.setText("")
            button.setFixedWidth(40)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def rows(layout: QLayout):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            child = item.layout() or (QWidget.layout(item.widget()) if item.widget() is not None else None)
            if child is not None:
                yield from rows(child)
        yield layout

    root = QWidget.layout(panel)  # (the preset widget's own "layout" attribute hides the method)
    if root is None:
        return
    for layout in list(rows(root)):
        if layout is not root:
            layout.setContentsMargins(0, 0, 0, 0)
        if not isinstance(layout, QHBoxLayout):
            continue
        widgets = [layout.itemAt(i).widget() for i in range(layout.count()) if layout.itemAt(i).widget()]
        if layout is not root:
            layout.setContentsMargins(0, 0, 0, 0)  # every row starts at the card's edge
        if any(isinstance(w, QComboBox) for w in widgets):
            for w in widgets:  # an empty name in front of a list only pushes it to the right
                if isinstance(w, QLabel) and not w.text() and (w.pixmap() is None or w.pixmap().isNull()):
                    w.hide()
            continue
        widgets = [w for w in widgets if not w.isHidden()]
        buttons = [w for w in widgets if isinstance(w, QPushButton) or (w.findChildren(QPushButton) and not w.findChildren(QComboBox))]
        others = [w for w in widgets if w not in buttons and not isinstance(w, QLabel)]
        if not buttons or others:
            continue  # not a row of buttons (a label and a field, say)
        for i in reversed(range(layout.count())):  # the stretches that kept them at their natural width
            if isinstance(layout.itemAt(i), QSpacerItem):
                layout.takeAt(i)
        for i in range(layout.count()):
            layout.setStretch(i, 0)
            label = layout.itemAt(i).widget()
            if isinstance(label, QLabel) and not label.text():
                label.hide()  # an empty status line (it shows up when there is something to say)
        for w in buttons:
            inner = [w] if isinstance(w, QPushButton) else w.findChildren(QPushButton)
            fixed = all(b.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed and b.maximumWidth() <= 40 for b in inner)
            if fixed:
                continue
            w.setMinimumWidth(0)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, w.sizePolicy().verticalPolicy())
            for b in inner:
                b.setMinimumWidth(0)
                b.setSizePolicy(QSizePolicy.Policy.Expanding, b.sizePolicy().verticalPolicy())
            if QWidget.layout(w) is not None:
                QWidget.layout(w).setContentsMargins(0, 0, 0, 0)
    group = getattr(panel, "_preset_group", None)
    if group is not None and QWidget.layout(group) is not None:
        QWidget.layout(group).setContentsMargins(12, 8, 12, 12)  # as the other cards
        QWidget.layout(group).setSpacing(8)
    title = getattr(panel, "instrument_title_label", None)
    if title is not None:  # the display: as wide as the card
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, title.sizePolicy().verticalPolicy())
