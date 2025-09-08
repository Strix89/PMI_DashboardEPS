"""
AnomalySNMP ML Engine - Gestione modello Isolation Forest e calcolo score
Implementazione prevista nel Task 3
"""

import numpy as np
import pandas as pd
import time
import gc
import psutil
from sklearn.ensemble import IsolationForest
from flask import session
import logging
import pickle
import hashlib
import os
from typing import Dict, Any, Optional, Tuple
from functools import lru_cache

# Import delle eccezioni personalizzate e logging
from ..exceptions import (
    ModelTrainingError, ModelNotTrainedError, BaselineCalculationError,
    ScoreCalculationError, SessionError, SessionNotFoundError, SessionCorruptedError,
    ParameterValidationError, MemoryError, PerformanceError, validate_parameters
)
from ..logging_config import (
    get_logger, operation_context, performance_monitor, 
    error_handler, LoggingMixin
)
from ..monitoring import monitor_operation

# Usa il logger specifico per AnomalySNMP
logger = get_logger('anomaly_snmp.ml_engine')

class AnomalyDetectionModel(LoggingMixin):
    """Classe per gestione del modello di rilevamento anomalie con ottimizzazioni performance"""
    
    def __init__(self, cache_dir: str = None, enable_caching: bool = True):
        super().__init__()
        self.model = None
        self.baseline = None
        self._training_start_time = None
        self._memory_threshold = 1024 * 1024 * 1024  # 1GB threshold
        
        # Performance optimizations
        self.enable_caching = enable_caching
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '..', 'cache')
        self._ensure_cache_dir()
        
        # Model cache
        self._model_cache: Dict[str, Any] = {}
        self._baseline_cache: Dict[str, Dict] = {}
        
        # Batch processing settings
        self._batch_size = 1000
        
        self.log_info("AnomalyDetectionModel inizializzato con ottimizzazioni performance", 'init')
        self.log_info(f"Cache abilitata: {enable_caching}, Directory cache: {self.cache_dir}", 'init')
    
    def _ensure_cache_dir(self):
        """Crea la directory cache se non esiste"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            self.log_warning(f"Impossibile creare directory cache: {e}", 'cache_setup')
            self.enable_caching = False
    
    def _get_model_cache_key(self, train_data: np.ndarray, contamination: float) -> str:
        """Genera una chiave cache per il modello basata sui dati e parametri"""
        data_hash = hashlib.md5(str(train_data.shape).encode() + 
                               str(train_data.mean()).encode() + 
                               str(contamination).encode()).hexdigest()
        return f"isolation_forest_{data_hash}"
    
    def _save_model_to_cache(self, cache_key: str, model: IsolationForest, baseline: Dict):
        """Salva modello e baseline nella cache"""
        if not self.enable_caching:
            return
        
        try:
            cache_data = {
                'model': model,
                'baseline': baseline,
                'timestamp': time.time()
            }
            cache_file = os.path.join(self.cache_dir, f"{cache_key}_model.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            self.log_info(f"Modello salvato in cache: {cache_file}", 'cache_save')
        except Exception as e:
            self.log_warning(f"Errore salvataggio modello in cache: {e}", 'cache_save')
    
    def _load_model_from_cache(self, cache_key: str) -> Optional[Tuple[IsolationForest, Dict]]:
        """Carica modello e baseline dalla cache"""
        if not self.enable_caching:
            return None
        
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}_model.pkl")
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                
                # Controlla se il cache è troppo vecchio (24 ore)
                if time.time() - cache_data.get('timestamp', 0) > 24 * 3600:
                    os.remove(cache_file)
                    return None
                
                self.log_info(f"Modello caricato da cache: {cache_file}", 'cache_load')
                return cache_data['model'], cache_data['baseline']
        except Exception as e:
            self.log_warning(f"Errore caricamento modello da cache: {e}", 'cache_load')
        
        return None
    
    def _force_garbage_collection(self):
        """Forza garbage collection per liberare memoria"""
        collected = gc.collect()
        memory_info = psutil.virtual_memory()
        self.log_info(f"Garbage collection: {collected} oggetti liberati, "
                     f"memoria disponibile: {memory_info.available / 1024**2:.1f}MB", 'gc')
    
    @monitor_operation('train_isolation_forest')
    def train_isolation_forest(self, train_data: np.ndarray, contamination: float, use_cache: bool = True) -> IsolationForest:
        """
        Addestra il modello Isolation Forest con ottimizzazioni performance
        
        Args:
            train_data: Dati di training normalizzati (solo campioni normali)
            contamination: Percentuale di contaminazione attesa (0.01-0.15)
            use_cache: Se utilizzare la cache per velocizzare il training
            
        Returns:
            IsolationForest: Modello addestrato
            
        Raises:
            ValueError: Se i parametri non sono validi
            RuntimeError: Se il training fallisce
        """
        try:
            # Validazione parametri
            if not isinstance(train_data, np.ndarray):
                raise ValueError("train_data deve essere un numpy array")
            
            if train_data.size == 0:
                raise ValueError("train_data non può essere vuoto")
            
            if not (0.01 <= contamination <= 0.15):
                raise ValueError("contamination deve essere tra 0.01 e 0.15")
            
            self.log_info(f"Training Isolation Forest con contamination={contamination}", 'train_model')
            self.log_info(f"Dati di training: {train_data.shape[0]} campioni, {train_data.shape[1]} feature", 'train_model')
            
            # Controlla cache prima del training
            cache_key = self._get_model_cache_key(train_data, contamination)
            if use_cache:
                cached_result = self._load_model_from_cache(cache_key)
                if cached_result is not None:
                    model, baseline = cached_result
                    self.model = model
                    self.baseline = baseline
                    self.log_info("Modello e baseline caricati da cache", 'train_model')
                    return model
            
            # Controlla memoria disponibile prima del training
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 80:
                self.log_warning(f"Memoria alta prima del training: {memory_info.percent:.1f}%", 'train_model')
                self._force_garbage_collection()
            
            # Ottimizza dati per il training (usa float32 per risparmiare memoria)
            if train_data.dtype == np.float64:
                train_data = train_data.astype(np.float32)
                self.log_info("Dati convertiti a float32 per ottimizzazione memoria", 'train_model')
            
            # Inizializzazione modello Isolation Forest con parametri ottimizzati
            n_estimators = min(100, max(50, len(train_data) // 100))  # Adatta il numero di alberi ai dati
            max_samples = min(256, len(train_data))  # Limita campioni per albero per performance
            
            model = IsolationForest(
                contamination=contamination,
                random_state=42,  # Per riproducibilità
                n_estimators=n_estimators,
                max_samples=max_samples,
                max_features=1.0,  # Usa tutte le feature
                bootstrap=False,
                n_jobs=-1,  # Usa tutti i core disponibili
                verbose=0
            )
            
            # Training del modello con monitoraggio memoria
            self.log_info(f"Avvio training del modello (n_estimators={n_estimators}, max_samples={max_samples})", 'train_model')
            self._training_start_time = time.time()
            
            model.fit(train_data)
            
            training_time = time.time() - self._training_start_time
            self.log_info(f"Training completato in {training_time:.2f} secondi", 'train_model')
            
            # Verifica che il modello sia stato addestrato correttamente
            if not hasattr(model, 'decision_function'):
                raise RuntimeError("Modello non addestrato correttamente")
            
            # Test rapido del modello con batch processing per grandi dataset
            test_size = min(100, len(train_data))
            test_indices = np.random.choice(len(train_data), test_size, replace=False)
            test_scores = model.decision_function(train_data[test_indices])
            
            if len(test_scores) != test_size:
                raise RuntimeError("Modello non produce output validi")
            
            self.log_info(f"Score range sui dati di training: [{test_scores.min():.4f}, {test_scores.max():.4f}]", 'train_model')
            
            # Calcola baseline immediatamente per cache
            baseline = self.calculate_baseline(model, train_data)
            
            # Salva in cache se abilitato
            if use_cache:
                self._save_model_to_cache(cache_key, model, baseline)
            
            self.model = model
            self.baseline = baseline
            
            # Forza garbage collection dopo training
            self._force_garbage_collection()
            
            return model
            
        except ValueError as e:
            logger.error(f"Errore di validazione parametri: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore durante il training: {e}")
            raise RuntimeError(f"Training fallito: {str(e)}")
    
    @monitor_operation('calculate_baseline')
    def calculate_baseline(self, model: IsolationForest, train_data: np.ndarray) -> dict:
        """
        Calcola la baseline statistica (μnormal, σnormal) sui punteggi del training set
        
        Args:
            model: Modello Isolation Forest addestrato
            train_data: Dati di training normalizzati (solo campioni normali)
            
        Returns:
            dict: Baseline contenente mu_normal e sigma_normal
            
        Raises:
            ValueError: Se il modello non è addestrato o i dati non sono validi
            RuntimeError: Se il calcolo della baseline fallisce
        """
        try:
            # Validazione parametri
            if model is None:
                raise ValueError("Il modello non può essere None")
            
            if not hasattr(model, 'decision_function'):
                raise ValueError("Il modello deve essere addestrato")
            
            if not isinstance(train_data, np.ndarray) or train_data.size == 0:
                raise ValueError("train_data deve essere un numpy array non vuoto")
            
            self.log_info("Calcolo baseline statistica con ottimizzazioni", 'calculate_baseline')
            self.log_info(f"Calcolo su {train_data.shape[0]} campioni di training", 'calculate_baseline')
            
            # Calcola i punteggi grezzi con batch processing per dataset grandi
            if len(train_data) > self._batch_size:
                self.log_info(f"Utilizzo batch processing con batch_size={self._batch_size}", 'calculate_baseline')
                raw_scores = self._calculate_scores_batched(model, train_data)
            else:
                raw_scores = model.decision_function(train_data)
            
            # Verifica che i punteggi siano validi
            if len(raw_scores) != len(train_data):
                raise RuntimeError("Numero di punteggi non corrisponde ai dati di input")
            
            if np.any(np.isnan(raw_scores)) or np.any(np.isinf(raw_scores)):
                raise RuntimeError("Punteggi non validi (NaN o Inf) nel calcolo baseline")
            
            # Calcola media e deviazione standard
            mu_normal = float(np.mean(raw_scores))
            sigma_normal = float(np.std(raw_scores, ddof=1))  # Correzione di Bessel
            
            # Verifica che sigma non sia zero (evita divisione per zero)
            if sigma_normal <= 0:
                logger.warning("Deviazione standard molto piccola, impostata a valore minimo")
                sigma_normal = 1e-6
            
            baseline = {
                'mu_normal': mu_normal,
                'sigma_normal': sigma_normal,
                'n_samples': len(train_data),
                'score_range': {
                    'min': float(np.min(raw_scores)),
                    'max': float(np.max(raw_scores))
                }
            }
            
            self.log_info(f"Baseline calcolata: μ={mu_normal:.6f}, σ={sigma_normal:.6f}", 'calculate_baseline')
            self.log_info(f"Range punteggi: [{baseline['score_range']['min']:.6f}, {baseline['score_range']['max']:.6f}]", 'calculate_baseline')
            
            self.baseline = baseline
            
            # Forza garbage collection dopo calcolo baseline
            self._force_garbage_collection()
            
            return baseline
            
        except ValueError as e:
            logger.error(f"Errore di validazione nella baseline: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore nel calcolo baseline: {e}")
            raise RuntimeError(f"Calcolo baseline fallito: {str(e)}")
    
    def _calculate_scores_batched(self, model: IsolationForest, data: np.ndarray) -> np.ndarray:
        """
        Calcola punteggi in batch per ottimizzare memoria su dataset grandi
        
        Args:
            model: Modello Isolation Forest
            data: Dati da processare
            
        Returns:
            Array con tutti i punteggi
        """
        self.log_info(f"Calcolo punteggi in batch per {len(data)} campioni", 'batch_scoring')
        
        all_scores = []
        n_batches = (len(data) + self._batch_size - 1) // self._batch_size
        
        for i in range(0, len(data), self._batch_size):
            batch_end = min(i + self._batch_size, len(data))
            batch_data = data[i:batch_end]
            
            batch_scores = model.decision_function(batch_data)
            all_scores.append(batch_scores)
            
            # Log progresso ogni 10 batch
            batch_num = i // self._batch_size + 1
            if batch_num % 10 == 0:
                self.log_info(f"Processato batch {batch_num}/{n_batches}", 'batch_scoring')
            
            # Controllo memoria ogni batch
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                self.log_warning(f"Memoria alta durante batch scoring: {memory_percent:.1f}%", 'batch_scoring')
                gc.collect()
        
        # Combina tutti i punteggi
        combined_scores = np.concatenate(all_scores)
        self.log_info(f"Batch scoring completato: {len(combined_scores)} punteggi calcolati", 'batch_scoring')
        
        return combined_scores
    
    @lru_cache(maxsize=1000)
    def _cached_score_calculation(self, raw_score: float, mu_normal: float, sigma_normal: float) -> Tuple[float, float, str, str]:
        """
        Calcolo S_score con cache per valori ripetuti
        
        Args:
            raw_score: Punteggio grezzo
            mu_normal: Media baseline
            sigma_normal: Deviazione standard baseline
            
        Returns:
            Tuple (s_score, deviation_factor, risk_level, risk_color)
        """
        # Applica la formula ibrida per calcolare S_score
        if raw_score <= mu_normal:
            s_score = 1.0
            deviation_factor = 0.0
        else:
            # Calcola la deviazione in termini di sigma
            deviation = (raw_score - mu_normal) / (3 * sigma_normal)
            s_score = max(0.0, 1.0 - deviation)
            deviation_factor = deviation
        
        # Determina la categoria di rischio basata su S_score
        if s_score >= 0.8:
            risk_level = "Normal"
            risk_color = "green"
        elif s_score >= 0.6:
            risk_level = "Low Risk"
            risk_color = "yellow"
        elif s_score >= 0.3:
            risk_level = "Medium Risk"
            risk_color = "orange"
        else:
            risk_level = "High Risk"
            risk_color = "red"
        
        return s_score, deviation_factor, risk_level, risk_color
    
    @monitor_operation('calculate_anomaly_score')
    def calculate_anomaly_score(self, model: IsolationForest, data_point: np.ndarray, baseline: dict) -> dict:
        """
        Calcola l'S_score utilizzando la formula ibrida Isolation Forest + Statistical Process Control
        
        Formula: S_score(s_new) = {
            1.0                                    se s_new ≤ μnormal
            max(0, 1 - (s_new - μnormal)/(3 * σnormal))  se s_new > μnormal
        }
        
        Args:
            model: Modello Isolation Forest addestrato
            data_point: Singolo punto dati da valutare (shape: (n_features,) o (1, n_features))
            baseline: Baseline statistica con mu_normal e sigma_normal
            
        Returns:
            dict: Risultato contenente s_score, raw_score e dettagli del calcolo
            
        Raises:
            ValueError: Se i parametri non sono validi
            RuntimeError: Se il calcolo fallisce
        """
        try:
            # Validazione parametri
            if model is None:
                raise ValueError("Il modello non può essere None")
            
            if not hasattr(model, 'decision_function'):
                raise ValueError("Il modello deve essere addestrato")
            
            if not isinstance(data_point, np.ndarray):
                raise ValueError("data_point deve essere un numpy array")
            
            if baseline is None or not isinstance(baseline, dict):
                raise ValueError("baseline deve essere un dizionario valido")
            
            required_keys = ['mu_normal', 'sigma_normal']
            if not all(key in baseline for key in required_keys):
                raise ValueError(f"baseline deve contenere le chiavi: {required_keys}")
            
            # Assicurati che data_point abbia la forma corretta (1, n_features)
            if data_point.ndim == 1:
                data_point = data_point.reshape(1, -1)
            elif data_point.ndim != 2 or data_point.shape[0] != 1:
                raise ValueError("data_point deve avere forma (n_features,) o (1, n_features)")
            
            # Estrai parametri baseline
            mu_normal = baseline['mu_normal']
            sigma_normal = baseline['sigma_normal']
            
            # Calcola il punteggio grezzo usando Isolation Forest
            raw_score = model.decision_function(data_point)[0]  # Prendi il primo (e unico) elemento
            
            # Verifica che il punteggio sia valido
            if np.isnan(raw_score) or np.isinf(raw_score):
                raise RuntimeError("Punteggio grezzo non valido (NaN o Inf)")
            
            # Usa calcolo cached per performance migliori
            s_score, deviation_factor, risk_level, risk_color = self._cached_score_calculation(
                float(raw_score), mu_normal, sigma_normal
            )
            
            result = {
                's_score': float(s_score),
                'raw_score': float(raw_score),
                'deviation_factor': float(deviation_factor),
                'risk_level': risk_level,
                'risk_color': risk_color,
                'baseline_used': {
                    'mu_normal': mu_normal,
                    'sigma_normal': sigma_normal
                }
            }
            
            self.log_debug(f"S_score calcolato: {s_score:.4f} (raw: {raw_score:.4f}, risk: {risk_level})", 'calculate_score')
            
            return result
            
        except ValueError as e:
            logger.error(f"Errore di validazione nel calcolo S_score: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore nel calcolo S_score: {e}")
            raise RuntimeError(f"Calcolo S_score fallito: {str(e)}")
    
    def clear_cache(self, max_age_hours: int = 24):
        """
        Pulisce la cache rimuovendo file vecchi
        
        Args:
            max_age_hours: Età massima dei file cache in ore
        """
        if not self.enable_caching or not os.path.exists(self.cache_dir):
            return
        
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            removed_count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('_model.pkl'):
                    filepath = os.path.join(self.cache_dir, filename)
                    file_age = current_time - os.path.getmtime(filepath)
                    
                    if file_age > max_age_seconds:
                        os.remove(filepath)
                        removed_count += 1
            
            self.log_info(f"Cache cleanup modelli: rimossi {removed_count} file vecchi", 'cache_cleanup')
            
        except Exception as e:
            self.log_warning(f"Errore durante cache cleanup modelli: {e}", 'cache_cleanup')
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sulla cache dei modelli
        
        Returns:
            Dict con statistiche cache
        """
        if not self.enable_caching or not os.path.exists(self.cache_dir):
            return {'cache_enabled': False}
        
        try:
            model_files = [f for f in os.listdir(self.cache_dir) if f.endswith('_model.pkl')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in model_files)
            
            return {
                'cache_enabled': True,
                'cache_dir': self.cache_dir,
                'model_file_count': len(model_files),
                'total_size_mb': total_size / (1024**2),
                'model_files': model_files
            }
        except Exception as e:
            return {'cache_enabled': True, 'error': str(e)}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Ottiene informazioni sull'utilizzo di memoria
        
        Returns:
            Dict con informazioni memoria
        """
        try:
            memory_info = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            return {
                'system_memory': {
                    'total_gb': memory_info.total / (1024**3),
                    'available_gb': memory_info.available / (1024**3),
                    'percent_used': memory_info.percent
                },
                'process_memory': {
                    'rss_mb': process_memory.rss / (1024**2),
                    'vms_mb': process_memory.vms / (1024**2)
                },
                'model_loaded': self.model is not None,
                'baseline_loaded': self.baseline is not None
            }
        except Exception as e:
            return {'error': str(e)}
    
    @monitor_operation('save_model_to_session')
    def save_model_to_session(self, model: IsolationForest, baseline: dict, test_set: pd.DataFrame):
        """
        Salva modello, baseline e test set nella sessione Flask per persistenza
        
        Args:
            model: Modello Isolation Forest addestrato
            baseline: Baseline statistica con mu_normal e sigma_normal
            test_set: DataFrame con i dati di test ordinati per la simulazione
            
        Raises:
            ValueError: Se i parametri non sono validi
            RuntimeError: Se il salvataggio fallisce
        """
        try:
            # Validazione parametri
            if model is None:
                raise ValueError("Il modello non può essere None")
            
            if not hasattr(model, 'decision_function'):
                raise ValueError("Il modello deve essere addestrato")
            
            if baseline is None or not isinstance(baseline, dict):
                raise ValueError("baseline deve essere un dizionario valido")
            
            required_baseline_keys = ['mu_normal', 'sigma_normal']
            if not all(key in baseline for key in required_baseline_keys):
                raise ValueError(f"baseline deve contenere le chiavi: {required_baseline_keys}")
            
            if test_set is None or not isinstance(test_set, pd.DataFrame):
                raise ValueError("test_set deve essere un DataFrame valido")
            
            if test_set.empty:
                raise ValueError("test_set non può essere vuoto")
            
            self.log_info("Salvataggio modello e artifacts in sessione Flask con ottimizzazioni", 'save_session')
            self.log_info(f"Test set: {len(test_set)} campioni", 'save_session')
            self.log_info(f"Baseline: μ={baseline['mu_normal']:.6f}, σ={baseline['sigma_normal']:.6f}", 'save_session')
            
            # Controlla memoria prima del salvataggio
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 80:
                self.log_warning(f"Memoria alta prima del salvataggio: {memory_info.percent:.1f}%", 'save_session')
                self._force_garbage_collection()
            
            # Inizializza la sezione anomaly_snmp nella sessione se non esiste
            if 'anomaly_snmp' not in session:
                session['anomaly_snmp'] = {}
            
            # Ottimizza test_set per il salvataggio (riduci precisione float per risparmiare spazio)
            test_set_optimized = test_set.copy()
            for col in test_set_optimized.select_dtypes(include=[np.float64]).columns:
                test_set_optimized[col] = test_set_optimized[col].astype(np.float32)
            
            # Salva gli artifacts del modello
            # Nota: Non possiamo serializzare direttamente il modello sklearn in sessione
            # Salviamo i parametri necessari per ricreare il modello se necessario
            session['anomaly_snmp']['model_artifacts'] = {
                'baseline': {
                    'mu_normal': float(baseline['mu_normal']),
                    'sigma_normal': float(baseline['sigma_normal']),
                    'n_samples': baseline.get('n_samples', 0),
                    'score_range': baseline.get('score_range', {'min': 0, 'max': 0})
                },
                'model_params': {
                    'contamination': float(model.contamination),
                    'n_estimators': int(model.n_estimators),
                    'max_samples': model.max_samples,
                    'max_features': float(model.max_features),
                    'bootstrap': bool(model.bootstrap),
                    'random_state': int(model.random_state) if model.random_state else None
                },
                'test_set': test_set_optimized.to_dict('records'),  # Converti DataFrame ottimizzato
                'test_set_size': len(test_set),
                'current_offset': 0  # Inizializza l'offset per la simulazione
            }
            
            # Salva lo stato della simulazione
            session['anomaly_snmp']['simulation_state'] = {
                'is_running': False,
                'speed': 1000,  # Velocità default in ms
                'current_index': 0,
                'total_points': len(test_set)
            }
            
            # Salva timestamp per tracking
            from datetime import datetime
            session['anomaly_snmp']['metadata'] = {
                'created_at': datetime.now().isoformat(),
                'model_trained': True,
                'baseline_calculated': True
            }
            
            # Forza il salvataggio della sessione
            session.modified = True
            
            self.log_info("Modello e artifacts salvati con successo in sessione", 'save_session')
            self.log_info(f"Sessione contiene {len(session['anomaly_snmp']['model_artifacts']['test_set'])} punti di test", 'save_session')
            
            # Salva anche riferimenti locali per uso immediato
            self.model = model
            self.baseline = baseline
            
            # Forza garbage collection dopo salvataggio
            self._force_garbage_collection()
            
            # Log utilizzo memoria finale
            final_memory = psutil.virtual_memory()
            self.log_info(f"Memoria dopo salvataggio: {final_memory.percent:.1f}%", 'save_session')
            
        except ValueError as e:
            logger.error(f"Errore di validazione nel salvataggio sessione: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore nel salvataggio in sessione: {e}")
            raise RuntimeError(f"Salvataggio in sessione fallito: {str(e)}")
    
    def load_model_from_session(self):
        """
        Carica modello e baseline dalla sessione Flask
        
        Returns:
            tuple: (model, baseline, test_set) se disponibili, altrimenti (None, None, None)
            
        Raises:
            RuntimeError: Se i dati in sessione sono corrotti
        """
        try:
            if 'anomaly_snmp' not in session:
                logger.warning("Nessuna sessione anomaly_snmp trovata")
                return None, None, None
            
            if 'model_artifacts' not in session['anomaly_snmp']:
                logger.warning("Nessun model_artifacts in sessione")
                return None, None, None
            
            artifacts = session['anomaly_snmp']['model_artifacts']
            
            # Verifica che tutti i dati necessari siano presenti
            if 'baseline' not in artifacts or 'test_set' not in artifacts:
                logger.warning("Dati incompleti in sessione")
                return None, None, None
            
            baseline = artifacts['baseline']
            test_set_data = artifacts['test_set']
            
            # Ricostruisci il DataFrame del test set
            test_set = pd.DataFrame(test_set_data)
            
            logger.info("Dati caricati dalla sessione con successo")
            logger.info(f"Baseline: μ={baseline['mu_normal']:.6f}, σ={baseline['sigma_normal']:.6f}")
            logger.info(f"Test set: {len(test_set)} campioni")
            
            # Nota: Il modello sklearn non può essere serializzato in sessione
            # Dovrebbe essere riaddestrato se necessario, o mantenuto in memoria
            # Per ora restituiamo None per il modello
            return None, baseline, test_set
            
        except Exception as e:
            logger.error(f"Errore nel caricamento dalla sessione: {e}")
            raise RuntimeError(f"Caricamento dalla sessione fallito: {str(e)}")
    
    def get_session_status(self):
        """
        Verifica lo stato della sessione e restituisce informazioni di debug
        
        Returns:
            dict: Informazioni sullo stato della sessione
        """
        try:
            if 'anomaly_snmp' not in session:
                return {'session_exists': False, 'message': 'Nessuna sessione trovata'}
            
            anomaly_session = session['anomaly_snmp']
            
            status = {
                'session_exists': True,
                'has_model_artifacts': 'model_artifacts' in anomaly_session,
                'has_simulation_state': 'simulation_state' in anomaly_session,
                'has_metadata': 'metadata' in anomaly_session
            }
            
            if status['has_model_artifacts']:
                artifacts = anomaly_session['model_artifacts']
                status['baseline_available'] = 'baseline' in artifacts
                status['test_set_size'] = artifacts.get('test_set_size', 0)
                status['current_offset'] = artifacts.get('current_offset', 0)
            
            if status['has_simulation_state']:
                sim_state = anomaly_session['simulation_state']
                status['simulation_running'] = sim_state.get('is_running', False)
                status['current_index'] = sim_state.get('current_index', 0)
                status['total_points'] = sim_state.get('total_points', 0)
            
            if status['has_metadata']:
                metadata = anomaly_session['metadata']
                status['created_at'] = metadata.get('created_at', 'Unknown')
                status['model_trained'] = metadata.get('model_trained', False)
                status['baseline_calculated'] = metadata.get('baseline_calculated', False)
            
            return status
            
        except Exception as e:
            logger.error(f"Errore nel controllo stato sessione: {e}")
            return {'session_exists': False, 'error': str(e)}