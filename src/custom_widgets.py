from PyQt6.QtWidgets import QListWidget
from PyQt6.QtGui import QMouseEvent


class DeselectableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if item is not None and item.isSelected():
            # If the clicked item is already selected, deselect it
            item.setSelected(False)
        else:
            # Otherwise, let the default behavior handle selection
            super().mousePressEvent(event)
