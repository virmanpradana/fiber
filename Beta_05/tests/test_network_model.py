#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import tempfile
import shutil

# Ajustar path para importar desde src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.model.network_model import NetworkModel
from src.model.storage import ConfigStorage

class TestNetworkModel(unittest.TestCase):
    """Pruebas para el modelo de red híbrido."""
    
    def setUp(self):
        """Preparar entorno de prueba."""
        # Crear directorio temporal para tests
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test_config.db')
        
        # Inicializar storage y modelo
        self.storage = ConfigStorage(self.db_path)
        self.model = NetworkModel(self.storage)
    
    def tearDown(self):
        """Limpiar después de las pruebas."""
        # Cerrar conexiones
        if hasattr(self, 'storage'):
            self.storage.close()
        
        # Eliminar directorio temporal
        shutil.rmtree(self.test_dir)
    
    def test_initial_graph(self):
        """Verifica que el grafo inicial tiene nodos y enlaces correctos."""
        # El modelo debe tener al menos el nodo SET y algunos CTs
        self.assertTrue('SET' in self.model.G)
        
        # Debe haber algunos nodos más además de SET
        self.assertGreater(len(self.model.G.nodes()), 1)
        
        # Debe haber algunos enlaces
        self.assertGreater(len(self.model.G.edges()), 0)
    
    def test_check_ct_connectivity(self):
        """Verifica la detección de conectividad de CTs."""
        # SET siempre debe estar conectado
        self.assertEqual(self.model.check_ct_connectivity('SET'), 'conectado')
        
        # Verificar un CT que debe estar conectado inicialmente
        first_circuit_cts = list(self.model.G.neighbors('SET'))
        if first_circuit_cts:
            first_ct = first_circuit_cts[0]
            self.assertEqual(self.model.check_ct_connectivity(first_ct), 'conectado')
        
        # Un nodo inexistente debe reportar error
        self.assertEqual(self.model.check_ct_connectivity('NODO_INEXISTENTE'), 'error')
    
    def test_update_fiber_status(self):
        """Verifica la actualización del estado de fibras."""
        # Obtener el primer segmento para probar
        segments = self.model.get_segment_data()
        if not segments:
            self.skipTest("No hay segmentos para probar")
        
        segment = segments[0]
        segment_id = segment['id']
        
        # Verificar que inicialmente todas las fibras están ok
        for i in range(1, 5):  # Fibras de comunicación
            fiber_key = str(i)
            self.assertEqual(segment['fibers'].get(fiber_key), 'ok')
        
        # Cambiar estado de una fibra
        success, message = self.model.update_fiber_status(segment_id, 1, 'averiado')
        self.assertTrue(success)
        
        # Verificar que el estado cambió
        segments = self.model.get_segment_data()
        for s in segments:
            if s['id'] == segment_id:
                self.assertEqual(s['fibers']['1'], 'averiado')
                break
        
        # Intentar cambiar una fibra inexistente
        success, message = self.model.update_fiber_status('segmento_inexistente', 1, 'averiado')
        self.assertFalse(success)
    
    def test_get_network_status(self):
        """Verifica la obtención del estado completo de la red."""
        status = self.model.get_network_status()
        
        # Verificar que contiene las secciones esperadas
        self.assertIn('ct_connectivity', status)
        self.assertIn('segment_statuses', status)
        self.assertIn('suggestions', status)
        
        # Verificar que hay datos en cada sección
        self.assertTrue(isinstance(status['ct_connectivity'], dict))
        self.assertTrue(isinstance(status['segment_statuses'], list))
        self.assertTrue(isinstance(status['suggestions'], list))
    
    def test_save_load_configuration(self):
        """Verifica el guardado y carga de configuraciones."""
        # Guardar configuración actual
        config_name = "test_config"
        success, _ = self.model.save_configuration(config_name)
        self.assertTrue(success)
        
        # Modificar un segmento
        segments = self.model.get_segment_data()
        if segments:
            segment_id = segments[0]['id']
            self.model.update_fiber_status(segment_id, 1, 'averiado')
        
        # Cargar configuración guardada (debe restaurar estado original)
        success, _ = self.model.load_configuration(config_name)
        self.assertTrue(success)
        
        # Verificar que se restauró el estado original
        segments = self.model.get_segment_data()
        if segments:
            segment = next((s for s in segments if s['id'] == segment_id), None)
            if segment:
                self.assertEqual(segment['fibers']['1'], 'ok')
    
    def test_logical_graph(self):
        """Verifica la construcción del grafo lógico."""
        # Obtener grafo lógico
        logical_graph = self.model.get_logical_graph()
        
        # Debe ser un grafo dirigido
        self.assertTrue(hasattr(logical_graph, 'is_directed') and logical_graph.is_directed())
        
        # Debe contener al menos el nodo SET
        self.assertTrue('SET' in logical_graph)
        
        # Verificar caché (el segundo llamado debe usar caché)
        self.model._cache_valid = True
        cached_graph = self.model.get_logical_graph()
        self.assertIs(cached_graph, logical_graph)

if __name__ == '__main__':
    unittest.main()