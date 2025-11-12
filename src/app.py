import sys
import os
import json
import csv
import shutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
    QTextEdit, QPushButton, QRadioButton, QListWidget, QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog,
    QSplitter, QAbstractItemView, QHeaderView, QListWidgetItem, QScrollArea, QFrame, QFileDialog, QErrorMessage
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QGuiApplication

from src.dialogs import (
    EditWordDialog, ManageTagsDialog, OpenProjectDialog, ManagePOSDialog, AddWordDialog,
    RenameProjectDialog, ImportantWarningDialog
)
from src.wizards import SetProjectNameUpdateErrorWizard
from src.simulated_kozuka_logic import generate_words
from src.functions import zip_folder, unzip_file, get_folder_names, clear_folder
from src.custom_widgets import DeselectableListWidget


class ConlangDictionaryApp(QMainWindow):
    """
    A GUI application for creating, managing, and searching a dictionary for a
    constructed language, rewritten in PyQt6.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conlang Dictionary")
        self.setGeometry(100, 100, 1100, 800)  # Increased size slightly for PyQt widgets

        # --- Data File Setup ---
        # Get application data directory
        try:
            app_data_path = os.getenv('LOCALAPPDATA')
            if app_data_path is None:
                app_data_path = os.path.expanduser("~/.local/share")  # Fallback for Linux

            self.app_data_dir = os.path.join(app_data_path, "ConlangDictionary")
            self.app_data_master_dir = self.app_data_dir
            os.makedirs(self.app_data_dir, exist_ok=True)

        except OSError as e:
            QMessageBox.critical(self, "Fatal Error", f"Could not create data directory: {e}")
            sys.exit(1)  # Exit if we can't create the data directory

        self.dictionary_file = os.path.join(self.app_data_dir, "conlang_dictionary.json")
        self.tags_file = os.path.join(self.app_data_dir, "conlang_tags.json")
        self.grammar_file = os.path.join(self.app_data_dir, "conlang_grammar.json")
        self.light_dark_mode = os.path.join(self.app_data_master_dir, "dark_light_mode.txt")

        try:
            with open(self.light_dark_mode, "r") as f:
                data = f.read()

            if data == "l":
                self.set_light_mode()
            else:
                self.set_dark_mode()
        except FileNotFoundError:
            self.set_light_mode()

        if os.path.exists(self.dictionary_file):
            self.check_old_file_and_update()
        else:
            dialog = OpenProjectDialog(self)
            dialog.exec()

        # --- Load Data ---
        self.dictionary = self.load_dictionary()
        self.all_tags, self.word_classes = self.load_tags()
        self.grammar_data = self.load_grammar()

        # --- Create UI ---
        self.create_widgets()

        # --- Initial Population ---
        self.update_word_display()
        self.update_tag_filter_listbox()
        self.update_grammar_table_listbox()
        self.load_grammar_rules()

    # --- Data Load/Save Methods (Mostly unchanged, except for dialogs) ---

    def load_dictionary(self):
        if not os.path.exists(self.dictionary_file):
            return []
        try:
            with open(self.dictionary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure backward compatibility
                for entry in data:
                    entry.setdefault('pos', 'Other')
                    entry.setdefault('description', '')
                    entry.setdefault('tags', [])
                    entry.setdefault('roots', [])
                    entry.setdefault('derived', [])
                    # Ensure english is always a list
                    if 'english' not in entry or not isinstance(entry['english'], list):
                        entry['english'] = [str(entry.get('english', ''))]
                return data
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.critical(self, "Error Loading Dictionary", f"Could not read dictionary file: {e}")
            return []

    def save_dictionary(self):
        try:
            with open(self.dictionary_file, 'w', encoding='utf-8') as f:
                json.dump(self.dictionary, f, ensure_ascii=False, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Error Saving Dictionary", f"Could not save to dictionary file: {e}")

    def load_tags(self):
        if not os.path.exists(self.tags_file):
            return [], [
                "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction", "Interjection",
                "Prefix", "Suffix"
            ]
        try:
            with open(self.tags_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                if type(data) == list:
                    return data, [
                        "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction", "Interjection",
                        "Prefix", "Suffix"
                    ]
                else:
                    return data["tags"], data["pos"]
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.critical(self, "Error Loading Tags", f"Could not read tags file: {e}")
            return [], [
                "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction", "Interjection",
                "Prefix", "Suffix"
            ]

    def save_tags(self):
        try:
            self.all_tags.sort()
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump({"tags": self.all_tags, "pos": self.word_classes}, f, ensure_ascii=False, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Error Saving Tags", f"Could not save to tags file: {e}")

    def load_grammar(self):
        if not os.path.exists(self.grammar_file):
            return {"rules": "", "tables": {}}
        try:
            with open(self.grammar_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data.setdefault('rules', '')
                data.setdefault('tables', {})

                # --- Migration ---
                # Check for old string-based table data and migrate
                migrated_tables = {}
                for table_name, content in data['tables'].items():
                    if isinstance(content, str):
                        # This is old data. Migrate it to the new structure.
                        print(f"Migrating old grammar table: {table_name}")
                        migrated_data = {
                            "data": [[content]],
                            "row_headers": ["1"],
                            "col_headers": ["Notes"]
                        }
                        migrated_tables[table_name] = migrated_data
                    elif isinstance(content, dict):
                        # This is new data, just ensure it has all keys
                        content.setdefault("data", [[]])
                        content.setdefault("row_headers", [])
                        content.setdefault("col_headers", [])
                        migrated_tables[table_name] = content

                data['tables'] = migrated_tables
                # --- End Migration ---

                return data
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.critical(self, "Error Loading Grammar", f"Could not read grammar file: {e}")
            return {"rules": "", "tables": {}}

    def save_grammar(self):
        try:
            with open(self.grammar_file, 'w', encoding='utf-8') as f:
                json.dump(self.grammar_data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Error Saving Grammar", f"Could not save to grammar file: {e}")

    def check_old_file_and_update(self):
        if os.path.exists(self.dictionary_file):
            wizard = SetProjectNameUpdateErrorWizard(info_parent=self)

            if wizard.exec():
                name = wizard.field("name")

                new_location = os.path.join(self.app_data_master_dir, name)
                os.makedirs(new_location, exist_ok=True)

                if os.path.exists(self.dictionary_file):
                    new_dict_path = os.path.join(new_location, "conlang_dictionary.json")
                    shutil.move(self.dictionary_file, new_location)
                    self.dictionary_file = new_dict_path

                if os.path.exists(self.tags_file):
                    new_tags_path = os.path.join(new_location, "conlang_tags.json")
                    shutil.move(self.tags_file, new_location)
                    self.tags_file = new_tags_path

                if os.path.exists(self.grammar_file):
                    new_grammar_path = os.path.join(new_location, "conlang_grammar.json")
                    shutil.move(self.grammar_file, new_location)
                    self.grammar_file = new_grammar_path

                self.app_data_dir = new_location

    # --- UI Creation Methods ---

    def create_widgets(self):
        self.main_notebook = QTabWidget()
        self.setCentralWidget(self.main_notebook)

        self.create_menu_bar()

        # Create tabs
        self.tab_dictionary = QWidget()
        self.tab_word_generator = QWidget()
        self.tab_grammar = QWidget()
        self.tab_stats = QWidget()
        self.tab_help = QWidget()

        self.main_notebook.addTab(self.tab_dictionary, 'Dictionary')
        self.main_notebook.addTab(self.tab_word_generator, 'Word Generator')
        self.main_notebook.addTab(self.tab_grammar, 'Grammar Appendix')
        self.main_notebook.addTab(self.tab_stats, 'Statistics')
        self.main_notebook.addTab(self.tab_help, 'How To Use / Help')

        # Populate tabs
        self.create_dictionary_tab()
        self.create_word_generator_tab()
        self.create_grammar_tab()
        self.create_statistics_tab()
        self.create_help_tab()

    def create_menu_bar(self):
        self.menu_bar = self.menuBar()

        fileMenu = self.menu_bar.addMenu("&File")
        settingsMenu = self.menu_bar.addMenu("Settings")

        open_new_action = QAction("Open/New Project", self)
        open_new_action.triggered.connect(self.open_make_new_project)
        fileMenu.addAction(open_new_action)

        fileMenu.addSeparator()

        rename = QAction("Rename Project", self)
        rename.triggered.connect(self.rename_project)
        fileMenu.addAction(rename)

        delete = QAction("Delete Project", self)
        delete.triggered.connect(self.delete_project)
        fileMenu.addAction(delete)

        fileMenu.addSeparator()

        export_csv = QAction("Export as CSV", self)
        export_csv.triggered.connect(self.save_csv_file)
        fileMenu.addAction(export_csv)

        export_zip = QAction("Export as ZIP", self)
        export_zip.triggered.connect(self.export_to_zip)
        fileMenu.addAction(export_zip)

        import_zip = QAction("Import as ZIP", self)
        import_zip.triggered.connect(self.import_to_zip)
        fileMenu.addAction(import_zip)

        set_dark_mode = QAction("Darkmode", self)
        set_dark_mode.triggered.connect(self.set_dark_mode)
        settingsMenu.addAction(set_dark_mode)

        set_light_mode = QAction("Lightmode", self)
        set_light_mode.triggered.connect(self.set_light_mode)
        settingsMenu.addAction(set_light_mode)

    def create_dictionary_tab(self):
        main_layout = QHBoxLayout(self.tab_dictionary)  # Main layout for the tab

        # --- Left Panel ---
        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)  # Similar to fixed width in Tkinter

        # Search and Filter Group
        search_frame = QGroupBox("Search & Filter")
        search_frame_layout = QVBoxLayout(search_frame)

        search_frame_layout.addWidget(QLabel("Search Term:"))
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.update_word_display)
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

        clear_button = QPushButton("Clear Filters / Show All")
        clear_button.clicked.connect(self.clear_filters)
        search_frame_layout.addWidget(clear_button)

        left_panel_layout.addWidget(search_frame)
        left_panel_layout.addStretch(1)  # Pushes widgets to the top
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
        self.tree.horizontalHeader().setMinimumSectionSize(120)
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
        pos_button = QPushButton("Manage Parts of Speech")
        pos_button.clicked.connect(self.manage_pos)
        button_frame.addWidget(delete_button)
        button_frame.addWidget(edit_button)
        button_frame.addWidget(add_button)
        button_frame.addWidget(pos_button)
        button_frame.addStretch(1)
        dict_frame_layout.addLayout(button_frame)

        right_panel_layout.addWidget(dict_frame)

        # Details Notebook
        self.details_notebook = QTabWidget()
        self.details_notebook.setMaximumHeight(250)  # Set a max height

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
        # Use lambda to pass the argument
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

        right_panel_layout.addWidget(self.details_notebook)
        main_layout.addWidget(right_panel, 1)  # Add right panel with stretch factor 1

    def create_word_generator_tab(self):
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; padding: 5px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        main_layout = QHBoxLayout(self.tab_word_generator)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()

        self.content_layout = QVBoxLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        self.content_layout.addWidget(
            QLabel("Based on Kozuka. Go here for how to use: https://kozuka.kmwc.org/help.html")
        )

        patterns_group = QWidget()
        patterns_layout = QVBoxLayout(patterns_group)
        patterns_layout.setContentsMargins(0, 0, 0, 0)

        patterns_title = QLabel("Patterns")
        title_font = patterns_title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        patterns_title.setFont(title_font)
        patterns_layout.addWidget(patterns_title)

        # This layout will hold the dynamic pattern rows
        self.pattern_rows_layout = QVBoxLayout()
        patterns_layout.addLayout(self.pattern_rows_layout)

        add_pattern_button = QPushButton("+ Add pattern")
        add_pattern_button.clicked.connect(self.add_pattern_row)
        patterns_layout.addWidget(add_pattern_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.content_layout.addWidget(patterns_group)
        self.content_layout.addWidget(self._create_separator())

        main_pattern_layout = QHBoxLayout()
        main_pattern_label = QLabel("Main pattern:")
        self.main_pattern_input = QLineEdit()

        main_pattern_layout.addWidget(main_pattern_label)
        main_pattern_layout.addWidget(self.main_pattern_input, 1)  # 1 stretch factor

        self.content_layout.addLayout(main_pattern_layout)
        self.content_layout.addWidget(self._create_separator())

        controls_layout = QHBoxLayout()

        # --- Generating Box ---
        gen_box = QFrame()
        gen_box.setFrameShape(QFrame.Shape.StyledPanel)
        gen_layout = QGridLayout(gen_box)

        gen_layout.addWidget(QLabel("Number of words:"), 0, 0)
        self.num_words_input = QLineEdit("100")
        self.num_words_input.setFixedWidth(80)
        gen_layout.addWidget(self.num_words_input, 0, 1)

        generate_button = QPushButton(QIcon.fromTheme("view-refresh"), "Generate")
        generate_button.clicked.connect(self.generate_output)
        gen_layout.addWidget(generate_button, 3, 0, 1, 2)

        gen_layout.setColumnStretch(2, 1)  # Add stretch to the right

        controls_layout.addWidget(gen_box, 1)  # 1 stretch factor

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

    def create_grammar_tab(self):
        # Use a splitter to allow resizing
        main_splitter = QSplitter(Qt.Orientation.Vertical, self.tab_grammar)
        layout = QHBoxLayout(self.tab_grammar)  # Main layout
        layout.addWidget(main_splitter)

        # Rules Pane
        rules_frame = QGroupBox("Grammar Rules")
        rules_layout = QVBoxLayout(rules_frame)
        self.grammar_rules_text = QTextEdit()
        rules_layout.addWidget(self.grammar_rules_text)
        save_rules_btn = QPushButton("Save Rules")
        save_rules_btn.clicked.connect(self.save_grammar_rules)
        rules_layout.addWidget(save_rules_btn)

        main_splitter.addWidget(rules_frame)

        # Tables Pane
        tables_frame = QGroupBox("Grammar Tables")
        tables_layout = QHBoxLayout(tables_frame)  # Horizontal layout
        tables_frame.setLayout(tables_layout)

        # Table List and Controls
        table_controls_frame = QWidget()
        table_controls_layout = QVBoxLayout(table_controls_frame)
        table_controls_layout.addWidget(QLabel("Tables:"))
        self.table_listbox = QListWidget()
        self.table_listbox.itemSelectionChanged.connect(self.load_table_into_editor)
        table_controls_layout.addWidget(self.table_listbox)

        create_table_btn = QPushButton("Create Table")
        create_table_btn.clicked.connect(self.create_grammar_table)
        table_controls_layout.addWidget(create_table_btn)

        delete_table_btn = QPushButton("Delete Table")
        delete_table_btn.clicked.connect(self.delete_grammar_table)
        table_controls_layout.addWidget(delete_table_btn)

        table_controls_frame.setMaximumWidth(250)
        tables_layout.addWidget(table_controls_frame)

        # Table Editor
        table_editor_frame = QWidget()
        table_editor_layout = QVBoxLayout(table_editor_frame)

        # --- New Table Controls ---
        table_edit_controls_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.clicked.connect(self.add_table_row)
        self.remove_row_btn = QPushButton("Remove Row")
        self.remove_row_btn.clicked.connect(self.remove_table_row)
        self.add_col_btn = QPushButton("Add Column")
        self.add_col_btn.clicked.connect(self.add_table_column)
        self.remove_col_btn = QPushButton("Remove Column")
        self.remove_col_btn.clicked.connect(self.remove_table_column)

        table_edit_controls_layout.addWidget(self.add_row_btn)
        table_edit_controls_layout.addWidget(self.remove_row_btn)
        table_edit_controls_layout.addStretch()
        table_edit_controls_layout.addWidget(self.add_col_btn)
        table_edit_controls_layout.addWidget(self.remove_col_btn)

        table_editor_layout.addLayout(table_edit_controls_layout)
        # --- End New Table Controls ---

        self.table_editor = QTableWidget()  # Replaced QTextEdit
        # Allow editing headers
        self.table_editor.horizontalHeader().setSectionsClickable(True)
        self.table_editor.verticalHeader().setSectionsClickable(True)
        self.table_editor.horizontalHeader().sectionDoubleClicked.connect(self.edit_table_header)
        self.table_editor.verticalHeader().sectionDoubleClicked.connect(self.edit_table_header)

        table_editor_layout.addWidget(self.table_editor)

        save_table_btn = QPushButton("Save Current Table")
        save_table_btn.clicked.connect(self.save_grammar_table)
        table_editor_layout.addWidget(save_table_btn)

        tables_layout.addWidget(table_editor_frame)  # Add to horizontal layout

        main_splitter.addWidget(tables_frame)
        main_splitter.setSizes([300, 500])  # Initial size split

    def create_statistics_tab(self):
        layout = QVBoxLayout(self.tab_stats)
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)

        refresh_btn = QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self.refresh_stats_page)
        layout.addWidget(refresh_btn)

        self.refresh_stats_page()  # Initial load

    def create_help_tab(self):
        layout = QVBoxLayout(self.tab_help)
        help_text_widget = QTextEdit()
        help_text_widget.setReadOnly(True)
        layout.addWidget(help_text_widget)

        # Help content (same as before)
        help_content = """Welcome to the Conlang Dictionary Builder!

