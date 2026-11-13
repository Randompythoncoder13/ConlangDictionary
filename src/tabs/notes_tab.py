import os
import re
import csv
import json
import uuid
import html
import shutil
import sys
import markdown
import base64

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextBrowser,
    QPushButton, QToolButton, QListWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QSplitter, QDialog, QFileDialog, QMenu,
    QApplication, QLineEdit, QFrame, QButtonGroup
)
from PySide6.QtGui import (
    QTextCursor, QFont, QAction, QImage, QSyntaxHighlighter,
    QTextCharFormat, QColor, QKeySequence, QShortcut
)
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QEvent, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.custom_widgets import IPAPickerPopup, GrammarEditor
from src.dialogs import GlossDialog
from src.functions import load_sections

TABLE_MACRO_RE = re.compile(r"\{\{table:([^}]+)\}\}")
FONT_MACRO_RE = re.compile(r"\{\{f:([^}]+)\}\}")
IPA_MACRO_RE = re.compile(r"\{\{ipa:([^}]+)\}\}")
SC_MACRO_RE = re.compile(r"\{\{sc:([^}]+)\}\}")
RULE_MACRO_RE = re.compile(r"\{\{rule:([^}]+)\}\}")

GLOSS_BLOCK_RE = re.compile(r"^:::\s*gloss(?:\s+([^\n]*))?\n(.*?)\n^:::\s*$", re.MULTILINE | re.DOTALL)
CALLOUT_BLOCK_RE = re.compile(
    r"^:::\s*(note|example|rule|warning)(?:\s+([^\n]*))?\n(.*?)\n^:::\s*$",
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)
GRAMMAR_TAG_RE = re.compile(r"\b([123]?(?:SG|PL|DU)|[A-Z]{2,6})\b")


