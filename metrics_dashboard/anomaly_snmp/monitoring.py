"""
AnomalySNMP Monitoring and Performance Tracking

Sistema di monitoraggio per tracciare performance, utilizzo risorse e metriche
operative del componente AnomalySNMP.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
import json

from .logging_config import get_logger, log_performance_metric


@dataclass
class PerformanceMetric:
    """Struttura per una metrica di performance"""
    timestamp: datetime
    operation: str
    duration: float
    memory_usage_mb: float
    cpu_percent: float
    session_id: str = None
    contamination: float = None
    train_split: float = None
    additional_data: Dict[str, Any] = None


@dataclass
class SystemMetric:
    """Struttura per metriche di sistema"""
    timestamp: datetime
    memory_total_mb: float
    memory_available_mb: float
    memory_percent: float
    cpu_percent: float
    disk_usage_percent: float


class PerformanceMonitor:
    """
    Monitor per tracciare performance e utilizzo risorse
    """
    
    def __init__(self, max_metrics: int = 1000):
        """
        Inizializza il monitor di performance
        
        Args:
            max_metrics: Numero massimo di metriche da mantenere in memoria
        """
        self.logger = get_logger('anomaly_snmp.performance')
        self.max_metrics = max_metrics
        
        # Storage per metriche
        self.performance_metrics: deque = deque(maxlen=max_metrics)
        self.system_metrics: deque = deque(maxlen=max_metrics)
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        
        # Configurazione soglie
        self.slow_operation_threshold = 2.0  # secondi
        self.memory_warning_threshold = 80.0  # percentuale
        self.cpu_warning_threshold = 80.0  # percentuale
        
        # Thread per monitoraggio sistema
        self._monitoring_active = False
        self._monitoring_thread = None
        self._lock = threading.Lock()
    
    def start_system_monitoring(self, interval: float = 30.0):
        """
        Avvia il monitoraggio continuo del sistema
        
        Args:
            interval: Intervallo in secondi tra le rilevazioni
        """
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._system_monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info(f"Monitoraggio sistema avviato (intervallo: {interval}s)")
    
    def stop_system_monitoring(self):
        """Ferma il monitoraggio del sistema"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        
        self.logger.info("Monitoraggio sistema fermato")
    
    def _system_monitoring_loop(self, interval: float):
        """Loop principale per monitoraggio sistema"""
        while self._monitoring_active:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Errore nel monitoraggio sistema: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """Raccoglie metriche di sistema"""
        try:
            # Metriche memoria
            memory = psutil.virtual_memory()
            
            # Metriche CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Metriche disco
            disk = psutil.disk_usage('/')
            
            metric = SystemMetric(
                timestamp=datetime.now(),
                memory_total_mb=memory.total / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                memory_percent=memory.percent,
                cpu_percent=cpu_percent,
                disk_usage_percent=disk.percent
            )
            
            with self._lock:
                self.system_metrics.append(metric)
            
            # Log warning se soglie superate
            if memory.percent > self.memory_warning_threshold:
                self.logger.warning(
                    f"Utilizzo memoria alto: {memory.percent:.1f}%",
                    extra={'memory_percent': memory.percent, 'operation': 'system_monitoring'}
                )
            
            if cpu_percent > self.cpu_warning_threshold:
                self.logger.warning(
                    f"Utilizzo CPU alto: {cpu_percent:.1f}%",
                    extra={'cpu_percent': cpu_percent, 'operation': 'system_monitoring'}
                )
                
        except Exception as e:
            self.logger.error(f"Errore raccolta metriche sistema: {e}")
    
    def record_operation(self, operation: str, duration: float, 
                        session_id: str = None, contamination: float = None,
                        train_split: float = None, **additional_data):
        """
        Registra una metrica di performance per un'operazione
        
        Args:
            operation: Nome dell'operazione
            duration: Durata in secondi
            session_id: ID della sessione
            contamination: Parametro di contaminazione
            train_split: Parametro di split training
            **additional_data: Dati aggiuntivi
        """
        try:
            # Raccoglie metriche correnti
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation=operation,
                duration=duration,
                memory_usage_mb=memory.used / (1024 * 1024),
                cpu_percent=cpu_percent,
                session_id=session_id,
                contamination=contamination,
                train_split=train_split,
                additional_data=additional_data
            )
            
            with self._lock:
                self.performance_metrics.append(metric)
                self.operation_stats[operation].append(duration)
                
                # Mantieni solo le ultime N metriche per operazione
                if len(self.operation_stats[operation]) > 100:
                    self.operation_stats[operation] = self.operation_stats[operation][-100:]
            
            # Log della metrica
            log_performance_metric(
                self.logger, operation, duration, 
                threshold=self.slow_operation_threshold,
                session_id=session_id,
                contamination=contamination,
                train_split=train_split,
                memory_usage_mb=metric.memory_usage_mb,
                cpu_percent=cpu_percent
            )
            
            # Log warning per operazioni lente
            if duration > self.slow_operation_threshold:
                self.logger.warning(
                    f"Operazione lenta rilevata: {operation} ({duration:.3f}s)",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'threshold': self.slow_operation_threshold,
                        'session_id': session_id
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Errore registrazione metrica: {e}")
    
    def get_operation_stats(self, operation: str) -> Dict[str, float]:
        """
        Ottiene statistiche per un'operazione specifica
        
        Args:
            operation: Nome dell'operazione
            
        Returns:
            Dict con statistiche (avg, min, max, count)
        """
        with self._lock:
            durations = self.operation_stats.get(operation, [])
        
        if not durations:
            return {'count': 0}
        
        return {
            'count': len(durations),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations)
        }
    
    def get_recent_metrics(self, minutes: int = 60) -> List[PerformanceMetric]:
        """
        Ottiene metriche recenti
        
        Args:
            minutes: Minuti di storia da recuperare
            
        Returns:
            Lista di metriche recenti
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_metrics = [
                metric for metric in self.performance_metrics
                if metric.timestamp >= cutoff_time
            ]
        
        return recent_metrics
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Ottiene un report dello stato di salute del sistema
        
        Returns:
            Dict con informazioni di salute del sistema
        """
        try:
            # Metriche correnti
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            disk = psutil.disk_usage('/')
            
            # Statistiche operazioni
            operation_summary = {}
            with self._lock:
                for op, durations in self.operation_stats.items():
                    if durations:
                        operation_summary[op] = {
                            'count': len(durations),
                            'avg_duration': sum(durations) / len(durations),
                            'slow_operations': len([d for d in durations if d > self.slow_operation_threshold])
                        }
            
            # Metriche recenti (ultima ora)
            recent_metrics = self.get_recent_metrics(60)
            
            health_status = "healthy"
            warnings = []
            
            # Controlli di salute
            if memory.percent > self.memory_warning_threshold:
                health_status = "warning"
                warnings.append(f"Memoria alta: {memory.percent:.1f}%")
            
            if cpu_percent > self.cpu_warning_threshold:
                health_status = "warning"
                warnings.append(f"CPU alta: {cpu_percent:.1f}%")
            
            if disk.percent > 90:
                health_status = "warning"
                warnings.append(f"Disco pieno: {disk.percent:.1f}%")
            
            # Conta operazioni lente recenti
            slow_ops_recent = len([m for m in recent_metrics if m.duration > self.slow_operation_threshold])
            if slow_ops_recent > 5:
                health_status = "warning"
                warnings.append(f"Molte operazioni lente recenti: {slow_ops_recent}")
            
            return {
                'status': health_status,
                'timestamp': datetime.now().isoformat(),
                'warnings': warnings,
                'system': {
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk.percent
                },
                'operations': operation_summary,
                'recent_activity': {
                    'total_operations_last_hour': len(recent_metrics),
                    'slow_operations_last_hour': slow_ops_recent,
                    'avg_duration_last_hour': sum(m.duration for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo system health: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def export_metrics(self, filepath: str, format: str = 'json'):
        """
        Esporta le metriche su file
        
        Args:
            filepath: Percorso del file di output
            format: Formato di export ('json' o 'csv')
        """
        try:
            with self._lock:
                metrics_data = [asdict(metric) for metric in self.performance_metrics]
                system_data = [asdict(metric) for metric in self.system_metrics]
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'performance_metrics': metrics_data,
                'system_metrics': system_data,
                'operation_stats': dict(self.operation_stats)
            }
            
            if format.lower() == 'json':
                with open(filepath, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                raise ValueError(f"Formato non supportato: {format}")
            
            self.logger.info(f"Metriche esportate in {filepath}")
            
        except Exception as e:
            self.logger.error(f"Errore export metriche: {e}")
            raise


# Istanza globale del monitor
performance_monitor = PerformanceMonitor()


def monitor_operation(operation: str = None):
    """
    Decorator per monitoraggio automatico delle operazioni
    
    Args:
        operation: Nome dell'operazione (default: nome funzione)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Estrai contesto se disponibile
                session_id = kwargs.get('session_id')
                contamination = kwargs.get('contamination')
                train_split = kwargs.get('train_split')
                
                performance_monitor.record_operation(
                    op_name, duration, session_id, contamination, train_split
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.record_operation(
                    op_name, duration, 
                    additional_data={'error': str(e), 'success': False}
                )
                raise
        
        return wrapper
    return decorator


def get_performance_summary() -> Dict[str, Any]:
    """
    Ottiene un riassunto delle performance del sistema
    
    Returns:
        Dict con riassunto performance
    """
    return performance_monitor.get_system_health()


def start_monitoring():
    """Avvia il monitoraggio del sistema"""
    performance_monitor.start_system_monitoring()


def stop_monitoring():
    """Ferma il monitoraggio del sistema"""
    performance_monitor.stop_system_monitoring()