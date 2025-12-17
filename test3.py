import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout, QStyle, QGroupBox, QLineEdit
)
from PySide6.QtGui import QFont, QBrush, QColor, QPalette
from PySide6.QtCore import Qt, QSize, Signal, QUrl
# from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

PC_TABLE_DATA = [
    # Row 1
    [
        None, "Bilabial", "Labiodental", "Dental", "Alveolar", "Postalveolar", "Retroflex", "Palatal", "Velar",
        "Uvular", "Pharyngeal", "Glottal"
    ],
    # Row 2 Plosive
    [
        "Plosive", "p/b", "/", "/", "t/d", "/", "ʈ/ɖ", "c/ɟ", "k/ɡ", "q/ɢ", "/", "ʔ/ "
    ],
    # Row 3 Nasal
    [
        "Nasal", " /m", " /ɱ", "/", " /n", "/", " /ɳ", " /ɲ", " /ŋ", " /ɴ", "/", "/"
    ],
    # Row 4 Trill
    [
        "Trill", " /ʙ", "/", "/", " /r", "/", "/", "/", "/", " /ʀ", "/", "/"
    ],
    # Row 5 Tap/flap
    [
        "Tap/flap", "/", " /ⱱ", "/", " /ɾ", "/", " /ɽ", "/", "/", "/", "/", "/"
    ],
    # Row 6 Fricative
    [
        "Fricative", "ɸ/β", "f/v", "θ/ð", "s/z", "ʃ/ʒ", "ʂ/ʐ", "ç/ʝ", "x/ɣ", "X/ʁ", "ħ/ʕ", "h/ɦ"
    ],
    # Row 7 Lateral Fricative
    [
        "Lateral\nFricative", "/", "/", "/", "ɬ/ɮ", "/", "/", "/", "/", "/", "/", "/"
    ],
    # Row 8 Approximant
    [
        "Approximant", "/", " /ʋ", "/", " /ɹ", "/", " /ɻ", " /j", " /ɰ", "/", "/", "/"
    ],
    # Row 9 Lateral Approximant
    [
        "Lateral\nApproximant", "/", "/", "/", " /l", "/", " /ɭ", " /ʎ", " /ʟ", "/", "/", "/"
    ]
]

NPC_TABLE_DATA = [
    [None, "Clicks", "Voiced Implosives", "Ejectives"],
    ["Bilabial", "ʘ", "ɓ", "pʼ/ɸʼ"],
    ["Labiodental", "", "", "fʼ"],
    ["Dental", "ǀ", "", "θʼ"],
    ["Alveolar", "ǃ/ǁ", "ɗ", "tʼ/sʼ"],
    ["Postalveolar", "", "", "ʃʼ"],
    ["Retroflex", "", "ᶑ", "ʈʼ/ʂʼ",],
    ["Palatal", "ǂ", "ʄ", "cʼ/ɕʼ"],
    ["Velar", "", "ɠ", "kʼ/xʼ"],
    ["Uvular", "", "ʛ", "qʼ/Xʼ"]
]

V_TABLE_DATA = [
    [None, "Front", "Near-Front", "Central", "Near-Back", "Back"],
    ["Close", "i/y", "", "ɨ/ʉ", "", "ɯ/u"],
    ["Near-Close", "", "I/Y", "", " /ʊ", ""],
    ["Close-Mid", "e/ø", "", "ɘ/ɵ", "", "ɤ/o"],
    ["Mid", "", "", "ə", "", ""],
    ["Open-Mid", "ɛ/œ", "", "ɜ/ɞ", "", "ʌ/ɔ"],
    ["Near-Open", "æ/ ", "", "ɐ/ ", "", ""],
    ["Open", "a/ɶ", "", "", "", "ɑ/ɒ"]
]


