"""
title.py

Add a title container to the instrument
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.project import __display_name__, __program__


def add_title_container(central_widget):
    """add container for main title"""
    title_container = QWidget(central_widget)
    title_container.setGeometry(
        JDXi.UI.Dimensions.TITLE.X,
        JDXi.UI.Dimensions.TITLE.Y,
        JDXi.UI.Dimensions.TITLE.WIDTH,
        JDXi.UI.Dimensions.TITLE.HEIGHT,
    )
    title_container.setStyleSheet(JDXi.UI.Style.TRANSPARENT_WHITE)
    title_layout = QHBoxLayout()
    title_container.setLayout(title_layout)
    title_label = QLabel(__display_name__)  # JD-Xi Studio
    font = QFont()
    font.setFamilies(["Myriad Pro", "Segoe UI"])  # Qt 6+
    font.setStyleHint(QFont.SansSerif)
    font.setPixelSize(26)  # pixels: points grow with the screen's DPI (Windows) and overlapped the display
    font.setBold(True)  # Optionally make it bold

    # Apply the font to the QLabel
    title_label.setFont(font)
    title_layout.addWidget(title_label)
