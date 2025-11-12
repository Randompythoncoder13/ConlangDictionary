import sys
import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit, QComboBox, QTextEdit, QPushButton, QListWidget,
    QMessageBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class EditWordDialog(QDialog):
    """
    A dialog window for editing an existing dictionary entry.
    """

    def __init__(self, entry_to_edit, word_classes, parent=None):
        super().__init__(parent)
        self.entry_to_edit = entry_to_edit
        self.word_classes = word_classes
        self.new_entry_data = None

        self.setWindowTitle(f"Edit '{self.entry_to_edit['conlang']}'")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QGridLayout(self)
        self.setLayout(layout)

        # Form fields
        layout.addWidget(QLabel("Conlang Word:"), 0, 0)
        self.con_entry = QLineEdit()
        self.con_entry.setText(entry_to_edit['conlang'])
        layout.addWidget(self.con_entry, 0, 1)

        # Join English words back into a comma-separated string
        english_str = ", ".join(entry_to_edit.get("english", []))
        layout.addWidget(QLabel("English Translation:"), 1, 0)
        self.eng_entry = QLineEdit()
        self.eng_entry.setText(english_str)
        layout.addWidget(self.eng_entry, 1, 1)

        layout.addWidget(QLabel("Part of Speech:"), 2, 0)
        self.pos_box = QComboBox()
        self.pos_box.addItems(self.word_classes)
        self.pos_box.setCurrentText(entry_to_edit['pos'])
        layout.addWidget(self.pos_box, 2, 1)

        layout.addWidget(QLabel("Description:"), 3, 0, Qt.AlignmentFlag.AlignTop)
        self.desc_text = QTextEdit()
        self.desc_text.setText(entry_to_edit['description'])
        self.desc_text.setMinimumHeight(100)
        layout.addWidget(self.desc_text, 3, 1)

        # Join tags back into a comma-separated string
        tags_str = ", ".join(entry_to_edit.get('tags', []))
        layout.addWidget(QLabel("Tags (comma-sep):"), 4, 0)
        self.tags_entry = QLineEdit()
        self.tags_entry.setText(tags_str)
        layout.addWidget(self.tags_entry, 4, 1)

        # Buttons
        button_box = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)  # Closes the dialog

        button_box.addStretch()
        button_box.addWidget(self.save_button)
        button_box.addWidget(self.cancel_button)
        layout.addLayout(button_box, 5, 0, 1, 2)

    def save_changes(self):
        # Package up the data for the main window to process
        self.new_entry_data = {
            "conlang": self.con_entry.text().strip(),
            "english": [e.strip() for e in self.eng_entry.text().strip().split(',') if e.strip()],
            "pos": self.pos_box.currentText(),
            "description": self.desc_text.toPlainText().strip(),
            "tags": [t.strip() for t in self.tags_entry.text().strip().split(',') if t.strip()]
        }

        if not self.new_entry_data["conlang"] or not self.new_entry_data["english"]:
            QMessageBox.warning(self, "Input Error", "Conlang and English fields are required.")
            self.new_entry_data = None  # Invalidate data
            return

        self.accept()  # Close the dialog


class AddWordDialog(QDialog):
    def __init__(self, word=None, word_classes=[], parent=None):
        super().__init__(parent)
        self.info_parent = parent
        self.word = word
        self.word_classes = word_classes
        self.new_entry_data = None

        self.setWindowTitle(f"Add Word")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QGridLayout(self)
        self.setLayout(layout)

        # Form fields
        layout.addWidget(QLabel("Conlang Word:"), 0, 0)
        self.con_entry = QLineEdit()
        if self.word:
            self.con_entry.setText(word)
        layout.addWidget(self.con_entry, 0, 1)

        layout.addWidget(QLabel("English Translation:"), 1, 0)
        self.eng_entry = QLineEdit()
        self.eng_entry.setPlaceholderText("e.g., set, place")
        layout.addWidget(self.eng_entry, 1, 1)

        layout.addWidget(QLabel("Part of Speech:"), 2, 0)
        self.pos_box = QComboBox()
        self.pos_box.addItems(self.word_classes)
        self.pos_box.setCurrentIndex(-1)
        layout.addWidget(self.pos_box, 2, 1)

        layout.addWidget(QLabel("Description:"), 3, 0, Qt.AlignmentFlag.AlignTop)
        self.desc_text = QTextEdit()
        self.desc_text.setMinimumHeight(100)
        layout.addWidget(self.desc_text, 3, 1)

        # Join tags back into a comma-separated string
        layout.addWidget(QLabel("Tags (comma-sep):"), 4, 0)
        self.tags_entry = QLineEdit()
        self.tags_entry.setPlaceholderText("e.g., informal, tech")
        layout.addWidget(self.tags_entry, 4, 1)

        # Buttons
        button_box = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)  # Closes the dialog

        button_box.addStretch()
        button_box.addWidget(self.save_button)
        button_box.addWidget(self.cancel_button)
        layout.addLayout(button_box, 5, 0, 1, 2)

    def save_changes(self):
        # Package up the data for the main window to process

        self.new_entry_data = {
            "conlang": self.con_entry.text().strip(),
            "english": [e.strip() for e in self.eng_entry.text().strip().split(',') if e.strip()],
            "pos": self.pos_box.currentText(),
            "description": self.desc_text.toPlainText().strip(),
            "tags": [t.strip() for t in self.tags_entry.text().strip().split(',') if t.strip()]
        }

        if not self.new_entry_data["conlang"] or not self.new_entry_data["english"]:
            QMessageBox.warning(self, "Input Error", "Conlang and English fields are required.")
            self.new_entry_data = None  # Invalidate data
            return

        if any(entry['conlang'].lower() == self.new_entry_data["conlang"].lower() for entry in self.info_parent.dictionary):
            QMessageBox.warning(self, "Duplicate Entry", f"The word '{self.new_entry_data["conlang"]}' already exists.")
            return

        if not self.new_entry_data["pos"]:
            QMessageBox.warning(self, "Input Error", "Part of Speech is required.")
            return

        self.accept()  # Close the dialog


