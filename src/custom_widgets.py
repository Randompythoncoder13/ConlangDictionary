import os
import sys

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget, QLabel, QHBoxLayout, QStyle, QToolButton, QListWidget, QSizePolicy,
    QApplication, QLineEdit, QPushButton, QVBoxLayout, QGridLayout, QScrollArea
)
from PySide6.QtGui import QFont, QColor, QPalette, QMouseEvent, QFontMetrics
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QEvent, QRect

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


class IPAPickerPopup(QWidget):
    character_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.ipa_categories = {
            "Consonants (Pulmonic)": [
                ['p', 'b', 't', 'd', 'ʈ', 'ɖ', 'c', 'ɟ'],
                ['k', 'g', 'q', 'ɢ', 'ʔ', 'm', 'ɱ', 'n'],
                ['ɳ', 'ɲ', 'ŋ', 'ɴ', 'ʙ', 'r', 'ʀ', 'ⱱ'],
                ['ɾ', 'ɽ', 'ɸ', 'β', 'f', 'v', 'θ', 'ð'],
                ['s', 'z', 'ʃ', 'ʒ', 'ʂ', 'ʐ', 'ç', 'ʝ'],
                ['x', 'ɣ', 'χ', 'ʁ', 'ħ', 'ʕ', 'h', 'ɦ'],
                ['ɬ', 'ɮ', 'ʋ', 'ɹ', 'ɻ', 'j', 'ɰ', 'l'],
                ['ɭ', 'ʎ', 'ʟ']
            ],
            "Consonants (Non-Pulmonic & Other)": [
                ['ʘ', 'ɓ', 'ǀ', 'ǃ', 'ʄ', 'ǂ', 'ɠ', 'ǁ'],
                ['ʛ', 'ʍ', 'w', 'ɥ', 'ʜ', 'ʢ', 'ʡ', 'ɕ'],
                ['ʑ', 'ɺ', 'ɧ']
            ],
            "Vowels": [
                ['i', 'y', 'ɨ', 'ʉ', 'ɯ', 'u', 'ɪ', 'ʏ'],
                ['ʊ', 'e', 'ø', 'ɘ', 'ɵ', 'ɤ', 'o', 'ə'],
                ['ɛ', 'œ', 'ɜ', 'ɞ', 'ʌ', 'ɔ', 'æ', 'ɐ'],
                ['a', 'ɶ', 'ɑ', 'ɒ']
            ],
            "Diacritics": [
                ['◌̥', '◌̬', "◌̩", "◌̯", "◌̆", "◌ʰ", '◌ʷ', '◌ʲ'],
                ['◌ˠ', '◌ˤ', '◌̃', "◌͡◌", "ː", "ˑ", "ʼ"]
            ]
        }
        self.init_ui()

    def init_ui(self):
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        for category_name, symbols_grid in self.ipa_categories.items():
            header = QLabel(category_name)
            header.setStyleSheet("font-weight: bold; text-decoration: underline;")
            content_layout.addWidget(header)

            grid_widget = QWidget()
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setSpacing(4)
            grid_layout.setContentsMargins(0, 0, 0, 0)

            for row_idx, row_data in enumerate(symbols_grid):
                for col_idx, symbol in enumerate(row_data):
                    btn = QPushButton(symbol)
                    btn.setFixedSize(36, 36)
                    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

                    clean_symbol = symbol.replace('◌', '')
                    btn.clicked.connect(lambda checked=False, s=clean_symbol: self.on_button_clicked(s))

                    grid_layout.addWidget(btn, row_idx, col_idx)

            content_layout.addWidget(grid_widget)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        self.setFixedSize(340, 320)

    def on_button_clicked(self, symbol):
        self.character_selected.emit(symbol)


class IPALineEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter word or sound change rule...")

        self.ipa_btn = QPushButton("IPA")
        self.ipa_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.ipa_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout.addWidget(self.text_input)
        layout.addWidget(self.ipa_btn)

        self.ipa_picker = IPAPickerPopup(self)

        self.ipa_btn.clicked.connect(self.show_ipa_picker)
        self.ipa_picker.character_selected.connect(self.insert_ipa_character)

        QApplication.instance().installEventFilter(self)

    def text(self):
        return self.text_input.text()

    def setText(self, text):
        self.text_input.setText(text)

    def show_ipa_picker(self):
        if self.ipa_picker.isVisible():
            self.ipa_picker.hide()
            return

        button_pos = self.ipa_btn.mapToGlobal(QPoint(0, 0))
        popup_x = button_pos.x()
        popup_y = button_pos.y() + self.ipa_btn.height()

        self.ipa_picker.move(popup_x, popup_y)
        self.ipa_picker.show()

    def insert_ipa_character(self, character):
        self.text_input.insert(character)
        self.text_input.setFocus()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and self.ipa_picker.isVisible():
            click_pos = event.globalPosition().toPoint()

            if not self.ipa_picker.geometry().contains(click_pos):
                btn_pos = self.ipa_btn.mapToGlobal(QPoint(0, 0))
                btn_rect = QRect(btn_pos, self.ipa_btn.size())

                if not btn_rect.contains(click_pos):
                    self.ipa_picker.hide()

        return super().eventFilter(obj, event)

    def setPlaceholderText(self, text):
        self.text_input.setPlaceholderText(text)

    def clear(self):
        self.text_input.clear()


class LetterBlock(QWidget):
    move_left_sig = Signal(QWidget)
    move_right_sig = Signal(QWidget)
    delete_sig = Signal(QWidget)

    def __init__(self, letter, ipa, custom_font_family=None):
        super().__init__()
        self.letter = letter
        self.ipa = ipa

        self.custom_font = custom_font_family

        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            LetterBlock {
                border: 1px solid #777777;
                border-radius: 8px;
                background-color: rgba(128, 128, 128, 0.1);
            }
        """)
        self.setFixedSize(140, 160)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- Top Layout: Delete Button ---
        top_layout = QHBoxLayout()
        self.btn_delete = QPushButton("✕")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setStyleSheet("border: none; color: #ff4444; font-weight: bold;")
        self.btn_delete.clicked.connect(lambda: self.delete_sig.emit(self))
        top_layout.addStretch()
        top_layout.addWidget(self.btn_delete)
        main_layout.addLayout(top_layout)

        # --- Middle Layout: Upper and Lower Case Letters ---
        letters_layout = QHBoxLayout()

        self.lbl_big_upper = QLabel()
        self.lbl_big_upper.setAlignment(Qt.AlignCenter | Qt.AlignRight)

        self.lbl_big_lower = QLabel()
        self.lbl_big_lower.setAlignment(Qt.AlignCenter | Qt.AlignLeft)

        letters_layout.addWidget(self.lbl_big_upper)
        letters_layout.addWidget(self.lbl_big_lower)
        main_layout.addLayout(letters_layout)

        # --- Middle Layout: Small IPA Label ---
        self.lbl_small = QLabel()
        self.lbl_small.setAlignment(Qt.AlignCenter)
        self.lbl_small.setStyleSheet("color: gray;")
        main_layout.addWidget(self.lbl_small)

        main_layout.addStretch()

        # --- Bottom Layout: Navigation Arrows ---
        bottom_layout = QHBoxLayout()
        self.btn_left = QPushButton("◀")
        self.btn_right = QPushButton("▶")
        self.btn_left.setFixedSize(30, 30)
        self.btn_right.setFixedSize(30, 30)

        self.btn_left.clicked.connect(lambda: self.move_left_sig.emit(self))
        self.btn_right.clicked.connect(lambda: self.move_right_sig.emit(self))

        bottom_layout.addWidget(self.btn_left)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_right)
        main_layout.addLayout(bottom_layout)

        self.update_display(False)

    def update_display(self, use_custom_font):
        # Determine which font to use
        font = self.custom_font if use_custom_font else QApplication.font()
        font.setPointSize(24)

        # Apply font to both big labels
        self.lbl_big_upper.setFont(font)
        self.lbl_big_lower.setFont(font)

        # Force uppercase for the left label, lowercase for the right label
        self.lbl_big_upper.setText(self.letter.upper())
        self.lbl_big_lower.setText(self.letter.lower())

        # Update the IPA label
        if use_custom_font:
            self.lbl_small.setText(f"{self.letter.upper()} /{self.ipa}/")
        else:
            self.lbl_small.setText(f"/{self.ipa}/")