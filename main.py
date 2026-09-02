from src.app import ConlangDictionaryApp
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from pathlib import Path
import sys
import os
import json
import pyperclip
import playsound3
import qdarktheme

if __name__ == "__main__":
    app = QApplication(sys.argv)

    try:
        if sys.platform == "win32":
            app_data_path = Path(os.getenv('LOCALAPPDATA', ''))
        elif sys.platform == "darwin":
            app_data_path = Path.home() / 'Library' / 'Application Support'
        else:
            app_data_path = Path.home() / '.local' / 'share'

        app_data_dir = app_data_path / "ConlangDictionary"
        os.makedirs(app_data_dir, exist_ok=True)
    except OSError as e:
        sys.exit(1)

    l_d_mode_file = os.path.join(app_data_dir, "dark_light_mode.txt")
    settings_file = os.path.join(app_data_dir, "settings.json")
    if os.path.exists(l_d_mode_file):
        with open(l_d_mode_file, "r") as f:
            ld_data = f.read()

        with open(settings_file, "w") as f:
            data = {"l/d": ld_data, "font": "Charis-Regular.tff"}
            json.dump(data, f, indent=4)

        os.remove(l_d_mode_file)
    elif not os.path.exists(settings_file):
        with open(settings_file, "w") as f:
            data = {"l/d": "l", "font": "JuliaMono-Regular.tff"}

    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.resolve()

    with open(settings_file, "r") as f:
        settings = json.load(f)
        font = settings["font"]

    font_path = base_dir / "assets" / "font" / font
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
