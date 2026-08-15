from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit, QPushButton, QListWidget, QTableWidget,
    QTableWidgetItem, QMessageBox, QInputDialog, QSplitter
)
from PySide6.QtCore import Qt


class GrammarTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        layout = QHBoxLayout(self)
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
        self.table_editor.setStyleSheet("QTableWidget { background-color: palette(base); }")
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

    def load_grammar_rules(self):
        self.grammar_rules_text.setText(self.main_app.grammar_data.get('rules', ''))

    def save_grammar_rules(self):
        self.main_app.grammar_data['rules'] = self.grammar_rules_text.toPlainText().strip()
        self.main_app.save_grammar()
        QMessageBox.information(self, "Success", "Grammar rules saved.")

    def update_grammar_table_listbox(self):
        self.table_listbox.clear()
        for table_name in sorted(self.main_app.grammar_data['tables'].keys()):
            # noinspection PyTypeChecker
            self.table_listbox.addItem(table_name)

    def load_table_into_editor(self):
        selected_items = self.table_listbox.selectedItems()

        self.table_editor.clear()
        self.table_editor.setRowCount(0)
        self.table_editor.setColumnCount(0)

        if not selected_items:
            return

        table_name = selected_items[0].text()
        table_data = self.main_app.grammar_data['tables'].get(table_name)

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

        self.main_app.grammar_data['tables'][table_name] = table_object
        self.main_app.save_grammar()
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