class ConlangMarkupHighlighter(QSyntaxHighlighter):
    def __init__(self, document, is_dark=False):
        super().__init__(document)
        self.is_dark = is_dark
        self._rebuild_rules()

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._rebuild_rules()
        self.rehighlight()

    def _rebuild_rules(self):
        self.rules = []

        if self.is_dark:
            c_heading = "#58a6ff"
            c_macro = "#d2a8ff"
            c_block = "#ffa657"
            c_bold = "#f0f6fc"
            c_italic = "#a5d6ff"
            c_quote = "#8b949e"
        else:
            c_heading = "#0969da"
            c_macro = "#8250df"
            c_block = "#bc4c00"
            c_bold = "#1f2328"
            c_italic = "#0550ae"
            c_quote = "#57606a"

        # Headings
        h_fmt = QTextCharFormat()
        h_fmt.setForeground(QColor(c_heading))
        h_fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"^#{1,6}\s.*$"), h_fmt))

        # Bold
        b_fmt = QTextCharFormat()
        b_fmt.setForeground(QColor(c_bold))
        b_fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"\*\*[^*]+\*\*"), b_fmt))

        # Italic
        i_fmt = QTextCharFormat()
        i_fmt.setForeground(QColor(c_italic))
        i_fmt.setFontItalic(True)
        self.rules.append((re.compile(r"(?<!\*)\*[^*\n]+\*(?!\*)"), i_fmt))

        # Macros
        m_fmt = QTextCharFormat()
        m_fmt.setForeground(QColor(c_macro))
        m_fmt.setFontWeight(QFont.Weight.DemiBold)
        self.rules.append((re.compile(r"\{\{[a-zA-Z]+:[^}]+\}\}"), m_fmt))

        # Fencing
        blk_fmt = QTextCharFormat()
        blk_fmt.setForeground(QColor(c_block))
        blk_fmt.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"^:::.*$"), blk_fmt))

        # Blockquotes
        q_fmt = QTextCharFormat()
        q_fmt.setForeground(QColor(c_quote))
        q_fmt.setFontItalic(True)
        self.rules.append((re.compile(r"^>\s.*$"), q_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class NotesTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.is_dark_mode = getattr(main_app, "is_dark_mode", False)

        self._loading = False
        self._loading_table = False
        self.current_section_index = None
        self.sections = load_sections(main_app)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(1000)
        self.autosave_timer.timeout.connect(self._autosave_rules)

        self.table_autosave_timer = QTimer(self)
        self.table_autosave_timer.setSingleShot(True)
        self.table_autosave_timer.setInterval(1200)
        self.table_autosave_timer.timeout.connect(self._autosave_current_table)

        self._build_ui()
        self._setup_shortcuts()
        self._populate_section_list()
        self.update_grammar_table_listbox()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(6)

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_splitter.setHandleWidth(6)
        outer_layout.addWidget(main_splitter)

        main_splitter.addWidget(self._build_editor_frame())
        main_splitter.addWidget(self._build_tables_pane())
        main_splitter.setSizes([560, 300])

        self._init_ipa_picker()

    def _build_editor_frame(self):
        editor_frame = QWidget()
        editor_h_layout = QHBoxLayout(editor_frame)
        editor_h_layout.setContentsMargins(0, 0, 0, 0)
        editor_h_layout.setSpacing(10)

        sections_pane = self._build_sections_pane()
        sections_pane.setMinimumWidth(210)
        sections_pane.setMaximumWidth(260)
        editor_h_layout.addWidget(sections_pane)

        editor_pane = QFrame()
        editor_pane.setObjectName("NotesWorkspaceFrame")
        editor_v_layout = QVBoxLayout(editor_pane)
        editor_v_layout.setContentsMargins(0, 0, 0, 0)
        editor_v_layout.setSpacing(6)

        editor_v_layout.addWidget(self._build_toolbar())

        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_splitter.setHandleWidth(6)

        self.editor = GrammarEditor(self)
        self.editor.setPlaceholderText(
            "Write chapter notes here...\n"
            "Tip: Use {{f:word}} for conlang script, {{table:Name}} for tables, "
            "or click 'Gloss Block' / 'Callout' in the toolbar."
        )
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 6px;
                padding: 10px;
                font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        self.highlighter = ConlangMarkupHighlighter(self.editor.document(), self.is_dark_mode)
        self.editor.textChanged.connect(self._on_editor_text_changed)

        self.preview = QWebEngineView()
        self.preview.setStyleSheet("background-color: palette(base); border-radius: 6px;")

        self.editor_splitter.addWidget(self.editor)
        self.editor_splitter.addWidget(self.preview)
        self.editor_splitter.setSizes([450, 450])

        editor_v_layout.addWidget(self.editor_splitter, 1)

        editor_v_layout.addWidget(self._build_status_bar())

        editor_h_layout.addWidget(editor_pane, 1)
        return editor_frame

    def _build_sections_pane(self):
        frame = QGroupBox("Chapters")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        self.chapter_search = QLineEdit()
        self.chapter_search.setPlaceholderText("Filter chapters...")
        self.chapter_search.setClearButtonEnabled(True)
        self.chapter_search.textChanged.connect(self._filter_section_list)
        layout.addWidget(self.chapter_search)

        self.section_list = QListWidget()
        self.section_list.setAlternatingRowColors(False)
        self.section_list.setStyleSheet("""
            QListWidget {
                border: 1px solid palette(mid);
                border-radius: 5px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                font-weight: bold;
            }
        """)
        self.section_list.currentRowChanged.connect(self._on_section_selected)
        layout.addWidget(self.section_list, 1)

        btn_row_top = QHBoxLayout()
        btn_row_top.setSpacing(4)

        add_btn = QPushButton("+ New")
        add_btn.setToolTip("Create a new grammar chapter")
        add_btn.clicked.connect(self._add_section)

        rename_btn = QPushButton("Rename")
        rename_btn.setToolTip("Rename the selected chapter")
        rename_btn.clicked.connect(self._rename_section)

        delete_btn = QPushButton("Delete")
        delete_btn.setToolTip("Delete the selected chapter")
        delete_btn.clicked.connect(self._delete_section)

        for b in (add_btn, rename_btn, delete_btn):
            btn_row_top.addWidget(b)
        layout.addLayout(btn_row_top)

        btn_row_order = QHBoxLayout()
        btn_row_order.setSpacing(4)

        move_up_btn = QPushButton("↑ Move Up")
        move_up_btn.setToolTip("Move chapter up")
        move_up_btn.clicked.connect(lambda: self._move_section(-1))

        move_down_btn = QPushButton("↓ Move Down")
        move_down_btn.setToolTip("Move chapter down")
        move_down_btn.clicked.connect(lambda: self._move_section(1))

        btn_row_order.addWidget(move_up_btn)
        btn_row_order.addWidget(move_down_btn)
        layout.addLayout(btn_row_order)

        return frame

    def _build_toolbar(self):
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: palette(window);
                border: 1px solid palette(mid);
                border-radius: 6px;
            }
            QPushButton, QToolButton {
                padding: 4px 8px;
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        heading_btn = QToolButton()
        heading_btn.setText("Heading ▾")
        heading_menu = QMenu(heading_btn)
        for level, desc in ((1, "H1 — Chapter Section"), (2, "H2 — Sub-section"), (3, "H3 — Topic")):
            action = QAction(desc, self)
            action.triggered.connect(lambda checked=False, lvl=level: self._insert_heading(lvl))
            heading_menu.addAction(action)
        heading_btn.setMenu(heading_menu)
        heading_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(heading_btn)

        bold_btn = QPushButton("B")
        bold_btn.setToolTip("Bold (Ctrl+B)")
        bold_font = QFont()
        bold_font.setBold(True)
        bold_btn.setFont(bold_font)
        bold_btn.setFixedWidth(28)
        bold_btn.clicked.connect(lambda: self._wrap_selection("**"))
        layout.addWidget(bold_btn)

        italic_btn = QPushButton("I")
        italic_btn.setToolTip("Italic (Ctrl+I)")
        italic_font = QFont()
        italic_font.setItalic(True)
        italic_btn.setFont(italic_font)
        italic_btn.setFixedWidth(28)
        italic_btn.clicked.connect(lambda: self._wrap_selection("*"))
        layout.addWidget(italic_btn)

        bullet_btn = QPushButton("• List")
        bullet_btn.setToolTip("Toggle bullet list")
        bullet_btn.clicked.connect(self._toggle_bullet_list)
        layout.addWidget(bullet_btn)

        layout.addWidget(self._make_vsep())

        conlang_btn = QPushButton("Conlang Script")
        conlang_btn.setToolTip("Wrap text in custom conlang font {{f:...}} (Ctrl+K)")
        conlang_btn.clicked.connect(lambda: self._wrap_selection("{{f:", "}}"))
        layout.addWidget(conlang_btn)

        ling_btn = QToolButton()
        ling_btn.setText("Linguistics ▾")
        ling_btn.setToolTip("Insert phonetic, small-caps, or sound-change notation")
        ling_menu = QMenu(ling_btn)

        act_ipa = QAction("IPA Transcription  {{ipa:/.../}}", self)
        act_ipa.triggered.connect(lambda: self._wrap_selection("{{ipa:/", "/}}"))
        ling_menu.addAction(act_ipa)

        act_sc = QAction("Small Caps Gloss Tag  {{sc:NOM}}", self)
        act_sc.triggered.connect(lambda: self._wrap_selection("{{sc:", "}}"))
        ling_menu.addAction(act_sc)

        act_rule = QAction("Sound Change Rule  {{rule:A > B / C _ D}}", self)
        act_rule.triggered.connect(lambda: self._wrap_selection("{{rule:", "}}"))
        ling_menu.addAction(act_rule)

        ling_btn.setMenu(ling_menu)
        ling_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(ling_btn)

        self.ipa_btn = QPushButton("IPA Chart")
        self.ipa_btn.setToolTip("Open interactive IPA character picker")
        self.ipa_btn.clicked.connect(self._toggle_ipa_picker)
        layout.addWidget(self.ipa_btn)

        gloss_btn = QToolButton()
        gloss_btn.setText("Gloss ▾")
        gloss_btn.setToolTip("Insert an interlinear gloss")
        gloss_menu = QMenu(gloss_btn)

        act_gloss_block = QAction("Insert Auto-Aligned Gloss Block (::: gloss)", self)
        act_gloss_block.triggered.connect(self._insert_gloss_template)
        gloss_menu.addAction(act_gloss_block)

        act_gloss_dlg = QAction("Open Gloss Builder Dialog...", self)
        act_gloss_dlg.triggered.connect(self._open_gloss_dialog)
        gloss_menu.addAction(act_gloss_dlg)

        gloss_btn.setMenu(gloss_menu)
        gloss_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(gloss_btn)

        callout_btn = QToolButton()
        callout_btn.setText("Callout ▾")
        callout_btn.setToolTip("Insert a styled Note, Example, Sound Rule, or Warning box")
        callout_menu = QMenu(callout_btn)
        for kind, label in (
            ("note", "Note Box"),
            ("example", "Example Box"),
            ("rule", "Grammar / Sound Rule Box"),
            ("warning", "Irregularity / Warning Box"),
        ):
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, k=kind: self._insert_callout(k))
            callout_menu.addAction(act)
        callout_btn.setMenu(callout_menu)
        callout_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(callout_btn)

        layout.addWidget(self._make_vsep())

        table_macro_btn = QPushButton("Embed Table")
        table_macro_btn.setToolTip("Embed a dynamic Grammar Table {{table:Name}}")
        table_macro_btn.clicked.connect(self._insert_table_macro)
        layout.addWidget(table_macro_btn)

        image_btn = QPushButton("Image")
        image_btn.setToolTip("Import and embed an image")
        image_btn.clicked.connect(self._insert_image)
        layout.addWidget(image_btn)

        help_btn = QPushButton("Syntax Guide")
        help_btn.clicked.connect(self._show_syntax_help)
        layout.addWidget(help_btn)

        layout.addStretch()

        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)

        for idx, (label, tip) in enumerate((
            ("Write", "Editor only"),
            ("Split", "Side-by-side Editor and Live Preview"),
            ("Read", "Clean Reader view only"),
        )):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            if idx == 1:
                btn.setChecked(True)
            self.view_group.addButton(btn, idx)
            layout.addWidget(btn)

        self.view_group.idClicked.connect(self._set_view_mode)

        return bar

    def _build_status_bar(self):
        footer = QFrame()
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(12)

        self.chapter_title_label = QLabel("Chapter: —")
        self.chapter_title_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.chapter_title_label)

        self.word_count_label = QLabel("0 words  •  0 chars")
        self.word_count_label.setStyleSheet("color: gray;")
        layout.addWidget(self.word_count_label)

        layout.addStretch()

        self.save_status_label = QLabel("All changes saved")
        self.save_status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.save_status_label)

        save_now_btn = QPushButton("Save Now")
        save_now_btn.setToolTip("Save chapter immediately (Ctrl+S)")
        save_now_btn.clicked.connect(self.save_grammar_rules)
        layout.addWidget(save_now_btn)

        return footer

    @staticmethod
    def _make_vsep():
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+B"), self.editor, activated=lambda: self._wrap_selection("**"))
        QShortcut(QKeySequence("Ctrl+I"), self.editor, activated=lambda: self._wrap_selection("*"))
        QShortcut(QKeySequence("Ctrl+K"), self.editor, activated=lambda: self._wrap_selection("{{f:", "}}"))
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_grammar_rules)

    def _set_view_mode(self, mode_id: int):
        if mode_id == 0:
            self.editor.setVisible(True)
            self.preview.setVisible(False)
        elif mode_id == 1:
            self.editor.setVisible(True)
            self.preview.setVisible(True)
            self.editor_splitter.setSizes([450, 450])
        elif mode_id == 2:
            self.editor.setVisible(False)
            self.preview.setVisible(True)

    def _build_tables_pane(self):
        tables_frame = QGroupBox("Grammar Tables")
        tables_layout = QHBoxLayout(tables_frame)

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

        export_btn = QPushButton("Export to CSV / MD")
        export_btn.clicked.connect(self.export_table_csv)
        table_controls_layout.addWidget(export_btn)

        import_btn = QPushButton("Import from CSV")
        import_btn.clicked.connect(self.import_table_csv)
        table_controls_layout.addWidget(import_btn)

        insert_btn = QPushButton("Insert into Chapter")
        insert_btn.clicked.connect(self.insert_table_into_section)
        table_controls_layout.addWidget(insert_btn)

        table_controls_frame.setMaximumWidth(250)
        tables_layout.addWidget(table_controls_frame)

        table_editor_frame = QWidget()
        table_editor_layout = QVBoxLayout(table_editor_frame)

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
        self.table_editor.setStyleSheet("QTableWidget { background-color: palette(base); }")
        self.table_editor.horizontalHeader().setSectionsClickable(True)
        self.table_editor.verticalHeader().setSectionsClickable(True)
        self.table_editor.horizontalHeader().sectionDoubleClicked.connect(self.edit_table_header)
        self.table_editor.verticalHeader().sectionDoubleClicked.connect(self.edit_table_header)
        self.table_editor.itemChanged.connect(self._on_table_item_changed)

        table_editor_layout.addWidget(self.table_editor)

        save_table_btn = QPushButton("Save Current Table")
        save_table_btn.clicked.connect(self.save_grammar_table)
        table_editor_layout.addWidget(save_table_btn)

        tables_layout.addWidget(table_editor_frame)

        return tables_frame

    def load_grammar_rules(self):
        """Reload chapters from main_app.grammar_data (e.g. on tab activation)."""
        keep_index = self.current_section_index or 0
        self.sections = load_sections(self.main_app)
        self._populate_section_list(select_index=keep_index)

    def save_grammar_rules(self):
        self.autosave_timer.stop()
        self._persist_sections()
        self.save_status_label.setText("All changes saved")

    def _persist_sections(self):
        payload = json.dumps({"sections": self.sections})
        self.main_app.grammar_data['rules'] = payload
        self.main_app.save_grammar()

    def _autosave_rules(self):
        self._persist_sections()
        self.save_status_label.setText("All changes saved")

    def _populate_section_list(self, select_index=0):
        self._loading = True
        self.section_list.clear()

        for section in self.sections:
            self.section_list.addItem(section['title'])

        self._loading = False

        if self.sections:
            select_index = max(0, min(select_index, len(self.sections) - 1))
            self.section_list.setCurrentRow(select_index)

        if hasattr(self, "chapter_search") and self.chapter_search.text():
            self._filter_section_list(self.chapter_search.text())

    def _filter_section_list(self, query: str):
        q = query.strip().lower()
        for idx in range(self.section_list.count()):
            item = self.section_list.item(idx)
            item.setHidden(bool(q) and q not in item.text().lower())

    def _on_section_selected(self, row):
        if row < 0 or row >= len(self.sections):
            self.current_section_index = None
            self.chapter_title_label.setText("Chapter: —")
            return

        self.current_section_index = row
        section = self.sections[row]
        content = section.get('content', '')
        title = section.get('title', 'Untitled')

        self.chapter_title_label.setText(f"Chapter: {title}")

        self._loading = True
        self.editor.setPlainText(content)
        self._loading = False

        self._update_word_count(content)
        self._update_preview(content)

    def _add_section(self):
        title, ok = QInputDialog.getText(self, "New Chapter", "Chapter title:")
        if not ok or not title.strip():
            return

        title = title.strip()
        if any(s['title'] == title for s in self.sections):
            QMessageBox.warning(self, "Duplicate", f"A chapter named '{title}' already exists.")
            return

        self.sections.append({"id": str(uuid.uuid4()), "title": title, "content": f"# {title}\n\n"})
        self._persist_sections()
        self._populate_section_list(select_index=len(self.sections) - 1)
        self.editor.setFocus()

    def _rename_section(self):
        row = self.section_list.currentRow()
        if row < 0:
            return

        old_title = self.sections[row]['title']
        title, ok = QInputDialog.getText(self, "Rename Chapter", "Chapter title:", text=old_title)
        if not ok or not title.strip():
            return

        title = title.strip()
        if any(i != row and s['title'] == title for i, s in enumerate(self.sections)):
            QMessageBox.warning(self, "Duplicate", f"A chapter named '{title}' already exists.")
            return

        self.sections[row]['title'] = title
        self._persist_sections()
        self._populate_section_list(select_index=row)

    def _delete_section(self):
        row = self.section_list.currentRow()
        if row < 0:
            return

        title = self.sections[row]['title']
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Delete chapter '{title}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        del self.sections[row]
        if not self.sections:
            self.sections.append({"id": str(uuid.uuid4()), "title": "General", "content": ""})

        self._persist_sections()
        self._populate_section_list(select_index=max(0, row - 1))

    def _move_section(self, direction: int):
        row = self.section_list.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.sections):
            return

        self.sections[row], self.sections[new_row] = self.sections[new_row], self.sections[row]
        self._persist_sections()
        self._populate_section_list(select_index=new_row)

    def _on_editor_text_changed(self):
        if self._loading or self.current_section_index is None:
            return

        text = self.editor.toPlainText()
        self.sections[self.current_section_index]['content'] = text
        self.save_status_label.setText("Unsaved changes...")
        self._update_word_count(text)
        self._update_preview(text)
        self.autosave_timer.start()

    def _update_word_count(self, text: str):
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self.word_count_label.setText(f"{words:,} words  •  {chars:,} chars")

    def _update_preview(self, markdown_text: str):
        processed = self._expand_gloss_blocks(markdown_text)
        processed = self._expand_callout_blocks(processed)

        processed = self._expand_table_macros(processed)

        processed = self._expand_inline_macros(processed)

        body_html = markdown.markdown(
            processed,
            extensions=['tables', 'sane_lists', 'fenced_code', 'nl2br']
        )

        font_face_css = ""
        conlang_font_family = "ConlangCustomFont"
        font_path = getattr(self.main_app, "font_path", None)

        if font_path and os.path.exists(font_path):
            try:
                with open(font_path, "rb") as font_file:
                    font_base64 = base64.b64encode(font_file.read()).decode('utf-8')
                    font_face_css = f"""
                        @font-face {{
                            font-family: "{conlang_font_family}";
                            src: url(data:font/truetype;base64,{font_base64}) format('truetype');
                        }}
                    """
            except OSError:
                pass

        if getattr(self, 'is_dark_mode', False):
            bg_color = "#0d1117"
            surface_color = "#161b22"
            text_color = "#e6edf3"
            muted_color = "#8b949e"
            border_color = "#30363d"
            th_bg = "#21262d"
            row_th_bg = "#1b2028"
            accent_color = "#58a6ff"
            code_bg = "rgba(110,118,129,0.25)"
        else:
            bg_color = "#ffffff"
            surface_color = "#f6f8fa"
            text_color = "#1f2328"
            muted_color = "#57606a"
            border_color = "#d0d7de"
            th_bg = "#eaeef2"
            row_th_bg = "#f0f3f6"
            accent_color = "#0969da"
            code_bg = "#eff1f3"

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                {font_face_css}

                * {{ box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
                    line-height: 1.7;
                    color: {text_color};
                    background-color: {bg_color};
                    padding: 28px 36px;
                    max-width: 880px;
                    margin: 0 auto;
                    font-size: 15px;
                }}
                h1, h2, h3, h4 {{
                    color: {text_color};
                    font-weight: 650;
                    line-height: 1.3;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                }}
                h1 {{
                    font-size: 1.85em;
                    padding-bottom: 0.3em;
                    border-bottom: 2px solid {border_color};
                    margin-top: 0.2em;
                }}
                h2 {{
                    font-size: 1.4em;
                    padding-bottom: 0.2em;
                    border-bottom: 1px solid {border_color};
                }}
                h3 {{ font-size: 1.15em; }}
                hr {{
                    border: none;
                    border-top: 1px solid {border_color};
                    margin: 24px 0;
                }}

                /* Conlang Script & Linguistic Inline Badges */
                .conlang-script {{
                    font-family: "{conlang_font_family}", sans-serif;
                    font-size: 1.25em;
                    line-height: 1.2;
                    padding: 0 2px;
                }}
                .ipa-badge {{
                    font-family: "Charis SIL", "Doulos SIL", "Gentium Plus", "Noto Sans", "Segoe UI", sans-serif;
                    background-color: {code_bg};
                    padding: 1px 6px;
                    border-radius: 4px;
                    font-size: 0.95em;
                }}
                .sc {{
                    font-variant: small-caps;
                    font-size: 0.92em;
                    letter-spacing: 0.04em;
                    font-weight: 600;
                    color: {accent_color};
                }}
                .sound-rule {{
                    font-family: "Charis SIL", "Doulos SIL", "Gentium Plus", monospace;
                    background-color: {surface_color};
                    border: 1px solid {border_color};
                    padding: 2px 8px;
                    border-radius: 5px;
                    font-weight: 500;
                }}

                /* Interlinear Gloss Blocks */
                .gloss-card {{
                    background-color: {surface_color};
                    border: 1px solid {border_color};
                    border-left: 4px solid {accent_color};
                    border-radius: 6px;
                    padding: 12px 16px;
                    margin: 16px 0;
                    overflow-x: auto;
                }}
                .gloss-title {{
                    font-size: 0.8em;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    color: {muted_color};
                    margin-bottom: 6px;
                    font-weight: 600;
                }}
                .gloss-units {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px 22px;
                    margin-bottom: 6px;
                }}
                .gloss-unit {{
                    display: flex;
                    flex-direction: column;
                }}
                .gloss-line-0 {{
                    font-weight: 600;
                    font-style: italic;
                    color: {text_color};
                }}
                .gloss-line-extra {{
                    color: {text_color};
                }}
                .gloss-line-tags {{
                    font-size: 0.92em;
                    color: {muted_color};
                }}
                .gloss-translation {{
                    margin-top: 6px;
                    padding-top: 6px;
                    border-top: 1px dashed {border_color};
                    color: {text_color};
                }}

                /* Callout Cards */
                .callout {{
                    background-color: {surface_color};
                    border: 1px solid {border_color};
                    border-left-width: 4px;
                    border-radius: 6px;
                    padding: 12px 16px;
                    margin: 16px 0;
                }}
                .callout-header {{
                    font-weight: 700;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                    margin-bottom: 6px;
                }}
                .callout-note {{ border-left-color: #3b82f6; }}
                .callout-note .callout-header {{ color: #3b82f6; }}
                .callout-example {{ border-left-color: #10b981; }}
                .callout-example .callout-header {{ color: #10b981; }}
                .callout-rule {{ border-left-color: #a855f7; }}
                .callout-rule .callout-header {{ color: #a855f7; }}
                .callout-warning {{ border-left-color: #f59e0b; }}
                .callout-warning .callout-header {{ color: #f59e0b; }}

                /* Tables */
                .table-wrapper {{
                    margin: 18px 0;
                    overflow-x: auto;
                    border: 1px solid {border_color};
                    border-radius: 6px;
                }}
                .table-caption {{
                    background-color: {th_bg};
                    padding: 8px 14px;
                    font-weight: 700;
                    font-size: 0.95em;
                    border-bottom: 1px solid {border_color};
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    font-size: 0.94em;
                }}
                th, td {{
                    border: 1px solid {border_color};
                    padding: 8px 12px;
                    text-align: left;
                }}
                .table-wrapper table th, .table-wrapper table td {{
                    border-left: none;
                    border-right: 1px solid {border_color};
                    border-bottom: 1px solid {border_color};
                }}
                th {{
                    background-color: {th_bg};
                    font-weight: 600;
                }}
                th.row-header {{
                    background-color: {row_th_bg};
                    font-weight: 600;
                    width: 1%;
                    white-space: nowrap;
                }}
                tr:nth-child(even) td {{
                    background-color: {surface_color};
                }}

                img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 6px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.12);
                    margin: 10px 0;
                }}
                blockquote {{
                    margin: 0 0 16px 0;
                    padding: 8px 16px;
                    color: {muted_color};
                    border-left: 4px solid {border_color};
                    background: {surface_color};
                    border-radius: 0 6px 6px 0;
                }}
                code {{
                    background-color: {code_bg};
                    padding: 0.2em 0.4em;
                    border-radius: 4px;
                    font-family: "JetBrains Mono", "Consolas", monospace;
                    font-size: 0.9em;
                }}
                pre code {{
                    display: block;
                    padding: 12px;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            {body_html}
        </body>
        </html>
        """

        images_dir = self._ensure_image_dir()
        base_url = QUrl.fromLocalFile(images_dir + os.sep)
        self.preview.setHtml(full_html, base_url)

    def _expand_inline_macros(self, text: str) -> str:
        text = FONT_MACRO_RE.sub(
            lambda m: f'<span class="conlang-script">{html.escape(m.group(1))}</span>', text
        )
        text = IPA_MACRO_RE.sub(lambda m: f'<span class="ipa-badge">{html.escape(m.group(1))}</span>', text)
        text = SC_MACRO_RE.sub(lambda m: f'<span class="sc">{html.escape(m.group(1).lower())}</span>', text)
        def _format_rule(match):
            raw = html.escape(match.group(1).strip())
            raw = raw.replace("-&gt;", "→").replace("&gt;", "→")
            return f'<span class="sound-rule">{raw}</span>'

        text = RULE_MACRO_RE.sub(_format_rule, text)
        return text

    def _expand_gloss_blocks(self, text: str) -> str:
        """
        Transforms:
        ::: gloss Optional Title
        conlang line
        morpheme-break line
        GLOSS.TAG line
        "Free translation"
        :::
        into an aligned flexbox interlinear gloss card.
        """
        def _format_gloss_tags(token: str) -> str:
            escaped = html.escape(token)
            return GRAMMAR_TAG_RE.sub(
                lambda m: f'<span class="sc">{m.group(1).lower()}</span>',
                escaped
            )

        def _replace(match):
            title = (match.group(1) or "").strip()
            body = match.group(2).strip()
            raw_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
            if not raw_lines:
                return ""

            translation = ""
            if len(raw_lines) >= 2 and (
                raw_lines[-1].startswith(('"', "'", "“", "‘"))
                or raw_lines[-1].endswith(('"', "'", "”", "’"))
            ):
                translation = raw_lines.pop()

            tokenized_rows = [ln.split() for ln in raw_lines]
            max_cols = max((len(r) for r in tokenized_rows), default=0)

            units_html = []
            for col_idx in range(max_cols):
                col_cells = []
                for row_idx, row_tokens in enumerate(tokenized_rows):
                    tok = row_tokens[col_idx] if col_idx < len(row_tokens) else ""
                    if row_idx == 0:
                        cell_txt = self._expand_inline_macros(tok)
                        col_cells.append(f'<span class="gloss-line-0">{cell_txt}</span>')
                    elif row_idx == len(tokenized_rows) - 1:
                        col_cells.append(f'<span class="gloss-line-tags">{_format_gloss_tags(tok)}</span>')
                    else:
                        col_cells.append(f'<span class="gloss-line-extra">{html.escape(tok)}</span>')

                units_html.append(f'<div class="gloss-unit">{"".join(col_cells)}</div>')

            title_html = f'<div class="gloss-title">{html.escape(title)}</div>' if title else ""
            trans_html = (
                f'<div class="gloss-translation">{html.escape(translation)}</div>'
                if translation else ""
            )

            return (
                f'\n<div class="gloss-card">'
                f'{title_html}'
                f'<div class="gloss-units">{"".join(units_html)}</div>'
                f'{trans_html}'
                f'</div>\n'
            )

        return GLOSS_BLOCK_RE.sub(_replace, text)

    def _expand_callout_blocks(self, text: str) -> str:
        default_titles = {
            "note": "Note",
            "example": "Example",
            "rule": "Grammar / Sound Rule",
            "warning": "Irregularity / Exception",
        }

        def _replace(match):
            kind = match.group(1).lower()
            custom_title = (match.group(2) or "").strip()
            body_md = match.group(3).strip()

            header = html.escape(custom_title) if custom_title else default_titles.get(kind, "Note")
            inner_expanded = self._expand_inline_macros(body_md)
            inner_html = markdown.markdown(
                inner_expanded,
                extensions=['tables', 'sane_lists', 'fenced_code', 'nl2br']
            )
            return (
                f'\n<div class="callout callout-{kind}">'
                f'<div class="callout-header">{header}</div>'
                f'<div class="callout-body">{inner_html}</div>'
                f'</div>\n'
            )

        return CALLOUT_BLOCK_RE.sub(_replace, text)

    def _expand_table_macros(self, text: str) -> str:
        def replace(match):
            name = match.group(1).strip()
            table = self.main_app.grammar_data.get('tables', {}).get(name)
            if not table:
                return f'*[Missing table: {html.escape(name)}]*'
            return self._table_to_html(table, name)

        return TABLE_MACRO_RE.sub(replace, text)

    def _table_to_html(self, table: dict, name: str) -> str:
        col_headers = table.get('col_headers', [])
        row_headers = table.get('row_headers', [])
        data = table.get('data', [])

        ths = []
        if row_headers:
            ths.append('<th class="row-header"></th>')
        for ch in col_headers:
            ths.append(f'<th>{ self._expand_inline_macros(html.escape(str(ch))) }</th>')

        rows_html = []
        for r_idx, row in enumerate(data):
            cells = []
            if row_headers:
                r_label = str(row_headers[r_idx]) if r_idx < len(row_headers) else ""
                cells.append(f'<th scope="row" class="row-header">{self._expand_inline_macros(html.escape(r_label))}</th>')
            for cell in row:
                clean = str(cell).replace('\n', '<br>')
                cells.append(f'<td>{self._expand_inline_macros(clean)}</td>')
            rows_html.append(f'<tr>{"".join(cells)}</tr>')

        return (
            f'\n<div class="table-wrapper">'
            f'<div class="table-caption">{html.escape(name)}</div>'
            f'<table>'
            f'<thead><tr>{"".join(ths)}</tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody>'
            f'</table>'
            f'</div>\n'
        )

    @staticmethod
    def _table_to_markdown(table, name):
        """Used when exporting a Grammar Table to an external .md file."""
        col_headers = table.get('col_headers', [])
        row_headers = table.get('row_headers', [])
        data = table.get('data', [])

        header_row = ([""] + list(col_headers)) if row_headers else list(col_headers)

        lines = [f"### {name}", ""]
        lines.append("| " + " | ".join(header_row) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_row)) + " |")

        for r_idx, row in enumerate(data):
            if row_headers:
                label = str(row_headers[r_idx]) if r_idx < len(row_headers) else ""
                row_label = [label]
            else:
                row_label = []

            clean_row = [str(c).replace('\n', ' ') for c in row]
            cells = row_label + clean_row
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines) + "\n\n"

    def _wrap_selection(self, prefix, suffix=None):
        suffix = suffix if suffix is not None else prefix
        cursor = self.editor.textCursor()

        if cursor.hasSelection():
            text = cursor.selectedText().replace('\u2029', '\n')
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(pos + len(prefix))
            self.editor.setTextCursor(cursor)

        self.editor.setFocus()

    def _insert_heading(self, level):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("#" * level + " ")
        self.editor.setFocus()

    def _insert_gloss_template(self):
        template = (
            "\n::: gloss Example Clause\n"
            "word1 word2\n"
            "stem1-affix stem2\n"
            "1SG.NOM verb.PST\n"
            "\"Free translation here.\"\n"
            ":::\n"
        )
        self.editor.insertPlainText(template)
        self.editor.setFocus()

    def _insert_callout(self, kind: str):
        titles = {
            "note": "Usage Note",
            "example": "Corpus Example",
            "rule": "Phonological Shift",
            "warning": "Irregular Form",
        }
        template = (
            f"\n::: {kind} {titles.get(kind, 'Note')}\n"
            f"Write your {kind} details here...\n"
            f":::\n"
        )
        self.editor.insertPlainText(template)
        self.editor.setFocus()

    def _toggle_bullet_list(self):
        cursor = self.editor.textCursor()

        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.insertText("- ")
            self.editor.setFocus()
            return

        doc = self.editor.document()
        start_block = doc.findBlock(cursor.selectionStart())
        end_block = doc.findBlock(cursor.selectionEnd())

        blocks = []
        block = start_block
        while block.isValid():
            blocks.append(block)
            if block == end_block:
                break
            block = block.next()

        edit_cursor = QTextCursor(doc)
        edit_cursor.beginEditBlock()

        for b in blocks:
            line_cursor = QTextCursor(b)
            line_cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            line_cursor.insertText("- ")

        edit_cursor.endEditBlock()
        self.editor.setFocus()

    def _init_ipa_picker(self):
        self.ipa_picker = IPAPickerPopup(self)
        self.ipa_picker.character_selected.connect(self._insert_ipa_character)
        QApplication.instance().installEventFilter(self)

    def _toggle_ipa_picker(self):
        if self.ipa_picker.isVisible():
            self.ipa_picker.hide()
            return

        button_pos = self.ipa_btn.mapToGlobal(QPoint(0, 0))
        popup_x = button_pos.x()
        popup_y = button_pos.y() + self.ipa_btn.height()
        self.ipa_picker.move(popup_x, popup_y)
        self.ipa_picker.show()

    def _insert_ipa_character(self, character):
        self.editor.insertPlainText(character)
        self.editor.setFocus()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and self.ipa_picker.isVisible():
            click_pos = event.globalPosition().toPoint()
            if not self.ipa_picker.geometry().contains(click_pos):
                btn_pos = self.ipa_btn.mapToGlobal(QPoint(0, 0))
                btn_rect = QRect(btn_pos, self.ipa_btn.size())
                if not btn_rect.contains(click_pos):
                    self.ipa_picker.hide()

        return super().eventFilter(obj, event)

    def _ensure_image_dir(self):
        if sys.platform == "win32":
            path = self.main_app.path.split('\\')
        else:
            path = self.main_app.path.split('/')

        for _ in range(2):
            try:
                path.remove('src')
            except ValueError:
                pass

        dest_dir = os.path.join('/'.join(path), "assets", "imported_images")
        os.makedirs(dest_dir, exist_ok=True)
        return dest_dir

    @staticmethod
    def _unique_filename(directory, filename):
        name, ext = os.path.splitext(filename)
        candidate = filename
        counter = 1

        while os.path.exists(os.path.join(directory, candidate)):
            candidate = f"{name}_{counter}{ext}"
            counter += 1

        return candidate

    def _insert_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if not file_path:
            return

        dest_dir = self._ensure_image_dir()
        dest_name = self._unique_filename(dest_dir, os.path.basename(file_path))
        shutil.copy2(file_path, os.path.join(dest_dir, dest_name))

        alt_text, ok = QInputDialog.getText(
            self, "Image Alt Text", "Enter a short description:",
            text=os.path.splitext(dest_name)[0]
        )
        if not ok or not alt_text.strip():
            alt_text = os.path.splitext(dest_name)[0]

        self.editor.insertPlainText(f"![{alt_text}]({dest_name})")

    def handle_clipboard_image(self, mime_data):
        """Called by GrammarEditor.insertFromMimeData on image paste."""
        image = mime_data.imageData()
        qimage = image if isinstance(image, QImage) else QImage(image)
        if qimage is None or qimage.isNull():
            return

        name, ok = QInputDialog.getText(self, "Name Pasted Image", "Enter a name for this image:")
        if not ok or not name.strip():
            return

        safe_name = re.sub(r'[^A-Za-z0-9_\-]+', '_', name.strip())
        dest_dir = self._ensure_image_dir()
        filename = self._unique_filename(dest_dir, f"{safe_name}.png")
        qimage.save(os.path.join(dest_dir, filename), "PNG")

        self.editor.insertPlainText(f"![{safe_name}]({filename})")

    def _open_gloss_dialog(self):
        dialog = GlossDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            gloss_text = dialog.get_markdown().strip()
            formatted_gloss = f"\n::: gloss\n{gloss_text}\n:::\n"
            self.editor.insertPlainText(formatted_gloss)

    def _insert_table_macro(self):
        table_names = sorted(self.main_app.grammar_data.get('tables', {}).keys())
        if not table_names:
            QMessageBox.information(self, "No Tables", "Create a grammar table first.")
            return

        name, ok = QInputDialog.getItem(self, "Insert Table", "Choose a table to embed:", table_names, 0, False)
        if ok and name:
            self.editor.insertPlainText(f"{{{{table:{name}}}}}")

    def update_grammar_table_listbox(self):
        self.table_listbox.clear()
        for table_name in sorted(self.main_app.grammar_data['tables'].keys()):
            # noinspection PyTypeChecker
            self.table_listbox.addItem(table_name)

    def load_table_into_editor(self):
        selected_items = self.table_listbox.selectedItems()

        self._loading_table = True
        self.table_editor.clear()
        self.table_editor.setRowCount(0)
        self.table_editor.setColumnCount(0)

        if not selected_items:
            self._loading_table = False
            return

        table_name = selected_items[0].text()
        table_data = self.main_app.grammar_data['tables'].get(table_name)

        if not table_data or not isinstance(table_data, dict):
            self._loading_table = False
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

        self._loading_table = False

    def _on_table_item_changed(self, _item):
        if self._loading_table:
            return
        self.table_autosave_timer.start()

    def _autosave_current_table(self):
        if self.table_listbox.selectedItems():
            self.save_grammar_table(silent=True)

    def save_grammar_table(self, silent=False):
        selected_items = self.table_listbox.selectedItems()
        if not selected_items:
            if not silent:
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

        self.main_app.grammar_data['tables'][table_name] = table_object
        self.main_app.save_grammar()

        if self.current_section_index is not None:
            self._update_preview(self.editor.toPlainText())

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

        self.main_app.grammar_data['tables'][table_name] = new_table
        self.main_app.save_grammar()

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
            del self.main_app.grammar_data['tables'][table_name]
            self.main_app.save_grammar()
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

        self.table_autosave_timer.start()

    def remove_table_row(self):
        current_row = self.table_editor.currentRow()
        if current_row != -1:
            self.table_editor.removeRow(current_row)
            for r in range(current_row, self.table_editor.rowCount()):
                self.table_editor.setVerticalHeaderItem(r, QTableWidgetItem(str(r + 1)))
            self.table_autosave_timer.start()

    def add_table_column(self):
        current_col = self.table_editor.currentColumn()
        if current_col == -1:
            current_col = self.table_editor.columnCount()

        self.table_editor.insertColumn(current_col)
        new_header = QTableWidgetItem(f"Header {current_col + 1}")
        self.table_editor.setHorizontalHeaderItem(current_col, new_header)

        for c in range(current_col + 1, self.table_editor.columnCount()):
            self.table_editor.setHorizontalHeaderItem(c, QTableWidgetItem(f"Header {c + 1}"))

        self.table_autosave_timer.start()

    def remove_table_column(self):
        current_col = self.table_editor.currentColumn()
        if current_col != -1:
            self.table_editor.removeColumn(current_col)
            for c in range(current_col, self.table_editor.columnCount()):
                self.table_editor.setHorizontalHeaderItem(c, QTableWidgetItem(f"Header {c + 1}"))
            self.table_autosave_timer.start()

    def edit_table_header(self, logical_index):
        sender = self.sender()

        if sender == self.table_editor.horizontalHeader():
            header_item = self.table_editor.horizontalHeaderItem(logical_index)
            old_text = header_item.text() if header_item else f"Header {logical_index + 1}"
            new_text, ok = QInputDialog.getText(self, "Edit Header", "Enter new column header:", text=old_text)
            if ok and new_text:
                self.table_editor.setHorizontalHeaderItem(logical_index, QTableWidgetItem(new_text))
                self.table_autosave_timer.start()

        elif sender == self.table_editor.verticalHeader():
            header_item = self.table_editor.verticalHeaderItem(logical_index)
            old_text = header_item.text() if header_item else str(logical_index + 1)
            new_text, ok = QInputDialog.getText(self, "Edit Header", "Enter new row header:", text=old_text)
            if ok and new_text:
                self.table_editor.setVerticalHeaderItem(logical_index, QTableWidgetItem(new_text))
                self.table_autosave_timer.start()

    def export_table_csv(self):
        selected_items = self.table_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Table Selected", "Please select a table to export.")
            return

        table_name = selected_items[0].text()
        table_data = self.main_app.grammar_data['tables'].get(table_name)
        if not table_data:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Table", f"{table_name}.csv", "CSV Files (*.csv);;Markdown Files (*.md)"
        )
        if not file_path:
            return

        row_headers = table_data.get("row_headers", [])
        col_headers = table_data.get("col_headers", [])
        data = table_data.get("data", [])

        try:
            if file_path.lower().endswith(".md"):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self._table_to_markdown(table_data, table_name))
            else:
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    header_row = ([""] + list(col_headers)) if row_headers else list(col_headers)
                    writer.writerow(header_row)
                    for r_idx, row in enumerate(data):
                        row_label = [row_headers[r_idx]] if row_headers and r_idx < len(row_headers) else []
                        writer.writerow(row_label + row)
        except OSError as e:
            QMessageBox.critical(self, "Export Failed", f"Could not write file: {e}")
            return

        QMessageBox.information(self, "Exported", f"Table '{table_name}' exported.")

    def import_table_csv(self):
        selected_items = self.table_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Table Selected", "Please select a table to import into.")
            return

        table_name = selected_items[0].text()
        file_path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        except OSError as e:
            QMessageBox.critical(self, "Import Failed", f"Could not read file: {e}")
            return

        if not rows:
            QMessageBox.warning(self, "Empty File", "The selected CSV file is empty.")
            return

        has_row_headers = bool(rows[0]) and rows[0][0] == ""
        col_headers = rows[0][1:] if has_row_headers else rows[0]

        new_row_headers = []
        new_data = []
        for row in rows[1:]:
            if not row:
                continue
            if has_row_headers:
                new_row_headers.append(row[0])
                new_data.append(row[1:])
            else:
                new_row_headers.append(str(len(new_data) + 1))
                new_data.append(row)

        num_cols = len(col_headers)
        for row in new_data:
            if len(row) < num_cols:
                row.extend([""] * (num_cols - len(row)))

        self.main_app.grammar_data['tables'][table_name] = {
            "data": new_data,
            "row_headers": new_row_headers,
            "col_headers": col_headers
        }
        self.main_app.save_grammar()

        items = self.table_listbox.findItems(table_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.table_listbox.setCurrentItem(items[0])
        else:
            self.load_table_into_editor()

        QMessageBox.information(self, "Imported", f"Table '{table_name}' updated from CSV.")

    def insert_table_into_section(self):
        selected_items = self.table_listbox.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Table Selected", "Please select a table to insert.")
            return
        if self.current_section_index is None:
            QMessageBox.warning(self, "No Chapter Selected", "Please select a chapter to insert into.")
            return

        table_name = selected_items[0].text()
        cursor = self.editor.textCursor()
        cursor.insertText(f"\n{{{{table:{table_name}}}}}\n")

    def update_theme(self, is_dark_mode: bool):
        self.is_dark_mode = is_dark_mode
        if hasattr(self, "highlighter"):
            self.highlighter.set_theme(is_dark_mode)

        if self.current_section_index is not None:
            text = self.editor.toPlainText()
            self._update_preview(text)

    def _show_syntax_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("ConlangMark & Syntax Guide")
        dialog.resize(580, 540)
        layout = QVBoxLayout(dialog)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)

        help_html = """
        <h2 style="margin-bottom: 4px;">ConlangMark Reference Guide</h2>
        <hr>
        <p><b>Standard Markdown:</b> <code># H1</code>, <code>## H2</code>, <code>**bold**</code>,
        <code>*italic*</code>, <code>- bullet list</code>, <code>&gt; blockquote</code></p>

        <h3>Inline Linguistic Macros</h3>
        <ul>
            <li><b>Conlang Script:</b> <code>{{f:text}}</code> — Renders text in your custom conlang font.</li>
            <li><b>IPA Transcription:</b> <code>{{ipa:/kaltxɪ/}}</code> — Styled phonetic badge with IPA font stack.</li>
            <li><b>Small Caps Tag:</b> <code>{{sc:erg}}</code> — Renders grammatical labels in small caps.</li>
            <li><b>Sound Change Rule:</b> <code>{{rule:a &gt; e / _ i}}</code> — Formats phonological shift rules.</li>
            <li><b>Embed Grammar Table:</b> <code>{{table:TableName}}</code> — Live-embeds a table from below.</li>
        </ul>

        <h3>Auto-Aligned Interlinear Glosses</h3>
        <pre style="padding:8px; border-radius:4px;">::: gloss Example Clause
kaltxì ma frapo
kaltxì ma fra-po
hello VOC all-person
"Hello, everyone!"
:::</pre>
        <p><i>Words align automatically column-by-column, and uppercase tags like <code>VOC</code>, <code>1SG</code>, or <code>NOM</code> render in small caps.</i></p>

        <h3>Callout Boxes</h3>
        <pre style="padding:8px; border-radius:4px;">::: note Historical Note
Final vowels were dropped in unstressed syllables.
:::</pre>
        <p><i>Supported types: <code>::: note</code>, <code>::: example</code>, <code>::: rule</code>, <code>::: warning</code>.</i></p>
        """
        browser.setHtml(help_html)
        layout.addWidget(browser)

        close_btn = QPushButton("Close Guide")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()
