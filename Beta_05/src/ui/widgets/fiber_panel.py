# a:\Beta_02\src\ui\widgets\fiber_panel.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QGroupBox, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

# Constantes
# Change the relative import to an absolute import from the 'src' package root
# This assumes 'src' is the top-level package recognized by Python
# when the application starts (e.g., running from the Beta_02 directory).
from constants import (
    DEFAULT_FIBRAS_COMMS_IDA,
    DEFAULT_FIBRAS_COMMS_VUELTA,
    DEFAULT_FIBRAS_RESERVA,
    DEFAULT_FIBRAS_CCTV
)

logger = logging.getLogger(__name__)

class FiberButton(QPushButton):
    """Botón personalizado para representar una fibra."""

    def __init__(self, fiber_num, status="ok", parent=None):
        """Inicializa el botón.

        Args:
            fiber_num: Número de fibra
            status: Estado de la fibra ('ok' o 'averiado')
            parent: Widget padre
        """
        super().__init__(parent)

        self.fiber_num = fiber_num
        self.status = status

        # Configurar texto
        self.setText(f"F{fiber_num}")
        self.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

        # Fijar tamaño
        self.setFixedSize(40, 30)

        # Actualizar apariencia
        self.update_appearance()

    def update_appearance(self):
        """Actualiza la apariencia del botón según el estado."""
        if self.status == 'ok':
            self.setStyleSheet("""
                QPushButton {
                    background-color: #16a34a;
                    color: white;
                    border: 1px solid #064e3b;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #15803d;
                }
                QPushButton:pressed {
                    background-color: #166534;
                }
            """)
        else:  # averiado
            self.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626;
                    color: white;
                    border: 1px solid #991b1b;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #b91c1c;
                }
                QPushButton:pressed {
                    background-color: #7f1d1d;
                }
            """)

        # Actualizar tooltip
        self.setToolTip(f"Fibra {self.fiber_num}: {self.status.upper()}\nClick para cambiar estado")

    def set_status(self, new_status):
        """Cambia el estado de la fibra."""
        if new_status in ['ok', 'averiado'] and new_status != self.status:
            self.status = new_status
            self.update_appearance()


class FiberPanel(QWidget):
    """Panel para visualizar y manipular el estado de las fibras."""

    # Señal emitida cuando se cambia el estado de una fibra
    fiber_status_changed = pyqtSignal(str, int, str)  # segment_id, fiber_num, new_status
    restore_all_requested = pyqtSignal(str)  # segment_id

    def __init__(self, model, parent=None):
        """Inicializa el panel.

        Args:
            model: Modelo de red
            parent: Widget padre
        """
        super().__init__(parent)
        self.model = model
        self.segment_id = None
        self.segment_data = None
        self.fiber_buttons = {}  # {fiber_num: FiberButton}

        self._init_ui()

    def _init_ui(self):
        """Inicializa la interfaz del panel."""
        # Layout principal
        main_layout = QVBoxLayout(self)

        # Título
        self.title_label = QLabel("Detalle de Fibras")
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        main_layout.addWidget(self.title_label)

        # Información del segmento
        self.segment_info = QLabel()
        main_layout.addWidget(self.segment_info)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)

        # Grupo Fibras IDA
        ida_group = QGroupBox("Fibras IDA")
        ida_layout = QGridLayout(ida_group)
        main_layout.addWidget(ida_group)

        # Grupo Fibras VUELTA
        vuelta_group = QGroupBox("Fibras VUELTA")
        vuelta_layout = QGridLayout(vuelta_group)
        main_layout.addWidget(vuelta_group)

        # Grupo Fibras RESERVA
        reserva_group = QGroupBox("Fibras RESERVA")
        reserva_layout = QGridLayout(reserva_group)
        main_layout.addWidget(reserva_group)

        # Grupo Fibras CCTV
        cctv_group = QGroupBox("Fibras CCTV")
        cctv_layout = QGridLayout(cctv_group)
        main_layout.addWidget(cctv_group)

        # Guardar referencias a layouts
        self.group_layouts = {
            'ida': ida_layout,
            'vuelta': vuelta_layout,
            'reserva': reserva_layout,
            'cctv': cctv_layout
        }

        # Panel de controles
        controls_layout = QHBoxLayout()

        # Leyenda
        legend_layout = QVBoxLayout()
        legend_title = QLabel("Estado:")
        legend_title.setFont(QFont("Segoe UI", 8))

        ok_layout = QHBoxLayout()
        ok_indicator = QLabel()
        ok_indicator.setFixedSize(16, 16)
        ok_indicator.setStyleSheet("background-color: #16a34a; border: 1px solid black;")
        ok_label = QLabel("OK")
        ok_layout.addWidget(ok_indicator)
        ok_layout.addWidget(ok_label)

        fault_layout = QHBoxLayout()
        fault_indicator = QLabel()
        fault_indicator.setFixedSize(16, 16)
        fault_indicator.setStyleSheet("background-color: #dc2626; border: 1px solid black;")
        fault_label = QLabel("Averiado")
        fault_layout.addWidget(fault_indicator)
        fault_layout.addWidget(fault_label)

        legend_layout.addWidget(legend_title)
        legend_layout.addLayout(ok_layout)
        legend_layout.addLayout(fault_layout)

        controls_layout.addLayout(legend_layout)
        controls_layout.addStretch()

        # Botón de restaurar
        self.restore_button = QPushButton("Restaurar Todas")
        self.restore_button.clicked.connect(self.on_restore_all)
        self.restore_button.setToolTip("Restaura todas las fibras del segmento a estado 'ok'")
        controls_layout.addWidget(self.restore_button)

        main_layout.addLayout(controls_layout)

        # Tip para el usuario
        tip_label = QLabel("Haga clic en una fibra para cambiar su estado")
        tip_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal, True))  # Cursiva
        tip_label.setStyleSheet("color: #64748b;")  # Color gris
        main_layout.addWidget(tip_label)

        # Margen inferior para empujar el box de controles abajo
        main_layout.addStretch()

    def set_segment(self, segment_id, segment_data):
        """Establece el segmento activo y actualiza la vista.

        Args:
            segment_id: ID del segmento
            segment_data: Datos del segmento
        """
        if not segment_id or not segment_data:
            self.clear()
            return

        self.segment_id = segment_id
        self.segment_data = segment_data

        # Actualizar información del segmento
        source = segment_data.get('source', '?')
        target = segment_data.get('target', '?')
        circuit = segment_data.get('circuit', 'N/A')
        self.segment_info.setText(f"Segmento: {segment_id} ({source}↔{target}) - Circuito: {circuit}")

        # Limpiar botones existentes
        for button in self.fiber_buttons.values():
            button.setParent(None)
        self.fiber_buttons.clear()

        # Obtener datos de fibras
        fibers = segment_data.get('fibers', {})

        # Crear botones para cada tipo de fibra
        self.create_fiber_buttons('ida', DEFAULT_FIBRAS_COMMS_IDA, fibers)
        self.create_fiber_buttons('vuelta', DEFAULT_FIBRAS_COMMS_VUELTA, fibers)
        self.create_fiber_buttons('reserva', DEFAULT_FIBRAS_RESERVA, fibers)
        self.create_fiber_buttons('cctv', DEFAULT_FIBRAS_CCTV, fibers)

    def create_fiber_buttons(self, group_name, fiber_list, fibers_data):
        """Crea botones para un grupo de fibras.

        Args:
            group_name: Nombre del grupo ('ida', 'vuelta', etc.)
            fiber_list: Lista de números de fibra
            fibers_data: Diccionario con estados de fibras
        """
        layout = self.group_layouts[group_name]

        # Limpiar layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # Crear botones
        cols = min(4, len(fiber_list))
        for i, fiber_num in enumerate(fiber_list):
            fiber_key = str(fiber_num)
            status = fibers_data.get(fiber_key, 'ok')

            row = i // cols
            col = i % cols

            button = FiberButton(fiber_num, status)
            button.clicked.connect(lambda checked, fn=fiber_num: self.on_fiber_button_clicked(fn))

            layout.addWidget(button, row, col)
            self.fiber_buttons[fiber_num] = button

    def on_fiber_button_clicked(self, fiber_num):
        """Maneja el clic en un botón de fibra."""
        if not self.segment_id:
            return

        button = self.fiber_buttons.get(fiber_num)
        if not button:
            return

        # Cambiar estado (alternar entre 'ok' y 'averiado')
        new_status = 'averiado' if button.status == 'ok' else 'ok'

        # Emitir señal para que el controlador actualice el modelo
        self.fiber_status_changed.emit(self.segment_id, fiber_num, new_status)

    def on_restore_all(self):
        """Restaura todas las fibras del segmento a estado 'ok'."""
        if not self.segment_id:
            return

        # Emitir señal para que el controlador restaure todas las fibras
        self.restore_all_requested.emit(self.segment_id)

    def update_fiber_status(self, fiber_num, new_status):
        """Actualiza el estado visual de una fibra sin emitir señales.

        Args:
            fiber_num: Número de fibra
            new_status: Nuevo estado ('ok' o 'averiado')
        """
        button = self.fiber_buttons.get(fiber_num)
        if button:
            button.set_status(new_status)

    def clear(self):
        """Limpia el panel."""
        self.segment_id = None
        self.segment_data = None
        self.segment_info.setText("")

        # Limpiar botones
        for button in self.fiber_buttons.values():
            button.setParent(None)
        self.fiber_buttons.clear()

        # Limpiar layouts
        for layout in self.group_layouts.values():
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
