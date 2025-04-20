#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsView, QGraphicsScene
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter

# Importar BaseView
from ui.views.base_view import BaseView

logger = logging.getLogger(__name__)

class LayoutView(QWidget):
    """Vista para mostrar y editar el layout topográfico de la planta."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        layout = QVBoxLayout(self)
        
        # Mensaje de vista en desarrollo
        info_label = QLabel("Vista de Layout Topográfico en desarrollo")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Arial", 14)
        info_label.setFont(font)
        info_label.setStyleSheet("color: #3b82f6; margin: 20px;")
        layout.addWidget(info_label)
        
        # Vista gráfica para futuro desarrollo
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)
        
        # Añadir texto explicativo a la escena
        self.scene.addText(
            "Esta vista permitirá visualizar y editar el layout topográfico\n"
            "de la planta y sus componentes. Funcionalidad en desarrollo.",
            QFont("Arial", 10)
        )
    
    def update_view(self, status_data=None):
        """Actualiza la vista con los datos del modelo."""
        # Implementación futura - por ahora solo un placeholder
        pass
        
    def reset_view(self):
        """Restablece la vista a su estado inicial."""
        if self.view and self.scene:
            self.view.resetTransform()
            self.view.centerOn(0, 0)
