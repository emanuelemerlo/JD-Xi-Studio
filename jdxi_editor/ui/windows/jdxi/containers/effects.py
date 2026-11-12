"""
Effects buttons
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.ui.windows.jdxi.helpers.button_row import create_button_row
from picoui.specs.widgets import ButtonSpec


def add_effects_container(central_widget, open_vocal_fx, open_effects):
    """Effects button in top row"""
    fx_container = QWidget(central_widget)
    fx_container.setGeometry(
        JDXi.UI.Dimensions.EFFECTS.X,
        JDXi.UI.Dimensions.EFFECTS.Y,
        JDXi.UI.Dimensions.EFFECTS.WIDTH,
        JDXi.UI.Dimensions.EFFECTS.HEIGHT,
    )
    fx_layout = QVBoxLayout(fx_container)
    vocal_effects_row, vocal_effects_button = create_button_row(
        ButtonSpec(label="Vocoder", slot=open_vocal_fx),
        vertical=True,
    )
    effects_row, effects_button = create_button_row(
        ButtonSpec(label="Effects", slot=open_effects),
        vertical=True,
        spacing=10,
    )
    vocal_effects_row.setSpacing(3)
    fx_layout.setSpacing(6)
    fx_layout.addLayout(vocal_effects_row)
    fx_layout.addLayout(effects_row)
    fx_container.setStyleSheet(JDXi.UI.Style.TRANSPARENT)
    # each label centred over its button
    for row in (vocal_effects_row, effects_row):
        for i in range(row.count()):
            widget = row.itemAt(i).widget()
            if widget is not None:
                row.setAlignment(widget, Qt.AlignmentFlag.AlignHCenter)
                if isinstance(widget, QLabel):
                    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    # They open an editor: momentary, not left lit (they stayed pressed)
    for button in (vocal_effects_button, effects_button):
        button.setCheckable(False)
    return vocal_effects_button, effects_button
