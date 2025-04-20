from PyQt6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsView, QGraphicsScene, QGraphicsTextItem, QMenu, QMessageBox, QFileDialog
from PyQt6.QtGui import QColor, QBrush, QPen, QPainter, QFont, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
import math
import logging
import os

# Importación absoluta para el orden de circuitos
from constants import DEFAULT_RING_ORDER
from .base_view import BaseView

logger = logging.getLogger(__name__)

class CustomGraphicsScene(QGraphicsScene):
    def update_links_for_node(self, node):
        # Implement your logic here
        pass

class NetworkNode(QGraphicsItem):
    def __init__(self, node_id, node_type, status, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.node_type = node_type
        self.status = status
        self.is_set = False
        # Inicializar brush y pen por defecto
        self._brush = QBrush(QColor(148, 163, 184))
        self._pen = QPen(QColor(229, 231, 235), 1.5)
        self.update_appearance()

        # Habilitar interacción
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # Para tooltip
        self.setToolTip(f"Nodo: {self.node_id}\nTipo: {self.node_type}\nEstado: {self.status}")
    
    def setBrush(self, brush):
        """Sets the brush for the node's appearance."""
        self._brush = brush
        self.update()

    def setPen(self, pen):
        """Sets the pen for the node's appearance."""
        self._pen = pen
        self.update()

    def paint(self, painter, option, widget):
        """Override paint method to use the custom pen and brush."""
        if painter is not None:
            painter.setBrush(self._brush)
            painter.setPen(self._pen)
            painter.drawEllipse(self.boundingRect())
    
    def boundingRect(self):
        """Defines the bounding rectangle for the node."""
        radius = 20  # Example radius for the node
        return QRectF(-radius, -radius, 2 * radius, 2 * radius)
    
    def update_appearance(self):
        """Actualiza la apariencia del nodo según su estado."""
        # Colores según estado
        if self.is_set:
            brush_color = QColor(58, 12, 163)  # #3a0ca3
            text_color = Qt.GlobalColor.white
        elif self.status == 'conectado':
            brush_color = QColor(22, 163, 74)  # #16a34a (verde)
            text_color = Qt.GlobalColor.white
        elif self.status == 'aislado':
            brush_color = QColor(249, 115, 22)  # #f97316 (naranja)
            text_color = Qt.GlobalColor.white
        elif self.status == 'error':
            brush_color = QColor(220, 38, 38)  # #dc2626 (rojo)
            text_color = Qt.GlobalColor.white
        else:
            brush_color = QColor(148, 163, 184)  # #94a3b8 (gris)
            text_color = Qt.GlobalColor.black
        
        self.setBrush(QBrush(brush_color))
        self.setPen(QPen(QColor(229, 231, 235), 1.5))  # #e5e7eb (gris claro)
    
    def update_status(self, new_status):
        """Actualiza el estado del nodo."""
        if self.status != new_status:
            self.status = new_status
            self.update_appearance()
            self.setToolTip(f"Nodo: {self.node_id}\nTipo: {self.node_type}\nEstado: {new_status}")
    
    def itemChange(self, change, value):
        """Maneja cambios en el elemento gráfico."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            scene = self.scene()
            if scene is not None and hasattr(scene, 'update_links_for_node'):
                if isinstance(scene, CustomGraphicsScene):
                    scene.update_links_for_node(self)
        
        return super().itemChange(change, value)


class NetworkLink(QGraphicsLineItem):
    """Enlace de red interactivo."""
    
    def __init__(self, segment_id, source_node, target_node, status="ok", parent=None):
        """Inicializa el enlace.
        
        Args:
            segment_id: Identificador único del segmento
            source_node: Nodo de origen (NetworkNode)
            target_node: Nodo de destino (NetworkNode)
            status: Estado del enlace ('ok', 'faulty')
            parent: Elemento gráfico padre
        """
        self.segment_id = segment_id
        self.source_node = source_node
        self.target_node = target_node
        self.status = status
        
        # Posiciones iniciales
        source_pos = source_node.pos()
        target_pos = target_node.pos()
        
        # Construir elemento gráfico
        super().__init__(source_pos.x(), source_pos.y(), target_pos.x(), target_pos.y(), parent)
        
        # Configurar apariencia
        self.update_appearance()
        
        # Para tooltip
        self.src_id = source_node.node_id
        self.tgt_id = target_node.node_id
        self.setToolTip(f"Enlace: {segment_id}\n({self.src_id}↔{self.tgt_id})\nEstado: {status}")
        
        # Habilitar selección
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Mover detrás de nodos
        self.setZValue(-1)
    
    def update_appearance(self):
        """Actualiza la apariencia del enlace según su estado."""
        # Estilo según estado
        if self.status == 'ok':
            color = QColor(22, 163, 74)  # #16a34a (verde)
            width = 2.0
            pattern = Qt.PenStyle.SolidLine
        elif self.status == 'faulty':
            color = QColor(220, 38, 38)  # #dc2626 (rojo)
            width = 2.0
            pattern = Qt.PenStyle.DashLine
        else:
            color = QColor(148, 163, 184)  # #94a3b8 (gris)
            width = 1.5
            pattern = Qt.PenStyle.SolidLine
        
        self.setPen(QPen(color, width, pattern))
    
    def update_status(self, new_status):
        """Actualiza el estado del enlace."""
        if self.status != new_status:
            self.status = new_status
            self.update_appearance()
            self.setToolTip(f"Enlace: {self.segment_id}\n({self.src_id}↔{self.tgt_id})\nEstado: {new_status}")
    
    def update_position(self):
        """Actualiza la posición del enlace según los nodos conectados."""
        source_pos = self.source_node.pos()
        target_pos = self.target_node.pos()
        self.setLine(source_pos.x(), source_pos.y(), target_pos.x(), target_pos.y())
    
    def highlight(self, active=True):
        """Resalta o quita resalte del enlace."""
        if active:
            # Resaltar con color destacado y ancho mayor
            highlight_color = QColor(247, 37, 133)  # #f72585 (rosa brillante)
            current_width = self.pen().width()
            highlight_width = current_width + 2
            
            self.setPen(QPen(highlight_color, highlight_width, Qt.PenStyle.SolidLine))
            self.setZValue(0)  # Traer al frente
        else:
            # Restaurar apariencia normal
            self.update_appearance()
            self.setZValue(-1)  # Enviar atrás


class NetworkView(QGraphicsView):
    """Vista interactiva de la red de fibra óptica."""
    
    # Señal emitida cuando se selecciona un segmento
    segment_selected = pyqtSignal(str)
    
    def __init__(self, model, parent=None):
        """Inicializa la vista de red.
        
        Args:
            model: Modelo de red
            parent: Widget padre
        """
        super().__init__(parent)
        self.model = model
        # Ensure scene is an attribute, not a property or method
        self._scene = CustomGraphicsScene(self)
        self.setScene(self._scene)
        
        # Atributos para seguimiento de elementos
        self.nodes = {}  # {node_id: NetworkNode}
        self.links = {}  # {segment_id: NetworkLink}
        self.highlighted_link = None
        self.selected_node = None
        
        # Configuración de la vista
        self.setRenderHints(QPainter.RenderHint.Antialiasing | 
                          QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor(248, 250, 252)))  # #f8fafc
        
        # Estado para zoom y posicionamiento
        self.scale_factor = 1.0
        
        # Conexiones para eventos
        self.setup_connections()
        
        # Inicializar escena
        self.initialize_scene()

    @property
    def scene(self) -> CustomGraphicsScene:
        return self._scene

    def setup_connections(self):
        """Configura las conexiones para eventos."""
        # Nada específico aquí por ahora
        pass
    
    def initialize_scene(self):
        """Inicializa la escena gráfica."""
        # Limpiar escena
        self.scene.clear()
        self.nodes.clear()
        self.links.clear()
        
        # Añadir instrucción inicial
        text = self.scene.addText("Cargando red...")
        if text is not None:
            text.setDefaultTextColor(QColor(100, 116, 139))  # #64748b
            font = QFont("Segoe UI", 14)
            text.setFont(font)
            text.setPos(0, 0)
    
    def update_view(self, status_data=None):
        if getattr(self, '_updating_view', False):
            return
        self._updating_view = True
        try:
            if not status_data:
                return
            
            # Primer paso: determinar si necesitamos reconstruir toda la escena
            need_rebuild = False
            
            # Si no hay nodos o hay una diferencia en nodos existentes vs modelo
            with self.model.graph_lock:
                model_node_ids = set(self.model.G.nodes())
                view_node_ids = set(self.nodes.keys())
                
                if not self.nodes or model_node_ids != view_node_ids:
                    need_rebuild = True
            
            if need_rebuild:
                # Reconstruir escena completa
                self.rebuild_scene(status_data)
            else:
                # Actualizar elementos existentes
                self.update_elements(status_data)
        finally:
            self._updating_view = False
    
    def rebuild_scene(self, status_data):
        """Reconstruye toda la escena desde cero, usando layout circular tipo anillo."""
        logger.debug("Reconstruyendo escena completa (layout anillo)")
        self.scene.clear()
        self.nodes.clear()
        self.links.clear()
        self.highlighted_link = None

        # Obtener datos de la planta y segmentos
        plant_id = getattr(self.model, 'active_plant_id', 'default')
        from constants import get_plant_config
        plant_config = get_plant_config(plant_id)
        circuits = plant_config.get('circuitos', {})
        ct_statuses = status_data.get('ct_connectivity', {})
        segments = status_data.get('segment_statuses', [])

        # Layout circular para circuitos y CTs
        positions = {}
        all_nodes = ['SET']
        for circuit, cts in circuits.items():
            all_nodes.extend(cts)
        positions['SET'] = (0, 0)
        circle_radius = 200
        num_circuits = len(circuits)
        for i, (circuit_id, cts) in enumerate(circuits.items()):
            angle = 2 * math.pi * i / max(1, num_circuits)
            circuit_x = circle_radius * math.cos(angle)
            circuit_y = circle_radius * math.sin(angle)
            ct_spacing = 50
            num_cts = len(cts)
            for j, ct_id in enumerate(cts):
                perp_angle = angle + (math.pi / 2)
                offset = (j - (num_cts - 1) / 2) * ct_spacing
                ct_x = circuit_x + offset * math.cos(perp_angle)
                ct_y = circuit_y + offset * math.sin(perp_angle)
                positions[ct_id] = (ct_x, ct_y)

        # Crear nodos
        for node_id in all_nodes:
            if node_id not in positions:
                continue
            if node_id == 'SET':
                node_type = 'set'
                status = 'conectado'
            else:
                node_type = 'ct'
                status = ct_statuses.get(node_id, 'desconocido')
            node = NetworkNode(node_id, node_type, status)
            node.setPos(*positions[node_id])
            self.scene.addItem(node)
            self.nodes[node_id] = node
            # Etiqueta
            label = QGraphicsTextItem(node_id)
            label.setPos(positions[node_id][0] - 20, positions[node_id][1] + 10)
            self.scene.addItem(label)

        # Crear enlaces/segmentos
        for segment in segments:
            segment_id = segment.get('id')
            source_id = segment.get('source')
            target_id = segment.get('target')
            status = segment.get('comm_status', 'ok')
            if source_id not in self.nodes or target_id not in self.nodes:
                continue
            source_node = self.nodes[source_id]
            target_node = self.nodes[target_id]
            link = NetworkLink(segment_id, source_node, target_node, status)
            self.scene.addItem(link)
            self.links[segment_id] = link

        # Ajustar vista
        if self.nodes:
            items_rect = self.scene.itemsBoundingRect()
            padding = 30
            adjusted_rect = items_rect.adjusted(-padding, -padding, padding, padding)
            self.fitInView(adjusted_rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.scale(1.1, 1.1)
            self.scale_factor = 1.1
    
    def ensure_node_positions(self):
        """Asegura que todos los nodos tienen posiciones asignadas."""
        with self.model.graph_lock:
            # Calcular posiciones para nodos que no tienen
            calc_positions = False
            for node in self.model.G.nodes():
                if node not in self.model.node_positions:
                    calc_positions = True
                    break
            
            if calc_positions:
                self.calculate_node_positions()
    
    def calculate_node_positions(self):
        # Este método ya no debe existir aquí. La lógica de posicionamiento está en el modelo.
        pass  # Eliminado. La vista solo debe usar self.model.node_positions
    
    def create_nodes(self, status_data):
        """Crea los nodos en la escena."""
        ct_statuses = status_data.get('ct_connectivity', {})
        
        with self.model.graph_lock:
            for node_id, data in self.model.G.nodes(data=True):
                # Obtener posición
                if node_id not in self.model.node_positions:
                    logger.warning(f"Nodo {node_id} sin posición, omitiendo")
                    continue
                
                pos = self.model.node_positions[node_id]
                node_type = data.get('type', 'unknown')
                
                # Obtener estado para CTs
                status = 'unknown'
                if node_id == 'SET':
                    status = 'central'
                else:
                    status = ct_statuses.get(node_id, 'unknown')
                
                # Crear nodo
                node = NetworkNode(node_id, node_type, status)
                node.setPos(pos[0], pos[1])
                
                # Añadir a la escena
                self.scene.addItem(node)
                self.nodes[node_id] = node
                
                # Añadir etiqueta
                self.create_node_label(node)
    
    def create_node_label(self, node):
        """Crea una etiqueta para un nodo."""
        node_id = node.node_id
        is_set = (node_id == 'SET')
        
        # Configurar texto
        label = QGraphicsTextItem(node_id)
        label.setDefaultTextColor(Qt.GlobalColor.black)
        
        # Fuente según tipo
        font_size = 9 if is_set else 8
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        label.setFont(font)
        
        # Centrar respecto al nodo
        label_rect = label.boundingRect()
        label_x = node.pos().x() - label_rect.width() / 2
        
        # Posición debajo del nodo (radio + margen)
        radius = 18 if is_set else 12
        label_y = node.pos().y() + radius + 8
        
        label.setPos(label_x, label_y)
        
        # Añadir a la escena
        self.scene.addItem(label)
    
    def create_links(self, status_data):
        """Crea los enlaces en la escena."""
        segments = status_data.get('segment_statuses', [])
        
        for segment in segments:
            segment_id = segment.get('id')
            source_id = segment.get('source')
            target_id = segment.get('target')
            status = segment.get('comm_status', 'ok')
            
            # Comprobar que los nodos existen
            if source_id not in self.nodes or target_id not in self.nodes:
                logger.warning(f"No se puede crear enlace {segment_id}: nodo(s) no encontrado(s)")
                continue
            
            # Crear enlace
            link = NetworkLink(
                segment_id,
                self.nodes[source_id],
                self.nodes[target_id],
                status
            )
            
            # Añadir a la escena
            self.scene.addItem(link)
            self.links[segment_id] = link
    
    def update_elements(self, status_data):
        """Actualiza los elementos existentes sin reconstruir la escena."""
        # Actualizar estados de nodos
        ct_statuses = status_data.get('ct_connectivity', {})
        for node_id, node in self.nodes.items():
            if node_id == 'SET':
                continue
            
            status = ct_statuses.get(node_id, 'unknown')
            node.update_status(status)
        
        # Actualizar estados de enlaces
        segments = status_data.get('segment_statuses', [])
        segment_dict = {s.get('id'): s.get('comm_status', 'ok') for s in segments}
        
        for segment_id, link in self.links.items():
            status = segment_dict.get(segment_id, 'unknown')
            link.update_status(status)
    
    def update_links_for_node(self, node):
        """Actualiza los enlaces conectados a un nodo que se ha movido."""
        node_id = node.node_id
        with self.model.graph_lock:
            self.model.node_positions[node_id] = (node.pos().x(), node.pos().y())
        
        # Buscar enlaces conectados
        for segment_id, link in self.links.items():
            if link.source_node == node or link.target_node == node:
                link.update_position()
    
    def highlight_segment(self, segment_id):
        """Resalta un segmento específico."""
        # Quitar resaltado anterior
        if self.highlighted_link:
            self.highlighted_link.highlight(False)
            self.highlighted_link = None
        
        # Aplicar nuevo resaltado
        if segment_id and segment_id in self.links:
            link = self.links[segment_id]
            link.highlight(True)
            self.highlighted_link = link
    
    def reset_view(self):
        self.resetTransform()
        self.scale_factor = 1.0
        if self.scene is not None and hasattr(self.scene, "itemsBoundingRect"):
            self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.scale(1.1, 1.1)
            self.scale_factor = 1.1
    
    def wheelEvent(self, event):
        """Maneja el evento de rueda del ratón para zoom real (ampliar/reducir)."""
        if event is not None and hasattr(event, "angleDelta"):
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
            resulting_scale = self.scale_factor * zoom_factor
            if resulting_scale < 0.2 or resulting_scale > 5:
                return
            self.scale(zoom_factor, zoom_factor)
            self.scale_factor *= zoom_factor
    
    def mousePressEvent(self, event):
        """Maneja el evento de clic del ratón."""
        if event is not None and hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
            # Obtener item bajo el cursor
            if event is not None and hasattr(event, "pos"):
                pos = self.mapToScene(event.pos())
                item = self.scene.itemAt(pos, self.transform())
                
                # Limpiar selección anterior de nodo
                self.selected_node = None
                
                if isinstance(item, NetworkLink):
                    # Seleccionar segmento
                    segment_id = item.segment_id
                    self.highlight_segment(segment_id)
                    self.segment_selected.emit(segment_id)
                    return
                elif isinstance(item, NetworkNode):
                    # Guardar referencia al nodo seleccionado para menú contextual
                    self.selected_node = item
        
        # Comportamiento estándar para otros casos
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Tras soltar el ratón, actualizar todas las posiciones de enlaces
        for link in self.links.values():
            link.update_position()
    
    def contextMenuEvent(self, event):
        """Maneja eventos de menú contextual en la vista."""
        if event is not None and hasattr(event, "pos"):
            item = self.itemAt(event.pos())
            
            # Verificar si se hizo clic en un nodo
            node_id = None
            if isinstance(item, NetworkNode):
                node_id = item.node_id
            
            # Crear menú contextual
            menu = QMenu(self)
            
            if node_id:
                # Menú para nodos
                title_action = menu.addAction(f"Nodo: {node_id}")
                if title_action is not None:
                    title_action.setEnabled(False)
                    title_font = title_action.font() if hasattr(title_action, "font") else None
                    if title_font is not None:
                        title_font.setBold(True)
                        title_action.setFont(title_font)
                
                menu.addSeparator()
                
                # Acción para mostrar información del nodo
                info_action = menu.addAction("Información")
                
                # Acción para conectarse al nodo (simulada)
                connect_action = menu.addAction("Conectar...")
                
                # Acción para telnet al nodo (simulada)
                telnet_action = menu.addAction("Telnet")
                
                # Si es un nodo CT, añadir opciones específicas
                node_data = self.model.G.nodes.get(node_id, {})
                if node_data.get('type') == 'ct':
                    menu.addSeparator()
                    
                    # Verificar integridad del circuito
                    circuit = node_data.get('circuit')
                    if circuit:
                        circuit_action = menu.addAction(f"Verificar circuito {circuit}")
            else:
                # Menú para la vista en general
                reset_action = menu.addAction("Restablecer vista")
                refresh_action = menu.addAction("Refrescar")
                
                menu.addSeparator()
                
                export_action = menu.addAction("Exportar vista como imagen")
            
            # Mostrar menú contextual
            if event is not None and hasattr(event, "globalPos"):
                action = menu.exec(event.globalPos())
            
            # Manejar acciones seleccionadas
            if node_id and action:
                if action == info_action:
                    self._show_node_info(node_id)
                elif action == connect_action:
                    self._connect_to_node(node_id)
                elif action == telnet_action:
                    self._telnet_to_node(node_id)
                elif node_data.get('type') == 'ct' and 'circuit_action' in locals() and action == circuit_action:
                    self._verify_circuit(node_data.get('circuit'))
            elif not node_id and action:
                if action == reset_action:
                    self.reset_view()
                elif action == refresh_action:
                    # Solicitar actualización del padre
                    parent = self.parent()
                    while parent:
                        update_status = getattr(parent, 'update_network_status', None)
                        if callable(update_status):
                            update_status()
                            break
                        parent = parent.parent() if hasattr(parent, 'parent') else None
                elif action == export_action:
                    self._export_view_as_image()
    
    def _show_node_info(self, node_id):
        """Muestra información detallada de un nodo."""
        if not node_id or not self.model.G.has_node(node_id):
            return
        
        # Obtener datos del nodo
        node_data = self.model.G.nodes[node_id]
        
        # Preparar información
        info = f"<b>ID:</b> {node_id}<br>"
        info += f"<b>Tipo:</b> {node_data.get('type', 'desconocido')}<br>"
        
        if 'circuit' in node_data:
            info += f"<b>Circuito:</b> {node_data['circuit']}<br>"
        
        # Obtener enlaces conectados
        connected_segments = []
        for u, v, data in self.model.G.edges(node_id, data=True):
            other_node = v if u == node_id else u
            segment_id = data.get('id', f"{u}-{v}")
            connected_segments.append(f"{segment_id} → {other_node}")
        
        if connected_segments:
            info += f"<b>Segmentos conectados:</b><br>"
            for segment in connected_segments:
                info += f"• {segment}<br>"
        
        # Mostrar estado si es un CT
        if node_data.get('type') == 'ct':
            status = self.model.check_ct_connectivity(node_id)
            status_text = {
                'conectado': '<span style="color: #16a34a;">Conectado</span>',
                'aislado': '<span style="color: #f97316;">Aislado</span>',
                'error': '<span style="color: #dc2626;">Error</span>'
            }.get(status, f"<span style='color: #64748b;'>{status}</span>")
            
            info += f"<b>Estado:</b> {status_text}<br>"
        
        # Mostrar diálogo con información
        QMessageBox.information(
            self,
            f"Información de {node_id}",
            info
        )
    
    def _connect_to_node(self, node_id):
        """Simula la conexión a un nodo."""
        pass

    def _telnet_to_node(self, node_id):
        """Simula la conexión Telnet a un nodo."""
        pass

    def _verify_circuit(self, circuit_id):
        """Verifica la integridad de un circuito específico."""
        if not circuit_id:
            return
        
        # Obtener nodos del circuito
        cts = self.model.DEFAULT_CIRCUITOS.get(circuit_id, [])
        
        if not cts:
            QMessageBox.warning(
                self,
                f"Circuito {circuit_id}",
                f"No hay CTs definidos para el circuito {circuit_id}"
            )
            return
        
        # Verificar conectividad de cada CT
        statuses = {}
        for ct in cts:
            statuses[ct] = self.model.check_ct_connectivity(ct)
        
        # Contar estados
        connected = sum(1 for st in statuses.values() if st == 'conectado')
        isolated = sum(1 for st in statuses.values() if st == 'aislado')
        errors = sum(1 for st in statuses.values() if st == 'error')
        
        # Preparar mensaje
        message = f"<b>Circuito:</b> {circuit_id}<br>"
        message += f"<b>CTs:</b> {', '.join(cts)}<br><br>"
        
        message += f"<b>Conectados ({connected}/{len(cts)}):</b><br>"
        for ct, status in statuses.items():
            if status == 'conectado':
                message += f"• {ct}<br>"
        
        if isolated > 0:
            message += f"<br><b>Aislados ({isolated}/{len(cts)}):</b><br>"
            for ct, status in statuses.items():
                if status == 'aislado':
                    message += f"• {ct}<br>"
        
        if errors > 0:
            message += f"<br><b>Errores ({errors}/{len(cts)}):</b><br>"
            for ct, status in statuses.items():
                if status == 'error':
                    message += f"• {ct}<br>"
        
        # Verificar integridad de segmentos entre CTs
        message += "<br><b>Integridad de segmentos:</b><br>"
        all_segments_ok = True
        
        for i in range(len(cts) - 1):
            ct1 = cts[i]
            ct2 = cts[i + 1]
            
            segment_id = None
            segment_data = None
            
            # Buscar segmento entre estos CTs
            for u, v, data in self.model.G.edges(data=True):
                if (u == ct1 and v == ct2) or (u == ct2 and v == ct1):
                    segment_id = data.get('id', f"{u}-{v}")
                    segment_data = data
                    break
            
            if segment_id and segment_data:
                # Verificar estado de fibras de comunicación
                fibers = segment_data.get('fibers', {})
                ida_ok = self.model._check_segment_path_direction(fibers, self.model.DEFAULT_FIBRAS_COMMS_IDA)
                vuelta_ok = self.model._check_segment_path_direction(fibers, self.model.DEFAULT_FIBRAS_COMMS_VUELTA)
                
                if ida_ok and vuelta_ok:
                    message += f"• {ct1} ↔ {ct2}: <span style='color: #16a34a;'>OK</span><br>"
                else:
                    message += f"• {ct1} ↔ {ct2}: <span style='color: #dc2626;'>PROBLEMA</span>"
                    if not ida_ok:
                        message += " (IDA)"
                    if not vuelta_ok:
                        message += " (VUELTA)"
                    message += "<br>"
                    all_segments_ok = False
            else:
                message += f"• {ct1} ↔ {ct2}: <span style='color: #dc2626;'>NO ENCONTRADO</span><br>"
                all_segments_ok = False
        
        # Verificar conexión a SET
        if 'SET' in self.model.G and cts:
            first_ct = cts[0]
            segment_id = None
            
            # Buscar segmento entre SET y primer CT
            for u, v, data in self.model.G.edges(data=True):
                if (u == 'SET' and v == first_ct) or (u == first_ct and v == 'SET'):
                    segment_id = data.get('id', f"{u}-{v}")
                    segment_data = data
                    break
            
            if segment_id and segment_data:
                # Verificar estado de fibras de comunicación
                fibers = segment_data.get('fibers', {})
                ida_ok = self.model._check_segment_path_direction(fibers, self.model.DEFAULT_FIBRAS_COMMS_IDA)
                vuelta_ok = self.model._check_segment_path_direction(fibers, self.model.DEFAULT_FIBRAS_COMMS_VUELTA)
                
                message += f"• SET ↔ {first_ct}: "
                if ida_ok and vuelta_ok:
                    message += f"<span style='color: #16a34a;'>OK</span><br>"
                else:
                    message += f"<span style='color: #dc2626;'>PROBLEMA</span>"
                    if not ida_ok:
                        message += " (IDA)"
                    if not vuelta_ok:
                        message += " (VUELTA)"
                    message += "<br>"
                    all_segments_ok = False
            else:
                message += f"• SET ↔ {first_ct}: <span style='color: #dc2626;'>NO ENCONTRADO</span><br>"
                all_segments_ok = False
        
        # Resumen
        message += "<br><b>Resumen:</b><br>"
        
        if connected == len(cts):
            message += "✅ Todos los CTs están conectados<br>"
        else:
            message += f"⚠️ {isolated + errors}/{len(cts)} CTs con problemas<br>"
        
        if all_segments_ok:
            message += "✅ Todos los segmentos están OK<br>"
        else:
            message += "⚠️ Hay problemas en algunos segmentos<br>"
        
        # Mostrar diálogo
        QMessageBox.information(
            self,
            f"Verificación del Circuito {circuit_id}",
            message
        )
    
    def _export_view_as_image(self):
        """Exporta la vista actual como imagen."""
        # Solicitar nombre de archivo
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Vista como Imagen",
            os.path.expanduser("~/fibra_red.png"),
            "Imágenes (*.png *.jpg *.bmp)"
        )
        
        if file_path:
            # Crear imagen
            if self.scene is not None and hasattr(self.scene, "itemsBoundingRect"):
                scene_rect = self.scene.itemsBoundingRect()
                image = QImage(
                    int(scene_rect.width()), 
                    int(scene_rect.height()),
                    QImage.Format.Format_ARGB32
                )
                image.fill(Qt.GlobalColor.white)
                
                # Configurar renderizado
                painter = QPainter(image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Renderizar escena
                if hasattr(self.scene, "render"):
                    self.scene.render(
                        painter,
                        QRectF(0, 0, scene_rect.width(), scene_rect.height()),
                        scene_rect
                    )
                painter.end()
                
                # Guardar imagen
                if image.save(file_path):
                    QMessageBox.information(
                        self,
                        "Exportar Vista",
                        f"Vista exportada correctamente a:\n{file_path}"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"No se pudo guardar la imagen en {file_path}"
                    )

BaseView.register(NetworkView)