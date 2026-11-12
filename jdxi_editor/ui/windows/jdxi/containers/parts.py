from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QLabel, QVBoxLayout, QWidget

from jdxi_editor.core.jdxi import JDXi
from jdxi_editor.core.synth.type import JDXiSynth
from jdxi_editor.ui.windows.jdxi.helpers.button_row import create_button_row
from picoui.specs.widgets import ButtonSpec
from jdxi_editor.i18n import tr


def create_parts_container(
    parent_widget,
    on_open_d1,
    on_open_d2,
    on_open_drums,
    on_open_analog,
    on_open_arp,
    on_select_synth,
):
    """Create the Parts Select container widget"""
    parts_container = QWidget(parent_widget)
    # On the panel (it was placed on the window, so it came apart from the
    # panel when the window grew); 20 px up: where it sat below the menu bar
    parts_container.setGeometry(
        JDXi.UI.Dimensions.PARTS.X,
        JDXi.UI.Dimensions.PARTS.Y - 20,
        JDXi.UI.Dimensions.PARTS.WIDTH,
        JDXi.UI.Dimensions.PARTS.HEIGHT,
    )
    parts_layout = QVBoxLayout(parts_container)
    parts_layout.setSpacing(3)

    parts_label = QLabel(tr("Parts Select"))
    parts_label.setStyleSheet(JDXi.UI.Style.PARTS_SELECT)
    parts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    parts_layout.addWidget(parts_label)

    digital1_row, digital1_button = create_button_row(
        ButtonSpec(label="Digital Synth 1", slot=on_open_d1)
    )
    digital2_row, digital2_button = create_button_row(
        ButtonSpec(label="Digital Synth 2", slot=on_open_d2)
    )
    drums_row, drums_button = create_button_row(
        ButtonSpec(label="Drums", slot=on_open_drums)
    )
    analog_row, analog_button = create_button_row(
        ButtonSpec(label="Analog Synth", slot=on_open_analog)
    )
    arp_row, arp_button = create_button_row(
        ButtonSpec(label="Arpeggiator", slot=on_open_arp)
    )

    # Connect buttons to synth selector
    analog_button.clicked.connect(lambda: on_select_synth(JDXiSynth.ANALOG_SYNTH))
    digital1_button.clicked.connect(lambda: on_select_synth(JDXiSynth.DIGITAL_SYNTH_1))
    digital2_button.clicked.connect(lambda: on_select_synth(JDXiSynth.DIGITAL_SYNTH_2))
    drums_button.clicked.connect(lambda: on_select_synth(JDXiSynth.DRUM_KIT))

    # Button group ensures one active selection
    button_group = QButtonGroup(parts_container)  # kept alive with the panel
    for b in [digital1_button, digital2_button, analog_button, drums_button]:
        button_group.addButton(b)
    button_group.setExclusive(True)

    # Arpeggiator lights while its editor is open (the instrument sets it)
    for row in [digital1_row, digital2_row, drums_row, analog_row, arp_row]:
        parts_layout.addLayout(row)

    parts_container.setStyleSheet(JDXi.UI.Style.TRANSPARENT)

    return parts_container, {
        "digital1": digital1_button,
        "digital2": digital2_button,
        "analog": analog_button,
        "drums": drums_button,
        "arp": arp_button,
    }
