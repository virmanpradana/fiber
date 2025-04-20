#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QGroupBox, QFormLayout,
    QSpinBox, QLineEdit, QMessageBox, QSplitter, QDialog, QDialogButtonBox,
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QGraphicsView, QGraphicsScene
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QPen, QBrush, QPainter
from typing import Dict, Any, Optional, TYPE_CHECKING

# Importar BaseView
from ui.views.base_view import BaseView

# Importar constantes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from constants import get_cctv_config

# Importar NetworkModel directamente (no es circular)
from model.network_model import NetworkModel

# Usamos TYPE_CHECKING para evitar importaciones reales en tiempo de ejecución
if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger(__name__)

class CCTVConfigDialog(QDialog):
    """Diálogo para configurar cámaras CCTV en un CT."""
    
    def __init__(self, ct_id, cctv_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configuración CCTV para {ct_id}")
        self.setMinimumWidth(400)
        
        self.ct_id = ct_id
        self.cctv_data = cctv_data or {"camaras": 0, "baculos": []}
        
        layout = QVBoxLayout(self)
        
        # Formulario para datos básicos
        form_layout = QFormLayout()
        
        # Número de cámaras
        self.sb_camaras = QSpinBox()
        self.sb_camaras.setMinimum(0)
        self.sb_camaras.setMaximum(10)
        self.sb_camaras.setValue(self.cctv_data.get("camaras", 0))
        form_layout.addRow("Número de cámaras:", self.sb_camaras)
        
        layout.addLayout(form_layout)
        
        # Tabla de báculos
        self.group_baculos = QGroupBox("Báculos")
        baculos_layout = QVBoxLayout(self.group_baculos)
        
        self.tabla_baculos = QTableWidget(0, 3)
        self.tabla_baculos.setHorizontalHeaderLabels(["ID", "Descripción", "Cámaras"])
        header = self.tabla_baculos.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        baculos_layout.addWidget(self.tabla_baculos)
        
        # Botones para gestionar báculos
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Añadir Báculo")
        self.btn_add.clicked.connect(self.add_baculo)
        btn_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("Eliminar Seleccionado")
        self.btn_remove.clicked.connect(self.remove_baculo)
        btn_layout.addWidget(self.btn_remove)
        
        baculos_layout.addLayout(btn_layout)
        layout.addWidget(self.group_baculos)
        
        # Botones del diálogo
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Cargar báculos existentes
        self._load_baculos()
        
    def _load_baculos(self):
        """Carga los báculos existentes en la tabla."""
        baculos = self.cctv_data.get("baculos", [])
        self.tabla_baculos.setRowCount(len(baculos))
        
        for i, baculo_id in enumerate(baculos):
            item_id = QTableWidgetItem(baculo_id)
            item_desc = QTableWidgetItem(f"Báculo {baculo_id}")
            item_camaras = QTableWidgetItem("1")  # Por defecto 1 cámara por báculo
            
            self.tabla_baculos.setItem(i, 0, item_id)
            self.tabla_baculos.setItem(i, 1, item_desc)
            self.tabla_baculos.setItem(i, 2, item_camaras)
    
    def add_baculo(self):
        """Añade un nuevo báculo a la tabla."""
        row_count = self.tabla_baculos.rowCount()
        self.tabla_baculos.insertRow(row_count)
        
        # Generar ID automático
        new_id = f"B{row_count + 1:02d}"
        
        item_id = QTableWidgetItem(new_id)
        item_desc = QTableWidgetItem(f"Báculo {new_id}")
        item_camaras = QTableWidgetItem("1")
        
        self.tabla_baculos.setItem(row_count, 0, item_id)
        self.tabla_baculos.setItem(row_count, 1, item_desc)
        self.tabla_baculos.setItem(row_count, 2, item_camaras)
    
    def remove_baculo(self):
        """Elimina el báculo seleccionado."""
        selected_rows = self.tabla_baculos.selectedIndexes()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        self.tabla_baculos.removeRow(row)
    
    def get_data(self):
        """Obtiene los datos de configuración CCTV."""
        num_camaras = self.sb_camaras.value()
        
        baculos = []
        for row in range(self.tabla_baculos.rowCount()):
            item = self.tabla_baculos.item(row, 0)
            if item is not None:
                baculo_id = item.text()
                baculos.append(baculo_id)
        
        return {
            "camaras": num_camaras,
            "baculos": baculos
        }


class CCTVView(QWidget):
    """Vista que muestra y gestiona la configuración de videovigilancia CCTV."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plant_id = "default"
        self.cctv_data = {}
        self._setup_ui()
        
    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        layout = QVBoxLayout(self)
        
        # Panel superior de información
        info_layout = QHBoxLayout()
        self.lbl_plant = QLabel("Planta: Default")
        info_layout.addWidget(self.lbl_plant)
        
        info_layout.addStretch()
        
        self.lbl_stats = QLabel("Cámaras: 0 | Báculos: 0")
        info_layout.addWidget(self.lbl_stats)
        
        layout.addLayout(info_layout)
        
        # Splitter para dividir la vista
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Panel izquierdo: Árbol editable de CTs, báculos y cámaras ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Elemento", "Cantidad"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        splitter.addWidget(self.tree)
        
        # --- Panel derecho: Detalles y botones ---
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        self.lbl_ct_title = QLabel("Seleccione un elemento")
        self.lbl_ct_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        details_layout.addWidget(self.lbl_ct_title)
        
        # Detalles de cámaras
        self.group_camaras = QGroupBox("Cámaras")
        camaras_layout = QFormLayout(self.group_camaras)
        self.lbl_num_camaras = QLabel("0")
        camaras_layout.addRow("Número de cámaras:", self.lbl_num_camaras)
        details_layout.addWidget(self.group_camaras)
        
        # Tabla de báculos
        self.group_baculos = QGroupBox("Báculos")
        baculos_layout = QVBoxLayout(self.group_baculos)
        
        self.tabla_baculos = QTableWidget(0, 2)
        self.tabla_baculos.setHorizontalHeaderLabels(["ID", "Cámaras"])
        header = self.tabla_baculos.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        baculos_layout.addWidget(self.tabla_baculos)
        
        details_layout.addWidget(self.group_baculos)
        
        # Panel derecho: Visualización tipo anillo CCTV
        self.cctv_ring_view = QGraphicsView()
        self.cctv_ring_scene = QGraphicsScene()
        self.cctv_ring_view.setScene(self.cctv_ring_scene)
        self.cctv_ring_view.setMinimumHeight(260)
        self.cctv_ring_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        details_layout.addWidget(self.cctv_ring_view)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("Guardar Cambios")
        self.btn_save.clicked.connect(self._save_changes)
        btn_layout.addWidget(self.btn_save)
        
        btn_layout.addStretch()
        
        details_layout.addLayout(btn_layout)
        details_layout.addStretch()
        
        splitter.addWidget(details_widget)
        
        # Configurar proporción inicial del splitter
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
    
    def update_view(self, status_data=None):
        """Actualiza la vista con los datos del modelo."""
        window = self.window()
        # Comprobamos el tipo en tiempo de ejecución sin importar la clase
        if window.__class__.__name__ == "MainWindow":
            get_plant_id = getattr(window, "get_current_plant_id", None)
            if callable(get_plant_id):
                self.plant_id = get_plant_id()
            # Obtener modelo de red
            model = getattr(window, 'model', None)
            if isinstance(model, NetworkModel):
                self.cctv_data = model.load_cctv_config(self.plant_id)
            else:
                from constants import get_cctv_config
                self.cctv_data = get_cctv_config(self.plant_id)
        else:
            from constants import get_cctv_config
            self.cctv_data = get_cctv_config(self.plant_id)
        self.lbl_plant.setText(f"Planta: {self.plant_id}")
        self._update_tree()
        self._draw_cctv_ring()
        total_camaras = sum(data.get("camaras", 0) for data in self.cctv_data.values())
        total_baculos = sum(len(data.get("baculos", [])) for data in self.cctv_data.values())
        self.lbl_stats.setText(f"Cámaras: {total_camaras} | Báculos: {total_baculos}")
    
    def _update_tree(self):
        """Actualiza el árbol de CTs, báculos y cámaras."""
        self.tree.clear()
        icon_ct = QIcon.fromTheme("network-server")
        icon_baculo = QIcon.fromTheme("media-eject")
        icon_camara = QIcon.fromTheme("camera-video")
        for ct_id, data in sorted(self.cctv_data.items()):
            ct_item = QTreeWidgetItem([ct_id, str(data.get("camaras", 0))])
            ct_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "ct", "id": ct_id})
            ct_item.setIcon(0, icon_ct)
            for baculo_id in data.get("baculos", []):
                baculo_item = QTreeWidgetItem([baculo_id, "1"])
                baculo_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "baculo", "id": baculo_id, "parent": ct_id})
                baculo_item.setIcon(0, icon_baculo)
                cam_item = QTreeWidgetItem([f"Cámara {baculo_id}-1", "1"])
                cam_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "camara", "parent": baculo_id})
                cam_item.setIcon(0, icon_camara)
                baculo_item.addChild(cam_item)
                ct_item.addChild(baculo_item)
            self.tree.addTopLevelItem(ct_item)
        self.tree.expandAll()
    
    def _draw_cctv_ring(self):
        """Dibuja la visualización tipo anillo de CCTV."""
        self.cctv_ring_scene.clear()
        ct_list = list(self.cctv_data.keys())
        if not ct_list:
            text_item = self.cctv_ring_scene.addText("Sin CTs definidos")
            if text_item is not None:
                text_item.setPos(0, 0)
            return
        center = (0, 0)
        radius = 100
        angle_step = 2 * math.pi / max(1, len(ct_list))
        node_positions = {}
        # Dibujar CTs en círculo
        for i, ct_id in enumerate(ct_list):
            angle = i * angle_step
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            node_positions[ct_id] = (x, y)
            ellipse = self.cctv_ring_scene.addEllipse(x-18, y-18, 36, 36, QPen(QColor("#1e293b"), 2), QBrush(QColor("#60a5fa")))
            if ellipse is not None:
                ellipse.setZValue(1)
            label = self.cctv_ring_scene.addText(ct_id)
            if label is not None:
                label.setDefaultTextColor(QColor("#1e293b"))
                label.setPos(x-18, y+20)
        # Dibujar báculos y cámaras
        for ct_id, data in self.cctv_data.items():
            ct_x, ct_y = node_positions[ct_id]
            baculos = data.get("baculos", [])
            for j, baculo_id in enumerate(baculos):
                angle = math.atan2(ct_y, ct_x) + (j-len(baculos)/2)*0.25
                bx = ct_x + 50 * math.cos(angle)
                by = ct_y + 50 * math.sin(angle)
                self.cctv_ring_scene.addLine(ct_x, ct_y, bx, by, QPen(QColor("#f59e42"), 2))
                ellipse = self.cctv_ring_scene.addEllipse(bx-12, by-12, 24, 24, QPen(QColor("#b45309"), 2), QBrush(QColor("#fde68a")))
                if ellipse is not None:
                    ellipse.setZValue(1)
                label = self.cctv_ring_scene.addText(baculo_id)
                if label is not None:
                    label.setDefaultTextColor(QColor("#b45309"))
                    label.setPos(bx-12, by+14)
                # Cámara (solo una por báculo en este ejemplo)
                cx = bx + 30 * math.cos(angle)
                cy = by + 30 * math.sin(angle)
                self.cctv_ring_scene.addLine(bx, by, cx, cy, QPen(QColor("#2563eb"), 1, Qt.PenStyle.DashLine))
                ellipse = self.cctv_ring_scene.addEllipse(cx-8, cy-8, 16, 16, QPen(QColor("#2563eb"), 1), QBrush(QColor("#a5b4fc")))
                if ellipse is not None:
                    ellipse.setZValue(1)
                label = self.cctv_ring_scene.addText(f"Cam {baculo_id}-1")
                if label is not None:
                    label.setDefaultTextColor(QColor("#2563eb"))
                    label.setPos(cx-8, cy+10)
        self.cctv_ring_view.fitInView(self.cctv_ring_scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def _show_tree_context_menu(self, pos):
        """Muestra el menú contextual para el árbol."""
        item = self.tree.itemAt(pos)
        menu = QMenu(self)
        viewport = self.tree.viewport() if hasattr(self.tree, "viewport") else None
        global_pos = viewport.mapToGlobal(pos) if viewport is not None and hasattr(viewport, "mapToGlobal") else pos
        if not item:
            add_ct = menu.addAction("Añadir CT")
            action = menu.exec(global_pos)
            if action == add_ct:
                self._add_ct()
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data["type"] == "ct":
            add_baculo = menu.addAction("Añadir Báculo")
            edit_ct = menu.addAction("Editar CT")
            del_ct = menu.addAction("Eliminar CT")
            action = menu.exec(global_pos)
            if action == add_baculo:
                self._add_baculo(item)
            elif action == edit_ct:
                self._edit_ct(item)
            elif action == del_ct:
                self._delete_ct(item)
        elif data["type"] == "baculo":
            add_camara = menu.addAction("Añadir Cámara")
            edit_baculo = menu.addAction("Editar Báculo")
            del_baculo = menu.addAction("Eliminar Báculo")
            action = menu.exec(global_pos)
            if action == add_camara:
                self._add_camara(item)
            elif action == edit_baculo:
                self._edit_baculo(item)
            elif action == del_baculo:
                self._delete_baculo(item)
        elif data["type"] == "camara":
            edit_camara = menu.addAction("Editar Cámara")
            del_camara = menu.addAction("Eliminar Cámara")
            action = menu.exec(global_pos)
            if action == edit_camara:
                self._edit_camara(item)
            elif action == del_camara:
                self._delete_camara(item)
    
    def _add_ct(self):
        """Añade un nuevo CT."""
        ct_id, ok = QInputDialog.getText(self, "Nuevo CT", "ID del CT:")
        if ok and ct_id:
            self.cctv_data[ct_id] = {"camaras": 0, "baculos": []}
            self._update_tree()
    
    def _add_baculo(self, ct_item):
        """Añade un nuevo báculo a un CT."""
        baculo_id, ok = QInputDialog.getText(self, "Nuevo Báculo", "ID del Báculo:")
        if ok and baculo_id:
            ct_id = ct_item.text(0)
            self.cctv_data[ct_id]["baculos"].append(baculo_id)
            self._update_tree()
    
    def _add_camara(self, baculo_item):
        """Añade una nueva cámara a un báculo."""
        cam_id, ok = QInputDialog.getText(self, "Nueva Cámara", "ID de la Cámara:")
        if ok and cam_id:
            # Aquí puedes expandir la estructura de datos para cámaras si lo deseas
            pass
        self._update_tree()
    
    def _edit_ct(self, ct_item):
        """Edita un CT existente."""
        ct_id = ct_item.text(0)
        new_id, ok = QInputDialog.getText(self, "Editar CT", "Nuevo ID para el CT:", text=ct_id)
        if ok and new_id and new_id != ct_id:
            self.cctv_data[new_id] = self.cctv_data.pop(ct_id)
            self._update_tree()
    
    def _edit_baculo(self, baculo_item):
        """Edita un báculo existente."""
        baculo_id = baculo_item.text(0)
        new_id, ok = QInputDialog.getText(self, "Editar Báculo", "Nuevo ID para el Báculo:", text=baculo_id)
        if ok and new_id and new_id != baculo_id:
            parent_ct = baculo_item.parent().text(0)
            baculos = self.cctv_data[parent_ct]["baculos"]
            idx = baculos.index(baculo_id)
            baculos[idx] = new_id
            self._update_tree()
    
    def _edit_camara(self, cam_item):
        """Edita una cámara existente."""
        cam_id = cam_item.text(0)
        new_id, ok = QInputDialog.getText(self, "Editar Cámara", "Nuevo ID para la Cámara:", text=cam_id)
        if ok and new_id and new_id != cam_id:
            cam_item.setText(0, new_id)
    
    def _delete_ct(self, ct_item):
        """Elimina un CT existente."""
        ct_id = ct_item.text(0)
        if ct_id in self.cctv_data:
            del self.cctv_data[ct_id]
            self._update_tree()
    
    def _delete_baculo(self, baculo_item):
        """Elimina un báculo existente."""
        baculo_id = baculo_item.text(0)
        parent_ct = baculo_item.parent().text(0)
        baculos = self.cctv_data[parent_ct]["baculos"]
        if baculo_id in baculos:
            baculos.remove(baculo_id)
            self._update_tree()
    
    def _delete_camara(self, cam_item):
        """Elimina una cámara existente."""
        # Aquí puedes expandir la estructura de datos para cámaras si lo deseas
        parent_baculo = cam_item.parent().text(0)
        cam_item.parent().removeChild(cam_item)
        self._update_tree()
    
    def _save_changes(self):
        """Guarda los cambios en la configuración CCTV."""
        window = self.window()
        if window.__class__.__name__ == "MainWindow":
            model = getattr(window, 'model', None)
            if isinstance(model, NetworkModel):
                ok, msg = model.save_cctv_config(self.cctv_data, self.plant_id)
                if ok:
                    QMessageBox.information(self, "Guardar Cambios", msg)
                else:
                    QMessageBox.warning(self, "Error", msg)
                return
        QMessageBox.warning(self, "Error", "No se pudo guardar la configuración CCTV.")
    
    def reset_view(self):
        """Restablece la vista a su estado inicial."""
        # Actualizar con datos frescos
        self.update_view(None)
        
    def contextMenuEvent(self, event):
        """Muestra un menú contextual al hacer clic derecho."""
        menu = QMenu(self)
        update_action = menu.addAction("Actualizar Vista")
        if update_action is not None:
            update_action.triggered.connect(lambda: self.update_view(None))
        menu.exec(event.globalPos())
