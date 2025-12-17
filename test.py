"""
Pixel Font Maker
A simple application built with PySide6 to create, map, and test pixel-based fonts.

This single-file application includes:
1.  PixelEditor: A custom widget for drawing 16x16 pixel glyphs.
2.  FontRenderer: A custom widget to display text rendered with the custom font.
3.  MainWindow: The main application window that connects everything.
"""

import sys
import copy
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QTextEdit, QScrollArea,
)
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QPaintEvent, QMouseEvent
from PySide6.QtCore import Qt, QSize, QRect, Signal, QPoint

# --- Configuration ---
GRID_SIZE = 16  # The dimension for the pixel font (e.g., 16x16)

class PixelEditor(QWidget):
    """
    A custom widget that provides a clickable/drawable grid for editing a single glyph.
    """
    # Signal emitted when the grid is modified by the user
    gridChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize an empty grid
        self.grid_data = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self._cell_size = QSize(0, 0)

        # Set a reasonable minimum size
        self.setMinimumSize(300, 300)

        # Mouse tracking state
        self._is_drawing = False
        self._draw_mode = 1  # 1 for drawing (black), 0 for erasing (white)

        # Set a dark frame for visual separation
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setLineWidth(2)

    def setFrameStyle(self, style):
        """Helper to set QFrame-like properties on a QWidget."""
        self.setProperty("frameStyle", style)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def setLineWidth(self, width):
        """Helper to set QFrame-like properties on a QWidget."""
        self.setProperty("lineWidth", width)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _update_cell_size(self):
        """Recalculates the size of each grid cell based on widget size."""
        if GRID_SIZE == 0:
            self._cell_size = QSize(0, 0)
            return

        width = self.width() - (2 * self.width())
        height = self.height() - (2 * self.width())

        cell_w = width / GRID_SIZE
        cell_h = height / GRID_SIZE

        # Use the smaller dimension to maintain square pixels
        min_dim = min(cell_w, cell_h)
        self._cell_size = QSize(int(min_dim), int(min_dim))

    def get_grid_data(self) -> list[list[int]]:
        """Returns a deep copy of the current grid data."""
        return copy.deepcopy(self.grid_data)[::-1]

    def set_grid_data(self, data: list[list[int]]):
        """
        Sets the grid data from an external source (e.g., loading a saved glyph).
        """
        if data and len(data) == GRID_SIZE and len(data[0]) == GRID_SIZE:
            self.grid_data = copy.deepcopy(data)[::-1]
        else:
            self.clear_grid()
        self.update() # Trigger a repaint

    def clear_grid(self):
        """Resets the grid to be completely empty (all 0s)."""
        self.grid_data = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.update()
        self.gridChanged.emit() # Notify that grid was cleared

    def paintEvent(self, event: QPaintEvent):
        """Handles drawing the grid, cells, and border."""
        super().paintEvent(event) # Handle frame drawing

        painter = QPainter(self)

        # Get content rect (inside the frame)
        content_rect = self.contentsRect()
        painter.translate(content_rect.topLeft())

        self._update_cell_size()

        if self._cell_size.width() == 0 or self._cell_size.height() == 0:
            return

        total_grid_width = self._cell_size.width() * GRID_SIZE
        total_grid_height = self._cell_size.height() * GRID_SIZE

        # Center the grid within the content rect
        offset_x = (content_rect.width() - total_grid_width) // 2
        offset_y = (content_rect.height() - total_grid_height) // 2
        painter.translate(offset_x, offset_y)

        # --- Draw Cells ---
        painter.setPen(Qt.NoPen)
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid_data[y][x] == 1:
                    painter.setBrush(Qt.black)
                else:
                    painter.setBrush(Qt.white)

                painter.drawRect(
                    x * self._cell_size.width(),
                    y * self._cell_size.height(),
                    self._cell_size.width(),
                    self._cell_size.height()
                )

        # --- Draw Grid Lines ---
        painter.setPen(Qt.lightGray)
        painter.setBrush(Qt.NoBrush)

        # Vertical lines
        for x in range(GRID_SIZE + 1):
            x_pos = x * self._cell_size.width()
            painter.drawLine(x_pos, 0, x_pos, total_grid_height)

        # Horizontal lines
        for y in range(GRID_SIZE + 1):
            y_pos = y * self._cell_size.height()
            painter.drawLine(0, y_pos, total_grid_width, y_pos)

    def _get_cell_from_pos(self, pos: QPoint) -> tuple[int, int] | None:
        """Converts a mouse position to grid (x, y) coordinates."""
        if self._cell_size.width() == 0 or self._cell_size.height() == 0:
            return None

        # Adjust for frame
        content_rect = self.contentsRect()
        local_pos = pos - content_rect.topLeft()

        # Adjust for centering
        total_grid_width = self._cell_size.width() * GRID_SIZE
        total_grid_height = self._cell_size.height() * GRID_SIZE
        offset_x = (content_rect.width() - total_grid_width) // 2
        offset_y = (content_rect.height() - total_grid_height) // 2

        grid_pos = local_pos - QPoint(offset_x, offset_y)

        x = grid_pos.x() // self._cell_size.width()
        y = grid_pos.y() // self._cell_size.height()

        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            return (x, y)
        return None

    def _update_cell(self, pos: QPoint):
        """Updates a single cell's data based on position and draw mode."""
        cell = self._get_cell_from_pos(pos)
        if cell:
            x, y = cell
            if self.grid_data[y][x] != self._draw_mode:
                self.grid_data[y][x] = self._draw_mode
                self.update() # Repaint
                self.gridChanged.emit() # Notify of change

    def mousePressEvent(self, event: QMouseEvent):
        """Handles starting a draw or erase action."""
        if event.button() == Qt.LeftButton:
            self._is_drawing = True
            self._draw_mode = 1  # Draw
            self._update_cell(event.pos())
        elif event.button() == Qt.RightButton:
            self._is_drawing = True
            self._draw_mode = 0  # Erase
            self._update_cell(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent):
        """Continues drawing or erasing while the mouse is held down."""
        if self._is_drawing:
            self._update_cell(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Stops the draw/erase action."""
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self._is_drawing = False

    def resizeEvent(self, event):
        """Ensures grid is recalculated on resize."""
        self._update_cell_size()
        self.update()


class FontRenderer(QWidget):
    """
    A custom widget that renders a string of text using the generated font data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_data = {}
        self.text_to_render = ""
        self._sorted_keys = []

        # --- Rendering Configuration ---
        self.pixel_size = 3       # How many screen pixels per font "pixel"
        self.glyph_padding = 1    # Padding between glyphs (in font pixels)
        self.line_padding = 4     # Padding between lines (in font pixels)

        self.setMinimumSize(400, 300)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setLineWidth(2)

    def setFrameStyle(self, style):
        """Helper to set QFrame-like properties on a QWidget."""
        self.setProperty("frameStyle", style)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def setLineWidth(self, width):
        """Helper to set QFrame-like properties on a QWidget."""
        self.setProperty("lineWidth", width)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_font_data(self, font_data: dict):
        """
        Updates the renderer's font dictionary.
        Sorts keys by length (desc) to handle multi-character glyphs (e.g., "th" before "t").
        """
        self.font_data = font_data
        # Sort keys by length, descending. Crucial for multi-char glyphs.
        self._sorted_keys = sorted(self.font_data.keys(), key=len, reverse=True)
        self.update() # Repaint with new font

    def set_text(self, text: str):
        """Sets the text to be rendered."""
        self.text_to_render = text
        self.update() # Repaint with new text

    def _draw_glyph(self, painter: QPainter, x_offset: int, y_offset: int, data: list[list[int]]):
        """Draws a single glyph at the specified offset."""
        painter.setBrush(Qt.black)
        painter.setPen(Qt.NoPen)

        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if data[y][x] == 1:
                    painter.drawRect(
                        x_offset + (x * self.pixel_size),
                        y_offset + (y * self.pixel_size),
                        self.pixel_size,
                        self.pixel_size
                    )

    def _draw_placeholder(self, painter: QPainter, x_offset: int, y_offset: int, char: str):
        """Draws a placeholder for un-mapped characters."""
        glyph_width_px = GRID_SIZE * self.pixel_size
        glyph_height_px = GRID_SIZE * self.pixel_size

        # Draw a gray box
        painter.setBrush(Qt.lightGray)
        painter.setPen(Qt.NoPen)
        painter.drawRect(x_offset, y_offset, glyph_width_px, glyph_height_px)

        # Draw a red question mark or the char itself
        painter.setPen(QColor("red"))
        # A simple "!" to indicate a missing glyph
        rect = QRect(x_offset, y_offset, glyph_width_px, glyph_height_px)
        painter.drawText(rect, Qt.AlignCenter, "!")

    def paintEvent(self, event: QPaintEvent):
        """
        Handles the complex logic of parsing text and drawing all glyphs.
        """
        super().paintEvent(event) # Handle frame drawing

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False) # We want sharp pixels

        # Get content rect (inside the frame) and fill with white
        content_rect = self.contentsRect()
        painter.fillRect(content_rect, QColor("white"))

        # Start drawing from the top-left of the content area
        painter.translate(content_rect.topLeft())

        # Calculate pixel dimensions
        glyph_width_px = GRID_SIZE * self.pixel_size
        glyph_height_px = GRID_SIZE * self.pixel_size

        # Calculate advance widths (how far to move X after drawing)
        x_advance = glyph_width_px + (self.glyph_padding * self.pixel_size)
        y_advance = glyph_height_px + (self.line_padding * self.pixel_size)

        current_x = 0
        current_y = 0

        i = 0
        text_len = len(self.text_to_render)

        while i < text_len:
            # Handle newline
            if self.text_to_render[i] == '\n':
                current_x = 0
                current_y += y_advance
                i += 1
                continue

            # Check for word wrap
            if current_x + glyph_width_px > content_rect.width():
                current_x = 0
                current_y += y_advance

            # --- Glyph Matching Logic ---
            matched_key = None
            for key in self._sorted_keys:
                if self.text_to_render.startswith(key, i):
                    matched_key = key
                    break # Found the longest matching key

            if matched_key:
                glyph_data = self.font_data[matched_key]
                self._draw_glyph(painter, current_x, current_y, glyph_data)
                i += len(matched_key)
            else:
                # No match found, draw placeholder
                char = self.text_to_render[i]
                self._draw_placeholder(painter, current_x, current_y, char)
                i += 1

            current_x += x_advance


