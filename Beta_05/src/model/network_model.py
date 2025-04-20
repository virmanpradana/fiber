#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import logging
import time
import threading
from typing import Dict, List, Tuple, Optional, Any, Set
import json
import os
from datetime import datetime
import sys

# Añadir directorio padre al path para importar constantes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import get_plant_config, DEFAULT_CIRCUITOS, DEFAULT_RING_ORDER
from constants import DEFAULT_FIBRAS_COMMS_IDA, DEFAULT_FIBRAS_COMMS_VUELTA
from constants import DEFAULT_FIBRAS_RESERVA, DEFAULT_FIBRAS_CCTV, DEFAULT_TOTAL_FIBRAS

# Logger por defecto
default_logger = logging.getLogger(__name__)

CACHE_EXPIRATION_TIME = 10  # Segundos

def _has_path_limited(graph, source, target, max_depth=30):
    """Búsqueda iterativa limitada para evitar recursión infinita."""
    if source == target:
        return True
    visited = set()
    stack = [(source, 0)]
    while stack:
        node, depth = stack.pop()
        if node == target:
            return True
        if depth >= max_depth:
            continue
        for neighbor in graph.successors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append((neighbor, depth + 1))
    return False

def _has_path_limited_iterative(graph, source, target, max_depth=30):
    """Búsqueda iterativa en profundidad limitada para evitar recursión infinita."""
    if source == target:
        return True
    visited = {source}
    stack = [(source, 0)]
    while stack:
        node, depth = stack.pop()
        if node == target:
            return True
        if depth >= max_depth:
            continue
        try:
            neighbors = list(graph.successors(node))
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append((neighbor, depth + 1))
        except Exception as e:
            default_logger.error(f"Error obteniendo sucesores para {node} en _has_path_limited_iterative: {e}")
            return False
    return False

