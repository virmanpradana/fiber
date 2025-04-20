#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsPixmapItem, QMenu,
    QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtGui import QColor, QBrush, QPen, QFont, QPixmap, QPainter

# Intentar importar módulos WebEngine para mapas
WEB_ENGINE_AVAILABLE = False
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebChannel import QWebChannel
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    logging.warning("PyQt6.QtWebEngineWidgets no está disponible. Se utilizará una vista alternativa.")
    # Continuar sin WebEngine, usaremos una visualización alternativa

# Intentar importar folium para mapas
FOLIUM_AVAILABLE = False
try:
    import folium
    import tempfile
    FOLIUM_AVAILABLE = True
except ImportError:
    logging.warning("Folium no está disponible. Se utilizará una visualización alternativa.")

import json

# Importar BaseView
from ui.views.base_view import BaseView

# Importar constantes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from constants import get_plant_config

logger = logging.getLogger(__name__)

class GPSView(QWidget):
    """Vista de mapa GPS con edición interactiva usando folium y QWebEngineView."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        if WEB_ENGINE_AVAILABLE and FOLIUM_AVAILABLE:
            self._setup_channel()
            self._load_map()
        else:
            self._setup_fallback_view()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        if WEB_ENGINE_AVAILABLE and FOLIUM_AVAILABLE:
            self.web_view = QWebEngineView()
            layout.addWidget(self.web_view)
        else:
            # Esta variable la utilizaremos en el fallback
            self.web_view = None
            
    def _setup_fallback_view(self):
        """Configura una vista alternativa cuando WebEngine o Folium no están disponibles."""
        layout = self.layout()
        if layout is not None:
            # Limpiar el layout actual si tiene widgets
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget() if item is not None else None
                if widget:
                    widget.deleteLater()
            # Mensaje de error
            error_label = QLabel(
                "No se pueden mostrar mapas GPS porque faltan dependencias.\n\n"
                "Por favor, instale las siguientes dependencias:\n"
                "- PyQt6-WebEngine: pip install PyQt6-WebEngine\n"
                "- Folium: pip install folium\n\n"
                "Después de instalar, reinicie la aplicación."
            )
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: #721c24; background-color: #f8d7da; padding: 20px; border-radius: 5px;")
            install_btn = QPushButton("Instalar dependencias automáticamente")
            install_btn.clicked.connect(self._install_missing_dependencies)
            layout.addWidget(error_label)
            layout.addWidget(install_btn)
            # Only call addStretch if layout is a QVBoxLayout or QHBoxLayout
            from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout
            if isinstance(layout, (QVBoxLayout, QHBoxLayout)):
                layout.addStretch()
            # Crear una escena gráfica simple como vista alternativa
            scene = QGraphicsScene()
            view = QGraphicsView(scene)
            view.setMinimumHeight(400)
            rect = scene.addRect(0, 0, 500, 300, QPen(Qt.GlobalColor.black), QBrush(QColor("#e2e3e5")))
            text = scene.addText("Vista GPS no disponible - Faltan dependencias")
            if text is not None:
                text.setPos(150, 140)
                text.setDefaultTextColor(QColor("#383d41"))
            layout.addWidget(view)
            
    def _install_missing_dependencies(self):
        """Intenta instalar las dependencias faltantes."""
        try:
            import subprocess
            
            QMessageBox.information(
                self, "Instalando dependencias", 
                "Se intentarán instalar las dependencias faltantes.\nEsto puede tardar unos momentos."
            )
            
            missing_packages = []
            if not WEB_ENGINE_AVAILABLE:
                missing_packages.append("PyQt6-WebEngine>=6.0.0")
            if not FOLIUM_AVAILABLE:
                missing_packages.append("folium>=0.12.0")
            
            for pkg in missing_packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            
            QMessageBox.information(
                self, "Instalación completa", 
                "Las dependencias se han instalado correctamente.\n"
                "Por favor, reinicie la aplicación para aplicar los cambios."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error de instalación", 
                f"No se pudieron instalar las dependencias: {str(e)}\n"
                "Por favor, instálelas manualmente usando pip."
            )

    def _setup_channel(self):
        if not WEB_ENGINE_AVAILABLE or not FOLIUM_AVAILABLE or self.web_view is None:
            return
        self.channel = QWebChannel()
        self.channel.registerObject('gpsBridge', self)
        page = self.web_view.page() if self.web_view is not None else None
        if page is not None:
            page.setWebChannel(self.channel)

    def _load_map(self):
        if not WEB_ENGINE_AVAILABLE or not FOLIUM_AVAILABLE or self.web_view is None:
            return
        # Obtener nodos de la planta activa
        parent = self.parent()
        model = getattr(parent, 'model', None) if parent else None
        plant_id = getattr(model, 'active_plant_id', 'default') if model else 'default'
        plant_config = get_plant_config(plant_id)
        gps_positions = plant_config.get('gps_positions', {})
        # Crear mapa folium centrado
        center = (39.6, -1.9)
        if gps_positions:
            center = list(gps_positions.values())[0]
        m = folium.Map(location=center, zoom_start=15)
        # Añadir marcadores
        for node_id, coords in gps_positions.items():
            folium.Marker(
                location=coords,
                popup=node_id,
                draggable=True,
                icon=folium.Icon(color='blue' if node_id == 'SET' else 'green')
            ).add_to(m)
        # Añadir JS para edición interactiva
        html = getattr(m.get_root(), 'html', None)
        if html is not None:
            html.add_child(folium.Element(self._js_bridge_script()))
        # Guardar HTML temporal
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        m.save(tmp.name)
        self.web_view.load(QUrl.fromLocalFile(tmp.name))

    def _js_bridge_script(self):
        # JS para comunicar drag/add/delete con Python
        return '''
<script type="text/javascript">
    function connectMarkersToQt() {
        for (let i in markers) {
            let marker = markers[i];
            marker.on('dragend', function(e) {
                let pos = marker.getLatLng();
                if (window.gpsBridge) {
                    window.gpsBridge.markerMoved(marker.options.title, pos.lat, pos.lng);
                }
            });
            marker.on('click', function(e) {
                if (window.gpsBridge) {
                    window.gpsBridge.markerClicked(marker.options.title);
                }
            });
        }
    }
    if (typeof markers !== 'undefined') {
        connectMarkersToQt();
    }
</script>
'''

    @pyqtSlot(str, float, float)
    def markerMoved(self, node_id, lat, lng):
        parent = self.parent()
        model = getattr(parent, 'model', None) if parent else None
        if model and hasattr(model, 'node_positions'):
            model.node_positions[node_id] = (lat, lng)
            # Si hay método para guardar posiciones, llamarlo aquí
            if hasattr(model, 'save_gps_positions'):
                model.save_gps_positions()
        self.refresh_map()

    @pyqtSlot(str)
    def markerClicked(self, node_id):
        # Menú contextual para borrar/editar
        menu = QMenu(self)
        edit_action = menu.addAction("Editar posición")
        delete_action = menu.addAction("Eliminar nodo")
        action = menu.exec(self.cursor().pos())
        if action == edit_action:
            lat, ok1 = QInputDialog.getDouble(self, "Editar Latitud", f"Latitud para {node_id}")
            lng, ok2 = QInputDialog.getDouble(self, "Editar Longitud", f"Longitud para {node_id}")
            if ok1 and ok2:
                self.markerMoved(node_id, lat, lng)
        elif action == delete_action:
            self.delete_node(node_id)

    def add_node(self, node_id, lat, lng):
        parent = self.parent()
        model = getattr(parent, 'model', None) if parent else None
        if model and hasattr(model, 'node_positions'):
            model.node_positions[node_id] = (lat, lng)
            if hasattr(model, 'save_gps_positions'):
                model.save_gps_positions()
        self.refresh_map()

    def delete_node(self, node_id):
        parent = self.parent()
        model = getattr(parent, 'model', None) if parent else None
        if model and hasattr(model, 'node_positions') and node_id in model.node_positions:
            del model.node_positions[node_id]
            if hasattr(model, 'save_gps_positions'):
                model.save_gps_positions()
        self.refresh_map()

    def refresh_map(self):
        self._load_map()

BaseView.register(GPSView)
