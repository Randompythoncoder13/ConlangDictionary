from PyQt6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QTextEdit, QWizard, QWizardPage


class SPNUEWIntroPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("File Error Due to Update")

        layout = QVBoxLayout()
        text_display = QTextEdit()
        text_display.setReadOnly(True)

        text_display.setPlainText(
            "An update has changed how files are stored.  In order to properly save your current conlang project you"
            " are required to enter a project name."
        )
        text_display.resize(text_display.size())
        layout.addWidget(text_display)
        layout.addWidget(QLabel("Enter a project name to save your file as:"))
        self.nameLineEdit = QLineEdit()
        layout.addWidget(self.nameLineEdit)
        self.setLayout(layout)

        self.registerField("name", self.nameLineEdit)


class SetProjectNameUpdateErrorWizard(QWizard):
    def __init__(self, parent=None, info_parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Error Due to Update")
        self.info_parent = info_parent

        self.addPage(SPNUEWIntroPage(self))
