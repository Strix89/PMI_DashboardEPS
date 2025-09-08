"""
AnomalySNMP Logging Configuration

Sistema di logging specializzato per il componente AnomalySNMP che integra
con il sistema di logging esistente dell'applicazione PMI Dashboard.
"""

import os
import logging
import logging.handlers
import time
import functools
from datetime import datetime, UTC
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager

# Import del sistema di logging esistente
try:
    from ..logging_config import setup_logging as pmi_setup_logging
except ImportError:
    # Fallback se il modulo principale non è disponibile
    pmi_setup_logging = None


class AnomalySNMPFormatter(logging.Formatter):
    """
    Formatter personalizzato per i log di AnomalySNMP
    
    Aggiunge informazioni specifiche del componente e formattazione consistente
    con il resto dell'applicazione.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatta il record di log con informazioni specifiche di AnomalySNMP
        
        Args:
            record: Record di log da formattare
            
        Returns:
            Stringa formattata del log
        """
        # Aggiungi timestamp ISO
        record.iso_timestamp = datetime.now(UTC).isoformat() + 'Z'
        
        # Aggiungi identificativo componente
        record.component = 'AnomalySNMP'
        
        # Aggiungi informazioni di contesto se disponibili
        if not hasattr(record, 'operation'):
            record.operation = 'N/A'
        if not hasattr(record, 'session_id'):
            record.session_id = 'N/A'
        if not hasattr(record, 'contamination'):
            record.contamination = 'N/A'
        if not hasattr(record, 'train_split'):
            record.train_split = 'N/A'
        
        return super().format(record)


