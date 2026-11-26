"""
The PCM waveforms of a SuperNATURAL partial, browsed by family.

The 160 waves (MIDI Implementation, Wave Number 1-160) in families, a search,
favourites (★, remembered) and «Try»: a wave chosen is set on the partial at
once and a short note plays it on the part's channel, so the arrows go
through the waves by ear. Cancel puts the wave back; OK is one Undo step.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jdxi_editor.i18n import tr
from jdxi_editor.midi.data.pcm.waves import PCM_WAVES

FAVOURITES_KEY = "digital/pcm_favourites"
TRY_KEY = "digital/pcm_try"
TRY_NOTE = 60  # C4
TRY_VELOCITY = 100
TRY_LENGTH_MS = 600

# families: name -> wave numbers (as the Parameter Guide lists them, grouped by sound)
FAMILIES: dict[str, tuple[int, ...]] = {
    "Synth & Lead": tuple(range(1, 28)) + (82,),
    "Bass": tuple(range(28, 36)) + tuple(range(134, 139)),
    "Bell & Metallic": tuple(range(36, 45)),
    "Voice & Formant": tuple(range(45, 63)),
    "Pad & Strings": tuple(n for n in range(63, 90) if n != 82) + tuple(range(139, 146)),
    "FX & Noise": tuple(range(90, 97)),
    "Hit & Drum": tuple(range(97, 109)),
    "Keys & Organ": tuple(range(109, 127)),
    "Guitar": tuple(range(127, 134)),
    "Brass & Wind": tuple(range(146, 157)),
    "Ethnic": tuple(range(157, 161)),
}
ALL, STARRED = "__all__", "__starred__"


def wave_name(number: int) -> str:
    """«Calc.Saw» for 1 (the name without its number)."""
    text = PCM_WAVES[number] if 0 <= number < len(PCM_WAVES) else str(number)
    return text.split(": ", 1)[1] if ": " in text else text


def family_of(number: int) -> str:
    for family, numbers in FAMILIES.items():
        if number in numbers:
            return family
    return ""


def family_label(family: str) -> str:
    return {
        "Synth & Lead": tr("Synth & Lead"), "Bass": tr("Bass"), "Bell & Metallic": tr("Bell & Metallic"),
        "Voice & Formant": tr("Voice & Formant"), "Pad & Strings": tr("Pad & Strings"),
        "FX & Noise": tr("FX & Noise"), "Hit & Drum": tr("Hit & Drum"), "Keys & Organ": tr("Keys & Organ"),
        "Guitar": tr("Guitar"), "Brass & Wind": tr("Brass & Wind"), "Ethnic": tr("Ethnic"),
    }.get(family, family)


def matches(number: int, text: str) -> bool:
    """The search: words in the name (any order), or the number."""
    text = text.strip().lower()
    if not text:
        return True
    if text.isdigit():
        return str(number).startswith(text.lstrip("0") or "0")
    name = wave_name(number).lower()
    return all(word in name or word in family_of(number).lower() for word in text.split())


def favourites(settings: Optional[QSettings] = None) -> set[int]:
    settings = settings or _settings()
    raw = settings.value(FAVOURITES_KEY, "")
    try:
        return {int(x) for x in str(raw or "").split(",") if x.strip()}
    except ValueError:
        return set()


def set_favourites(numbers: set[int], settings: Optional[QSettings] = None) -> None:
    (settings or _settings()).setValue(FAVOURITES_KEY, ",".join(str(n) for n in sorted(numbers)))


def _settings() -> QSettings:
    from jdxi_editor.project import __organization_name__, __program__

    return QSettings(__organization_name__, __program__)


class WaveBrowser(QDialog):
    """Choose the PCM wave of a partial: families, search, ★, try by ear."""

    STYLE = (
        "QDialog { background: #121214; color: #e6e6e6; }"
        "QLabel { color: #c9cbd1; background: transparent; }"
        "QLineEdit { background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px; padding: 5px 8px; }"
        "QListWidget { background: #17181b; color: #e6e6e6; border: 1px solid #2e3036; border-radius: 8px; outline: 0; }"
        "QListWidget::item { padding: 4px 8px; border-radius: 4px; }"
        "QListWidget::item:selected { background: #2a3a30; color: #ffffff; }"
        "QListWidget::item:hover:!selected { background: #22242a; }"
        "QCheckBox { color: #c9cbd1; }"
        "QPushButton { background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px; padding: 5px 12px; }"
        "QPushButton:hover { border-color: #6b6f78; }"
    )

    def __init__(self, wave_pv, play_note: Optional[Callable[[int, int], None]] = None, title: str = "",
                 accent: str = "#eb5757", history=None, parent: Optional[QWidget] = None,
                 settings: Optional[QSettings] = None):
        super().__init__(parent)
        self.pv = wave_pv
        self.play_note = play_note  # (note, velocity); velocity 0: note off
        self.history = history
        self.settings = settings or _settings()
        self.original = wave_pv.value()
        self.starred = favourites(self.settings)
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.timeout.connect(self._note_off)
        self._sounding = False
        self.setWindowTitle(title or tr("PCM wave"))
        self.setStyleSheet(self.STYLE)
        self.resize(560, 520)

        root = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search by name or number…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        root.addWidget(self.search)
        row = QHBoxLayout()
        self.families = QListWidget()
        self.families.setFixedWidth(170)
        for key, label in [(ALL, tr("All waves")), (STARRED, "★ " + tr("Favourites"))] + [
            (f, family_label(f)) for f in FAMILIES
        ]:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.families.addItem(item)
        self.families.currentRowChanged.connect(self.refresh)
        row.addWidget(self.families)
        self.waves = QListWidget()
        self.waves.currentItemChanged.connect(self._chosen)
        self.waves.itemDoubleClicked.connect(lambda _i: self.accept())
        row.addWidget(self.waves, 1)
        root.addLayout(row, 1)

        bottom = QHBoxLayout()
        self.try_box = QCheckBox(tr("Try: set it and play a note"))
        self.try_box.setToolTip(tr("Each wave chosen is set on the partial and plays C4 on the part's channel"))
        self.try_box.setChecked(str(self.settings.value(TRY_KEY, "true")).lower() == "true")
        self.try_box.toggled.connect(lambda on: self.settings.setValue(TRY_KEY, "true" if on else "false"))
        self.try_box.setEnabled(play_note is not None)
        bottom.addWidget(self.try_box)
        self.star = QPushButton("☆")
        self.star.setToolTip(tr("Add to or remove from the favourites"))
        self.star.setFixedWidth(36)
        self.star.clicked.connect(self.toggle_star)
        bottom.addWidget(self.star)
        bottom.addStretch()
        self.status = QLabel("")
        bottom.addWidget(self.status)
        root.addLayout(bottom)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        # open on the wave's family, the wave selected
        family = family_of(self.original)
        start = list(FAMILIES).index(family) + 2 if family else 0
        self.families.setCurrentRow(start)
        self._select(self.original)
        self.search.setFocus()

    # --- list
    def refresh(self, *_args) -> None:
        item = self.families.currentItem()
        key = item.data(Qt.ItemDataRole.UserRole) if item is not None else ALL
        text = self.search.text()
        if text.strip():  # a search looks in every family
            numbers = range(1, len(PCM_WAVES))
        elif key == STARRED:
            numbers = sorted(self.starred)
        elif key == ALL:
            numbers = range(1, len(PCM_WAVES))
        else:
            numbers = FAMILIES[key]
        current = self.current_number()
        self.waves.blockSignals(True)
        self.waves.clear()
        for number in numbers:
            if not matches(number, text):
                continue
            star = "★ " if number in self.starred else ""
            item = QListWidgetItem(f"{star}{number:03d}  {wave_name(number)}")
            item.setData(Qt.ItemDataRole.UserRole, number)
            item.setToolTip(family_label(family_of(number)))
            self.waves.addItem(item)
        self.waves.blockSignals(False)
        if current is not None:
            self._select(current, play=False)
        self.status.setText(tr("{n} waves").format(n=self.waves.count()))

    def _select(self, number: int, play: bool = False) -> None:
        for row in range(self.waves.count()):
            if self.waves.item(row).data(Qt.ItemDataRole.UserRole) == number:
                if not play:
                    self.waves.blockSignals(True)
                self.waves.setCurrentRow(row)
                self.waves.blockSignals(False)
                self._show_star(number)
                return

    def current_number(self) -> Optional[int]:
        item = self.waves.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    # --- choosing and trying
    def _chosen(self, item, _previous=None) -> None:
        if item is None:
            return
        number = item.data(Qt.ItemDataRole.UserRole)
        self._show_star(number)
        if self.try_box.isChecked() and self.play_note is not None:
            self._set_wave(number)
            self._note_off()
            self.play_note(TRY_NOTE, TRY_VELOCITY)
            self._sounding = True
            self._note_timer.start(TRY_LENGTH_MS)

    def _set_wave(self, number: int) -> None:
        if self.pv.value() == number:
            return
        if self.history is not None:  # the tries are not steps of their own
            self.history._replaying = True
        try:
            self.pv.setValue(number)
        finally:
            if self.history is not None:
                self.history._replaying = False

    def _note_off(self) -> None:
        if self._sounding and self.play_note is not None:
            self.play_note(TRY_NOTE, 0)
        self._sounding = False

    def toggle_star(self) -> None:
        number = self.current_number()
        if number is None:
            return
        self.starred ^= {number}
        set_favourites(self.starred, self.settings)
        self.refresh()
        self._show_star(number)

    def _show_star(self, number: int) -> None:
        self.star.setText("★" if number in self.starred else "☆")

    # --- closing
    def accept(self) -> None:
        number = self.current_number()
        self._note_off()
        if number is not None:
            self._set_wave(self.original)  # the step goes from the original to the wave chosen
            self.pv.setValue(number)
        super().accept()

    def reject(self) -> None:
        self._note_off()
        self._set_wave(self.original)
        super().reject()


class WaveField(QWidget):
    """The Wave Number on the partial's card: the wave's name and «Browse…»."""

    def __init__(self, wave_pv, open_browser: Callable[[], None], parent=None):
        super().__init__(parent)
        self.pv = wave_pv
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        caption = QLabel(tr("Wave Number"))
        caption.setStyleSheet("color: #c9cbd1; font-size: 11px; background: transparent;")
        layout.addWidget(caption)
        row = QHBoxLayout()
        self.button = QPushButton()
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setToolTip(tr("Browse the PCM waves by family, search them and try them by ear"))
        self.button.setStyleSheet(
            "QPushButton { background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px;"
            " padding: 5px 10px; text-align: left; } QPushButton:hover { border-color: #6b6f78; }"
            " QPushButton:disabled { color: #5c5f66; border-color: #2a2d33; }"
        )
        self.button.clicked.connect(open_browser)
        row.addWidget(self.button, 1)
        layout.addLayout(row)
        wave_pv.watch(self._show)
        wave_pv.watch_enabled(self.button.setEnabled)

    def _show(self, number: int) -> None:
        text = f"{number:03d}  {wave_name(number)}" if number else tr("Off")
        self.button.setText(text + "   …")