class MainWindow(QMainWindow):
    """
    Main application window.
    Holds the editor, renderer, and control buttons, and manages the font data.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pixel Font Maker")
        self.setGeometry(100, 100, 1000, 600)

        # This dictionary holds the entire custom font
        # Key: string (e.g., "a", "b", "th")
        # Value: list[list[int]] (the 16x16 grid data)
        self.font_data = {}

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- Left Panel: Editor ---
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 10, 0)

        # Character Input
        char_layout = QHBoxLayout()
        char_label = QLabel("Character:")
        self.char_input = QLineEdit()
        self.char_input.setPlaceholderText("e.g., 'a' or 'th'")
        self.char_input.setFixedWidth(100)
        char_layout.addWidget(char_label)
        char_layout.addWidget(self.char_input)
        char_layout.addStretch()

        editor_layout.addLayout(char_layout)

        # Pixel Editor Widget
        self.editor = PixelEditor()
        editor_layout.addWidget(self.editor, 1) # Give stretch factor

        # Editor Buttons
        editor_button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save/Update Glyph")
        self.clear_button = QPushButton("Clear Grid")
        editor_button_layout.addWidget(self.clear_button)
        editor_button_layout.addWidget(self.save_button)
        editor_layout.addLayout(editor_button_layout)

        # --- Right Panel: Renderer ---
        renderer_layout = QVBoxLayout()
        renderer_layout.setContentsMargins(10, 0, 0, 0)

        # Test Text Input
        test_label = QLabel("Test Your Font:")
        self.test_text_input = QTextEdit()
        self.test_text_input.setPlaceholderText("Type here to see your font in action...")
        self.test_text_input.setMinimumHeight(100)
        self.test_text_input.setMaximumHeight(200)

        # Font Renderer Widget
        self.renderer = FontRenderer()

        # Add scroll area for the renderer
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.renderer)
        self.renderer.setMinimumSize(400, 400) # Give renderer a min size

        renderer_layout.addWidget(test_label)
        renderer_layout.addWidget(self.test_text_input)
        renderer_layout.addWidget(scroll_area, 1) # Give stretch factor

        # --- Add Panels to Main Layout ---
        left_frame = QFrame()
        left_frame.setLayout(editor_layout)

        right_frame = QFrame()
        right_frame.setLayout(renderer_layout)

        main_layout.addWidget(left_frame, 1)
        main_layout.addWidget(right_frame, 1)

        # --- Connect Signals and Slots ---
        self.save_button.clicked.connect(self.save_glyph)
        self.clear_button.clicked.connect(self.editor.clear_grid)

        # When the character input changes, try to load that glyph
        self.char_input.textChanged.connect(self.load_glyph_for_editing)

        # When the test text changes, update the renderer
        self.test_text_input.textChanged.connect(self.update_renderer_text)

        # If user clears grid, and it was for the current char, save the clear
        self.editor.gridChanged.connect(self.auto_save_cleared_glyph)

    def save_glyph(self):
        """
        Saves the current editor grid data into the main font_data dictionary.
        """
        char = self.char_input.text()
        if not char:
            # Maybe show a status message later
            print("Cannot save glyph: No character specified.")
            return

        grid_data = self.editor.get_grid_data()
        self.font_data[char] = grid_data

        # Update the renderer's font data
        self.renderer.set_font_data(self.font_data)
        print(f"Saved glyph for: '{char}'")

    def auto_save_cleared_glyph(self):
        """
        If the grid is cleared while a character is active,
        and that char exists, update it to be empty.
        """
        char = self.char_input.text()
        if char and char in self.font_data:
            # Check if grid is *actually* empty
            grid_data = self.editor.get_grid_data()
            if all(all(cell == 0 for cell in row) for row in grid_data):
                self.font_data[char] = grid_data
                self.renderer.set_font_data(self.font_data)
                print(f"Auto-saved empty glyph for: '{char}'")

    def load_glyph_for_editing(self, char: str):
        """
        When the char_input QLineEdit changes, this slot is called.
        It loads the corresponding glyph into the editor, or clears it if new.
        """
        if char in self.font_data:
            self.editor.set_grid_data(self.font_data[char])
        else:
            # This is a new character, so clear the grid for them
            self.editor.clear_grid()

    def update_renderer_text(self):
        """
        Passes the text from the QTextEdit to the FontRenderer widget.
        """
        text = self.test_text_input.toPlainText()
        self.renderer.set_text(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())