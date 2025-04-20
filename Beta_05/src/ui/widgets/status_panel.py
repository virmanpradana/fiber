from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QTextEdit

class StatusPanel(QGroupBox):
    """
    Panel autocontenida para mostrar el estado y sugerencias.
    """
    def __init__(self, parent=None):
        super().__init__("Estado y Sugerencias", parent)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

    def set_suggestions(self, suggestions):
        self.text_edit.clear()
        for suggestion in suggestions:
            self.text_edit.append(suggestion)
