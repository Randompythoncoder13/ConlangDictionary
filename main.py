from src.app import ConlangDictionaryApp
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply a simple stylesheet for a cleaner look
    app.setStyleSheet("""
        QWidget {
            font-size: 10pt;
        }
        QGroupBox {
            font-weight: bold;
            font-size: 11pt;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px 5px 5px;
        }
        QPushButton {
            padding: 5px 10px;
        }
        QTableWidget {
            gridline-color: #ddd;
        }
        QHeaderView::section {
            padding: 4px;
            border: 1px solid #ddd;
            font-weight: bold;
        }
    """)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
