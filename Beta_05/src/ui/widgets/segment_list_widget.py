from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

class SegmentListWidget(QGroupBox):
    """
    Widget autocontenida para mostrar y gestionar la lista de segmentos.
    Señal: segment_selected(str) -> id del segmento seleccionado o None.
    """
    segment_selected = pyqtSignal(object)
    segment_created = pyqtSignal()
    segment_edited = pyqtSignal(object)  # segmento seleccionado
    segment_deleted = pyqtSignal(object)  # segmento seleccionado
    segment_moved_up = pyqtSignal(object)
    segment_moved_down = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__("Segmentos", parent)
        self.setMinimumWidth(200)
        layout = QVBoxLayout(self)
        
        # Botonera de acciones
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("+")
        self.btn_add.setToolTip("Crear segmento")
        self.btn_edit = QPushButton("✎")
        self.btn_edit.setToolTip("Editar segmento")
        self.btn_delete = QPushButton("🗑")
        self.btn_delete.setToolTip("Borrar segmento")
        self.btn_up = QPushButton("↑")
        self.btn_up.setToolTip("Subir segmento")
        self.btn_down = QPushButton("↓")
        self.btn_down.setToolTip("Bajar segmento")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        layout.addLayout(btn_layout)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.list_widget.itemSelectionChanged.connect(self._emit_selected)

        # Conexión de señales
        self.btn_add.clicked.connect(self._on_create)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_up.clicked.connect(self._on_move_up)
        self.btn_down.clicked.connect(self._on_move_down)

    def set_segments(self, segments, selected_id=None):
        self.list_widget.clear()
        for segment in segments:
            seg_id = segment.get('id', '')
            src = segment.get('source', '?')
            dst = segment.get('target', '?')
            status = segment.get('comm_status', 'ok')
            display_text = f"{seg_id} ({src}↔{dst})"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, segment)
            if status == 'faulty':
                item.setForeground(Qt.GlobalColor.red)
            self.list_widget.addItem(item)
            if selected_id and seg_id == selected_id:
                self.list_widget.setCurrentItem(item)

    def get_selected_segment(self):
        items = self.list_widget.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        return None

    def clear_selection(self):
        self.list_widget.clearSelection()

    def _emit_selected(self):
        segment = self.get_selected_segment()
        self.segment_selected.emit(segment)

    def _on_create(self):
        self.segment_created.emit()

    def _on_edit(self):
        segment = self.get_selected_segment()
        if segment:
            self.segment_edited.emit(segment)

    def _on_delete(self):
        segment = self.get_selected_segment()
        if segment:
            self.segment_deleted.emit(segment)

    def _on_move_up(self):
        segment = self.get_selected_segment()
        if segment:
            self.segment_moved_up.emit(segment)

    def _on_move_down(self):
        segment = self.get_selected_segment()
        if segment:
            self.segment_moved_down.emit(segment)
