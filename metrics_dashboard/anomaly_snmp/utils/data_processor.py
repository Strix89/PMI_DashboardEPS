"""
AnomalySNMP Data Processor - Gestione preprocessing dati SNMP
Implementazione prevista nel Task 2
"""

import pandas as pd
import numpy as np
import os
import gc
import psutil
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
import logging
from functools import lru_cache
from typing import Optional, Dict, Tuple, Any
import pickle
import hashlib

# Import delle eccezioni personalizzate e logging
from ..exceptions import (
    DatasetNotFoundError, DatasetValidationError, DatasetCorruptedError,
    DataProcessingError, NormalizationError, SMOTEError, MemoryError,
    ParameterValidationError, validate_parameters
)
from ..logging_config import (
    get_logger, operation_context, performance_monitor, 
    error_handler, LoggingMixin
)
from ..monitoring import monitor_operation

logger = get_logger('anomaly_snmp.data_processing')

class SNMPDataProcessor(LoggingMixin):
    """Classe per il preprocessing dei dati SNMP-MIB con gestione errori robusta e ottimizzazioni performance"""
    
    def __init__(self, cache_dir: str = None, enable_caching: bool = True):
        super().__init__()
        self.scaler = StandardScaler()
        self.smote = SMOTE(random_state=42)
        self._memory_threshold = 500 * 1024 * 1024  # 500MB threshold
        
        # Performance optimizations
        self.enable_caching = enable_caching
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '..', 'cache')
        self._ensure_cache_dir()
        
        # Memory management
        self._chunk_size = 10000  # Process data in chunks
        self._lazy_loading = True
        
        # Cache for processed data
        self._dataset_cache: Dict[str, Any] = {}
        self._scaler_cache: Dict[str, StandardScaler] = {}
        
        self.log_info("SNMPDataProcessor inizializzato con ottimizzazioni performance", 'init')
        self.log_info(f"Cache abilitata: {enable_caching}, Directory cache: {self.cache_dir}", 'init')
    
    def _ensure_cache_dir(self):
        """Crea la directory cache se non esiste"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            self.log_warning(f"Impossibile creare directory cache: {e}", 'cache_setup')
            self.enable_caching = False
    
    def _get_cache_key(self, dataset_path: str, operation: str = 'load') -> str:
        """Genera una chiave cache basata sul path e timestamp del file"""
        try:
            file_stat = os.stat(dataset_path)
            content = f"{dataset_path}_{operation}_{file_stat.st_mtime}_{file_stat.st_size}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return hashlib.md5(f"{dataset_path}_{operation}".encode()).hexdigest()
    
    def _save_to_cache(self, cache_key: str, data: Any, operation: str = 'data'):
        """Salva dati nella cache"""
        if not self.enable_caching:
            return
        
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}_{operation}.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            self.log_info(f"Dati salvati in cache: {cache_file}", 'cache_save')
        except Exception as e:
            self.log_warning(f"Errore salvataggio cache: {e}", 'cache_save')
    
    def _load_from_cache(self, cache_key: str, operation: str = 'data') -> Optional[Any]:
        """Carica dati dalla cache"""
        if not self.enable_caching:
            return None
        
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}_{operation}.pkl")
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                self.log_info(f"Dati caricati da cache: {cache_file}", 'cache_load')
                return data
        except Exception as e:
            self.log_warning(f"Errore caricamento cache: {e}", 'cache_load')
        
        return None
    
    @monitor_operation('load_dataset')
    @performance_monitor(operation='load_dataset', threshold=5.0)
    @error_handler(operation='load_dataset', recovery_suggestion='Verificare che il file dataset esista e sia accessibile')
    def load_dataset(self, dataset_path: str, use_cache: bool = True) -> pd.DataFrame:
        """
        Carica il dataset SNMP-MIB e valida la struttura dati con ottimizzazioni performance
        
        Args:
            dataset_path: Percorso al file CSV del dataset
            use_cache: Se utilizzare la cache per velocizzare il caricamento
            
        Returns:
            DataFrame con i dati caricati e validati
            
        Raises:
            DatasetNotFoundError: Se il file non esiste
            DatasetValidationError: Se la struttura del dataset non è valida
            DatasetCorruptedError: Se il dataset è corrotto
            MemoryError: Se non c'è memoria sufficiente
        """
        with operation_context(self._logger, 'load_dataset', dataset_path=dataset_path, use_cache=use_cache) as ctx:
            # Validazione parametri
            if not dataset_path or not isinstance(dataset_path, str):
                raise ParameterValidationError(
                    parameter='dataset_path',
                    value=dataset_path,
                    details={'error': 'Percorso dataset deve essere una stringa non vuota'}
                )
            
            # Verifica esistenza file
            if not os.path.exists(dataset_path):
                raise DatasetNotFoundError(dataset_path)
            
            # Controlla cache prima di caricare
            cache_key = self._get_cache_key(dataset_path, 'load_dataset')
            if use_cache:
                cached_data = self._load_from_cache(cache_key, 'dataset')
                if cached_data is not None:
                    self.log_info("Dataset caricato da cache", 'load_dataset')
                    ctx['loaded_from_cache'] = True
                    ctx['rows'] = cached_data.shape[0]
                    ctx['columns'] = cached_data.shape[1]
                    return cached_data
            
            # Verifica dimensione file e memoria disponibile
            file_size = os.path.getsize(dataset_path)
            available_memory = psutil.virtual_memory().available
            
            ctx['file_size_mb'] = file_size / (1024 * 1024)
            ctx['available_memory_mb'] = available_memory / (1024 * 1024)
            
            if file_size > available_memory * 0.5:  # Usa max 50% della memoria disponibile
                raise MemoryError(
                    message=f"File troppo grande per la memoria disponibile: {file_size/(1024*1024):.1f}MB",
                    operation='load_dataset',
                    memory_info={
                        'file_size_mb': file_size / (1024 * 1024),
                        'available_memory_mb': available_memory / (1024 * 1024)
                    }
                )
            
            self.log_info(f"Caricamento dataset: {dataset_path} ({file_size/(1024*1024):.1f}MB)", 'load_dataset')
            
            try:
                # Carica il dataset CSV con gestione errori e ottimizzazioni memoria
                if self._lazy_loading and file_size > 50 * 1024 * 1024:  # 50MB
                    # Per file grandi, usa chunked loading
                    self.log_info("File grande rilevato, utilizzo caricamento chunked", 'load_dataset')
                    df = self._load_dataset_chunked(dataset_path)
                else:
                    # Caricamento normale per file piccoli
                    df = pd.read_csv(dataset_path, low_memory=False)
                
                if df.empty:
                    raise DatasetCorruptedError(
                        message="Dataset vuoto",
                        dataset_path=dataset_path,
                        corruption_details={'issue': 'empty_dataset'}
                    )
                
                ctx['rows'] = df.shape[0]
                ctx['columns'] = df.shape[1]
                ctx['loaded_from_cache'] = False
                
                self.log_info(f"Dataset caricato: {df.shape[0]} righe, {df.shape[1]} colonne", 'load_dataset')
                
                # Valida la struttura del dataset
                self._validate_dataset_structure(df, dataset_path)
                
                # Salva in cache se abilitato
                if use_cache:
                    self._save_to_cache(cache_key, df, 'dataset')
                
                return df
                
            except pd.errors.EmptyDataError:
                raise DatasetCorruptedError(
                    message="File dataset vuoto o corrotto",
                    dataset_path=dataset_path,
                    corruption_details={'issue': 'empty_file'}
                )
            except pd.errors.ParserError as e:
                raise DatasetCorruptedError(
                    message=f"Errore nel parsing del CSV: {str(e)}",
                    dataset_path=dataset_path,
                    corruption_details={'issue': 'parser_error', 'details': str(e)}
                )
            except UnicodeDecodeError as e:
                raise DatasetCorruptedError(
                    message=f"Errore di encoding del file: {str(e)}",
                    dataset_path=dataset_path,
                    corruption_details={'issue': 'encoding_error', 'details': str(e)}
                )
    
    def _load_dataset_chunked(self, dataset_path: str) -> pd.DataFrame:
        """
        Carica dataset grandi utilizzando chunked loading per ottimizzare memoria
        
        Args:
            dataset_path: Percorso al file CSV
            
        Returns:
            DataFrame completo caricato in chunks
        """
        self.log_info(f"Caricamento chunked con chunk_size={self._chunk_size}", 'chunked_loading')
        
        chunks = []
        total_rows = 0
        
        try:
            # Prima passata: conta le righe per stimare memoria
            with open(dataset_path, 'r') as f:
                estimated_rows = sum(1 for _ in f) - 1  # -1 per header
            
            self.log_info(f"Righe stimate: {estimated_rows}", 'chunked_loading')
            
            # Carica in chunks
            chunk_reader = pd.read_csv(dataset_path, chunksize=self._chunk_size, low_memory=False)
            
            for i, chunk in enumerate(chunk_reader):
                chunks.append(chunk)
                total_rows += len(chunk)
                
                # Log progresso ogni 10 chunks
                if i % 10 == 0:
                    self.log_info(f"Processato chunk {i+1}, righe totali: {total_rows}", 'chunked_loading')
                
                # Controllo memoria ogni chunk
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 85:
                    self.log_warning(f"Memoria alta durante chunked loading: {memory_percent:.1f}%", 'chunked_loading')
                    # Forza garbage collection
                    gc.collect()
            
            # Combina tutti i chunks
            self.log_info("Combinazione chunks in DataFrame finale", 'chunked_loading')
            df = pd.concat(chunks, ignore_index=True)
            
            # Libera memoria dei chunks
            del chunks
            gc.collect()
            
            self.log_info(f"Chunked loading completato: {len(df)} righe totali", 'chunked_loading')
            return df
            
        except Exception as e:
            self.log_error(f"Errore durante chunked loading: {e}", 'chunked_loading')
            raise DatasetCorruptedError(
                message=f"Errore nel caricamento chunked: {str(e)}",
                dataset_path=dataset_path,
                corruption_details={'issue': 'chunked_loading_error', 'details': str(e)}
            )
    
    def _validate_dataset_structure(self, df: pd.DataFrame, dataset_path: str = None) -> None:
        """
        Valida la struttura del dataset SNMP-MIB
        
        Args:
            df: DataFrame da validare
            dataset_path: Percorso del dataset per logging
            
        Raises:
            DatasetValidationError: Se la struttura non è valida
        """
        validation_errors = []
        validation_details = {}
        
        try:
            # Verifica che ci sia la colonna 'class'
            if 'class' not in df.columns:
                validation_errors.append("Colonna 'class' mancante nel dataset")
                validation_details['missing_class_column'] = True
            
            # Verifica numero minimo di colonne
            if df.shape[1] < 9:  # 8 feature + 1 class
                validation_errors.append(f"Dataset ha solo {df.shape[1]} colonne, richieste almeno 9")
                validation_details['insufficient_columns'] = df.shape[1]
            
            # Verifica che ci siano almeno le 8 feature di interfaccia
            interface_features = [col for col in df.columns if col.startswith('if')]
            interface_cols = df.columns[:8]  # Prime 8 colonne dovrebbero essere le feature
            
            if len(interface_features) < 8 and len(interface_cols) < 8:
                validation_errors.append(f"Trovate solo {len(interface_features)} feature di interfaccia, richieste almeno 8")
                validation_details['interface_features_found'] = len(interface_features)
                validation_details['interface_features_required'] = 8
            
            # Verifica valori mancanti nelle feature di interfaccia
            if len(interface_cols) >= 8:
                missing_values = df[interface_cols].isnull().sum()
                if missing_values.any():
                    validation_errors.append("Valori mancanti trovati nelle feature di interfaccia")
                    validation_details['missing_values_per_column'] = missing_values.to_dict()
            
            # Verifica valori non numerici nelle feature
            if len(interface_cols) >= 8:
                non_numeric_cols = []
                for col in interface_cols:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        non_numeric_cols.append(col)
                
                if non_numeric_cols:
                    validation_errors.append(f"Feature non numeriche trovate: {non_numeric_cols}")
                    validation_details['non_numeric_features'] = non_numeric_cols
            
            # Verifica che ci siano classi valide
            if 'class' in df.columns:
                valid_classes = ['normal', 'bruteForce', 'httpFlood', 'icmp-echo', 'slowloris', 'slowpost', 'tcp-syn', 'udp-flood']
                unique_classes = set(df['class'].unique())
                invalid_classes = unique_classes - set(valid_classes)
                
                if invalid_classes:
                    validation_errors.append(f"Classi non valide trovate: {list(invalid_classes)}")
                    validation_details['invalid_classes'] = list(invalid_classes)
                    validation_details['valid_classes'] = valid_classes
                
                # Verifica distribuzione classi
                class_counts = df['class'].value_counts()
                if len(class_counts) < 2:
                    validation_errors.append("Dataset deve contenere almeno 2 classi diverse")
                    validation_details['unique_classes_count'] = len(class_counts)
                
                validation_details['class_distribution'] = class_counts.to_dict()
            
            # Verifica dimensioni minime del dataset
            if df.shape[0] < 100:
                validation_errors.append(f"Dataset troppo piccolo: {df.shape[0]} righe, richieste almeno 100")
                validation_details['dataset_size'] = df.shape[0]
                validation_details['minimum_size'] = 100
            
            # Se ci sono errori di validazione, solleva eccezione
            if validation_errors:
                error_message = "Validazione dataset fallita: " + "; ".join(validation_errors)
                raise DatasetValidationError(
                    message=error_message,
                    dataset_path=dataset_path,
                    validation_details=validation_details
                )
            
            # Log successo validazione
            self.log_info("Struttura dataset validata con successo", 'validate_dataset')
            self.log_info(f"Feature di interfaccia: {list(interface_cols)}", 'validate_dataset')
            self.log_info(f"Classi presenti: {sorted(df['class'].unique())}", 'validate_dataset')
            self.log_info(f"Distribuzione classi: {df['class'].value_counts().to_dict()}", 'validate_dataset')
            
        except DatasetValidationError:
            raise
        except Exception as e:
            raise DatasetValidationError(
                message=f"Errore imprevisto durante validazione: {str(e)}",
                dataset_path=dataset_path,
                validation_details={'unexpected_error': str(e)}
            )
    
    def _optimize_memory_usage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ottimizza l'utilizzo di memoria del DataFrame riducendo i tipi di dati
        
        Args:
            df: DataFrame da ottimizzare
            
        Returns:
            DataFrame ottimizzato per memoria
        """
        self.log_info("Ottimizzazione memoria DataFrame", 'memory_optimization')
        
        original_memory = df.memory_usage(deep=True).sum() / 1024**2
        
        # Ottimizza colonne numeriche
        for col in df.select_dtypes(include=['int64']).columns:
            col_min = df[col].min()
            col_max = df[col].max()
            
            if col_min >= 0:
                if col_max < 255:
                    df[col] = df[col].astype('uint8')
                elif col_max < 65535:
                    df[col] = df[col].astype('uint16')
                elif col_max < 4294967295:
                    df[col] = df[col].astype('uint32')
            else:
                if col_min > -128 and col_max < 127:
                    df[col] = df[col].astype('int8')
                elif col_min > -32768 and col_max < 32767:
                    df[col] = df[col].astype('int16')
                elif col_min > -2147483648 and col_max < 2147483647:
                    df[col] = df[col].astype('int32')
        
        # Ottimizza colonne float
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = pd.to_numeric(df[col], downcast='float')
        
        # Ottimizza colonne categoriche
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:  # Se meno del 50% valori unici
                df[col] = df[col].astype('category')
        
        optimized_memory = df.memory_usage(deep=True).sum() / 1024**2
        memory_reduction = (original_memory - optimized_memory) / original_memory * 100
        
        self.log_info(f"Memoria ottimizzata: {original_memory:.2f}MB → {optimized_memory:.2f}MB "
                     f"(riduzione: {memory_reduction:.1f}%)", 'memory_optimization')
        
        return df
    
    def _force_garbage_collection(self):
        """Forza garbage collection per liberare memoria"""
        collected = gc.collect()
        memory_info = psutil.virtual_memory()
        self.log_info(f"Garbage collection: {collected} oggetti liberati, "
                     f"memoria disponibile: {memory_info.available / 1024**2:.1f}MB", 'gc')
    
    @monitor_operation('transform_labels')
    def transform_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Trasforma le etichette: 7 tipi attacco → 1 classe anomalia
        
        Converte tutte le classi di attacco in un'unica classe 'anomaly' (etichetta 1)
        mentre mantiene 'normal' come classe 0.
        
        Args:
            df: DataFrame con le etichette originali
            
        Returns:
            DataFrame con etichette trasformate (0=normal, 1=anomaly)
        """
        self.log_info("Trasformazione etichette in corso con ottimizzazioni memoria", 'transform_labels')
        
        # Ottimizza memoria prima della trasformazione
        df = self._optimize_memory_usage(df)
        
        # Crea una copia del dataframe per evitare modifiche inplace
        df_transformed = df.copy()
        
        # Conta le classi originali
        original_counts = df['class'].value_counts()
        self.log_info(f"Distribuzione classi originali: {original_counts.to_dict()}", 'transform_labels')
        
        # Trasforma le etichette: normal -> 0, tutti gli attacchi -> 1
        attack_classes = ['bruteForce', 'httpFlood', 'icmp-echo', 'slowloris', 'slowpost', 'tcp-syn', 'udp-flood']
        
        # Usa vectorized operation per performance migliori
        df_transformed['binary_class'] = (df_transformed['class'] != 'normal').astype('uint8')
        
        # Mantieni anche l'etichetta originale per riferimento
        df_transformed['original_class'] = df_transformed['class'].astype('category')
        
        # Sostituisci la colonna class con quella binaria
        df_transformed['class'] = df_transformed['binary_class']
        df_transformed = df_transformed.drop('binary_class', axis=1)
        
        # Log della trasformazione
        new_counts = df_transformed['class'].value_counts()
        self.log_info(f"Distribuzione classi trasformate: {new_counts.to_dict()}", 'transform_labels')
        self.log_info(f"Classi di attacco consolidate: {attack_classes}", 'transform_labels')
        
        # Verifica che la trasformazione sia corretta
        normal_count = len(df_transformed[df_transformed['class'] == 0])
        anomaly_count = len(df_transformed[df_transformed['class'] == 1])
        total_attacks = sum(original_counts[attack] for attack in attack_classes if attack in original_counts)
        
        if normal_count != original_counts.get('normal', 0):
            raise ValueError("Errore nella trasformazione: conteggio normal non corretto")
        if anomaly_count != total_attacks:
            raise ValueError("Errore nella trasformazione: conteggio anomalie non corretto")
        
        self.log_info(f"Trasformazione completata: {normal_count} normal, {anomaly_count} anomalie", 'transform_labels')
        
        # Forza garbage collection dopo trasformazione
        self._force_garbage_collection()
        
        return df_transformed
    
    @monitor_operation('normalize_features')
    def normalize_features(self, df: pd.DataFrame, use_cache: bool = True) -> tuple:
        """
        Normalizza le 8 feature di interfaccia con StandardScaler e caching
        
        Args:
            df: DataFrame con le feature da normalizzare
            use_cache: Se utilizzare la cache per il scaler
            
        Returns:
            Tuple (df_normalized, scaler) dove:
            - df_normalized: DataFrame con feature normalizzate
            - scaler: StandardScaler fitted per uso futuro
        """
        self.log_info("Normalizzazione feature in corso con ottimizzazioni", 'normalize_features')
        
        # Seleziona le prime 8 colonne (feature di interfaccia)
        interface_features = df.columns[:8]
        self.log_info(f"Feature di interfaccia da normalizzare: {list(interface_features)}", 'normalize_features')
        
        # Genera cache key basata sui dati
        feature_data = df[interface_features].values
        data_hash = hashlib.md5(str(feature_data.shape).encode() + 
                               str(feature_data.mean()).encode()).hexdigest()
        cache_key = f"scaler_{data_hash}"
        
        # Controlla cache per scaler
        cached_scaler = None
        if use_cache:
            cached_scaler = self._load_from_cache(cache_key, 'scaler')
        
        if cached_scaler is not None:
            self.log_info("Scaler caricato da cache", 'normalize_features')
            scaler = cached_scaler
        else:
            # Crea e addestra nuovo scaler
            scaler = StandardScaler()
            scaler.fit(feature_data)
            
            # Salva in cache
            if use_cache:
                self._save_to_cache(cache_key, scaler, 'scaler')
        
        # Crea una copia ottimizzata del dataframe
        df_normalized = df.copy()
        
        # Applica normalizzazione
        X_normalized = scaler.transform(feature_data)
        
        # Sostituisci le feature normalizzate nel dataframe
        df_normalized[interface_features] = X_normalized
        
        # Ottimizza memoria del risultato
        df_normalized = self._optimize_memory_usage(df_normalized)
        
        # Log delle statistiche di normalizzazione
        self.log_info("Normalizzazione completata:", 'normalize_features')
        for i, feature in enumerate(interface_features):
            mean_val = scaler.mean_[i]
            std_val = scaler.scale_[i]
            self.log_info(f"  {feature}: mean={mean_val:.2e}, std={std_val:.2e}", 'normalize_features')
        
        # Forza garbage collection
        self._force_garbage_collection()
        
        return df_normalized, scaler
    
    @monitor_operation('split_and_oversample')
    def split_and_oversample(self, df: pd.DataFrame, contamination: float, train_split: float) -> dict:
        """
        Suddivide i dati e applica SMOTE per oversampling
        
        Args:
            df: DataFrame normalizzato con etichette trasformate
            contamination: Percentuale di contaminazione desiderata (0.01-0.15)
            train_split: Percentuale per training set (0.5-0.9)
            
        Returns:
            Dict con i dataset processati:
            - normal_original: Dati normali originali
            - normal_synthetic: Campioni SMOTE generati
            - normal_train: Training set normale
            - normal_test: Test set normale
            - anomaly_data: Tutti i dati di anomalia
            - test_set_ordered: Test set finale ordinato
        """
        self.log_info(f"Split dati e oversampling con contamination={contamination}, train_split={train_split}", 'split_oversample')
        
        # Ottimizza memoria prima del processing
        df = self._optimize_memory_usage(df)
        
        # Separa dati normali e anomalie usando operazioni vettorizzate
        normal_mask = df['class'] == 0
        normal_data = df[normal_mask].copy()
        anomaly_data = df[~normal_mask].copy()
        
        self.log_info(f"Dati originali: {len(normal_data)} normal, {len(anomaly_data)} anomalie", 'split_oversample')
        
        # Calcola il numero target di campioni normali usando la formula
        anomaly_count = len(anomaly_data)
        normal_target = self._calculate_smote_target(contamination, anomaly_count)
        
        self.log_info(f"Target campioni normali per contamination {contamination}: {normal_target}", 'split_oversample')
        
        # Suddividi i dati normali originali in train/test con ottimizzazioni
        normal_shuffled = normal_data.sample(frac=1, random_state=42).reset_index(drop=True)
        train_size = int(len(normal_shuffled) * train_split)
        
        normal_train_original = normal_shuffled.iloc[:train_size].copy()
        normal_test = normal_shuffled.iloc[train_size:].copy()
        
        # Libera memoria del dataframe shuffled
        del normal_shuffled
        self._force_garbage_collection()
        
        self.log_info(f"Split normale: {len(normal_train_original)} train, {len(normal_test)} test", 'split_oversample')
        
        # Calcola quanti campioni sintetici generare
        synthetic_needed = max(0, normal_target - len(normal_train_original))
        
        if synthetic_needed > 0:
            # Applica SMOTE per generare campioni sintetici con ottimizzazioni memoria
            normal_synthetic = self._generate_synthetic_samples_optimized(normal_train_original, synthetic_needed)
            self.log_info(f"Generati {len(normal_synthetic)} campioni sintetici con SMOTE", 'split_oversample')
        else:
            # Se abbiamo già abbastanza campioni, non generiamo sintetici
            normal_synthetic = pd.DataFrame(columns=normal_train_original.columns)
            self.log_info("Nessun campione sintetico necessario", 'split_oversample')
        
        # Combina i dati normali originali e sintetici per il training
        if len(normal_synthetic) > 0:
            normal_train_combined = pd.concat([normal_train_original, normal_synthetic], ignore_index=True)
            # Ottimizza memoria del risultato combinato
            normal_train_combined = self._optimize_memory_usage(normal_train_combined)
        else:
            normal_train_combined = normal_train_original.copy()
        
        # Prepara il test set ordinato per la simulazione
        test_set_ordered = self.prepare_test_set(normal_test, anomaly_data)
        
        result = {
            'normal_original': normal_data,
            'normal_synthetic': normal_synthetic,
            'normal_train': normal_train_combined,
            'normal_test': normal_test,
            'anomaly_data': anomaly_data,
            'test_set_ordered': test_set_ordered
        }
        
        # Log del risultato finale
        self.log_info("Risultato split e oversampling:", 'split_oversample')
        for key, data in result.items():
            if isinstance(data, pd.DataFrame):
                self.log_info(f"  {key}: {len(data)} campioni", 'split_oversample')
        
        # Forza garbage collection finale
        self._force_garbage_collection()
        
        return result
    
    def _calculate_smote_target(self, contamination: float, anomaly_count: int) -> int:
        """
        Calcola il numero target di campioni normali per raggiungere la contaminazione desiderata
        
        Formula: N_normal_target = (anomaly_count / contamination) - anomaly_count
        
        Args:
            contamination: Percentuale di contaminazione (0.01-0.15)
            anomaly_count: Numero di campioni di anomalia
            
        Returns:
            Numero target di campioni normali
        """
        total_target = anomaly_count / contamination
        normal_target = int(total_target - anomaly_count)
        
        logger.info(f"Calcolo SMOTE target: {anomaly_count} anomalie / {contamination} = {total_target:.0f} totale")
        logger.info(f"Target campioni normali: {total_target:.0f} - {anomaly_count} = {normal_target}")
        
        return normal_target
    
    def _generate_synthetic_samples_optimized(self, normal_data: pd.DataFrame, synthetic_needed: int) -> pd.DataFrame:
        """
        Genera campioni sintetici usando SMOTE con ottimizzazioni memoria
        
        Args:
            normal_data: Dati normali originali per il training
            synthetic_needed: Numero di campioni sintetici da generare
            
        Returns:
            DataFrame con i campioni sintetici generati
        """
        self.log_info(f"Generazione {synthetic_needed} campioni sintetici con SMOTE ottimizzato", 'smote_generation')
        
        # Controlla memoria disponibile
        memory_info = psutil.virtual_memory()
        if memory_info.percent > 80:
            self.log_warning(f"Memoria alta prima di SMOTE: {memory_info.percent:.1f}%", 'smote_generation')
            self._force_garbage_collection()
        
        try:
            # Estrai le feature (prime 8 colonne) con ottimizzazioni
            feature_cols = normal_data.columns[:8]
            X_normal = normal_data[feature_cols].values.astype(np.float32)  # Usa float32 per risparmiare memoria
            y_normal = normal_data['class'].values.astype(np.uint8)
            
            # Crea dati artificiali per SMOTE (aggiungi alcune anomalie fittizie)
            n_fake_anomalies = min(10, len(normal_data) // 2)
            X_fake_anomalies = X_normal[:n_fake_anomalies] * 1.5  # Modifica leggermente i valori
            y_fake_anomalies = np.ones(n_fake_anomalies, dtype=np.uint8)
            
            # Combina per SMOTE
            X_combined = np.vstack([X_normal, X_fake_anomalies]).astype(np.float32)
            y_combined = np.hstack([y_normal, y_fake_anomalies]).astype(np.uint8)
            
            # Calcola il sampling strategy per ottenere il numero desiderato di campioni normali
            total_normal_desired = len(normal_data) + synthetic_needed
            sampling_strategy = {0: total_normal_desired, 1: n_fake_anomalies}
            
            # Applica SMOTE con parametri ottimizzati per memoria
            smote = SMOTE(
                sampling_strategy=sampling_strategy, 
                random_state=42,
                n_jobs=1  # Usa single thread per controllare memoria
            )
            
            self.log_info("Applicazione SMOTE in corso...", 'smote_generation')
            X_resampled, y_resampled = smote.fit_resample(X_combined, y_combined)
            
            # Libera memoria intermedia
            del X_combined, y_combined, X_normal, X_fake_anomalies
            self._force_garbage_collection()
            
            # Estrai solo i nuovi campioni normali (quelli oltre i dati originali)
            normal_mask = y_resampled == 0
            X_normal_resampled = X_resampled[normal_mask]
            
            # Prendi solo i campioni sintetici (escludendo quelli originali)
            X_synthetic = X_normal_resampled[len(normal_data):]
            
            # Crea DataFrame per i campioni sintetici
            synthetic_df = pd.DataFrame(X_synthetic, columns=feature_cols)
            
            # Aggiungi le altre colonne mantenendo i valori tipici dei dati normali
            for col in normal_data.columns[8:]:
                if col == 'class':
                    synthetic_df[col] = np.uint8(0)  # Classe normale
                elif col == 'original_class':
                    synthetic_df[col] = pd.Categorical(['normal'] * len(synthetic_df))
                else:
                    # Per le altre feature, usa la media dei dati normali
                    synthetic_df[col] = normal_data[col].mean()
            
            # Ottimizza memoria del risultato
            synthetic_df = self._optimize_memory_usage(synthetic_df)
            
            self.log_info(f"SMOTE ottimizzato completato: generati {len(synthetic_df)} campioni sintetici", 'smote_generation')
            
            # Libera memoria finale
            del X_resampled, y_resampled, X_normal_resampled, X_synthetic
            self._force_garbage_collection()
            
            return synthetic_df
            
        except Exception as e:
            self.log_error(f"Errore durante SMOTE ottimizzato: {e}", 'smote_generation')
            raise DataProcessingError(
                message=f"Errore nella generazione campioni sintetici: {str(e)}",
                operation='smote_generation',
                details={'synthetic_needed': synthetic_needed, 'error': str(e)}
            )
    
    def _generate_synthetic_samples(self, normal_data: pd.DataFrame, synthetic_needed: int) -> pd.DataFrame:
        """
        Genera campioni sintetici usando SMOTE
        
        Args:
            normal_data: Dati normali originali per il training
            synthetic_needed: Numero di campioni sintetici da generare
            
        Returns:
            DataFrame con i campioni sintetici generati
        """
        logger.info(f"Generazione {synthetic_needed} campioni sintetici con SMOTE...")
        
        # Estrai le feature (prime 8 colonne)
        X_normal = normal_data.iloc[:, :8].values
        y_normal = normal_data['class'].values
        
        # Crea dati artificiali per SMOTE (aggiungi alcune anomalie fittizie)
        # SMOTE richiede almeno 2 classi, quindi creiamo alcune anomalie temporanee
        n_fake_anomalies = min(10, len(normal_data) // 2)
        X_fake_anomalies = X_normal[:n_fake_anomalies] * 1.5  # Modifica leggermente i valori
        y_fake_anomalies = np.ones(n_fake_anomalies)
        
        # Combina per SMOTE
        X_combined = np.vstack([X_normal, X_fake_anomalies])
        y_combined = np.hstack([y_normal, y_fake_anomalies])
        
        # Calcola il sampling strategy per ottenere il numero desiderato di campioni normali
        total_normal_desired = len(normal_data) + synthetic_needed
        sampling_strategy = {0: total_normal_desired, 1: n_fake_anomalies}
        
        # Applica SMOTE
        smote = SMOTE(sampling_strategy=sampling_strategy, random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X_combined, y_combined)
        
        # Estrai solo i nuovi campioni normali (quelli oltre i dati originali)
        normal_mask = y_resampled == 0
        X_normal_resampled = X_resampled[normal_mask]
        
        # Prendi solo i campioni sintetici (escludendo quelli originali)
        X_synthetic = X_normal_resampled[len(normal_data):]
        
        # Crea DataFrame per i campioni sintetici
        synthetic_df = pd.DataFrame(X_synthetic, columns=normal_data.columns[:8])
        
        # Aggiungi le altre colonne mantenendo i valori tipici dei dati normali
        for col in normal_data.columns[8:]:
            if col == 'class':
                synthetic_df[col] = 0  # Classe normale
            elif col == 'original_class':
                synthetic_df[col] = 'normal'  # Classe originale normale
            else:
                # Per le altre feature, usa la media dei dati normali
                synthetic_df[col] = normal_data[col].mean()
        
        logger.info(f"SMOTE completato: generati {len(synthetic_df)} campioni sintetici")
        
        return synthetic_df
    
    def clear_cache(self, max_age_hours: int = 24):
        """
        Pulisce la cache rimuovendo file vecchi
        
        Args:
            max_age_hours: Età massima dei file cache in ore
        """
        if not self.enable_caching or not os.path.exists(self.cache_dir):
            return
        
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            removed_count = 0
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    filepath = os.path.join(self.cache_dir, filename)
                    file_age = current_time - os.path.getmtime(filepath)
                    
                    if file_age > max_age_seconds:
                        os.remove(filepath)
                        removed_count += 1
            
            self.log_info(f"Cache cleanup: rimossi {removed_count} file vecchi", 'cache_cleanup')
            
        except Exception as e:
            self.log_warning(f"Errore durante cache cleanup: {e}", 'cache_cleanup')
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sulla cache
        
        Returns:
            Dict con statistiche cache
        """
        if not self.enable_caching or not os.path.exists(self.cache_dir):
            return {'cache_enabled': False}
        
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            return {
                'cache_enabled': True,
                'cache_dir': self.cache_dir,
                'file_count': len(cache_files),
                'total_size_mb': total_size / (1024**2),
                'files': cache_files
            }
        except Exception as e:
            return {'cache_enabled': True, 'error': str(e)}
    
    @monitor_operation('prepare_test_set')
    def prepare_test_set(self, normal_test: pd.DataFrame, anomaly_data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara il test set ordinato per la simulazione
        
        Combina i dati normali di test con le anomalie, ordinandoli per la simulazione.
        Prima mostra tutti i record normal_test, poi le anomalie nell'ordine originale.
        
        Args:
            normal_test: DataFrame con i dati normali di test
            anomaly_data: DataFrame con tutti i dati di anomalia
            
        Returns:
            DataFrame ordinato per la simulazione tempo reale
        """
        self.log_info("Preparazione test set per simulazione con ottimizzazioni", 'prepare_test_set')
        
        # Ottimizza memoria dei dataframe di input
        normal_test = self._optimize_memory_usage(normal_test)
        anomaly_data = self._optimize_memory_usage(anomaly_data)
        
        # Crea copie per evitare modifiche inplace
        normal_test_copy = normal_test.copy()
        anomaly_data_copy = anomaly_data.copy()
        
        # Aggiungi un indice di simulazione per tracciare l'ordine usando operazioni vettorizzate
        normal_test_copy['simulation_order'] = np.arange(len(normal_test_copy), dtype=np.uint32)
        anomaly_data_copy['simulation_order'] = np.arange(
            len(normal_test_copy), 
            len(normal_test_copy) + len(anomaly_data_copy), 
            dtype=np.uint32
        )
        
        # Combina i dataset
        test_set_combined = pd.concat([normal_test_copy, anomaly_data_copy], ignore_index=True)
        
        # Libera memoria delle copie intermedie
        del normal_test_copy, anomaly_data_copy
        self._force_garbage_collection()
        
        # Ordina per simulation_order per garantire l'ordine corretto
        test_set_ordered = test_set_combined.sort_values('simulation_order').reset_index(drop=True)
        
        # Ottimizza memoria del risultato finale
        test_set_ordered = self._optimize_memory_usage(test_set_ordered)
        
        # Log delle informazioni del test set
        self.log_info("Test set preparato per simulazione:", 'prepare_test_set')
        self.log_info(f"  Totale campioni: {len(test_set_ordered)}", 'prepare_test_set')
        self.log_info(f"  Campioni normali: {len(normal_test)} (indici 0-{len(normal_test)-1})", 'prepare_test_set')
        self.log_info(f"  Campioni anomalie: {len(anomaly_data)} (indici {len(normal_test)}-{len(test_set_ordered)-1})", 'prepare_test_set')
        
        # Verifica la distribuzione delle classi nel test set
        class_distribution = test_set_ordered['class'].value_counts().sort_index()
        self.log_info(f"  Distribuzione classi: {class_distribution.to_dict()}", 'prepare_test_set')
        
        # Forza garbage collection finale
        self._force_garbage_collection()
        
        return test_set_ordered