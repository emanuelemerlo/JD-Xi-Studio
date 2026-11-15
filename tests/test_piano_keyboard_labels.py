"""The drum names above the keyboard are centred on their keys."""

from PySide6.QtWidgets import QApplication


def test_drum_labels_over_their_keys():
    from jdxi_editor.ui.widgets.piano.keyboard import PianoKeyboard

    app = QApplication.instance() or QApplication([])
    keyboard = PianoKeyboard()
    keyboard.show()
    app.processEvents()
    keyboard.place_drum_labels()
    assert keyboard.drum_labels[36].text() == "BD1" and keyboard.drum_labels[37].text() == "RIM"
    for note, label in keyboard.drum_labels.items():
        key = keyboard._keys_by_note[note]
        key_x = key.mapTo(keyboard, key.rect().center()).x()
        label_x = label.mapTo(keyboard, label.rect().center()).x()
        assert abs(key_x - label_x) <= 1, (label.text(), key_x, label_x)
    black = keyboard.drum_labels[37].y()
    assert black < keyboard.drum_labels[36].y()  # black keys' names on the upper line
    keyboard.close()
