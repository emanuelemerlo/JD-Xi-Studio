"""repolish: a style sheet applied again after a property changed, also when PySide
hands back a stale object for widget.style() (seen on macOS)."""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QPushButton

from jdxi_editor.ui.style.editor_style import repolish


def test_repolish_applies_the_rule_of_a_new_property():
    app = QApplication.instance() or QApplication([])  # noqa: F841
    button = QPushButton("x")
    button.setStyleSheet('QPushButton { color: #00ff00; } QPushButton[unused="true"] { color: #ff0000; }')
    button.ensurePolished()
    assert button.palette().color(QPalette.ColorRole.ButtonText).name() == "#00ff00"
    button.setProperty("unused", True)
    repolish(button)
    assert button.palette().color(QPalette.ColorRole.ButtonText).name() == "#ff0000"


class Stale:  # what widget.style() returned on macOS: another object's wrapper
    pass


def test_repolish_with_a_stale_style_object(monkeypatch):
    app = QApplication.instance() or QApplication([])  # noqa: F841
    button = QPushButton("x")
    monkeypatch.setattr(button, "style", lambda: Stale())
    button.setStyleSheet('QPushButton { color: #00ff00; } QPushButton[unused="true"] { color: #ff0000; }')
    button.ensurePolished()
    assert button.palette().color(QPalette.ColorRole.ButtonText).name() == "#00ff00"
    button.setProperty("unused", True)
    repolish(button)  # no AttributeError, and the rule applies
    assert button.palette().color(QPalette.ColorRole.ButtonText).name() == "#ff0000"
