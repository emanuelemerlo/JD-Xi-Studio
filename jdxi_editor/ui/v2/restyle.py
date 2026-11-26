"""
The new look for editors whose logic stays as it is (Pattern, MIDI file player).

restyle() gives an existing editor the new editors' appearance: a flat dark
background, panels as cards with the title in the accent colour, dark lists
and fields, and each round button + label pair turned into one flat button
with its icon and text (the same button object, so every connection and
reference in the editor keeps working).
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QGroupBox, QLabel, QLayout, QPushButton, QTabWidget, QWidget

from jdxi_editor.ui.style.editor_style import BODY_PROPERTY, FLAT_PROPERTY, SHEEN_PROPERTY


MODIFIED_SIGN = "\u270e"  # ✎ the pencil of the tabs (was a dot)
MODIFIED_COLOUR = "#ffb347"


def modified_icon():
    """The pencil on the tab of an editor with changes not saved."""
    import qtawesome as qta

    return qta.icon("mdi.pencil", color=MODIFIED_COLOUR)


_ARROWS: dict[str, str] = {}


def spin_arrow(direction: str) -> str:
    """A small light arrow ("up" / "down") as a PNG file for the style sheets
    (a style sheet takes an image file, not a drawing): made once, cached."""
    if direction in _ARROWS:
        return _ARROWS[direction]
    import tempfile
    from pathlib import Path

    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QImage, QPainter, QPolygonF

    image = QImage(20, 12, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#d6d8dd"))
    points = ([QPointF(4, 10), QPointF(16, 10), QPointF(10, 2)] if direction == "up"
              else [QPointF(4, 2), QPointF(16, 2), QPointF(10, 10)])
    painter.drawPolygon(QPolygonF(points))
    painter.end()
    folder = Path(tempfile.gettempdir()) / "jdxi_studio_ui"
    folder.mkdir(exist_ok=True)
    path = folder / f"spin_{direction}.png"
    image.save(str(path))
    _ARROWS[direction] = path.as_posix()  # forward slashes: what a style sheet's url() wants
    return _ARROWS[direction]


def spin_buttons_style() -> str:
    """Spin boxes' up and down buttons wide enough to hit, with visible arrows
    (they were thin slits with tiny dots)."""
    up, down = spin_arrow("up"), spin_arrow("down")
    return f"""
    QSpinBox, QDoubleSpinBox {{ padding-right: 24px; min-height: 22px; }}
    QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border; width: 22px; background: #26282d; border-left: 1px solid #3a3d44;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-position: top right; border-top-right-radius: 5px; border-bottom: 1px solid #3a3d44;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-position: bottom right; border-bottom-right-radius: 5px;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: #34373e; }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({up}); width: 10px; height: 6px; }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({down}); width: 10px; height: 6px; }}
    QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled,
    QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ image: none; }}
    """


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
        font-size: 13px;
    }}
    QComboBox QAbstractItemView {{ background: #1b1c1f; color: #e6e6e6; selection-background-color: #333333;
        font-size: 13px; }}
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
    """ + spin_buttons_style()  # after the rule that sets the spin boxes' padding


def _is_round(button: QPushButton) -> bool:
    from jdxi_editor.ui.style.jdxi import JDXiUIStyle

    from jdxi_editor.ui.text_size import scale_style

    return button.styleSheet() in (JDXiUIStyle.BUTTON_ROUND, scale_style(JDXiUIStyle.BUTTON_ROUND))


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
    mark = QLabel(f"{MODIFIED_SIGN} " + tr("Modified"))
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
        buttons.append(button("mdi.reload", tr("Restore the original values and discard this editor's changes"), reload))

    restore = buttons[2] if reload is not None else None

    def update() -> None:
        undo.setEnabled(history.can_undo())
        redo.setEnabled(history.can_redo())
        if restore is not None:  # nothing changed in this editor: nothing to restore
            restore.setEnabled(history.can_restore())

    history.stateChanged.connect(update)
    update()
    return mark, buttons


TOOLTIP_STYLE = (
    "QToolTip { background-color: #1f2025; color: #e8e8ea; border: 1px solid #3a3d44;"
    " padding: 4px 6px; }"
)


MESSAGE_BOX_STYLE = (
    "QMessageBox { background-color: #1b1c1f; }"
    " QMessageBox QLabel { color: #e6e8eb; font-size: 13px; background: transparent; }"
    " QMessageBox QPushButton { background: #26282d; color: #e6e8eb; border: 1px solid #3a3d44;"
    " border-radius: 6px; padding: 5px 14px; min-width: 72px; }"
    " QMessageBox QPushButton:hover { border-color: #6fcf97; }"
    " QMessageBox QPushButton:default { border-color: #6fcf97; }"
    " QMessageBox QCheckBox { color: #a3a6ad; }"
)


class _MessageBoxLook(QObject):
    """Every message box in the app's look as it is shown: dark, light text (the
    windows' style sheets made their text red on a light background)."""

    def eventFilter(self, watched, event):  # noqa: N802 (Qt)
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QMessageBox

        if event.type() == QEvent.Type.Show and isinstance(watched, QMessageBox):
            from jdxi_editor.ui.text_size import scale_style

            if watched.styleSheet() not in (MESSAGE_BOX_STYLE, scale_style(MESSAGE_BOX_STYLE)):
                watched.setStyleSheet(MESSAGE_BOX_STYLE)
            fit_buttons(watched)
        if event.type() == QEvent.Type.Show:
            fit_title(watched)
        return False


def fit_buttons(box) -> None:
    """Every button of a message box as wide as its text and padding: the
    width was worked out before the style sheet's padding, which then cut
    long labels («Scarta le modifiche»)."""
    from PySide6.QtWidgets import QPushButton

    for button in box.findChildren(QPushButton):
        needed = button.fontMetrics().horizontalAdvance(button.text().replace("&", "")) + 40
        if button.minimumWidth() < needed:
            button.setMinimumWidth(needed)


TITLE_BAR_EXTRA = 150  # icon, close button and margins of a title bar


def fit_title(window) -> None:
    """A dialog at least as wide as its title in the title bar (titles were cut,
    the Italian ones above all)."""
    from PySide6.QtWidgets import QDialog

    if not isinstance(window, QDialog) or not window.isWindow():
        return
    needed = window.fontMetrics().horizontalAdvance(window.windowTitle()) + TITLE_BAR_EXTRA
    if window.width() < needed:
        window.setMinimumWidth(min(needed, 900))
        window.resize(needed, window.height())


_message_box_look = None


def apply_message_box_style(app) -> None:
    global _message_box_look
    if _message_box_look is None:
        _message_box_look = _MessageBoxLook()
        app.installEventFilter(_message_box_look)


def apply_tooltip_style(app) -> None:
    """Dark tooltips with light text everywhere. A tooltip is a window of its
    own: an editor's style sheet does not reach it, so the colours are set on
    the application (style sheet and palette); without them Windows showed
    the settings page's tooltips black."""
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QToolTip

    palette = QToolTip.palette()
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1f2025"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e8e8ea"))
    palette.setColor(QPalette.ColorRole.Window, QColor("#1f2025"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e8e8ea"))
    QToolTip.setPalette(palette)
    from jdxi_editor.ui.text_size import scale_style

    if TOOLTIP_STYLE not in app.styleSheet() and scale_style(TOOLTIP_STYLE) not in app.styleSheet():
        app.setStyleSheet(app.styleSheet() + "\n" + TOOLTIP_STYLE)
    apply_message_box_style(app)
