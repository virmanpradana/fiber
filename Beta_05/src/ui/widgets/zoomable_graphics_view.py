from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scale_factor = 1.0

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        resulting_scale = self._scale_factor * zoom_factor
        if resulting_scale < 0.2 or resulting_scale > 5:
            return
        self.scale(zoom_factor, zoom_factor)
        self._scale_factor *= zoom_factor
