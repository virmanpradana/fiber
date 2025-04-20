#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from PyQt6.QtCore import QObject

class BaseView(ABC):
    """Clase base para todas las vistas de la aplicación.
    
    Proporciona la interfaz común que todas las vistas deben implementar.
    """
    
    @abstractmethod
    def update_view(self, status_data=None):
        """Actualiza la vista con los datos actuales.
        
        Args:
            status_data: Datos de estado de la red
        """
        pass
    
    def reset_view(self):
        """Restablece la vista a su estado original."""
        pass  # Implementación opcional
