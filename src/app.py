import sys
import os
import csv
import shutil
from pathlib import Path
import json
import uuid

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit,
    QTextEdit, QPushButton, QListWidget, QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog, QSplitter,
    QListWidgetItem, QScrollArea, QFrame, QFileDialog, QErrorMessage, QComboBox, QRadioButton, QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QGuiApplication, QShortcut, QKeySequence

from src.dialogs import (
    OpenProjectDialog, RenameProjectDialog, ImportantWarningDialog, WarningDialog, ManagePOSDialog, ManageTagsDialog,
    EditWordDialog, AddWordDialog, DebugDialog, WordSelectionDialog
)
from src.simulated_kozuka_logic import generate_words
from src.functions import zip_folder, unzip_file, get_folder_names, clear_folder, get_font, process_font
from src.custom_widgets import IPATable, DeselectableListWidget
from src.IPA_tables import PC_TABLE_DATA, NPC_TABLE_DATA, V_TABLE_DATA, OA_TABLE_DATA
from src.db_manager import DatabaseManager
from src.help import help_text


class ConlangDictionaryApp(QMainWindow):
    """
    A GUI application for creating, managing, and searching a dictionary for a
    constructed language, written in PySide6.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conlang Dictionary")
        self.setGeometry(100, 100, 1100, 800)

        # --- Data File Setup ---
        self._setup_directories()
        self._load_theme_mode()
        self.path = str(Path(__file__).parent.resolve())
        self.sound_path = None

        self.font_exists = False
        self.custom_font_on = True

        if sys.platform == "win32":
            path = self.path.split('\\')
        else:
            path = self.path.split('/')
        path.remove('src')

        try:
            path.remove('src')
        except ValueError:
            pass

        path = f"{'\\'.join(path)}/assets/logo.png"

        if os.path.exists(path):
            self.setWindowIcon(QIcon(path))
        else:
            self.setWindowIcon(QIcon("assets/logo.png"))

        dialog = OpenProjectDialog(self)
        dialog.exec()

        self.update_version()

        self.db_path = os.path.join(self.app_data_dir, "project.db")
        self.db = DatabaseManager(self.db_path)
        self.db.migrate_from_json(self.app_data_dir)

        # --- Load Data from SQL ---
        self.dictionary = self.load_dictionary()
        self.all_tags, self.word_classes = self.load_tags()
        self.grammar_data = self.load_grammar()
        self.presents = self.load_presents()
        self.font = self.load_font()
        self.font_family_name = process_font(self.font_file) if self.font_file else ""

        # --- Create UI ---
        self.create_widgets()

        # --- Initial Population ---
        self.update_word_display()
        self.update_tag_filter_listbox()
        self.update_grammar_table_listbox()
        self.load_grammar_rules()

        self.shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut.activated.connect(self.debug)

    def _setup_directories(self):
        try:
            if sys.platform == "win32":
                app_data_path = os.getenv('LOCALAPPDATA')
            elif sys.platform == "darwin":
                app_data_path = os.path.expanduser('~/Library/Application Support')
            else:
                app_data_path = os.path.expanduser("~/.local/share")
            self.app_data_dir = os.path.join(app_data_path, "ConlangDictionary")
            self.app_data_master_dir = self.app_data_dir
            os.makedirs(self.app_data_dir, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "Fatal Error", f"Could not create data directory: {e}")
            sys.exit(1)

    def _load_theme_mode(self):
        self.light_dark_mode = os.path.join(self.app_data_master_dir, "dark_light_mode.txt")
        try:
            with open(self.light_dark_mode, "r") as f:
                if f.read() == "l":
                    self.set_light_mode()
                else:
                    self.set_dark_mode()
        except FileNotFoundError:
            self.set_light_mode()

    # --- Data Load/Save Methods ---

    def save_dictionary(self):
        self.db.save_dictionary(self.dictionary)

    def save_tags(self):
        self.all_tags.sort()
        self.db.save_tags_and_pos(self.all_tags, self.word_classes)

    def save_grammar(self):
        self.db.save_grammar(self.grammar_data)

    def save_presents(self):
        self.db.save_presets(self.presents)

    def load_dictionary(self):
        return self.db.get_dictionary()

    def load_tags(self):
        return self.db.get_tags_and_pos()

    def load_grammar(self):
        return self.db.get_grammar()

    def load_presents(self):
        return self.db.get_presets()

    def load_font(self):
        self.font_file = os.path.join(self.app_data_dir, "font.ttf")
        if not os.path.exists(self.font_file):
            self.font_file = os.path.join(self.app_data_dir, "font.otf")

        if os.path.exists(self.font_file):
            self.font_exists = True

            result = get_font(self.font_file)

            if type(result) == str:
                QMessageBox.warning(self, "Error", result)
                return None
            else:
                return result
        else:
            return None

    def update_version(self):
        if not os.path.exists(self.dictionary_file):
            return
        try:
            with open(self.dictionary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    entry.setdefault('pos', 'Other')
                    entry.setdefault('description', '')
                    entry.setdefault('tags', [])
                    entry.setdefault('roots', [])
                    entry.setdefault('derived', [])
                    entry.setdefault('ipa', '')
                    entry.setdefault('syllable', '')
                    entry.setdefault('synonyms', [])
                    entry.setdefault('antonyms', [])
                    if 'english' not in entry or not isinstance(entry['english'], list):
                        entry['english'] = [str(entry.get('english', ''))]
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.critical(self, "Failure to Update", f"Could not read dictionary file: {e}")

        try:
            with open(self.dictionary_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Failure", f"Could not save to dictionary file: {e}")

        if not os.path.exists(self.tags_file):
            tags = []
            pos = [
                "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction", "Interjection",
                "Prefix", "Suffix"
            ]

            pos.sort()
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump({"tags": tags, "pos": pos}, f, ensure_ascii=False, indent=4)

        if not os.path.exists(self.grammar_file):
            grammar_data = {"rules": "", "tables": {}}

            with open(self.grammar_file, 'w', encoding='utf-8') as f:
                json.dump(grammar_data, f, ensure_ascii=False, indent=4)

        if not os.path.exists(self.generator_presents):
            with open(self.generator_presents, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    # --- UI Creation Methods ---

    def create_widgets(self):
        self.main_notebook = QTabWidget()
        self.setCentralWidget(self.main_notebook)

        self.create_menu_bar()

        self.tab_dictionary = QWidget()
        self.tab_word_generator = QWidget()
        self.tab_grammar = QWidget()
        self.tab_ipa = QWidget()
        self.tab_stats = QWidget()
        self.tab_help = QWidget()

        self.main_notebook.addTab(self.tab_dictionary, 'Dictionary')
        self.main_notebook.addTab(self.tab_word_generator, 'Word Generator')
        self.main_notebook.addTab(self.tab_grammar, 'Grammar Appendix')
        self.main_notebook.addTab(self.tab_ipa, 'IPA Chart')
        self.main_notebook.addTab(self.tab_stats, 'Statistics')
        self.main_notebook.addTab(self.tab_help, 'How To Use / Help')

        self.create_dictionary_tab()
        self.create_word_generator_tab()
        self.create_grammar_tab()
        self.create_ipa_tab()
        self.create_statistics_tab()
        self.create_help_tab()

    def create_menu_bar(self):
        self.menu_bar = self.menuBar()

        fileMenu = self.menu_bar.addMenu("&File")
        settingsMenu = self.menu_bar.addMenu("Settings")
        projectMenu = self.menu_bar.addMenu("Project")
        featureRequestMenu = self.menu_bar.addMenu("Feature Request")

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
        import_zip.triggered.connect(self.import_from_zip)
        fileMenu.addAction(import_zip)

        set_dark_mode = QAction("Dark Mode", self)
        set_dark_mode.triggered.connect(self.set_dark_mode)
        settingsMenu.addAction(set_dark_mode)

        set_light_mode = QAction("Light Mode", self)
        set_light_mode.triggered.connect(self.set_light_mode)
        settingsMenu.addAction(set_light_mode)

        import_font = QAction("Import Font", self)
        import_font.triggered.connect(self.add_font_script)
        projectMenu.addAction(import_font)

        feature_request = QAction("Request a Feature", self)
        feature_request.triggered.connect(self.make_feature_request)
        featureRequestMenu.addAction(feature_request)

    def create_dictionary_tab(self):
        main_layout = QHBoxLayout(self.tab_dictionary)

        # --- Left Panel ---
        left_panel = QWidget()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)

        # Search and Filter Group
        search_frame = QGroupBox("Search & Filter")
        search_frame_layout = QVBoxLayout(search_frame)

        search_frame_layout.addWidget(QLabel("Search Term:"))
        self.search_entry = QLineEdit()
        self.search_entry.textChanged.connect(self.update_word_display)
        self.default_font = self.search_entry.font()
        if self.font:
            self.search_entry.setFont(self.font)
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
        self.pattern_load_box.addItems([name["name"] for name in self.presents])
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

    def create_grammar_tab(self):
        main_splitter = QSplitter(Qt.Orientation.Vertical, self.tab_grammar)
        layout = QHBoxLayout(self.tab_grammar)
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
        tables_layout = QHBoxLayout(tables_frame)
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

        # Table Controls
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

        self.table_editor = QTableWidget()
        self.table_editor.horizontalHeader().setSectionsClickable(True)
        self.table_editor.verticalHeader().setSectionsClickable(True)
        self.table_editor.horizontalHeader().sectionDoubleClicked.connect(self.edit_table_header)
        self.table_editor.verticalHeader().sectionDoubleClicked.connect(self.edit_table_header)

        table_editor_layout.addWidget(self.table_editor)

        save_table_btn = QPushButton("Save Current Table")
        save_table_btn.clicked.connect(self.save_grammar_table)
        table_editor_layout.addWidget(save_table_btn)

        tables_layout.addWidget(table_editor_frame)

        main_splitter.addWidget(tables_frame)
        main_splitter.setSizes([300, 500])

    def create_ipa_tab(self):
        self.pc_table = IPATable(PC_TABLE_DATA, 9, 12, self)
        self.npc_table = IPATable(NPC_TABLE_DATA, 6, 3, self, 1)
        self.v_table = IPATable(V_TABLE_DATA, 8, 6, self)
        self.oa_table = IPATable(OA_TABLE_DATA, 11, 2, self, 1)

        self.pc_table.setFixedHeight(350)
        self.npc_table.setFixedHeight(230)
        self.v_table.setFixedHeight(310)
        self.oa_table.setFixedHeight(430)

        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.addWidget(self.pc_table)
        container_layout.addWidget(self.npc_table)
        container_layout.addWidget(self.v_table)
        container_layout.addWidget(self.oa_table)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container_widget)

        layout = QVBoxLayout(self.tab_ipa)
        layout.addWidget(scroll_area)

    def create_statistics_tab(self):
        layout = QVBoxLayout(self.tab_stats)
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)

        refresh_btn = QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self.refresh_stats_page)
        layout.addWidget(refresh_btn)

        self.refresh_stats_page()

    def create_help_tab(self):
        layout = QVBoxLayout(self.tab_help)
        help_text_widget = QTextEdit()
        help_text_widget.setReadOnly(True)
        layout.addWidget(help_text_widget)

        help_text_widget.setText(help_text)

    # --- Dictionary Page ---

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
            if self.custom_font_on:
                if self.font:
                    conlang_item.setFont(self.font)
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
        filtered_list = self.dictionary[:]

        if self.custom_font_on:
            if self.radio_conlang.isChecked():
                if self.font:
                    self.search_entry.setFont(self.font)
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
        self.add_word_dialog = AddWordDialog(word=word, word_classes=self.word_classes, parent=self)
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

        if not conlang_word or not english_words:
            QMessageBox.warning(self, "Input Error", "Conlang and English fields are required.")
            return

        if not pos:
            QMessageBox.warning(self, "Input Error", "Part of Speech is required.")
            return

        self._update_tags(tags_list)

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
        self.dictionary.append(new_entry)
        self.save_dictionary()
        self.update_word_display()

        if flag:
            self.select_word_in_table(new_entry["id"])

        self.refresh_stats_page()

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

            self.dictionary.remove(entry_to_delete)
            self.save_dictionary()
            self.update_word_display()
            QMessageBox.information(self, "Success", f"Deleted '{conlang_word}'.")
            self.refresh_stats_page()

    def edit_word(self):
        selected_row = self.tree.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Selection Error", "Please select a word to edit.")
            return

        word_id = self.tree.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
        self.entry_to_edit = self.get_entry_by_id(word_id)
        if not self.entry_to_edit:
            return

        self.delete_word_dialog = EditWordDialog(self.entry_to_edit, self.word_classes, self)
        self.delete_word_dialog.accepted.connect(lambda: self._process_edit_word())
        self.delete_word_dialog.show()

    def _process_edit_word(self):
        new_data = self.delete_word_dialog.new_entry_data
        if not new_data:
            return

        self._update_tags(new_data['tags'])
        self.entry_to_edit.update(new_data)

        self.save_dictionary()
        self.update_word_display()
        self.select_word_in_table(self.entry_to_edit["id"])
        self.refresh_stats_page()

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

                if self.custom_font_on:
                    if self.font:
                        description = (
                            f"<p style='font-size: 14pt'>"
                            f"<span style='font-family: \"{self.font_family_name}\"; font-size: 24pt; color: #2a82da;'>"
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
        for tag in sorted(self.all_tags):
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
        for pos in sorted(self.word_classes):
            item = QListWidgetItem(pos)
            self.filter_pos_listbox.addItem(item)
            if pos in selected_pos:
                new_items.append(item)

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

    def toggle_font(self):
        flag = False

        if self.tree.currentRow() != -1:
            flag = True
            row = self.tree.currentRow()
            item = self.tree.item(row, 0).text()

        self.custom_font_on = not self.custom_font_on
        self.update_word_display()

        if flag:
            self.select_word_in_table(item)

    def get_entry_by_id(self, word_id):
        return next((item for item in self.dictionary if item.get("id") == word_id), None)

    def find_entries_by_word(self, conlang_word):
        return [item for item in self.dictionary if item["conlang"].lower() == conlang_word.lower()]

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

        self.save_dictionary()
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

        self.save_dictionary()
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

        self.save_dictionary()
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

        self.save_dictionary()
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
        self.main_notebook.setCurrentWidget(self.tab_dictionary)

    # --- Grammar Page ---

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
        self.add_word(item.text())

    def save_pattern(self):
        name = self.pattern_save_name.text().strip()

        if not name:
            return

        self.pattern_save_name.clear()
        settings = self.get_settings()

        for present in self.presents:
            if present["name"] == name:
                dialog = WarningDialog(
                    "An existing pattern has this name, are you sure you want to overwrite that?", self
                )
                if dialog.exec():
                    present["patterns"] = settings["patterns"]
                    present["mainPattern"] = settings["mainPattern"]

                    self.pattern_load_box.clear()
                    self.pattern_load_box.addItems([name["name"] for name in self.presents])

                    self.save_presents()

                    return
                else:
                    return

        self.presents.append({"name": name, "patterns": settings["patterns"], "mainPattern": settings["mainPattern"]})

        self.pattern_load_box.clear()
        self.pattern_load_box.addItems([name["name"] for name in self.presents])

        self.save_presents()

    def load_pattern(self):
        preset_data = None

        name = self.pattern_load_box.currentText()
        for present in self.presents:
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

    # --- Menu Bar ---

    def open_make_new_project(self):
        dialog = OpenProjectDialog(self, flag=True)
        if dialog.exec():
            self.update_version()

            self.db_path = os.path.join(self.app_data_dir, "project.db")
            self.db = DatabaseManager(self.db_path)
            self.db.migrate_from_json(self.app_data_dir)

            self.dictionary = self.load_dictionary()
            self.all_tags, self.word_classes = self.load_tags()
            self.grammar_data = self.load_grammar()
            self.presents = self.load_presents()
            self.font = self.load_font()

            self.update_word_display()
            self.update_tag_filter_listbox()
            self.update_grammar_table_listbox()
            self.load_grammar_rules()

            self.refresh_stats_page()
            self.main_notebook.setCurrentIndex(0)

    def rename_project(self):
        dialog = RenameProjectDialog(self)
        dialog.exec()

    def delete_project(self):
        dialog = ImportantWarningDialog("Are you sure you wish to delete this project?", self)
        if dialog.exec():
            if hasattr(self, 'db') and self.db is not None:
                if hasattr(self.db, 'close'):
                    self.db.close()
                elif hasattr(self.db, 'conn'):
                    self.db.conn.close()
                self.db = None

            try:
                shutil.rmtree(self.app_data_dir)
            except OSError as e:
                QMessageBox.critical(self, "Deletion Error", f"Could not delete project folder:\n{e}")
                return

            open_dialog = OpenProjectDialog(self, True)
            open_dialog.exec()

            self.update_version()

            self.db_path = os.path.join(self.app_data_dir, "project.db")
            self.db = DatabaseManager(self.db_path)
            self.db.migrate_from_json(self.app_data_dir)

            self.dictionary = self.load_dictionary()
            self.all_tags, self.word_classes = self.load_tags()
            self.grammar_data = self.load_grammar()
            self.presents = self.load_presents()
            self.font = self.load_font()
            if self.font_file:
                self.font_family_name = process_font(self.font_file)
            else:
                self.font_family_name = ""

            self.update_word_display()
            self.update_tag_filter_listbox()
            self.update_grammar_table_listbox()
            self.load_grammar_rules()

            self.refresh_stats_page()
            self.main_notebook.setCurrentIndex(0)

    def save_csv_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")

        if file_name:
            try:
                with open(f"{file_name}", "w") as f:
                    headers = ['conlang', 'english', 'pos', 'description', 'tags', 'roots', 'derived']

                    writer = csv.DictWriter(f, fieldnames=headers)

                    writer.writeheader()

                    for entry in self.dictionary:
                        row_data = {
                            'conlang': entry.get('conlang', ''),
                            'english': '|'.join(entry.get('english', [])),
                            'syllabication': '|'.join(entry.get('syllable', '')),
                            'ipa': '|'.join(entry.get('ipa', '')),
                            'pos': entry.get('pos', ''),
                            'description': entry.get('description', ''),
                            'tags': '|'.join(entry.get('tags', [])),
                            'roots': '|'.join(entry.get('roots', [])),
                            'derived': '|'.join(entry.get('derived', [])),
                            'synonyms': '|'.join(entry.get('synonyms', [])),
                            'antonyms': '|'.join(entry.get('antonyms', []))
                        }

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

    def import_from_zip(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Import Project", "", "ZIP Files (*.zip)")

        if file_name:
            try:
                project_name = file_name.split("/")[-1].split(".")[0]
                new_project_dir = os.path.join(self.app_data_master_dir, project_name)

                if project_name in get_folder_names(self.app_data_master_dir):
                    dialog = ImportantWarningDialog(
                        "A project with the same name already exists! Do you wish to replace this project?", self
                    )
                    if dialog.exec():
                        clear_folder(new_project_dir)
                    else:
                        return

                unzip_file(file_name, new_project_dir)

                self.app_data_dir = new_project_dir

                self.db_path = os.path.join(self.app_data_dir, "project.db")
                self.db = DatabaseManager(self.db_path)

                self.db.migrate_from_json(self.app_data_dir)

                self.dictionary = self.db.get_dictionary()
                self.all_tags, self.word_classes = self.db.get_tags_and_pos()
                self.grammar_data = self.db.get_grammar()
                self.presents = self.db.get_presets()

                self.font = self.load_font()
                if self.font_file:
                    self.font_family_name = process_font(self.font_file)

                self.update_word_display()
                self.update_tag_filter_listbox()
                self.update_grammar_table_listbox()
                self.load_grammar_rules()
                self.refresh_stats_page()

                self.main_notebook.setCurrentIndex(0)
                self.setWindowTitle(project_name)
                QMessageBox.information(self, "Success", f"Project '{project_name}' imported successfully!")

            except Exception as e:
                error_dialog = QErrorMessage(self)
                error_dialog.showMessage(f"Error importing project: {e}")

    def set_dark_mode(self):
        QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)

        with open(self.light_dark_mode, "w") as f:
            f.write("d")

    def set_light_mode(self):
        QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Light)

        with open(self.light_dark_mode, "w") as f:
            f.write("l")

    def add_font_script(self):
        flag = False

        if self.font_exists:
            response = WarningDialog(
                "A font already exists for this project. Adding a new font will remove this one. Proceed?",
                self
            )
            if response.exec():
                flag = True
        else:
            flag = True

        if flag:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Add Custom Font", "", "Font Files (*.ttf *.otf)"
            )

            if file_name:
                try:
                    if Path(file_name).suffix == ".ttf":
                        shutil.copy(file_name, os.path.join(self.app_data_dir, "font.ttf"))
                    elif Path(file_name).suffix == ".otf":
                        shutil.copy(file_name, os.path.join(self.app_data_dir, "font.otf"))
                    else:
                        QMessageBox.warning(self, "Error", "Font file extension not supported.")
                        return
                except Exception as e:
                    QMessageBox.warning(self, "Error Loading Font", f"Could not load font file: {e}")
                    return

                result = get_font(file_name)

                if type(result) == str:
                    QMessageBox.warning(self, "Error", result)
                    self.font = None
                else:
                    self.font = result

    def make_feature_request(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Feature Request")
        msg.setText("Make a feature request at <a href='https://forms.gle/y6wGKhbLVQ2SP1Bo6'>this google form</a>.")

        msg.exec_()

    # --- Tables ---

    def update_grammar_table_listbox(self):
        self.table_listbox.clear()
        for table_name in sorted(self.grammar_data['tables'].keys()):
            self.table_listbox.addItem(table_name)

    def load_table_into_editor(self):
        selected_items = self.table_listbox.selectedItems()

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

        existing_tables = [self.table_listbox.item(i).text() for i in range(self.table_listbox.count())]
        if table_name in existing_tables:
            QMessageBox.warning(self, "Duplicate", f"A table named '{table_name}' already exists.")
            return

        num_rows, ok_r = QInputDialog.getInt(self, "Create Table", "Enter number of rows:", 3, 1, 100)
        if not ok_r:
            return

        num_cols, ok_c = QInputDialog.getInt(self, "Create Table", "Enter number of columns:", 3, 1, 100)
        if not ok_c:
            return

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

        items = self.table_listbox.findItems(table_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.table_listbox.setCurrentItem(items[0])

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

        if reply == QMessageBox.StandardButton.Yes:
            del self.grammar_data['tables'][table_name]
            self.save_grammar()
            self.update_grammar_table_listbox()
            self.table_editor.clear()
            self.table_editor.setRowCount(0)
            self.table_editor.setColumnCount(0)

    def add_table_row(self):
        current_row = self.table_editor.currentRow()
        if current_row == -1:
            current_row = self.table_editor.rowCount()

        self.table_editor.insertRow(current_row)

        new_header = QTableWidgetItem(str(current_row + 1))
        self.table_editor.setVerticalHeaderItem(current_row, new_header)

        for r in range(current_row + 1, self.table_editor.rowCount()):
            self.table_editor.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))

    def remove_table_row(self):
        current_row = self.table_editor.currentRow()
        if current_row != -1:
            self.table_editor.removeRow(current_row)

            for r in range(current_row, self.table_editor.rowCount()):
                self.table_editor.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))

    def add_table_column(self):
        current_col = self.table_editor.currentColumn()
        if current_col == -1:
            current_col = self.table_editor.columnCount()

        self.table_editor.insertColumn(current_col)

        new_header = QTableWidgetItem(f"Header {current_col + 1}")
        self.table_editor.setHorizontalHeaderItem(current_col, new_header)

        for c in range(current_col + 1, self.table_editor.columnCount()):
            self.table_editor.setHorizontalHeaderItem(c, QTableWidgetItem(f"Header {c + 1}"))

    def remove_table_column(self):
        current_col = self.table_editor.currentColumn()
        if current_col != -1:
            self.table_editor.removeColumn(current_col)

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
        event.accept()

    def empty(self, value=None):
        pass # Used to give to buttons before I have a function for them to execute so my code editor stops screaming at me

    def debug(self):
        dialog = DebugDialog(self)
        dialog.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
