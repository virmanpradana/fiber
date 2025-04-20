from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QListWidget, QPushButton, QListWidgetItem, QMessageBox
from PyQt6.QtCore import Qt

class SegmentEditDialog(QDialog):
    """
    Diálogo para crear o editar un segmento.
    Permite definir ID, CT origen, CT destino y el orden de los CTs del segmento.
    """
    def __init__(self, ct_list, segment=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar segmento" if segment else "Crear segmento")
        self.setMinimumWidth(350)
        self.ct_list = ct_list  # Lista de CTs disponibles
        self.segment = segment or {}
        layout = QVBoxLayout(self)

        # ID del segmento
        layout.addWidget(QLabel("ID del segmento:"))
        self.edit_id = QLineEdit(self.segment.get('id', ''))
        layout.addWidget(self.edit_id)

        # CT origen
        layout.addWidget(QLabel("CT Origen:"))
        self.combo_source = QComboBox()
        self.combo_source.addItems(self.ct_list)
        if self.segment.get('source') in self.ct_list:
            self.combo_source.setCurrentText(self.segment.get('source'))
        layout.addWidget(self.combo_source)

        # CT destino
        layout.addWidget(QLabel("CT Destino:"))
        self.combo_target = QComboBox()
        self.combo_target.addItems(self.ct_list)
        if self.segment.get('target') in self.ct_list:
            self.combo_target.setCurrentText(self.segment.get('target'))
        layout.addWidget(self.combo_target)

        # Orden de CTs en el segmento
        layout.addWidget(QLabel("Orden de CTs en el segmento:"))
        self.list_cts = QListWidget()
        for ct in self.segment.get('cts', []):
            if ct in self.ct_list:
                self.list_cts.addItem(ct)
        # Si es nuevo, sugerir origen y destino
        if not self.segment and self.ct_list:
            self.list_cts.addItem(self.ct_list[0])
            if len(self.ct_list) > 1:
                self.list_cts.addItem(self.ct_list[1])
        layout.addWidget(self.list_cts)

        # Botones para añadir/quitar CTs
        btns_cts = QHBoxLayout()
        self.btn_add_ct = QPushButton("Añadir CT")
        self.btn_remove_ct = QPushButton("Quitar CT")
        self.btn_up_ct = QPushButton("↑")
        self.btn_down_ct = QPushButton("↓")
        btns_cts.addWidget(self.btn_add_ct)
        btns_cts.addWidget(self.btn_remove_ct)
        btns_cts.addWidget(self.btn_up_ct)
        btns_cts.addWidget(self.btn_down_ct)
        layout.addLayout(btns_cts)

        # Botones de aceptar/cancelar
        btns = QHBoxLayout()
        self.btn_ok = QPushButton("Aceptar")
        self.btn_cancel = QPushButton("Cancelar")
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        # Conexiones
        self.btn_add_ct.clicked.connect(self._on_add_ct)
        self.btn_remove_ct.clicked.connect(self._on_remove_ct)
        self.btn_up_ct.clicked.connect(self._on_up_ct)
        self.btn_down_ct.clicked.connect(self._on_down_ct)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def _on_add_ct(self):
        # Añadir CT seleccionado de los combos si no está ya en la lista
        ct = self.combo_source.currentText()
        if ct and not self._ct_in_list(ct):
            self.list_cts.addItem(ct)

    def _on_remove_ct(self):
        row = self.list_cts.currentRow()
        if row >= 0:
            self.list_cts.takeItem(row)

    def _on_up_ct(self):
        row = self.list_cts.currentRow()
        if row > 0:
            item = self.list_cts.takeItem(row)
            self.list_cts.insertItem(row - 1, item)
            self.list_cts.setCurrentRow(row - 1)

    def _on_down_ct(self):
        row = self.list_cts.currentRow()
        if row < self.list_cts.count() - 1 and row >= 0:
            item = self.list_cts.takeItem(row)
            self.list_cts.insertItem(row + 1, item)
            self.list_cts.setCurrentRow(row + 1)

    def _ct_in_list(self, ct):
        for i in range(self.list_cts.count()):
            if self.list_cts.item(i).text() == ct:
                return True
        return False

    def get_data(self):
        # Devuelve los datos del segmento editado/creado
        return {
            'id': self.edit_id.text().strip(),
            'source': self.combo_source.currentText(),
            'target': self.combo_target.currentText(),
            'cts': [self.list_cts.item(i).text() for i in range(self.list_cts.count())]
        }
