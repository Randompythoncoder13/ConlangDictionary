from src.app import ConlangDictionaryApp
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
import sys
import pyperclip
import playsound3

if __name__ == "__main__":
    app = QApplication(sys.argv)

    font_path = "assets/font/Charis-Regular.ttf"
    font_id = QFontDatabase.addApplicationFont(font_path)

    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app_font = QFont(font_family, 11)
        app.setFont(app_font)

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
