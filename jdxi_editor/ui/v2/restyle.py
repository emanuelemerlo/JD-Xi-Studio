"""
The new look for editors whose logic stays as it is (Pattern, MIDI file player).

restyle() gives an existing editor the new editors' appearance: a flat dark
background, panels as cards with the title in the accent colour, dark lists
and fields, and each round button + label pair turned into one flat button
with its icon and text (the same button object, so every connection and
reference in the editor keeps working).
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QGroupBox, QLabel, QLayout, QPushButton, QTabWidget, QWidget

from jdxi_editor.ui.style.editor_style import BODY_PROPERTY, FLAT_PROPERTY, SHEEN_PROPERTY


def stylesheet(root_class: str, accent: str) -> str:
    return f"""
    {root_class} {{ background: #121214; }}
    QWidget {{ color: #e6e6e6; }}
    QLabel {{ color: #c9cbd1; background: transparent; }}
    QGroupBox {{
        background: #1b1c1f; border: 1px solid #2e3036; border-radius: 10px;
        margin-top: 0px; padding: 34px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: padding; subcontrol-position: top left; left: 14px; top: 12px;
        color: {accent}; font-size: 12px; font-weight: 700; letter-spacing: 2px; background: transparent;
    }}
    QTabWidget::pane {{ background: #1b1c1f; border: 1px solid #2a2d33; border-radius: 8px; }}
    QTabBar::tab {{ background: #1b1c1f; color: #c9cbd1; padding: 6px 14px; border: 1px solid #2a2d33;
        border-bottom: 0; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
    QTabBar::tab:selected {{ background: {accent}; color: #0e0f11; }}
    QPushButton {{ background: #1b1c1f; color: #e6e6e6; border: 1px solid #3a3d44; border-radius: 6px; padding: 5px 12px; }}
    QPushButton:hover {{ border-color: #6b6e75; }}
    QPushButton:checked {{ background: {accent}; color: #0e0f11; border-color: {accent}; }}
    QPushButton:disabled {{ color: #5a5d64; }}
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
        background: #121214; color: #ffffff; border: 1px solid #3a3d44; border-radius: 5px; padding: 2px 6px;
    }}
    QComboBox QAbstractItemView {{ background: #1b1c1f; color: #e6e6e6; selection-background-color: #333333; }}
    QSlider::groove:horizontal {{ height: 4px; background: #2a2d33; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: #ffffff; width: 12px; margin: -5px 0; border-radius: 6px; }}
    QScrollArea {{ background: transparent; border: 0; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QAbstractScrollArea {{ background: #121214; }}
    QScrollBar:horizontal, QScrollBar:vertical {{ background: #121214; border: 0; }}
    QScrollBar::handle {{ background: #3a3d44; border-radius: 4px; }}
    QCheckBox {{ color: #c9cbd1; }}
    QTableWidget, QListWidget, QTreeWidget {{ background: #121214; color: #e6e6e6; border: 1px solid #2a2d33; }}
    QHeaderView::section {{ background: #1b1c1f; color: #a3a6ad; border: 0; padding: 4px; }}
    """


def _is_round(button: QPushButton) -> bool:
    from jdxi_editor.ui.style.jdxi import JDXiUIStyle

    return button.styleSheet() == JDXiUIStyle.BUTTON_ROUND


def _layout_of(widget: QWidget) -> tuple[QLayout, int] | tuple[None, int]:
    parent = widget.parentWidget()
    if parent is None or parent.layout() is None:
        return None, -1

    def search(layout: QLayout):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() is widget:
                return layout, i
            if item.layout() is not None:
                found = search(item.layout())
                if found[0] is not None:
                    return found
        return None, -1

    return search(parent.layout())


def _label_row(widget) -> tuple[str, QIcon | None] | None:
    """(text, icon) of an icon + text label row, or None when *widget* is not one."""
    if widget is None or isinstance(widget, QPushButton):
        return None
    if isinstance(widget, QLabel):
        labels = [widget]
    elif widget.layout() is not None and not widget.findChildren(QPushButton):
        labels = widget.findChildren(QLabel)
    else:
        return None
    text, icon = "", None
    for label in labels:
        pixmap = label.pixmap()
        if pixmap is not None and not pixmap.isNull():
            icon = QIcon(pixmap)
        elif label.text():
            text = label.text()
    return (text, icon) if text or icon is not None else None


def _flatten(button: QPushButton, label: tuple[str, QIcon | None] | None) -> None:
    button.setStyleSheet("")
    button.setMinimumSize(QSize(0, 28))
    button.setMaximumSize(QSize(16777215, 16777215))
    if label is not None:
        text, icon = label
        if text:
            button.setText(text)
        if icon is not None:
            button.setIcon(icon)
            button.setIconSize(QSize(16, 16))
    button.setMinimumWidth(button.sizeHint().width())  # the whole name, not cut


def flatten_round_buttons(root: QWidget) -> int:
    """Each round button and its icon + label row become one flat button; returns how many.

    The label row is the unused neighbour in the layout: the one before the
    button when the layout puts labels first, otherwise the one after.
    """
    rounds = [b for b in root.findChildren(QPushButton) if _is_round(b)]
    layouts: dict[int, QLayout] = {}
    for button in rounds:
        layout, _ = _layout_of(button)
        if layout is not None:
            layouts[id(layout)] = layout
    done = set()
    for layout in layouts.values():
        used = set()
        widgets = [layout.itemAt(i).widget() for i in range(layout.count())]
        for i, widget in enumerate(widgets):
            if not (isinstance(widget, QPushButton) and _is_round(widget)):
                continue
            label = None
            for j in (i - 1, i + 1):
                if 0 <= j < len(widgets) and j not in used:
                    found = _label_row(widgets[j])
                    if found is not None:
                        used.add(j)
                        widgets[j].hide()
                        label = found
                        break
            _flatten(widget, label)
            done.add(id(widget))
    for button in rounds:  # buttons outside a layout
        if id(button) not in done:
            _flatten(button, None)
    return len(rounds)


def restyle(editor: QWidget, accent: str) -> None:
    """The new look for *editor* (call after its widgets are built)."""
    editor.setProperty(BODY_PROPERTY, False)
    editor.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    for panel in editor.findChildren(QWidget):
        if isinstance(panel, (QGroupBox, QTabWidget)):
            panel.setProperty(FLAT_PROPERTY, True)  # no glossy sheen
            panel.setProperty(SHEEN_PROPERTY, False)
    editor.setStyleSheet(stylesheet(type(editor).__name__, accent))
    flatten_round_buttons(editor)


def title_badge(text: str, accent: str) -> QLabel:
    """The editor's name as a badge in its colour, as at the top of the other new editors."""
    label = QLabel(text.upper())
    label.setObjectName("v2Title")
    label.setStyleSheet(
        f"QLabel#v2Title {{ background: {accent}; color: #0e0f11; border-radius: 6px;"
        " padding: 3px 12px; font-size: 16px; font-weight: 800; letter-spacing: 2px; }"
    )
    label.setSizePolicy(label.sizePolicy().horizontalPolicy(), label.sizePolicy().verticalPolicy())
    return label


def edit_controls(editor, reload=None):
    """A "Modified" mark and the Undo / Redo (/ Reload) buttons for an editor with a history."""
    import qtawesome as qta
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QToolButton

    from jdxi_editor.i18n import tr

    history = editor.history
    mark = QLabel(tr("● Modified"))
    mark.setObjectName("v2Modified")
    mark.setStyleSheet("QLabel#v2Modified { color: #ffb347; font-size: 12px; font-weight: 700; padding-left: 8px; }")
    mark.setToolTip(tr("Changes not saved to a file: changing the sound from the program asks first"))
    mark.setVisible(history.modified)
    history.modifiedChanged.connect(mark.setVisible)

    def button(icon: str, tip: str, slot) -> QToolButton:
        b = QToolButton()
        b.setObjectName("v2EditButton")
        b.setIcon(qta.icon(icon, color="#e6e6e6", color_disabled="#55585f"))
        b.setIconSize(QSize(20, 20))
        b.setToolTip(tip)
        b.setAutoRaise(True)
        b.setStyleSheet(
            "QToolButton#v2EditButton { border: 1px solid #3a3d44; border-radius: 5px; padding: 3px; background: #1b1c1f; }"
            "QToolButton#v2EditButton:hover { border-color: #ff2a1a; }"
            "QToolButton#v2EditButton:disabled { border-color: #26282d; }"
        )
        b.clicked.connect(slot)
        return b

    undo = button("mdi.undo", tr("Undo the last change (Ctrl+Z)"), history.undo)
    redo = button("mdi.redo", tr("Redo (Ctrl+Y)"), history.redo)
    buttons = [undo, redo]
    if reload is not None:
        buttons.append(button("mdi.reload", tr("Reload the preset: back to the sound as stored, the changes are lost"), reload))

    def update() -> None:
        undo.setEnabled(history.can_undo())
        redo.setEnabled(history.can_redo())

    history.stateChanged.connect(update)
    update()
    return mark, buttons
