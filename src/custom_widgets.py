import os
import sys

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget, QLabel, QHBoxLayout, QStyle, QToolButton, QListWidget, QSizePolicy
)
from PySide6.QtGui import QFont, QColor, QPalette, QMouseEvent, QFontMetrics
from PySide6.QtCore import Qt, QSize

import pyperclip
from playsound3 import playsound


class DeselectableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if item is not None and item.isSelected():
            item.setSelected(False)
        else:
            super().mousePressEvent(event)


class IPACellWidget(QWidget):
    """
    A custom widget for a single IPA character cell.
    It contains the IPA text and a speaker button.
    The widget itself can be clicked to toggle its active state (background color).
    The speaker button can be clicked to play a sound.
    """

    def __init__(self, ipa_text, parent=None):
        super().__init__(None)
        self.ipa_text = ipa_text
        self.is_active = True
        self.parent = parent

        # --- Create Palettes ---
        self.setAutoFillBackground(True)
        self.normal_palette = self.palette()
        self.grey_palette = QPalette()
        self.grey_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))

        # --- Create Widgets ---
        self.label = QLabel(self.ipa_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(24)

        font = QFont("Arial", 10)
        self.label.setFont(font)
        font_metrics = QFontMetrics(font)

        tallest_possible_string = "t͡s"
        text_height = font_metrics.boundingRect(tallest_possible_string).height() + 4

        self.update_background()

        if ipa_text and ipa_text != "etc":
            self.speaker_button = QToolButton()
            self.speaker_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

            self.speaker_button.setFixedSize(QSize(text_height, text_height))
            self.speaker_button.setIconSize(QSize(text_height - 4, text_height - 4))
            self.speaker_button.setToolTip(f"Play sound for {self.ipa_text}")

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)
        if ipa_text and ipa_text != "etc":
            layout.addWidget(self.speaker_button, 0)

        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(1)
        self.setLayout(layout)

        self.setFixedHeight(text_height + 2)

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)

        # --- Connections ---
        if ipa_text and ipa_text != "etc":
            self.speaker_button.clicked.connect(self.play_sound)
        else:
            self.speaker_button = None

    def update_background(self):
        """Updates the widget's background based on the is_active state."""
        if self.is_active:
            self.setPalette(self.normal_palette)
            self.label.setStyleSheet("")
        else:
            self.setPalette(self.grey_palette)
            self.label.setStyleSheet("color: #A3A3A3;")

    def mousePressEvent(self, event):
        """Overrides the mouse press event to toggle the cell's active state."""
        if not self.speaker_button:
            return

        child = self.childAt(event.position().toPoint())
        if child == self.speaker_button:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.copy_to_clipboard()

        super().mousePressEvent(event)

    def copy_to_clipboard(self):
        pyperclip.copy(self.ipa_text)

    def play_sound(self):
        if sys.platform == "win32":
            path = self.parent.path.split('\\')
        else:
            path = self.parent.path.split('/')
        path.remove('src')

        try:
            path.remove('src')
        except ValueError:
            pass

        if os.path.exists(f"{'\\'.join(path)}\\assets\\ipa_sounds"):
            playsound(f"{'\\'.join(path)}\\assets\\ipa_sounds\\{self.label.text()}.mp3", block=False)
        else:
            playsound(f"assets/ipa_sounds/{self.label.text()}.mp3", block=False)


class IPATable(QTableWidget):
    def __init__(self, table, rows, cols, parent, variant=0):
        super().__init__()

        self.table = table
        self.parent = parent
        self.variant = variant

        self.setRowCount(rows)
        self.setColumnCount(cols)

        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.header_font = QFont("Arial", 10)
        self.header_font.setBold(True)

        self.populate_table()
        self.resize_table()

    def create_item(self, text, is_header=False):
        """Helper function to create a centered QTableWidgetItem."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_header:
            item.setFont(self.header_font)
        return item

    def populate_table(self):
        """Fills the table with data from the TABLE_DATA list."""
        for r_idx, row_data in enumerate(self.table):
            for c_idx, cell_text in enumerate(row_data):

                if cell_text is None:
                    continue

                if self.variant == 0:
                    is_header = (r_idx < 1) or (c_idx == 0)
                elif self.variant == 1:
                    is_header = r_idx < 1
                else:
                    is_header = False

                is_special_cell = cell_text == "/"
                cell_text = "" if cell_text == "/" else cell_text

                if is_header or is_special_cell:
                    item = self.create_item(cell_text, is_header)

                    self.setItem(r_idx, c_idx, item)
                else:
                    cell = QWidget()
                    container = QHBoxLayout(cell)

                    if self.variant == 0:
                        if cell_text.split("/")[0] != " ":
                            cell_widget_l = IPACellWidget(cell_text.split("/")[0], self.parent)
                        else:
                            cell_widget_l = QLabel("           ")

                        if cell_text.split("/")[1] != " ":
                            cell_widget_r = IPACellWidget(cell_text.split("/")[1], self.parent)
                        else:
                            cell_widget_r = QLabel("           ")

                        container.addWidget(cell_widget_l)
                        container.addWidget(cell_widget_r)

                    elif self.variant == 1:
                        cell_widget = IPACellWidget(cell_text, self.parent)

                        container.addWidget(cell_widget)

                    self.setCellWidget(r_idx, c_idx, cell)

    def resize_table(self):
        """Resizes all columns and rows to fit their content."""
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.setColumnWidth(0, self.columnWidth(0) + 15)

        total_width = sum(self.columnWidth(c) for c in range(self.columnCount()))
        total_height = sum(self.rowHeight(r) for r in range(self.rowCount()))

        self.setMinimumSize(total_width + 2, total_height + 2)
