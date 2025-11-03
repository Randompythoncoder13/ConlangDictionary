import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os

# Current Code on Microsoft Store

class ConlangDictionaryApp:
    # A GUI application for creating, managing, and searching a dictionary for a constructed language.

    def __init__(self, root):
        self.root = root
        self.root.tk.call('tk', 'scaling', 1.25)
        self.root.title("Conlang Dictionary Builder")
        self.root.geometry("1000x750")

        self.word_classes = [
            "Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Preposition", "Conjunction", "Interjection", "Prefix",
            "Suffix", "Other"
        ]

        self.style = ttk.Style()
        self.style.theme_use('clam')

        app_data_path = os.getenv('LOCALAPPDATA')

        self.app_data_dir = os.path.join(app_data_path, "ConlangDictionary")

        try:
            os.makedirs(self.app_data_dir, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Fatal Error", f"Could not create data directory: {e}")
            self.root.destroy()

        self.dictionary_file = os.path.join(self.app_data_dir, "conlang_dictionary.json")
        self.tags_file = os.path.join(self.app_data_dir, "conlang_tags.json")
        self.grammar_file = os.path.join(self.app_data_dir, "conlang_grammar.json")

        self.dictionary = self.load_dictionary()
        self.all_tags = self.load_tags()
        self.grammar_data = self.load_grammar()

        self.create_widgets()

        self.update_word_display()
        self.update_tag_filter_listbox()
        self.update_grammar_table_listbox()
        self.load_grammar_rules()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_dictionary(self):
        # Loads the dictionary from a JSON file and ensures backward compatibility.
        if not os.path.exists(self.dictionary_file):
            return []
        try:
            with open(self.dictionary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data:
                    entry.setdefault('pos', 'Other')
                    entry.setdefault('description', '')
                    entry.setdefault('tags', [])
                    entry.setdefault('roots', [])
                    entry.setdefault('derived', [])
                return data
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Error Loading Dictionary", f"Could not read dictionary file: {e}")
            return []

    def save_dictionary(self):
        # Saves the current dictionary to the JSON file.
        try:
            with open(self.dictionary_file, 'w', encoding='utf-8') as f:
                json.dump(self.dictionary, f, ensure_ascii=False, indent=4)
        except IOError as e:
            messagebox.showerror("Error Saving Dictionary", f"Could not save to dictionary file: {e}")

    def load_tags(self):
        # Loads the list of all tags from its JSON file.
        if not os.path.exists(self.tags_file):
            return []
        try:
            with open(self.tags_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Error Loading Tags", f"Could not read tags file: {e}")
            return []

    def save_tags(self):
        # Saves the list of all tags to its JSON file.
        try:
            self.all_tags.sort()
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_tags, f, ensure_ascii=False, indent=4)
        except IOError as e:
            messagebox.showerror("Error Saving Tags", f"Could not save to tags file: {e}")

    def load_grammar(self):
        # Loads grammar rules and tables from its JSON file.
        if not os.path.exists(self.grammar_file):
            return {"rules": "", "tables": {}}
        try:
            with open(self.grammar_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data.setdefault('rules', '')
                data.setdefault('tables', {})
                return data
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Error Loading Grammar", f"Could not read grammar file: {e}")
            return {"rules": "", "tables": {}}

    def save_grammar(self):
        # Saves the grammar rules and tables to its JSON file.
        try:
            with open(self.grammar_file, 'w', encoding='utf-8') as f:
                json.dump(self.grammar_data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            messagebox.showerror("Error Saving Grammar", f"Could not save to grammar file: {e}")

    def create_widgets(self):
        # Creates and lays out all the GUI widgets.
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tab_dictionary = ttk.Frame(self.main_notebook, padding=10)
        self.tab_grammar = ttk.Frame(self.main_notebook, padding=10)
        self.tab_stats = ttk.Frame(self.main_notebook, padding=10)
        self.tab_help = ttk.Frame(self.main_notebook, padding=10)

        self.main_notebook.add(self.tab_dictionary, text='Dictionary')
        self.main_notebook.add(self.tab_grammar, text='Grammar Appendix')
        self.main_notebook.add(self.tab_stats, text='Statistics')
        self.main_notebook.add(self.tab_help, text='How To Use / Help')

        self.create_dictionary_tab(self.tab_dictionary)
        self.create_grammar_tab(self.tab_grammar)
        self.create_statistics_tab(self.tab_stats)
        self.create_help_tab(self.tab_help)

    def create_dictionary_tab(self, parent_tab):
        # Create all widgets for the Dictionary tab.
        main_frame = ttk.Frame(parent_tab)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Panel
        left_panel = ttk.Frame(main_frame, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor=tk.N)
        left_panel.pack_propagate(False)

        # Add Word Secion
        add_frame = ttk.LabelFrame(left_panel, text="Add Word", padding="10")
        add_frame.pack(fill=tk.X, expand=False)

        ttk.Label(add_frame, text="Conlang Word:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.conlang_entry = ttk.Entry(add_frame, width=30)
        self.conlang_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(add_frame, text="English Translation:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.english_entry = ttk.Entry(add_frame, width=30)
        self.english_entry.grid(row=1, column=1, sticky=tk.EW, pady=2)

        ttk.Label(add_frame, text="Part of Speech:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pos_combobox = ttk.Combobox(add_frame, values=self.word_classes, width=27, state='readonly')
        self.pos_combobox.grid(row=2, column=1, sticky=tk.EW, pady=2)

        ttk.Label(add_frame, text="Description:").grid(row=3, column=0, sticky=tk.NW, pady=2)
        self.description_text = tk.Text(add_frame, width=30, height=4, wrap=tk.WORD)
        self.description_text.grid(row=3, column=1, sticky=tk.EW, pady=2)

        ttk.Label(add_frame, text="Tags (comma-sep):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.tags_entry = ttk.Entry(add_frame, width=30)
        self.tags_entry.grid(row=4, column=1, sticky=tk.EW, pady=2)

        add_button = ttk.Button(add_frame, text="Add Word", command=self.add_word)
        add_button.grid(row=5, column=0, columnspan=2, pady=10)

        add_frame.columnconfigure(1, weight=1)

        # Search and Filter Section
        search_frame = ttk.LabelFrame(left_panel, text="Search & Filter", padding="10")
        search_frame.pack(fill=tk.X, expand=False, pady=10)

        ttk.Label(search_frame, text="Search Term:").pack(anchor=tk.W)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(fill=tk.X, pady=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.update_word_display)

        self.search_var = tk.StringVar(value="conlang")
        ttk.Radiobutton(
            search_frame, text="In Conlang", variable=self.search_var, value="conlang", command=self.update_word_display
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            search_frame, text="In English", variable=self.search_var, value="english", command=self.update_word_display
        ).pack(anchor=tk.W)

        ttk.Label(search_frame, text="Filter by Class:").pack(anchor=tk.W, pady=(10, 0))
        self.filter_pos_combobox = ttk.Combobox(
            search_frame, values=["All Classes"] + self.word_classes, state='readonly'
        )
        self.filter_pos_combobox.set("All Classes")
        self.filter_pos_combobox.bind("<<ComboboxSelected>>", self.update_word_display)
        self.filter_pos_combobox.pack(fill=tk.X)

        ttk.Label(search_frame, text="Filter by Tags:").pack(anchor=tk.W, pady=(10, 0))
        tag_filter_frame = ttk.Frame(search_frame)
        tag_filter_frame.pack(fill=tk.X, expand=True)

        tag_scrollbar = ttk.Scrollbar(tag_filter_frame, orient=tk.VERTICAL)
        self.tag_filter_listbox = tk.Listbox(
            tag_filter_frame, selectmode=tk.MULTIPLE, height=5, yscrollcommand=tag_scrollbar.set, exportselection=False
        )
        tag_scrollbar.config(command=self.tag_filter_listbox.yview)
        tag_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tag_filter_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tag_filter_listbox.bind("<<ListboxSelect>>", self.update_word_display)

        manage_tags_button = ttk.Button(search_frame, text="Manage Tags", command=self.manage_tags)
        manage_tags_button.pack(pady=(5, 0), fill=tk.X)

        clear_button = ttk.Button(search_frame, text="Clear Filters / Show All", command=self.clear_filters)
        clear_button.pack(pady=10, fill=tk.X)

        # Right Panel
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        dict_frame = ttk.LabelFrame(right_panel, text="Dictionary", padding="10")
        dict_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("Conlang Word", "English Translation", "Part of Speech", "Tags")
        self.tree = ttk.Treeview(dict_frame, columns=cols, show='headings', selectmode='browse')

        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("Conlang Word", width=150)
        self.tree.column("English Translation", width=150)
        self.tree.column("Part of Speech", width=100)
        self.tree.column("Tags", width=150)

        scrollbar = ttk.Scrollbar(dict_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # Edit/Delete Buttons
        button_frame = ttk.Frame(right_panel)
        button_frame.pack(fill=tk.X, pady=5)
        delete_button = ttk.Button(button_frame, text="Delete Selected", command=self.delete_word)
        delete_button.pack(side=tk.LEFT, padx=5)
        edit_button = ttk.Button(button_frame, text="Edit Selected", command=self.edit_word)
        edit_button.pack(side=tk.LEFT, padx=5)

        # Details Notebook
        self.details_notebook = ttk.Notebook(right_panel)
        self.details_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Description Tab
        desc_tab = ttk.Frame(self.details_notebook, padding=10)
        self.display_description_text = tk.Text(
            desc_tab, height=6, wrap=tk.WORD, state=tk.DISABLED, background=self.root.cget('bg'), relief=tk.FLAT
        )
        self.display_description_text.pack(fill=tk.BOTH, expand=True)

        # Etymology Tab
        etym_tab = ttk.Frame(self.details_notebook, padding=5)
        etym_tab.columnconfigure(0, weight=1)
        etym_tab.columnconfigure(1, weight=1)
        etym_tab.rowconfigure(1, weight=1)

        # Roots
        roots_frame = ttk.LabelFrame(etym_tab, text="Root Words (comes from)")
        roots_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=5, pady=5)
        roots_frame.rowconfigure(0, weight=1)
        roots_frame.columnconfigure(0, weight=1)

        self.roots_listbox = tk.Listbox(roots_frame, exportselection=False)
        self.roots_listbox.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.roots_listbox.bind("<Double-1>", self.jump_to_word_from_listbox)

        add_root_btn = ttk.Button(roots_frame, text="Add Root", command=lambda: self.add_etymology_link('root'))
        add_root_btn.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        del_root_btn = ttk.Button(roots_frame, text="Remove Root", command=lambda: self.remove_etymology_link('root'))
        del_root_btn.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Derived
        derived_frame = ttk.LabelFrame(etym_tab, text="Derived Words (leads to)")
        derived_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
        derived_frame.rowconfigure(0, weight=1)
        derived_frame.columnconfigure(0, weight=1)

        self.derived_listbox = tk.Listbox(derived_frame, exportselection=False)
        self.derived_listbox.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.derived_listbox.bind("<Double-1>", self.jump_to_word_from_listbox)

        add_derived_btn = ttk.Button(derived_frame, text="Add Derived",
                                     command=lambda: self.add_etymology_link('derived'))
        add_derived_btn.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        del_derived_btn = ttk.Button(derived_frame, text="Remove Derived",
                                     command=lambda: self.remove_etymology_link('derived'))
        del_derived_btn.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        self.details_notebook.add(desc_tab, text='Description')
        self.details_notebook.add(etym_tab, text='Etymology')

    def create_grammar_tab(self, parent_tab):
        # Create all widgets for the Grammar Appendix tab.
        main_pane = ttk.PanedWindow(parent_tab, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Rules Pane
        rules_frame = ttk.LabelFrame(main_pane, text="Grammar Rules", padding="10")
        main_pane.add(rules_frame, weight=0)

        rules_text_frame = ttk.Frame(rules_frame)
        rules_text_frame.pack(fill=tk.X, expand=False)

        rules_scrollbar = ttk.Scrollbar(rules_text_frame, orient=tk.VERTICAL)
        self.grammar_rules_text = tk.Text(rules_text_frame, wrap=tk.WORD, yscrollcommand=rules_scrollbar.set, height=15)
        rules_scrollbar.config(command=self.grammar_rules_text.yview)
        rules_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.grammar_rules_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        save_rules_btn = ttk.Button(rules_frame, text="Save Rules", command=self.save_grammar_rules)
        save_rules_btn.pack(pady=5)

        # Tables Pane
        tables_frame = ttk.LabelFrame(main_pane, text="Grammar Tables", padding="10")
        main_pane.add(tables_frame, weight=1)

        tables_frame.columnconfigure(1, weight=1)
        tables_frame.rowconfigure(0, weight=1)

        # Table List and Controls
        table_controls_frame = ttk.Frame(tables_frame)
        table_controls_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 10))

        ttk.Label(table_controls_frame, text="Tables:").pack(anchor=tk.W)
        self.table_listbox = tk.Listbox(table_controls_frame, height=10, exportselection=False)
        self.table_listbox.pack(expand=True) # fill=tk.Y
        self.table_listbox.bind("<<ListboxSelect>>", self.load_table_into_editor)

        create_table_btn = ttk.Button(table_controls_frame, text="Create Table", command=self.create_grammar_table)
        create_table_btn.pack(fill=tk.X, pady=(5, 0))
        delete_table_btn = ttk.Button(table_controls_frame, text="Delete Table", command=self.delete_grammar_table)
        delete_table_btn.pack(fill=tk.X, pady=5)

        # Table Editor
        table_editor_frame = ttk.Frame(tables_frame)
        table_editor_frame.grid(row=0, column=1, sticky="nsew")
        table_editor_frame.rowconfigure(0, weight=1)
        table_editor_frame.columnconfigure(0, weight=1)

        table_editor_scrollbar = ttk.Scrollbar(table_editor_frame, orient=tk.VERTICAL)
        self.table_text_editor = tk.Text(table_editor_frame, wrap=tk.WORD, yscrollcommand=table_editor_scrollbar.set)
        table_editor_scrollbar.config(command=self.table_text_editor.yview)
        table_editor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.table_text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        save_table_btn = ttk.Button(tables_frame, text="Save Current Table", command=self.save_grammar_table)
        save_table_btn.grid(row=1, column=1, sticky="ew", pady=5)

    def create_statistics_tab(self, parent_tab):
        stats_frame = ttk.Frame(parent_tab)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        stats_scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL)
        self.stats_text = tk.Text(
            stats_frame, wrap=tk.WORD, yscrollcommand=stats_scrollbar.set, relief=tk.FLAT, background=self.root.cget('bg')
        )
        stats_scrollbar.config(command=self.stats_text.yview)
        stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.refresh_stats_page()

        self.stats_text.config(state=tk.DISABLED)

    def create_help_tab(self, parent_tab):
        # Create all widgets for the Help tab.
        help_frame = ttk.Frame(parent_tab)
        help_frame.pack(fill=tk.BOTH, expand=True)

        help_scrollbar = ttk.Scrollbar(help_frame, orient=tk.VERTICAL)
        help_text = tk.Text(help_frame, wrap=tk.WORD, yscrollcommand=help_scrollbar.set,
                            relief=tk.FLAT, background=self.root.cget('bg'))
        help_scrollbar.config(command=help_text.yview)
        help_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Define the help content
        help_content = """Welcome to the Conlang Dictionary Builder!

This application helps you create, manage, and explore your constructed language. Here's a quick guide to its features.

== Dictionary Tab ==

* Add Word: Use the form on the left to add a new word. "Conlang Word" and "English Translation" are required. You can add multiple English translations by separating them with a comma and a space (e.g., "set, place").

* Search & Filter:
    - Search Term: Type to search in either the Conlang or English words.
    - Filter by Class: Select a Part of Speech to see only words of that type.
    - Filter by Tags: Select one or more tags to find words that have ALL of those tags.
    - Manage Tags: Add or remove tags from the global list. This does not remove tags from words that already use them.
    - Clear Filters: Resets all search and filter fields.

* Word List: This is the main list of your words.
    - Double-click (or select and click "Edit Selected") to edit a word.
    - Single-click to select a word and view its details below.
    - Delete Selected: Permanently deletes the selected word.

* Description Tab: Shows the "Description" notes for the selected word.

* Etymology Tab: Tracks word origins.
    - Root Words: Words that THIS word comes from (e.g., "walk" is a root of "walking").
    - Derived Words: Words that come from THIS word (e.g., "walking" is derived from "walk").
    - Adding/Removing: Use the buttons to link words. This creates a two-way link (adding a root to Word A automatically adds Word A as a derivative of Word B).
    - Jump to Word: Double-click a word in the "Roots" or "Derived" list to jump to it in the main dictionary.

== Grammar Appendix Tab ==

This tab is for your language's documentation.

* Grammar Rules: A single, large text box for your general notes (phonology, syntax, etc.).
    - IMPORTANT: This text is NOT saved automatically. You must click the "Save Rules" button to save your changes.

* Grammar Tables: A place to store multiple, separate tables (e.g., verb conjugations, noun declensions).
    - Create Table: Prompts you for a name and creates a new, blank table.
    - Delete Table: Deletes the selected table.
    - Editor: Click a table name to load it into the text editor on the right.
    - IMPORTANT: Changes to a table are NOT saved automatically. You must click "Save Current Table" to save your changes to the selected table.
    - Tables do have to be built by you, the below format is suggested but use whatever you want.
    +----+----+----+
    |    |    |    |
    +----+----+----+
    |    |    |    |
    +----+----+----+

== Saving Your Data ==

* Dictionary: Your dictionary is automatically saved to conlang_dictionary.json every time you add, edit, or delete a word.
* Grammar: Your grammar rules and tables are saved to conlang_grammar.json ONLY when you click the "Save Rules" or "Save Current Table" buttons.
* Tags: Your tag list is saved to conlang_tags.json when you add or remove tags via the "Manage Tags" window.
"""

        # Add the text
        help_text.insert(tk.END, help_content)

        # Make the text widget read-only
        help_text.config(state=tk.DISABLED)

    def populate_dictionary_list(self, entries):
        # Populates the treeview with the list of dictionary entries.
        for item in self.tree.get_children():
            self.tree.delete(item)
        entries.sort(key=lambda x: x['conlang'].lower())
        for entry in entries:
            tags_str = ", ".join(entry.get('tags', []))
            english = ""
            for word in range(len(entry["english"])):
                english += entry["english"][word]
                if word < len(entry["english"]) - 1:
                    english += ", "
            self.tree.insert(
                "", tk.END, values=(entry["conlang"], english, entry["pos"], tags_str), iid=entry["conlang"]
            )

    def update_word_display(self, event=None):
        # Filters and searches the dictionary, then updates the treeview.
        filtered_list = self.dictionary[:]

        # Filter by part of speech
        filter_class = self.filter_pos_combobox.get()
        if filter_class and filter_class != "All Classes":
            filtered_list = [entry for entry in filtered_list if entry.get('pos') == filter_class]

        # Filter by selected tags
        selected_tag_indices = self.tag_filter_listbox.curselection()
        if selected_tag_indices:
            selected_tags = {self.tag_filter_listbox.get(i) for i in selected_tag_indices}
            filtered_list = [entry for entry in filtered_list if selected_tags.issubset(set(entry.get('tags', [])))]

        # Filter by search term
        search_term = self.search_entry.get().strip()
        if search_term:
            search_field = self.search_var.get()

            if search_field == "conlang":
                filtered_list = [entry for entry in filtered_list if search_term.lower() in entry[search_field].lower()]
            elif search_field == "english":
                new_filtered_list = []
                for entry in filtered_list:
                    for word in entry[search_field]:
                        if search_term.lower() in word.lower():
                            new_filtered_list.append(entry)
                            break
                filtered_list = new_filtered_list

        self.populate_dictionary_list(filtered_list)
        self.on_item_select()

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

    def add_word(self):
        # Adds a new word to the dictionary.
        conlang_word = self.conlang_entry.get().strip()
        english_word = self.english_entry.get().strip()
        pos = self.pos_combobox.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()
        tags_list = [t.strip() for t in self.tags_entry.get().strip().split(',') if t.strip()]

        if not conlang_word or not english_word:
            messagebox.showwarning("Input Error", "Conlang and English fields are required.")
            return

        if any(entry['conlang'].lower() == conlang_word.lower() for entry in self.dictionary):
            messagebox.showwarning("Duplicate Entry", f"The word '{conlang_word}' already exists.")
            return

        self._update_tags(tags_list)

        new_entry = {
            "conlang": conlang_word,
            "english": english_word.split(', '),
            "pos": pos,
            "description": description,
            "tags": tags_list,
            "roots": [],
            "derived": []
        }
        self.dictionary.append(new_entry)
        self.save_dictionary()
        self.update_word_display()

        self.conlang_entry.delete(0, tk.END)
        self.english_entry.delete(0, tk.END)
        self.pos_combobox.set('')
        self.description_text.delete("1.0", tk.END)
        self.tags_entry.delete(0, tk.END)

        self.tree.selection_set(conlang_word)
        self.tree.see(conlang_word)

        self.refresh_stats_page()

    def delete_word(self):
        # Deletes the selected word and updates etymology links.
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a word to delete.")
            return

        conlang_word = selected_item[0]
        entry_to_delete = self.get_entry(conlang_word)
        if not entry_to_delete: return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{conlang_word}'?"):
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
            self.update_word_display()
            messagebox.showinfo("Success", f"Deleted '{conlang_word}'.")

    def edit_word(self, event=None):
        # Opens a new window to edit the selected word.
        selected_item_id = self.tree.focus()
        if not selected_item_id:
            messagebox.showwarning("Selection Error", "Please select a word to edit.")
            return

        entry_to_edit = self.get_entry(selected_item_id)
        if not entry_to_edit:
            return

        editor = tk.Toplevel(self.root)
        editor.title(f"Edit '{entry_to_edit['conlang']}'")
        editor.transient(self.root)
        editor.grab_set()

        frame = ttk.Frame(editor, padding="15")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Conlang Word:").grid(row=0, column=0, sticky=tk.W, pady=5)
        con_entry = ttk.Entry(frame, width=40)
        con_entry.grid(row=0, column=1, sticky=tk.EW)
        con_entry.insert(0, entry_to_edit['conlang'])

        english = ""
        for word in range(len(entry_to_edit["english"])):
            english += entry_to_edit["english"][word]
            if word < len(entry_to_edit["english"]) - 1:
                english += ", "

        ttk.Label(frame, text="English Translation:").grid(row=1, column=0, sticky=tk.W, pady=5)
        eng_entry = ttk.Entry(frame, width=40)
        eng_entry.grid(row=1, column=1, sticky=tk.EW)
        eng_entry.insert(0, english)

        ttk.Label(frame, text="Part of Speech:").grid(row=2, column=0, sticky=tk.W, pady=5)
        pos_box = ttk.Combobox(frame, values=self.word_classes, width=38, state='readonly')
        pos_box.grid(row=2, column=1, sticky=tk.EW)
        pos_box.set(entry_to_edit['pos'])

        ttk.Label(frame, text="Description:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(frame, width=40, height=7, wrap=tk.WORD)
        desc_text.grid(row=3, column=1, sticky=tk.EW)
        desc_text.insert("1.0", entry_to_edit['description'])

        ttk.Label(frame, text="Tags (comma-sep):").grid(row=4, column=0, sticky=tk.W, pady=5)
        tags_entry = ttk.Entry(frame, width=40)
        tags_entry.grid(row=4, column=1, sticky=tk.EW)
        tags_entry.insert(0, ", ".join(entry_to_edit.get('tags', [])))

        frame.columnconfigure(1, weight=1)

        def save_changes():
            new_conlang = con_entry.get().strip()
            old_conlang = entry_to_edit['conlang']

            if new_conlang.lower() != old_conlang.lower() and any(
                    e['conlang'].lower() == new_conlang.lower() for e in self.dictionary):
                messagebox.showerror("Error", "The new conlang word already exists.", parent=editor)
                return

            new_tags_list = [t.strip() for t in tags_entry.get().strip().split(',') if t.strip()]
            self._update_tags(new_tags_list)

            entry_to_edit['conlang'] = new_conlang
            entry_to_edit['english'] = eng_entry.get().strip().split(', ')
            entry_to_edit['pos'] = pos_box.get().strip()
            entry_to_edit['description'] = desc_text.get("1.0", tk.END).strip()
            entry_to_edit['tags'] = new_tags_list

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
            self.tree.selection_set(new_conlang)
            self.tree.see(new_conlang)
            editor.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=editor.destroy).pack(side=tk.LEFT, padx=5)

        self.refresh_stats_page()

    def on_item_double_click(self, event):
        self.edit_word(event)

    def on_item_select(self, event=None):
        selected_item_id = self.tree.focus()
        description = ""
        entry = None

        if selected_item_id:
            entry = self.get_entry(selected_item_id)
            if entry:
                description = entry.get('description', '')

        self.display_description_text.config(state=tk.NORMAL)
        self.display_description_text.delete('1.0', tk.END)
        self.display_description_text.insert('1.0', description)
        self.display_description_text.config(state=tk.DISABLED)

        self.update_etymology_display(entry)

    def clear_filters(self):
        self.search_entry.delete(0, tk.END)
        self.filter_pos_combobox.set("All Classes")
        self.tag_filter_listbox.selection_clear(0, tk.END)
        self.update_word_display()

    def update_tag_filter_listbox(self):
        # Refreshes the 'Filter by Tags' listbox with self.all_tags.
        self.tag_filter_listbox.delete(0, tk.END)
        for tag in sorted(self.all_tags):
            self.tag_filter_listbox.insert(tk.END, tag)

    def manage_tags(self):
        # Opens a Toplevel window to add/remove global tags.
        manager = tk.Toplevel(self.root)
        manager.title("Manage Tags")
        manager.transient(self.root)
        manager.grab_set()

        frame = ttk.Frame(manager, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for tag in self.all_tags:
            listbox.insert(tk.END, tag)

        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=5)

        entry = ttk.Entry(entry_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        def add_tag():
            tag = entry.get().strip()
            if tag and tag not in self.all_tags:
                self.all_tags.append(tag)
                self.all_tags.sort()
                self.save_tags()
                listbox.delete(0, tk.END)
                for t in self.all_tags: listbox.insert(tk.END, t)
                self.update_tag_filter_listbox()
                entry.delete(0, tk.END)

        add_btn = ttk.Button(entry_frame, text="Add Tag", command=add_tag)
        add_btn.pack(side=tk.RIGHT)

        def remove_tag():
            selected_indices = listbox.curselection()
            if not selected_indices: return

            tag_to_remove = listbox.get(selected_indices[0])
            if messagebox.askyesno("Confirm Delete",
                                   f"Really remove '{tag_to_remove}' from the global tag list?\n"
                                   "(This does NOT remove it from words.)",
                                   parent=manager):
                self.all_tags.remove(tag_to_remove)
                self.save_tags()
                listbox.delete(selected_indices[0])
                self.update_tag_filter_listbox()

        remove_btn = ttk.Button(frame, text="Remove Selected Tag", command=remove_tag)
        remove_btn.pack(fill=tk.X, pady=5)

        close_btn = ttk.Button(frame, text="Close", command=manager.destroy)
        close_btn.pack(pady=(10, 0))

    def get_entry(self, conlang_word):
        # Helper to find a dictionary entry by its conlang word."""
        return next((item for item in self.dictionary if item["conlang"] == conlang_word), None)

    def update_etymology_display(self, entry):
        # Populates the etymology listboxes based on the selected entry.
        self.roots_listbox.delete(0, tk.END)
        self.derived_listbox.delete(0, tk.END)

        if entry:
            for root_word in sorted(entry.get('roots', [])):
                self.roots_listbox.insert(tk.END, root_word)
            for derived_word in sorted(entry.get('derived', [])):
                self.derived_listbox.insert(tk.END, derived_word)

    def add_etymology_link(self, link_type):
        # Adds a new root or derived word link.
        selected_word_id = self.tree.focus()
        if not selected_word_id:
            messagebox.showwarning("No Word Selected", "Please select a word to add a link to.")
            return

        entry_A = self.get_entry(selected_word_id)
        if not entry_A: return

        prompt = f"Enter the conlang word that is a {link_type} of '{selected_word_id}':"
        word_B_name = simpledialog.askstring("Add Etymology Link", prompt, parent=self.root)

        if not word_B_name or word_B_name.strip() == "":
            return

        word_B_name = word_B_name.strip()

        if word_B_name == selected_word_id:
            messagebox.showwarning("Self-Link", "A word cannot be its own root or derivative.")
            return

        entry_B = self.get_entry(word_B_name)
        if not entry_B:
            messagebox.showerror("Word Not Found", f"The word '{word_B_name}' does not exist in the dictionary.")
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
        # Removes an existing root or derived word link.
        selected_word_id = self.tree.focus()
        if not selected_word_id: return

        entry_A = self.get_entry(selected_word_id)
        if not entry_A: return

        listbox = self.roots_listbox if link_type == 'root' else self.derived_listbox
        selected_indices = listbox.curselection()

        if not selected_indices:
            messagebox.showwarning("No Link Selected", f"Please select a {link_type} word to remove.")
            return

        word_B_name = listbox.get(selected_indices[0])
        entry_B = self.get_entry(word_B_name)

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

    def jump_to_word_from_listbox(self, event):
        # Finds and selects a word in the main tree from an etymology listbox.
        listbox = event.widget
        selected_indices = listbox.curselection()
        if not selected_indices: return

        word_to_find = listbox.get(selected_indices[0])

        if self.tree.exists(word_to_find):
            self.tree.selection_set(word_to_find)
            self.tree.see(word_to_find)
            self.main_notebook.select(self.tab_dictionary)

            selected_item_id = self.tree.focus(word_to_find)
            description = ""
            entry = None

            if selected_item_id:
                entry = self.get_entry(selected_item_id)
                if entry:
                    description = entry.get('description', '')

            self.display_description_text.config(state=tk.NORMAL)
            self.display_description_text.delete('1.0', tk.END)
            self.display_description_text.insert('1.0', description)
            self.display_description_text.config(state=tk.DISABLED)

            self.update_etymology_display(entry)
        else:
            messagebox.showwarning("Link Error", f"The word '{word_to_find}' seems to be missing.")

    def load_grammar_rules(self):
        self.grammar_rules_text.delete('1.0', tk.END)
        self.grammar_rules_text.insert('1.0', self.grammar_data.get('rules', ''))

    def save_grammar_rules(self):
        self.grammar_data['rules'] = self.grammar_rules_text.get('1.0', tk.END).strip()
        self.save_grammar()
        messagebox.showinfo("Success", "Grammar rules saved.", parent=self.tab_grammar)

    def update_grammar_table_listbox(self):
        self.table_listbox.delete(0, tk.END)
        for table_name in sorted(self.grammar_data['tables'].keys()):
            self.table_listbox.insert(tk.END, table_name)

    def load_table_into_editor(self, event=None):
        selected_indices = self.table_listbox.curselection()
        if not selected_indices: return

        table_name = self.table_listbox.get(selected_indices[0])
        content = self.grammar_data['tables'].get(table_name, '')

        self.table_text_editor.delete('1.0', tk.END)
        self.table_text_editor.insert('1.0', content)

    def save_grammar_table(self):
        selected_indices = self.table_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Table Selected", "Please select a table to save.", parent=self.tab_grammar)
            return

        table_name = self.table_listbox.get(selected_indices[0])
        content = self.table_text_editor.get('1.0', tk.END).strip()

        self.grammar_data['tables'][table_name] = content
        self.save_grammar()
        messagebox.showinfo("Success", f"Table '{table_name}' saved.", parent=self.tab_grammar)

    def create_grammar_table(self):
        table_name = simpledialog.askstring("Create Table", "Enter a name for the new table:", parent=self.tab_grammar)

        if not table_name or table_name.strip() == "":
            return

        table_name = table_name.strip()

        if table_name in self.grammar_data['tables']:
            messagebox.showwarning("Duplicate", f"A table named '{table_name}' already exists.",
                                   parent=self.tab_grammar)
            return

        self.grammar_data['tables'][table_name] = f"# Table: {table_name}\n(Enter your table data here)"
        self.save_grammar()

        self.update_grammar_table_listbox()
        try:
            index = list(self.table_listbox.get(0, tk.END)).index(table_name)
            self.table_listbox.selection_set(index)
            self.load_table_into_editor()
        except ValueError:
            pass

    def delete_grammar_table(self):
        selected_indices = self.table_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Table Selected", "Please select a table to delete.", parent=self.tab_grammar)
            return

        table_name = self.table_listbox.get(selected_indices[0])

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the table '{table_name}'?",
                               parent=self.tab_grammar):
            del self.grammar_data['tables'][table_name]
            self.save_grammar()
            self.update_grammar_table_listbox()
            self.table_text_editor.delete('1.0', tk.END)

    def refresh_stats_page(self):
        self.stats_text.config(state=tk.NORMAL)

        total_words = len(self.dictionary)
        parts_of_speech = dict(zip(self.word_classes, [0 for x in range(len(self.word_classes))]))
        tags = dict(zip(self.all_tags, [0 for x in range(len(self.all_tags))]))
        root_words = 0
        terminal_words = 0

        for word in self.dictionary:
            parts_of_speech[word["pos"]] += 1

            for tag in word["tags"]:
                tags[tag] += 1

            if not word["roots"]:
                root_words += 1

            if not word["derived"]:
                terminal_words += 1

        stats_text_content = f"Total Words: {total_words}\nRoot Words: {root_words}\nTerminal Words: {terminal_words}\n\n== Parts of Speech ==\n"

        for pos in parts_of_speech.keys():
            if pos in ["Suffix", "Prefix"]:
                stats_text_content += f"{pos}es: {parts_of_speech[pos]}\n"
            elif pos == "Other":
                stats_text_content += f"{pos}: {parts_of_speech[pos]}\n"
            else:
                stats_text_content += f"{pos}s: {parts_of_speech[pos]}\n"

        stats_text_content += "\n== Tags ==\n"

        for tag in tags.keys():
            stats_text_content += f"{tag}: {tags[tag]}\n"

        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, stats_text_content)

        self.stats_text.config(state=tk.DISABLED)

    def on_closing(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ConlangDictionaryApp(root)
    root.mainloop()
