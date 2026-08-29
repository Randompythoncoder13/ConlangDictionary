import os
import re
import csv
import json
import uuid
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit, QTextBrowser,
    QPushButton, QToolButton, QListWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QSplitter, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QFileDialog, QMenu, QApplication
)
from PySide6.QtGui import QTextCursor, QFont, QAction, QImage
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QEvent, QUrl

from custom_widgets import IPAPickerPopup

TABLE_MACRO_RE = re.compile(r"\{\{table:([^}]+)\}\}")
DEFAULT_CHAPTERS = ["Phonology", "Morphology", "Syntax"]


def _load_sections(main_app):
    """Load structured chapters from grammar_data['rules'], migrating legacy
    plain-text rules into a single 'General' chapter on first read."""
    raw = main_app.grammar_data.get('rules', '')

    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                sections = parsed.get('sections')
                if isinstance(sections, list) and sections:
                    # Defensive normalization in case of malformed entries
                    clean = []
                    for s in sections:
                        if isinstance(s, dict) and 'title' in s:
                            clean.append({
                                "id": s.get("id") or str(uuid.uuid4()),
                                "title": s["title"],
                                "content": s.get("content", "")
                            })
                    if clean:
                        return clean
        except (json.JSONDecodeError, TypeError):
            pass  # Not JSON -> legacy plain string

    legacy_text = raw if isinstance(raw, str) else ""
    return [{"id": str(uuid.uuid4()), "title": "General", "content": legacy_text}]


class GrammarEditor(QTextEdit):
    """Plain-text Markdown editor. Intercepts image paste from the clipboard
    and forces plain-text paste for regular text (so rich text/HTML from
    other apps doesn't pollute the Markdown source)."""

    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self.tab = tab
        self.setAcceptRichText(False)

    def insertFromMimeData(self, source):
        if source.hasImage():
            self.tab.handle_clipboard_image(source)
            return
        if source.hasText():
            self.insertPlainText(source.text())
            return
        super().insertFromMimeData(source)


