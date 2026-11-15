

def test_notes_start_the_lines_in_the_middle_of_the_first_step():
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

    from jdxi_editor.ui.widgets.pattern.step_guide import StepGuide

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    column = QVBoxLayout(host)
    buttons = [QPushButton() for _ in range(16)]
    guide = StepGuide(lambda: buttons, notes=True)
    row = QHBoxLayout()
    for b in buttons:
        b.setFixedSize(30, 30)
        row.addWidget(b)
    column.addWidget(guide)
    column.addLayout(row)
    host.show()
    app.processEvents()
    def left(i):
        return guide.mapFrom(host, buttons[i].mapTo(host, buttons[i].rect().topLeft())).x()

    x1, x2, _y = guide.segments()[0]
    assert x1 == (left(0) + left(0) + 29) // 2 + 2  # from the middle of step 1 (its note on the left half)
    assert x2 == left(2) + 29
    host.close()
