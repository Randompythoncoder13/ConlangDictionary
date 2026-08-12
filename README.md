# Conlang Dictionary App
A desktop application built with Python and PySide6 designed to help you create, manage, and explore a dictionary and grammar for your constructed language (conlang).

### Features
This application provides a comprehensive suite of tools for conlang development, organized into several main tabs:

1. Dictionary Tab
   + Word Management: Add, edit, and delete words with detailed information.
   + Rich Word Entries: Each entry includes:
     + The conlang word
     + One or more English translations (separated by commas)
     + Syllabication
     + IPA Pronunciation
     + Part of Speech (customizable)
     + A description/definition field
     + Tags (customizable)
   + Etymology Tracking: Link words together by defining "Root" (words this word comes from) and "Derived" (words that come from this word) relationships. You can double-click a linked word to jump to it.
   + Lexical Relations: Link words to their Synonyms and Antonyms for quick reference.
   + Powerful Search & Filtering: Search for words in either your conlang or in English, and filter the dictionary view by Part of Speech, tags, or both.
   + Customization: Manage your project's specific lists for Parts of Speech and tags, and toggle your custom imported fonts on or off.


2. Word Generator Tab
   + Kozuka-Based: Uses logic inspired by the [Kozuka](https://kozuka.kmwc.org/) word generator to create words based on custom letter/sound patterns.
   + Save/Load Presets: Save your generator patterns as a named preset and reload them later.
   + Quick Add: Double-click any word in the generated list to open the "Add Word" dialog with it pre-filled.


3. Grammar Appendix Tab
   + Grammar Rules: A dedicated rich text editor for your main grammar documentation (e.g., phonology, syntax, morphology). Requires manual save.
   + Grammar Tables: Create and manage multiple tables for things like noun declensions, verb conjugations, or affix lists. The table editor supports adding/removing rows and columns and editing headers. Requires manual save.


4. Custom Alphabet Tab
   + Define Letters: Input single characters for your alphabet and assign default IPA pronunciations.
   + Custom Sorting Order: Arrange letter blocks left-to-right to directly control how words are sorted alphabetically in the Dictionary Tab.
   + Populating IPA: Automatically generate pronunciations for dictionary words with blank IPA fields based on your defined letter-to-IPA mapping (this safely preserves any manually entered pronunciations).
   + Display Options: Toggle your imported custom conlang font to display your alphabet blocks.


5. IPA Chart Tab
   + Interactive IPA Tables: View comprehensively mapped charts for Pulmonic Consonants, Non-Pulmonic Consonants, Vowels, and Other symbols.
   + Audio Playback: Click the speaker icon next to compatible IPA characters to hear their pronunciation.
   + Copy to Clipboard: Click on any IPA cell to instantly copy the character to your clipboard.


6. Statistics Tab
   + At-a-Glance Info: Get a quick overview of your dictionary, including:
     + Total word count
     + Number of root words (no etymological parents)
     + Number of terminal words (no etymological children)
     + Word counts by Part of Speech
     + Word counts by tag


7. How To Use / Help Tab
   + Built-in Guide: A comprehensive help tab that explains all the application's features.


File Menu
  + Multi-Project Support: Create and switch between multiple conlang projects. Each project is stored in its own folder.
  + Project Operations: Easily rename or delete the current project.
  + Import/Export: Back up your entire project (dictionary, grammar, tags) to a .zip file, or import a project from a .zip file.
  + CSV Export: Export your dictionary list to a .csv file for use in other applications.

Project
  + Custom Fonts: Import .ttf or .otf font files to render your custom conlang script dynamically throughout the application.

Support & Feedback Menu
  + Request a Feature: Link to a [Google Form](https://forms.gle/Tbcp4ZTEdrRSxUwF9) where you can request a new feature.
  + Report a Bug: Link to a [Google Form](https://forms.gle/VxbFc5RZt55Q69a36) where you can report a bug.
  + Support Project on Ko-Fi: [Link](https://ko-fi.com/mastercheese129) to give a small donation to the project.

### How to Run

Prerequisites
+ [Python 3](https://www.python.org/)
+ [PySide6](https://github.com/pyside/pyside-setup): The GUI framework used by the application.
+ [Pyperclip](https://pypi.org/project/pyperclip/): Allows copying to the clipboard.
+ [Playsound3](https://pypi.org/project/playsound3/): Allows for playing sound files.

You can install dependencies using pip:
`pip install PySide6 pyperclip playsound3`

Running the Application
1. Download: Download the main.py script and the accompanying src directory.

2. Directory Structure: Ensure your files are arranged like this:
```
/Your-Project-Folder
|-- main.py
|-- /src
|   |-- app.py
|   |-- custom_widgets.py
|   |-- db_manager.py
|   |-- dialogs.py
|   |-- functions.py
|   |-- IPA_tables.py
|   |-- simulated_kozuka_logic.py
|   |-- wizards.py
|   |-- /tabs
|       |-- alphabet_tab.py
|       |-- dictionary_tab.py
|       |-- grammar_tab.py
|       |-- help_tab.py
|       |-- ipa_tab.py
|       |-- stats_tab.py
|       |-- word_gen_tab.py
|
|-- /assets
    |-- logo.png
    |-- /font
    |   |-- Charis-Regular.ttf
    |
    |-- /ipa_sounds
        |-- !.mp3
        |-- a.mp3
        |-- b.mp3
        |-- ...
```

Execute: Run the main.py script from your terminal:
`python main.py`

### Data Storage
Your conlang projects are stored locally on your computer in your user's application data directory.
+ Windows: `C:\Users\<YourUser>\AppData\Local\ConlangDictionary`
+ MacOs: `/Users/<YourUse>/Application Support/ConlangDictionary`
+ Linux: `/home/<YourUser>/.local/share/ConlangDictionary`

Each project you create will be a subfolder in this location. The app uses a localized SQLite database (project.db) to efficiently store your dictionary, grammar tables, tags, and presets. Note: Older JSON-based projects are automatically backed up and migrated to this new database format upon opening. Your custom fonts and theme preferences are also saved directly in your project's directory.