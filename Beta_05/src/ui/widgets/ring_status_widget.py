from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QTextEdit, QGraphicsScene
from PyQt6.QtGui import QPainter
from .zoomable_graphics_view import ZoomableGraphicsView

class RingStatusWidget(QGroupBox):
    """
    Widget autocontenida para mostrar el estado del anillo y su visualización simplificada.
    Proporciona acceso a los elementos gráficos y métodos para actualizar el estado.
    """
    def __init__(self, parent=None):
        super().__init__("Estado del Anillo (Vista Simplificada)", parent)
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Estado: Pendiente de verificación")
        layout.addWidget(self.status_label)
        self.ring_view_canvas = ZoomableGraphicsView()
        self.ring_view_canvas.setScene(QGraphicsScene())
        self.ring_view_canvas.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ring_view_canvas.setMinimumHeight(250)
        layout.addWidget(self.ring_view_canvas)
        self.ring_view_text = QTextEdit()
        self.ring_view_text.setReadOnly(True)
        self.ring_view_text.setMaximumHeight(100)
        layout.addWidget(self.ring_view_text)