class PerformanceFilter(logging.Filter):
    """
    Filtro per identificare operazioni lente e aggiungere metriche di performance
    """
    
    def __init__(self, slow_threshold: float = 2.0):
        """
        Inizializza il filtro di performance
        
        Args:
            slow_threshold: Soglia in secondi per considerare un'operazione lenta
        """
        super().__init__()
        self.slow_threshold = slow_threshold
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filtra e arricchisce i record con informazioni di performance
        
        Args:
            record: Record di log da filtrare
            
        Returns:
            True se il record deve essere processato
        """
        # Aggiungi flag per operazioni lente
        if hasattr(record, 'duration') and record.duration > self.slow_threshold:
            record.is_slow_operation = True
            record.performance_warning = f"Operazione lenta: {record.duration:.3f}s"
        else:
            record.is_slow_operation = False
            record.performance_warning = ''
        
        return True


class ErrorContextFilter(logging.Filter):
    """
    Filtro per aggiungere contesto agli errori
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Aggiunge contesto di errore ai record
        
        Args:
            record: Record di log da arricchire
            
        Returns:
            True se il record deve essere processato
        """
        # Aggiungi informazioni di default per gli errori
        if record.levelno >= logging.ERROR:
            if not hasattr(record, 'error_context'):
                record.error_context = 'General error'
            if not hasattr(record, 'recovery_suggestion'):
                record.recovery_suggestion = 'Verificare i parametri e riprovare'
        
        return True


def setup_anomaly_snmp_logging(app=None, log_level: str = 'INFO') -> Dict[str, logging.Logger]:
    """
    Configura il sistema di logging per AnomalySNMP
    
    Args:
        app: Istanza Flask (opzionale)
        log_level: Livello di logging
        
    Returns:
        Dict con i logger configurati
    """
    # Converti il livello di logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Crea directory per i log se non esiste
    if app:
        log_dir = os.path.join(os.path.dirname(app.instance_path), 'logs', 'anomaly_snmp')
    else:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', 'anomaly_snmp')
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurazione formatter
    detailed_formatter = AnomalySNMPFormatter(
        '%(iso_timestamp)s [%(levelname)s] %(component)s [%(filename)s:%(lineno)d] '
        '%(funcName)s() [Op:%(operation)s] [Session:%(session_id)s]: %(message)s'
    )
    
    error_formatter = AnomalySNMPFormatter(
        '%(iso_timestamp)s [%(levelname)s] %(component)s ERROR\n'
        'File: %(filename)s:%(lineno)d\n'
        'Function: %(funcName)s()\n'
        'Operation: %(operation)s\n'
        'Session: %(session_id)s\n'
        'Message: %(message)s\n'
        'Context: %(error_context)s\n'
        'Recovery: %(recovery_suggestion)s\n'
        'Performance: %(performance_warning)s\n'
        '---'
    )
    
    performance_formatter = AnomalySNMPFormatter(
        '%(iso_timestamp)s [PERF] %(component)s: %(message)s '
        '[Duration: %(duration).3fs] [Operation: %(operation)s]'
    )
    
    # Crea filtri
    perf_filter = PerformanceFilter(slow_threshold=2.0)
    error_filter = ErrorContextFilter()
    
    # Logger principale per AnomalySNMP
    main_logger = logging.getLogger('anomaly_snmp')
    main_logger.setLevel(numeric_level)
    main_logger.handlers.clear()
    
    # Handler per log generale
    main_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'anomaly_snmp.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setFormatter(detailed_formatter)
    main_handler.addFilter(perf_filter)
    main_logger.addHandler(main_handler)
    
    # Logger per errori
    error_logger = logging.getLogger('anomaly_snmp.errors')
    error_logger.setLevel(logging.WARNING)
    error_logger.handlers.clear()
    
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    error_handler.setFormatter(error_formatter)
    error_handler.addFilter(error_filter)
    error_logger.addHandler(error_handler)
    
    # Logger per performance
    perf_logger = logging.getLogger('anomaly_snmp.performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.handlers.clear()
    
    perf_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'performance.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    perf_handler.setFormatter(performance_formatter)
    perf_handler.addFilter(perf_filter)
    perf_logger.addHandler(perf_handler)
    
    # Logger per data processing
    data_logger = logging.getLogger('anomaly_snmp.data_processing')
    data_logger.setLevel(numeric_level)
    data_logger.handlers.clear()
    
    data_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'data_processing.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    data_handler.setFormatter(detailed_formatter)
    data_logger.addHandler(data_handler)
    
    # Logger per ML operations
    ml_logger = logging.getLogger('anomaly_snmp.ml_engine')
    ml_logger.setLevel(numeric_level)
    ml_logger.handlers.clear()
    
    ml_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'ml_operations.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    ml_handler.setFormatter(detailed_formatter)
    ml_logger.addHandler(ml_handler)
    
    # Logger per simulazione
    simulation_logger = logging.getLogger('anomaly_snmp.simulation')
    simulation_logger.setLevel(numeric_level)
    simulation_logger.handlers.clear()
    
    simulation_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'simulation.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    simulation_handler.setFormatter(detailed_formatter)
    simulation_logger.addHandler(simulation_handler)
    
    # Console handler per development
    if app and app.config.get('DEBUG'):
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] AnomalySNMP: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Aggiungi console handler a tutti i logger
        for logger in [main_logger, error_logger, perf_logger, data_logger, ml_logger, simulation_logger]:
            logger.addHandler(console_handler)
    
    # Log di inizializzazione
    main_logger.info("Sistema di logging AnomalySNMP inizializzato", extra={
        'operation': 'logging_init',
        'session_id': 'system',
        'contamination': 'N/A',
        'train_split': 'N/A'
    })
    main_logger.info(f"Livello di logging: {log_level}")
    main_logger.info(f"Directory log: {log_dir}")
    
    return {
        'main': main_logger,
        'error': error_logger,
        'performance': perf_logger,
        'data_processing': data_logger,
        'ml_engine': ml_logger,
        'simulation': simulation_logger
    }


def get_logger(name: str = 'anomaly_snmp') -> logging.Logger:
    """
    Ottiene un logger configurato per AnomalySNMP
    
    Args:
        name: Nome del logger
        
    Returns:
        Logger configurato
    """
    return logging.getLogger(name)


def log_operation_start(logger: logging.Logger, operation: str, **context) -> None:
    """
    Log dell'inizio di un'operazione
    
    Args:
        logger: Logger instance
        operation: Nome dell'operazione
        **context: Contesto aggiuntivo
    """
    extra = {
        'operation': operation,
        'session_id': context.get('session_id', 'N/A'),
        'contamination': context.get('contamination', 'N/A'),
        'train_split': context.get('train_split', 'N/A'),
        **context
    }
    
    logger.info(f"Inizio operazione: {operation}", extra=extra)


def log_operation_success(logger: logging.Logger, operation: str, duration: float = None, **context) -> None:
    """
    Log del successo di un'operazione
    
    Args:
        logger: Logger instance
        operation: Nome dell'operazione
        duration: Durata in secondi
        **context: Contesto aggiuntivo
    """
    extra = {
        'operation': operation,
        'session_id': context.get('session_id', 'N/A'),
        'contamination': context.get('contamination', 'N/A'),
        'train_split': context.get('train_split', 'N/A'),
        **context
    }
    
    if duration is not None:
        extra['duration'] = duration
        message = f"Operazione completata: {operation} ({duration:.3f}s)"
    else:
        message = f"Operazione completata: {operation}"
    
    logger.info(message, extra=extra)


def log_operation_error(logger: logging.Logger, operation: str, error: Exception, 
                       duration: float = None, **context) -> None:
    """
    Log di errore durante un'operazione
    
    Args:
        logger: Logger instance
        operation: Nome dell'operazione
        error: Eccezione verificatasi
        duration: Durata prima dell'errore
        **context: Contesto aggiuntivo
    """
    extra = {
        'operation': operation,
        'session_id': context.get('session_id', 'N/A'),
        'contamination': context.get('contamination', 'N/A'),
        'train_split': context.get('train_split', 'N/A'),
        'error_context': f"Errore durante {operation}",
        'recovery_suggestion': context.get('recovery_suggestion', 'Verificare i parametri e riprovare'),
        **context
    }
    
    if duration is not None:
        extra['duration'] = duration
    
    logger.error(f"Operazione fallita: {operation} - {str(error)}", extra=extra, exc_info=True)


def log_performance_metric(logger: logging.Logger, operation: str, duration: float, 
                          threshold: float = 2.0, **context) -> None:
    """
    Log di metriche di performance
    
    Args:
        logger: Logger instance
        operation: Nome dell'operazione
        duration: Durata in secondi
        threshold: Soglia per considerare l'operazione lenta
        **context: Contesto aggiuntivo
    """
    extra = {
        'operation': operation,
        'duration': duration,
        'session_id': context.get('session_id', 'N/A'),
        'contamination': context.get('contamination', 'N/A'),
        'train_split': context.get('train_split', 'N/A'),
        **context
    }
    
    level = logging.WARNING if duration > threshold else logging.INFO
    message = f"Performance: {operation} - {duration:.3f}s"
    
    if duration > threshold:
        message += f" (LENTO - soglia: {threshold}s)"
    
    logger.log(level, message, extra=extra)


@contextmanager
def operation_context(logger: logging.Logger, operation: str, **context):
    """
    Context manager per logging automatico di operazioni
    
    Args:
        logger: Logger instance
        operation: Nome dell'operazione
        **context: Contesto aggiuntivo
        
    Yields:
        Dict con informazioni di contesto aggiornabili
    """
    start_time = time.time()
    operation_context_dict = dict(context)
    
    try:
        log_operation_start(logger, operation, **operation_context_dict)
        yield operation_context_dict
        
        duration = time.time() - start_time
        log_operation_success(logger, operation, duration, **operation_context_dict)
        
        # Log performance se necessario
        perf_logger = get_logger('anomaly_snmp.performance')
        log_performance_metric(perf_logger, operation, duration, **operation_context_dict)
        
    except Exception as e:
        duration = time.time() - start_time
        log_operation_error(logger, operation, e, duration, **operation_context_dict)
        raise


def performance_monitor(operation: str = None, threshold: float = 2.0):
    """
    Decorator per monitoraggio automatico delle performance
    
    Args:
        operation: Nome dell'operazione (default: nome della funzione)
        threshold: Soglia per operazioni lente
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            logger = get_logger('anomaly_snmp.performance')
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                log_performance_metric(logger, op_name, duration, threshold)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                log_operation_error(logger, op_name, e, duration)
                raise
        
        return wrapper
    return decorator


