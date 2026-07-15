import sys
import os
import csv
import shutil
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMessageBox, QFileDialog, QErrorMessage
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QGuiApplication, QShortcut, QKeySequence

from src.dialogs import OpenProjectDialog, RenameProjectDialog, ImportantWarningDialog, WarningDialog, DebugDialog
from src.functions import zip_folder, unzip_file, get_folder_names, clear_folder, get_font, process_font
from src.db_manager import DatabaseManager

from src.tabs.dictionary_tab import DictionaryTab
from src.tabs.grammar_tab import GrammarTab
from src.tabs.stats_tab import StatsTab
from src.tabs.word_gen_tab import WordGenTab
from src.tabs.ipa_tab import IPATab
from src.tabs.help_tab import HelpTab
from src.tabs.alphabet_tab import AlphabetTab


class ConlangDictionaryApp(QMainWindow):
    """
    A GUI application for creating, managing, and searching a dictionary for a
    constructed language, written in PySide6.
    """

    #region init
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

        self.db_path = self.app_data_dir / "project.db"
        self.db = DatabaseManager(self.db_path)
        self.db.migrate_from_json(self.app_data_dir)

        self.custom_font_on = False

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
        self.tab_dictionary.update_word_display()
        self.tab_dictionary.update_tag_filter_listbox()
        self.tab_grammar.update_grammar_table_listbox()
        self.tab_grammar.load_grammar_rules()

        self.shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.shortcut.activated.connect(self.debug)

    def _setup_directories(self):
        try:
            if sys.platform == "win32":
                app_data_path = Path(os.getenv('LOCALAPPDATA', ''))
            elif sys.platform == "darwin":
                app_data_path = Path.home() / 'Library' / 'Application Support'
            else:
                app_data_path = Path.home() / '.local' / 'share'

            self.app_data_dir = app_data_path / "ConlangDictionary"
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
    #endregion

    #region Data Load/Save Methods

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
                self.custom_font_on = True
                return result
        else:
            return None
    #endregion

    #region UI Creation Methods

    def create_widgets(self):
        self.main_notebook = QTabWidget()
        self.setCentralWidget(self.main_notebook)

        self.create_menu_bar()

        self.tab_dictionary = DictionaryTab(self)
        self.tab_word_generator = WordGenTab(self)
        self.tab_grammar = GrammarTab(self)
        self.tab_ipa = IPATab(self)
        self.tab_stats = StatsTab(self)
        self.tab_help = HelpTab(self)
        self.tab_alphabet = AlphabetTab(self)

        self.main_notebook.addTab(self.tab_dictionary, 'Dictionary')
        self.main_notebook.addTab(self.tab_word_generator, 'Word Generator')
        self.main_notebook.addTab(self.tab_grammar, 'Grammar Appendix')
        self.main_notebook.addTab(self.tab_alphabet, 'Custom Alphabet')
        self.main_notebook.addTab(self.tab_ipa, 'IPA Chart')
        self.main_notebook.addTab(self.tab_stats, 'Statistics')
        self.main_notebook.addTab(self.tab_help, 'How To Use / Help')

    def create_menu_bar(self):
        self.menu_bar = self.menuBar()

        fileMenu = self.menu_bar.addMenu("&File")
        settingsMenu = self.menu_bar.addMenu("Settings")
        projectMenu = self.menu_bar.addMenu("Project")
        supportMenu = self.menu_bar.addMenu("Support && Feedback")

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
        supportMenu.addAction(feature_request)

        bug_report = QAction("Report a Bug", self)
        bug_report.triggered.connect(self.make_bug_report)
        supportMenu.addAction(bug_report)

        ko_fi = QAction("Support Project on Ko-Fi", self)
        ko_fi.triggered.connect(self.donate_kofi)
        supportMenu.addAction(ko_fi)
    #endregion

    #region Menu Bar

    def open_make_new_project(self):
        dialog = OpenProjectDialog(self, flag=True)
        if dialog.exec():
            self.db_path = os.path.join(self.app_data_dir, "project.db")
            self.db = DatabaseManager(self.db_path)
            self.db.migrate_from_json(self.app_data_dir)

            self.dictionary = self.load_dictionary()
            self.all_tags, self.word_classes = self.load_tags()
            self.grammar_data = self.load_grammar()
            self.presents = self.load_presents()
            self.font = self.load_font()

            self.tab_dictionary.update_word_display()
            self.tab_dictionary.update_tag_filter_listbox()
            self.tab_grammar.update_grammar_table_listbox()
            self.tab_grammar.load_grammar_rules()

            self.tab_stats.refresh_stats_page()
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

            self.tab_dictionary.update_word_display()
            self.tab_dictionary.update_tag_filter_listbox()
            self.tab_grammar.update_grammar_table_listbox()
            self.tab_grammar.load_grammar_rules()

            self.tab_stats.refresh_stats_page()
            self.main_notebook.setCurrentIndex(0)

    def save_csv_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")

        if file_name:
            with open(f"{file_name}", "w", newline='') as f:
                headers = [
                    'conlang', 'english', 'syllabication', 'ipa', 'pos', 'description', 'tags', 'roots', 'derived',
                    'synonyms', 'antonyms'
                ]

                writer = csv.DictWriter(f, fieldnames=headers)

                writer.writeheader()

                for entry in self.dictionary:
                    print(entry)
                    row_data = {
                        'conlang': entry.get('conlang', ''),
                        'english': '|'.join(entry.get('english', [])),
                        'syllabication': '|'.join(entry.get('syllable', '')),
                        'ipa': '|'.join(entry.get('ipa', '')),
                        'pos': entry.get('pos', ''),
                        'description': entry.get('description', ''),
                        'tags': '|'.join(entry.get('tags', [])),
                        'roots': '|'.join(self.tab_dictionary.get_entry_by_id(root_id)['conlang'] for root_id in
                                          entry.get('roots', [])),
                        'derived': '|'.join(self.tab_dictionary.get_entry_by_id(root_id)['conlang'] for root_id in
                                            entry.get('derived', [])),
                        'synonyms': '|'.join(self.tab_dictionary.get_entry_by_id(root_id)['conlang'] for root_id in
                                             entry.get('synonyms', [])),
                        'antonyms': '|'.join(self.tab_dictionary.get_entry_by_id(root_id)['conlang'] for root_id in
                                             entry.get('antonyms', [])),
                    }

                    writer.writerow(row_data)

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

                self.tab_dictionary.update_word_display()
                self.tab_dictionary.update_tag_filter_listbox()
                self.tab_grammar.update_grammar_table_listbox()
                self.tab_grammar.load_grammar_rules()
                self.tab_stats.refresh_stats_page()

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

    def make_bug_report(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Feature Request")
        msg.setText("Make a bug report at <a href='https://forms.gle/sepe4PwjWyoKszB66'>this google form</a>.")

        msg.exec_()

    def donate_kofi(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Donation")
        msg.setText("Make a donation at at the website below or click <a href='https://ko-fi.com/mastercheese129'>here</a>.\nhttps://ko-fi.com/mastercheese129")

        msg.exec_()
    #endregion

    #region Random/Utility

    def update_tags(self, tags_list):
        new_tag_found = False
        for tag in tags_list:
            if tag not in self.all_tags:
                self.all_tags.append(tag)
                new_tag_found = True
        if new_tag_found:
            self.save_tags()
            self.tab_dictionary.update_tag_filter_listbox()

    def closeEvent(self, event):
        event.accept()

    def empty(self, value=None):
        pass # Used to give to buttons before I have a function for them to execute so my code editor stops screaming at me

    def debug(self):
        dialog = DebugDialog(self)
        dialog.show()
    #endregion

    #region Cross-Tab Signals
    def toggle_font(self, origin):
        if origin == "dict":
            self.tab_alphabet.toggle_font(True)
        elif origin == "alpha":
            self.tab_dictionary.toggle_font(True)

    #endregion


if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
