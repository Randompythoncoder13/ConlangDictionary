import uuid

from PySide6.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog, QListWidgetItem, QRadioButton, QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer

from src.dialogs import ManagePOSDialog, ManageTagsDialog, EditWordDialog, AddWordDialog, WordSelectionDialog
from src.custom_widgets import DeselectableListWidget


class DictionaryTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        main_layout = QHBoxLayout(self)
        self.custom_font_on = self.main_app.custom_font_on
        self.font = self.main_app.font

        # --- Left Panel ---
        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)

        # Search and Filter Group
        search_frame = QGroupBox("Search & Filter")
        search_frame_layout = QVBoxLayout(search_frame)

        search_frame_layout.addWidget(QLabel("Search Term:"))
        self.search_entry = QLineEdit()

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.update_word_display)

        self.search_entry.textChanged.connect(self.search_timer.start)
        self.default_font = self.search_entry.font()
        if self.main_app.font:
            self.search_entry.setFont(self.main_app.font)
        search_frame_layout.addWidget(self.search_entry)

        self.radio_conlang = QRadioButton("In Conlang")
        self.radio_conlang.setChecked(True)
        self.radio_conlang.toggled.connect(self.update_word_display)
        search_frame_layout.addWidget(self.radio_conlang)

        self.radio_english = QRadioButton("In English")
        self.radio_english.toggled.connect(self.update_word_display)
        search_frame_layout.addWidget(self.radio_english)

        search_frame_layout.addWidget(QLabel("Filter by Part of Speech:"))
        self.filter_pos_listbox = DeselectableListWidget()
        self.filter_pos_listbox.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.filter_pos_listbox.itemSelectionChanged.connect(self.update_word_display)
        self.filter_pos_listbox.setFixedHeight(120)
        search_frame_layout.addWidget(self.filter_pos_listbox)

        self.update_filter_pos_listbox()

        search_frame_layout.addWidget(QLabel("Filter by Tags:"))
        self.tag_filter_listbox = DeselectableListWidget()
        self.tag_filter_listbox.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.tag_filter_listbox.itemSelectionChanged.connect(self.update_word_display)
        self.tag_filter_listbox.setFixedHeight(120)
        search_frame_layout.addWidget(self.tag_filter_listbox)

        manage_tags_button = QPushButton("Manage Tags")
        manage_tags_button.clicked.connect(self.manage_tags)
        search_frame_layout.addWidget(manage_tags_button)

        pos_button = QPushButton("Manage Parts of Speech")
        pos_button.clicked.connect(self.manage_pos)
        search_frame_layout.addWidget(pos_button)

        clear_button = QPushButton("Clear Filters / Show All")
        clear_button.clicked.connect(self.clear_filters)
        search_frame_layout.addWidget(clear_button)

        left_panel_layout.addWidget(search_frame)
        left_panel_layout.addStretch(1)
        main_layout.addWidget(left_panel)

        # --- Right Panel ---
        right_panel = QWidget()
        right_panel_layout = QVBoxLayout(right_panel)

        # Dictionary Table
        dict_frame = QGroupBox("Dictionary")
        dict_frame_layout = QVBoxLayout(dict_frame)

        self.cols = ("Conlang Word", "English Translation", "Part of Speech", "Tags")
        self.tree = QTableWidget(0, len(self.cols))
        self.tree.setHorizontalHeaderLabels(self.cols)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # Read-only
        self.tree.verticalHeader().setVisible(False)
        self.tree.horizontalHeader().setStretchLastSection(True)
        self.tree.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tree.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tree.horizontalHeader().setMinimumSectionSize(125)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self.tree.itemSelectionChanged.connect(self.on_item_select)
        self.tree.itemDoubleClicked.connect(self.on_item_double_click)

        dict_frame_layout.addWidget(self.tree)

        # Edit/Delete Buttons
        button_frame = QHBoxLayout()
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_word)
        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self.edit_word)
        add_button = QPushButton("Add Word")
        add_button.clicked.connect(lambda: self.add_word(flag=True))
        font_toggle_button = QPushButton("Toggle Custom Font")
        font_toggle_button.clicked.connect(self.toggle_font)
        button_frame.addWidget(delete_button)
        button_frame.addWidget(edit_button)
        button_frame.addWidget(add_button)
        button_frame.addWidget(font_toggle_button)
        button_frame.addStretch(1)
        dict_frame_layout.addLayout(button_frame)

        right_panel_layout.addWidget(dict_frame)

        # Details Notebook
        self.details_notebook = QTabWidget()
        self.details_notebook.setMaximumHeight(250)

        # Description Tab
        desc_tab = QWidget()
        desc_tab_layout = QVBoxLayout(desc_tab)
        self.display_description_text = QTextEdit()
        self.display_description_text.setReadOnly(True)
        desc_tab_layout.addWidget(self.display_description_text)
        self.details_notebook.addTab(desc_tab, "Description")

        # Etymology Tab
        etym_tab = QWidget()
        etym_tab_layout = QHBoxLayout(etym_tab)

        # Roots Group
        roots_frame = QGroupBox("Root Words (comes from)")
        roots_frame_layout = QVBoxLayout(roots_frame)
        self.roots_listbox = QListWidget()
        self.roots_listbox.itemDoubleClicked.connect(self.jump_to_word_from_listbox)
        roots_frame_layout.addWidget(self.roots_listbox)
        roots_btn_layout = QHBoxLayout()
        add_root_btn = QPushButton("Add Root")
        add_root_btn.clicked.connect(lambda: self.add_etymology_link('root'))
        del_root_btn = QPushButton("Remove Root")
        del_root_btn.clicked.connect(lambda: self.remove_etymology_link('root'))
        roots_btn_layout.addWidget(add_root_btn)
        roots_btn_layout.addWidget(del_root_btn)
        roots_frame_layout.addLayout(roots_btn_layout)

        # Derived Group
        derived_frame = QGroupBox("Derived Words (leads to)")
        derived_frame_layout = QVBoxLayout(derived_frame)
        self.derived_listbox = QListWidget()
        self.derived_listbox.itemDoubleClicked.connect(self.jump_to_word_from_listbox)
        derived_frame_layout.addWidget(self.derived_listbox)
        derived_btn_layout = QHBoxLayout()
        add_derived_btn = QPushButton("Add Derived")
        add_derived_btn.clicked.connect(lambda: self.add_etymology_link('derived'))
        del_derived_btn = QPushButton("Remove Derived")
        del_derived_btn.clicked.connect(lambda: self.remove_etymology_link('derived'))
        derived_btn_layout.addWidget(add_derived_btn)
        derived_btn_layout.addWidget(del_derived_btn)
        derived_frame_layout.addLayout(derived_btn_layout)

        etym_tab_layout.addWidget(roots_frame)
        etym_tab_layout.addWidget(derived_frame)
        self.details_notebook.addTab(etym_tab, "Etymology")

        # Lexical Relations Tab
        lex_rel_tab = QWidget()
        lex_rel_tab_layout = QHBoxLayout(lex_rel_tab)

        # Synonyms Group
        synonyms_frame = QGroupBox("Synonyms")
        synonyms_frame_layout = QVBoxLayout(synonyms_frame)
        self.synonyms_listbox = QListWidget()
        self.synonyms_listbox.itemDoubleClicked.connect(self.jump_to_word_from_listbox)
        synonyms_frame_layout.addWidget(self.synonyms_listbox)
        synonyms_btn_layout = QHBoxLayout()
        add_synonym_btn = QPushButton("Add Synonym")
        add_synonym_btn.clicked.connect(lambda: self.add_lex_rel_link('synonym'))
        del_synonym_btn = QPushButton("Remove Synonym")
        del_synonym_btn.clicked.connect(lambda: self.remove_lex_rel_link('synonym'))
        synonyms_btn_layout.addWidget(add_synonym_btn)
        synonyms_btn_layout.addWidget(del_synonym_btn)
        synonyms_frame_layout.addLayout(synonyms_btn_layout)

        # Antonyms Group
        antonyms_frame = QGroupBox("Antonyms")
        antonyms_frame_layout = QVBoxLayout(antonyms_frame)
        self.antonyms_listbox = QListWidget()
        self.antonyms_listbox.itemDoubleClicked.connect(self.jump_to_word_from_listbox)
        antonyms_frame_layout.addWidget(self.antonyms_listbox)
        antonyms_btn_layout = QHBoxLayout()
        add_antonym_btn = QPushButton("Add Antonym")
        add_antonym_btn.clicked.connect(lambda: self.add_lex_rel_link('antonym'))
        del_antonym_btn = QPushButton("Remove Antonym")
        del_antonym_btn.clicked.connect(lambda: self.remove_lex_rel_link('antonym'))
        antonyms_btn_layout.addWidget(add_antonym_btn)
        antonyms_btn_layout.addWidget(del_antonym_btn)
        antonyms_frame_layout.addLayout(antonyms_btn_layout)

        lex_rel_tab_layout.addWidget(synonyms_frame)
        lex_rel_tab_layout.addWidget(antonyms_frame)
        self.details_notebook.addTab(lex_rel_tab, "Lexical Relations")

        right_panel_layout.addWidget(self.details_notebook)
        main_layout.addWidget(right_panel, 1)

    def populate_dictionary_list(self, entries):
        self.tree.setSortingEnabled(False)

        try:
            self.tree.itemSelectionChanged.disconnect(self.on_item_select)
        except TypeError:
            pass

        self.tree.setRowCount(0)

        entries.sort(key=lambda x: x['conlang'].lower())

        for entry in entries:
            row_position = self.tree.rowCount()
            self.tree.insertRow(row_position)

            tags_str = ", ".join(entry.get('tags', []))
            english_str = ", ".join(entry.get('english', []))

            conlang_item = QTableWidgetItem(entry["conlang"])
            if self.main_app.custom_font_on:
                if self.main_app.font:
                    conlang_item.setFont(self.main_app.font)
            else:
                conlang_item.setFont(self.default_font)
            english_item = QTableWidgetItem(english_str)
            pos_item = QTableWidgetItem(entry["pos"])
            tags_item = QTableWidgetItem(tags_str)

            conlang_item.setData(Qt.ItemDataRole.UserRole, entry["id"])

            self.tree.setItem(row_position, 0, conlang_item)
            self.tree.setItem(row_position, 1, english_item)
            self.tree.setItem(row_position, 2, pos_item)
            self.tree.setItem(row_position, 3, tags_item)

        self.tree.setSortingEnabled(True)
        self.tree.itemSelectionChanged.connect(self.on_item_select)

        self.on_item_select()

    def update_word_display(self, event=None):
        filtered_list = self.main_app.dictionary[:]

        if self.main_app.custom_font_on:
            if self.radio_conlang.isChecked():
                if self.main_app.font:
                    self.search_entry.setFont(self.main_app.font)
            elif self.radio_english.isChecked():
                self.search_entry.setFont(self.default_font)
        else:
            self.search_entry.setFont(self.default_font)

        # Filter by part of speech
        selected_pos_item = self.filter_pos_listbox.selectedItems()
        if selected_pos_item:
            selected_pos = {item.text() for item in selected_pos_item}
            filtered_list = [entry for entry in filtered_list if entry['pos'] in selected_pos]

        # Filter by selected tags
        selected_tag_items = self.tag_filter_listbox.selectedItems()
        if selected_tag_items:
            selected_tags = {item.text() for item in selected_tag_items}
            filtered_list = [entry for entry in filtered_list if selected_tags.issubset(set(entry.get('tags', [])))]

        # Filter by search term
        search_term = self.search_entry.text().strip().lower()
        if search_term:
            if self.radio_conlang.isChecked():
                filtered_list = [entry for entry in filtered_list if search_term in entry["conlang"].lower()]
            elif self.radio_english.isChecked():
                new_filtered_list = []
                for entry in filtered_list:
                    if any(search_term in word.lower() for word in entry.get("english", [])):
                        new_filtered_list.append(entry)
                filtered_list = new_filtered_list

        self.populate_dictionary_list(filtered_list)

    def add_word(self, word=None, flag=None):
        self.add_word_dialog = AddWordDialog(word=word, word_classes=self.main_app.word_classes, parent=self)
        self.add_word_dialog.accepted.connect(lambda: self._process_new_word(flag))
        self.add_word_dialog.show()

    def _process_new_word(self, flag=None):
        new_data = self.add_word_dialog.new_entry_data

        if not new_data:
            return

        conlang_word = new_data["conlang"]
        english_words = new_data["english"]
        pos = new_data["pos"]
        description = new_data["description"]
        tags_list = new_data["tags"]
        ipa = new_data["ipa"]
        syllable = new_data["syllable"]

        if not conlang_word:
            QMessageBox.warning(self, "Input Error", "Conlang field is required.")
            return

        if not pos:
            QMessageBox.warning(self, "Input Error", "Part of Speech is required.")
            return

        self.main_app.update_tags(tags_list)

        new_entry = {
            "id": str(uuid.uuid4()),
            "conlang": conlang_word,
            "english": english_words,
            "pos": pos,
            "description": description,
            "tags": tags_list,
            "roots": [],
            "derived": [],
            "ipa": ipa,
            "syllable": syllable,
            "synonyms": [],
            "antonyms": []
        }
        self.main_app.dictionary.append(new_entry)
        self.main_app.save_dictionary()
        self.update_word_display()

        if flag:
            self.select_word_in_table(new_entry["id"])

        self.main_app.tab_stats.refresh_stats_page()

    def delete_word(self):
        selected_row = self.tree.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "Please select a word to delete.")
            return

        conlang_word = self.tree.item(selected_row, 0).text()
        word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        entry_to_delete = self.get_entry_by_id(word_id)

        if not entry_to_delete:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{conlang_word}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for root_id in entry_to_delete.get('roots', []):
                root_entry = self.get_entry_by_id(root_id)
                if root_entry and word_id in root_entry.get('derived', []):
                    root_entry['derived'].remove(word_id)

            for derived_id in entry_to_delete.get('derived', []):
                derived_entry = self.get_entry_by_id(derived_id)
                if derived_entry and word_id in derived_entry.get('roots', []):
                    derived_entry['roots'].remove(word_id)

            for syn_id in entry_to_delete.get('synonyms', []):
                syn_entry = self.get_entry_by_id(syn_id)
                if syn_entry and word_id in syn_entry.get('synonyms', []):
                    syn_entry['synonyms'].remove(word_id)

            for ant_id in entry_to_delete.get('antonyms', []):
                ant_entry = self.get_entry_by_id(ant_id)
                if ant_entry and word_id in ant_entry.get('antonyms', []):
                    ant_entry['antonyms'].remove(word_id)

            self.main_app.dictionary.remove(entry_to_delete)
            self.main_app.save_dictionary()
            self.update_word_display()
            QMessageBox.information(self, "Success", f"Deleted '{conlang_word}'.")
            self.main_app.tab_stats.refresh_stats_page()

    def edit_word(self):
        selected_row = self.tree.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "Please select a word to edit.")
            return

        word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        self.entry_to_edit = self.get_entry_by_id(word_id)
        if not self.entry_to_edit:
            return

        self.delete_word_dialog = EditWordDialog(self.entry_to_edit, self.main_app.word_classes, self)
        self.delete_word_dialog.accepted.connect(lambda: self._process_edit_word())
        self.delete_word_dialog.show()

    def _process_edit_word(self):
        new_data = self.delete_word_dialog.new_entry_data
        if not new_data:
            return

        self.main_app.update_tags(new_data['tags'])
        self.entry_to_edit.update(new_data)

        self.main_app.save_dictionary()
        self.update_word_display()
        self.select_word_in_table(self.entry_to_edit["id"])
        self.main_app.refresh_stats_page()

    def on_item_double_click(self, item):
        self.edit_word()

    def on_item_select(self):
        selected_row = self.tree.currentRow()
        description = ""
        entry = None

        if selected_row != -1:
            word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            entry = self.get_entry_by_id(word_id)
            if entry:
                english_words = ""
                counter = 0
                for word in entry['english']:
                    english_words += word
                    if counter != len(entry['english']) - 1:
                        english_words += ", "
                    counter += 1

                if self.main_app.custom_font_on:
                    if self.font:
                        description = (
                            f"<p style='font-size: 14pt'>"
                            f"<span style='font-family: \"{self.main_app.font_family_name}\"; font-size: 24pt; color: #2a82da;'>"
                            f"{entry['conlang']}<br>"
                            f"</span>"
                            f"({english_words})<br>"
                        )

                        if entry['syllable']:
                            description += f"{entry['syllable']}<br>"
                        if entry['ipa']:
                            description += f"/{entry['ipa']}/<br>"

                        description += f"{entry['pos']}<br>"
                        description += f"{entry['description']}"
                        description += f"</p>"
                    else:
                        description = (
                            f"<p style='font-size: 14pt'>"
                            f"<span style='font-size: 24pt; color: #2a82da;'>"
                            f"{entry['conlang']}<br>"
                            f"</span>"
                            f"({english_words})<br>"
                        )

                        if entry['syllable']:
                            description += f"{entry['syllable']}<br>"
                        if entry['ipa']:
                            description += f"/{entry['ipa']}/<br>"

                        description += f"{entry['pos']}<br>"
                        description += f"{entry['description']}"
                        description += f"</p>"
                else:
                    description = (
                        f"<p style='font-size: 14pt'>"
                        f"<span style='font-size: 24pt; color: #2a82da;'>"
                        f"{entry['conlang']}<br>"
                        f"</span>"
                        f"({english_words})<br>"
                    )

                    if entry['syllable']:
                        description += f"{entry['syllable']}<br>"
                    if entry['ipa']:
                        description += f"/{entry['ipa']}/<br>"

                    description += f"{entry['pos']}<br>"
                    description += f"{entry['description']}"
                    description += f"</p>"

        self.display_description_text.setText(description)
        self.update_etymology_display(entry)
        self.update_lex_rel_display(entry)

    def clear_filters(self):
        self.search_entry.clear()
        self.filter_pos_listbox.clearSelection()
        self.tag_filter_listbox.clearSelection()
        self.radio_conlang.setChecked(True)

    def update_tag_filter_listbox(self):
        selected_tags = {item.text() for item in self.tag_filter_listbox.selectedItems()}

        self.tag_filter_listbox.clear()

        new_items = []
        for tag in sorted(self.main_app.all_tags):
            # noinspection PyTypeChecker
            item = QListWidgetItem(tag)
            self.tag_filter_listbox.addItem(item)
            if tag in selected_tags:
                new_items.append(item)

        for item in new_items:
            item.setSelected(True)

    def update_filter_pos_listbox(self):
        selected_pos = {item.text() for item in self.filter_pos_listbox.selectedItems()}

        self.filter_pos_listbox.clear()

        new_items = []
        for pos in sorted(self.main_app.word_classes):
            # noinspection PyTypeChecker
            item = QListWidgetItem(pos)
            self.filter_pos_listbox.addItem(item)
            if pos in selected_pos:
                new_items.append(item)

        for item in new_items:
            item.setSelected(True)

    def manage_tags(self):
        dialog = ManageTagsDialog(self.main_app.all_tags, self)
        dialog.exec()

        if dialog.tags_changed:
            self.main_app.save_tags()
            self.update_tag_filter_listbox()

    def manage_pos(self):
        dialog = ManagePOSDialog(self.main_app.word_classes, self)
        dialog.exec()

        if dialog.pos_changed:
            self.main_app.save_tags()
            self.update_filter_pos_listbox()

    def toggle_font(self, no_recur=False):
        if self.tree.currentRow() != -1:
            flag = True
            row = self.tree.currentRow()
            item = self.tree.item(row, 0).data(Qt.ItemDataRole.UserRole)
        else:
            flag = False

        self.main_app.custom_font_on = not self.main_app.custom_font_on
        self.update_word_display()

        if flag:
            self.select_word_in_table(item)

        if not no_recur:
            self.main_app.toggle_font("dict")

    def get_entry_by_id(self, word_id):
        return next((item for item in self.main_app.dictionary if item.get("id") == word_id), None)

    def find_entries_by_word(self, conlang_word):
        return [item for item in self.main_app.dictionary if item["conlang"].lower() == conlang_word.lower()]

    def update_etymology_display(self, entry):
        self.roots_listbox.clear()
        self.derived_listbox.clear()

        if entry:
            for root_id in entry.get('roots', []):
                root_entry = self.get_entry_by_id(root_id)
                if root_entry:
                    item = QListWidgetItem(root_entry['conlang'])
                    item.setData(Qt.ItemDataRole.UserRole, root_id)
                    self.roots_listbox.addItem(item)

            for derived_id in entry.get('derived', []):
                derived_entry = self.get_entry_by_id(derived_id)
                if derived_entry:
                    item = QListWidgetItem(derived_entry['conlang'])
                    item.setData(Qt.ItemDataRole.UserRole, derived_id)
                    self.derived_listbox.addItem(item)

    def update_lex_rel_display(self, entry):
        self.synonyms_listbox.clear()
        self.antonyms_listbox.clear()

        if entry:
            for syn_id in entry.get('synonyms', []):
                syn_entry = self.get_entry_by_id(syn_id)
                if syn_entry:
                    item = QListWidgetItem(syn_entry['conlang'])
                    item.setData(Qt.ItemDataRole.UserRole, syn_id)
                    self.synonyms_listbox.addItem(item)

            for ant_id in entry.get('antonyms', []):
                ant_entry = self.get_entry_by_id(ant_id)
                if ant_entry:
                    item = QListWidgetItem(ant_entry['conlang'])
                    item.setData(Qt.ItemDataRole.UserRole, ant_id)
                    self.antonyms_listbox.addItem(item)

    def add_etymology_link(self, link_type):
        selected_row = self.tree.currentRow()
        if selected_row == -1: return

        selected_word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        entry_A = self.get_entry_by_id(selected_word_id)
        if not entry_A: return

        prompt = f"Enter the conlang word that is a {link_type} of '{entry_A['conlang']}':"
        word_B_name, ok = QInputDialog.getText(self.tree, "Add new Etymology", prompt)
        if not ok or not word_B_name.strip(): return
        word_B_name = word_B_name.strip()

        # Handle Homophones
        matches = self.find_entries_by_word(word_B_name)
        if not matches:
            QMessageBox.critical(self, "Word Not Found", f"The word '{word_B_name}' does not exist.")
            return

        if len(matches) > 1:
            dialog = WordSelectionDialog(matches, self)
            if dialog.exec():
                word_B_id = dialog.selected_uuid
            else:
                return
        else:
            word_B_id = matches[0]["id"]

        if word_B_id == selected_word_id:
            QMessageBox.warning(self, "Self-Link", "A word cannot be its own root or derivative.")
            return

        entry_B = self.get_entry_by_id(word_B_id)

        if link_type == 'root':
            if word_B_id not in entry_A['roots']: entry_A['roots'].append(word_B_id)
            if selected_word_id not in entry_B['derived']: entry_B['derived'].append(selected_word_id)
        elif link_type == 'derived':
            if word_B_id not in entry_A['derived']: entry_A['derived'].append(word_B_id)
            if selected_word_id not in entry_B['roots']: entry_B['roots'].append(selected_word_id)

        self.main_app.save_dictionary()
        self.update_etymology_display(entry_A)

    def remove_etymology_link(self, link_type):
        selected_row = self.tree.currentRow()
        if selected_row == -1: return

        selected_word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        entry_A = self.get_entry_by_id(selected_word_id)
        if not entry_A: return

        listbox = self.roots_listbox if link_type == 'root' else self.derived_listbox
        selected_items = listbox.selectedItems()
        if not selected_items: return

        word_B_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        entry_B = self.get_entry_by_id(word_B_id)

        if link_type == 'root':
            if word_B_id in entry_A['roots']: entry_A['roots'].remove(word_B_id)
            if entry_B and selected_word_id in entry_B['derived']: entry_B['derived'].remove(selected_word_id)
        elif link_type == 'derived':
            if word_B_id in entry_A['derived']: entry_A['derived'].remove(word_B_id)
            if entry_B and selected_word_id in entry_B['roots']: entry_B['roots'].remove(selected_word_id)

        self.main_app.save_dictionary()
        self.update_etymology_display(entry_A)

    def add_lex_rel_link(self, link_type):
        selected_row = self.tree.currentRow()
        if selected_row == -1: return

        selected_word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        entry_A = self.get_entry_by_id(selected_word_id)
        if not entry_A: return

        prompt = f"Enter the conlang word that is a {link_type} of '{entry_A['conlang']}':"
        word_B_name, ok = QInputDialog.getText(self.tree, f"Add new {link_type}", prompt)
        if not ok or not word_B_name.strip(): return
        word_B_name = word_B_name.strip()

        # Handle Homophones
        matches = self.find_entries_by_word(word_B_name)
        if not matches:
            QMessageBox.critical(self, "Word Not Found", f"The word '{word_B_name}' does not exist.")
            return

        if len(matches) > 1:
            dialog = WordSelectionDialog(matches, self)
            if dialog.exec():
                word_B_id = dialog.selected_uuid
            else:
                return
        else:
            word_B_id = matches[0]["id"]

        if word_B_id == selected_word_id:
            QMessageBox.warning(self, "Self-Link", f"A word cannot be its own {link_type}.")
            return

        entry_B = self.get_entry_by_id(word_B_id)

        if link_type == 'synonym':
            if word_B_id not in entry_A['synonyms']: entry_A['synonyms'].append(word_B_id)
            if selected_word_id not in entry_B['synonyms']: entry_B['synonyms'].append(selected_word_id)
        elif link_type == 'antonym':
            if word_B_id not in entry_A['antonyms']: entry_A['antonyms'].append(word_B_id)
            if selected_word_id not in entry_B['antonyms']: entry_B['antonyms'].append(selected_word_id)

        self.main_app.save_dictionary()
        self.update_lex_rel_display(entry_A)

    def remove_lex_rel_link(self, link_type):
        selected_row = self.tree.currentRow()
        if selected_row == -1: return

        selected_word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        entry_A = self.get_entry_by_id(selected_word_id)
        if not entry_A: return

        listbox = self.synonyms_listbox if link_type == 'synonym' else self.antonyms_listbox
        selected_items = listbox.selectedItems()
        if not selected_items: return

        word_B_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        entry_B = self.get_entry_by_id(word_B_id)

        if link_type == 'synonym':
            if word_B_id in entry_A['synonyms']: entry_A['synonyms'].remove(word_B_id)
            if entry_B and selected_word_id in entry_B['synonyms']: entry_B['synonyms'].remove(selected_word_id)
        elif link_type == 'antonym':  # Fixed typo here from original code ('antonyms')
            if word_B_id in entry_A['antonyms']: entry_A['antonyms'].remove(word_B_id)
            if entry_B and selected_word_id in entry_B['antonyms']: entry_B['antonyms'].remove(selected_word_id)

        self.main_app.save_dictionary()
        self.update_lex_rel_display(entry_A)

    def select_word_in_table(self, word_id):
        for row in range(self.tree.rowCount()):
            item = self.tree.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == word_id:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
                return

    def jump_to_word_from_listbox(self, item: QListWidgetItem):
        word_id = item.data(Qt.ItemDataRole.UserRole)
        self.select_word_in_table(word_id)
        self.main_app.main_notebook.setCurrentWidget(self)
