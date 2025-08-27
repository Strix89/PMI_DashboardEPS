"""
PMI Dashboard EPS - Discovery Engine
NMAP Scanner

Implementa la discovery tramite Network Mapper (NMAP).
Esegue host discovery, port scanning, service detection e OS fingerprinting.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import logging
import nmap
import ipaddress
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import re
import socket

logger = logging.getLogger(__name__)

class NMapScanner:
    """
    Scanner NMAP per discovery avanzata di dispositivi e servizi.
    
    Implementa le seguenti funzionalità:
    - Host discovery con multiple tecniche (ICMP, TCP SYN, ARP)
    - Port scanning TCP e UDP
    - Service version detection
    - OS detection e fingerprinting  
    - Script scanning per informazioni aggiuntive
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza l'NMAP Scanner.
        
        Args:
            config: Configurazione NMAP dal ConfigManager
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        
        # Inizializza oggetto NMAP
        try:
            self.nm = nmap.PortScanner()
            logger.info(f"NMAP Scanner inizializzato (versione: {self.nm.nmap_version()})")
        except Exception as e:
            logger.error(f"Errore inizializzazione NMAP: {e}")
            self.enabled = False
            self.nm = None
        
        # Configurazioni specifiche
        self.host_discovery_config = config.get('host_discovery', {})
        self.port_scan_config = config.get('port_scan', {})
        self.service_detection_config = config.get('service_detection', {})
        self.os_detection_config = config.get('os_detection', {})
        self.scripts_config = config.get('scripts', {})
        
        logger.debug(f"Configurazione NMAP: {self.config}")
    
    def scan(self, target_range: str, exclude_ranges: List[str] = None) -> Dict[str, Any]:
        """
        Esegue la scansione NMAP completa del range specificato.
        
        Args:
            target_range: Range di rete in formato CIDR
            exclude_ranges: Lista di range da escludere
            
        Returns:
            Dizionario con risultati dello scan NMAP
        """
        if not self.enabled or not self.nm:
            logger.info("NMAP Scanner disabilitato o non disponibile")
            return self._create_empty_result()
        
        logger.info(f"Avvio scansione NMAP per range: {target_range}")
        start_time = datetime.utcnow()
        
        try:
            # Genera argomenti NMAP
            nmap_args = self._build_nmap_arguments()
            logger.debug(f"Argomenti NMAP: {nmap_args}")
            
            # Prepara target escludendo range specificati
            target_string = self._prepare_targets(target_range, exclude_ranges or [])
            
            # Esegue la scansione
            logger.info(f"Esecuzione scansione NMAP con argomenti: {nmap_args}")
            scan_result = self.nm.scan(hosts=target_string, arguments=nmap_args)
            
            # Elabora i risultati
            devices = self._process_scan_results(scan_result)
            
            # Calcola statistiche
            end_time = datetime.utcnow()
            scan_duration = (end_time - start_time).total_seconds()
            statistics = self._calculate_statistics(scan_result, scan_duration)
            
            result = {
                'devices': devices,
                'statistics': statistics,
                'errors': []
            }
            
            logger.info(f"Scansione NMAP completata: {len(devices)} dispositivi trovati in {scan_duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Errore durante scansione NMAP: {e}")
            return {
                'devices': [],
                'statistics': {'scan_time_seconds': 0, 'error': str(e)},
                'errors': [{'error_type': 'nmap_scan_failed', 'message': str(e)}]
            }
    
    def _build_nmap_arguments(self) -> str:
        """
        Costruisce la stringa di argomenti per NMAP.
        
        Returns:
            Stringa argomenti NMAP
        """
        args = []
        
        # Timing template
        timing = self.config.get('port_scan', {}).get('timing_template', 4)
        args.append(f'-T{timing}')
        
        # Host discovery e Port scanning (non possiamo usare -sn con port scan)
        port_scan_enabled = self.port_scan_config.get('enabled', True)
        
        if port_scan_enabled:
            # Se il port scanning è abilitato, facciamo tutto insieme
            scan_type = self.port_scan_config.get('scan_type', 'syn')
            
            # Determina i tipi di scansione necessari
            tcp_ports = self.port_scan_config.get('tcp_ports', [])
            udp_ports = self.port_scan_config.get('udp_ports', [])
            
            # Costruisce la stringa delle porte combinando TCP e UDP
            port_specs = []
            
            # Aggiunge porte TCP
            if tcp_ports:
                tcp_port_string = ','.join(tcp_ports)
                port_specs.append(f'T:{tcp_port_string}')
            
            # Aggiunge porte UDP
            if udp_ports:
                udp_port_string = ','.join(udp_ports)
                port_specs.append(f'U:{udp_port_string}')
            
            # Se abbiamo porte da scansionare
            if port_specs:
                # Determina il tipo di scansione
                if tcp_ports and udp_ports:
                    # Scansione mista TCP+UDP
                    args.append('-sS')  # TCP SYN scan
                    args.append('-sU')  # UDP scan
                elif scan_type == 'syn' or (tcp_ports and not udp_ports):
                    args.append('-sS')
                elif scan_type == 'connect':
                    args.append('-sT')
                elif scan_type == 'udp' or (udp_ports and not tcp_ports):
                    args.append('-sU')
                
                # Singola opzione -p con tutte le porte
                combined_ports = ','.join(port_specs)
                args.append(f'-p {combined_ports}')
        else:
            # Solo host discovery senza port scanning
            if self.host_discovery_config.get('methods'):
                methods = self.host_discovery_config['methods']
                if 'ping' in methods:
                    args.append('-sn')  # Ping scan only per host discovery
        
        # Service detection - Migliorato
        if self.service_detection_config.get('enabled', True):
            args.append('-sV')
            
            version_intensity = self.service_detection_config.get('version_intensity', 7)
            args.append(f'--version-intensity {version_intensity}')
            
            if self.service_detection_config.get('version_light', False):
                args.append('--version-light')
                
            if self.service_detection_config.get('version_all', False):
                args.append('--version-all')
                
            if self.service_detection_config.get('probe_all_ports', False):
                args.append('--allports')
        
        # OS detection - Migliorato
        if self.os_detection_config.get('enabled', True):
            args.append('-O')
            
            if self.os_detection_config.get('osscan_limit', True):
                args.append('--osscan-limit')
            else:
                # Forza OS detection anche con poche informazioni
                args.append('--osscan-guess')
                
            if self.os_detection_config.get('aggressive', False):
                args.append('-A')  # Abilita detection aggressivo
                
            if self.os_detection_config.get('osscan_guess', False):
                args.append('--osscan-guess')
        
        # Script scanning
        if self.scripts_config.get('enabled', True):
            categories = self.scripts_config.get('categories', ['default', 'safe'])
            if categories:
                script_string = ','.join(categories)
                args.append(f'--script {script_string}')
            
            custom_scripts = self.scripts_config.get('custom_scripts', [])
            if custom_scripts:
                custom_string = ','.join(custom_scripts)
                args.append(f'--script {custom_string}')
        
        # Performance settings
        max_parallelism = self.port_scan_config.get('max_parallelism', 100)
        args.append(f'--max-parallelism {max_parallelism}')
        
        timeout = self.port_scan_config.get('timeout', '10s')
        args.append(f'--host-timeout {timeout}')
        
        max_retries = self.port_scan_config.get('max_retries', 2)
        args.append(f'--max-retries {max_retries}')
        
        # Output verbose per debugging
        args.append('-v')
        
        return ' '.join(args)
    
    def _prepare_targets(self, target_range: str, exclude_ranges: List[str]) -> str:
        """
        Prepara la stringa target per NMAP.
        
        Args:
            target_range: Range principale
            exclude_ranges: Range da escludere
            
        Returns:
            Stringa target per NMAP
        """
        target_string = target_range
        
        if exclude_ranges:
            exclude_string = ','.join(exclude_ranges)
            target_string += f' --exclude {exclude_string}'
        
        return target_string
    
    def _process_scan_results(self, scan_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Elabora i risultati raw di NMAP in dispositivi strutturati.
        
        Args:
            scan_result: Risultati raw da NMAP
            
        Returns:
            Lista di dispositivi elaborati
        """
        devices = []
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        if 'scan' not in scan_result:
            logger.warning("Nessun risultato scan trovato in NMAP")
            return devices
        
        for ip, host_data in scan_result['scan'].items():
            try:
                device = self._create_device_from_host(ip, host_data, timestamp)
                devices.append(device)
                logger.debug(f"Processato dispositivo NMAP: {ip}")
            except Exception as e:
                logger.error(f"Errore processamento host {ip}: {e}")
                continue
        
        return devices
    
    def _create_device_from_host(self, ip: str, host_data: Dict[str, Any], 
                                timestamp: str) -> Dict[str, Any]:
        """
        Crea una struttura dispositivo dai dati NMAP di un host.
        
        Args:
            ip: Indirizzo IP
            host_data: Dati host da NMAP
            timestamp: Timestamp della discovery
            
        Returns:
            Struttura dispositivo
        """
        # Informazioni base
        device = {
            'ip_address': ip,
            'mac_address': self._extract_mac_address(host_data),
            'hostname': self._extract_hostname(host_data, ip),
            'device_type': self._guess_device_type(host_data),
            'vendor': self._extract_vendor(host_data),
            'discovery_methods': ['nmap'],
            'response_time_ms': None,
            'first_seen': timestamp,
            'last_seen': timestamp,
            'operating_system': self._extract_os_info(host_data),
            'services': self._extract_services(host_data),
            'snmp_data': {},
            'discovery_details': {
                'nmap_discovery': {
                    'host_up': host_data.get('status', {}).get('state') == 'up',
                    'scan_duration_ms': None,
                    'ports_scanned': self._count_scanned_ports(host_data),
                    'open_ports': self._count_open_ports(host_data),
                    'os_detection_confidence': self._get_os_confidence(host_data)
                }
            }
        }
        
        return device
    
    def _extract_mac_address(self, host_data: Dict[str, Any]) -> str:
        """
        Estrae l'indirizzo MAC dai dati host.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Indirizzo MAC o stringa vuota
        """
        addresses = host_data.get('addresses', {})
        return addresses.get('mac', '').lower()
    
    def _extract_hostname(self, host_data: Dict[str, Any], ip: str) -> str:
        """
        Estrae il nome host dai dati NMAP o tramite reverse DNS.
        
        Args:
            host_data: Dati host NMAP
            ip: Indirizzo IP
            
        Returns:
            Nome host o stringa vuota
        """
        # Prova prima dai dati NMAP
        hostnames = host_data.get('hostnames', [])
        if hostnames and len(hostnames) > 0:
            hostname = hostnames[0].get('name', '')
            if hostname:
                return hostname
        
        # Fallback: reverse DNS
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return ""
    
    def _extract_vendor(self, host_data: Dict[str, Any]) -> str:
        """
        Estrae informazioni vendor dai dati NMAP.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Nome vendor o stringa vuota
        """
        # Prova dal MAC vendor
        vendor = host_data.get('vendor', {})
        if vendor:
            mac_address = self._extract_mac_address(host_data)
            return vendor.get(mac_address, '')
        
        # Prova dall'OS detection
        os_data = host_data.get('osmatch', [])
        if os_data and len(os_data) > 0:
            os_name = os_data[0].get('name', '')
            # Estrae vendor comune dai nomi OS
            if 'cisco' in os_name.lower():
                return 'Cisco'
            elif 'juniper' in os_name.lower():
                return 'Juniper'
            elif 'hp' in os_name.lower() or 'hewlett' in os_name.lower():
                return 'HP'
            elif 'dell' in os_name.lower():
                return 'Dell'
        
        return ""
    
    def _extract_os_info(self, host_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae informazioni sistema operativo.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Dizionario con informazioni OS
        """
        os_info = {}
        
        osmatch = host_data.get('osmatch', [])
        if osmatch and len(osmatch) > 0:
            best_match = osmatch[0]
            os_info = {
                'name': best_match.get('name', ''),
                'accuracy': best_match.get('accuracy', 0),
                'confidence': best_match.get('accuracy', 0),
                'cpe': []
            }
            
            # Estrae CPE (Common Platform Enumeration) 
            osclass = best_match.get('osclass', [])
            if osclass and len(osclass) > 0:
                cpe_list = osclass[0].get('cpe', [])
                os_info['cpe'] = cpe_list
        
        return os_info
    
    def _extract_services(self, host_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Estrae informazioni sui servizi dalle porte aperte.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Lista di servizi
        """
        services = []
        
        # Processa porte TCP
        tcp_ports = host_data.get('tcp', {})
        for port, port_data in tcp_ports.items():
            service = self._create_service_from_port('tcp', port, port_data)
            services.append(service)
        
        # Processa porte UDP
        udp_ports = host_data.get('udp', {})
        for port, port_data in udp_ports.items():
            service = self._create_service_from_port('udp', port, port_data)
            services.append(service)
        
        return services
    
    def _create_service_from_port(self, protocol: str, port: int, 
                                 port_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una struttura servizio dai dati porta NMAP.
        
        Args:
            protocol: Protocollo (tcp/udp)
            port: Numero porta
            port_data: Dati porta da NMAP
            
        Returns:
            Struttura servizio
        """
        service = {
            'port': port,
            'protocol': protocol,
            'service': port_data.get('name', 'unknown'),
            'version': self._extract_service_version(port_data),
            'state': port_data.get('state', 'unknown'),
            'banner': self._extract_banner(port_data),
            'cpe': port_data.get('cpe', [])
        }
        
        return service
    
    def _extract_service_version(self, port_data: Dict[str, Any]) -> str:
        """
        Estrae versione servizio dai dati porta.
        
        Args:
            port_data: Dati porta NMAP
            
        Returns:
            Stringa versione
        """
        product = port_data.get('product', '')
        version = port_data.get('version', '')
        extrainfo = port_data.get('extrainfo', '')
        
        # Combina le informazioni disponibili
        version_parts = [product, version, extrainfo]
        version_string = ' '.join(part for part in version_parts if part)
        
        return version_string
    
    def _extract_banner(self, port_data: Dict[str, Any]) -> str:
        """
        Estrae banner/intestazione servizio.
        
        Args:
            port_data: Dati porta NMAP
            
        Returns:
            Banner o stringa vuota
        """
        # NMAP può fornire banner in vari campi
        banner_fields = ['product', 'version', 'extrainfo', 'script']
        
        for field in banner_fields:
            banner = port_data.get(field, '')
            if banner and isinstance(banner, str):
                return banner
        
        return ""
    
    def _guess_device_type(self, host_data: Dict[str, Any]) -> str:
        """
        Tenta di identificare il tipo di dispositivo.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Tipo dispositivo stimato
        """
        # Analizza i servizi aperti per inferire il tipo
        services = self._extract_services(host_data)
        open_ports = [s['port'] for s in services if s['state'] == 'open']
        
        # Router/Network device
        if 161 in open_ports:  # SNMP
            if any(port in open_ports for port in [22, 23, 80, 443]):  # Management
                return "network_device"
        
        # Web server
        if any(port in open_ports for port in [80, 443, 8080, 8443]):
            return "web_server"
        
        # Mail server
        if any(port in open_ports for port in [25, 110, 143, 993, 995]):
            return "mail_server"
        
        # Database server
        if any(port in open_ports for port in [3306, 5432, 1433, 1521]):
            return "database_server"
        
        # Printer
        if any(port in open_ports for port in [515, 631, 9100]):
            return "printer"
        
        # Desktop/Workstation
        if any(port in open_ports for port in [135, 139, 445, 3389]):  # Windows
            return "workstation"
        
        if 22 in open_ports and len(open_ports) < 5:  # Linux/Unix con pochi servizi
            return "workstation"
        
        return "unknown"
    
    def _count_scanned_ports(self, host_data: Dict[str, Any]) -> int:
        """
        Conta il numero totale di porte scansionate.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Numero porte scansionate
        """
        tcp_ports = len(host_data.get('tcp', {}))
        udp_ports = len(host_data.get('udp', {}))
        return tcp_ports + udp_ports
    
    def _count_open_ports(self, host_data: Dict[str, Any]) -> int:
        """
        Conta il numero di porte aperte.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Numero porte aperte
        """
        open_count = 0
        
        # Conta porte TCP aperte
        for port_data in host_data.get('tcp', {}).values():
            if port_data.get('state') == 'open':
                open_count += 1
        
        # Conta porte UDP aperte
        for port_data in host_data.get('udp', {}).values():
            if port_data.get('state') == 'open':
                open_count += 1
        
        return open_count
    
    def _get_os_confidence(self, host_data: Dict[str, Any]) -> int:
        """
        Ottiene confidence dell'OS detection.
        
        Args:
            host_data: Dati host NMAP
            
        Returns:
            Confidence percentage (0-100)
        """
        osmatch = host_data.get('osmatch', [])
        if osmatch and len(osmatch) > 0:
            return osmatch[0].get('accuracy', 0)
        return 0
    
    def _calculate_statistics(self, scan_result: Dict[str, Any], 
                            scan_duration: float) -> Dict[str, Any]:
        """
        Calcola statistiche della scansione.
        
        Args:
            scan_result: Risultati raw NMAP
            scan_duration: Durata scansione in secondi
            
        Returns:
            Dizionario statistiche
        """
        stats = scan_result.get('nmap', {})
        hosts_data = scan_result.get('scan', {})
        
        total_hosts = len(hosts_data)
        responsive_hosts = sum(1 for host in hosts_data.values() 
                             if host.get('status', {}).get('state') == 'up')
        
        total_ports = sum(self._count_scanned_ports(host) for host in hosts_data.values())
        open_ports = sum(self._count_open_ports(host) for host in hosts_data.values())
        
        services_identified = sum(len(self._extract_services(host)) for host in hosts_data.values())
        
        os_fingerprints = sum(1 for host in hosts_data.values() 
                            if host.get('osmatch') and len(host['osmatch']) > 0)
        
        statistics = {
            'total_hosts_targeted': total_hosts,
            'responsive_hosts': responsive_hosts,
            'total_ports_scanned': total_ports,
            'open_ports_found': open_ports,
            'services_identified': services_identified,
            'os_fingerprints': os_fingerprints,
            'scan_time_seconds': round(scan_duration, 2),
            'nmap_version': stats.get('version', 'unknown'),
            'command_line': stats.get('command_line', ''),
            'scan_info': stats.get('scaninfo', {})
        }
        
        return statistics
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """
        Crea una struttura risultati vuota.
        
        Returns:
            Risultati vuoti
        """
        return {
            'devices': [],
            'statistics': {
                'total_hosts_targeted': 0,
                'responsive_hosts': 0,
                'total_ports_scanned': 0,
                'open_ports_found': 0,
                'services_identified': 0,
                'os_fingerprints': 0,
                'scan_time_seconds': 0
            },
            'errors': []
        }
    
    def is_enabled(self) -> bool:
        """
        Verifica se il scanner è abilitato.
        
        Returns:
            True se abilitato
        """
        return self.enabled and self.nm is not None
    
    def get_nmap_version(self) -> str:
        """
        Ottiene la versione di NMAP.
        
        Returns:
            Stringa versione NMAP
        """
        if self.nm:
            return '.'.join(map(str, self.nm.nmap_version()))
        return "Not available"
    
    def get_scanner_info(self) -> Dict[str, Any]:
        """
        Ottiene informazioni sullo scanner.
        
        Returns:
            Dizionario con info scanner
        """
        return {
            'name': 'NMAP Scanner',
            'version': '1.0.0',
            'enabled': self.enabled,
            'nmap_version': self.get_nmap_version(),
            'config': self.config
        }
    
    def __str__(self) -> str:
        """Rappresentazione string dell'NMapScanner."""
        return f"NMapScanner(enabled={self.enabled}, nmap_version='{self.get_nmap_version()}')"
    
    def __repr__(self) -> str:
        """Rappresentazione debug dell'NMapScanner."""
        return f"NMapScanner(enabled={self.enabled}, config={self.config})"
