from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit


class HelpTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        layout = QVBoxLayout(self)
        help_text_widget = QTextEdit()
        help_text_widget.setReadOnly(True)
        layout.addWidget(help_text_widget)

        help_text_widget.setText(help_text)


help_text = """Welcome to the Conlang Dictionary Builder!

This application helps you create, manage, and explore your constructed language. Here's a quick guide to its features.

== Menu Bar ==

* File:
    - Open/New Project: Open or create a new conlang project.
    - Rename Project: Renames the current conlang project.
    - Delete Project: Deletes the current conlang project.
    - Export as CSV: Exports just the dictionary as a CSV file.
    - Export as ZIP: Exports all the project's save files in a .zip to move projects to other computers.
    - Import as ZIP: Opens an exported .zip file and makes a new project, automatically populating it with the data contained in the .zip file.

* Settings:
    - Dark Mode: Sets the program to dark mode and saves this setting.
    - Light Mode: Sets the program to light mode and saves this setting.

* Project:
    - Import Font: Imports a custom .ttf or .otf font file to display your conlang words in the application.

* Feature Request:
    - Request a Feature: Link to a Google Form where you can request a new feature.

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
    - Add Word: Adds a new word. "Conlang Word", "English Translation", and "Part of Speech" are required.
    - Manage Parts of Speech: Add or remove parts of speech to fit the needs of your conlang.
    - Toggle Custom Font: Turns your imported custom font on or off for the word list and details.

* Description Tab: Shows the definition, syllabication, and IPA pronunciation for the selected word.

* Etymology Tab: Tracks word origins.
    - Root Words (comes from): Words that this word comes from.
    - Derived Words (leads to): Words that come from this word.
    - Double-click a word in the lists to jump to it in the main dictionary.

* Lexical Relations Tab: Tracks related words.
    - Synonyms: Words with similar meanings.
    - Antonyms: Words with opposite meanings.
    - Double-click a word in the lists to jump to it in the main dictionary.

== Word Generator Tab ==

* Generate Random Words:
    - This generator is based on a site called Kozuka (creator: https://github.com/auctumnus). It follows the same rules and they already made a very good page explaining them so view rules here: https://kozuka.kmwc.org/help.html
    - Using Output: Double-click on one of the generated words to automatically open the Add Word window with it autofilled.
    - Save/Load Pattern: Save your generator configurations (main pattern and rules) as presets to easily reuse them later.

== Grammar Appendix Tab ==

This tab is for your language's documentation.

* Grammar Rules: A single text box for your general notes.
    - IMPORTANT: You must click the "Save Rules" button to save your changes.

* Grammar Tables: A place to store multiple, separate tables.
    - Create Table: Prompts you for a name and size and creates a new, blank table.
    - Delete Table: Deletes the selected table.
    - Add/Remove Row/Column: Use the editor buttons to resize the table. Double-click headers to edit them.
    - IMPORTANT: You must click "Save Current Table" to save your changes to the selected table.

== IPA Chart Tab ==

* Interactive Tables: Displays Consonant, Non-Pulmonic Consonant, Vowel, and Other charts.
    - Click any IPA symbol to automatically copy it to your clipboard.
    - Click the play button next to a symbol to play its audio.

== Saving Your Data ==

* Database Storage: Your dictionary, tags, grammar rules, tables, and word generator presets are automatically managed and saved to a local SQLite database file named "project.db" within your project's folder. (Note: Old JSON projects are automatically migrated to this database upon opening if updating from an older version).
* Dictionary & Tags: Changes to your dictionary entries and tags are saved to the database immediately.
* Grammar: Grammar rules and tables are saved to the database ONLY when you click the "Save Rules" or "Save Current Table" buttons."""
