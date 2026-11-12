from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.ui.widgets.editor.helper import create_layout_with_items
from jdxi_editor.i18n import tr


def add_tone_container(
    central_widget, create_tone_buttons_horizontal_layout, previous_tone, next_tone
):
    """For tone buttons"""
    tone_container = QWidget(central_widget)
    tone_container.setGeometry(
        JDXi.UI.Dimensions.TONE.X,
        JDXi.UI.Dimensions.TONE.Y,
        JDXi.UI.Dimensions.TONE.WIDTH,
        JDXi.UI.Dimensions.TONE.HEIGHT,
    )
    tone_container.setStyleSheet(JDXi.UI.Style.TRANSPARENT)
    _row, tone_down_button, tone_up_button = create_tone_buttons_horizontal_layout(previous_tone, next_tone)
    from jdxi_editor.ui.windows.jdxi.containers.program import nav_block

    nav_block(tone_container, tr("Tone"), tone_down_button, tone_up_button)
    return tone_down_button, tone_up_button


def create_tone_buttons_row(previous_tone, next_tone):
    # Create Tone navigation buttons
    tone_down_button = QPushButton("-")
    tone_spacer = QLabel(" ")
    tone_up_button = QPushButton("+")

    # Calculate size for tone buttons
    tone_button_diameter = 25

    # --- Create tone up button
    tone_up_button.setFixedSize(tone_button_diameter, tone_button_diameter)
    tone_up_button.setStyleSheet(JDXi.UI.Style.BUTTON_ROUND_SMALL)
    tone_up_button.setToolTip(tr("Tone Up: Navigate to the next preset/tone"))

    # --- Create tone down button
    tone_down_button.setFixedSize(tone_button_diameter, tone_button_diameter)
    tone_down_button.setStyleSheet(JDXi.UI.Style.BUTTON_ROUND_SMALL)
    tone_down_button.setToolTip(tr("Tone Down: Navigate to the previous preset/tone"))

    # --- Connect buttons to functions
    tone_down_button.clicked.connect(previous_tone)
    tone_up_button.clicked.connect(next_tone)

    # --- Button layout
    button_layout = create_layout_with_items(
        [tone_down_button, tone_spacer, tone_up_button]
    )
    return button_layout, tone_down_button, tone_up_button