This application helps you create, manage, and explore your constructed language. Here's a quick guide to its features.

== Dictionary Tab ==

* Search & Filter:
    - Search Term: Type to search in either the Conlang or English words.
    - Filter by Part of Speech: Select a Part of Speech to see only words of that type.
    - Filter by Tags: Select one or more tags to find words that have ALL of those tags.
    - Manage Tags: Add or remove tags from the global list. This does not remove tags from words that already use them.
    - Clear Filters: Resets all search and filter fields.

* Word List: This is the main list of your words.
    - Double-click (or select and click "Edit Selected") to edit a word.
    - Single-click to select a word and view its details below.
    - Delete Selected: Permanently deletes the selected word.
    - Add Word: Adds a new word. "Conlang Word" and "English Translation" are required. You can add multiple English translations by separating them with a comma (e.g., "set, place").
    - Manage Parts of Speech: Add or remove parts of speech to fit the needs of your conlang.

* Description Tab: Shows the "Description" notes for the selected word.

* Etymology Tab: Tracks word origins.
    - Root Words: Words that THIS word comes from (e.g., "walk" is a root of "walking").
    - Derived Words: Words that come from THIS word (e.g., "walking" is derived from "walk").
    - Adding/Removing: Use the buttons to link words. This creates a two-way link (adding a root to Word A automatically adds Word A as a derivative of Word B).
    - Jump to Word: Double-click a word in the "Roots" or "Derived" list to jump to it in the main dictionary.

