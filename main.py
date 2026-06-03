from src.app import ConlangDictionaryApp
from PySide6.QtWidgets import QApplication
import sys
import pyperclip
import playsound3

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
