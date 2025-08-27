"""
PMI Dashboard EPS - Discovery Engine
Configuration Manager

Gestisce il caricamento e la validazione delle configurazioni YAML
per il modulo Discovery Engine.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import yaml
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import jsonschema
from jsonschema import validate

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Gestisce la configurazione del Discovery Engine.
    
    Carica e valida file di configurazione YAML, fornendo accesso
    strutturato alle impostazioni dei vari scanner e moduli.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inizializza il ConfigManager.
        
        Args:
            config_path: Percorso al file di configurazione. 
                        Se None, usa il file predefinito.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config: Dict[str, Any] = {}
        self.oids_config: Dict[str, Any] = {}
        
        logger.info(f"Inizializzazione ConfigManager con config: {self.config_path}")
        
        # Carica le configurazioni
        self._load_config()
        self._load_oids_config()
        self._validate_config()
        
    def _get_default_config_path(self) -> str:
        """
        Determina il percorso del file di configurazione predefinito.
        
        Returns:
            Percorso assoluto al file config.yml
        """
        # Determina la directory root del progetto
        current_dir = Path(__file__).parent.parent.parent
        config_file = current_dir / "config" / "config.yml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"File di configurazione non trovato: {config_file}")
            
        return str(config_file)
    
    def _load_config(self) -> None:
        """
        Carica il file di configurazione principale.
        
        Raises:
            FileNotFoundError: Se il file non esiste
            yaml.YAMLError: Se il file non è un YAML valido
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
                logger.info("Configurazione principale caricata con successo")
                logger.debug(f"Configurazione caricata: {self.config.keys()}")
        except FileNotFoundError:
            logger.error(f"File di configurazione non trovato: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Errore nel parsing YAML: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore imprevisto nel caricamento config: {e}")
            raise
    
    def _load_oids_config(self) -> None:
        """
        Carica il file di configurazione OID.
        """
        try:
            oids_path = Path(self.config_path).parent / "oids.yml"
            
            if not oids_path.exists():
                logger.warning(f"File OID non trovato: {oids_path}")
                self.oids_config = {}
                return
                
            with open(oids_path, 'r', encoding='utf-8') as file:
                self.oids_config = yaml.safe_load(file)
                logger.info("Configurazione OID caricata con successo")
                logger.debug(f"OID categorie caricate: {self.oids_config.keys()}")
                
        except yaml.YAMLError as e:
            logger.error(f"Errore nel parsing OID YAML: {e}")
            self.oids_config = {}
        except Exception as e:
            logger.warning(f"Errore nel caricamento OID config: {e}")
            self.oids_config = {}
    
    def _validate_config(self) -> None:
        """
        Valida la struttura della configurazione.
        
        Verifica che tutte le sezioni richieste siano presenti
        e che i valori siano nel formato corretto.
        """
        logger.info("Avvio validazione configurazione")
        
        required_sections = ['network', 'arp_discovery', 'nmap', 'snmp', 'output', 'logging']
        
        for section in required_sections:
            if section not in self.config:
                error_msg = f"Sezione mancante nella configurazione: {section}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # Validazioni specifiche
        self._validate_network_config()
        self._validate_output_config()
        self._validate_logging_config()
        
        logger.info("Validazione configurazione completata con successo")
    
    def _validate_network_config(self) -> None:
        """Valida la configurazione di rete."""
        network_config = self.config.get('network', {})
        
        if 'target_range' not in network_config:
            raise ValueError("target_range mancante nella configurazione network")
        
        # Verifica formato CIDR di base
        target_range = network_config['target_range']
        if '/' not in target_range:
            raise ValueError(f"target_range deve essere in formato CIDR: {target_range}")
            
        logger.debug(f"Network config validata: {target_range}")
    
    def _validate_output_config(self) -> None:
        """Valida la configurazione di output."""
        output_config = self.config.get('output', {})
        
        required_output_fields = ['format', 'file']
        for field in required_output_fields:
            if field not in output_config:
                raise ValueError(f"Campo mancante nella configurazione output: {field}")
                
        logger.debug("Output config validata")
    
    def _validate_logging_config(self) -> None:
        """Valida la configurazione di logging."""
        logging_config = self.config.get('logging', {})
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        level = logging_config.get('level', 'INFO')
        
        if level not in valid_levels:
            raise ValueError(f"Livello di logging non valido: {level}")
            
        logger.debug(f"Logging config validata: {level}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Ottiene un valore dalla configurazione.
        
        Args:
            key: Chiave della configurazione (supporta dot notation: 'network.target_range')
            default: Valore predefinito se la chiave non esiste
            
        Returns:
            Valore della configurazione o default
        """
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
                    
            return value
            
        except Exception:
            logger.warning(f"Errore nell'accesso alla configurazione: {key}")
            return default
    
    def get_network_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione di rete.
        
        Returns:
            Dizionario con configurazione network
        """
        return self.config.get('network', {})
    
    def get_arp_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione ARP scanner.
        
        Returns:
            Dizionario con configurazione ARP
        """
        return self.config.get('arp_discovery', {})
    
    def get_nmap_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione NMAP scanner.
        
        Returns:
            Dizionario con configurazione NMAP
        """
        return self.config.get('nmap', {})
    
    def get_snmp_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione SNMP scanner.
        
        Returns:
            Dizionario con configurazione SNMP
        """
        return self.config.get('snmp', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione di output.
        
        Returns:
            Dizionario con configurazione output
        """
        return self.config.get('output', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione di logging.
        
        Returns:
            Dizionario con configurazione logging
        """
        return self.config.get('logging', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione di performance.
        
        Returns:
            Dizionario con configurazione performance
        """
        return self.config.get('performance', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione di sicurezza.
        
        Returns:
            Dizionario con configurazione security
        """
        return self.config.get('security', {})
    
    def get_oid_config(self, category: str) -> Dict[str, Any]:
        """
        Ottiene la configurazione OID per una categoria.
        
        Args:
            category: Categoria OID (es. 'standard', 'vendor')
            
        Returns:
            Dizionario con OID della categoria
        """
        return self.oids_config.get(category, {})
    
    def get_all_oids(self) -> Dict[str, Any]:
        """
        Ottiene tutte le configurazioni OID.
        
        Returns:
            Dizionario completo delle configurazioni OID
        """
        return self.oids_config
    
    def is_scanner_enabled(self, scanner_name: str) -> bool:
        """
        Verifica se uno scanner è abilitato.
        
        Args:
            scanner_name: Nome dello scanner ('arp_discovery', 'nmap', 'snmp')
            
        Returns:
            True se lo scanner è abilitato
        """
        scanner_config = self.config.get(scanner_name, {})
        return scanner_config.get('enabled', False)
    
    def reload_config(self) -> None:
        """
        Ricarica la configurazione dai file.
        
        Utile per aggiornare la configurazione senza riavviare l'applicazione.
        """
        logger.info("Ricaricamento configurazione in corso...")
        
        try:
            self._load_config()
            self._load_oids_config()
            self._validate_config()
            logger.info("Configurazione ricaricata con successo")
        except Exception as e:
            logger.error(f"Errore nel ricaricamento configurazione: {e}")
            raise
    
    def __str__(self) -> str:
        """Rappresentazione string del ConfigManager."""
        return f"ConfigManager(config_path='{self.config_path}')"
    
    def __repr__(self) -> str:
        """Rappresentazione debug del ConfigManager."""
        return (f"ConfigManager(config_path='{self.config_path}', "
                f"sections={list(self.config.keys())})")