== Word Generator Tab ==

* Generate Random Words:
    - Generation Rules/Formatting: This is based on a site called Kozuka made by autumn (https://github.com/auctumnus). It follows the same rules and they already made a very good page explaining them so view rules here: https://kozuka.kmwc.org/help.html
    - Using Output: Double click on one of the generated words to automatically open up an Add Word window with it autofilled into the conlang field.

== Grammar Appendix Tab ==

This tab is for your language's documentation.

* Grammar Rules: A single, large text box for your general notes (phonology, syntax, etc.).
    - IMPORTANT: This text is NOT saved automatically. You must click the "Save Rules" button to save your changes.

* Grammar Tables: A place to store multiple, separate tables (e.g., verb conjugations, noun declensions).
    - Create Table: Prompts you for a name and size and creates a new, blank table.
    - Delete Table: Deletes the selected table.
    - Editor: Click a table name to load it into the text editor on the right.
    - IMPORTANT: Changes to a table are NOT saved automatically. You must click "Save Current Table" to save your changes to the selected table.

== Saving Your Data ==

* Dictionary: Your dictionary is automatically saved to conlang_dictionary.json every time you add, edit, or delete a word.
* Grammar: Your grammar rules and tables are saved to conlang_grammar.json ONLY when you click the "Save Rules" or "Save Current Table" buttons.
* Tags: Your tag list is saved to conlang_tags.json when you add or remove tags via the "Manage Tags" window.
"""
        help_text_widget.setText(help_content)

    # --- Dictionary Methods ---

    def populate_dictionary_list(self, entries):
        # Disable sorting while populating
        self.tree.setSortingEnabled(False)

        # Disconnect signal to avoid triggering on_item_select for every row
        try:
            self.tree.itemSelectionChanged.disconnect(self.on_item_select)
        except TypeError:
            pass  # Already disconnected

        self.tree.setRowCount(0)  # Clear the table

        entries.sort(key=lambda x: x['conlang'].lower())

        for entry in entries:
            row_position = self.tree.rowCount()
            self.tree.insertRow(row_position)

            tags_str = ", ".join(entry.get('tags', []))
            english_str = ", ".join(entry.get('english', []))

            # Create QTableWidgetItem for each cell
            conlang_item = QTableWidgetItem(entry["conlang"])
            english_item = QTableWidgetItem(english_str)
            pos_item = QTableWidgetItem(entry["pos"])
            tags_item = QTableWidgetItem(tags_str)

            # Store the conlang word in the first item's data for easy retrieval
            conlang_item.setData(Qt.ItemDataRole.UserRole, entry["conlang"])

            # Add items to the table
            self.tree.setItem(row_position, 0, conlang_item)
            self.tree.setItem(row_position, 1, english_item)
            self.tree.setItem(row_position, 2, pos_item)
            self.tree.setItem(row_position, 3, tags_item)

        # Re-enable sorting and reconnect signal
        self.tree.setSortingEnabled(True)
        self.tree.itemSelectionChanged.connect(self.on_item_select)

        # Clear details display
        self.on_item_select()

    def update_word_display(self, event=None):
        filtered_list = self.dictionary[:]

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
                    # Check if search term is in any of the English words
                    if any(search_term in word.lower() for word in entry.get("english", [])):
                        new_filtered_list.append(entry)
                filtered_list = new_filtered_list

        self.populate_dictionary_list(filtered_list)

    def add_word(self, word=None, flag=None):
        dialog = AddWordDialog(word=word, word_classes=self.word_classes, parent=self)
        if dialog.exec():  # This blocks until dialog is accepted or rejected
            # Dialog was accepted (Save clicked)
            new_data = dialog.new_entry_data

            conlang_word = new_data["conlang"]
            english_words = new_data["english"]
            pos = new_data["pos"]
            description = new_data["description"]
            tags_list = new_data["tags"]

            if not conlang_word or not english_words:
                QMessageBox.warning(self, "Input Error", "Conlang and English fields are required.")
                return

            if any(entry['conlang'].lower() == conlang_word.lower() for entry in self.dictionary):
                QMessageBox.warning(self, "Duplicate Entry", f"The word '{conlang_word}' already exists.")
                return

            if not pos:
                QMessageBox.warning(self, "Input Error", "Part of Speech is required.")
                return

            self._update_tags(tags_list)

            new_entry = {
                "conlang": conlang_word,
                "english": english_words,
                "pos": pos,
                "description": description,
                "tags": tags_list,
                "roots": [],
                "derived": []
            }
            self.dictionary.append(new_entry)
            self.save_dictionary()
            self.update_word_display()  # Refresh list

            if flag:
                self.select_word_in_table(conlang_word)

            self.refresh_stats_page()

    def delete_word(self):
        selected_row = self.tree.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "Please select a word to delete.")
            return

        conlang_word = self.tree.item(selected_row, 0).text()
        entry_to_delete = self.get_entry(conlang_word)
        if not entry_to_delete: return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{conlang_word}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Clean up etymology links
            for root_word in entry_to_delete.get('roots', []):
                root_entry = self.get_entry(root_word)
                if root_entry and conlang_word in root_entry.get('derived', []):
                    root_entry['derived'].remove(conlang_word)

            for derived_word in entry_to_delete.get('derived', []):
                derived_entry = self.get_entry(derived_word)
                if derived_entry and conlang_word in derived_entry.get('roots', []):
                    derived_entry['roots'].remove(conlang_word)

            self.dictionary.remove(entry_to_delete)
            self.save_dictionary()
            self.update_word_display()  # Refreshes and clears selection
            QMessageBox.information(self, "Success", f"Deleted '{conlang_word}'.")
            self.refresh_stats_page()

    def edit_word(self):
        selected_row = self.tree.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "Please select a word to edit.")
            return

        conlang_word = self.tree.item(selected_row, 0).text()
        entry_to_edit = self.get_entry(conlang_word)
        if not entry_to_edit:
            return

        # Open the dialog
        dialog = EditWordDialog(entry_to_edit, self.word_classes, self)
        if dialog.exec():  # This blocks until dialog is accepted or rejected
            # Dialog was accepted (Save clicked)
            new_data = dialog.new_entry_data
            if not new_data: return  # Should be caught by dialog, but as a safeguard

            old_conlang = entry_to_edit['conlang']
            new_conlang = new_data['conlang']

            # Check for duplicate if conlang word changed
            if new_conlang.lower() != old_conlang.lower() and any(
                    e['conlang'].lower() == new_conlang.lower() for e in self.dictionary):
                QMessageBox.critical(self, "Error", "The new conlang word already exists.")
                return

            # Update tags
            self._update_tags(new_data['tags'])

            # Update the entry in the dictionary list
            entry_to_edit.update(new_data)

            # Update etymology links if conlang word changed
            if new_conlang != old_conlang:
                for root_word in entry_to_edit.get('roots', []):
                    root_entry = self.get_entry(root_word)
                    if root_entry and old_conlang in root_entry.get('derived', []):
                        root_entry['derived'].remove(old_conlang)
                        root_entry['derived'].append(new_conlang)

                for derived_word in entry_to_edit.get('derived', []):
                    derived_entry = self.get_entry(derived_word)
                    if derived_entry and old_conlang in derived_entry.get('roots', []):
                        derived_entry['roots'].remove(old_conlang)
                        derived_entry['roots'].append(new_conlang)

            self.save_dictionary()
            self.update_word_display()
            # Manually update selection to new name
            self.select_word_in_table(new_conlang)
            self.refresh_stats_page()

    def on_item_double_click(self, item):
        # The item parameter is passed, but edit_word() uses currentRow()
        self.edit_word()

    def on_item_select(self):
        selected_row = self.tree.currentRow()
        description = ""
        entry = None

        if selected_row != -1:
            conlang_word = self.tree.item(selected_row, 0).text()
            entry = self.get_entry(conlang_word)
            if entry:
                description = entry.get('description', '')

        self.display_description_text.setText(description)
        self.update_etymology_display(entry)

    def clear_filters(self):
        self.search_entry.clear()
        self.filter_pos_listbox.clearSelection()
        self.tag_filter_listbox.clearSelection()
        self.radio_conlang.setChecked(True)
        # update_word_display will be triggered by the radio button change

    def update_tag_filter_listbox(self):
        # Save current selection
        selected_tags = {item.text() for item in self.tag_filter_listbox.selectedItems()}

        self.tag_filter_listbox.clear()

        # Repopulate
        new_items = []
        for tag in sorted(self.all_tags):
            item = QListWidgetItem(tag)
            self.tag_filter_listbox.addItem(item)
            if tag in selected_tags:
                new_items.append(item)

        # Restore selection
        for item in new_items:
            item.setSelected(True)

    def update_filter_pos_listbox(self):
        selected_pos = {item.text() for item in self.filter_pos_listbox.selectedItems()}

        self.filter_pos_listbox.clear()

        # Repopulate
        new_items = []
        for pos in sorted(self.word_classes):
            item = QListWidgetItem(pos)
            self.filter_pos_listbox.addItem(item)
            if pos in selected_pos:
                new_items.append(item)

        # Restore selection
        for item in new_items:
            item.setSelected(True)

    def manage_tags(self):
        dialog = ManageTagsDialog(self.all_tags, self)
        dialog.exec()

        if dialog.tags_changed:
            self.save_tags()
            self.update_tag_filter_listbox()

    def manage_pos(self):
        dialog = ManagePOSDialog(self.word_classes, self)
        dialog.exec()

        if dialog.pos_changed:
            self.save_tags()
            self.update_filter_pos_listbox()

    def get_entry(self, conlang_word):
        # Helper to find a dictionary entry by its conlang word.
        return next((item for item in self.dictionary if item["conlang"].lower() == conlang_word.lower()), None)

    def update_etymology_display(self, entry):
        self.roots_listbox.clear()
        self.derived_listbox.clear()

        if entry:
            for root_word in sorted(entry.get('roots', [])):
                self.roots_listbox.addItem(root_word)
            for derived_word in sorted(entry.get('derived', [])):
                self.derived_listbox.addItem(derived_word)

    def add_etymology_link(self, link_type):
        selected_row = self.tree.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "No Word Selected", "Please select a word to add a link to.")
            return

        selected_word_id = self.tree.item(selected_row, 0).text()
        entry_A = self.get_entry(selected_word_id)
        if not entry_A: return

        prompt = f"Enter the conlang word that is a {link_type} of '{selected_word_id}':"
        word_B_name, ok = QInputDialog.getText(self, "Add Etymology Link", prompt)

        if not ok or not word_B_name or word_B_name.strip() == "":
            return

        word_B_name = word_B_name.strip()

        if word_B_name.lower() == selected_word_id.lower():
            QMessageBox.warning(self, "Self-Link", "A word cannot be its own root or derivative.")
            return

        entry_B = self.get_entry(word_B_name)
        if not entry_B:
            QMessageBox.critical(self, "Word Not Found", f"The word '{word_B_name}' does not exist in the dictionary.")
            return

        if link_type == 'root':
            if word_B_name not in entry_A['roots']: entry_A['roots'].append(word_B_name)
            if selected_word_id not in entry_B['derived']: entry_B['derived'].append(selected_word_id)
        elif link_type == 'derived':
            if word_B_name not in entry_A['derived']: entry_A['derived'].append(word_B_name)
            if selected_word_id not in entry_B['roots']: entry_B['roots'].append(selected_word_id)

        self.save_dictionary()
        self.update_etymology_display(entry_A)

    def remove_etymology_link(self, link_type):
        selected_row = self.tree.currentRow()
        if selected_row == -1: return

        entry_A = self.get_entry(self.tree.item(selected_row, 0).text())
        if not entry_A: return

        listbox = self.roots_listbox if link_type == 'root' else self.derived_listbox
        selected_items = listbox.selectedItems()

        if not selected_items:
            QMessageBox.warning(self, "No Link Selected", f"Please select a {link_type} word to remove.")
            return

        word_B_name = selected_items[0].text()
        entry_B = self.get_entry(word_B_name)

        selected_word_id = entry_A['conlang']

        if link_type == 'root':
            if word_B_name in entry_A['roots']: entry_A['roots'].remove(word_B_name)
            if entry_B and selected_word_id in entry_B['derived']:
                entry_B['derived'].remove(selected_word_id)
        elif link_type == 'derived':
            if word_B_name in entry_A['derived']: entry_A['derived'].remove(word_B_name)
            if entry_B and selected_word_id in entry_B['roots']:
                entry_B['roots'].remove(selected_word_id)

        self.save_dictionary()
        self.update_etymology_display(entry_A)

    def select_word_in_table(self, conlang_word):
        """Finds and selects a word in the main QTableWidget."""
        # findItems returns a list of matching items
        items = self.tree.findItems(conlang_word, Qt.MatchFlag.MatchExactly)
        if items:
            # We only care about matches in the first column (col 0)
            for item in items:
                if item.column() == 0:
                    self.tree.setCurrentItem(item)
                    self.tree.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
                    return

    def jump_to_word_from_listbox(self, item: QListWidgetItem):
        word_to_find = item.text()

        items = self.tree.findItems(word_to_find, Qt.MatchFlag.MatchExactly)
        if items:
            # Find the item in column 0
            for found_item in items:
                if found_item.column() == 0:
                    self.tree.setCurrentItem(found_item)
                    self.tree.scrollToItem(found_item, QAbstractItemView.ScrollHint.EnsureVisible)
                    self.main_notebook.setCurrentWidget(self.tab_dictionary)
                    # on_item_select will be triggered by setCurrentItem
                    return

        QMessageBox.warning(self, "Link Error", f"The word '{word_to_find}' seems to be missing or filtered.")

    # --- Grammar Rules ---

    def load_grammar_rules(self):
        self.grammar_rules_text.setText(self.grammar_data.get('rules', ''))

    def save_grammar_rules(self):
        self.grammar_data['rules'] = self.grammar_rules_text.toPlainText().strip()
        self.save_grammar()
        QMessageBox.information(self, "Success", "Grammar rules saved.")

    # --- Stats Page ---

    def refresh_stats_page(self):
        total_words = len(self.dictionary)

        # Initialize counts
        parts_of_speech = {pos: 0 for pos in self.word_classes}
        tags = {tag: 0 for tag in self.all_tags}

        root_words = 0
        terminal_words = 0

        for word in self.dictionary:
            pos = word.get("pos", "Other")
            if pos in parts_of_speech:
                parts_of_speech[pos] += 1

            for tag in word.get("tags", []):
                if tag in tags:
                    tags[tag] += 1

            if not word.get("roots", []):
                root_words += 1

            if not word.get("derived", []):
                terminal_words += 1

        stats_lines = []
        stats_lines.append(f"Total Words: {total_words}")
        stats_lines.append(f"Root Words: {root_words} (no roots)")
        stats_lines.append(f"Terminal Words: {terminal_words} (no derivatives)")
        stats_lines.append("\n== Parts of Speech ==")

        for pos, count in parts_of_speech.items():
            if count > 0:
                stats_lines.append(f"{pos}: {count}")

        stats_lines.append("\n== Tags ==")

        for tag, count in sorted(tags.items()):
            if count > 0:
                stats_lines.append(f"{tag}: {count}")

        self.stats_text.setText("\n".join(stats_lines))

    # --- Kozuka Logic ---

    def add_pattern_row(self):
        """Adds a new pattern row (name, pattern, remove button) to the layout."""
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Name")

        pattern_input = QLineEdit()
        pattern_input.setPlaceholderText("Pattern")

        remove_button = QPushButton("- Remove")

        # Connect the remove button to a lambda that removes its parent widget
        remove_button.clicked.connect(lambda: self.remove_pattern_row(row_widget))

        row_layout.addWidget(name_input, 1)  # 1 stretch factor
        row_layout.addWidget(pattern_input, 3)  # 3 stretch factor
        row_layout.addWidget(remove_button)

        self.pattern_rows_layout.addWidget(row_widget)

    def remove_pattern_row(self, row_widget):
        """Removes a specific pattern row widget."""
        # Check if it's the last row, if so, don't remove
        if self.pattern_rows_layout.count() > 1:
            self.pattern_rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        else:
            self.show_error("You must have at least one pattern.")

    def _create_separator(self):
        """Helper to create a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def generate_output(self):
        settings = self.get_settings()
        self.gen_output_listbox.clear()

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

            # 1. Use findChildren (plural) ONCE to get a list of all QLineEdits
            all_line_edits = row_widget.findChildren(QLineEdit, None, Qt.FindChildOption.FindChildrenRecursively)

            # 2. Now access the items from the list
            # (It's much safer to check the length first!)
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
        self.add_word(item.text())

    # --- Menu Bar ---

    def open_make_new_project(self):
        dialog = OpenProjectDialog(self, flag=True)
        if dialog.exec():
            self.dictionary = self.load_dictionary()
            self.all_tags, self.word_classes = self.load_tags()
            self.grammar_data = self.load_grammar()

            self.update_word_display()
            self.update_tag_filter_listbox()
            self.update_grammar_table_listbox()
            self.load_grammar_rules()

    def rename_project(self):
        dialog = RenameProjectDialog(self)
        dialog.exec()

    def delete_project(self):
        dialog = ImportantWarningDialog("Are you sure you wish to delete this project?", self)
        if dialog.exec():
            shutil.rmtree(self.app_data_dir)

        self.open_make_new_project()

    def save_csv_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")

        if file_name:
            try:
                with open(f"{file_name}.csv", "w") as f:
                    headers = ['conlang', 'english', 'pos', 'description', 'tags', 'roots', 'derived']

                    writer = csv.DictWriter(f, fieldnames=headers)

                    # Write the header row to the CSV
                    writer.writeheader()

                    # Loop through each word entry in the JSON data
                    for entry in self.dictionary:
                        # Create a dictionary for the new CSV row
                        # Use .get() for safety, providing a default value

                        # For list fields, join them with a '|' character
                        # For simple fields, just get the value
                        row_data = {
                            'conlang': entry.get('conlang', ''),
                            'english': '|'.join(entry.get('english', [])),
                            'pos': entry.get('pos', ''),
                            'description': entry.get('description', ''),
                            'tags': '|'.join(entry.get('tags', [])),
                            'roots': '|'.join(entry.get('roots', [])),
                            'derived': '|'.join(entry.get('derived', []))
                        }

                        # Write the processed row to the CSV file
                        writer.writerow(row_data)
            except Exception as e:
                error_dialog = QErrorMessage()
                error_dialog.showMessage(f"Error saving file: {e}")

    def export_to_zip(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Project", "", "ZIP Files (*.zip)")

        if file_name:
            try:
                zip_folder(self.app_data_dir, file_name)
            except Exception as e:
                error_dialog = QErrorMessage()
                error_dialog.showMessage(f"Error exporting project: {e}")

    def import_to_zip(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Import Project", "", "ZIP Files (*.zip)")

        if file_name:
            try:
                if file_name.split("/")[-1].split(".")[0] in get_folder_names(self.app_data_master_dir):
                    dialog = ImportantWarningDialog(
                        "A project with the same name already exists! Do you wish to replace this project?"
                    )
                    if dialog.exec():
                        clear_folder(os.path.join(self.app_data_master_dir, file_name.split("/")[-1].split(".")[0]))
                        unzip_file(
                            file_name, os.path.join(self.app_data_master_dir, file_name.split("/")[-1].split(".")[0])
                        )

                        self.app_data_dir = os.path.join(
                            self.app_data_master_dir, file_name.split("/")[-1].split(".")[0]
                        )

                        self.dictionary_file = os.path.join(self.app_data_dir, "conlang_dictionary.json")
                        self.tags_file = os.path.join(self.app_data_dir, "conlang_tags.json")
                        self.grammar_file = os.path.join(self.app_data_dir, "conlang_grammar.json")

                        self.dictionary = self.load_dictionary()
                        self.all_tags, self.word_classes = self.load_tags()
                        self.grammar_data = self.load_grammar()

                        self.update_word_display()
                        self.update_tag_filter_listbox()
                        self.update_grammar_table_listbox()
                        self.load_grammar_rules()
                else:
                    unzip_file(
                        file_name, os.path.join(self.app_data_master_dir, file_name.split("/")[-1].split(".")[0])
                    )
            except Exception as e:
                error_dialog = QErrorMessage()
                error_dialog.showMessage(f"Error importing project: {e}")

    def set_dark_mode(self):
        QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)

        with open(self.light_dark_mode, "w") as f:
            f.write("d")

    def set_light_mode(self):
        QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Light)

        with open(self.light_dark_mode, "w") as f:
            f.write("l")

    # --- Tables ---

    def update_grammar_table_listbox(self):
        self.table_listbox.clear()
        for table_name in sorted(self.grammar_data['tables'].keys()):
            self.table_listbox.addItem(table_name)

    def load_table_into_editor(self):
        selected_items = self.table_listbox.selectedItems()

        # Clear table first
        self.table_editor.clear()
        self.table_editor.setRowCount(0)
        self.table_editor.setColumnCount(0)

        if not selected_items:
            return

        table_name = selected_items[0].text()
        table_data = self.grammar_data['tables'].get(table_name)

        if not table_data or not isinstance(table_data, dict):
            return

        data = table_data.get("data", [[]])
        row_headers = table_data.get("row_headers", [])
        col_headers = table_data.get("col_headers", [])

        num_rows = len(data)
        num_cols = len(data[0]) if num_rows > 0 else 0

        self.table_editor.setRowCount(num_rows)
        self.table_editor.setColumnCount(num_cols)

        self.table_editor.setVerticalHeaderLabels(row_headers)
        self.table_editor.setHorizontalHeaderLabels(col_headers)

        for r_idx, row in enumerate(data):
            # Ensure row has correct number of columns (for data integrity)
            if len(row) != num_cols:
                row.extend([""] * (num_cols - len(row)))

            for c_idx, cell_content in enumerate(row):
                self.table_editor.setItem(r_idx, c_idx, QTableWidgetItem(str(cell_content)))

    def save_grammar_table(self):
        selected_items = self.table_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Table Selected", "Please select a table to save.")
            return

        table_name = selected_items[0].text()

        num_rows = self.table_editor.rowCount()
        num_cols = self.table_editor.columnCount()

        new_data = []
        new_row_headers = []
        new_col_headers = []

        for r in range(num_rows):
            row_data = []
            header_item = self.table_editor.verticalHeaderItem(r)
            new_row_headers.append(header_item.text() if header_item else str(r + 1))

            for c in range(num_cols):
                item = self.table_editor.item(r, c)
                row_data.append(item.text() if item and item.text() is not None else "")
            new_data.append(row_data)

        for c in range(num_cols):
            header_item = self.table_editor.horizontalHeaderItem(c)
            new_col_headers.append(header_item.text() if header_item else f"Col {c + 1}")

        table_object = {
            "data": new_data,
            "row_headers": new_row_headers,
            "col_headers": new_col_headers
        }

        self.grammar_data['tables'][table_name] = table_object
        self.save_grammar()
        QMessageBox.information(self, "Success", f"Table '{table_name}' saved.")

    def create_grammar_table(self):
        table_name, ok = QInputDialog.getText(self, "Create Table", "Enter a name for the new table:")

        if not ok or not table_name or table_name.strip() == "":
            return

        table_name = table_name.strip()

        # Check if table name already exists in the listbox
        existing_tables = [self.table_listbox.item(i).text() for i in range(self.table_listbox.count())]
        if table_name in existing_tables:
            QMessageBox.warning(self, "Duplicate", f"A table named '{table_name}' already exists.")
            return

        num_rows, ok_r = QInputDialog.getInt(self, "Create Table", "Enter number of rows:", 3, 1, 100)
        if not ok_r: return
        num_cols, ok_c = QInputDialog.getInt(self, "Create Table", "Enter number of columns:", 3, 1, 100)
        if not ok_c: return

        default_data = [["" for _ in range(num_cols)] for _ in range(num_rows)]
        default_row_headers = [str(i + 1) for i in range(num_rows)]
        default_col_headers = [f"Header {i + 1}" for i in range(num_cols)]

        new_table = {
            "data": default_data,
            "row_headers": default_row_headers,
            "col_headers": default_col_headers
        }

        self.grammar_data['tables'][table_name] = new_table
        self.save_grammar()

        self.update_grammar_table_listbox()

        # Find and select the new table
        items = self.table_listbox.findItems(table_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.table_listbox.setCurrentItem(items[0])
            # load_table_into_editor will be called by the selection signal

    def delete_grammar_table(self):
        selected_items = self.table_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Table Selected", "Please select a table to delete.")
            return

        table_name = selected_items[0].text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the table '{table_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        del self.grammar_data['tables'][table_name]
        self.save_grammar()
        self.update_grammar_table_listbox()  # This will clear selection
        self.table_editor.clear()  # Clear table
        self.table_editor.setRowCount(0)
        self.table_editor.setColumnCount(0)

    def add_table_row(self):
        current_row = self.table_editor.currentRow()
        if current_row == -1:
            # If no row is selected, add to the end
            current_row = self.table_editor.rowCount()

        self.table_editor.insertRow(current_row)

        # Set default header
        new_header = QTableWidgetItem(str(current_row + 1))
        self.table_editor.setVerticalHeaderItem(current_row, new_header)
        # Fix subsequent headers
        for r in range(current_row + 1, self.table_editor.rowCount()):
            self.table_editor.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))

    def remove_table_row(self):
        current_row = self.table_editor.currentRow()
        if current_row != -1:
            self.table_editor.removeRow(current_row)
            # Fix subsequent headers
            for r in range(current_row, self.table_editor.rowCount()):
                self.table_editor.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))

    def add_table_column(self):
        current_col = self.table_editor.currentColumn()
        if current_col == -1:
            # If no col is selected, add to the end
            current_col = self.table_editor.columnCount()

        self.table_editor.insertColumn(current_col)

        # Set default header
        new_header = QTableWidgetItem(f"Header {current_col + 1}")
        self.table_editor.setHorizontalHeaderItem(current_col, new_header)
        # Fix subsequent headers
        for c in range(current_col + 1, self.table_editor.columnCount()):
            self.table_editor.setHorizontalHeaderItem(c, QTableWidgetItem(f"Header {c + 1}"))

    def remove_table_column(self):
        current_col = self.table_editor.currentColumn()
        if current_col != -1:
            self.table_editor.removeColumn(current_col)
            # Fix subsequent headers
            for c in range(current_col, self.table_editor.columnCount()):
                self.table_editor.setHorizontalHeaderItem(c, QTableWidgetItem(f"Header {c + 1}"))

    def edit_table_header(self, logical_index):
        sender = self.sender()

        if sender == self.table_editor.horizontalHeader():
            header_item = self.table_editor.horizontalHeaderItem(logical_index)
            old_text = header_item.text() if header_item else f"Header {logical_index + 1}"
            new_text, ok = QInputDialog.getText(self, "Edit Header", "Enter new column header:", text=old_text)

            if ok and new_text:
                self.table_editor.setHorizontalHeaderItem(logical_index, QTableWidgetItem(new_text))

        elif sender == self.table_editor.verticalHeader():
            header_item = self.table_editor.verticalHeaderItem(logical_index)
            old_text = header_item.text() if header_item else str(logical_index + 1)
            new_text, ok = QInputDialog.getText(self, "Edit Header", "Enter new row header:", text=old_text)

            if ok and new_text:
                self.table_editor.setVerticalHeaderItem(logical_index, QTableWidgetItem(new_text))

    # --- Random/Utility ---

    def _update_tags(self, tags_list):
        # Update global tags from a list of tags for a word.
        new_tag_found = False
        for tag in tags_list:
            if tag not in self.all_tags:
                self.all_tags.append(tag)
                new_tag_found = True
        if new_tag_found:
            self.save_tags()
            self.update_tag_filter_listbox()

    def show_error(self, message):
        """Displays an error message in the error label."""
        self.error_label.setText(message)
        self.error_label.show()

    def closeEvent(self, event):
        # In this app, data is saved automatically or via buttons,
        # so there's no need to prompt on close.
        # If we needed to, we'd pop up a QMessageBox here.
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply a simple stylesheet for a cleaner look
    app.setStyleSheet("""
        QWidget {
            font-size: 10pt;
        }
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px 5px 5px;
        }
        QPushButton {
            padding: 5px 10px;
        }
        QTableWidget {
            gridline-color: #ddd;
        }
        QHeaderView::section {
            padding: 4px;
            border: 1px solid #ddd;
            font-weight: bold;
        }
    """)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
