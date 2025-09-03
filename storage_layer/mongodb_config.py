"""
MongoDB Configuration Module

Questo modulo gestisce la configurazione e la connessione a MongoDB per il sistema
di monitoraggio dell'infrastruttura PMI Dashboard.

Caratteristiche:
- Configurazione centralizzata per MongoDB
- Gestione delle connessioni con pooling
- Supporto per ambienti multipli (development, production)
- Configurazione SSL/TLS
- Autenticazione e autorizzazione
- Retry automatico per le connessioni
- Logging dettagliato delle operazioni

Utilizzo:
    from storage_layer.mongodb_config import MongoDBConfig
    
    config = MongoDBConfig()
    client = config.get_client()
    database = config.get_database()

Autore: PMI Dashboard Team
Data: Febbraio 2025
"""

import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


class MongoDBConfig:
    """
    Classe per la gestione della configurazione MongoDB.
    
    Questa classe centralizza tutte le configurazioni necessarie per
    connettersi a MongoDB, incluse le impostazioni di sicurezza,
    pooling delle connessioni e gestione degli errori.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Inizializza la configurazione MongoDB.
        
        Args:
            config_file: Percorso opzionale al file di configurazione
        """
        self.logger = logging.getLogger(__name__)
        self._client: Optional[MongoClient] = None
        self._config = self._load_config(config_file)
        
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Carica la configurazione da variabili d'ambiente o file.
        
        Args:
            config_file: Percorso al file di configurazione (opzionale)
            
        Returns:
            Dizionario con la configurazione MongoDB
        """
        # Configurazione di default
        config = {
            # Connessione di base
            'host': os.getenv('MONGODB_HOST', 'localhost'),
            'port': int(os.getenv('MONGODB_PORT', '27017')),
            'database': os.getenv('MONGODB_DATABASE', 'pmi_infrastructure'),
            
            # Autenticazione
            'username': os.getenv('MONGODB_USERNAME'),
            'password': os.getenv('MONGODB_PASSWORD'),
            'auth_source': os.getenv('MONGODB_AUTH_SOURCE', 'admin'),
            
            # Configurazioni avanzate
            'replica_set': os.getenv('MONGODB_REPLICA_SET'),
            'ssl_enabled': os.getenv('MONGODB_SSL_ENABLED', 'false').lower() == 'true',
            'ssl_cert_path': os.getenv('MONGODB_SSL_CERT_PATH'),
            'ssl_key_path': os.getenv('MONGODB_SSL_KEY_PATH'),
            'ssl_ca_path': os.getenv('MONGODB_SSL_CA_PATH'),
            
            # Pool di connessioni
            'max_pool_size': int(os.getenv('MONGODB_MAX_POOL_SIZE', '100')),
            'min_pool_size': int(os.getenv('MONGODB_MIN_POOL_SIZE', '10')),
            'max_idle_time_ms': int(os.getenv('MONGODB_MAX_IDLE_TIME_MS', '30000')),
            
            # Timeout e retry
            'connect_timeout_ms': int(os.getenv('MONGODB_CONNECT_TIMEOUT_MS', '10000')),
            'server_selection_timeout_ms': int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT_MS', '5000')),
            'socket_timeout_ms': int(os.getenv('MONGODB_SOCKET_TIMEOUT_MS', '20000')),
            'retry_writes': os.getenv('MONGODB_RETRY_WRITES', 'true').lower() == 'true',
            'retry_reads': os.getenv('MONGODB_RETRY_READS', 'true').lower() == 'true',
            
            # Configurazioni specifiche per l'ambiente
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'log_level': os.getenv('MONGODB_LOG_LEVEL', 'INFO'),
        }
        
        # Carica configurazioni specifiche per ambiente
        if config['environment'] == 'production':
            config.update(self._get_production_config())
        elif config['environment'] == 'development':
            config.update(self._get_development_config())
        elif config['environment'] == 'testing':
            config.update(self._get_testing_config())
            
        return config
    
    def _get_production_config(self) -> Dict[str, Any]:
        """
        Configurazioni specifiche per l'ambiente di produzione.
        
        Returns:
            Dizionario con configurazioni di produzione
        """
        return {
            'ssl_enabled': True,
            'max_pool_size': 200,
            'min_pool_size': 20,
            'connect_timeout_ms': 15000,
            'server_selection_timeout_ms': 10000,
            'socket_timeout_ms': 30000,
            'log_level': 'WARNING'
        }
    
    def _get_development_config(self) -> Dict[str, Any]:
        """
        Configurazioni specifiche per l'ambiente di sviluppo.
        
        Returns:
            Dizionario con configurazioni di sviluppo
        """
        return {
            'ssl_enabled': False,
            'max_pool_size': 50,
            'min_pool_size': 5,
            'connect_timeout_ms': 5000,
            'server_selection_timeout_ms': 3000,
            'socket_timeout_ms': 10000,
            'log_level': 'DEBUG'
        }
    
    def _get_testing_config(self) -> Dict[str, Any]:
        """
        Configurazioni specifiche per l'ambiente di test.
        
        Returns:
            Dizionario con configurazioni di test
        """
        return {
            'database': 'pmi_infrastructure_test',
            'ssl_enabled': False,
            'max_pool_size': 10,
            'min_pool_size': 1,
            'connect_timeout_ms': 3000,
            'server_selection_timeout_ms': 2000,
            'socket_timeout_ms': 5000,
            'log_level': 'DEBUG'
        }
    
    def get_connection_string(self) -> str:
        """
        Genera la stringa di connessione MongoDB.
        
        Returns:
            Stringa di connessione MongoDB URI
        """
        # Costruisci la parte di autenticazione
        auth_part = ""
        if self._config['username'] and self._config['password']:
            username = quote_plus(self._config['username'])
            password = quote_plus(self._config['password'])
            auth_part = f"{username}:{password}@"
        
        # Costruisci la parte host:port
        host_part = f"{self._config['host']}:{self._config['port']}"
        
        # Costruisci la stringa di connessione base
        connection_string = f"mongodb://{auth_part}{host_part}/{self._config['database']}"
        
        # Aggiungi parametri di query
        query_params = []
        
        if self._config['auth_source'] and self._config['username']:
            query_params.append(f"authSource={self._config['auth_source']}")
        
        if self._config['replica_set']:
            query_params.append(f"replicaSet={self._config['replica_set']}")
        
        if self._config['ssl_enabled']:
            query_params.append("ssl=true")
            if self._config['ssl_cert_path']:
                query_params.append(f"ssl_certfile={self._config['ssl_cert_path']}")
            if self._config['ssl_key_path']:
                query_params.append(f"ssl_keyfile={self._config['ssl_key_path']}")
            if self._config['ssl_ca_path']:
                query_params.append(f"ssl_ca_certs={self._config['ssl_ca_path']}")
        
        # Aggiungi parametri di connessione
        query_params.extend([
            f"maxPoolSize={self._config['max_pool_size']}",
            f"minPoolSize={self._config['min_pool_size']}",
            f"maxIdleTimeMS={self._config['max_idle_time_ms']}",
            f"connectTimeoutMS={self._config['connect_timeout_ms']}",
            f"serverSelectionTimeoutMS={self._config['server_selection_timeout_ms']}",
            f"socketTimeoutMS={self._config['socket_timeout_ms']}",
            f"retryWrites={str(self._config['retry_writes']).lower()}",
            f"retryReads={str(self._config['retry_reads']).lower()}"
        ])
        
        if query_params:
            connection_string += "?" + "&".join(query_params)
        
        return connection_string
    
    def get_client(self) -> MongoClient:
        """
        Ottiene un client MongoDB configurato.
        
        Returns:
            Istanza di MongoClient configurata
            
        Raises:
            ConnectionFailure: Se la connessione a MongoDB fallisce
        """
        if self._client is None:
            try:
                connection_string = self.get_connection_string()
                
                # Log della connessione (senza credenziali)
                safe_connection_string = self._sanitize_connection_string(connection_string)
                self.logger.info(f"Connessione a MongoDB: {safe_connection_string}")
                
                self._client = MongoClient(connection_string)
                
                # Test della connessione
                self._client.admin.command('ping')
                self.logger.info("Connessione a MongoDB stabilita con successo")
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                self.logger.error(f"Errore di connessione a MongoDB: {e}")
                raise ConnectionFailure(f"Impossibile connettersi a MongoDB: {e}")
            except Exception as e:
                self.logger.error(f"Errore imprevisto durante la connessione a MongoDB: {e}")
                raise
        
        return self._client
    
    def get_database(self):
        """
        Ottiene il database MongoDB configurato.
        
        Returns:
            Istanza del database MongoDB
        """
        client = self.get_client()
        return client[self._config['database']]
    
    def _sanitize_connection_string(self, connection_string: str) -> str:
        """
        Rimuove le credenziali dalla stringa di connessione per il logging.
        
        Args:
            connection_string: Stringa di connessione completa
            
        Returns:
            Stringa di connessione senza credenziali
        """
        if '@' in connection_string:
            # Trova la posizione delle credenziali
            protocol_end = connection_string.find('://') + 3
            credentials_end = connection_string.find('@')
            
            # Sostituisci le credenziali con ***
            sanitized = (connection_string[:protocol_end] + 
                        "***:***" + 
                        connection_string[credentials_end:])
            return sanitized
        
        return connection_string
    
    def close_connection(self):
        """
        Chiude la connessione MongoDB.
        """
        if self._client:
            self._client.close()
            self._client = None
            self.logger.info("Connessione MongoDB chiusa")
    
    def test_connection(self) -> bool:
        """
        Testa la connessione a MongoDB.
        
        Returns:
            True se la connessione è riuscita, False altrimenti
        """
        try:
            client = self.get_client()
            client.admin.command('ping')
            return True
        except Exception as e:
            self.logger.error(f"Test di connessione fallito: {e}")
            return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Ottiene informazioni sul server MongoDB.
        
        Returns:
            Dizionario con informazioni sul server
        """
        try:
            client = self.get_client()
            return client.server_info()
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere informazioni sul server: {e}")
            return {}
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche del database.
        
        Returns:
            Dizionario con statistiche del database
        """
        try:
            db = self.get_database()
            return db.command('dbStats')
        except Exception as e:
            self.logger.error(f"Errore nell'ottenere statistiche del database: {e}")
            return {}
    
    @property
    def config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione corrente (senza credenziali).
        
        Returns:
            Dizionario con la configurazione (credenziali rimosse)
        """
        safe_config = self._config.copy()
        if 'password' in safe_config:
            safe_config['password'] = '***'
        return safe_config


# Istanza globale per l'uso nell'applicazione
mongodb_config = MongoDBConfig()


def get_mongodb_client() -> MongoClient:
    """
    Funzione di convenienza per ottenere un client MongoDB.
    
    Returns:
        Istanza di MongoClient configurata
    """
    return mongodb_config.get_client()


def get_mongodb_database():
    """
    Funzione di convenienza per ottenere il database MongoDB.
    
    Returns:
        Istanza del database MongoDB
    """
    return mongodb_config.get_database()