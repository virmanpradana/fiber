#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sqlite3
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigStorage:
    """Clase para gestionar la persistencia de configuraciones usando SQLite con soporte multi-planta."""
    
    def __init__(self, db_path):
        """Inicializa el almacenamiento.
        
        Args:
            db_path: Ruta al archivo SQLite
        """
        self.db_path = db_path
        
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Inicializar la base de datos
        self._init_db()
        
        logger.info(f"Almacenamiento configurado en: {db_path}")
    
    def _init_db(self):
        """Inicializa la estructura de la base de datos."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
            cursor = conn.cursor()
            
            # Verificar si existe la tabla con formato antiguo (sin soporte multi-planta)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configurations'")
            old_table_exists = cursor.fetchone() is not None
            
            # Verificar si tenemos el nuevo esquema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plants'")
            new_schema_exists = cursor.fetchone() is not None
            
            # Verificar la estructura de la tabla configurations
            if old_table_exists:
                cursor.execute("PRAGMA table_info(configurations)")
                columns = {row['name']: row for row in cursor.fetchall()}
                has_is_default = 'is_default' in columns
                has_plant_id = 'plant_id' in columns
                
                if not has_plant_id or not has_is_default:
                    # Necesitamos recrear la tabla con la estructura correcta
                    logger.info("Detectada estructura de tabla obsoleta. Recreando esquema...")
                    self._backup_and_recreate_schema(conn, cursor)
                elif old_table_exists and not new_schema_exists:
                    # Es necesario migrar el esquema
                    logger.info("Migrando esquema de base de datos para soporte multi-planta...")
                    self._migrate_schema(conn, cursor)
                else:
                    # Crear índices en caso de que falten
                    self._ensure_indices(conn, cursor)
            else:
                # Crear esquema nuevo si no existe
                if not new_schema_exists:
                    self._create_schema(conn, cursor)
            
            # Verificar existencia de tablas antes de eliminar registros
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plants'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM plants WHERE name = ?", ("Olmedilla",))
                cursor.execute("DELETE FROM plants WHERE name = ?", ("Sabinar II",))
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configurations'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM configurations WHERE plant_id = ?", ("Olmedilla",))
                cursor.execute("DELETE FROM configurations WHERE plant_id = ?", ("Sabinar II",))
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='network_data'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM network_data WHERE plant_id = ?", ("Olmedilla",))
                cursor.execute("DELETE FROM network_data WHERE plant_id = ?", ("Sabinar II",))
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='node_positions'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM node_positions WHERE plant_id = ?", ("Olmedilla",))
                cursor.execute("DELETE FROM node_positions WHERE plant_id = ?", ("Sabinar II",))
            
            conn.commit()
            conn.close()
            
            logger.info("Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    def _backup_and_recreate_schema(self, conn, cursor):
        """Hace backup de los datos existentes y recrea el esquema"""
        try:
            # 1. Obtener los datos actuales si existen
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configurations'")
            if cursor.fetchone():
                try:
                    cursor.execute("SELECT name, data, created, modified FROM configurations")
                    old_data = cursor.fetchall()
                    logger.info(f"Respaldados {len(old_data)} registros para migración")
                except sqlite3.OperationalError as e:
                    logger.warning(f"No se pudo respaldar datos debido a error: {e}")
                    old_data = []
            else:
                old_data = []
            
            # 2. Eliminar tablas antiguas
            cursor.execute("DROP TABLE IF EXISTS configurations")
            cursor.execute("DROP TABLE IF EXISTS configurations_old")
            
            # 3. Crear nuevo esquema
            self._create_schema(conn, cursor)
            
            # 4. Migrar datos antiguos si estaban disponibles
            if old_data:
                for item in old_data:
                    name = item[0]
                    data = item[1]
                    
                    # Si podemos obtener created y modified los usamos, si no usamos valores actuales
                    created = item[2] if len(item) > 2 else datetime.now().isoformat()
                    modified = item[3] if len(item) > 3 else datetime.now().isoformat()
                    
                    cursor.execute('''
                        INSERT INTO configurations (name, plant_id, data, is_default, created, modified)
                        VALUES (?, 'default', ?, 0, ?, ?)
                    ''', (name, data, created, modified))
                
                logger.info(f"Migrados {len(old_data)} registros al nuevo esquema")
            
            return True
        except Exception as e:
            logger.error(f"Error durante backup y recreación: {e}")
            raise
    
    def _ensure_indices(self, conn, cursor):
        """Crea índices si no existen"""
        # Asegurarse que los índices existen
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_plant_id ON configurations(plant_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_is_default ON configurations(is_default)')
        logger.info("Índices verificados")
    
    def _create_schema(self, conn, cursor):
        """Crea el esquema de la base de datos desde cero."""
        # Tabla de plantas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Añadir planta por defecto
        cursor.execute('''
            INSERT OR IGNORE INTO plants (id, name, description)
            VALUES ('default', 'Planta por defecto', 'Planta creada automáticamente')
        ''')
        
        # Tabla de configuraciones con soporte multi-planta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                data TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, plant_id),
                FOREIGN KEY (plant_id) REFERENCES plants(id)
            )
        ''')
        
        # Tabla de log de cambios de estado de fibras
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fiber_status_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                segment_id TEXT NOT NULL,
                fiber_num INTEGER NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                user_id TEXT,
                FOREIGN KEY (plant_id) REFERENCES plants(id)
            )
        ''')
        
        # Índices
        self._ensure_indices(conn, cursor)
        
        logger.info("Esquema de base de datos creado")
    
    def _migrate_schema(self, conn, cursor):
        """Migra el esquema antiguo al nuevo con soporte multi-planta."""
        # 1. Crear las nuevas tablas
        self._create_schema(conn, cursor)
        
        # 2. Migrar datos si existe la tabla antigua
        try:
            # Verificar si hay datos que migrar
            cursor.execute("SELECT COUNT(*) FROM configurations")
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"Migrando {count} configuraciones al nuevo esquema...")
                
                # Copiar datos de la tabla antigua a la nueva
                cursor.execute('''
                    INSERT INTO configurations (name, plant_id, data, created, modified)
                    SELECT name, 'default', data, created, modified FROM configurations
                ''')
                
                # Renombrar tabla antigua
                cursor.execute('ALTER TABLE configurations RENAME TO configurations_old')
                
                logger.info("Datos migrados correctamente")
        except Exception as e:
            logger.error(f"Error durante la migración de datos: {e}")
            raise
    
    def save_config(self, name, config_data, plant_id="default", is_default=False):
        """Guarda una configuración.
        
        Args:
            name: Nombre de la configuración
            config_data: Datos de configuración (se serializarán a JSON)
            plant_id: ID de la planta
            is_default: Si es la configuración por defecto para la planta
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Serializar a JSON
            data_json = json.dumps(config_data, default=str)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar si existen las tablas necesarias
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plants'")
            plants_exists = cursor.fetchone() is not None
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configurations'")
            config_exists = cursor.fetchone() is not None
            
            # Si no existen las tablas, crear el esquema
            if not plants_exists or not config_exists:
                self._create_schema(conn, cursor)
            
            # Asegurar que la planta existe
            cursor.execute('INSERT OR IGNORE INTO plants (id, name) VALUES (?, ?)', 
                          (plant_id, plant_id))
            
            if is_default:
                # Quitar la marca de defecto de otras configuraciones de la misma planta
                cursor.execute('''
                    UPDATE configurations SET is_default = 0
                    WHERE plant_id = ? AND is_default = 1
                ''', (plant_id,))
            
            # Insertar o actualizar
            cursor.execute('''
                INSERT OR REPLACE INTO configurations 
                (name, plant_id, data, is_default, modified) 
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (name, plant_id, data_json, 1 if is_default else 0))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Configuración '{name}' guardada correctamente para planta '{plant_id}'")
            return True
        except Exception as e:
            logger.error(f"Error guardando configuración '{name}' para planta '{plant_id}': {e}")
            return False
    
    def load_config(self, name, plant_id="default"):
        """Carga una configuración por nombre.
        
        Args:
            name: Nombre de la configuración
            plant_id: ID de la planta
            
        Returns:
            dict: Datos de configuración o None si no se encuentra
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data FROM configurations 
                WHERE name = ? AND plant_id = ?
            ''', (name, plant_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Deserializar JSON
                config_data = json.loads(row[0])
                logger.info(f"Configuración '{name}' cargada correctamente para planta '{plant_id}'")
                return config_data
            else:
                logger.warning(f"Configuración '{name}' no encontrada para planta '{plant_id}'")
                return None
        except Exception as e:
            logger.error(f"Error cargando configuración '{name}' para planta '{plant_id}': {e}")
            return None
    
    def get_default_config(self, plant_id="default"):
        """Obtiene la configuración por defecto para una planta.
        
        Args:
            plant_id: ID de la planta
            
        Returns:
            dict: Datos de configuración por defecto o None si no hay
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data FROM configurations 
                WHERE plant_id = ? AND is_default = 1
                ORDER BY modified DESC LIMIT 1
            ''', (plant_id,))
            
            row = cursor.fetchone()
            
            if not row:
                # Si no hay configuración por defecto, intentar con el nombre "default"
                cursor.execute('''
                    SELECT data FROM configurations 
                    WHERE plant_id = ? AND name = 'default'
                    ORDER BY modified DESC LIMIT 1
                ''', (plant_id,))
                row = cursor.fetchone()
            
            conn.close()
            
            if row:
                # Deserializar JSON
                config_data = json.loads(row[0])
                return config_data
            else:
                return None
        except Exception as e:
            logger.error(f"Error cargando configuración por defecto para planta '{plant_id}': {e}")
            return None
    
    def list_configs(self, plant_id="default"):
        """Lista todas las configuraciones disponibles para una planta.
        
        Args:
            plant_id: ID de la planta
        
        Returns:
            list: Lista de diccionarios con información de configuraciones
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, is_default, created, modified FROM configurations
                WHERE plant_id = ?
                ORDER BY modified DESC
            ''', (plant_id,))
            
            configs = []
            for row in cursor.fetchall():
                configs.append({
                    'name': row['name'],
                    'is_default': bool(row['is_default']),
                    'created': row['created'],
                    'modified': row['modified']
                })
            
            conn.close()
            return configs
        except Exception as e:
            logger.error(f"Error listando configuraciones para planta '{plant_id}': {e}")
            return []
    
    def delete_config(self, name, plant_id="default"):
        """Elimina una configuración.
        
        Args:
            name: Nombre de la configuración
            plant_id: ID de la planta
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM configurations 
                WHERE name = ? AND plant_id = ?
            ''', (name, plant_id))
            
            result = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if result:
                logger.info(f"Configuración '{name}' eliminada correctamente de planta '{plant_id}'")
            else:
                logger.warning(f"Configuración '{name}' no encontrada para eliminar en planta '{plant_id}'")
            
            return result
        except Exception as e:
            logger.error(f"Error eliminando configuración '{name}' de planta '{plant_id}': {e}")
            return False
    
    def get_plants(self):
        """Obtiene la lista de plantas disponibles.
        
        Returns:
            list: Lista de IDs de plantas
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM plants ORDER BY name')
            
            plants = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return plants if plants else ["default"]
        except Exception as e:
            logger.error(f"Error obteniendo lista de plantas: {e}")
            return ["default"]
    
    def plant_exists(self, plant_id):
        """Verifica si una planta existe.
        
        Args:
            plant_id: ID de la planta
            
        Returns:
            bool: True si la planta existe
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM plants WHERE id = ?', (plant_id,))
            
            exists = cursor.fetchone() is not None
            conn.close()
            
            return exists
        except Exception as e:
            logger.error(f"Error verificando existencia de planta '{plant_id}': {e}")
            return False
    
    def create_plant(self, plant_id, name=None, description=None):
        """Crea una nueva planta.
        
        Args:
            plant_id: ID de la planta
            name: Nombre visible (si es None, se usa el ID)
            description: Descripción opcional
            
        Returns:
            bool: True si se creó correctamente
        """
        try:
            if not name:
                name = plant_id
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO plants (id, name, description)
                VALUES (?, ?, ?)
            ''', (plant_id, name, description))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Planta '{plant_id}' creada correctamente")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"La planta '{plant_id}' ya existe")
            return False
        except Exception as e:
            logger.error(f"Error creando planta '{plant_id}': {e}")
            return False
    
    def rename_plant(self, old_id, new_id, new_name=None):
        """Renombra una planta.
        
        Args:
            old_id: ID actual de la planta
            new_id: Nuevo ID para la planta
            new_name: Nuevo nombre visible (si es None, se usa el nuevo ID)
            
        Returns:
            bool: True si se renombró correctamente
        """
        try:
            if not new_name:
                new_name = new_id
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar que la planta existe
            cursor.execute('SELECT 1 FROM plants WHERE id = ?', (old_id,))
            if not cursor.fetchone():
                conn.close()
                logger.warning(f"La planta '{old_id}' no existe")
                return False
                
            # Verificar que el nuevo ID no existe
            cursor.execute('SELECT 1 FROM plants WHERE id = ?', (new_id,))
            if cursor.fetchone():
                conn.close()
                logger.warning(f"Ya existe una planta con ID '{new_id}'")
                return False
            
            # Actualizar planta
            cursor.execute('''
                UPDATE plants SET id = ?, name = ?, modified = datetime('now')
                WHERE id = ?
            ''', (new_id, new_name, old_id))
            
            # Actualizar referencias en configuraciones
            cursor.execute('''
                UPDATE configurations SET plant_id = ?
                WHERE plant_id = ?
            ''', (new_id, old_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Planta '{old_id}' renombrada a '{new_id}'")
            return True
        except Exception as e:
            logger.error(f"Error renombrando planta '{old_id}' a '{new_id}': {e}")
            return False
    
    def delete_plant(self, plant_id):
        """Elimina una planta y todas sus configuraciones.
        
        Args:
            plant_id: ID de la planta
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar que no es la última planta
            cursor.execute('SELECT COUNT(*) FROM plants')
            if cursor.fetchone()[0] <= 1:
                conn.close()
                logger.warning("No se puede eliminar la última planta")
                return False
            
            # Eliminar configuraciones de la planta
            cursor.execute('DELETE FROM configurations WHERE plant_id = ?', (plant_id,))
            
            # Eliminar planta
            cursor.execute('DELETE FROM plants WHERE id = ?', (plant_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Planta '{plant_id}' y sus configuraciones eliminadas correctamente")
            return True
        except Exception as e:
            logger.error(f"Error eliminando planta '{plant_id}': {e}")
            return False
    
    def copy_configurations(self, source_plant_id, target_plant_id):
        """Copia todas las configuraciones de una planta a otra.
        
        Args:
            source_plant_id: ID de la planta origen
            target_plant_id: ID de la planta destino
            
        Returns:
            bool: True si se copiaron correctamente
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar que ambas plantas existen
            cursor.execute('SELECT 1 FROM plants WHERE id = ?', (source_plant_id,))
            if not cursor.fetchone():
                conn.close()
                logger.warning(f"La planta origen '{source_plant_id}' no existe")
                return False
                
            cursor.execute('SELECT 1 FROM plants WHERE id = ?', (target_plant_id,))
            if not cursor.fetchone():
                conn.close()
                logger.warning(f"La planta destino '{target_plant_id}' no existe")
                return False
            
            # Obtener configuraciones de origen
            cursor.execute('''
                SELECT name, data, is_default FROM configurations
                WHERE plant_id = ?
            ''', (source_plant_id,))
            
            configs = cursor.fetchall()
            
            # Copiar cada configuración
            for name, data, is_default in configs:
                cursor.execute('''
                    INSERT OR REPLACE INTO configurations
                    (name, plant_id, data, is_default, created, modified)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                ''', (name, target_plant_id, data, is_default))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Configuraciones copiadas de '{source_plant_id}' a '{target_plant_id}'")
            return True
        except Exception as e:
            logger.error(f"Error copiando configuraciones: {e}")
            return False
    
    def get_plant_info(self, plant_id):
        """Obtiene información de una planta.
        
        Args:
            plant_id: ID de la planta
            
        Returns:
            dict: Información de la planta o None si no existe
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, created, modified FROM plants
                WHERE id = ?
            ''', (plant_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'created': row['created'],
                    'modified': row['modified']
                }
            else:
                return None
        except Exception as e:
            logger.error(f"Error obteniendo información de planta '{plant_id}': {e}")
            return None
    
    def list_plants(self):
        """Lista todas las plantas con información detallada.
        
        Returns:
            list: Lista de diccionarios con información de plantas
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, created, modified FROM plants
                ORDER BY name
            ''')
            
            plants = []
            for row in cursor.fetchall():
                plants.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'created': row['created'],
                    'modified': row['modified']
                })
                
            conn.close()
            return plants
        except Exception as e:
            logger.error(f"Error listando plantas: {e}")
            return []
    
    def log_fiber_status_change(self, plant_id, segment_id, fiber_num, old_status, new_status, user_id=None):
        """Registra un cambio de estado de fibra en el log histórico."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO fiber_status_log (timestamp, plant_id, segment_id, fiber_num, old_status, new_status, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                plant_id,
                segment_id,
                fiber_num,
                old_status,
                new_status,
                user_id
            ))
            conn.commit()
            conn.close()
            logger.info(f"Log cambio fibra: {plant_id} {segment_id} F{fiber_num} {old_status}->{new_status}")
            return True
        except Exception as e:
            logger.error(f"Error registrando log de fibra: {e}")
            return False
    
    def get_fiber_status_history(self, plant_id=None, segment_id=None, fiber_num=None, limit=100):
        """Consulta el historial de cambios de estado de fibras.
        Args:
            plant_id: ID de la planta (opcional)
            segment_id: ID del segmento (opcional)
            fiber_num: número de fibra (opcional)
            limit: máximo de registros a devolver
        Returns:
            Lista de dicts con los campos del log ordenados por timestamp descendente.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM fiber_status_log WHERE 1=1"
            params = []
            if plant_id:
                query += " AND plant_id = ?"
                params.append(plant_id)
            if segment_id:
                query += " AND segment_id = ?"
                params.append(segment_id)
            if fiber_num:
                query += " AND fiber_num = ?"
                params.append(int(fiber_num))
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error consultando historial de fibras: {e}")
            return []
    
    def close(self):
        """Cierra cualquier recurso pendiente."""
        # No hay recursos persistentes que cerrar en esta implementación
        pass