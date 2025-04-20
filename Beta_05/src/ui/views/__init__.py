#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Paquete para las vistas de la aplicación Fiber Hybrid.
"""

import logging

logger = logging.getLogger(__name__)

# Importing base view should always work
from ui.views.base_view import BaseView

# Import other views with error handling
__all__ = ['BaseView']

# Try to import NetworkView
try:
    from ui.views.network_view import NetworkView
    __all__.append('NetworkView')
except ImportError as e:
    logger.warning(f"No se pudo importar NetworkView: {e}")

# Try to import CCTVView
try:
    from ui.views.cctv_view import CCTVView
    __all__.append('CCTVView')
except ImportError as e:
    logger.warning(f"No se pudo importar CCTVView: {e}")

# Try to import GPSView
try:
    from ui.views.gps_view import GPSView
    __all__.append('GPSView')
except ImportError as e:
    logger.warning(f"No se pudo importar GPSView: {e}")

# LayoutView is not available yet - removed from imports
# If you need to add it later, use the pattern:
# try:
#     from ui.views.layout_view import LayoutView
#     __all__.append('LayoutView')
# except ImportError as e:
#     logger.warning(f"No se pudo importar LayoutView: {e}")