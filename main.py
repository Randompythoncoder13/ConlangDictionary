from src.app import ConlangDictionaryApp
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
