"""Panel names shrink a little where a wider font would cut them, never grow."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from jdxi_editor.ui.style.fit import fit_text


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("sheet", ["", "font-size: 20px; font-weight: bold;", "QLabel { font-size: 20px; }"])
def test_a_long_name_is_made_to_fit(app, sheet):
    label = QLabel("Digital Synth 1")
    label.setStyleSheet(sheet)
    font = label.font()
    font.setPixelSize(20)
    label.setFont(font)
    label.setFixedWidth(80)
    label.ensurePolished()
    assert label.fontMetrics().horizontalAdvance(label.text()) > 80
    assert fit_text(label)
    label.ensurePolished()
    assert label.fontMetrics().horizontalAdvance(label.text()) <= 80


def test_a_name_that_fits_is_left_alone(app):
    label = QLabel("Amp")
    label.setFixedWidth(200)
    before = label.font().pixelSize(), label.styleSheet()
    assert not fit_text(label)
    assert (label.font().pixelSize(), label.styleSheet()) == before
