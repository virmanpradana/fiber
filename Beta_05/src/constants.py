#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Constantes y configuraciones predefinidas para la aplicación.
Este archivo contiene las configuraciones para las diferentes plantas.
"""

# Definición de las configuraciones predefinidas para plantas
DEFAULT_CIRCUITOS = {
    'C1': ['CT21', 'CT22'],
    'C2': ['CT12', 'CT19', 'CT20'],
    'C3': ['CT16', 'CT17', 'CT18'],
    'C4': ['CT13', 'CT14', 'CT15'],
    'C5': ['CT07', 'CT10', 'CT11'],
    'C6': ['CT04', 'CT05', 'CT06'],
    'C7': ['CT01', 'CT02', 'CT03'],
    'C8': ['CT09', 'CT08'],
}
DEFAULT_RING_ORDER = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']

# Configuraciones para fibras
DEFAULT_FIBRAS_COMMS_IDA = [1, 2]
DEFAULT_FIBRAS_COMMS_VUELTA = [3, 4]
DEFAULT_FIBRAS_RESERVA = list(range(5, 13))
DEFAULT_FIBRAS_CCTV = list(range(13, 17))
DEFAULT_TOTAL_FIBRAS = 16

# Configuraciones predefinidas para las plantas
PLANT_CONFIGS = {
    # Sabinar I - Configuración completa 22 CTs
    "Sabinar I": {
        "circuitos": DEFAULT_CIRCUITOS,
        "ring_order": DEFAULT_RING_ORDER,
        "fibras": {
            "comms_ida": DEFAULT_FIBRAS_COMMS_IDA,
            "comms_vuelta": DEFAULT_FIBRAS_COMMS_VUELTA,
            "reserva": DEFAULT_FIBRAS_RESERVA,
            "cctv": DEFAULT_FIBRAS_CCTV,
            "total": DEFAULT_TOTAL_FIBRAS
        },
        "gps_positions": {  # Posiciones GPS simuladas para Sabinar I
            "SET": (39.5000, -2.0000),
            "CT01": (39.4950, -2.0050),
            "CT02": (39.4930, -2.0100),
            "CT03": (39.4910, -2.0150),
            "CT04": (39.4890, -2.0200),
            "CT05": (39.4870, -2.0250),
            "CT06": (39.4850, -2.0300),
            "CT07": (39.4830, -2.0350),
            "CT08": (39.4810, -2.0400),
            "CT09": (39.4790, -2.0450),
            "CT10": (39.4770, -2.0500),
            "CT11": (39.4750, -2.0550),
            "CT12": (39.5050, -2.0050),
            "CT13": (39.5070, -2.0100),
            "CT14": (39.5090, -2.0150),
            "CT15": (39.5110, -2.0200),
            "CT16": (39.5130, -2.0250),
            "CT17": (39.5150, -2.0300),
            "CT18": (39.5170, -2.0350),
            "CT19": (39.5190, -2.0400),
            "CT20": (39.5210, -2.0450),
            "CT21": (39.5230, -2.0500),
            "CT22": (39.5250, -2.0550),
        }
    }
}

# Configuraciones CCTV predefinidas para plantas
CCTV_CONFIGS = {
    "Sabinar I": {
        "CT01": {"camaras": 2, "baculos": ["B01", "B02"]},
        "CT05": {"camaras": 1, "baculos": ["B03"]},
        "CT10": {"camaras": 3, "baculos": ["B04", "B05", "B06"]},
        "CT15": {"camaras": 2, "baculos": ["B07", "B08"]},
        "CT20": {"camaras": 1, "baculos": ["B09"]}
    }
}

def get_plant_config(plant_id):
    """Obtiene la configuración para una planta específica.
    
    Args:
        plant_id (str): ID de la planta
        
    Returns:
        dict: Configuración de la planta o configuración por defecto
    """
    # Si existe configuración predefinida, devolverla
    if plant_id in PLANT_CONFIGS:
        return PLANT_CONFIGS[plant_id]
    
    # Si no, devolver configuración por defecto
    return {
        "circuitos": DEFAULT_CIRCUITOS,
        "ring_order": DEFAULT_RING_ORDER,
        "fibras": {
            "comms_ida": DEFAULT_FIBRAS_COMMS_IDA,
            "comms_vuelta": DEFAULT_FIBRAS_COMMS_VUELTA,
            "reserva": DEFAULT_FIBRAS_RESERVA,
            "cctv": DEFAULT_FIBRAS_CCTV,
            "total": DEFAULT_TOTAL_FIBRAS
        },
        "gps_positions": {}
    }

def get_cctv_config(plant_id):
    """Obtiene la configuración CCTV para una planta específica.
    
    Args:
        plant_id (str): ID de la planta
        
    Returns:
        dict: Configuración CCTV de la planta o diccionario vacío
    """
    if plant_id in CCTV_CONFIGS:
        return CCTV_CONFIGS[plant_id].copy()
    
    # Si no hay configuración predefinida, devolver vacío
    return {}
