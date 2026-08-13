from src.app import ConlangDictionaryApp
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from pathlib import Path
import sys
import pyperclip
import playsound3
import qdarktheme

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.resolve()

    font_path = base_dir / "assets" / "font" / "Charis-Regular.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font_path))

    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app_font = QFont(font_family, 11)
        app.setFont(app_font)
    else:
        pass

    main_window = ConlangDictionaryApp()
    main_window.show()
    sys.exit(app.exec())
