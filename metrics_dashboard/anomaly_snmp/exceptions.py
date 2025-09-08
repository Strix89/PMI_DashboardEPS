"""
AnomalySNMP Custom Exceptions

Definisce eccezioni personalizzate per il componente AnomalySNMP per una gestione
degli errori più granulare e messaggi utente più informativi.
"""

class AnomalySNMPError(Exception):
    """Eccezione base per tutti gli errori del componente AnomalySNMP"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """
        Inizializza l'eccezione base
        
        Args:
            message: Messaggio di errore user-friendly
            error_code: Codice errore per identificazione programmatica
            details: Dettagli aggiuntivi per debug
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'ANOMALY_SNMP_GENERIC'
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Converte l'eccezione in dizionario per API response"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class DatasetError(AnomalySNMPError):
    """Errori relativi al caricamento e validazione del dataset"""
    
    def __init__(self, message: str, dataset_path: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if dataset_path:
            self.details['dataset_path'] = dataset_path


class DatasetNotFoundError(DatasetError):
    """Dataset non trovato"""
    
    def __init__(self, dataset_path: str):
        message = f"Dataset non trovato: {dataset_path}"
        # Chiama direttamente AnomalySNMPError per evitare il doppio error_code
        AnomalySNMPError.__init__(self, message, error_code='DATASET_NOT_FOUND')
        if dataset_path:
            self.details['dataset_path'] = dataset_path


class DatasetValidationError(DatasetError):
    """Errore di validazione struttura dataset"""
    
    def __init__(self, message: str, validation_details: dict = None, **kwargs):
        kwargs.pop('error_code', None)
        super().__init__(message, **kwargs)
        self.error_code = 'DATASET_VALIDATION_ERROR'
        if validation_details:
            self.details.update(validation_details)


class DatasetCorruptedError(DatasetError):
    """Dataset corrotto o formato non valido"""
    
    def __init__(self, message: str, corruption_details: dict = None, **kwargs):
        kwargs.pop('error_code', None)
        super().__init__(message, **kwargs)
        self.error_code = 'DATASET_CORRUPTED'
        if corruption_details:
            self.details.update(corruption_details)


class DataProcessingError(AnomalySNMPError):
    """Errori durante il preprocessing dei dati"""
    
    def __init__(self, message: str, processing_stage: str = None, **kwargs):
        kwargs.pop('error_code', None)
        super().__init__(message, **kwargs)
        self.error_code = 'DATA_PROCESSING_ERROR'
        if processing_stage:
            self.details['processing_stage'] = processing_stage


class NormalizationError(DataProcessingError):
    """Errore durante la normalizzazione delle feature"""
    
    def __init__(self, message: str, feature_info: dict = None, **kwargs):
        kwargs.pop('error_code', None)
        super().__init__(message=message, processing_stage='normalization', **kwargs)
        self.error_code = 'NORMALIZATION_ERROR'
        if feature_info:
            self.details.update(feature_info)


class SMOTEError(DataProcessingError):
    """Errore durante l'oversampling con SMOTE"""
    
    def __init__(self, message: str, smote_params: dict = None, **kwargs):
        kwargs.pop('error_code', None)
        super().__init__(message=message, processing_stage='smote_oversampling', **kwargs)
        self.error_code = 'SMOTE_ERROR'
        if smote_params:
            self.details.update(smote_params)


class ModelTrainingError(AnomalySNMPError):
    """Errori durante il training del modello"""
    
    def __init__(self, message: str, model_params: dict = None, **kwargs):
        kwargs.pop('error_code', None)
        super().__init__(message, **kwargs)
        self.error_code = 'MODEL_TRAINING_ERROR'
        if model_params:
            self.details['model_params'] = model_params


class ModelNotTrainedError(ModelTrainingError):
    """Modello non addestrato quando richiesto"""
    
    def __init__(self, operation: str = None):
        message = f"Modello non addestrato. Operazione richiesta: {operation or 'sconosciuta'}"
        super().__init__(
            message=message,
            error_code='MODEL_NOT_TRAINED'
        )
        if operation:
            self.details['requested_operation'] = operation


class BaselineCalculationError(AnomalySNMPError):
    """Errore nel calcolo della baseline statistica"""
    
    def __init__(self, message: str, baseline_data: dict = None, **kwargs):
        super().__init__(message, error_code='BASELINE_CALCULATION_ERROR', **kwargs)
        if baseline_data:
            self.details.update(baseline_data)


class ScoreCalculationError(AnomalySNMPError):
    """Errore nel calcolo dell'S_score"""
    
    def __init__(self, message: str, score_data: dict = None, **kwargs):
        super().__init__(message, error_code='SCORE_CALCULATION_ERROR', **kwargs)
        if score_data:
            self.details.update(score_data)


class SessionError(AnomalySNMPError):
    """Errori relativi alla gestione della sessione Flask"""
    
    def __init__(self, message: str, session_info: dict = None, **kwargs):
        super().__init__(message, error_code='SESSION_ERROR', **kwargs)
        if session_info:
            self.details.update(session_info)


class SessionNotFoundError(SessionError):
    """Sessione AnomalySNMP non trovata"""
    
    def __init__(self, required_component: str = None):
        message = "Sessione AnomalySNMP non trovata. Configurare prima il modello."
        # Chiama direttamente AnomalySNMPError per evitare il doppio error_code
        AnomalySNMPError.__init__(self, message, error_code='SESSION_NOT_FOUND')
        if required_component:
            self.details['required_component'] = required_component


class SessionCorruptedError(SessionError):
    """Dati di sessione corrotti o incompleti"""
    
    def __init__(self, message: str, missing_components: list = None, **kwargs):
        # Rimuovi error_code dai kwargs se presente per evitare conflitti
        kwargs.pop('error_code', None)
        # Chiama direttamente AnomalySNMPError per evitare il doppio error_code
        AnomalySNMPError.__init__(self, message, error_code='SESSION_CORRUPTED', **kwargs)
        if missing_components:
            self.details['missing_components'] = missing_components


class SimulationError(AnomalySNMPError):
    """Errori durante la simulazione tempo reale"""
    
    def __init__(self, message: str, simulation_state: dict = None, **kwargs):
        super().__init__(message, error_code='SIMULATION_ERROR', **kwargs)
        if simulation_state:
            self.details.update(simulation_state)


class SimulationDataExhaustedError(SimulationError):
    """Fine dei dati di simulazione raggiunta"""
    
    def __init__(self, current_offset: int, max_offset: int):
        message = f"Fine del dataset raggiunta. Offset corrente: {current_offset}, massimo: {max_offset}"
        super().__init__(
            message=message,
            error_code='SIMULATION_DATA_EXHAUSTED'
        )
        self.details.update({
            'current_offset': current_offset,
            'max_offset': max_offset
        })


class ConfigurationError(AnomalySNMPError):
    """Errori di configurazione parametri"""
    
    def __init__(self, message: str, invalid_params: dict = None, **kwargs):
        super().__init__(message, error_code='CONFIGURATION_ERROR', **kwargs)
        if invalid_params:
            self.details['invalid_params'] = invalid_params


class ParameterValidationError(ConfigurationError):
    """Errore di validazione parametri"""
    
    def __init__(self, parameter: str, value, valid_range: tuple = None, **kwargs):
        if valid_range:
            message = f"Parametro '{parameter}' non valido: {value}. Range valido: {valid_range}"
        else:
            message = f"Parametro '{parameter}' non valido: {value}"
        
        super().__init__(
            message=message,
            error_code='PARAMETER_VALIDATION_ERROR',
            **kwargs
        )
        self.details.update({
            'parameter': parameter,
            'provided_value': value,
            'valid_range': valid_range
        })


class MemoryError(AnomalySNMPError):
    """Errori di memoria durante operazioni intensive"""
    
    def __init__(self, message: str, operation: str = None, memory_info: dict = None, **kwargs):
        super().__init__(message, error_code='MEMORY_ERROR', **kwargs)
        if operation:
            self.details['operation'] = operation
        if memory_info:
            self.details.update(memory_info)


class PerformanceError(AnomalySNMPError):
    """Errori di performance (operazioni troppo lente)"""
    
    def __init__(self, message: str, operation: str = None, duration: float = None, **kwargs):
        super().__init__(message, error_code='PERFORMANCE_ERROR', **kwargs)
        if operation:
            self.details['operation'] = operation
        if duration:
            self.details['duration_seconds'] = duration


# Utility functions per gestione errori

def handle_exception(logger, exception: Exception, context: dict = None) -> dict:
    """
    Gestisce un'eccezione e restituisce una response standardizzata
    
    Args:
        logger: Logger instance
        exception: Eccezione da gestire
        context: Contesto aggiuntivo per il logging
        
    Returns:
        dict: Response standardizzata per API
    """
    context = context or {}
    
    if isinstance(exception, AnomalySNMPError):
        # Eccezione personalizzata - usa i dettagli strutturati
        logger.error(
            f"AnomalySNMP Error: {exception.message}",
            extra={
                'error_code': exception.error_code,
                'error_details': exception.details,
                **context
            }
        )
        
        return {
            'success': False,
            'error': exception.to_dict()
        }
    else:
        # Eccezione generica - wrappa in AnomalySNMPError
        logger.error(
            f"Unexpected error: {str(exception)}",
            extra={
                'exception_type': type(exception).__name__,
                **context
            },
            exc_info=True
        )
        
        wrapped_error = AnomalySNMPError(
            message="Errore interno del sistema",
            error_code='INTERNAL_ERROR',
            details={
                'original_exception': type(exception).__name__,
                'original_message': str(exception)
            }
        )
        
        return {
            'success': False,
            'error': wrapped_error.to_dict()
        }


def validate_parameters(params: dict, validation_rules: dict) -> None:
    """
    Valida parametri secondo regole specificate
    
    Args:
        params: Parametri da validare
        validation_rules: Regole di validazione
        
    Raises:
        ParameterValidationError: Se la validazione fallisce
    """
    for param_name, rules in validation_rules.items():
        if param_name not in params:
            if rules.get('required', False):
                raise ParameterValidationError(
                    parameter=param_name,
                    value=None,
                    details={'error': 'Parametro richiesto mancante'}
                )
            continue
        
        value = params[param_name]
        
        # Validazione tipo
        if 'type' in rules and not isinstance(value, rules['type']):
            raise ParameterValidationError(
                parameter=param_name,
                value=value,
                details={'expected_type': rules['type'].__name__, 'actual_type': type(value).__name__}
            )
        
        # Validazione range
        if 'range' in rules:
            min_val, max_val = rules['range']
            if not (min_val <= value <= max_val):
                raise ParameterValidationError(
                    parameter=param_name,
                    value=value,
                    valid_range=rules['range']
                )
        
        # Validazione custom
        if 'validator' in rules:
            validator_func = rules['validator']
            if not validator_func(value):
                raise ParameterValidationError(
                    parameter=param_name,
                    value=value,
                    details={'validation_rule': rules.get('validator_description', 'Custom validation failed')}
                )


def create_error_response(error_code: str, message: str, details: dict = None, http_status: int = 400) -> tuple:
    """
    Crea una response di errore standardizzata per API Flask
    
    Args:
        error_code: Codice errore
        message: Messaggio user-friendly
        details: Dettagli aggiuntivi
        http_status: Status code HTTP
        
    Returns:
        tuple: (response_dict, http_status)
    """
    response = {
        'success': False,
        'error': {
            'error_type': 'AnomalySNMPError',
            'message': message,
            'error_code': error_code,
            'details': details or {}
        }
    }
    
    return response, http_status