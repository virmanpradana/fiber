#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QComboBox, QDateEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush

# Importar BaseView
from ui.views.base_view import BaseView

logger = logging.getLogger(__name__)

class FiberHistoryView(QWidget):
    """Vista que muestra el historial de cambios en las fibras."""
    
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        layout = QVBoxLayout(self)
        
        # Panel de filtros
        filters_layout = QHBoxLayout()
        
        # Filtro por fecha
        filters_layout.addWidget(QLabel("Desde:"))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        filters_layout.addWidget(self.date_from)
        
        filters_layout.addWidget(QLabel("Hasta:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filters_layout.addWidget(self.date_to)
        
        # Filtro por segmento
        filters_layout.addWidget(QLabel("Segmento:"))
        self.segment_combo = QComboBox()
        self.segment_combo.addItem("Todos", None)
        filters_layout.addWidget(self.segment_combo)
        
        # Botón de búsqueda
        self.btn_search = QPushButton("Buscar")
        self.btn_search.clicked.connect(self._load_history)
        filters_layout.addWidget(self.btn_search)
        
        filters_layout.addStretch()
        
        layout.addLayout(filters_layout)
        
        # Tabla de historial
        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(["Fecha", "Hora", "Segmento", "Fibra", "Estado Anterior", "Estado Nuevo"])
        header = self.history_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.history_table)
        
        # Mensaje cuando no hay datos
        self.lbl_no_data = QLabel("No hay datos de historial disponibles.")
        self.lbl_no_data.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_data.setStyleSheet("color: gray;")
        layout.addWidget(self.lbl_no_data)
        self.lbl_no_data.setVisible(False)
        
    def update_view(self, status_data=None):
        """Actualiza la vista con los datos actuales."""
        # Actualizar lista de segmentos disponibles
        self._update_segment_list()
        
        # Cargar datos de historial
        self._load_history()
    
    def _update_segment_list(self):
        """Actualiza la lista de segmentos disponibles en el combo."""
        current_selection = self.segment_combo.currentData()
        
        self.segment_combo.clear()
        self.segment_combo.addItem("Todos", None)
        
        # Esta parte dependerá de cómo se acceda a los segmentos en tu modelo
        if hasattr(self.model, 'get_segments_list'):
            segments = self.model.get_segments_list()
            for segment_id in segments:
                self.segment_combo.addItem(segment_id, segment_id)
        
        # Restaurar selección anterior si es posible
        if current_selection:
            index = self.segment_combo.findData(current_selection)
            if index >= 0:
                self.segment_combo.setCurrentIndex(index)
    
    def _load_history(self):
        """Carga los datos de historial desde el modelo."""
        # Obtener filtros seleccionados
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        segment_id = self.segment_combo.currentData()
        
        # Obtener datos de historial desde el modelo
        history_data = []
        
        # Si el modelo tiene un método para obtener historial, usarlo
        if hasattr(self.model, 'get_fiber_history'):
            try:
                history_data = self.model.get_fiber_history(date_from, date_to, segment_id)
            except Exception as e:
                logger.error(f"Error cargando historial: {e}")
                QMessageBox.warning(self, "Error", f"Error al cargar datos de historial: {str(e)}")
        
        # Actualizar tabla con los datos obtenidos
        self._update_table(history_data)
    
    def _update_table(self, history_data):
        """Actualiza la tabla con los datos de historial."""
        self.history_table.setRowCount(0)  # Limpiar tabla
        
        if not history_data:
            self.lbl_no_data.setVisible(True)
            self.history_table.setVisible(False)
            return
        
        self.lbl_no_data.setVisible(False)
        self.history_table.setVisible(True)
        
        # Añadir filas a la tabla
        for i, record in enumerate(history_data):
            self.history_table.insertRow(i)
            
            # Fecha y hora podrían estar separadas o juntas dependiendo del modelo
            if 'timestamp' in record:
                # Si es un timestamp completo, separarlo
                date_time = record['timestamp'].split(' ')
                date = date_time[0] if len(date_time) > 0 else ""
                time = date_time[1] if len(date_time) > 1 else ""
            else:
                # Si están separados
                date = record.get('date', '')
                time = record.get('time', '')
            
            self.history_table.setItem(i, 0, QTableWidgetItem(date))
            self.history_table.setItem(i, 1, QTableWidgetItem(time))
            self.history_table.setItem(i, 2, QTableWidgetItem(record.get('segment_id', '')))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(record.get('fiber_num', ''))))
            
            old_status = record.get('old_status', '')
            new_status = record.get('new_status', '')
            
            old_status_item = QTableWidgetItem(old_status)
            new_status_item = QTableWidgetItem(new_status)
            
            # Colorear estados
            self._set_status_color(old_status_item, old_status)
            self._set_status_color(new_status_item, new_status)
            
            self.history_table.setItem(i, 4, old_status_item)
            self.history_table.setItem(i, 5, new_status_item)
    
    def _set_status_color(self, item, status):
        """Establece el color de fondo según el estado de la fibra."""
        if status == 'ok':
            item.setBackground(QBrush(QColor('#dcfce7')))  # Verde claro
        elif status == 'averiado':
            item.setBackground(QBrush(QColor('#fee2e2')))  # Rojo claro
        elif status == 'atenuado':
            item.setBackground(QBrush(QColor('#fef9c3')))  # Amarillo claro
        elif status == 'reserva':
            item.setBackground(QBrush(QColor('#dbeafe')))  # Azul claro
    
    def reset_view(self):
        """Restablece la vista a su estado inicial."""
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.segment_combo.setCurrentIndex(0)
        self._load_history()
