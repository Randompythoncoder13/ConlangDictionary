# Conlang Dictionary App
A desktop application built with Python and PyQt6 designed to help you create, manage, and explore a dictionary and grammar for your constructed language (conlang).

### Features
This application provides a comprehensive suite of tools for conlang development, organized into several main tabs:

Project Management (File Menu)
+ Multi-Project Support: Create and switch between multiple conlang projects. Each project is stored in its own folder.
+ Project Operations: Easily rename or delete the current project.
+ Import/Export: Back up your entire project (dictionary, grammar, tags) to a .zip file, or import a project from a .zip file.
+ CSV Export: Export your dictionary list to a .csv file for use in other applications.

1. Dictionary Tab
+ Word Management: Add, edit, and delete words with detailed information.
+ Rich Word Entries: Each entry includes:
  + The conlang word
  + One or more English translations (separated by commas)
  + Part of Speech (customizable)
  + Tags (customizable)
  + A rich text description/notes field
+ Etymology Tracking: Link words together by defining "Root" (words this word comes from) and "Derived" (words that come from this word) relationships. You can double-click a linked word to jump to it.
+ Powerful Search: Search for words in either your conlang or in English.
+ Filtering: Filter the dictionary view by Part of Speech, tags, or both.
+ Customization: Manage your project's specific lists for Parts of Speech and tags.

2. Word Generator Tab
+ Kozuka-Based: Uses logic inspired by the [Kozuka](https://kozuka.kmwc.org/) word generator.
+ Pattern Definition: Define custom letter/sound patterns (e.g., C=b,p,t,d, V=a,e,i) and a main pattern (e.g., CVCV) to generate words.
+ Save/Load Presets: Save your generator patterns as a named preset and reload them later.
+ Quick Add: Double-click any word in the generated list to open the "Add Word" dialog with it pre-filled.

3. Grammar Appendix Tab
+ Grammar Rules: A dedicated rich text editor for your main grammar documentation (e.g., phonology, syntax, morphology). Requires manual save.
+ Grammar Tables: Create and manage multiple tables for things like noun declensions, verb conjugations, or affix lists. The table editor supports adding/removing rows and columns and editing headers. Requires manual save.

4. Statistics Tab
+ At-a-Glance Info: Get a quick overview of your dictionary, including:
  + Total word count
  + Number of root words (no etymological parents)
  + Number of terminal words (no etymological children)
  + Word counts by Part of Speech
  + Word counts by tag

5. How To Use / Help Tab
+ Built-in Guide: A comprehensive help tab that explains all the application's features.

Settings Menu
+ Theme: Toggle between Light and Dark mode.

### How to Run

Prerequisites
+ [Python 3](https://www.python.org/)
+ [PyQt6](https://pypi.org/project/PyQt6/): The GUI framework used by the application.

You can install PyQt6 using pip:
`pip install PyQt6`

Running the Application
1. Download: Download the app.py script and the accompanying src directory.

2. Directory Structure: Ensure your files are arranged like this:
`/Your-Project-Folder
    |-- app.py
    |-- /src
        |-- dialogs.py
        |-- wizards.py
        |-- simulated_kozuka_logic.py
        |-- functions.py
        |-- custom_widgets.py`

Execute: Run the app.py script from your terminal:
`python app.py`

Data Storage
Your conlang projects are stored locally on your computer in your user's application data directory.
Windows: `C:\Users\<YourUser>\AppData\Local\ConlangDictionary`
Linux: `~/.local/share/ConlangDictionary`
Each project you create will be a subfolder in this location, containing its own set of JSON files for the dictionary, grammar, generator presets, and tags.
