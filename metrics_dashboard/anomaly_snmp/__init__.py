"""
AnomalySNMP Package Initialization

Inizializza il sistema di logging e monitoraggio per il componente AnomalySNMP
"""

import logging
from flask import Flask

# Import delle classi principali per facilitare l'uso
try:
    from .utils.data_processor import SNMPDataProcessor
    from .utils.ml_engine import AnomalyDetectionModel
except ImportError:
    # Fallback se i moduli non sono ancora disponibili
    SNMPDataProcessor = None
    AnomalyDetectionModel = None

# Import del sistema di logging e monitoraggio
try:
    from .logging_config import setup_anomaly_snmp_logging, get_logger
    from .monitoring import performance_monitor, start_monitoring
    from .exceptions import AnomalySNMPError
except ImportError:
    # Fallback al logging standard
    def get_logger(name):
        return logging.getLogger(name)
    
    def setup_anomaly_snmp_logging(app=None, log_level='INFO'):
        return {}
    
    class AnomalySNMPError(Exception):
        pass

# Logger per il package
logger = get_logger('anomaly_snmp')

def init_anomaly_snmp(app: Flask = None, log_level: str = 'INFO') -> dict:
    """
    Inizializza il componente AnomalySNMP con logging e monitoraggio
    
    Args:
        app: Istanza Flask (opzionale)
        log_level: Livello di logging
        
    Returns:
        Dict con i logger configurati
    """
    try:
        # Setup logging
        loggers = setup_anomaly_snmp_logging(app, log_level)
        
        # Avvia monitoraggio se in produzione
        if app and not app.config.get('DEBUG', False):
            try:
                start_monitoring()
                logger.info("Monitoraggio performance avviato")
            except Exception as e:
                logger.warning(f"Impossibile avviare monitoraggio: {e}")
        
        # Log inizializzazione
        logger.info("Componente AnomalySNMP inizializzato con successo")
        logger.info(f"Livello logging: {log_level}")
        
        return loggers
        
    except Exception as e:
        # Fallback al logging standard se l'inizializzazione fallisce
        logging.error(f"Errore inizializzazione AnomalySNMP: {e}")
        return {}

def get_component_status() -> dict:
    """
    Ottiene lo stato del componente AnomalySNMP
    
    Returns:
        Dict con informazioni di stato
    """
    try:
        from .monitoring import get_performance_summary
        return {
            'component': 'AnomalySNMP',
            'status': 'active',
            'performance': get_performance_summary()
        }
    except Exception as e:
        return {
            'component': 'AnomalySNMP',
            'status': 'error',
            'error': str(e)
        }

# Configurazione logging legacy per compatibilità
def setup_logging():
    """Configura il logging per il componente AnomalySNMP (legacy)"""
    return get_logger('anomaly_snmp')

# Inizializza il logging
setup_logging()

# Esporta le classi principali
__all__ = [
    'SNMPDataProcessor',
    'AnomalyDetectionModel', 
    'AnomalySNMPError',
    'init_anomaly_snmp',
    'get_component_status',
    'get_logger',
    'setup_logging'  # Per compatibilità
]