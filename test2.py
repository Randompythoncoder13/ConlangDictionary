import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QLineEdit, QPushButton, QListWidget,
    QLabel, QSplitter, QGroupBox, QScrollArea
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QSize, QPoint

# --- Constants ---
GRID_WIDTH = 16
GRID_HEIGHT = 16
EDITOR_CELL_SIZE = 25  # Size of each cell in the editor
PREVIEW_CELL_SIZE = 3  # Size of each pixel in the preview
GLYPH_SPACING = PREVIEW_CELL_SIZE * 2  # Space between characters in preview


class GlyphEditor(QWidget):
    """A widget for drawing a single glyph on a grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_data = [[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        # Set a fixed size based on grid dimensions and cell size
        self.setFixedSize(GRID_WIDTH * EDITOR_CELL_SIZE, GRID_HEIGHT * EDITOR_CELL_SIZE)

        self.drawing_state = None  # None, True (drawing), or False (erasing)
        self.setMouseTracking(True)  # Track mouse even when button isn't pressed

    def paintEvent(self, event):
        """Renders the grid and the glyph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- Draw the grid ---
        grid_pen = QPen(QColor(220, 220, 220), 1, Qt.SolidLine)
        painter.setPen(grid_pen)

        for x in range(GRID_WIDTH + 1):
            x_pos = x * EDITOR_CELL_SIZE
            painter.drawLine(x_pos, 0, x_pos, self.height())
        for y in range(GRID_HEIGHT + 1):
            y_pos = y * EDITOR_CELL_SIZE
            painter.drawLine(0, y_pos, self.width(), y_pos)

        # --- Draw the active pixels ---
        pixel_brush = QBrush(QColor(30, 30, 30))
        painter.setPen(Qt.NoPen)

        for y, row in enumerate(self.grid_data):
            for x, pixel_on in enumerate(row):
                if pixel_on:
                    painter.setBrush(pixel_brush)
                    painter.drawRect(
                        x * EDITOR_CELL_SIZE,
                        y * EDITOR_CELL_SIZE,
                        EDITOR_CELL_SIZE,
                        EDITOR_CELL_SIZE
                    )

    def _handle_mouse_event(self, event):
        """Helper function to handle both press and move events."""
        pos = event.position()
        x = int(pos.x() // EDITOR_CELL_SIZE)
        y = int(pos.y() // EDITOR_CELL_SIZE)

        # Check if the click is within the grid bounds
        if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
            if self.drawing_state is not None:
                if self.grid_data[y][x] != self.drawing_state:
                    self.grid_data[y][x] = self.drawing_state
                    self.update()  # Request a repaint

    def mousePressEvent(self, event):
        """Handles the start of a drawing or erasing action."""
        if event.button() == Qt.LeftButton:
            self.drawing_state = True
        elif event.button() == Qt.RightButton:
            self.drawing_state = False
        self._handle_mouse_event(event)

    def mouseMoveEvent(self, event):
        """Handles drawing or erasing while dragging the mouse."""
        self._handle_mouse_event(event)

    def mouseReleaseEvent(self, event):
        """Stops the drawing/erasing action."""
        self.drawing_state = None

    def get_data(self):
        """Returns the current glyph data."""
        # Return a deep copy
        return [row[:] for row in self.grid_data]

    def set_data(self, data):
        """Sets the editor's grid data from an external source."""
        if data and len(data) == GRID_HEIGHT and len(data[0]) == GRID_WIDTH:
            self.grid_data = [row[:] for row in data]
            self.update()

    def clear_grid(self):
        """Resets the grid to be empty."""
        self.grid_data = [[False for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.update()


class FontPreview(QWidget):
    """A widget to render text using the custom font."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_to_render = ""
        self.font_data = {}
        self.setMinimumHeight(GRID_HEIGHT * PREVIEW_CELL_SIZE + 20)
        self.setMinimumWidth(2000)  # Start with a wide area for the scrollbar

    def update_font(self, font_data):
        """Updates the font dictionary used for rendering."""
        self.font_data = font_data
        # Sort keys by length, descending, to match "th" before "t"
        self.sorted_keys = sorted(self.font_data.keys(), key=len, reverse=True)
        self.update()

    def set_text(self, text):
        """Sets the text to be rendered."""
        self.text_to_render = text
        self.update()

    def paintEvent(self, event):
        """Renders the text using the custom glyphs."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pixel_brush = QBrush(QColor(30, 30, 30))
        missing_pen = QPen(QColor(255, 0, 0), 1, Qt.DashLine)

        x_offset = 10  # Start with some padding
        y_offset = 10

        i = 0
        text = self.text_to_render

        while i < len(text):
            found_match = False
            for key in self.sorted_keys:
                if text[i:].startswith(key):
                    # Found a glyph
                    glyph_data = self.font_data[key]
                    self._draw_glyph(painter, x_offset, y_offset, glyph_data, pixel_brush)

                    x_offset += (GRID_WIDTH * PREVIEW_CELL_SIZE) + GLYPH_SPACING
                    i += len(key)
                    found_match = True
                    break

            if not found_match:
                # No glyph found for this character
                self._draw_missing_glyph_placeholder(painter, x_offset, y_offset, missing_pen)
                x_offset += (GRID_WIDTH * PREVIEW_CELL_SIZE) + GLYPH_SPACING
                i += 1

        # Update the minimum width to match the rendered text
        if x_offset > self.minimumWidth():
            self.setMinimumWidth(x_offset)

    def _draw_glyph(self, painter, x, y, data, brush):
        """Helper to draw a single glyph."""
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        for r, row in enumerate(data):
            for c, pixel_on in enumerate(row):
                if pixel_on:
                    painter.drawRect(
                        x + (c * PREVIEW_CELL_SIZE),
                        y + (r * PREVIEW_CELL_SIZE),
                        PREVIEW_CELL_SIZE,
                        PREVIEW_CELL_SIZE
                    )

    def _draw_missing_glyph_placeholder(self, painter, x, y, pen):
        """Helper to draw a box for a missing character."""
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        painter.drawRect(
            x, y,
            GRID_WIDTH * PREVIEW_CELL_SIZE,
            GRID_HEIGHT * PREVIEW_CELL_SIZE
        )
        # Draw a '?'
        painter.drawText(
            x + (GRID_WIDTH * PREVIEW_CELL_SIZE) // 4,
            y + (GRID_HEIGHT * PREVIEW_CELL_SIZE) // 2 + 5,
            "?"
        )


class MainWindow(QMainWindow):
    """The main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bitmap Font Maker")
        self.setGeometry(100, 100, 1000, 700)

        # This is the central data store for our font
        self.font_data = {}

        # --- Main Layout ---
        # Use a splitter to make editor and controls resizable
        self.main_splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(self.main_splitter)

        # --- Left Pane: Glyph Editor ---
        editor_container = QFrame(self)
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setAlignment(Qt.AlignCenter)

        self.editor = GlyphEditor(self)
        editor_layout.addWidget(self.editor)

        self.main_splitter.addWidget(editor_container)

        # --- Right Pane: Controls and Preview ---
        right_pane = QWidget(self)
        right_layout = QVBoxLayout(right_pane)

        # --- Group 1: Glyph Management ---
        manage_group = QGroupBox("Glyph Management")
        manage_layout = QVBoxLayout()

        self.glyph_list = QListWidget(self)
        self.glyph_list.setToolTip("Select a saved glyph to edit it.")
        manage_layout.addWidget(self.glyph_list)

        self.char_input = QLineEdit(self)
        self.char_input.setPlaceholderText("Enter character(s) (e.g., 'a' or 'th')")
        self.char_input.setToolTip("The character or sequence this glyph represents.")
        manage_layout.addWidget(self.char_input)

        button_layout = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.new_button.setToolTip("Clear the editor for a new glyph.")
        self.save_button = QPushButton("Save Glyph")
        self.save_button.setToolTip("Save the current drawing to the library.")
        self.delete_button = QPushButton("Delete")
        self.delete_button.setToolTip("Delete the selected glyph.")

        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.delete_button)
        manage_layout.addLayout(button_layout)

        manage_group.setLayout(manage_layout)
        right_layout.addWidget(manage_group)

        # --- Group 2: Font Preview ---
        preview_group = QGroupBox("Font Preview")
        preview_layout = QVBoxLayout()

        self.preview_input = QLineEdit(self)
        self.preview_input.setPlaceholderText("Type here to preview your font...")
        preview_layout.addWidget(self.preview_input)

        # --- Scroll Area for Preview ---
        self.preview_scroll_area = QScrollArea(self)
        self.preview_scroll_area.setWidgetResizable(True)
        self.preview_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.preview_widget = FontPreview(self)
        self.preview_scroll_area.setWidget(self.preview_widget)
        self.preview_scroll_area.setMinimumHeight(GRID_HEIGHT * PREVIEW_CELL_SIZE + 40)

        preview_layout.addWidget(self.preview_scroll_area)
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)

        right_pane.setLayout(right_layout)
        self.main_splitter.addWidget(right_pane)

        # Set initial sizes for the splitter
        self.main_splitter.setSizes([600, 400])

        # --- Connect Signals and Slots ---
        self.connect_signals()

    def connect_signals(self):
        """Connect all UI elements to their functions."""
        self.new_button.clicked.connect(self.clear_for_new)
        self.save_button.clicked.connect(self.save_glyph)
        self.delete_button.clicked.connect(self.delete_glyph)
        self.glyph_list.currentItemChanged.connect(self.load_glyph)
        self.preview_input.textChanged.connect(self.preview_widget.set_text)

    def clear_for_new(self):
        """Clears the editor and inputs for a new glyph."""
        self.editor.clear_grid()
        self.char_input.clear()
        self.glyph_list.clearSelection()

    def save_glyph(self):
        """Saves the current glyph data to the font dictionary."""
        char_key = self.char_input.text()
        if not char_key:
            print("Please enter a character key (e.g., 'a') to save.")  # Later, show this in a status bar
            return

        self.font_data[char_key] = self.editor.get_data()
        self.update_glyph_list()

        # Set the just-saved item as the current one
        items = self.glyph_list.findItems(char_key, Qt.MatchExactly)
        if items:
            self.glyph_list.setCurrentItem(items[0])

        # Update the preview widget's font data
        self.preview_widget.update_font(self.font_data)

    def delete_glyph(self):
        """Deletes the currently selected glyph."""
        current_item = self.glyph_list.currentItem()
        if not current_item:
            return

        char_key = current_item.text()
        if char_key in self.font_data:
            del self.font_data[char_key]

        self.update_glyph_list()
        self.clear_for_new()
        self.preview_widget.update_font(self.font_data)

    def load_glyph(self, current_item, previous_item):
        """Loads a saved glyph into the editor when selected from the list."""
        if not current_item:
            return

        char_key = current_item.text()
        if char_key in self.font_data:
            glyph_data = self.font_data[char_key]
            self.editor.set_data(glyph_data)
            self.char_input.setText(char_key)

    def update_glyph_list(self):
        """Refreshes the QListWidget with the keys from the font_data."""
        self.glyph_list.blockSignals(True)  # Prevent load_glyph from firing

        self.glyph_list.clear()
        sorted_keys = sorted(self.font_data.keys())
        self.glyph_list.addItems(sorted_keys)

        self.glyph_list.blockSignals(False)


# --- Main execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())