"""
PMI Dashboard EPS - Discovery Engine
Main Discovery Engine

Orchestratore principale per la discovery di rete utilizzando scanner ARP, NMAP e SNMP.
Coordina l'esecuzione sequenziale degli scanner e consolida i risultati.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

# Import moduli locali
from .utils.config_manager import ConfigManager
from .utils.output_manager import OutputManager
from .utils.network_utils import NetworkUtils
from .scanners.arp_scanner import ARPScanner
from .scanners.nmap_scanner import NMapScanner
from .scanners.snmp_scanner import SNMPScanner

logger = logging.getLogger(__name__)

class DiscoveryEngine:
    """
    Motore principale di discovery per PMI Dashboard EPS.
    
    Orchestratore che coordina l'esecuzione degli scanner ARP, NMAP e SNMP
    secondo il flusso definito nelle specifiche:
    1. ARP Discovery per identificazione rapida dispositivi
    2. NMAP Discovery per port scan e service detection  
    3. SNMP Discovery per raccolta informazioni dettagliate
    4. Consolidamento risultati e output strutturato
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inizializza il Discovery Engine.
        
        Args:
            config_path: Percorso file configurazione personalizzato
        """
        self.scan_id = str(uuid.uuid4())
        self.start_time: Optional[datetime] = None
        
        # Inizializza gestori configurazione
        logger.info(f"Inizializzazione Discovery Engine (scan_id: {self.scan_id})")
        
        try:
            self.config_manager = ConfigManager(config_path)
            self.setup_logging()
            
            self.output_manager = OutputManager(
                self.config_manager.get_output_config(),
                self._get_output_directory()
            )
            
            logger.info("ConfigManager e OutputManager inizializzati")
            
        except Exception as e:
            logger.error(f"Errore inizializzazione Discovery Engine: {e}")
            raise
        
        # Inizializza scanner
        self._init_scanners()
        
        # Risultati consolidati
        self.discovery_results: Optional[Dict[str, Any]] = None
        
        logger.info("Discovery Engine inizializzato con successo")
    
    def setup_logging(self) -> None:
        """
        Configura il sistema di logging secondo la configurazione.
        """
        logging_config = self.config_manager.get_logging_config()
        
        # Configurazione base logging
        log_level = getattr(logging, logging_config.get('level', 'INFO').upper())
        log_format = logging_config.get('format', 
                                       '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Configura root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Configura logging su file se specificato
        log_file = logging_config.get('file')
        if log_file:
            log_dir = self._get_log_directory()
            log_path = log_dir / log_file
            
            # Crea directory log se non esiste
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Configura file handler con rotazione
            from logging.handlers import RotatingFileHandler
            max_size = logging_config.get('max_size_mb', 10) * 1024 * 1024
            backup_count = logging_config.get('backup_count', 5)
            
            file_handler = RotatingFileHandler(
                log_path, maxBytes=max_size, backupCount=backup_count
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format))
            
            # Aggiunge handler a root logger
            logging.getLogger().addHandler(file_handler)
            
            logger.info(f"Logging configurato su file: {log_path}")
        
        # Configura logging specifico per componenti
        components_config = logging_config.get('components', {})
        for component, level in components_config.items():
            component_logger = logging.getLogger(f'discovery.scanners.{component}_scanner')
            component_level = getattr(logging, level.upper(), log_level)
            component_logger.setLevel(component_level)
        
        logger.info(f"Logging configurato: livello {logging_config.get('level', 'INFO')}")
    
    def _get_output_directory(self) -> str:
        """
        Determina la directory di output.
        
        Returns:
            Percorso directory output
        """
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir / "output")
    
    def _get_log_directory(self) -> Path:
        """
        Determina la directory dei log.
        
        Returns:
            Path directory log
        """
        current_dir = Path(__file__).parent.parent.parent
        return current_dir / "logs"
    
    def _init_scanners(self) -> None:
        """
        Inizializza i moduli scanner.
        """
        logger.info("Inizializzazione scanner")
        
        # ARP Scanner
        arp_config = self.config_manager.get_arp_config()
        self.arp_scanner = ARPScanner(arp_config)
        logger.info(f"ARP Scanner: {'abilitato' if self.arp_scanner.is_enabled() else 'disabilitato'}")
        
        # NMAP Scanner  
        nmap_config = self.config_manager.get_nmap_config()
        self.nmap_scanner = NMapScanner(nmap_config)
        logger.info(f"NMAP Scanner: {'abilitato' if self.nmap_scanner.is_enabled() else 'disabilitato'}")
        
        # SNMP Scanner
        snmp_config = self.config_manager.get_snmp_config()
        oids_config = self.config_manager.get_all_oids()
        self.snmp_scanner = SNMPScanner(snmp_config, oids_config)
        logger.info(f"SNMP Scanner: {'abilitato' if self.snmp_scanner.is_enabled() else 'disabilitato'}")
    
    def run_discovery(self, target_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Esegue la discovery completa seguendo il flusso specificato.
        
        Args:
            target_range: Range di rete target (override configurazione)
            
        Returns:
            Risultati completi della discovery
        """
        self.start_time = datetime.utcnow()
        
        # Determina parametri scansione
        network_config = self.config_manager.get_network_config()
        scan_range = target_range or network_config.get('target_range')
        configured_excludes = network_config.get('exclude_ranges', [])
        
        # Auto-esclusione IP locali
        exclude_ranges = NetworkUtils.exclude_local_ips_from_targets(scan_range, configured_excludes)
        
        # Ottieni informazioni di rete locali per logging
        network_info = NetworkUtils.get_network_info_summary()
        
        logger.info(f"=== AVVIO DISCOVERY COMPLETA ===")
        logger.info(f"Scan ID: {self.scan_id}")
        logger.info(f"Target Range: {scan_range}")
        logger.info(f"IP locali rilevati: {network_info['local_ips']}")
        logger.info(f"IP primario: {network_info['primary_ip']}")
        logger.info(f"Exclude Ranges: {exclude_ranges}")
        
        if not scan_range:
            raise ValueError("Target range non specificato nella configurazione")
        
        # Valida il range di rete
        if not NetworkUtils.validate_network_range(scan_range):
            raise ValueError(f"Range di rete non valido: {scan_range}")
        
        # Inizializza struttura risultati
        self.discovery_results = self.output_manager.create_discovery_result_structure(self.scan_id)
        self.discovery_results['discovery_metadata']['network_range'] = scan_range
        self.discovery_results['discovery_metadata']['configuration_used'] = self.config_manager.config_path
        self.discovery_results['discovery_metadata']['local_machine_info'] = network_info
        
        try:
            # FASE 1: ARP Discovery
            arp_results = self._execute_arp_discovery(scan_range, exclude_ranges)
            
            # FASE 2: NMAP Discovery  
            nmap_results = self._execute_nmap_discovery(scan_range, exclude_ranges)
            
            # FASE 3: SNMP Discovery
            snmp_results = self._execute_snmp_discovery()
            
            # FASE 4: Consolidamento risultati
            self._consolidate_results(arp_results, nmap_results, snmp_results)
            
            # FASE 5: Finalizzazione e output
            self._finalize_discovery()
            
            logger.info(f"=== DISCOVERY COMPLETATA ===")
            logger.info(f"Dispositivi trovati: {len(self.discovery_results['devices'])}")
            logger.info(f"Durata totale: {self.discovery_results['discovery_metadata']['scan_duration_seconds']}s")
            
            return self.discovery_results
            
        except Exception as e:
            logger.error(f"Errore durante discovery: {e}")
            
            # Aggiunge errore ai risultati
            self.output_manager.add_error_to_results(self.discovery_results, {
                'error_type': 'discovery_failed',
                'message': str(e)
            })
            
            # Finalizza comunque i risultati parziali
            self._finalize_discovery()
            raise
    
    def _execute_arp_discovery(self, target_range: str, exclude_ranges: List[str]) -> Dict[str, Any]:
        """
        Esegue la Fase 1: ARP Discovery.
        
        Args:
            target_range: Range di rete target
            exclude_ranges: Range da escludere
            
        Returns:
            Risultati ARP discovery
        """
        logger.info("=== FASE 1: ARP DISCOVERY ===")
        
        if not self.arp_scanner.is_enabled():
            logger.info("ARP Scanner disabilitato - saltando fase")
            return {'devices': [], 'statistics': {}, 'errors': []}
        
        try:
            arp_results = self.arp_scanner.scan(target_range, exclude_ranges)
            
            # Aggiunge dispositivi ai risultati consolidati
            for device in arp_results['devices']:
                self.output_manager.add_device_to_results(self.discovery_results, device)
            
            # Aggiunge statistiche
            self.discovery_results['scan_statistics']['arp_scan'] = arp_results['statistics']
            
            # Aggiunge eventuali errori
            for error in arp_results['errors']:
                self.output_manager.add_error_to_results(self.discovery_results, error)
            
            devices_found = len(arp_results['devices'])
            logger.info(f"ARP Discovery completata: {devices_found} dispositivi trovati")
            
            return arp_results
            
        except Exception as e:
            logger.error(f"Errore ARP Discovery: {e}")
            self.output_manager.add_error_to_results(self.discovery_results, {
                'error_type': 'arp_discovery_failed',
                'message': str(e)
            })
            return {'devices': [], 'statistics': {'error': str(e)}, 'errors': []}
    
    def _execute_nmap_discovery(self, target_range: str, exclude_ranges: List[str]) -> Dict[str, Any]:
        """
        Esegue la Fase 2: NMAP Discovery.
        
        Args:
            target_range: Range di rete target
            exclude_ranges: Range da escludere
            
        Returns:
            Risultati NMAP discovery
        """
        logger.info("=== FASE 2: NMAP DISCOVERY ===")
        
        if not self.nmap_scanner.is_enabled():
            logger.info("NMAP Scanner disabilitato - saltando fase")
            return {'devices': [], 'statistics': {}, 'errors': []}
        
        try:
            nmap_results = self.nmap_scanner.scan(target_range, exclude_ranges)
            
            # Aggiunge statistiche
            self.discovery_results['scan_statistics']['nmap_scan'] = nmap_results['statistics']
            
            # Aggiunge eventuali errori
            for error in nmap_results['errors']:
                self.output_manager.add_error_to_results(self.discovery_results, error)
            
            devices_found = len(nmap_results['devices'])
            logger.info(f"NMAP Discovery completata: {devices_found} dispositivi scansionati")
            
            return nmap_results
            
        except Exception as e:
            logger.error(f"Errore NMAP Discovery: {e}")
            self.output_manager.add_error_to_results(self.discovery_results, {
                'error_type': 'nmap_discovery_failed',
                'message': str(e)
            })
            return {'devices': [], 'statistics': {'error': str(e)}, 'errors': []}
    
    def _execute_snmp_discovery(self) -> Dict[str, Any]:
        """
        Esegue la Fase 3: SNMP Discovery sui dispositivi già identificati.
        
        Returns:
            Risultati SNMP discovery
        """
        logger.info("=== FASE 3: SNMP DISCOVERY ===")
        
        if not self.snmp_scanner.is_enabled():
            logger.info("SNMP Scanner disabilitato - saltando fase")
            return {'devices': [], 'statistics': {}, 'errors': []}
        
        # Raccoglie IP dei dispositivi già trovati
        target_hosts = [device['ip_address'] for device in self.discovery_results['devices']]
        
        if not target_hosts:
            logger.info("Nessun dispositivo target per SNMP Discovery")
            return {'devices': [], 'statistics': {}, 'errors': []}
        
        try:
            snmp_results = self.snmp_scanner.scan(target_hosts)
            
            # Aggiunge statistiche
            self.discovery_results['scan_statistics']['snmp_scan'] = snmp_results['statistics']
            
            # Aggiunge eventuali errori
            for error in snmp_results['errors']:
                self.output_manager.add_error_to_results(self.discovery_results, error)
            
            devices_found = len(snmp_results['devices'])
            logger.info(f"SNMP Discovery completata: {devices_found} dispositivi accessibili via SNMP")
            
            return snmp_results
            
        except Exception as e:
            logger.error(f"Errore SNMP Discovery: {e}")
            self.output_manager.add_error_to_results(self.discovery_results, {
                'error_type': 'snmp_discovery_failed',
                'message': str(e)
            })
            return {'devices': [], 'statistics': {'error': str(e)}, 'errors': []}
    
    def _consolidate_results(self, arp_results: Dict[str, Any], 
                           nmap_results: Dict[str, Any], 
                           snmp_results: Dict[str, Any]) -> None:
        """
        Consolida i risultati di tutti gli scanner.
        
        Unisce informazioni da ARP, NMAP e SNMP per ciascun dispositivo,
        evitando duplicati e arricchendo le informazioni disponibili.
        
        Args:
            arp_results: Risultati ARP scanner
            nmap_results: Risultati NMAP scanner  
            snmp_results: Risultati SNMP scanner
        """
        logger.info("=== FASE 4: CONSOLIDAMENTO RISULTATI ===")
        
        # Dizionario per tenere traccia dei dispositivi per IP
        devices_by_ip: Dict[str, Dict[str, Any]] = {}
        
        # Inizializza con dispositivi esistenti (principalmente da ARP)
        for device in self.discovery_results['devices']:
            ip = device['ip_address']
            devices_by_ip[ip] = device
        
        # Integra risultati NMAP
        for nmap_device in nmap_results['devices']:
            ip = nmap_device['ip_address']
            
            if ip in devices_by_ip:
                # Arricchisce dispositivo esistente con dati NMAP
                existing_device = devices_by_ip[ip]
                existing_device = self._merge_nmap_data(existing_device, nmap_device)
                devices_by_ip[ip] = existing_device
            else:
                # Nuovo dispositivo trovato solo da NMAP
                devices_by_ip[ip] = nmap_device
        
        # Integra risultati SNMP
        for snmp_device in snmp_results['devices']:
            ip = snmp_device['ip_address']
            
            if ip in devices_by_ip:
                # Arricchisce dispositivo esistente con dati SNMP
                existing_device = devices_by_ip[ip]
                existing_device = self._merge_snmp_data(existing_device, snmp_device)
                devices_by_ip[ip] = existing_device
            else:
                # Dispositivo trovato solo via SNMP (raro ma possibile)
                devices_by_ip[ip] = snmp_device
        
        # Aggiorna la lista dispositivi consolidati
        consolidated_devices = list(devices_by_ip.values())
        
        # Filtra dispositivi vuoti/inutili
        filtered_devices = self._filter_meaningful_devices(consolidated_devices)
        self.discovery_results['devices'] = filtered_devices
        
        # Aggiorna metodi di discovery utilizzati
        methods_used = set()
        for device in filtered_devices:
            methods_used.update(device.get('discovery_methods', []))
        
        self.discovery_results['discovery_metadata']['scan_methods_used'] = sorted(list(methods_used))
        
        logger.info(f"Consolidamento completato: {len(consolidated_devices)} dispositivi trovati, {len(filtered_devices)} con informazioni utili")
        
        # Log statistiche per metodo
        arp_devices = sum(1 for d in filtered_devices if 'arp' in d.get('discovery_methods', []))
        nmap_devices = sum(1 for d in filtered_devices if 'nmap' in d.get('discovery_methods', []))
        snmp_devices = sum(1 for d in filtered_devices if 'snmp' in d.get('discovery_methods', []))
        
        logger.info(f"Dispositivi con informazioni per metodo - ARP: {arp_devices}, NMAP: {nmap_devices}, SNMP: {snmp_devices}")
    
    def _merge_nmap_data(self, existing_device: Dict[str, Any], 
                        nmap_device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unisce dati NMAP in un dispositivo esistente.
        
        Args:
            existing_device: Dispositivo esistente
            nmap_device: Dati da NMAP scanner
            
        Returns:
            Dispositivo con dati uniti
        """
        # Aggiunge 'nmap' ai metodi di discovery
        discovery_methods = set(existing_device.get('discovery_methods', []))
        discovery_methods.update(nmap_device.get('discovery_methods', []))
        existing_device['discovery_methods'] = sorted(list(discovery_methods))
        
        # Aggiorna informazioni se non già presenti o migliori
        if not existing_device.get('hostname') and nmap_device.get('hostname'):
            existing_device['hostname'] = nmap_device['hostname']
        
        if not existing_device.get('vendor') and nmap_device.get('vendor'):
            existing_device['vendor'] = nmap_device['vendor']
        
        # Aggiorna device_type se NMAP ha identificato meglio
        if (existing_device.get('device_type') == 'unknown' and 
            nmap_device.get('device_type') != 'unknown'):
            existing_device['device_type'] = nmap_device['device_type']
        
        # Unisce informazioni OS
        if nmap_device.get('operating_system'):
            existing_device['operating_system'] = nmap_device['operating_system']
        
        # Unisce servizi
        existing_device['services'] = nmap_device.get('services', [])
        
        # Unisce discovery details
        existing_device['discovery_details']['nmap_discovery'] = nmap_device.get(
            'discovery_details', {}
        ).get('nmap_discovery', {})
        
        # Aggiorna response_time se disponibile
        if nmap_device.get('response_time_ms') is not None:
            existing_device['response_time_ms'] = nmap_device['response_time_ms']
        
        return existing_device
    
    def _merge_snmp_data(self, existing_device: Dict[str, Any], 
                        snmp_device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unisce dati SNMP in un dispositivo esistente.
        
        Args:
            existing_device: Dispositivo esistente
            snmp_device: Dati da SNMP scanner
            
        Returns:
            Dispositivo con dati uniti
        """
        # Aggiunge 'snmp' ai metodi di discovery
        discovery_methods = set(existing_device.get('discovery_methods', []))
        discovery_methods.update(snmp_device.get('discovery_methods', []))
        existing_device['discovery_methods'] = sorted(list(discovery_methods))
        
        # Aggiorna informazioni se migliori da SNMP
        snmp_hostname = snmp_device.get('hostname', '')
        if snmp_hostname and not existing_device.get('hostname'):
            existing_device['hostname'] = snmp_hostname
        
        snmp_vendor = snmp_device.get('vendor', '')
        if snmp_vendor and not existing_device.get('vendor'):
            existing_device['vendor'] = snmp_vendor
        
        # Aggiorna MAC se non presente (dalle interfacce SNMP)
        if not existing_device.get('mac_address') and snmp_device.get('mac_address'):
            existing_device['mac_address'] = snmp_device['mac_address']
        
        # Device type: preferisce network_device se identificato via SNMP
        if snmp_device.get('device_type') == 'network_device':
            existing_device['device_type'] = 'network_device'
        
        # Unisce tutti i dati SNMP
        existing_device['snmp_data'] = snmp_device.get('snmp_data', {})
        
        # Aggiunge servizio SNMP ai servizi
        snmp_services = snmp_device.get('services', [])
        existing_services = existing_device.get('services', [])
        
        # Aggiunge servizio SNMP se non già presente
        snmp_service_exists = any(s.get('service') == 'snmp' for s in existing_services)
        if not snmp_service_exists and snmp_services:
            for service in snmp_services:
                if service.get('service') == 'snmp':
                    existing_services.append(service)
                    break
        
        existing_device['services'] = existing_services
        
        # Unisce discovery details
        existing_device['discovery_details']['snmp_discovery'] = snmp_device.get(
            'discovery_details', {}
        ).get('snmp_discovery', {})
        
        return existing_device
    
    def _finalize_discovery(self) -> None:
        """
        Finalizza la discovery e genera l'output.
        """
        logger.info("=== FASE 5: FINALIZZAZIONE ===")
        
        # Finalizza risultati con statistiche finali
        self.output_manager.finalize_results(self.discovery_results, self.start_time)
        
        # Genera file di output
        try:
            generated_files = self.output_manager.generate_output(self.discovery_results)
            
            logger.info("File di output generati:")
            for file_path in generated_files:
                logger.info(f"  - {file_path}")
                
        except Exception as e:
            logger.error(f"Errore generazione output: {e}")
            self.output_manager.add_error_to_results(self.discovery_results, {
                'error_type': 'output_generation_failed',
                'message': str(e)
            })
    
    def get_scanner_status(self) -> Dict[str, Any]:
        """
        Ottiene lo stato di tutti gli scanner.
        
        Returns:
            Dizionario con stato scanner
        """
        return {
            'arp_scanner': self.arp_scanner.get_scanner_info(),
            'nmap_scanner': self.nmap_scanner.get_scanner_info(), 
            'snmp_scanner': self.snmp_scanner.get_scanner_info()
        }
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Ottiene un riassunto della configurazione.
        
        Returns:
            Riassunto configurazione
        """
        network_config = self.config_manager.get_network_config()
        target_range = network_config.get('target_range')
        configured_excludes = network_config.get('exclude_ranges', [])
        
        # Calcola esclusioni finali (inclusi IP locali)
        final_excludes = []
        if target_range:
            final_excludes = NetworkUtils.exclude_local_ips_from_targets(target_range, configured_excludes)
        
        # Ottieni informazioni rete locali
        network_info = NetworkUtils.get_network_info_summary()
        
        return {
            'scan_id': self.scan_id,
            'config_file': self.config_manager.config_path,
            'target_range': target_range,
            'configured_exclude_ranges': configured_excludes,
            'final_exclude_ranges': final_excludes,
            'local_network_info': network_info,
            'enabled_scanners': [
                name for name, info in self.get_scanner_status().items()
                if info.get('enabled', False)
            ],
            'output_formats': self.output_manager.get_output_files_info()
        }
    
    def _filter_meaningful_devices(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra dispositivi che non hanno informazioni utili.
        
        Un dispositivo è considerato significativo se ha almeno una di queste caratteristiche:
        - Porte aperte
        - Servizi identificati  
        - Dati SNMP utili
        - Hostname risolto (non 'unknown' o vuoto)
        - MAC address conosciuto (non 'unknown' o vuoto)
        - Sistema operativo identificato
        
        Args:
            devices: Lista dispositivi da filtrare
            
        Returns:
            Lista dispositivi filtrati con informazioni utili
        """
        meaningful_devices = []
        
        for device in devices:
            is_meaningful = False
            
            # Controlla MAC address valido
            mac_address = device.get('mac_address', '')
            if mac_address and mac_address not in ['unknown', '', '00:00:00:00:00:00']:
                is_meaningful = True
            
            # Controlla hostname risolto
            hostname = device.get('hostname', '')
            if hostname and hostname not in ['unknown', '', device.get('ip_address', '')]:
                is_meaningful = True
            
            # Controlla porte aperte
            open_ports = device.get('open_ports', [])
            if open_ports and len(open_ports) > 0:
                is_meaningful = True
                
            # Controlla servizi identificati
            services = device.get('services', [])
            if services and len(services) > 0:
                is_meaningful = True
            
            # Controlla dati NMAP utili
            nmap_data = device.get('nmap_data', {})
            if nmap_data:
                # Ha OS detection?
                os_detection = nmap_data.get('os_detection', {})
                if os_detection and os_detection.get('os_matches'):
                    is_meaningful = True
                    
                # Ha script results?
                script_results = nmap_data.get('script_results', {})
                if script_results and any(script_results.values()):
                    is_meaningful = True
                    
                # Ha porte aperte in nmap_data?
                nmap_ports = nmap_data.get('ports', {})
                if nmap_ports and any(nmap_ports.values()):
                    is_meaningful = True
            
            # Controlla dati SNMP utili
            snmp_data = device.get('snmp_data', {})
            if snmp_data and any(v for v in snmp_data.values() if v not in ['', 'unknown', None, {}]):
                is_meaningful = True
            
            # Controlla sistema operativo
            operating_system = device.get('operating_system', {})
            if operating_system and any(v for v in operating_system.values() if v not in ['', 'unknown', None]):
                is_meaningful = True
            
            # Se il dispositivo ha informazioni utili, lo mantiene
            if is_meaningful:
                meaningful_devices.append(device)
            else:
                # Log dei dispositivi scartati per debugging
                logger.debug(f"Dispositivo {device.get('ip_address')} scartato: nessuna informazione utile")
        
        logger.info(f"Filtraggio dispositivi: {len(devices)} totali -> {len(meaningful_devices)} con informazioni utili")
        return meaningful_devices
    
    def __str__(self) -> str:
        """Rappresentazione string del DiscoveryEngine."""
        return f"DiscoveryEngine(scan_id='{self.scan_id}')"
    
    def __repr__(self) -> str:
        """Rappresentazione debug del DiscoveryEngine."""
        enabled_scanners = [
            name for name, info in self.get_scanner_status().items()
            if info.get('enabled', False)
        ]
        return f"DiscoveryEngine(scan_id='{self.scan_id}', scanners={enabled_scanners})"
