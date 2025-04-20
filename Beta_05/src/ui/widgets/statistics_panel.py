from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QGridLayout, QLabel

class StatisticsPanel(QGroupBox):
    """
    Panel autocontenida para mostrar estadísticas de CTs y fibras.
    Proporciona métodos para actualizar los valores de estado.
    """
    def __init__(self, parent=None):
        super().__init__("Estadísticas", parent)
        layout = QVBoxLayout(self)

        # Estado de CTs
        ct_group = QGroupBox("Estado de CTs")
        ct_layout = QVBoxLayout(ct_group)
        self.ct_connected_label = QLabel("Conectados: --")
        self.ct_isolated_label = QLabel("Aislados: --")
        self.ct_error_label = QLabel("Error: --")
        ct_layout.addWidget(self.ct_connected_label)
        ct_layout.addWidget(self.ct_isolated_label)
        ct_layout.addWidget(self.ct_error_label)
        layout.addWidget(ct_group)

        # Estado de Fibras
        fiber_group = QGroupBox("Estado de Fibras")
        fiber_layout = QGridLayout(fiber_group)
        fiber_layout.addWidget(QLabel("Tipo"), 0, 0)
        fiber_layout.addWidget(QLabel("OK"), 0, 1)
        fiber_layout.addWidget(QLabel("Averiadas"), 0, 2)
        fiber_layout.addWidget(QLabel("Comunicación:"), 1, 0)
        self.comm_ok_label = QLabel("--/--")
        self.comm_ok_label.setStyleSheet("color: #16a34a")
        fiber_layout.addWidget(self.comm_ok_label, 1, 1)
        self.comm_faulty_label = QLabel("--/--")
        self.comm_faulty_label.setStyleSheet("color: #dc2626")
        fiber_layout.addWidget(self.comm_faulty_label, 1, 2)
        fiber_layout.addWidget(QLabel("Reserva:"), 2, 0)
        self.reserve_ok_label = QLabel("--/--")
        self.reserve_ok_label.setStyleSheet("color: #16a34a")
        fiber_layout.addWidget(self.reserve_ok_label, 2, 1)
        self.reserve_faulty_label = QLabel("--/--")
        self.reserve_faulty_label.setStyleSheet("color: #dc2626")
        fiber_layout.addWidget(self.reserve_faulty_label, 2, 2)
        fiber_layout.addWidget(QLabel("CCTV:"), 3, 0)
        self.cctv_ok_label = QLabel("--/--")
        self.cctv_ok_label.setStyleSheet("color: #16a34a")
        fiber_layout.addWidget(self.cctv_ok_label, 3, 1)
        self.cctv_faulty_label = QLabel("--/--")
        self.cctv_faulty_label.setStyleSheet("color: #dc2626")
        fiber_layout.addWidget(self.cctv_faulty_label, 3, 2)
        layout.addWidget(fiber_group)

    def update_ct_stats(self, connected, isolated, error):
        self.ct_connected_label.setText(f"Conectados: {connected}")
        self.ct_isolated_label.setText(f"Aislados: {isolated}")
        self.ct_error_label.setText(f"Error: {error}")
        self.ct_connected_label.setStyleSheet("color: #16a34a;")
        self.ct_isolated_label.setStyleSheet("color: #f97316;" if isolated > 0 else "")
        self.ct_error_label.setStyleSheet("color: #dc2626;" if error > 0 else "")

    def update_fiber_stats(self, comm_ok, comm_total, reserve_ok, reserve_total, cctv_ok, cctv_total):
        comm_faulty = comm_total - comm_ok
        reserve_faulty = reserve_total - reserve_ok
        cctv_faulty = cctv_total - cctv_ok
        self.comm_ok_label.setText(f"{comm_ok}/{comm_total}")
        self.comm_faulty_label.setText(f"{comm_faulty}/{comm_total}")
        self.reserve_ok_label.setText(f"{reserve_ok}/{reserve_total}")
        self.reserve_faulty_label.setText(f"{reserve_faulty}/{reserve_total}")
        self.cctv_ok_label.setText(f"{cctv_ok}/{cctv_total}")
        self.cctv_faulty_label.setText(f"{cctv_faulty}/{cctv_total}")
