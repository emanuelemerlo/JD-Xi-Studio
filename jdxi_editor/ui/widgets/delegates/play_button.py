from PySide6.QtCore import QSize
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from jdxi_editor.i18n import tr
from jdxi_editor.ui.widgets.delegates.paint import paint_cell_button


class PlayButtonDelegate(QStyledItemDelegate):
    """Delegate for Play button in table."""

    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback

    def paint(self, painter, option, index):
        """Draw a play button."""
        if option.state & QStyle.StateFlag.State_Enabled:
            paint_cell_button(painter, option, "▶ " + tr("Play"))

    def editorEvent(self, event, model, option, index):
        """Handle button click."""
        if event.type() == event.Type.MouseButtonPress:
            if option.rect.contains(event.pos()):
                if self.play_callback:
                    self.play_callback(index)
                return True
        return super().editorEvent(event, model, option, index)

    def sizeHint(self, option, index):
        """Return button size."""
        return QSize(80, 30)
