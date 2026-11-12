"""
Program container for instrument UI
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.i18n import tr


def add_program_container(central_widget, create_program_buttons_row):
    """add program container"""
    program_container = QWidget(central_widget)
    program_container.setGeometry(
        JDXi.UI.Dimensions.PROGRAM.X,
        JDXi.UI.Dimensions.PROGRAM.Y,
        JDXi.UI.Dimensions.PROGRAM.WIDTH,
        JDXi.UI.Dimensions.PROGRAM.HEIGHT,
    )
    _row, program_down_button, program_up_button = create_program_buttons_row()
    nav_block(program_container, tr("Program"), program_down_button, program_up_button)
    return program_down_button, program_up_button


def create_program_buttons_row():
    """create program navigation buttons"""
    program_down_button = QPushButton("-")
    program_spacer = QLabel(" ")
    program_up_button = QPushButton("+")

    # create program up button
    program_up_button.setFixedSize(25, 25)
    program_up_button.setStyleSheet(JDXi.UI.Style.BUTTON_ROUND_SMALL)
    program_up_button.setToolTip(tr("Program Up: Navigate to the next program"))

    # create program down button
    program_down_button.setFixedSize(25, 25)
    program_down_button.setStyleSheet(JDXi.UI.Style.BUTTON_ROUND_SMALL)
    program_down_button.setToolTip(tr("Program Down: Navigate to the previous program"))

    # create program layout
    program_layout = QHBoxLayout()
    program_layout.addStretch()
    program_layout.addWidget(program_down_button)
    program_layout.addWidget(program_spacer)
    program_layout.addWidget(program_up_button)
    program_layout.addStretch()
    return program_layout, program_down_button, program_up_button


def nav_row(down_button, up_button) -> QHBoxLayout:
    """- and + centred with a fixed gap: the same in Program and Tone."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addStretch()
    row.addWidget(down_button)
    row.addSpacing(14)
    row.addWidget(up_button)
    row.addStretch()
    return row


def nav_block(container, label_text: str, down_button, up_button) -> None:
    """Label right above its - + buttons, top-aligned (Program and Tone look alike)."""
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    label = QLabel(label_text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(JDXi.UI.Style.TRANSPARENT)
    layout.addWidget(label)
    layout.addLayout(nav_row(down_button, up_button))
    layout.addStretch()
