from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox,
    QListWidgetItem, QScrollArea, QFrame, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from src.dialogs import WarningDialog
from src.simulated_kozuka_logic import generate_words


class WordGenTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; padding: 5px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        main_layout = QHBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()

        self.content_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        label = QLabel("Based on Kozuka. Go here for how to use: https://kozuka.kmwc.org/help.html")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_layout.addWidget(label)

        patterns_group = QWidget()
        patterns_layout = QVBoxLayout(patterns_group)
        patterns_layout.setContentsMargins(0, 0, 0, 0)

        patterns_title = QLabel("Patterns")
        title_font = patterns_title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        patterns_title.setFont(title_font)
        patterns_layout.addWidget(patterns_title)

        self.pattern_rows_layout = QVBoxLayout()
        patterns_layout.addLayout(self.pattern_rows_layout)

        add_pattern_button = QPushButton("+ Add pattern")
        add_pattern_button.clicked.connect(lambda: self.add_pattern_row())
        patterns_layout.addWidget(add_pattern_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.content_layout.addWidget(patterns_group)
        self.content_layout.addWidget(self._create_separator())

        main_pattern_layout = QHBoxLayout()
        main_pattern_label = QLabel("Main pattern:")
        self.main_pattern_input = QLineEdit()

        main_pattern_layout.addWidget(main_pattern_label)
        main_pattern_layout.addWidget(self.main_pattern_input, 1)

        self.content_layout.addLayout(main_pattern_layout)
        self.content_layout.addWidget(self._create_separator())

        controls_layout = QHBoxLayout()

        # --- Generating Box ---
        gen_box = QFrame()
        # gen_box.setFrameShape(QFrame.Shape.StyledPanel)
        gen_layout = QGridLayout(gen_box)

        gen_layout.addWidget(QLabel("Number of words:"), 0, 0)
        self.num_words_input = QLineEdit("100")
        self.num_words_input.setFixedWidth(80)
        gen_layout.addWidget(self.num_words_input, 0, 1)

        generate_button = QPushButton(QIcon.fromTheme("view-refresh"), "Generate")
        generate_button.clicked.connect(self.generate_output)
        gen_layout.addWidget(generate_button, 3, 0, 1, 2)

        self.pattern_save_name = QLineEdit()
        self.pattern_save_name.setFixedWidth(300)
        self.pattern_save_name.setPlaceholderText("Pattern Name")
        gen_layout.addWidget(self.pattern_save_name, 0, 2, 1, 1)

        save_pattern_button = QPushButton("Save Pattern")
        save_pattern_button.setFixedWidth(300)
        save_pattern_button.clicked.connect(self.save_pattern)
        gen_layout.addWidget(save_pattern_button, 3, 2, 1, 2)

        self.pattern_load_box = QComboBox()
        self.pattern_load_box.addItems([name["name"] for name in self.main_app.presents])
        self.pattern_load_box.setFixedWidth(300)
        gen_layout.addWidget(self.pattern_load_box, 0, 3, 1, 1)

        load_pattern_button = QPushButton("Load Pattern")
        load_pattern_button.setFixedWidth(300)
        load_pattern_button.clicked.connect(self.load_pattern)
        gen_layout.addWidget(load_pattern_button, 3, 3, 1, 2)

        gen_layout.setColumnStretch(2, 1)

        controls_layout.addWidget(gen_box, 1)

        self.content_layout.addLayout(controls_layout)
        self.content_layout.addWidget(self._create_separator())

        output_layout = QHBoxLayout()

        self.gen_output_listbox = QListWidget()
        self.gen_output_listbox.itemDoubleClicked.connect(self.make_word_from_gen)
        output_layout.addWidget(self.gen_output_listbox)

        self.content_layout.addLayout(output_layout)
        self.content_layout.addWidget(self._create_separator())

        self.add_pattern_row()
        self.add_pattern_row()

        self.content_layout.addStretch()

    def add_pattern_row(self, name="", pattern=""):  # <-- Add optional arguments
        """
        Adds a new pattern row (name, pattern, remove button) to the layout.
        Optionally populates it with initial name and pattern data.
        """

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Name")
        name_input.setText(name)

        pattern_input = QLineEdit()
        pattern_input.setPlaceholderText("Pattern")
        pattern_input.setText(pattern)

        remove_button = QPushButton("- Remove")
        remove_button.clicked.connect(lambda checked, widget=row_widget: self.remove_pattern_row(widget))

        row_layout.addWidget(name_input, 1)
        row_layout.addWidget(pattern_input, 3)
        row_layout.addWidget(remove_button)

        self.pattern_rows_layout.addWidget(row_widget)

    def remove_pattern_row(self, row_widget):
        """Removes a specific pattern row widget."""
        if self.pattern_rows_layout.count() > 1:
            self.pattern_rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        else:
            self.show_error("You must have at least one pattern.")

    def clear_pattern_rows(self):
        """Removes ALL dynamic pattern rows from the layout."""
        while self.pattern_rows_layout.count() > 0:
            item = self.pattern_rows_layout.takeAt(self.pattern_rows_layout.count() - 1)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _create_separator(self):
        """Helper to create a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def generate_output(self):
        settings = self.get_settings()
        self.gen_output_listbox.clear()

        # noinspection PyTypeChecker
        for word in generate_words(settings["mainPattern"], settings["patterns"], count=settings["numWords"]):
            self.gen_output_listbox.addItem(word)

    def get_settings(self):
        """Collects all settings from the UI into a dictionary."""
        settings = {
            "patterns": [],
            "mainPattern": self.main_pattern_input.text(),
            "numWords": int(self.num_words_input.text()),
        }

        for i in range(self.pattern_rows_layout.count()):
            row_widget = self.pattern_rows_layout.itemAt(i).widget()

            # noinspection PyTypeChecker
            all_line_edits = row_widget.findChildren(QLineEdit, None, Qt.FindChildOption.FindChildrenRecursively)

            if len(all_line_edits) >= 2:
                name_input = all_line_edits[0]
                pattern_input = all_line_edits[1]

                settings["patterns"].append({
                    name_input.text(): pattern_input.text()
                })
            else:
                print(f"Warning: Row {i} did not contain two QLineEdit widgets.")

        return settings

    def make_word_from_gen(self, item: QListWidgetItem):
        self.main_app.tab_dictionary.add_word(item.text())

    def save_pattern(self):
        name = self.pattern_save_name.text().strip()

        if not name:
            return

        self.pattern_save_name.clear()
        settings = self.get_settings()

        for present in self.main_app.presents:
            if present["name"] == name:
                dialog = WarningDialog(
                    "An existing pattern has this name, are you sure you want to overwrite that?", self
                )
                if dialog.exec():
                    present["patterns"] = settings["patterns"]
                    present["mainPattern"] = settings["mainPattern"]

                    self.pattern_load_box.clear()
                    self.pattern_load_box.addItems([name["name"] for name in self.main_app.presents])

                    self.main_app.save_presents()

                    return
                else:
                    return

        self.main_app.presents.append({"name": name, "patterns": settings["patterns"], "mainPattern": settings["mainPattern"]})

        self.pattern_load_box.clear()
        self.pattern_load_box.addItems([name["name"] for name in self.main_app.presents])

        self.main_app.save_presents()

    def load_pattern(self):
        preset_data = None

        name = self.pattern_load_box.currentText()
        for present in self.main_app.presents:
            if present["name"] == name:
                preset_data = present
                break

        if not preset_data:
            QMessageBox.warning(self, "Critical Error", f"Error: Preset not found.")
            return

        self.clear_pattern_rows()

        self.main_pattern_input.setText(preset_data.get("mainPattern", ""))

        patterns_list = preset_data.get("patterns", [])
        for pattern_dict in patterns_list:
            if pattern_dict:
                try:
                    name = list(pattern_dict.keys())[0]
                    pattern = list(pattern_dict.values())[0]

                    self.add_pattern_row(name, pattern)
                except IndexError:
                    QMessageBox.warning(self, "Load Error", f"Warning: Could not load pattern_dict: {pattern_dict}")

    def show_error(self, message):
        """Displays an error message in the error label."""
        self.error_label.setText(message)
        self.error_label.show()

    def reset(self):
        self.pattern_load_box.clear()
        self.pattern_load_box.addItems([name["name"] for name in self.main_app.presents])
        self.pattern_load_box.setCurrentIndex(0)

        self.clear_pattern_rows()
        self.main_pattern_input.setText("")
        self.num_words_input.setText("100")
        self.pattern_save_name.setText("")
        self.gen_output_listbox.clear()
