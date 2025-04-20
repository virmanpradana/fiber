#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
import os
import importlib.util
import subprocess
from pathlib import Path

# Asegurarnos de estar en el directorio correcto para importaciones
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir.parent))

def check_and_install_dependencies():
    """Verifica e instala las dependencias necesarias si faltan."""
    # Listado de paquetes esenciales para la aplicación
    required_packages = {
        'PyQt6': 'PyQt6>=6.0.0',
        'PyQt6-WebEngine': 'PyQt6-WebEngine>=6.0.0',  # Añadido para soporte de WebEngineWidgets
        'networkx': 'networkx>=2.6.0',
        'matplotlib': 'matplotlib>=3.4.0',
        'numpy': 'numpy>=1.20.0',
        'pandas': 'pandas>=1.3.0',
        'sqlalchemy': 'sqlalchemy>=1.4.0',
        'pillow': 'pillow>=8.0.0',
        'folium': 'folium>=0.12.0'  # Añadido para mapas
    }
    
    missing_packages = []
    
    # Comprobar cada paquete
    for package_name, install_spec in required_packages.items():
        if importlib.util.find_spec(package_name) is None:
            missing_packages.append(install_spec)
    
    # Si faltan paquetes, instalarlos
    if missing_packages:
        print("Faltan dependencias necesarias. Instalando...")
        for pkg in missing_packages:
            print(f"Instalando {pkg}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                print(f"✓ {pkg} instalado correctamente")
            except subprocess.CalledProcessError:
                print(f"✗ Error al instalar {pkg}. Por favor instálelo manualmente.")
                sys.exit(1)
        print("Todas las dependencias han sido instaladas.")
    return True

# Verificar dependencias antes de cualquier otra operación
check_and_install_dependencies()

# Configuración específica según sistema operativo
# Importante: Para Windows NO configurar QT_QPA_PLATFORM
if sys.platform == "win32":
    # En Windows, eliminamos cualquier configuración de plataforma para usar la nativa
    if "QT_QPA_PLATFORM" in os.environ:
        del os.environ["QT_QPA_PLATFORM"]
    
    # Para depuración
    print("Ejecutando en Windows - usando plataforma Qt nativa")
else:
    # Para Linux y otros sistemas
    print("Ejecutando en Linux/otro SO")

# Importaciones de PyQt6
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError:
    print("ERROR: No se pudo importar el módulo PyQt6.")
    print("Por favor, instale PyQt6 con el siguiente comando:")
    print("pip install PyQt6")
    sys.exit(1)

# Importaciones del proyecto - usar importaciones relativas
from ui.main_window import MainWindow
from model.network_model import NetworkModel
from model.storage import ConfigStorage

# Crear directorio de configuración antes de configurar logging
app_dir = os.path.dirname(os.path.abspath(__file__))
log_path = os.path.join(app_dir, '..', 'fiber_hybrid.log')
config_dir = os.path.join(app_dir, '..', 'config')
os.makedirs(config_dir, exist_ok=True)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path, mode='w')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Función principal que inicia la aplicación."""
    try:
        # Crear directorio de configuración si no existe (ya se asegura arriba)
        # Inicializar el modelo
        db_path = os.path.join(config_dir, 'network_config.db')
        storage = ConfigStorage(db_path)
        # Forzar planta inicial a 'Sabinar I' para evitar problemas de arranque
        model = NetworkModel(storage)
        try:
            model.set_active_plant('Sabinar I')
            logger.info("Planta inicial establecida a 'Sabinar I'")
        except Exception as e:
            logger.error(f"No se pudo establecer 'Sabinar I' como planta inicial: {e}")
        
        # Inicializar la aplicación Qt
        app = QApplication(sys.argv)
        app.setApplicationName("Fiber Hybrid PON")
        app.setApplicationVersion("1.0")
        
        # Crear y mostrar la ventana principal
        main_window = MainWindow(model)
        logger.info("Ventana principal creada")
        
        # Mostrar la ventana principal (más simple y compatible con todos los sistemas)
        main_window.show()
        
        # Métodos adicionales solo para Windows
        if sys.platform == "win32":
            # Estos métodos pueden fallar en Linux, así que los protegemos
            try:
                main_window.raise_()  # Traer al frente en Windows
                main_window.activateWindow()  # Activar la ventana en Windows
            except Exception as e:
                logger.warning(f"No se pudieron aplicar métodos específicos de Windows: {e}")
        
        logger.info("Ventana principal mostrada")
        
        # Ejecutar el bucle de eventos
        return app.exec()
        
    except Exception as e:
        import traceback
        # Avoid logger.error(..., exc_info=True) to prevent recursion in logging
        logger.error(f"Error crítico: {e}")
        print("\n[ERROR CRÍTICO]", e)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())