class ManageTagsDialog(QDialog):
    """
    A dialog window for managing the global list of tags.
    """

    def __init__(self, all_tags, parent=None):
        super().__init__(parent)
        self.all_tags = all_tags  # This is a reference to the main list
        self.setWindowTitle("Manage Tags")
        self.setModal(True)
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout(self)

        self.listbox = QListWidget()
        self.listbox.addItems(sorted(self.all_tags))
        layout.addWidget(self.listbox)

        entry_frame = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Enter new tag...")
        self.add_btn = QPushButton("Add Tag")
        self.add_btn.clicked.connect(self.add_tag)
        entry_frame.addWidget(self.entry)
        entry_frame.addWidget(self.add_btn)
        layout.addLayout(entry_frame)

        self.remove_btn = QPushButton("Remove Selected Tag")
        self.remove_btn.clicked.connect(self.remove_tag)
        layout.addWidget(self.remove_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        self.tags_changed = False

    def add_tag(self):
        tag = self.entry.text().strip()
        if tag and tag not in self.all_tags:
            self.all_tags.append(tag)
            self.all_tags.sort()
            self.listbox.clear()
            self.listbox.addItems(self.all_tags)
            self.entry.clear()
            self.tags_changed = True

    def remove_tag(self):
        selected_items = self.listbox.selectedItems()
        if not selected_items:
            return

        tag_to_remove = selected_items[0].text()
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Really remove '{tag_to_remove}' from the global tag list?\n"
            "(This does NOT remove it from words.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.all_tags.remove(tag_to_remove)
            self.listbox.takeItem(self.listbox.row(selected_items[0]))
            self.tags_changed = True


class ManagePOSDialog(QDialog):
    """
    A dialog window for managing the list of Parts of Words.
    """

    def __init__(self, pos, parent=None):
        super().__init__(parent)
        self.pos = pos  # This is a reference to the main list
        self.setWindowTitle("Manage Parts of Speech")
        self.setModal(True)
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout(self)

        self.listbox = QListWidget()
        self.listbox.addItems(sorted(self.pos))
        layout.addWidget(self.listbox)

        entry_frame = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Enter Part of Speech...")
        self.add_btn = QPushButton("Add POS")
        self.add_btn.clicked.connect(self.add_tag)
        entry_frame.addWidget(self.entry)
        entry_frame.addWidget(self.add_btn)
        layout.addLayout(entry_frame)

        self.remove_btn = QPushButton("Remove Selected Part of Speech")
        self.remove_btn.clicked.connect(self.remove_tag)
        layout.addWidget(self.remove_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        self.pos_changed = False

    def add_tag(self):
        pos = self.entry.text().strip()
        if pos and pos not in self.pos:
            self.pos.append(pos)
            self.pos.sort()
            self.listbox.clear()
            self.listbox.addItems(self.pos)
            self.entry.clear()
            self.pos_changed = True

    def remove_tag(self):
        selected_items = self.listbox.selectedItems()
        if not selected_items:
            return

        pos_to_remove = selected_items[0].text()
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Really remove '{pos_to_remove}' from the Parts of Speech list?\n"
            "(This does NOT remove it from words.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.pos.remove(pos_to_remove)
            self.listbox.takeItem(self.listbox.row(selected_items[0]))
            self.pos_changed = True


class OpenProjectDialog(QDialog):
    def __init__(self, parent=None, flag=False):
        super().__init__(parent)
        self.info_parent = parent
        self.flag = flag

        self.setWindowTitle("Open/Create Project")
        self.setModal(True)
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout(self)
        top_box = QGroupBox("Select Project")
        bottom_box = QGroupBox("Create New Project")
        top_frame = QGridLayout(top_box)
        bottom_frame = QGridLayout(bottom_box)

        self.project_select = QComboBox()
        self.project_select.addItems(self.fetch_projects())
        self.project_select.setCurrentIndex(-1)
        top_frame.addWidget(self.project_select, 0, 0)

        top_submit = QPushButton("Open")
        top_submit.clicked.connect(self.open_project)
        top_frame.addWidget(top_submit, 1, 0)

        self.project_create = QLineEdit()
        bottom_frame.addWidget(self.project_create, 0, 0)

        bottom_submit = QPushButton("Create")
        bottom_submit.clicked.connect(self.create_project)
        bottom_frame.addWidget(bottom_submit, 1, 0)

        layout.addWidget(top_box)
        layout.addWidget(bottom_box)

    def fetch_projects(self):
        if self.flag:
            folders = os.listdir(self.info_parent.app_data_master_dir)
            try:
                folders.remove("dark_light_mode.txt")
            except ValueError:
                pass
            return folders
        else:
            folders = os.listdir(self.info_parent.app_data_dir)
            try:
                folders.remove("dark_light_mode.txt")
            except ValueError:
                pass
            return folders

    def open_project(self):
        if self.project_select.currentText() == "":
            return

        if self.flag:
            self.info_parent.app_data_dir = os.path.join(
                self.info_parent.app_data_master_dir, self.project_select.currentText()
            )
        else:
            self.info_parent.app_data_dir = os.path.join(
                self.info_parent.app_data_dir, self.project_select.currentText()
            )

        self.info_parent.dictionary_file = os.path.join(self.info_parent.app_data_dir, "conlang_dictionary.json")
        self.info_parent.tags_file = os.path.join(self.info_parent.app_data_dir, "conlang_tags.json")
        self.info_parent.grammar_file = os.path.join(self.info_parent.app_data_dir, "conlang_grammar.json")

        self.info_parent.setWindowTitle(f"{self.project_select.currentText()} Dictionary")

        self.accept()

    def create_project(self):
        if self.project_create.text().strip() == "":
            return

        if self.flag:
            self.info_parent.app_data_dir = os.path.join(
                self.info_parent.app_data_master_dir, self.project_create.text().strip()
            )
        else:
            self.info_parent.app_data_dir = os.path.join(
                self.info_parent.app_data_dir, self.project_create.text().strip()
            )

        os.makedirs(os.path.join(self.info_parent.app_data_dir, self.project_create.text().strip()), exist_ok=True)
        self.info_parent.dictionary_file = os.path.join(self.info_parent.app_data_dir, "conlang_dictionary.json")
        self.info_parent.tags_file = os.path.join(self.info_parent.app_data_dir, "conlang_tags.json")
        self.info_parent.grammar_file = os.path.join(self.info_parent.app_data_dir, "conlang_grammar.json")

        self.info_parent.setWindowTitle(f"{self.project_create.text().strip()} Dictionary")

        self.accept()

    def closeEvent(self, event):
        if self.flag:
            self.accept()
        else:
            sys.exit()


class RenameProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.info_parent = parent

        self.setWindowTitle("Rename Project")
        self.setModal(True)
        self.setMinimumSize(300, 400)

        layout = QVBoxLayout(self)
        box = QGroupBox("Rename Project")
        frame = QGridLayout(box)

        self.project_name = QLineEdit()
        frame.addWidget(self.project_name, 0, 0)

        top_submit = QPushButton("Rename")
        top_submit.clicked.connect(self.rename_project)
        frame.addWidget(top_submit, 1, 0)

        layout.addWidget(box)

    def rename_project(self):
        if self.project_name.text().strip() == "":
            return

        new_location = os.path.join(self.info_parent.app_data_master_dir, self.project_name.text().strip())

        os.rename(self.info_parent.app_data_dir, new_location)
        self.info_parent.app_data_dir = new_location

        self.info_parent.dictionary_file = os.path.join(self.info_parent.app_data_dir, "conlang_dictionary.json")
        self.info_parent.tags_file = os.path.join(self.info_parent.app_data_dir, "conlang_tags.json")
        self.info_parent.grammar_file = os.path.join(self.info_parent.app_data_dir, "conlang_grammar.json")

        self.accept()


class WarningDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)

        self.setWindowTitle("WARNING!")

        QBtn = (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(message)
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class SecondaryCheckDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("ARE YOU SURE?!?")

        layout = QVBoxLayout()

        QBtn = (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        layout.addWidget(QLabel("Type \"CONFIRM\" to proceed with the action."))

        self.entry_field = QLineEdit()
        layout.addWidget(self.entry_field)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.check_confirm)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def check_confirm(self):
        if self.entry_field.text().strip().lower() == "confirm":
           self.accept()


class ImportantWarningDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)

        self.setWindowTitle("WARNING!")

        QBtn = (QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.run_check)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(message)
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def run_check(self):
        dialog = SecondaryCheckDialog(self)
        if dialog.exec():
            self.accept()
        else:
            self.reject()
