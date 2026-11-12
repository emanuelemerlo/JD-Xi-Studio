from jdxi_editor.i18n import tr
from typing import Union

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.ui.widgets.label_click import make_label_clickable
from picoui.specs.widgets import ButtonSpec

# Fallback tooltips when not using ButtonSpec
_TOOLTIP_MAP = {
    "Digital Synth 1": tr("Digital Synth 1: Open the Digital Synth 1 editor"),
    "Digital Synth 2": tr("Digital Synth 2: Open the Digital Synth 2 editor"),
    "Drums": tr("Drums: Open the Drums editor"),
    "Analog Synth": tr("Analog Synth: Open the Analog Synth editor"),
    "Arpeggiator": tr("Arpeggiator: Open the Arpeggiator editor"),
    "Vocoder": tr("Vocoder: Open the Vocal Effects editor"),
    "Effects": tr("Effects: Open the Effects editor"),
}


def create_button_row(
    text_or_spec: Union[str, ButtonSpec],
    slot=None,
    vertical=False,
    spacing=10,
):
    """Create address row with label and circular button.

    Accepts either (text, slot) for backward compatibility or a ButtonSpec.
    When a ButtonSpec is passed, slot is ignored; use spec.slot.
    """
    if isinstance(text_or_spec, ButtonSpec):
        spec = text_or_spec
        text = spec.label or ""
        slot = spec.slot
        tooltip = tr(spec.tooltip) if spec.tooltip else _TOOLTIP_MAP.get(text, text)
    else:
        text = text_or_spec
        tooltip = _TOOLTIP_MAP.get(text, text)

    if not vertical:
        row = QHBoxLayout()
    else:
        row = QVBoxLayout()
    row.setSpacing(spacing)

    # Add label with color based on text
    label = QLabel(text)
    label.setStyleSheet(JDXi.UI.Style.LABEL_SYNTH_PART)  # every part the same colour
    row.addWidget(label)

    # Add spacer to push button to right
    row.addStretch()

    # Add button
    button = QPushButton()
    button.setFixedSize(30, 30)
    button.setCheckable(True)
    if slot is not None:
        button.clicked.connect(slot)

    button.setStyleSheet(JDXi.UI.Style.BUTTON_ROUND)
    button.setToolTip(tooltip)

    row.addWidget(button)
    # Clicking the part name works like clicking its button
    make_label_clickable(label, button)
    return row, button
