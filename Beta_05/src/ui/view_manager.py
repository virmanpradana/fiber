from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QStackedWidget
from PyQt6.QtCore import pyqtSignal

class ViewManager(QWidget):
    """
    Gestiona el área central de vistas principales (QStackedWidget + QComboBox).
    Permite añadir vistas y seleccionar la activa.
    Señal: view_changed(index: int)
    """
    view_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        self.stack = QStackedWidget()
        layout.addWidget(self.combo)
        layout.addWidget(self.stack)
        self.combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.combo.currentIndexChanged.connect(self.view_changed.emit)

    def add_view(self, name, widget, data=None):
        self.combo.addItem(name, data)
        self.stack.addWidget(widget)

    def set_current_index(self, index):
        self.combo.setCurrentIndex(index)

    def current_index(self):
        return self.combo.currentIndex()

    def current_widget(self):
        return self.stack.currentWidget()

    def count(self):
        return self.stack.count()
