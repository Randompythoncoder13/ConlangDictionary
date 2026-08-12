from PySide6.QtWidgets import  QWidget, QVBoxLayout, QTextEdit, QPushButton


class StatsTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

        layout = QVBoxLayout(self)
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)

        refresh_btn = QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self.refresh_stats_page)
        layout.addWidget(refresh_btn)

        self.refresh_stats_page()

    def refresh_stats_page(self):
        total_words = len(self.main_app.dictionary)

        # Initialize counts
        parts_of_speech = {pos: 0 for pos in self.main_app.word_classes}
        tags = {tag: 0 for tag in self.main_app.all_tags}

        root_words = 0
        terminal_words = 0

        for word in self.main_app.dictionary:
            pos = word.get("pos", "Other")
            for part in pos:
                if part in parts_of_speech:
                    parts_of_speech[part] += 1

            for tag in word.get("tags", []):
                if tag in tags:
                    tags[tag] += 1

            if not word.get("roots", []):
                root_words += 1

            if not word.get("derived", []):
                terminal_words += 1

        stats_lines = [
            f"Total Words: {total_words}", f"Root Words: {root_words} (no roots)",
            f"Terminal Words: {terminal_words} (no derivatives)", "\n== Parts of Speech =="
        ]

        for pos, count in parts_of_speech.items():
            if count > 0:
                stats_lines.append(f"{pos}: {count}")

        stats_lines.append("\n== Tags ==")

        for tag, count in sorted(tags.items()):
            if count > 0:
                stats_lines.append(f"{tag}: {count}")

        self.stats_text.setText("\n".join(stats_lines))
