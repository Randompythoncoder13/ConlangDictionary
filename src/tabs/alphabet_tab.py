import json

from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QScrollArea, QLayout, QStyle, QMessageBox,
    QProgressDialog
)
from PySide6.QtGui import QFont

from custom_widgets import LetterBlock, IPALineEdit
from dialogs import WarningDialog


class AlphabetTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.font_exist = self.main_app.font_exists
        self.font = QFont(self.main_app.font)
        self.custom_font_on = self.main_app.custom_font_on

        self.blocks = []
        self.sort_data = []

        self.translators = [{}, {}, []]

        self.init_ui()

        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        control_layout = QHBoxLayout()

        self.input_letter = QLineEdit()
        self.input_letter.setPlaceholderText("Letter (e.g., A)")

        self.input_ipa = IPALineEdit()
        self.input_ipa.setPlaceholderText("IPA (e.g., æ)")

        btn_add = QPushButton("Add to Alphabet")
        btn_add.clicked.connect(self.add_block)

        btn_font = QPushButton("Toggle Custom Font")
        btn_font.clicked.connect(self.toggle_font)

        btn_generate_ipa = QPushButton("Populate Empty IPA Fields")
        btn_generate_ipa.clicked.connect(self.populate_ipa)

        control_layout.addWidget(self.input_letter)
        control_layout.addWidget(self.input_ipa)
        control_layout.addWidget(btn_add)
        control_layout.addWidget(btn_font)
        control_layout.addWidget(btn_generate_ipa)
        control_layout.addStretch()

        main_layout.addLayout(control_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)

        self.flow_widget = QWidget()
        self.flow_layout = FlowLayout(self.flow_widget, margin=10, h_spacing=10, v_spacing=10)
        self.scroll_area.setWidget(self.flow_widget)

        main_layout.addWidget(self.scroll_area)

    def add_block(self, flag=False, data=None):
        if not flag:
            letter = self.input_letter.text().strip().lower()
            ipa = self.input_ipa.text().strip()
        else:
            letter = data["letter"]
            ipa = data["ipa"]

        if not letter:
            return

        if len(letter) > 1:
            QMessageBox.warning(self, "Error", "Please enter only letter")
            return

        if any(block.letter == letter for block in self.blocks):
            if not flag:
                QMessageBox.warning(self, "Error", f"You can't have two blocks with the same letter.")
            return

        if self.font_exist:
            block = LetterBlock(letter, ipa, self.font)
        else:
            block = LetterBlock(letter, ipa)

        if self.font_exist:
            block.update_display(self.custom_font_on)

        block.move_left_sig.connect(self.move_block_left)
        block.move_right_sig.connect(self.move_block_right)
        block.delete_sig.connect(self.delete_block)

        self.blocks.append(block)
        self.refresh_layout()

        self.input_letter.clear()
        self.input_ipa.clear()
        self.input_letter.setFocus()

    def move_block_left(self, block):
        idx = self.blocks.index(block)
        if idx > 0:
            self.blocks[idx], self.blocks[idx - 1] = self.blocks[idx - 1], self.blocks[idx]
            self.refresh_layout()

    def move_block_right(self, block):
        idx = self.blocks.index(block)
        if idx < len(self.blocks) - 1:
            self.blocks[idx], self.blocks[idx + 1] = self.blocks[idx + 1], self.blocks[idx]
            self.refresh_layout()

    def delete_block(self, block):
        dialog = WarningDialog("Are you sure you wish to delete this?", self)
        if dialog.exec():
            self.blocks.remove(block)
            block.deleteLater()
            self.refresh_layout()

    def refresh_layout(self):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for block in self.blocks:
            self.flow_layout.addWidget(block)

        self.update_data()

    def toggle_font(self, no_recur=False):
        if not no_recur:
            self.main_app.toggle_font("alpha")

        self.custom_font_on = self.main_app.custom_font_on

        for block in self.blocks:
            if self.font_exist:
                block.update_display(self.custom_font_on)

        self.refresh_layout()

    def update_data(self):
        data = []
        self.translators = [{}, {}, []]

        for block in self.blocks:
            data.append({"letter": block.letter, "ipa": block.ipa})

            self.translators[0][block.letter] = block.ipa
            self.translators[1][block.ipa] = block.letter
            self.translators[2].append(block.letter)

        if self.translators[2]:
            self.main_app.custom_alphabet = self.translators[2]
        else:
            self.main_app.custom_alphabet = [
                "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
                "u", "v", "w", "x", "y", "z",
            ]

        try:
            self.main_app.tab_dictionary.update_word_display()
        except AttributeError:
            pass

        self.sort_data = data

        self.save_data()

    def save_data(self):
        with open(f"{self.main_app.app_data_dir}\\alphabet.json", "w") as file:
            json.dump(self.sort_data, file, indent=4)

    def load_data(self):
        self.blocks = []
        self.sort_data = []
        self.translators = [{}, {}, []]

        try:
            with open(f"{self.main_app.app_data_dir}\\alphabet.json", "r") as file:
                self.sort_data = json.load(file)

                for data in self.sort_data:
                    self.add_block(True, data)

                    self.translators[0][data["letter"]] = data["ipa"]
                    self.translators[1][data["ipa"]] = data["letter"]
                    self.translators[2].append(data["letter"])

            if self.translators[2]:
                self.main_app.custom_alphabet = self.translators[2]
            else:
                self.main_app.custom_alphabet = [
                    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
                    "u", "v", "w", "x", "y", "z",
                ]

            self.refresh_layout()

        except FileNotFoundError:
            self.refresh_layout()
        except json.decoder.JSONDecodeError as e:
            self.refresh_layout()
            print(e)

    def populate_ipa(self):
        dialog = WarningDialog("This will write the default IPA you have made below to all empty IPA fields. Any ones manually entered will remain the same. Do you wish to continue?", self)
        if dialog.exec():
            progress = QProgressDialog("Populating IPA Fields...", "Cancel", 0, len(self.main_app.dictionary), self)
            progress.setWindowTitle("Please Wait")
            progress.setWindowModality(Qt.WindowModal)  # Blocks input to the main window
            progress.setMinimumDuration(0)

            for word in self.main_app.dictionary:
                if not word["ipa"]:
                    word["ipa"] = self.word_to_ipa(word["conlang"])
                progress.setValue(progress.value() + 1)

            progress.setValue(progress.value() + 1)

            self.main_app.save_dictionary()

    def word_to_ipa(self, word: str):
        return "".join([self.translators[0].get(char, char) for char in word.lower()])

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, h_spacing=-1, v_spacing=-1):
        super().__init__(parent)
        self._item_list = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.h_space = h_spacing
        self.v_space = v_spacing

    def addItem(self, item):
        self._item_list.append(item)

    def horizontalSpacing(self):
        if self.h_space >= 0: return self.h_space
        return self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing) if self.parent() else 0

    def verticalSpacing(self):
        if self.v_space >= 0: return self.v_space
        return self.smartSpacing(QStyle.PM_LayoutVerticalSpacing) if self.parent() else 0

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self._item_list:
            space_x = self.horizontalSpacing()
            space_y = self.verticalSpacing()
            next_x = x + item.sizeHint().width() + space_x

            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent:
            return -1
        elif parent.isWidgetType():
            return parent.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()