def error_handler(operation: str = None, recovery_suggestion: str = None):
    """
    Decorator per gestione automatica degli errori
    
    Args:
        operation: Nome dell'operazione
        recovery_suggestion: Suggerimento per il recovery
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            logger = get_logger('anomaly_snmp.errors')
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'recovery_suggestion': recovery_suggestion or 'Verificare i parametri e riprovare'
                }
                log_operation_error(logger, op_name, e, **context)
                raise
        
        return wrapper
    return decorator


class LoggingMixin:
    """
    Mixin class per aggiungere capacità di logging alle classi
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = get_logger(f'anomaly_snmp.{self.__class__.__name__.lower()}')
        self._session_context = {}
    
    def set_session_context(self, session_id: str = None, contamination: float = None, 
                           train_split: float = None, **kwargs):
        """
        Imposta il contesto di sessione per il logging
        
        Args:
            session_id: ID della sessione
            contamination: Parametro di contaminazione
            train_split: Parametro di split training
            **kwargs: Altri parametri di contesto
        """
        self._session_context.update({
            'session_id': session_id or 'N/A',
            'contamination': contamination or 'N/A',
            'train_split': train_split or 'N/A',
            **kwargs
        })
    
    def log_info(self, message: str, operation: str = None, **extra):
        """Log di informazione con contesto"""
        context = {**self._session_context, 'operation': operation or 'general', **extra}
        self._logger.info(message, extra=context)
    
    def log_warning(self, message: str, operation: str = None, **extra):
        """Log di warning con contesto"""
        context = {**self._session_context, 'operation': operation or 'general', **extra}
        self._logger.warning(message, extra=context)
    
    def log_error(self, message: str, operation: str = None, error: Exception = None, **extra):
        """Log di errore con contesto"""
        context = {
            **self._session_context, 
            'operation': operation or 'general',
            'error_context': f"Errore in {self.__class__.__name__}",
            **extra
        }
        self._logger.error(message, extra=context, exc_info=error is not None)
    
    def log_performance(self, operation: str, duration: float, **extra):
        """Log di performance con contesto"""
        perf_logger = get_logger('anomaly_snmp.performance')
        context = {**self._session_context, **extra}
        log_performance_metric(perf_logger, operation, duration, **context)