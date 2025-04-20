#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import importlib.util
import os
from pathlib import Path

class DependencyManager:
    """Gestiona la verificación e instalación de dependencias."""
    
    @staticmethod
    def get_requirements_path():
        """Obtiene la ruta al archivo requirements.txt"""
        # Buscar en el directorio raíz del proyecto (dos niveles arriba desde este archivo)
        src_dir = Path(__file__).parent.parent
        project_root = src_dir.parent
        req_path = project_root / "requirements.txt"
        
        if req_path.exists():
            return str(req_path)
        return None
    
    @staticmethod
    def parse_requirements(req_path):
        """Lee y parsea el archivo requirements.txt"""
        if not req_path:
            return {}
            
        requirements = {}
        try:
            with open(req_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Ignorar comentarios y líneas vacías
                    if line and not line.startswith('#'):
                        # Extraer el nombre del paquete (antes de cualquier operador de versión)
                        parts = line.split('>=')[0].split('==')[0].split('<')[0].strip()
                        requirements[parts] = line
        except Exception as e:
            print(f"Error al leer el archivo requirements.txt: {e}")
        
        return requirements
    
    @staticmethod
    def verify_and_install(specific_packages=None):
        """Verifica e instala las dependencias necesarias."""
        # Si no se especifican paquetes, usar requirements.txt
        if specific_packages is None:
            req_path = DependencyManager.get_requirements_path()
            requirements = DependencyManager.parse_requirements(req_path)
        else:
            requirements = specific_packages
        
        missing_packages = []
        
        # Comprobar cada paquete
        for package_name, install_spec in requirements.items():
            if importlib.util.find_spec(package_name) is None:
                missing_packages.append(install_spec)
        
        # Si faltan paquetes, instalarlos
        if missing_packages:
            print("===== Gestor de Dependencias =====")
            print(f"Se encontraron {len(missing_packages)} dependencias faltantes:")
            
            for pkg in missing_packages:
                print(f"Instalando {pkg}...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg], 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print(f"✓ {pkg} instalado correctamente")
                except subprocess.CalledProcessError as e:
                    print(f"✗ Error al instalar {pkg}: {e}")
                    print("Por favor instale la dependencia manualmente:")
                    print(f"    pip install {pkg}")
            
            print("===== Instalación de dependencias completada =====")
        return True

if __name__ == "__main__":
    # Si se ejecuta directamente este archivo, verificar todas las dependencias
    DependencyManager.verify_and_install()
