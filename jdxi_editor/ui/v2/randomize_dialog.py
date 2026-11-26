"""
Randomize a SuperNATURAL tone: a section of the partial shown, the partial,
or the whole tone, by a little, a medium amount or much. Each press is one
Undo step, so it can be pressed again and again and taken back.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from jdxi_editor.i18n import tr
from jdxi_editor.ui.v2 import partial_tools as pt


class RandomizeDialog(QDialog):
    STYLE = (
        "QDialog { background: #121214; color: #e6e6e6; }"
        "QLabel { color: #c9cbd1; background: transparent; }"
        "QRadioButton { color: #e6e6e6; }"
        "QComboBox { background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px; padding: 3px 8px; }"
        "QPushButton { background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px; padding: 6px 14px; }"
        "QPushButton:hover { border-color: #6b6f78; }"
    )

    def __init__(self, editor, partial: int, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.partial = partial
        self.setWindowTitle(tr("Randomize"))
        self.setStyleSheet(self.STYLE)
        self.setMinimumWidth(480)
        accent = getattr(editor, "ACCENT", "#eb5757")
        root = QVBoxLayout(self)

        root.addWidget(QLabel(tr("What")))
        self.scope = QButtonGroup(self)
        line = QHBoxLayout()
        self.section_radio = QRadioButton(tr("Section"))
        line.addWidget(self.section_radio)
        self.section = QComboBox()
        for section in pt.SECTIONS:
            self.section.addItem(pt.section_name(section), section)
        self.section.currentIndexChanged.connect(lambda _i: self.section_radio.setChecked(True))
        line.addWidget(self.section)
        line.addWidget(QLabel(tr("of partial {n}").format(n=partial + 1)))
        line.addStretch()
        root.addLayout(line)
        self.partial_radio = QRadioButton(tr("Partial {n}").format(n=partial + 1))
        self.tone_radio = QRadioButton(tr("The whole tone (three partials, Wave Shape, Analog Feel)"))
        for button, key in ((self.section_radio, "section"), (self.partial_radio, "partial"), (self.tone_radio, "tone")):
            button.setProperty("scope", key)
            self.scope.addButton(button)
        root.addWidget(self.partial_radio)
        root.addWidget(self.tone_radio)
        self.section_radio.setChecked(True)

        root.addSpacing(6)
        root.addWidget(QLabel(tr("How much")))
        self.amount = QButtonGroup(self)
        amounts = QHBoxLayout()
        for key, label, tip in (
            ("little", tr("A little"), tr("Each value moves by up to 10% of its range: a variation of the sound.")),
            ("medium", tr("Medium"), tr("Up to 30%: the same character, clearly different.")),
            ("much", tr("Much"), tr("Anything, also the waveforms, filter types and LFO shapes: a new sound.")),
        ):
            button = QRadioButton(label)
            button.setToolTip(tip)
            button.setProperty("amount", key)
            self.amount.addButton(button)
            amounts.addWidget(button)
            if key == "medium":
                button.setChecked(True)
        amounts.addStretch()
        root.addLayout(amounts)
        note = QLabel(tr("The name, category, playing style (mono, portamento, bend) and which partials are on "
                         "stay as they are; a partial randomized stays audible. Each press is one Undo step."))
        note.setWordWrap(True)
        note.setStyleSheet("color: #8a8d94; font-size: 11px;")
        note.setMinimumWidth(420)
        note.setMinimumHeight(note.heightForWidth(420) + 4)
        root.addWidget(note)

        self.result = QLabel("")
        root.addWidget(self.result)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.go = QPushButton("🎲  " + tr("Randomize"))
        self.go.setStyleSheet(f"QPushButton {{ background: {accent}; color: #0e0f11; border: none; font-weight: 700; }}")
        self.go.setDefault(True)
        self.go.clicked.connect(self.randomize)
        buttons.addWidget(self.go)
        undo = QPushButton(tr("Undo"))
        undo.clicked.connect(self.undo)
        buttons.addWidget(undo)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        root.addLayout(buttons)

    def chosen_scope(self) -> str:
        button = self.scope.checkedButton()
        return button.property("scope") if button is not None else "section"

    def chosen_amount(self) -> str:
        button = self.amount.checkedButton()
        return button.property("amount") if button is not None else "medium"

    def randomize(self) -> int:
        changed = pt.randomize(self.editor, self.chosen_scope(), self.chosen_amount(), self.partial,
                               self.section.currentData())
        self.result.setText(tr("{n} values changed.").format(n=changed))
        return changed

    def undo(self) -> None:
        history = getattr(self.editor, "history", None)
        if history is not None and history.undo():
            self.result.setText(tr("Taken back."))