class NetworkModel:
    """Modelo para la red de fibra óptica, con soporte para múltiples plantas."""
    
    def _ensure_predefined_plants(self):
        """Asegura que las plantas predefinidas existen en la base de datos."""
        if not self.storage:
            return
        # Solo Sabinar I como preconfigurada
        for plant_id in ["Sabinar I"]:
            if not self.storage.plant_exists(plant_id):
                old_plant_id = self.active_plant_id
                self.active_plant_id = plant_id
                self._init_graph()  # Inicializar con datos predefinidos
                graph_data = self._prepare_graph_data_for_save()
                self.storage.create_plant(plant_id)
                self.storage.save_config("default", graph_data, plant_id, is_default=True)
                self.active_plant_id = old_plant_id

    def __init__(self, storage=None):
        """Inicializa el modelo de red.
        
        Args:
            storage: Instancia de ConfigStorage para guardar/cargar configuraciones
        """
        self.G = nx.Graph()  # Grafo físico
        self.graph_lock = threading.Lock()  # Lock para proteger G
        self._DG_cache = None  # Caché del grafo lógico dirigido
        self._cache_valid = False
        self._last_cache_time = 0
        self.node_positions = {}  # Posiciones de los nodos
        self.storage = storage
        self.active_plant_id = "default"  # ID de la planta activa
        
        # Inicializar plantas predefinidas si no existen
        self._ensure_predefined_plants()
        # Inicializar con valores por defecto
        self._init_graph()
        default_logger.info("NetworkModel inicializado con soporte multi-planta")
    
    def _init_graph(self, graph_data=None):
        """Inicializa el grafo con datos cargados o con valores por defecto."""
        with self.graph_lock:
            default_logger.info(f"[INIT_GRAPH] INICIO para planta: {self.active_plant_id}")
            self.G.clear()
            
            if graph_data and isinstance(graph_data, dict):
                default_logger.info("Inicializando grafo desde datos cargados")
                # Aquí iría el código para cargar nodos y enlaces desde graph_data
                # Simplificado para este ejemplo
                nodes = graph_data.get('nodes', [])
                edges = graph_data.get('edges', [])
                
                for node in nodes:
                    default_logger.debug(f"Añadiendo nodo: {node['id']} datos: {node}")
                    self.G.add_node(node['id'], **{k: v for k, v in node.items() if k != 'id'})
                
                for edge in edges:
                    default_logger.debug(f"Añadiendo enlace: {edge['source']}->{edge['target']} datos: {edge}")
                    self.G.add_edge(
                        edge['source'],
                        edge['target'],
                        **{k: v for k, v in edge.items() if k not in ['source', 'target']}
                    )
                
                # Cargar posiciones si existen
                if 'node_positions' in graph_data:
                    self.node_positions = graph_data['node_positions']
            else:
                default_logger.info(f"Inicializando grafo por defecto para planta {self.active_plant_id}")
                # Obtener configuración de la planta activa
                plant_config = get_plant_config(self.active_plant_id)
                circuitos = plant_config.get("circuitos", DEFAULT_CIRCUITOS)
                ring_order = plant_config.get("ring_order", DEFAULT_RING_ORDER)
                default_logger.debug(f"Configuración circuitos: {circuitos}")
                
                # Crear nodo SET
                self.G.add_node('SET', type='set', label='SET')
                default_logger.debug("Añadido nodo SET")
                
                # Agregar CTs según circuitos
                for circuit_id, cts in circuitos.items():
                    for ct in cts:
                        if not self.G.has_node(ct):
                            default_logger.debug(f"Añadiendo nodo CT: {ct} (circuito {circuit_id})")
                            self.G.add_node(ct, type='ct', circuit=circuit_id, label=ct)
                        else:
                            self.G.nodes[ct]['circuit'] = circuit_id
                
                # Conectar SET con cada CT inicial de circuito
                for circuit_id, cts in circuitos.items():
                    if not cts:
                        continue
                    
                    # SET -> primer CT
                    origen = 'SET'
                    destino = cts[0]
                    segment_id = f"{origen}-{destino}"
                    default_logger.debug(f"Añadiendo enlace: {origen}->{destino} (circuito {circuit_id})")
                    self.G.add_edge(
                        origen,
                        destino,
                        id=segment_id,
                        circuit=circuit_id,
                        fibers=self._get_initial_fiber_status()
                    )
                    
                    # Conectar CTs en secuencia
                    for i in range(len(cts) - 1):
                        origen = cts[i]
                        destino = cts[i+1]
                        segment_id = f"{origen}-{destino}"
                        default_logger.debug(f"Añadiendo enlace: {origen}->{destino} (circuito {circuit_id})")
                        self.G.add_edge(
                            origen,
                            destino,
                            id=segment_id,
                            circuit=circuit_id,
                            fibers=self._get_initial_fiber_status()
                        )
                
                # Inicializar posiciones de nodos desde la configuración de la planta
                gps_positions = plant_config.get('gps_positions', {})
                for node_id, coords in gps_positions.items():
                    if node_id in self.G:
                        # Convertir coordenadas GPS a posiciones en el grafo
                        # Simplificado: usamos las coordenadas GPS como posición relativa
                        self.node_positions[node_id] = coords
            
            # Invalidar caché
            self._cache_valid = False
            self._DG_cache = None
            self._last_cache_time = 0
            default_logger.info(f"[INIT_GRAPH] FIN para planta: {self.active_plant_id} (nodos: {len(self.G.nodes())}, enlaces: {len(self.G.edges())})")
    
    def _get_initial_fiber_status(self):
        """Genera estado inicial para todas las fibras."""
        return {str(i): 'ok' for i in range(1, DEFAULT_TOTAL_FIBRAS + 1)}
    
    def get_logical_graph(self):
        """Construye y devuelve el grafo lógico dirigido."""
        with self.graph_lock:
            logging.info("[GET_LOGICAL_GRAPH] Iniciando construcción/obtención de DG")
            current_time = time.time()
            if not self._cache_valid or self._DG_cache is None or (current_time - self._last_cache_time > CACHE_EXPIRATION_TIME):
                logging.info("[GET_LOGICAL_GRAPH] Construyendo DG desde cero")
                self._DG_cache = self._build_directed_logical_graph_py()
                self._cache_valid = True
                self._last_cache_time = current_time
            logging.info("[GET_LOGICAL_GRAPH] Finalizado")
            return self._DG_cache
    
    def _build_directed_logical_graph_py(self):
        logging.info("[BUILD_DG] INICIO para planta: %s", self.active_plant_id)
        DG = nx.DiGraph()
        DG.add_nodes_from(self.G.nodes(data=True))
        plant_config = get_plant_config(self.active_plant_id)
        fibras_config = plant_config.get('fibras', {})
        fibras_ida = fibras_config.get('comms_ida', DEFAULT_FIBRAS_COMMS_IDA)
        fibras_vuelta = fibras_config.get('comms_vuelta', DEFAULT_FIBRAS_COMMS_VUELTA)
        for u, v, data in self.G.edges(data=True):
            segment_id = data.get('id', f"{u}-{v}")
            circuit_id = data.get('circuit')
            fibers_status = data.get('fibers', {})
            logging.debug(f"[BUILD_DG] Procesando enlace {u}-{v}")
            if self._check_segment_path_direction(fibers_status, fibras_ida):
                DG.add_edge(u, v, type='ida', circuit=circuit_id, segment=segment_id)
                logging.debug(f"[BUILD_DG] Añadido edge IDA {u}->{v}")
            if self._check_segment_path_direction(fibers_status, fibras_vuelta):
                DG.add_edge(v, u, type='vuelta', circuit=circuit_id, segment=segment_id)
                logging.debug(f"[BUILD_DG] Añadido edge VUELTA {v}->{u}")
        self._add_ring_connections_py(DG)
        logging.info("[BUILD_DG] FIN para planta: %s", self.active_plant_id)
        return DG
    
    def _check_segment_path_direction(self, fibers_status, direction_fibers):
        """Verifica si existe al menos una fibra 'ok' en la dirección dada."""
        if not fibers_status:
            return False
        
        for fiber_num in direction_fibers:
            if fibers_status.get(str(fiber_num)) == 'ok':
                return True
        
        return False
    
    def _add_ring_connections_py(self, DG):
        """Añade conexiones lógicas de parcheo en SET entre circuitos evitando ciclos redundantes."""
        plant_config = get_plant_config(self.active_plant_id)
        ring_order = plant_config.get('ring_order', DEFAULT_RING_ORDER)
        circuitos = plant_config.get('circuitos', DEFAULT_CIRCUITOS)
        if not ring_order:
            return
        num_circuits = len(ring_order)
        for i in range(num_circuits):
            circuit_actual = ring_order[i]
            circuit_siguiente = ring_order[(i + 1) % num_circuits]
            cts_actual = circuitos.get(circuit_actual, [])
            cts_siguiente = circuitos.get(circuit_siguiente, [])
            if not cts_actual or not cts_siguiente:
                continue
            nodo_final = cts_actual[-1]
            nodo_inicial = cts_siguiente[0]
            logging.debug(f"[ADD_RING] nodo_final: {nodo_final}, nodo_inicial: {nodo_inicial}")
            path_exists = _has_path_limited_iterative(DG, nodo_final, nodo_inicial, max_depth=30)
            logging.debug(f"[ADD_RING] path_exists({nodo_final}->{nodo_inicial}): {path_exists}")
            if (DG.has_node(nodo_final) and DG.has_node('SET') and 
                DG.has_node(nodo_inicial) and 
                not path_exists):
                DG.add_edge(
                    nodo_final, 
                    nodo_inicial, 
                    type='set_patch',
                    from_circuit=circuit_actual, 
                    to_circuit=circuit_siguiente
                )
                logging.info(f"Añadiendo parche SET: {nodo_final} -> {nodo_inicial}")
        logging.info("[ADD_RING] FIN")

    def check_ct_connectivity(self, target_ct):
        """Verifica la conectividad bidireccional entre SET y un CT."""
        if target_ct == 'SET':
            return 'conectado'
        with self.graph_lock:
            if not self.G.has_node(target_ct):
                default_logger.warning(f"check_ct_connectivity: Nodo {target_ct} no existe")
                return 'error'
        try:
            DG = self.get_logical_graph()
            if not DG.has_node('SET') or not DG.has_node(target_ct):
                return 'aislado'
            try:
                has_path_to_ct = _has_path_limited_iterative(DG, 'SET', target_ct, max_depth=30)
            except Exception:
                default_logger.error(f"Error en has_path entre SET y {target_ct}")
                return 'error'
            try:
                has_path_from_ct = _has_path_limited_iterative(DG, target_ct, 'SET', max_depth=30)
            except Exception:
                default_logger.error(f"Error en has_path entre {target_ct} y SET")
                return 'error'
            if has_path_to_ct and has_path_from_ct:
                return 'conectado'
            else:
                return 'aislado'
        except Exception as e:
            default_logger.error(f"Error en check_ct_connectivity: {e}")
            return 'error'
    
    def _check_ring_integrity(self):
        """Verifica la integridad del anillo lógico evitando recursión infinita."""
        try:
            DG = self.get_logical_graph()
            results = {}
            plant_config = get_plant_config(self.active_plant_id)
            ring_order = plant_config.get('ring_order', DEFAULT_RING_ORDER)
            circuitos = plant_config.get('circuitos', DEFAULT_CIRCUITOS)
            for i in range(len(ring_order)):
                circuit_actual = ring_order[i]
                circuit_siguiente = ring_order[(i + 1) % len(ring_order)]
                cts_actual = circuitos.get(circuit_actual, [])
                cts_siguiente = circuitos.get(circuit_siguiente, [])
                if not cts_actual or not cts_siguiente:
                    results[f"{circuit_actual}-{circuit_siguiente}"] = False
                    continue
                nodo_final = cts_actual[-1]
                nodo_inicial = cts_siguiente[0]
                if nodo_final == nodo_inicial:
                    results[f"{circuit_actual}-{circuit_siguiente}"] = False
                    continue
                if DG.has_node(nodo_final) and DG.has_node(nodo_inicial):
                    try:
                        has_path = _has_path_limited_iterative(DG, nodo_final, nodo_inicial, max_depth=30)
                    except Exception:
                        default_logger.error(f"Error en has_path entre {nodo_final} y {nodo_inicial}")
                        has_path = False
                    results[f"{circuit_actual}-{circuit_siguiente}"] = has_path
                else:
                    results[f"{circuit_actual}-{circuit_siguiente}"] = False
            return results
        except Exception as e:
            default_logger.error(f"Error general en _check_ring_integrity: {e}")
            return {}
    
    def get_network_status(self):
        """Obtiene el estado completo de la red."""
        try:
            try:
                # Obtener todos los CTs
                with self.graph_lock:
                    all_cts = sorted([n for n, d in self.G.nodes(data=True) if d.get('type') == 'ct'])
            except RecursionError:
                print("[ERROR] RecursionError: El grafo es demasiado profundo o está corrupto (nodos).")
                return {
                    'ct_connectivity': {},
                    'segment_statuses': [],
                    'suggestions': ["ERROR: RecursionError: El grafo es demasiado profundo o está corrupto."]
                }

            # Verificar conectividad
            ct_statuses = {}
            for ct in all_cts:
                try:
                    ct_statuses[ct] = self.check_ct_connectivity(ct)
                except RecursionError:
                    print(f"[ERROR] RecursionError: El grafo es demasiado profundo o está corrupto (check_ct_connectivity para {ct}).")
                    ct_statuses[ct] = 'error'

            # Obtener estado de segmentos
            segments = self.get_segment_data()
            
            # Obtener configuración de fibras para la planta activa
            plant_config = get_plant_config(self.active_plant_id)
            fibras_config = plant_config.get('fibras', {})
            
            fibras_ida = fibras_config.get('comms_ida', DEFAULT_FIBRAS_COMMS_IDA)
            fibras_vuelta = fibras_config.get('comms_vuelta', DEFAULT_FIBRAS_COMMS_VUELTA)
            
            # Calcular estado de comunicación por segmento
            for segment in segments:
                fibers = segment.get('fibers', {})
                comm_status = 'ok'
                
                # Verificar fibras de comunicación
                for fiber_num in fibras_ida + fibras_vuelta:
                    if fibers.get(str(fiber_num)) == 'averiado':
                        comm_status = 'faulty'
                        break
                
                segment['comm_status'] = comm_status
            
            # Generar sugerencias
            suggestions = self.get_reconnection_suggestions(ct_statuses, segments)
            
            return {
                'ct_connectivity': ct_statuses,
                'segment_statuses': segments,
                'suggestions': suggestions
            }
        except RecursionError:
            print("[ERROR] RecursionError: El grafo es demasiado profundo o está corrupto (get_network_status).")
            return {
                'ct_connectivity': {},
                'segment_statuses': [],
                'suggestions': ["ERROR: RecursionError: El grafo es demasiado profundo o está corrupto."]
            }
        except Exception as e:
            # No logging here, just print
            print(f"[ERROR] Error en get_network_status: {e}")
            return {
                'ct_connectivity': {},
                'segment_statuses': [],
                'suggestions': [f"ERROR: {e}"]
            }
    
    def get_segment_data(self):
        """Obtiene datos de todos los segmentos."""
        segments = []
        processed_edges = set()
        
        with self.graph_lock:
            for u, v, data in self.G.edges(data=True):
                edge_key = tuple(sorted((u, v)))
                if edge_key in processed_edges:
                    continue
                
                processed_edges.add(edge_key)
                seg_data = data.copy()
                seg_data['id'] = data.get('id', f"{u}-{v}")
                seg_data['source'] = u
                seg_data['target'] = v
                
                # Asegurar que las fibras estén correctamente formateadas
                fibers_dict = seg_data.get('fibers', {})
                if isinstance(fibers_dict, dict):
                    seg_data['fibers'] = {
                        str(k): (v_f if v_f in ['ok', 'averiado'] else 'ok')
                        for k, v_f in fibers_dict.items()
                    }
                else:
                    seg_data['fibers'] = self._get_initial_fiber_status()
                
                segments.append(seg_data)
        
        # Ordenar segmentos
        segments.sort(key=lambda x: (x.get('circuit', 'ZZZ'), x.get('id', '')))
        return segments
    
    def update_fiber_status(self, segment_id, fiber_num, new_status, user_id=None):
        """Actualiza el estado de una fibra específica y registra el cambio en el log histórico."""
        if new_status not in ['ok', 'averiado']:
            return False, f"Estado '{new_status}' no es válido"
        fiber_key = str(fiber_num)
        segment_found = False
        updated = False
        message = f"Segmento {segment_id} no encontrado"
        with self.graph_lock:
            for u, v, data in self.G.edges(data=True):
                segment_match = (
                    data.get('id') == segment_id or 
                    f"{u}-{v}" == segment_id or 
                    f"{v}-{u}" == segment_id
                )
                if segment_match:
                    if 'fibers' not in data or not isinstance(data['fibers'], dict):
                        data['fibers'] = self._get_initial_fiber_status()
                    segment_found = True
                    if fiber_key in data['fibers']:
                        old_status = data['fibers'][fiber_key]
                        if old_status != new_status:
                            data['fibers'][fiber_key] = new_status
                            updated = True
                            message = f"Fibra {fiber_key} en segmento {segment_id} actualizada a '{new_status}'"
                            self._cache_valid = False
                            self._DG_cache = None
                            # Registrar en log histórico
                            if self.storage:
                                self.storage.log_fiber_status_change(
                                    self.active_plant_id, segment_id, fiber_key, old_status, new_status, user_id
                                )
                        else:
                            message = f"Fibra {fiber_key} en {segment_id} ya estaba en estado '{new_status}'"
                    else:
                        message = f"Error: Fibra {fiber_key} no encontrada en el segmento {segment_id}"
                        return False, message
                    break
        return segment_found, message
    
    def get_reconnection_suggestions(self, ct_statuses, segments):
        """Genera sugerencias de diagnóstico basadas en el estado actual."""
        suggestions = []
        
        # Análisis de estado de CTs
        aislados = sorted([ct for ct, st in ct_statuses.items() if st == 'aislado'])
        errores = sorted([ct for ct, st in ct_statuses.items() if st == 'error'])
        conectados = sorted([ct for ct, st in ct_statuses.items() if st == 'conectado'])
        
        if errores:
            suggestions.append(f"🔴 ¡ERROR en CTs!: {', '.join(errores)}. Revisar logs o estado físico.")
        
        if aislados:
            suggestions.append(f"🟠 CTs AISLADOS (sin conexión bidireccional con SET): {', '.join(aislados)}")
        
        total_cts = len(conectados) + len(aislados) + len(errores)
        if not aislados and not errores:
            if total_cts > 0 and len(conectados) == total_cts:
                suggestions.append("✅ Todos los CTs parecen estar conectados bidireccionalmente con SET.")
            elif total_cts == 0:
                suggestions.append("ℹ️ No hay CTs definidos o detectados en la red.")
        
        # Obtener configuración de fibras para la planta activa
        plant_config = get_plant_config(self.active_plant_id)
        fibras_config = plant_config.get('fibras', {})
        
        fibras_ida = fibras_config.get('comms_ida', DEFAULT_FIBRAS_COMMS_IDA)
        fibras_vuelta = fibras_config.get('comms_vuelta', DEFAULT_FIBRAS_COMMS_VUELTA)
        fibras_reserva = fibras_config.get('reserva', DEFAULT_FIBRAS_RESERVA)
        fibras_cctv = fibras_config.get('cctv', DEFAULT_FIBRAS_CCTV)
        
        # Análisis de fibras
        suggestions.append("\n--- Diagnóstico de Fibras de Comunicación (1-4) ---")
        fallo_segmento_comms = False
        
        for segment in segments:
            seg_id = segment['id']
            u, v = segment['source'], segment['target']
            fibers = segment.get('fibers', {})
            
            # Fibras IDA
            averiadas_ida = [fn for fn in fibras_ida if fibers.get(str(fn)) == 'averiado']
            # Fibras VUELTA
            averiadas_vuelta = [fn for fn in fibras_vuelta if fibers.get(str(fn)) == 'averiado']
            # Fibras RESERVA
            reservas_ok = sorted([int(fn) for fn in fibras_reserva if fibers.get(str(fn)) == 'ok'])
            # Fibras CCTV
            cctv_averiadas = [fn for fn in fibras_cctv if fibers.get(str(fn)) == 'averiado']
            
            segment_suggestions = []
            
            if averiadas_ida or averiadas_vuelta:
                fallo_segmento_comms = True
                suggestions.append(f"\nSegmento: {seg_id} ({u}↔{v})")
                
                if averiadas_ida:
                    needed = len(averiadas_ida)
                    segment_suggestions.append(f"  - IDA ({u}→{v}) averiadas: {averiadas_ida}")
                    
                    if len(reservas_ok) >= needed:
                        sug_res = reservas_ok[:needed]
                        segment_suggestions.append(f"    -> Sugerencia: Usar {needed} reserva(s): {sug_res}")
                        reservas_ok = reservas_ok[needed:]
                    else:
                        segment_suggestions.append(f"    -> ⚠️ Reservas ({len(reservas_ok)}) insuficientes (necesita {needed}).")
                
                if averiadas_vuelta:
                    needed = len(averiadas_vuelta)
                    segment_suggestions.append(f"  - VUELTA ({v}→{u}) averiadas: {averiadas_vuelta}")
                    
                    if len(reservas_ok) >= needed:
                        sug_res = reservas_ok[:needed]
                        segment_suggestions.append(f"    -> Sugerencia: Usar {needed} reserva(s): {sug_res}")
                    else:
                        segment_suggestions.append(f"    -> ⚠️ Reservas ({len(reservas_ok)}) insuficientes (necesita {needed}).")
                
                # Si hay fibras CCTV averiadas, también mostrar sugerencias para ellas
                if cctv_averiadas:
                    segment_suggestions.append(f"  - CCTV averiadas: {cctv_averiadas}")
                    if len(reservas_ok) >= len(cctv_averiadas):
                        sug_res = reservas_ok[:len(cctv_averiadas)]
                        segment_suggestions.append(f"    -> Sugerencia: Usar {len(cctv_averiadas)} reserva(s): {sug_res} para CCTV")
                
                suggestions.extend(segment_suggestions)
        
        if not fallo_segmento_comms and aislados:
            suggestions.append("\nℹ️ No se detectaron fallos en fibras de comunicación (1-4) en los segmentos.")
            suggestions.append("   Posible causa de aislamiento: Problema en parcheo SET o fallo físico no reportado.")
        
        # Verificación Anillo Lógico en SET
        suggestions.append("\n--- Verificación Lógica del Anillo en SET ---")
        try:
            ring_status = self._check_ring_integrity()
            
            all_ok = all(ring_status.values())
            if all_ok:
                suggestions.append("✅ Anillo lógico completo: todos los circuitos correctamente parchados en SET.")
            else:
                broken_connections = [f"{key}" for key, status in ring_status.items() if not status]
                suggestions.append(f"⚠️ Anillo lógico incompleto: problemas en conexiones entre circuitos:")
                for conn in broken_connections:
                    suggestions.append(f"  - Conexión {conn} interrumpida")
        except Exception as e:
            default_logger.error(f"Error verificando integridad del anillo: {e}")
            suggestions.append(f"❌ Error al verificar integridad del anillo: {e}")
        
        suggestions.append("\nNOTA: Este diagnóstico es lógico. Siempre verificar físicamente las conexiones y equipos.")
        return suggestions
        
    def get_fiber_statistics(self, segments):
        """Calcula estadísticas sobre el estado de las fibras."""
        if not segments:
            return {
                'comm_ok': 0, 'comm_total': 0,
                'reserve_ok': 0, 'reserve_total': 0,
                'cctv_ok': 0, 'cctv_total': 0
            }
        
        # Obtener configuración de fibras para la planta activa
        plant_config = get_plant_config(self.active_plant_id)
        fibras_config = plant_config.get('fibras', {})
        
        fibras_ida = fibras_config.get('comms_ida', DEFAULT_FIBRAS_COMMS_IDA)
        fibras_vuelta = fibras_config.get('comms_vuelta', DEFAULT_FIBRAS_COMMS_VUELTA)
        fibras_reserva = fibras_config.get('reserva', DEFAULT_FIBRAS_RESERVA)
        fibras_cctv = fibras_config.get('cctv', DEFAULT_FIBRAS_CCTV)
        
        comm_fibers_range = fibras_ida + fibras_vuelta
        reserve_fibers_range = fibras_reserva
        cctv_fibers_range = fibras_cctv
        
        # Totales
        total_comm_fibers = len(segments) * len(comm_fibers_range)
        total_reserve_fibers = len(segments) * len(reserve_fibers_range)
        total_cctv_fibers = len(segments) * len(cctv_fibers_range)
        
        # Contadores OK
        comm_fibers_ok = 0
        reserve_fibers_ok = 0
        cctv_fibers_ok = 0
        
        for segment in segments:
            fibers = segment.get('fibers', {})
            
            # Contar fibras OK por tipo
            comm_fibers_ok += sum(1 for fn in comm_fibers_range if fibers.get(str(fn)) == 'ok')
            reserve_fibers_ok += sum(1 for fn in reserve_fibers_range if fibers.get(str(fn)) == 'ok')
            cctv_fibers_ok += sum(1 for fn in cctv_fibers_range if fibers.get(str(fn)) == 'ok')
        
        return {
            'comm_ok': comm_fibers_ok,
            'comm_total': total_comm_fibers,
            'reserve_ok': reserve_fibers_ok,
            'reserve_total': total_reserve_fibers,
            'cctv_ok': cctv_fibers_ok,
            'cctv_total': total_cctv_fibers
        }

    def restore_segment_fibers(self, segment_id):
        """Restaura todas las fibras de un segmento a estado 'ok'."""
        segment_found = False
        message = f"Segmento {segment_id} no encontrado"
        fibers_changed = 0
        
        with self.graph_lock:
            for u, v, data in self.G.edges(data=True):
                segment_match = (
                    data.get('id') == segment_id or 
                    f"{u}-{v}" == segment_id or 
                    f"{v}-{u}" == segment_id
                )
                
                if segment_match:
                    segment_found = True
                    
                    # Asegurar que exista el diccionario de fibras
                    if 'fibers' not in data or not isinstance(data['fibers'], dict):
                        data['fibers'] = self._get_initial_fiber_status()
                        fibers_changed = DEFAULT_TOTAL_FIBRAS
                    else:
                        # Restaurar solo las fibras averiadas
                        for fiber_key in data['fibers']:
                            if data['fibers'][fiber_key] == 'averiado':
                                data['fibers'][fiber_key] = 'ok'
                                fibers_changed += 1
                    
                    # Invalidar caché si hubo cambios
                    if fibers_changed > 0:
                        self._cache_valid = False
                        self._DG_cache = None
                    
                    message = f"{fibers_changed} fibras restauradas en segmento {segment_id}"
                    break
        
        return segment_found, message

    def save_configuration(self, name, plant_id=None):
        """Guarda la configuración actual en el almacenamiento.
        
        Args:
            name: Nombre para la configuración
            plant_id: ID de la planta (si es None, se usa la planta activa)
            
        Returns:
            tuple: (éxito, mensaje)
        """
        if not self.storage:
            return False, "No hay sistema de almacenamiento configurado"
        
        try:
            # Usar planta activa si no se especifica
            if plant_id is None:
                plant_id = self.active_plant_id
                
            # Capturar estado actual del grafo
            graph_data = self._prepare_graph_data_for_save()
            
            # Guardar en almacenamiento
            success = self.storage.save_config(name, graph_data, plant_id)
            
            if success:
                return True, f"Configuración '{name}' guardada correctamente para planta '{plant_id}'"
            else:
                return False, f"Error al guardar configuración '{name}' para planta '{plant_id}'"
        except Exception as e:
            default_logger.error(f"Error en save_configuration: {e}")
            return False, f"Error guardando configuración: {str(e)}"
    
    def _prepare_graph_data_for_save(self):
        """Prepara los datos del grafo para guardar.
        
        Returns:
            dict: Datos serializables del grafo
        """
        with self.graph_lock:
            # Extraer nodos
            nodes = []
            for node_id, data in self.G.nodes(data=True):
                node_data = {'id': node_id}
                node_data.update(data)
                nodes.append(node_data)
            
            # Extraer enlaces
            edges = []
            for u, v, data in self.G.edges(data=True):
                edge_data = {'source': u, 'target': v}
                edge_data.update(data)
                edges.append(edge_data)
            
            return {
                'nodes': nodes,
                'edges': edges,
                'node_positions': self.node_positions,
                'timestamp': datetime.now().isoformat()
            }
    
    def load_configuration(self, name, plant_id=None):
        """Carga una configuración desde el almacenamiento.
        
        Args:
            name: Nombre de la configuración a cargar
            plant_id: ID de la planta (si es None, se usa la planta activa)
            
        Returns:
            tuple: (éxito, mensaje)
        """
        if not self.storage:
            return False, "No hay sistema de almacenamiento configurado"
        
        try:
            # Usar planta activa si no se especifica
            if plant_id is None:
                plant_id = self.active_plant_id
                
            # Cargar datos desde almacenamiento
            graph_data = self.storage.load_config(name, plant_id)
            
            if not graph_data:
                return False, f"Configuración '{name}' no encontrada para planta '{plant_id}'"
            
            # Reinicializar grafo con los datos cargados
            self._init_graph(graph_data)
            
            return True, f"Configuración '{name}' cargada correctamente para planta '{plant_id}'"
        except Exception as e:
            default_logger.error(f"Error en load_configuration: {e}")
            return False, f"Error cargando configuración: {str(e)}"
    
    def list_configurations(self, plant_id=None):
        """Lista todas las configuraciones disponibles para una planta.
        
        Args:
            plant_id: ID de la planta (si es None, se usa la planta activa)
            
        Returns:
            list: Lista de diccionarios con información de configuraciones
        """
        if not self.storage:
            return []
        
        # Usar planta activa si no se especifica
        if plant_id is None:
            plant_id = self.active_plant_id
            
        return self.storage.list_configs(plant_id)

    def get_available_plants(self):
        """Obtiene la lista de plantas disponibles."""
        if not self.storage:
            return ["default"]
        
        plants = self.storage.get_plants()
        return plants
    
    def set_active_plant(self, plant_id):
        """Establece la planta activa.
        
        Args:
            plant_id: ID de la planta
            
        Returns:
            tuple: (éxito, mensaje)
        """
        if plant_id == self.active_plant_id:
            return True, f"Planta '{plant_id}' ya está activa"
            
        # Verificar si la planta existe
        available_plants = self.get_available_plants()
        
        # Si no existe y es la predefinida, crearla
        if plant_id not in available_plants:
            if plant_id == "Sabinar I":
                # Crear planta con configuración predefinida
                success, message = self.create_plant(plant_id, None)
                if not success:
                    return False, message
            else:
                return False, f"Planta '{plant_id}' no existe"
        
        # Actualizar planta activa
        self.active_plant_id = plant_id
        
        # Cargar configuración por defecto para esta planta
        default_config = None
        if self.storage is not None:
            default_config = self.storage.get_default_config(plant_id)
        
        if default_config:
            self._init_graph(default_config)
        else:
            # Si no hay configuración por defecto, inicializar con datos base (constants)
            self._init_graph()
            # Guardar como configuración estándar para futuras cargas
            if self.storage is not None:
                graph_data = self._prepare_graph_data_for_save()
                self.storage.save_config("default", graph_data, plant_id, is_default=True)
        
        return True, f"Planta '{plant_id}' activada correctamente"
    
    def create_plant(self, plant_id, base_plant_id=None):
        """Crea una nueva planta.
        
        Args:
            plant_id: ID de la planta a crear
            base_plant_id: ID de planta base para copiar datos (opcional)
            
        Returns:
            tuple: (éxito, mensaje)
        """
        if not self.storage:
            return False, "No hay sistema de almacenamiento configurado"
            
        # Verificar si ya existe
        available_plants = self.get_available_plants()
        if plant_id in available_plants:
            return False, f"La planta '{plant_id}' ya existe"
        
        # Crear planta
        success = self.storage.create_plant(plant_id)
        
        if not success:
            return False, f"Error al crear planta '{plant_id}'"
        
        # Si especificaron planta base, copiar datos
        if base_plant_id:
            # Si base es la planta predefinida, usar configuración predefinida y guardar deep copy
            if base_plant_id == "Sabinar I":
                from copy import deepcopy
                old_plant_id = self.active_plant_id
                self.active_plant_id = base_plant_id
                self._init_graph()  # Inicializar con datos predefinidos
                graph_data = deepcopy(self._prepare_graph_data_for_save())
                self.active_plant_id = plant_id
                self._init_graph(graph_data)  # Inicializar la nueva planta con la copia
                self.storage.save_config("default", graph_data, plant_id, is_default=True)
                self.active_plant_id = old_plant_id
            else:
                # Copiar configuraciones desde la planta base (base de datos)
                self.storage.copy_configurations(base_plant_id, plant_id)
        else:
            # Crear una configuración por defecto basada en constantes
            old_plant_id = self.active_plant_id
            self.active_plant_id = plant_id
            self._init_graph()  # Inicializar con datos predefinidos
            graph_data = self._prepare_graph_data_for_save()
            self.storage.save_config("default", graph_data, plant_id, is_default=True)
            self.active_plant_id = old_plant_id
        
        return True, f"Planta '{plant_id}' creada correctamente"
    
    def rename_plant(self, old_id, new_id):
        """Renombra una planta.
        
        Args:
            old_id: ID actual de la planta
            new_id: Nuevo ID para la planta
            
        Returns:
            tuple: (éxito, mensaje)
        """
        if not self.storage:
            return False, "No hay sistema de almacenamiento configurado"
            
        # Verificar que existe
        available_plants = self.get_available_plants()
        if old_id not in available_plants:
            return False, f"La planta '{old_id}' no existe"
            
        # Verificar que el nuevo nombre no existe
        if new_id in available_plants:
            return False, f"Ya existe una planta con el nombre '{new_id}'"
        
        # Renombrar
        success = self.storage.rename_plant(old_id, new_id)
        
        if not success:
            return False, f"Error al renombrar planta '{old_id}'"
            
        # Actualizar planta activa si es necesario
        if self.active_plant_id == old_id:
            self.active_plant_id = new_id
        
        return True, f"Planta '{old_id}' renombrada a '{new_id}'"
    
    def delete_plant(self, plant_id):
        """Elimina una planta.
        
        Args:
            plant_id: ID de la planta a eliminar
            
        Returns:
            tuple: (éxito, mensaje)
        """
        if not self.storage:
            return False, "No hay sistema de almacenamiento configurado"
            
        # Verificar que existe
        available_plants = self.get_available_plants()
        if plant_id not in available_plants:
            return False, f"La planta '{plant_id}' no existe"
            
        # Verificar que no es la última planta
        if len(available_plants) <= 1:
            return False, "No se puede eliminar la única planta disponible"
            
        # Eliminar
        success = self.storage.delete_plant(plant_id)
        
        if not success:
            return False, f"Error al eliminar planta '{plant_id}'"
            
        # Si era la planta activa, cambiar a otra
        if self.active_plant_id == plant_id:
            other_plant = next((p for p in available_plants if p != plant_id), None)
            if other_plant:
                self.set_active_plant(other_plant)
        
        return True, f"Planta '{plant_id}' eliminada correctamente"
    
    def export_diagnostic(self, file_path):
        """Exporta el diagnóstico actual a un archivo de texto.
        
        Args:
            file_path: Ruta del archivo donde guardar el diagnóstico
        
        Returns:
            tuple: (éxito, mensaje)
        """
        try:
            # Obtener estado actual
            status_data = self.get_network_status()
            
            # Preparar contenido del informe
            report = []
            
            # Encabezado
            report.append("========================================")
            report.append("INFORME DE DIAGNÓSTICO DE RED FIBRA ÓPTICA")
            report.append(f"Planta: {self.active_plant_id}")
            report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("========================================\n")
            
            # Estado de CTs
            report.append("ESTADO DE CONECTIVIDAD DE CTs:")
            report.append("-----------------------------")
            
            ct_statuses = status_data.get('ct_connectivity', {})
            for ct, status in sorted(ct_statuses.items()):
                report.append(f"- {ct}: {status}")
            
            # Estado de segmentos
            report.append("\nESTADO DE SEGMENTOS:")
            report.append("-------------------")
            
            segments = status_data.get('segment_statuses', [])
            for segment in segments:
                seg_id = segment.get('id', '')
                source = segment.get('source', '?')
                target = segment.get('target', '?')
                circuit = segment.get('circuit', 'N/A')
                comm_status = segment.get('comm_status', 'ok')
                
                report.append(f"\nSegmento: {seg_id} ({source}↔{target})")
                report.append(f"Circuito: {circuit}")
                report.append(f"Estado comm: {comm_status}")
                
                # Detalles de fibras
                fibers = segment.get('fibers', {})
                report.append("Fibras:")
                
                # Obtener configuración de fibras
                plant_config = get_plant_config(self.active_plant_id)
                fibras_config = plant_config.get('fibras', {})
                
                fibras_ida = fibras_config.get('comms_ida', DEFAULT_FIBRAS_COMMS_IDA)
                fibras_vuelta = fibras_config.get('comms_vuelta', DEFAULT_FIBRAS_COMMS_VUELTA)
                fibras_reserva = fibras_config.get('reserva', DEFAULT_FIBRAS_RESERVA)
                fibras_cctv = fibras_config.get('cctv', DEFAULT_FIBRAS_CCTV)
                
                for fiber_num in sorted([int(fn) for fn in fibers.keys()]):
                    status = fibers.get(str(fiber_num), 'ok')
                    fiber_type = "?"
                    
                    if fiber_num in fibras_ida:
                        fiber_type = "COMM-IDA"
                    elif fiber_num in fibras_vuelta:
                        fiber_type = "COMM-VUELTA"
                    elif fiber_num in fibras_reserva:
                        fiber_type = "RESERVA"
                    elif fiber_num in fibras_cctv:
                        fiber_type = "CCTV"
                    
                    report.append(f"  - F{fiber_num} ({fiber_type}): {status}")
            
            # Sugerencias
            report.append("\nSUGERENCIAS:")
            report.append("-----------")
            
            for suggestion in status_data.get('suggestions', ["No hay sugerencias disponibles."]):
                report.append(suggestion)
            
            # Escribir a archivo
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write('\n'.join(report))
            
            return True, f"Diagnóstico exportado a {file_path}"
        except Exception as e:
            default_logger.error(f"Error exportando diagnóstico: {e}")
            return False, f"Error exportando diagnóstico: {str(e)}"

    def save_cctv_config(self, cctv_data, plant_id=None):
        """Guarda la configuración CCTV para la planta activa o especificada."""
        if not self.storage:
            return False, "No hay sistema de almacenamiento configurado"
        if plant_id is None:
            plant_id = self.active_plant_id
        # Guardar como configuración 'cctv' (nombre fijo)
        try:
            success = self.storage.save_config("cctv", cctv_data, plant_id)
            if success:
                return True, f"Configuración CCTV guardada para planta '{plant_id}'"
            else:
                return False, f"Error al guardar configuración CCTV para planta '{plant_id}'"
        except Exception as e:
            return False, f"Error guardando configuración CCTV: {e}"

    def load_cctv_config(self, plant_id=None):
        """Carga la configuración CCTV para la planta activa o especificada."""
        if not self.storage:
            return {}
        if plant_id is None:
            plant_id = self.active_plant_id
        try:
            cctv_data = self.storage.load_config("cctv", plant_id)
            if cctv_data is not None:
                return cctv_data
            # Si no hay config guardada, usar la de constantes
            from constants import get_cctv_config
            return get_cctv_config(plant_id)
        except Exception:
            from constants import get_cctv_config
            return get_cctv_config(plant_id)