class GlossDialog(QDialog):
    """Modal for building a Leipzig-style interlinear gloss block."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Interlinear Gloss Builder")
        self.setMinimumWidth(440)

        layout = QFormLayout(self)

        self.original_edit = QLineEdit()
        self.morphemes_edit = QLineEdit()
        self.gloss_edit = QLineEdit()
        self.translation_edit = QLineEdit()

        layout.addRow("Original Text:", self.original_edit)
        layout.addRow("Morphemes:", self.morphemes_edit)
        layout.addRow("Gloss:", self.gloss_edit)
        layout.addRow("Free Translation:", self.translation_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_markdown(self):
        original = self.original_edit.text().strip()
        morphemes = self.morphemes_edit.text().strip()
        gloss = self.gloss_edit.text().strip()
        translation = self.translation_edit.text().strip()

        return self.get_aligned_gloss(original, morphemes, gloss, translation)

    def get_aligned_gloss(self, line1, line2, line3, line4_translation):
        # Split the first three lines into tokens
        tokens1 = line1.split()
        tokens2 = line2.split()
        tokens3 = line3.split()

        # Ensure they all have the same number of words
        if not (len(tokens1) == len(tokens2) == len(tokens3)):
            raise ValueError("The first three lines must have the same number of space-separated words.")

        aligned_1, aligned_2, aligned_3 = "", "", ""

        # Calculate the max width for each column and pad accordingly
        for t1, t2, t3 in zip(tokens1, tokens2, tokens3):
            col_width = max(len(t1), len(t2), len(t3)) + 1  # +1 for spacing

            aligned_1 += t1.ljust(col_width)
            aligned_2 += t2.ljust(col_width)
            aligned_3 += t3.ljust(col_width)

        # Print the aligned lines plus the free translation
        return f"{aligned_1}\n\n{aligned_2}\n\n{aligned_3}\n\n{line4_translation}\n\n"


class GrammarTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        self._loading = False
        self._loading_table = False
        self.current_section_index = None
        self.sections = _load_sections(main_app)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(1200)
        self.autosave_timer.timeout.connect(self._autosave_rules)

        self.table_autosave_timer = QTimer(self)
        self.table_autosave_timer.setSingleShot(True)
        self.table_autosave_timer.setInterval(1200)
        self.table_autosave_timer.timeout.connect(self._autosave_current_table)

        self._build_ui()
        self._populate_section_list()
        self.update_grammar_table_listbox()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        outer_layout.addWidget(main_splitter)

        main_splitter.addWidget(self._build_editor_frame())
        main_splitter.addWidget(self._build_tables_pane())
        main_splitter.setSizes([500, 350])

        self._init_ipa_picker()

    def _build_editor_frame(self):
        editor_frame = QWidget()
        editor_h_layout = QHBoxLayout(editor_frame)

        sections_pane = self._build_sections_pane()
        sections_pane.setMaximumWidth(220)
        editor_h_layout.addWidget(sections_pane)

        editor_pane = QWidget()
        editor_v_layout = QVBoxLayout(editor_pane)
        editor_v_layout.addLayout(self._build_toolbar())

        editor_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.editor = GrammarEditor(self)
        self.editor.setStyleSheet("QTextEdit { background-color: palette(base); }")
        if getattr(self.main_app, "custom_font", None):
            self.editor.setFont(self.main_app.custom_font)
        self.editor.textChanged.connect(self._on_editor_text_changed)

        self.preview = QTextBrowser()
        self.preview.setStyleSheet("QTextBrowser { background-color: palette(base); }")
        self.preview.setOpenExternalLinks(True)
        images_dir = self._ensure_image_dir()
        self.preview.document().setBaseUrl(QUrl.fromLocalFile(images_dir + os.sep))

        editor_splitter.addWidget(self.editor)
        editor_splitter.addWidget(self.preview)
        editor_splitter.setSizes([420, 420])

        editor_v_layout.addWidget(editor_splitter)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_now_btn = QPushButton("Save Chapter Now")
        save_now_btn.clicked.connect(self.save_grammar_rules)
        save_row.addWidget(save_now_btn)
        editor_v_layout.addLayout(save_row)

        editor_h_layout.addWidget(editor_pane, 1)
        return editor_frame

    def _build_sections_pane(self):
        frame = QGroupBox("Chapters")
        layout = QVBoxLayout(frame)

        self.section_list = QListWidget()
        self.section_list.currentRowChanged.connect(self._on_section_selected)
        layout.addWidget(self.section_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_section)
        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self._rename_section)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_section)
        for b in (add_btn, rename_btn, delete_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        return frame

    def _build_toolbar(self):
        layout = QHBoxLayout()

        heading_btn = QToolButton()
        heading_btn.setText("Heading ")
        heading_menu = QMenu(heading_btn)
        for level in (1, 2, 3):
            action = QAction(f"Heading {level}", self)
            action.triggered.connect(lambda checked=False, lvl=level: self._insert_heading(lvl))
            heading_menu.addAction(action)
        heading_btn.setMenu(heading_menu)
        heading_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        layout.addWidget(heading_btn)

        bold_btn = QPushButton("B")
        bold_font = QFont()
        bold_font.setBold(True)
        bold_btn.setFont(bold_font)
        bold_btn.setFixedWidth(32)
        bold_btn.clicked.connect(lambda: self._wrap_selection("**"))
        layout.addWidget(bold_btn)

        italic_btn = QPushButton("I")
        italic_font = QFont()
        italic_font.setItalic(True)
        italic_btn.setFont(italic_font)
        italic_btn.setFixedWidth(32)
        italic_btn.clicked.connect(lambda: self._wrap_selection("*"))
        layout.addWidget(italic_btn)

        bullet_btn = QPushButton("\u2022 List")
        bullet_btn.clicked.connect(self._toggle_bullet_list)
        layout.addWidget(bullet_btn)

        layout.addSpacing(12)

        self.ipa_btn = QPushButton("IPA")
        self.ipa_btn.clicked.connect(self._toggle_ipa_picker)
        layout.addWidget(self.ipa_btn)

        image_btn = QPushButton("Insert Image")
        image_btn.clicked.connect(self._insert_image)
        layout.addWidget(image_btn)

        gloss_btn = QPushButton("Gloss Builder")
        gloss_btn.clicked.connect(self._open_gloss_dialog)
        layout.addWidget(gloss_btn)

        table_macro_btn = QPushButton("Insert Table")
        table_macro_btn.clicked.connect(self._insert_table_macro)
        layout.addWidget(table_macro_btn)

        layout.addStretch()
        return layout

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

    # ------------------------------------------------------------------ #
    # Chapter (section) management
    # ------------------------------------------------------------------ #
    def load_grammar_rules(self):
        """Reload chapters from main_app.grammar_data (e.g. on tab activation)."""
        keep_index = self.current_section_index or 0
        self.sections = _load_sections(self.main_app)
        self._populate_section_list(select_index=keep_index)

    def save_grammar_rules(self):
        self.autosave_timer.stop()
        self._persist_sections()
        QMessageBox.information(self, "Success", "Grammar chapter saved.")

    def _persist_sections(self):
        payload = json.dumps({"sections": self.sections})
        self.main_app.grammar_data['rules'] = payload
        self.main_app.save_grammar()

    def _autosave_rules(self):
        self._persist_sections()

    def _populate_section_list(self, select_index=0):
        self._loading = True
        self.section_list.clear()
        for section in self.sections:
            self.section_list.addItem(section['title'])
        self._loading = False

        if self.sections:
            select_index = max(0, min(select_index, len(self.sections) - 1))
            self.section_list.setCurrentRow(select_index)

    def _on_section_selected(self, row):
        if row < 0 or row >= len(self.sections):
            self.current_section_index = None
            return

        self.current_section_index = row
        content = self.sections[row].get('content', '')

        self._loading = True
        self.editor.setPlainText(content)
        self._loading = False

        self._update_preview(content)

    def _add_section(self):
        title, ok = QInputDialog.getText(self, "New Chapter", "Chapter title:")
        if not ok or not title.strip():
            return
        title = title.strip()

        if any(s['title'] == title for s in self.sections):
            QMessageBox.warning(self, "Duplicate", f"A chapter named '{title}' already exists.")
            return

        self.sections.append({"id": str(uuid.uuid4()), "title": title, "content": ""})
        self._persist_sections()
        self._populate_section_list(select_index=len(self.sections) - 1)

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

    # ------------------------------------------------------------------ #
    # Editor <-> preview
    # ------------------------------------------------------------------ #
    def _on_editor_text_changed(self):
        if self._loading or self.current_section_index is None:
            return

        text = self.editor.toPlainText()
        self.sections[self.current_section_index]['content'] = text
        self._update_preview(text)
        self.autosave_timer.start()

    def _update_preview(self, markdown_text):
        rendered = self._expand_table_macros(markdown_text)
        self.preview.setMarkdown(rendered)

    def _expand_table_macros(self, text):
        def replace(match):
            name = match.group(1).strip()
            table = self.main_app.grammar_data.get('tables', {}).get(name)
            if not table:
                return f"*[Missing table: {name}]*"
            return self._table_to_markdown(table, name)
        return TABLE_MACRO_RE.sub(replace, text)

    @staticmethod
    def _table_to_markdown(table, name):
        col_headers = table.get('col_headers', [])
        row_headers = table.get('row_headers', [])
        data = table.get('data', [])

        header_row = ([""] + list(col_headers)) if row_headers else list(col_headers)
        lines = [f"**{name}**", ""]
        lines.append("| " + " | ".join(header_row) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_row)) + " |")

        for r_idx, row in enumerate(data):
            row_label = [row_headers[r_idx]] if row_headers and r_idx < len(row_headers) else []
            cells = row_label + [str(c) for c in row]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------ #
    # Formatting toolbar actions
    # ------------------------------------------------------------------ #
    def _wrap_selection(self, prefix, suffix=None):
        suffix = suffix if suffix is not None else prefix
        cursor = self.editor.textCursor()

        if cursor.hasSelection():
            start, end = cursor.selectionStart(), cursor.selectionEnd()
            text = self.editor.toPlainText()[start:end]
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{suffix}")
            cursor.setPosition(pos + len(prefix))
            self.editor.setTextCursor(cursor)

    def _insert_heading(self, level):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("#" * level + " ")

    def _toggle_bullet_list(self):
        cursor = self.editor.textCursor()

        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cursor.insertText("- ")
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

    # ------------------------------------------------------------------ #
    # IPA picker (mirrors IPALineEdit's show/hide-on-click-away pattern)
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Image handling (file insert + clipboard paste)
    # ------------------------------------------------------------------ #
    def _ensure_image_dir(self):
        dest_dir = os.path.join(self.main_app.path, "assets", "imported_images")
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

    # ------------------------------------------------------------------ #
    # Interlinear gloss + table macro
    # ------------------------------------------------------------------ #
    def _open_gloss_dialog(self):
        dialog = GlossDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.editor.insertPlainText("\n" + dialog.get_markdown() + "\n")

    def _insert_table_macro(self):
        table_names = sorted(self.main_app.grammar_data.get('tables', {}).keys())
        if not table_names:
            QMessageBox.information(self, "No Tables", "Create a grammar table first.")
            return

        name, ok = QInputDialog.getItem(self, "Insert Table", "Choose a table to embed:", table_names, 0, False)
        if ok and name:
            self.editor.insertPlainText(f"{{{{table:{name}}}}}")

    # ------------------------------------------------------------------ #
    # Grammar table CRUD (retained + extended from the original tab)
    # ------------------------------------------------------------------ #
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

        if not silent:
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

    # ------------------------------------------------------------------ #
    # Table export / import / insert-into-chapter
    # ------------------------------------------------------------------ #
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
