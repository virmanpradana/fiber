#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import sys
import math
import random  # Necesario para simulación de fallos aleatorios en sandbox
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QGroupBox, QMessageBox, QTextEdit, QDialog, QLineEdit, 
    QDialogButtonBox, QFileDialog, QComboBox, QMenu, QFrame, QGridLayout,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem,
    QStackedWidget, QToolBar, QFormLayout, QRadioButton, QInputDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QRectF, QSize
from PyQt6.QtGui import QAction, QIcon, QPainter, QBrush, QPen, QColor, QFont, QTransform

# Usar importaciones absolutas en lugar de relativas
from ui.views.network_view import NetworkView
from ui.widgets.fiber_panel import FiberPanel  # Movido a la carpeta widgets
from ui.widgets.segment_list_widget import SegmentListWidget
from ui.widgets.statistics_panel import StatisticsPanel
from ui.widgets.status_panel import StatusPanel
from ui.widgets.ring_status_widget import RingStatusWidget
from ui.view_manager import ViewManager
from ui.widgets.sandbox_panel import SandboxPanel
from ui.views.cctv_view import CCTVView
from ui.views.gps_view import GPSView
from ui.views.layout_view import LayoutView
from ui.widgets.segment_edit_dialog import SegmentEditDialog
from ui.views.fiber_history_view import FiberHistoryView
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación Fiber Hybrid.
    Incluye visualización de red, estado, estadísticas y gestión de configuración.
    Adaptada para soportar múltiples vistas (Fibra, CCTV, GPS, Layout) y múltiples plantas.
    """
    
    # Señal emitida cuando la planta activa cambia
    plant_changed = pyqtSignal(str)
    
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.selected_segment_id = None
        self.current_status_data = None
        self.update_timer = None
        self.current_plant_id = self.model.active_plant_id
        self.current_plant_name = "Default"  # Placeholder, se cargará desde el modelo
        self.has_unsaved_changes = False  # Indicador de cambios sin guardar
        
        # Store view instances
        self.fiber_ring_view = None  # Vista de anillo de fibra
        self.cctv_view = None        # Vista CCTV (placeholder)
        self.gps_map_view = None     # Vista GPS (placeholder)
        self.layout_view = None      # Vista Layout (placeholder)
        self.fiber_history_view = None  # Vista Historial de Fibras
        
        self._init_ui()
        self._setup_menu()
        self._setup_toolbar()  # Barra de herramientas para selector de planta
        self._setup_connections()
        
        # Carga inicial de datos y actualización de UI
        self.load_initial_data()
        self._start_update_timer()
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario principal."""
        self.setWindowTitle(f"Fiber Hybrid - Diagnóstico F.O. - Planta: {self.current_plant_name}")
        self.setMinimumSize(1400, 850)  # Tamaño por defecto ligeramente mayor
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        
        # Splitter principal (división horizontal)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # --- Panel Izquierdo (Lista de Segmentos y Panel de Fibras) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.segment_list_widget = SegmentListWidget()
        left_layout.addWidget(self.segment_list_widget)

        self.fiber_panel = FiberPanel(self.model)
        self.fiber_panel.setVisible(False)
        left_layout.addWidget(self.fiber_panel)
        left_layout.addStretch()
        
        # --- Panel Central (ViewManager) ---
        self.view_manager = ViewManager()
        self.fiber_ring_view = NetworkView(self.model)
        self.cctv_view = CCTVView()
        self.gps_map_view = GPSView()
        self.layout_view = LayoutView()
        self.fiber_history_view = FiberHistoryView(self.model)
        self.view_manager.add_view("Anillo Fibra Óptica", self.fiber_ring_view, "fiber")
        self.view_manager.add_view("Anillo CCTV", self.cctv_view, "cctv")
        self.view_manager.add_view("Mapa GPS", self.gps_map_view, "gps")
        self.view_manager.add_view("Layout Topográfico", self.layout_view, "layout")
        self.view_manager.add_view("Historial de Fibras", self.fiber_history_view, "fiber_history")
        
        # Panel inferior central (estado/sugerencias)
        self.status_panel = StatusPanel()
        bottom_central_panel = QWidget()
        bottom_central_layout = QVBoxLayout(bottom_central_panel)
        bottom_central_layout.setContentsMargins(0, 0, 0, 0)
        bottom_central_layout.addWidget(self.status_panel)
        
        # Splitter vertical para vista principal y estado/sugerencias
        central_splitter = QSplitter(Qt.Orientation.Vertical)
        central_splitter.addWidget(self.view_manager)
        central_splitter.addWidget(bottom_central_panel)
        central_splitter.setSizes([650, 150])
        
        # --- Panel Derecho (Estadísticas y Anillo Simplificado) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.statistics_panel = StatisticsPanel()
        self.statistics_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.statistics_panel)
        self.ring_status_widget = RingStatusWidget()
        self.ring_status_widget.setMinimumHeight(250)
        self.ring_status_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.ring_status_widget)
        right_layout.addStretch()
        refresh_button = QPushButton(QIcon.fromTheme("view-refresh"), "Actualizar Ahora")
        refresh_button.clicked.connect(self.update_network_status)
        right_layout.addWidget(refresh_button)
        
        # --- Añadir Paneles al Splitter Principal ---
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(central_splitter)  # Añadir el splitter vertical aquí
        self.main_splitter.addWidget(right_panel)
        
        # División inicial del splitter principal
        self.main_splitter.setSizes([250, 750, 400])  # Tamaños ajustados
        
        # --- Panel de Notificaciones ---
        self.notification_frame = QFrame(self)
        self.notification_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.notification_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.notification_frame.setStyleSheet("background-color: #e0f2fe; border: 1px solid #0284c7; border-radius: 4px; padding: 5px;")
        self.notification_frame.setMaximumHeight(80)
        
        notification_layout = QHBoxLayout(self.notification_frame)  # QHBoxLayout para icono + texto
        self.notification_icon_label = QLabel()  # Placeholder para icono
        self.notification_label = QLabel("")
        notification_layout.addWidget(self.notification_icon_label)
        notification_layout.addWidget(self.notification_label, 1)  # Estirar etiqueta
        
        self.notification_frame.setVisible(False)
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.addPermanentWidget(self.notification_frame, 1)

        # --- Panel de Sandbox (ahora modular) ---
        self.sandbox_panel = SandboxPanel()
        self.sandbox_panel.setVisible(False)
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.addPermanentWidget(self.sandbox_panel)
    
    def _setup_menu(self):
        """Configura la barra de menú."""
        menubar = self.menuBar()
        if menubar is None:
            return
        
        # Menú Archivo
        file_menu = menubar.addMenu("Archivo") if hasattr(menubar, 'addMenu') else None
        if file_menu is not None:
            # Acción Nuevo
            new_action = QAction("Nueva Configuración", self)
            new_action.setShortcut("Ctrl+N")
            new_action.triggered.connect(self.new_configuration)
            file_menu.addAction(new_action)
            
            # Acción Cargar
            load_action = QAction("Cargar Configuración...", self)
            load_action.setShortcut("Ctrl+O")
            load_action.triggered.connect(self.load_configuration)
            file_menu.addAction(load_action)
            
            # Acción Guardar
            save_action = QAction("Guardar Configuración", self)
            save_action.setShortcut("Ctrl+S")
            save_action.triggered.connect(self.save_configuration)
            file_menu.addAction(save_action)
            
            file_menu.addSeparator()
            
            # Acción Exportar Diagnóstico
            export_action = QAction("Exportar Diagnóstico", self)
            export_action.setShortcut("Ctrl+E")
            export_action.triggered.connect(self.export_diagnostic)
            file_menu.addAction(export_action)
            
            # Acción Salir
            exit_action = QAction("Salir", self)
            exit_action.setShortcut("Ctrl+Q")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)
        
        # Menú Ver
        view_menu = menubar.addMenu("Ver") if hasattr(menubar, 'addMenu') else None
        if view_menu is not None:
            # Acción Refrescar
            refresh_action = QAction("Refrescar", self)
            refresh_action.setShortcut("F5")
            refresh_action.triggered.connect(self.update_network_status)
            view_menu.addAction(refresh_action)
            
            # Acción Reset Vista
            reset_view_action = QAction("Restablecer Vista", self)
            reset_view_action.triggered.connect(self.reset_active_view)
            view_menu.addAction(reset_view_action)
            
            # Acción Historial de Fibras
            fiber_history_action = QAction("Historial de Fibras", self)
            # Buscar el índice de la vista 'fiber_history' en el ViewManager
            def get_view_index_by_key(key):
                for i in range(self.view_manager.combo.count()):
                    if self.view_manager.combo.itemData(i) == key:
                        return i
                return -1
            fiber_history_action.triggered.connect(lambda: self.view_manager.set_current_index(get_view_index_by_key("fiber_history")))
            view_menu.addAction(fiber_history_action)
        
        # Menú Herramientas
        tools_menu = menubar.addMenu("Herramientas") if hasattr(menubar, 'addMenu') else None
        if tools_menu is not None:
            # Acción Sandbox
            sandbox_action = QAction("Panel de Pruebas (Sandbox)", self)
            sandbox_action.setCheckable(True)
            sandbox_action.setChecked(False)
            sandbox_action.toggled.connect(self.toggle_sandbox_panel)
            tools_menu.addAction(sandbox_action)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("Ayuda") if hasattr(menubar, 'addMenu') else None
        if help_menu is not None:
            # Acción Acerca de
            about_action = QAction("Acerca de", self)
            about_action.triggered.connect(self.show_about)
            help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Configura la barra de herramientas con selector de planta."""
        toolbar = QToolBar("Plantas")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        # Etiqueta para el selector de planta
        toolbar.addWidget(QLabel("Planta: "))
        
        # Combo box para seleccionar planta
        self.plant_selector_combo = QComboBox()
        self.plant_selector_combo.setMinimumWidth(120)
        self.plant_selector_combo.currentIndexChanged.connect(self.on_plant_changed)
        toolbar.addWidget(self.plant_selector_combo)
        
        # Botones para gestión de plantas
        self.btn_new_plant = QPushButton("Nueva")
        self.btn_new_plant.setToolTip("Crear una nueva planta")
        self.btn_new_plant.clicked.connect(self.on_new_plant)
        toolbar.addWidget(self.btn_new_plant)
        
        self.btn_rename_plant = QPushButton("Renombrar")
        self.btn_rename_plant.setToolTip("Renombrar la planta actual")
        self.btn_rename_plant.clicked.connect(self.on_rename_plant)
        toolbar.addWidget(self.btn_rename_plant)
        
        self.btn_delete_plant = QPushButton("Eliminar")
        self.btn_delete_plant.setToolTip("Eliminar la planta seleccionada")
        self.btn_delete_plant.clicked.connect(self.on_delete_plant)
        toolbar.addWidget(self.btn_delete_plant)
        
        # Separador
        toolbar.addSeparator()
        
        # Información de la planta
        self.lbl_plant_info = QLabel()
        toolbar.addWidget(self.lbl_plant_info)
    
    def _setup_connections(self):
        """Configura las conexiones entre señales y slots."""
        # Selección de segmento en la lista
        self.segment_list_widget.segment_selected.connect(self.on_segment_selected)

        # Conexiones del panel de segmentos para gestión avanzada
        self.segment_list_widget.segment_created.connect(self.on_segment_create)
        self.segment_list_widget.segment_edited.connect(self.on_segment_edit)
        self.segment_list_widget.segment_deleted.connect(self.on_segment_delete)
        self.segment_list_widget.segment_moved_up.connect(self.on_segment_move_up)
        self.segment_list_widget.segment_moved_down.connect(self.on_segment_move_down)

        # Selección de segmento en la vista de red (asumiendo NetworkView es la vista de fibra)
        if isinstance(self.fiber_ring_view, NetworkView):
            self.fiber_ring_view.segment_selected.connect(self.select_segment_by_id)
        # TODO: Connect segment selection signals from other views (CCTV, Layout) if they support it

        # Panel de fibras
        self.fiber_panel.fiber_status_changed.connect(self.on_fiber_status_changed)
        self.fiber_panel.restore_all_requested.connect(self.on_restore_all_fibers)

        # Selector de Vista
        self.view_manager.view_changed.connect(self.on_view_changed)

        # Selector de Planta
        self.plant_selector_combo.currentIndexChanged.connect(self.on_plant_changed)

        # Cambio de planta (custom signal)
        self.plant_changed.connect(self.handle_plant_change)

        # Conexiones del panel de Sandbox
        self.sandbox_panel.simulate_failure.connect(self._simulate_failure)
        self.sandbox_panel.restore_selected_segment.connect(self._restore_selected_segment_fibers)
        self.sandbox_panel.simulate_random_failure.connect(self._simulate_random_failure)
        self.sandbox_panel.restore_all_segments.connect(self._restore_all_segments)
    
    def _start_update_timer(self):
        """Inicia el temporizador para actualizaciones periódicas."""
        if not self.update_timer:
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.update_network_status)
            self.update_timer.start(5000)  # Actualización cada 5 segundos
    
    def reset_active_view(self):
        """Restablece el zoom y la posición de la vista activa."""
        active_widget = self.view_manager.current_widget()

        if isinstance(active_widget, QGraphicsView):
            # Verificar si scene es un método o una propiedad
            if hasattr(active_widget, 'scene'):
                if callable(active_widget.scene):
                    scene = active_widget.scene()
                else:
                    scene = active_widget.scene
            else:
                scene = None
                
            if scene is not None and hasattr(scene, 'items'):
                try:
                    # Limitar el tiempo para esta operación
                    items = scene.items()
                    if items:
                        if hasattr(scene, 'itemsBoundingRect'):
                            items_rect = scene.itemsBoundingRect()
                            if items_rect is not None and not items_rect.isNull():
                                padding = 30
                                adjusted_rect = items_rect.adjusted(-padding, -padding, padding, padding)
                                active_widget.fitInView(adjusted_rect, Qt.AspectRatioMode.KeepAspectRatio)
                            else:
                                active_widget.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                        else:
                            active_widget.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                except Exception as e:
                    logger.error(f"Error al restablecer vista: {e}")
                    active_widget.resetTransform()  # Reset más simple si falla el fitInView
        elif hasattr(active_widget, 'reset_view') and callable(getattr(active_widget, 'reset_view', None)):
            active_widget.reset_view()  # type: ignore[attr-defined]
        elif isinstance(active_widget, QLabel):
            pass
        else:
            logger.warning(f"No se pudo restablecer la vista para el widget tipo: {type(active_widget)}")
            self.show_notification("No se puede restablecer esta vista.", level='info')

        # También aplicamos la misma corrección para el ring_canvas
        ring_canvas = getattr(self.ring_status_widget, 'ring_view_canvas', None)
        if ring_canvas is not None and isinstance(ring_canvas, QGraphicsView):
            # Verificar si scene es un método o una propiedad
            if hasattr(ring_canvas, 'scene'):
                if callable(ring_canvas.scene):
                    scene = ring_canvas.scene()
                else:
                    scene = ring_canvas.scene
            else:
                scene = None
                
            if scene is not None and hasattr(scene, 'items'):
                try:
                    items = scene.items()
                    if items:
                        if hasattr(scene, 'itemsBoundingRect'):
                            items_rect = scene.itemsBoundingRect()
                            if items_rect is not None and not items_rect.isNull():
                                padding = 30
                                adjusted_rect = items_rect.adjusted(-padding, -padding, padding, padding)
                                ring_canvas.fitInView(adjusted_rect, Qt.AspectRatioMode.KeepAspectRatio)
                            else:
                                ring_canvas.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                        else:
                            ring_canvas.fitInView(scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                except Exception as e:
                    logger.error(f"Error al restablecer vista del anillo: {e}")
                    ring_canvas.resetTransform()  # Reset más simple si falla el fitInView

    def update_network_status(self):
        if getattr(self, '_updating_network_status', False):
            return
        self._updating_network_status = True
        try:
            """Actualiza el estado de la red y la interfaz."""
            try:
                self.current_status_data = self.model.get_network_status()
                # Si el modelo devolvió un error, no intentes actualizar la UI
                if (
                    not self.current_status_data
                    or not isinstance(self.current_status_data, dict)
                    or not self.current_status_data.get('segment_statuses')
                    or "RecursionError" in str(self.current_status_data.get('suggestions', ''))
                ):
                    print("\n[ERROR ACTUALIZANDO ESTADO DE RED] RecursionError: El grafo es demasiado profundo o está corrupto.")
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Error de recursión: El grafo de red es demasiado profundo o está corrupto.\nRevise la configuración de la red."
                    )
                    return
                self.update_ui()
            except RecursionError:
                print("\n[ERROR ACTUALIZANDO ESTADO DE RED] RecursionError: El grafo es demasiado profundo o está corrupto.")
                # No QMessageBox ni logging aquí para evitar más recursión
                return
            except Exception as e:
                print("\n[ERROR ACTUALIZANDO ESTADO DE RED]", e)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error actualizando estado de red: {e}"
                )
        finally:
            self._updating_network_status = False
    
    def update_ui(self):
        """Actualiza todos los elementos de la interfaz con los datos actuales."""
        try:
            # Si el modelo devolvió un error, no intentes actualizar la UI
            if (
                not self.current_status_data
                or not isinstance(self.current_status_data, dict)
                or not self.current_status_data.get('segment_statuses')
                or "RecursionError" in str(self.current_status_data.get('suggestions', ''))
            ):
                self.segment_list_widget.set_segments([], None)
                self.fiber_panel.setVisible(False)
                self.status_panel.set_suggestions(["Error: El grafo es demasiado profundo o está corrupto."])
            self.update_statistics()
            if self.selected_segment_id:
                self.fiber_panel.set_segment(
                    self.selected_segment_id,
                    self.get_segment_data(self.selected_segment_id)
                )
        except RecursionError:
            print("[ERROR] RecursionError: El grafo es demasiado profundo o está corrupto (update_ui).")
            QMessageBox.critical(
                self,
                "Error",
                "Error de recursión: El grafo de red es demasiado profundo o está corrupto.\nRevise la configuración de la red."
            )
        except Exception as e:
            print(f"[ERROR] Error actualizando la UI: {e}")
            QMessageBox.warning(self, "Error en la Interfaz", f"Ocurrió un error actualizando la interfaz: {e}")

    def update_segment_list(self):
        """Actualiza la lista de segmentos con los datos actuales."""
        if isinstance(self.current_status_data, dict):
            segments = self.current_status_data.get('segment_statuses', []) if self.current_status_data else []
            self.segment_list_widget.set_segments(segments, self.selected_segment_id)
    
    def update_status_panel(self):
        """Actualiza el panel de estado con las sugerencias."""
        if not self.current_status_data:
            return
        
        suggestions = self.current_status_data.get('suggestions', ["No hay sugerencias disponibles."])
        self.status_panel.set_suggestions(suggestions)
    
    def update_statistics(self):
        """Actualiza las estadísticas mostradas."""
        if not self.current_status_data:
            return
        
        # Contar estados de CT
        ct_statuses = self.current_status_data.get('ct_connectivity', {})
        connected = sum(1 for status in ct_statuses.values() if status == 'conectado')
        isolated = sum(1 for status in ct_statuses.values() if status == 'aislado')
        error = sum(1 for status in ct_statuses.values() if status == 'error')
        self.statistics_panel.update_ct_stats(connected, isolated, error)
        
        # Obtener estadísticas de fibras
        segments = self.current_status_data.get('segment_statuses', []) if self.current_status_data else []
        fiber_stats = self.model.get_fiber_statistics(segments)
        
        # Actualizar estadísticas de fibras
        comm_ok = fiber_stats.get('comm_ok', 0)
        comm_total = fiber_stats.get('comm_total', 0)
        reserve_ok = fiber_stats.get('reserve_ok', 0)
        reserve_total = fiber_stats.get('reserve_total', 0)
        cctv_ok = fiber_stats.get('cctv_ok', 0)
        cctv_total = fiber_stats.get('cctv_total', 0)
        self.statistics_panel.update_fiber_stats(comm_ok, comm_total, reserve_ok, reserve_total, cctv_ok, cctv_total)
        
        # Verificar integridad del anillo
        try:
            ring_status = self.model._check_ring_integrity()
            all_ok = all(ring_status.values())
            
            if all_ok:
                self.ring_status_widget.status_label.setText("Estado: ✅ Anillo completo")
                self.ring_status_widget.status_label.setStyleSheet("color: #16a34a;")
            else:
                broken_count = sum(1 for status in ring_status.values() if not status)
                total_count = len(ring_status)
                self.ring_status_widget.status_label.setText(f"Estado: ⚠️ Anillo incompleto ({broken_count}/{total_count} fallos)")
                self.ring_status_widget.status_label.setStyleSheet("color: #f97316;")
            
            # Actualizar visualización circular del anillo
            self.update_ring_visualization(ring_status)
        except Exception as e:
            logger.error(f"Error verificando integridad del anillo: {e}")
            self.ring_status_widget.status_label.setText(f"Estado: ❌ Error verificando anillo")
            self.ring_status_widget.status_label.setStyleSheet("color: #dc2626;")
    
    def update_ring_visualization(self, ring_status):
        """Actualiza la visualización circular del anillo con el estado actual."""
        try:
            widget = self.ring_status_widget
            if not hasattr(widget, 'ring_view_canvas') or not ring_status:
                return
            scene = widget.ring_view_canvas.scene() if hasattr(widget.ring_view_canvas, 'scene') else None
            if scene is None:
                return
            if hasattr(scene, 'clear'):
                scene.clear()
            
            # Configurar escena
            center_x = 0
            center_y = 0
            radius = 70
            node_radius = 12
            
            # Colores
            node_color = QColor("#3b82f6")  # Color principal de nodos
            ok_color = QColor("#16a34a")    # Verde para conexiones OK
            fault_color = QColor("#dc2626") # Rojo para conexiones fallidas
            
            # Importar correctamente DEFAULT_RING_ORDER desde el módulo network_model
            try:
                from model.network_model import DEFAULT_RING_ORDER as circuit_order
            except ImportError:
                circuit_order = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]
                logger.warning("No se pudo importar DEFAULT_RING_ORDER, usando valores por defecto")
            
            if not circuit_order:
                if hasattr(scene, 'addText'):
                    scene.addText("No hay circuitos definidos")
                return
                
            # Calcular posiciones de los nodos en círculo
            positions = {}
            node_items = {}
            angle_step = 2 * 3.14159 / len(circuit_order)
            
            for i, circuit_id in enumerate(circuit_order):
                angle = i * angle_step
                pos_x = center_x + radius * math.cos(angle)
                pos_y = center_y + radius * math.sin(angle)
                positions[circuit_id] = (pos_x, pos_y)
                
                # Crear nodo
                node = QGraphicsEllipseItem(
                    pos_x - node_radius, 
                    pos_y - node_radius, 
                    node_radius * 2, 
                    node_radius * 2
                )
                node.setBrush(QBrush(node_color))
                node.setPen(QPen(QColor("#1e3a8a"), 1.5))
                if hasattr(scene, 'addItem'):
                    scene.addItem(node)
                node_items[circuit_id] = node
                
                # Etiqueta del circuito
                label = QGraphicsTextItem(circuit_id)
                font = QFont("Segoe UI", 8, QFont.Weight.Bold)
                label.setFont(font)
                label.setDefaultTextColor(QColor("#1e293b"))
                label_width = label.boundingRect().width()
                label_height = label.boundingRect().height()
                label.setPos(pos_x - label_width/2, pos_y - label_height/2)
                if hasattr(scene, 'addItem'):
                    scene.addItem(label)
            
            # Dibujar conexiones entre nodos
            for i in range(len(circuit_order)):
                circuit_actual = circuit_order[i]
                circuit_siguiente = circuit_order[(i + 1) % len(circuit_order)]
                key = f"{circuit_actual}-{circuit_siguiente}"
                
                if key in ring_status:
                    status_ok = ring_status[key]
                    
                    # Obtener posiciones
                    x1, y1 = positions[circuit_actual]
                    x2, y2 = positions[circuit_siguiente]
                    
                    # Crear línea con estado
                    pen = QPen(ok_color if status_ok else fault_color, 2)
                    if not status_ok:
                        pen.setStyle(Qt.PenStyle.DashLine)
                        
                    line = QGraphicsLineItem(x1, y1, x2, y2)
                    line.setPen(pen)
                    if hasattr(scene, 'addItem'):
                        scene.addItem(line)
                    
                    # Colocar línea detrás de los nodos
                    line.setZValue(-1)
            
            # Ajustar vista
            if hasattr(scene, 'itemsBoundingRect'):
                rect = scene.itemsBoundingRect()
                if rect is not None and not rect.isNull():
                    widget.ring_view_canvas.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            
            # Actualizar texto de estado
            all_ok = all(ring_status.values())
            if all_ok:
                widget.status_label.setText("Estado: ✅ Anillo completo")
                widget.status_label.setStyleSheet("color: #16a34a;")
            else:
                broken_count = sum(1 for status in ring_status.values() if not status)
                total_count = len(ring_status)
                widget.status_label.setText(f"Estado: ⚠️ Anillo incompleto ({broken_count}/{total_count} fallos)")
                widget.status_label.setStyleSheet("color: #f97316;")
                
            # Detalles de conexiones en el widget de texto
            details = "<html><body><pre>\n"
            for key, status in ring_status.items():
                if "-" in key:
                    from_circuit, to_circuit = key.split("-")
                    icon = "✅" if status else "❌"
                    details += f"{from_circuit} → {to_circuit}: {icon}\n"
            details += "</pre></body></html>"
            widget.ring_view_text.setHtml(details)
        except Exception as e:
            logger.error(f"Error en la visualización del anillo: {e}", exc_info=True)
            QMessageBox.warning(self, "Error en Visualización", f"Ocurrió un error en la visualización del anillo: {e}")
    
    def show_notification(self, message, level='info', duration=3000):
        """Muestra una notificación temporal.
        
        Args:
            message: Mensaje a mostrar
            level: Nivel ('info', 'success', 'warning', 'error')
            duration: Duración en milisegundos
        """
        # Configurar estilo según nivel
        style = {
            'info': "background-color: #e0f2fe; border: 1px solid #0284c7;",
            'success': "background-color: #dcfce7; border: 1px solid #16a34a;",
            'warning': "background-color: #fef9c3; border: 1px solid #ca8a04;",
            'error': "background-color: #fee2e2; border: 1px solid #dc2626;"
        }
        
        self.notification_frame.setStyleSheet(style.get(level, style['info']))
        self.notification_label.setText(message)
        self.notification_frame.setVisible(True)
        
        # Programar ocultamiento
        QTimer.singleShot(duration, lambda: self.notification_frame.setVisible(False))
    
    def on_segment_selected(self, segment_data=None):
        """Maneja la selección de un segmento en la lista."""
        if segment_data is None:
            self.selected_segment_id = None
            self.fiber_panel.setVisible(False)
            if self.fiber_ring_view is not None and hasattr(self.fiber_ring_view, 'highlight_segment'):
                self.fiber_ring_view.highlight_segment(None)
            self._update_sandbox_label()
            return
        segment_id = segment_data.get('id') if segment_data is not None else None
        self.selected_segment_id = segment_id
        if self.fiber_ring_view is not None and hasattr(self.fiber_ring_view, 'highlight_segment'):
            self.fiber_ring_view.highlight_segment(segment_id)
        self.fiber_panel.set_segment(segment_id, segment_data)
        self.fiber_panel.setVisible(True)
        self._update_sandbox_label()

    def on_segment_create(self):
        """Crea un nuevo segmento."""
        ct_list = sorted([n for n, d in self.model.G.nodes(data=True) if d.get('type') == 'ct'])
        dialog = SegmentEditDialog(ct_list, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            success, msg = self.model.add_segment(data)
            if success:
                self.mark_unsaved_changes()
                self.update_network_status()
            else:
                QMessageBox.warning(self, "Error", msg)

    def on_segment_edit(self, segment):
        """Edita un segmento existente."""
        ct_list = sorted([n for n, d in self.model.G.nodes(data=True) if d.get('type') == 'ct'])
        dialog = SegmentEditDialog(ct_list, segment, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            # Fix for line 953: Add None check before calling get()
            segment_id = segment.get('id') if segment is not None else None
            success, msg = self.model.edit_segment(segment_id, data)
            if success:
                self.mark_unsaved_changes()
                self.update_network_status()
            else:
                QMessageBox.warning(self, "Error", msg)

    def on_segment_delete(self, segment):
        """Elimina un segmento."""
        # Fix for line 990: Add None check before calling get()
        segment_id = segment.get('id') if segment is not None else None
        segment_name = segment_id if segment_id else "desconocido"
        reply = QMessageBox.question(self, "Eliminar segmento", f"¿Eliminar el segmento '{segment_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.model.delete_segment(segment_id)
            if success:
                self.mark_unsaved_changes()
                self.update_network_status()
            else:
                QMessageBox.warning(self, "Error", msg)

    def on_segment_move_up(self, segment):
        """Mueve un segmento hacia arriba."""
        success, msg = self.model.move_segment(segment.get('id') if segment is not None else None, direction='up')
        if success:
            self.mark_unsaved_changes()
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", msg)

    def on_segment_move_down(self, segment):
        """Mueve un segmento hacia abajo."""
        success, msg = self.model.move_segment(segment.get('id') if segment is not None else None, direction='down')
        if success:
            self.mark_unsaved_changes()
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", msg)

    def select_segment_by_id(self, segment_id):
        """Selecciona un segmento por su ID."""
        self.segment_list_widget.clear_selection()
        if isinstance(self.current_status_data, dict):
            segments = self.current_status_data.get('segment_statuses', [])
            for segment in segments:
                if segment.get('id') == segment_id:
                    self.segment_list_widget.set_segments(segments, segment_id)
                    break
    
    def get_segment_data(self, segment_id):
        """Obtiene los datos de un segmento por su ID."""
        if isinstance(self.current_status_data, dict):
            segments = self.current_status_data.get('segment_statuses', [])
            for segment in segments:
                if segment.get('id') == segment_id:
                    return segment
        return None
    
    def on_fiber_status_changed(self, segment_id, fiber_num, new_status):
        """Maneja el cambio de estado de una fibra."""
        # Actualizar modelo
        success, message = self.model.update_fiber_status(segment_id, fiber_num, new_status)
        
        if success:
            # Marcar cambios sin guardar
            self.mark_unsaved_changes()
            
            # Actualizar inmediatamente el estado
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def on_restore_all_fibers(self, segment_id):
        """Restaura todas las fibras de un segmento a estado 'ok'."""
        if not segment_id:
            return
        
        # Usar el método del modelo para restaurar las fibras
        success, message = self.model.restore_segment_fibers(segment_id)
        
        if success:
            # Marcar cambios sin guardar
            self.mark_unsaved_changes()
            
            # Mostrar notificación temporal
            self.show_notification(message, 'success')
            
            # Actualizar estado
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def new_configuration(self):
        """Crea una nueva configuración."""
        # Confirmar si hay cambios sin guardar
        reply = QMessageBox.question(
            self,
            "Nueva Configuración",
            "¿Crear nueva configuración? Se perderán los cambios no guardados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reiniciar modelo con configuración por defecto
            self.model._init_graph(None)
            self.model.node_positions = {}
            
            # Actualizar interfaz
            self.update_network_status()
    
    def load_configuration(self):
        """Carga una configuración para la planta actual."""
        if not self.model.storage:
            QMessageBox.warning(self, "Error", "No hay sistema de almacenamiento configurado.")
            return

        try:
            # Listar configs específicas para la planta actual
            configs = self.model.list_configurations(self.current_plant_id)
            
            if not configs:
                QMessageBox.information(
                    self, 
                    "Información", 
                    f"No hay configuraciones guardadas para la planta '{self.current_plant_name}'."
                )
                return

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Cargar Configuración ({self.current_plant_name})")
            dialog.setMinimumWidth(350)
            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel(f"Seleccione una configuración para '{self.current_plant_name}':"))
            
            combo = QComboBox()
            for config in configs:
                combo.addItem(config["name"], config["name"])
            layout.addWidget(combo)
            
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_name = combo.currentData()
                if selected_name:
                    success, message = self.model.load_configuration(selected_name, self.current_plant_id)
                    if success:
                        self.show_notification(message, 'success')
                        self.update_network_status()  # Refresh UI with loaded config
                    else:
                        QMessageBox.warning(self, "Error", message)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error cargando configuración: {str(e)}")
    
    def save_configuration(self):
        """Guarda la configuración actual."""
        if not self.model.storage:
            QMessageBox.warning(self, "Error", "No hay sistema de almacenamiento configurado.")
            return

        # Pedir nombre de configuración
        name, ok = QInputDialog.getText(
            self, 
            "Guardar Configuración", 
            f"Nombre para la configuración de planta '{self.current_plant_name}':",
            QLineEdit.EchoMode.Normal, 
            ""
        )
        
        if ok and name.strip():
            success, message = self.model.save_configuration(name, self.current_plant_id)
            if success:
                self.show_notification(message, 'success')
            else:
                QMessageBox.warning(self, "Error", message)

    def get_current_plant_id(self):
        """Obtiene el ID de la planta actualmente seleccionada."""
        return self.current_plant_id

    def export_diagnostic(self):
        """Exporta el diagnóstico actual a un archivo de texto."""
        # Solicitar ruta de archivo
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Diagnóstico",
            os.path.join(os.path.dirname(self.model.storage.db_path), 
                        f"diagnostico_{self.current_plant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"),
            "Archivos de texto (*.txt)"
        )
        
        if not file_path:
            return  # Usuario canceló
        
        # Llamar al método del modelo para exportar
        success, message = self.model.export_diagnostic(file_path)
        
        if success:
            self.show_notification(message, 'success')
        else:
            QMessageBox.warning(self, "Error", message)
    
    def show_about(self):
        """Muestra información sobre la aplicación."""
        from datetime import datetime
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        QMessageBox.about(
            self,
            "Acerca de Fiber Hybrid",
            f"Fiber Hybrid - Prueba de Concepto\n\n"
            f"Versión: 1.0\n"
            f"Fecha: {fecha_actual}\n\n"
            "Una demostración de aplicación híbrida Python/Rust/Qt\n"
            "para diagnóstico de redes de fibra óptica.\n\n"
            "© 2025 virmanpradana"
        )
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana."""
        # Detener temporizador
        if self.update_timer:
            self.update_timer.stop()
        
        # Cerrar conexión a la base de datos
        if self.model.storage:
            self.model.storage.close()
        
        # Aceptar cierre
        event.accept()
    
    def toggle_sandbox_panel(self, checked):
        """Muestra u oculta el panel de Sandbox."""
        self.sandbox_panel.setVisible(checked)
    
    def _simulate_failure(self, fiber_num):
        """Simula un fallo en una fibra específica del segmento seleccionado."""
        if not self.selected_segment_id:
            QMessageBox.warning(
                self,
                "Segmento no seleccionado",
                "Seleccione primero un segmento en la lista para simular un fallo."
            )
            return
        
        logger.info(f"Simulando fallo en fibra {fiber_num} del segmento {self.selected_segment_id}")
        
        # Actualizar estado en el modelo
        success, message = self.model.update_fiber_status(self.selected_segment_id, fiber_num, 'averiado')
        
        if success:
            level = 'warning' if 'actualizada a' in message else 'info'
            self.show_notification(message, level=level)
            
            # Actualizar interfaz
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def _restore_selected_segment_fibers(self):
        """Restaura todas las fibras del segmento seleccionado a estado OK."""
        if not self.selected_segment_id:
            QMessageBox.warning(
                self,
                "Segmento no seleccionado",
                "Seleccione primero un segmento en la lista para restaurar sus fibras."
            )
            return
        
        logger.info(f"Restaurando todas las fibras en segmento {self.selected_segment_id}")
        
        # Restaurar con el método del modelo
        success, message = self.model.restore_segment_fibers(self.selected_segment_id)
        
        if success:
            self.show_notification(message, level='success')
            
            # Actualizar interfaz
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def _simulate_random_failure(self):
        """Simula un fallo aleatorio en alguna fibra de la red."""
        import random
        
        # Obtener segmentos disponibles
        if not self.current_status_data:
            self.update_network_status()
        
        segments = self.current_status_data.get('segment_statuses', []) # type: ignore
        
        if not segments:
            QMessageBox.warning(self, "Error", "No hay segmentos disponibles")
            return
        
        # Seleccionar segmento aleatorio
        segment = random.choice(segments)
        segment_id = segment.get('id') if segment is not None else None
        
        # Seleccionar fibra aleatoria (1-16)
        fiber_num = random.randint(1, 16)
        
        logger.info(f"Simulando fallo aleatorio en fibra {fiber_num} del segmento {segment_id}")
        
        # Actualizar estado
        success, message = self.model.update_fiber_status(segment_id, fiber_num, 'averiado')
        
        if success:
            self.show_notification(
                f"Fallo aleatorio simulado: {message}",
                level='warning'
            )
            
            # Actualizar interfaz
            self.update_network_status()
            
            # Seleccionar el segmento afectado
            self.select_segment_by_id(segment_id)
        else:
            QMessageBox.warning(self, "Error", message)
    
    def _restore_all_segments(self):
        """Restaura todas las fibras de todos los segmentos a estado OK."""
        if not self.current_status_data:
            self.update_network_status()
        
        segments = self.current_status_data.get('segment_statuses', []) # type: ignore
        
        if not segments:
            QMessageBox.warning(self, "Error", "No hay segmentos para restaurar")
            return
        
        restored_count = 0
        segments_count = 0
        
        for segment in segments:
            segment_id = segment.get('id') if segment is not None else None
            success, message = self.model.restore_segment_fibers(segment_id)
            
            if success:
                segments_count += 1
                if "fibras restauradas" in message:
                    # Extraer número de fibras restauradas
                    try:
                        fibers_count = int(message.split()[0])
                        restored_count += fibers_count
                    except:
                        pass
        
        if segments_count > 0:
            self.show_notification(
                f"Restaurados {segments_count} segmentos ({restored_count} fibras en total)",
                level='success'
            )
            
            # Actualizar interfaz
            self.update_network_status()
        else:
            QMessageBox.warning(self, "Error", "No se pudo restaurar ningún segmento")
    
    def zoom_wheel_event(self, event):
        """Maneja la rueda del ratón para hacer zoom en QGraphicsView."""
        if not self.ring_status_widget.ring_view_canvas.scene(): 
            return  # No hay escena, no hacer nada
        
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        # Guardar la posición de la escena bajo el cursor
        old_pos = self.ring_status_widget.ring_view_canvas.mapToScene(event.position().toPoint())
        
        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.ring_status_widget.ring_view_canvas.scale(zoom_factor, zoom_factor)
        
        # Obtener la nueva posición de la escena bajo el cursor
        new_pos = self.ring_status_widget.ring_view_canvas.mapToScene(event.position().toPoint())
        
        # Mover la escena para mantener el punto bajo el cursor
        delta = new_pos - old_pos
        self.ring_status_widget.ring_view_canvas.translate(delta.x(), delta.y())
    
    def _update_sandbox_label(self):
        """Actualiza la etiqueta en el panel sandbox con el segmento seleccionado."""
        self.sandbox_panel.set_selected_segment(self.selected_segment_id)
    
    def on_view_changed(self, index):
        """Cambia la vista mostrada en el ViewManager y actualiza la vista si es necesario."""
        self.view_manager.set_current_index(index)
        active_widget = self.view_manager.current_widget()
        if active_widget is not None and hasattr(active_widget, 'update_view') and callable(getattr(active_widget, 'update_view', None)):
            if self.current_status_data:
                active_widget.update_view(self.current_status_data)  # type: ignore[attr-defined]
            else:
                self.update_network_status()
    
    def on_plant_changed(self, index):
        """Maneja el cambio de planta seleccionada."""
        if index < 0 or self.plant_selector_combo.count() == 0:
            return
            
        plant_id = self.plant_selector_combo.itemData(index)
        if plant_id == self.current_plant_id:
            return  # No ha cambiado
            
        logger.info(f"Cambiando a planta: {plant_id}")
        self.handle_plant_change(plant_id)
    
    def handle_plant_change(self, plant_id):
        """Gestiona el cambio de planta activa."""
        # Verificar si hay cambios sin guardar
        if self.has_unsaved_changes:
            # Mostrar diálogo de confirmación
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "¿Desea continuar con la iteración? Se perderán los cambios no guardados.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                # Cancelar cambio de planta y restaurar combo box
                index = self.plant_selector_combo.findData(self.current_plant_id)
                if index >= 0:
                    self.plant_selector_combo.blockSignals(True)
                    self.plant_selector_combo.setCurrentIndex(index)
                    self.plant_selector_combo.blockSignals(False)
                return
        
        success, message = self.model.set_active_plant(plant_id)
        
        if success:
            self.current_plant_id = plant_id
            self.current_plant_name = self.plant_selector_combo.currentText()
            
            # Actualizar título de la ventana
            self.setWindowTitle(f"Fiber Hybrid - Diagnóstico F.O. - Planta: {self.current_plant_name}")
            
            # Limpiar marca de cambios sin guardar
            self.clear_unsaved_changes()
            
            # Actualizar interfaz
            self.update_network_status()
            
            # Notificar a otros componentes
            self.plant_changed.emit(plant_id)
            
            self.show_notification(message, 'success')
        else:
            QMessageBox.warning(self, "Error", f"Error cambiando planta: {message}")
            
            # Restaurar combo box a la selección anterior
            index = self.plant_selector_combo.findData(self.current_plant_id)
            if index >= 0:
                self.plant_selector_combo.blockSignals(True)
                self.plant_selector_combo.setCurrentIndex(index)
                self.plant_selector_combo.blockSignals(False)
    
    def on_new_plant(self):
        """Abre diálogo para crear una nueva planta."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nueva Planta")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        name_edit = QLineEdit()
        form_layout.addRow("Nombre de la Planta:", name_edit)
        
        # Opciones para copiar desde otra planta
        copy_group = QGroupBox("Configuración Inicial")
        copy_layout = QVBoxLayout(copy_group)
        
        radio_empty = QRadioButton("Crear Planta Vacía")
        radio_empty.setChecked(True)
        copy_layout.addWidget(radio_empty)
        
        radio_copy = QRadioButton("Copiar Datos de Planta Existente")
        copy_layout.addWidget(radio_copy)
        
        # Selector de planta para copiar
        copy_combo = QComboBox()
        copy_combo.setEnabled(False)
        copy_layout.addWidget(copy_combo)
        
        # Cargar plantas disponibles
        plants = self.model.get_available_plants()
        if "Olmedilla" in plants:
            plants.remove("Olmedilla")
        for plant_id in plants:
            copy_combo.addItem(plant_id, plant_id)
            
        # Solo añadir Sabinar I como predefinida si no existe
        if "Sabinar I" not in plants:
            copy_combo.addItem("Sabinar I", "Sabinar I")
        
        # Conectar para habilitar/deshabilitar combo
        radio_copy.toggled.connect(copy_combo.setEnabled)
        
        layout.addLayout(form_layout)
        layout.addWidget(copy_group)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            plant_id = name_edit.text().strip()
            
            if not plant_id:
                QMessageBox.warning(self, "Error", "El nombre de la planta no puede estar vacío.")
                return
                
            # Determinar si copiar y de qué planta
            base_plant_id = None
            if radio_copy.isChecked():
                base_plant_id = copy_combo.currentData()
            
            # Crear planta
            success, message = self.model.create_plant(plant_id, base_plant_id)
            
            if success:
                # Refrescar lista de plantas
                self.load_plant_list()
                
                # Seleccionar la nueva planta
                index = self.plant_selector_combo.findData(plant_id)
                if index >= 0:
                    self.plant_selector_combo.setCurrentIndex(index)
                
                self.show_notification(f"Planta '{plant_id}' creada correctamente.", 'success')
            else:
                QMessageBox.warning(self, "Error", message)
    
    def on_rename_plant(self):
        """Renombra la planta actual."""
        current_id = self.current_plant_id
        
        if not current_id:
            QMessageBox.warning(self, "Error", "No hay planta activa.")
            return
        
        # Solicitar nuevo nombre
        new_id, ok = QInputDialog.getText(
            self, "Renombrar Planta", 
            f"Nuevo nombre para la planta '{current_id}':",
            QLineEdit.EchoMode.Normal, current_id
        )
        
        if not ok or not new_id.strip():
            return
            
        new_id = new_id.strip()
        
        # Solicitar confirmación
        answer = QMessageBox.question(
            self,
            "Confirmar Cambio",
            f"¿Desea renombrar la planta '{current_id}' a '{new_id}'?\n\nEsto modificará todas las configuraciones existentes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if answer != QMessageBox.StandardButton.Yes:
            return
            
        # Realizar cambio
        success, message = self.model.rename_plant(current_id, new_id)
        
        if success:
            # Refrescar lista de plantas
            self.load_plant_list()
            
            # Seleccionar la planta renombrada
            index = self.plant_selector_combo.findData(new_id)
            if index >= 0:
                self.plant_selector_combo.setCurrentIndex(index)
                
            self.show_notification(message, 'success')
        else:
            QMessageBox.warning(self, "Error", message)
    
    def on_delete_plant(self):
        """Elimina una planta."""
        current_id = self.current_plant_id
        
        if not current_id:
            QMessageBox.warning(self, "Error", "No hay planta activa para eliminar.")
            return
        
        # Verificar que no sea la última planta
        plants = self.model.get_available_plants()
        if "Olmedilla" in plants:
            plants.remove("Olmedilla")
        if len(plants) <= 1:
            QMessageBox.warning(
                self,
                "Error",
                "No se puede eliminar la única planta disponible.\nDebe existir al menos una planta."
            )
            return
            
        # Solicitar confirmación
        answer = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar la planta '{current_id}'?\n\nEsta operación eliminará todas las configuraciones asociadas y no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if answer != QMessageBox.StandardButton.Yes:
            return
            
        # Primero cambiar a otra planta
        other_plant = next((p for p in plants if p != current_id), None)
        if other_plant:
            success, change_msg = self.model.set_active_plant(other_plant)
            if not success:
                QMessageBox.warning(self, "Error", f"No se pudo cambiar de planta: {change_msg}")
                return
                
            self.current_plant_id = other_plant
            
        # Eliminar planta
        success, message = self.model.delete_plant(current_id)
        
        if success:
            # Refrescar lista de plantas
            self.load_plant_list()
            
            # Actualizar selección actual
            index = self.plant_selector_combo.findData(self.current_plant_id)
            if index >= 0:
                self.plant_selector_combo.setCurrentIndex(index)
                
            self.show_notification(message, 'success')
        else:
            QMessageBox.warning(self, "Error", message)
    
    def load_plant_list(self):
        """Carga la lista de plantas disponibles en el combo box."""
        # Guardar selección actual
        current_selection = self.plant_selector_combo.currentData()
        
        # Limpiar y rellenar combo
        self.plant_selector_combo.clear()
        
        # Obtener plantas disponibles
        plants = self.model.get_available_plants()
        if "Olmedilla" in plants:
            plants.remove("Olmedilla")
        
        # Si no hay plantas, añadir una por defecto
        if not plants:
            self.plant_selector_combo.addItem("Default", "default")
            return
        
        # Añadir plantas
        selected_index = 0
        for i, plant_id in enumerate(sorted(plants)):
            self.plant_selector_combo.addItem(plant_id, plant_id)
            if plant_id == current_selection or plant_id == self.model.active_plant_id:
                selected_index = i
                
        # Si hay plantas, seleccionar la última activa
        if self.plant_selector_combo.count() > 0:
            self.plant_selector_combo.setCurrentIndex(selected_index)
            
        # Actualizar información de la planta
        self._update_plant_info()
    
    def _update_plant_info(self):
        """Actualiza la etiqueta de información de la planta."""
        try:
            plant_id = self.current_plant_id
            
            # Contar nodos y segmentos
            with self.model.graph_lock:
                num_nodes = len([n for n, d in self.model.G.nodes(data=True) if d.get('type') == 'ct'])
                num_segments = len(self.model.G.edges())
                
            # Mostrar información básica
            self.lbl_plant_info.setText(f"CTs: {num_nodes} | Segmentos: {num_segments}")
            
        except Exception as e:
            logger.error(f"Error actualizando info de planta: {e}")
            self.lbl_plant_info.setText("Error obteniendo información")
    
    def load_initial_data(self):
        """Carga los datos iniciales al arrancar o cambiar de planta."""
        self.load_plant_list()
        # Seleccionar la primera planta disponible como activa
        if self.plant_selector_combo.count() > 0:
            self.plant_selector_combo.setCurrentIndex(0)
            self.current_plant_id = self.plant_selector_combo.itemData(0)
            self.current_plant_name = self.plant_selector_combo.currentText()
            self.update_network_status()

    @property
    def has_unsaved_changes(self):
        """Verifica si hay cambios sin guardar en la configuración actual."""
        return getattr(self, '_has_unsaved_changes', False)

    @has_unsaved_changes.setter
    def has_unsaved_changes(self, value):
        self._has_unsaved_changes = value

    def mark_unsaved_changes(self):
        """Marca que hay cambios sin guardar en la configuración actual."""
        self.has_unsaved_changes = True
        # Actualizar título para reflejar cambios
        self.setWindowTitle(f"Fiber Hybrid - Diagnóstico F.O. - Planta: {self.current_plant_name} *")

    def clear_unsaved_changes(self):
        """Limpia la marca de cambios sin guardar."""
        self.has_unsaved_changes = False
        # Actualizar título para quitar asterisco
        self.setWindowTitle(f"Fiber Hybrid - Diagnóstico F.O. - Planta: {self.current_plant_name}")