class IPACellWidget(QWidget):
    """
    A custom widget for a single IPA character cell.
    It contains the IPA text and a speaker button.
    The widget itself can be clicked to toggle its active state (background color).
    The speaker button can be clicked to play a sound.
    """

    playSound = Signal(str)

    def __init__(self, ipa_text, parent=None):
        super().__init__(parent)
        self.ipa_text = ipa_text
        self.is_active = True  # Start in the "normal" state

        # --- Create Palettes for Toggling ---
        self.setAutoFillBackground(True)

        # Normal (white) palette
        self.normal_palette = self.palette()

        # Greyed-out (deselected) palette
        self.grey_palette = QPalette()
        self.grey_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))

        # --- Create Widgets ---
        self.label = QLabel(self.ipa_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 10))  # Match main font

        self.update_background()

        self.speaker_button = QPushButton()
        play_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.speaker_button.setIcon(play_icon)
        self.speaker_button.setFixedSize(QSize(22, 22))
        self.speaker_button.setFlat(True)
        self.speaker_button.setToolTip(f"Play sound for {self.ipa_text}")

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)  # Label expands
        layout.addWidget(self.speaker_button, 0)  # Button is fixed size
        layout.setContentsMargins(5, 2, 5, 2)  # Tighten margins
        layout.setSpacing(5)
        self.setLayout(layout)

        # --- Connections ---
        self.speaker_button.clicked.connect(self.play_sound)

    def update_background(self):
        """Updates the widget's background based on the is_active state."""
        if self.is_active:
            self.setPalette(self.normal_palette)
            self.label.setStyleSheet("")
        else:
            self.setPalette(self.grey_palette)
            self.label.setStyleSheet("color: #A3A3A3;")

    def mousePressEvent(self, event):
        """Overrides the mouse press event to toggle the cell's active state."""
        # Check if the click was on the button; if so, let the button handle it.
        child = self.childAt(event.position().toPoint())
        if child == self.speaker_button:
            super().mousePressEvent(event)
            return

        # If the click is anywhere else, toggle the state.
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_active_state()

        super().mousePressEvent(event)

    def toggle_active_state(self):
        """Toggles the active state and updates the background."""
        self.is_active = not self.is_active
        self.update_background()

    def play_sound(self):
        self.playSound.emit(f"ipa_sounds/{self.label.text()}.mp3")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPA Pulmonic Consonants Chart")

        # Set a font that is likely to support IPA characters
        self.setFont(QFont("Arial", 10))

        self.table = QTableWidget()

        # Define table dimensions
        self.num_rows = 9
        self.num_cols = 12  # Changed from 25 to 27
        self.table.setRowCount(self.num_rows)
        self.table.setColumnCount(self.num_cols)

        # Hide the default headers, as we are creating our own
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)

        # Define brushes and fonts
        self.shaded_brush = QBrush(QColor(230, 230, 230))
        self.header_font = QFont()
        self.header_font.setBold(True)

        self.populate_table()
        self.resize_table()

        # Set the central widget
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.table)
        self.setCentralWidget(central_widget)

        # self._player = QMediaPlayer()
        # self._audio_output = QAudioOutput()
        # self._player.setAudioOutput(self._audio_output)

        # Set initial size
        self.resize(1200, 700)

    def create_item(self, text, is_header=False):
        """Helper function to create a centered QTableWidgetItem."""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if is_header:
            item.setFont(self.header_font)
        return item

    def populate_table(self):
        """Fills the table with data from the TABLE_DATA list."""
        for r_idx, row_data in enumerate(PC_TABLE_DATA):
            for c_idx, cell_text in enumerate(row_data):

                if cell_text is None:
                    continue

                # Check conditions
                is_header = (r_idx < 1) or (c_idx == 0)
                is_special_cell = cell_text == "/"
                cell_text = "" if cell_text == "/" else cell_text

                if is_header or is_special_cell:
                    # Use a standard QTableWidgetItem for headers, shaded cells, and empty cells
                    item = self.create_item(cell_text, is_header)

                    self.table.setItem(r_idx, c_idx, item)
                else:
                    # This is a data cell, so use our custom IPACellWidget
                    cell = QWidget()
                    container = QHBoxLayout(cell)

                    if cell_text.split("/")[0] != " ":
                        cell_widget_l = IPACellWidget(cell_text.split("/")[0])
                        cell_widget_l.playSound.connect(self.play_audio)
                    else:
                        cell_widget_l = QLabel("               ")

                    if cell_text.split("/")[1] != " ":
                        cell_widget_r = IPACellWidget(cell_text.split("/")[1])
                        cell_widget_r.playSound.connect(self.play_audio)
                    else:
                        cell_widget_r = QLabel("               ")

                    container.addWidget(cell_widget_l)
                    container.addWidget(cell_widget_r)
                    self.table.setCellWidget(r_idx, c_idx, cell)

    def resize_table(self):
        """Resizes all columns and rows to fit their content."""
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # Give a little more width to data columns for padding
        for c in range(1, self.num_cols):
            self.table.setColumnWidth(c, self.table.columnWidth(c) + 10)

        # Give a little more width to the first (header) column
        self.table.setColumnWidth(0, self.table.columnWidth(0) + 15)

    def play_audio(self, file_path):
        """ Slot to play the requested audio file. """
        # Check if file exists (again, for safety)
        if not os.path.exists(file_path):
            print(f"Error: Cannot play non-existent file: {file_path}")
            return

        full_path = os.path.abspath(file_path)
        # self._player.stop()  # Stop any currently playing sound
        # self._player.setSource(QUrl.fromLocalFile(full_path))
        # self._player.play()
        print("audio plays")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
