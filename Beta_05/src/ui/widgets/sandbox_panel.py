from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QFrame, QGridLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class SandboxPanel(QGroupBox):
    """
    Panel autocontenida para pruebas y simulación de fallos.
    Señales:
        simulate_failure(fiber_num: int)
        restore_selected_segment()
        simulate_random_failure()
        restore_all_segments()
    """
    simulate_failure = pyqtSignal(int)
    restore_selected_segment = pyqtSignal()
    simulate_random_failure = pyqtSignal()
    restore_all_segments = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Panel de Pruebas (Sandbox)", parent)
        self.setFixedWidth(200)
        layout = QVBoxLayout(self)
        info_label = QLabel("Herramientas para simular fallos y probar la aplicación.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        segment_group = QGroupBox("Segmento Seleccionado")
        segment_layout = QVBoxLayout(segment_group)
        self.selected_segment_label = QLabel("Ninguno seleccionado")
        segment_layout.addWidget(self.selected_segment_label)
        fail_buttons_layout = QGridLayout()
        for i, fiber_num in enumerate([1, 2, 3, 4]):
            fail_btn = QPushButton(f"Fallo F{fiber_num}")
            fail_btn.setToolTip(f"Marca la fibra {fiber_num} como 'averiado'")
            fail_btn.clicked.connect(lambda checked, num=fiber_num: self.simulate_failure.emit(num))
            fail_buttons_layout.addWidget(fail_btn, 0, i)
        restore_btn = QPushButton("Restaurar Fibras")
        restore_btn.setToolTip("Restaura todas las fibras del segmento seleccionado a 'ok'")
        restore_btn.clicked.connect(self.restore_selected_segment.emit)
        segment_layout.addLayout(fail_buttons_layout)
        segment_layout.addWidget(restore_btn)
        layout.addWidget(segment_group)
        random_group = QGroupBox("Fallos Aleatorios")
        random_layout = QVBoxLayout(random_group)
        random_btn = QPushButton("Fallo Aleatorio")
        random_btn.setToolTip("Genera un fallo aleatorio en alguna fibra de la red")
        random_btn.clicked.connect(self.simulate_random_failure.emit)
        random_layout.addWidget(random_btn)
        restore_all_btn = QPushButton("Restaurar Todos")
        restore_all_btn.setToolTip("Restaura todas las fibras de la red a estado 'ok'")
        restore_all_btn.clicked.connect(self.restore_all_segments.emit)
        random_layout.addWidget(restore_all_btn)
        layout.addWidget(random_group)
        layout.addStretch()

    def set_selected_segment(self, segment_id):
        if segment_id:
            self.selected_segment_label.setText(f"Segmento: {segment_id}")
            self.selected_segment_label.setStyleSheet("font-weight: bold;")
        else:
            self.selected_segment_label.setText("Ninguno seleccionado")
            self.selected_segment_label.setStyleSheet("font-style: italic; color: grey;")
