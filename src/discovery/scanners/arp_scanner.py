"""
PMI Dashboard EPS - Discovery Engine
ARP Scanner

Implementa la discovery tramite protocollo ARP (Address Resolution Protocol).
Utilizza ping sweep e analisi della tabella ARP per identificare dispositivi attivi.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import subprocess
import platform
import re
import logging
import ipaddress
import concurrent.futures
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
import psutil

logger = logging.getLogger(__name__)

class ARPScanner:
    """
    Scanner ARP per discovery di dispositivi nella rete locale.
    
    Implementa le seguenti funzionalità:
    - Ping sweep per popolare la tabella ARP
    - Lettura e parsing della tabella ARP di sistema
    - Identificazione vendor tramite MAC address OUI
    - Discovery multi-thread per performance ottimali
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inizializza l'ARP Scanner.
        
        Args:
            config: Configurazione ARP dal ConfigManager
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.ping_sweep = config.get('ping_sweep', True)
        self.timeout_seconds = config.get('timeout_seconds', 1)
        self.max_parallel_pings = config.get('max_parallel_pings', 50)
        self.ping_count = config.get('ping_count', 1)
        
        self.platform = platform.system().lower()
        self.discovered_devices: List[Dict[str, Any]] = []
        
        logger.info(f"ARP Scanner inizializzato (abilitato: {self.enabled})")
        logger.debug(f"Configurazione ARP: {self.config}")
    
    def scan(self, target_range: str, exclude_ranges: List[str] = None) -> Dict[str, Any]:
        """
        Esegue la scansione ARP del range specificato.
        
        Args:
            target_range: Range di rete in formato CIDR (es. 192.168.1.0/24)
            exclude_ranges: Lista di range da escludere
            
        Returns:
            Dizionario con risultati dello scan ARP
        """
        if not self.enabled:
            logger.info("ARP Scanner disabilitato nella configurazione")
            return self._create_empty_result()
        
        logger.info(f"Avvio scansione ARP per range: {target_range}")
        start_time = datetime.utcnow()
        
        try:
            # Genera lista IP target
            ip_targets = self._generate_ip_list(target_range, exclude_ranges or [])
            logger.info(f"Identificati {len(ip_targets)} IP da scansionare")
            
            # Esegue ping sweep se configurato
            if self.ping_sweep:
                ping_results = self._execute_ping_sweep(ip_targets)
                logger.info(f"Ping sweep completato: {ping_results['responsive_hosts']} host responsive")
            
            # Legge la tabella ARP
            arp_entries = self._read_arp_table()
            logger.info(f"Letta tabella ARP: {len(arp_entries)} voci")
            
            # Filtra le voci ARP per il range target
            relevant_entries = self._filter_arp_entries(arp_entries, ip_targets)
            logger.info(f"Trovate {len(relevant_entries)} voci ARP rilevanti")
            
            # Crea dispositivi dalla tabella ARP
            devices = self._create_devices_from_arp(relevant_entries)
            
            # Calcola statistiche
            end_time = datetime.utcnow()
            scan_duration = (end_time - start_time).total_seconds()
            
            result = {
                'devices': devices,
                'statistics': {
                    'total_ips_pinged': len(ip_targets) if self.ping_sweep else 0,
                    'ping_responses': ping_results.get('responsive_hosts', 0) if self.ping_sweep else 0,
                    'arp_entries_found': len(relevant_entries),
                    'scan_time_seconds': round(scan_duration, 2),
                    'success_rate': self._calculate_success_rate(len(ip_targets), len(devices))
                },
                'errors': []
            }
            
            logger.info(f"Scansione ARP completata: {len(devices)} dispositivi trovati in {scan_duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Errore durante scansione ARP: {e}")
            return {
                'devices': [],
                'statistics': {'scan_time_seconds': 0, 'error': str(e)},
                'errors': [{'error_type': 'arp_scan_failed', 'message': str(e)}]
            }
    
    def _generate_ip_list(self, target_range: str, exclude_ranges: List[str]) -> List[str]:
        """
        Genera la lista di IP da scansionare.
        
        Args:
            target_range: Range di rete CIDR
            exclude_ranges: Range da escludere
            
        Returns:
            Lista di indirizzi IP come stringhe
        """
        try:
            network = ipaddress.ip_network(target_range, strict=False)
            ip_list = []
            
            # Converte exclude_ranges in set di IP
            excluded_ips = set()
            for exclude_range in exclude_ranges:
                try:
                    if '-' in exclude_range:
                        # Range tipo "192.168.1.100-192.168.1.110"
                        start_ip, end_ip = exclude_range.split('-')
                        start = ipaddress.ip_address(start_ip.strip())
                        end = ipaddress.ip_address(end_ip.strip())
                        
                        current = start
                        while current <= end:
                            excluded_ips.add(str(current))
                            current += 1
                    else:
                        # Range CIDR
                        exclude_network = ipaddress.ip_network(exclude_range, strict=False)
                        excluded_ips.update(str(ip) for ip in exclude_network.hosts())
                except ValueError as e:
                    logger.warning(f"Range exclude non valido ignorato: {exclude_range} - {e}")
            
            # Genera lista IP escludendo quelli nel set excluded_ips
            for ip in network.hosts():
                if str(ip) not in excluded_ips:
                    ip_list.append(str(ip))
            
            logger.debug(f"Generati {len(ip_list)} IP (esclusi {len(excluded_ips)})")
            return ip_list
            
        except ValueError as e:
            logger.error(f"Errore nel parsing del range di rete: {e}")
            raise
    
    def _execute_ping_sweep(self, ip_targets: List[str]) -> Dict[str, Any]:
        """
        Esegue ping sweep parallelo per popolare la tabella ARP.
        
        Args:
            ip_targets: Lista di IP da pingare
            
        Returns:
            Statistiche del ping sweep
        """
        logger.info(f"Inizio ping sweep su {len(ip_targets)} IP")
        
        responsive_hosts = 0
        completed_pings = 0
        
        # Esegue ping in parallelo con ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_pings) as executor:
            # Sottomette tutti i job di ping
            future_to_ip = {
                executor.submit(self._ping_host, ip): ip 
                for ip in ip_targets
            }
            
            # Raccoglie i risultati
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                completed_pings += 1
                
                try:
                    is_responsive = future.result()
                    if is_responsive:
                        responsive_hosts += 1
                        logger.debug(f"Host responsive: {ip}")
                except Exception as e:
                    logger.debug(f"Errore ping {ip}: {e}")
                
                # Log progresso ogni 50 ping
                if completed_pings % 50 == 0:
                    logger.debug(f"Ping progresso: {completed_pings}/{len(ip_targets)}")
        
        logger.info(f"Ping sweep completato: {responsive_hosts}/{len(ip_targets)} host responsive")
        
        return {
            'responsive_hosts': responsive_hosts,
            'total_pings': len(ip_targets),
            'success_rate': (responsive_hosts / len(ip_targets)) * 100 if ip_targets else 0
        }
    
    def _ping_host(self, ip: str) -> bool:
        """
        Esegue ping verso un singolo host.
        
        Args:
            ip: Indirizzo IP da pingare
            
        Returns:
            True se l'host risponde al ping
        """
        try:
            # Determina il comando ping in base al sistema operativo
            if self.platform == 'windows':
                cmd = ['ping', '-n', str(self.ping_count), '-w', str(self.timeout_seconds * 1000), ip]
            else:
                cmd = ['ping', '-c', str(self.ping_count), '-W', str(self.timeout_seconds), ip]
            
            # Esegue il comando sopprimendo l'output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds + 2
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            logger.debug(f"Timeout ping per {ip}")
            return False
        except Exception as e:
            logger.debug(f"Errore ping {ip}: {e}")
            return False
    
    def _read_arp_table(self) -> List[Dict[str, str]]:
        """
        Legge la tabella ARP del sistema.
        
        Returns:
            Lista di dizionari con voci ARP (ip, mac, interface)
        """
        logger.debug("Lettura tabella ARP del sistema")
        
        try:
            if self.platform == 'windows':
                return self._read_arp_table_windows()
            else:
                return self._read_arp_table_unix()
                
        except Exception as e:
            logger.error(f"Errore lettura tabella ARP: {e}")
            return []
    
    def _read_arp_table_windows(self) -> List[Dict[str, str]]:
        """
        Legge la tabella ARP su Windows usando 'arp -a'.
        
        Returns:
            Lista di voci ARP
        """
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"Comando arp fallito: {result.stderr}")
                return []
            
            arp_entries = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                # Cerca pattern: IP_ADDRESS MAC_ADDRESS TYPE
                # Esempio: 192.168.1.1     aa-bb-cc-dd-ee-ff     dynamic
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([a-fA-F0-9\-]{17})', line)
                if match:
                    ip = match.group(1)
                    mac = match.group(2).replace('-', ':').lower()
                    
                    arp_entries.append({
                        'ip': ip,
                        'mac': mac,
                        'interface': 'unknown'  # Windows arp -a non fornisce sempre l'interfaccia
                    })
            
            logger.debug(f"Lette {len(arp_entries)} voci ARP da Windows")
            return arp_entries
            
        except Exception as e:
            logger.error(f"Errore lettura ARP Windows: {e}")
            return []
    
    def _read_arp_table_unix(self) -> List[Dict[str, str]]:
        """
        Legge la tabella ARP su sistemi Unix/Linux da /proc/net/arp.
        
        Returns:
            Lista di voci ARP
        """
        try:
            arp_entries = []
            
            # Prova prima /proc/net/arp (Linux)
            arp_file = '/proc/net/arp'
            if os.path.exists(arp_file):
                with open(arp_file, 'r') as f:
                    lines = f.readlines()[1:]  # Salta header
                    
                    for line in lines:
                        parts = line.strip().split()
                        if len(parts) >= 6:
                            ip = parts[0]
                            mac = parts[3]
                            interface = parts[5]
                            
                            # Verifica che il MAC sia valido (non 00:00:00:00:00:00)
                            if mac != '00:00:00:00:00:00' and ':' in mac:
                                arp_entries.append({
                                    'ip': ip,
                                    'mac': mac.lower(),
                                    'interface': interface
                                })
            else:
                # Fallback: usa comando arp
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        # Cerca pattern vario per sistemi Unix
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+).*?([a-fA-F0-9:]{17})', line)
                        if match:
                            arp_entries.append({
                                'ip': match.group(1),
                                'mac': match.group(2).lower(),
                                'interface': 'unknown'
                            })
            
            logger.debug(f"Lette {len(arp_entries)} voci ARP da Unix")
            return arp_entries
            
        except Exception as e:
            logger.error(f"Errore lettura ARP Unix: {e}")
            return []
    
    def _filter_arp_entries(self, arp_entries: List[Dict[str, str]], 
                           target_ips: List[str]) -> List[Dict[str, str]]:
        """
        Filtra le voci ARP per mantenere solo quelle nel range target.
        
        Args:
            arp_entries: Voci ARP complete
            target_ips: IP target dello scan
            
        Returns:
            Voci ARP filtrate
        """
        target_set = set(target_ips)
        relevant_entries = []
        
        for entry in arp_entries:
            if entry['ip'] in target_set:
                relevant_entries.append(entry)
        
        logger.debug(f"Filtrate {len(relevant_entries)} voci ARP rilevanti")
        return relevant_entries
    
    def _create_devices_from_arp(self, arp_entries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Crea strutture dispositivo dalle voci ARP.
        
        Args:
            arp_entries: Voci ARP filtrate
            
        Returns:
            Lista di dispositivi
        """
        devices = []
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        for entry in arp_entries:
            device = {
                'ip_address': entry['ip'],
                'mac_address': entry['mac'],
                'hostname': self._resolve_hostname(entry['ip']),
                'device_type': 'unknown',
                'vendor': self._get_vendor_from_mac(entry['mac']),
                'discovery_methods': ['arp'],
                'response_time_ms': None,  # ARP non misura response time
                'first_seen': timestamp,
                'last_seen': timestamp,
                'operating_system': {},
                'services': [],
                'snmp_data': {},
                'discovery_details': {
                    'arp_discovery': {
                        'found': True,
                        'method': 'arp_table_lookup',
                        'timestamp': timestamp,
                        'interface': entry.get('interface', 'unknown')
                    }
                }
            }
            
            devices.append(device)
            logger.debug(f"Creato dispositivo ARP: {device['ip_address']} ({device['mac_address']})")
        
        return devices
    
    def _resolve_hostname(self, ip: str) -> str:
        """
        Tenta di risolvere il nome host dell'IP.
        
        Args:
            ip: Indirizzo IP
            
        Returns:
            Nome host o stringa vuota se non risolvibile
        """
        try:
            import socket
            hostname = socket.gethostbyaddr(ip)[0]
            logger.debug(f"Risolto hostname {ip} -> {hostname}")
            return hostname
        except Exception:
            return ""
    
    def _get_vendor_from_mac(self, mac_address: str) -> str:
        """
        Determina il vendor dal MAC address usando OUI.
        
        Args:
            mac_address: Indirizzo MAC in formato XX:XX:XX:XX:XX:XX
            
        Returns:
            Nome vendor o stringa vuota se non identificato
        """
        if not mac_address or len(mac_address) < 8:
            return ""
        
        # Database OUI comuni (primi 3 ottetti)
        oui_database = {
            "00:50:56": "VMware",
            "00:0c:29": "VMware", 
            "00:1c:42": "VMware",
            "08:00:27": "Oracle VirtualBox",
            "00:15:5d": "Microsoft",
            "00:e0:4c": "Cisco",
            "00:1b:0d": "Cisco",
            "cc:46:d6": "Cisco",
            "f8:66:f2": "Cisco",
            "3c:ce:73": "Cisco",
            "00:90:7f": "Cisco",
            "00:25:84": "Apple",
            "28:cf:e9": "Apple", 
            "a4:5e:60": "Apple",
            "ac:de:48": "Apple",
            "00:1f:3c": "Hewlett Packard Enterprise",
            "00:17:08": "Hewlett Packard",
            "70:10:6f": "Hewlett Packard Enterprise",
            "00:24:81": "Dell",
            "d4:ae:52": "Dell",
            "90:b1:1c": "Dell",
            "00:1a:a0": "Netgear",
            "a0:04:60": "Netgear",
            "00:14:6c": "Netgear",
            "00:26:f2": "Netgear"
        }
        
        # Estrae OUI (primi 8 caratteri)
        oui = mac_address[:8].lower()
        vendor = oui_database.get(oui, "")
        
        if vendor:
            logger.debug(f"Identificato vendor {mac_address} -> {vendor}")
        
        return vendor
    
    def _calculate_success_rate(self, total_targets: int, found_devices: int) -> float:
        """
        Calcola il tasso di successo della discovery.
        
        Args:
            total_targets: Numero totale di IP target
            found_devices: Numero di dispositivi trovati
            
        Returns:
            Tasso di successo in percentuale
        """
        if total_targets == 0:
            return 0.0
        
        return round((found_devices / total_targets) * 100, 2)
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """
        Crea una struttura risultati vuota.
        
        Returns:
            Risultati vuoti
        """
        return {
            'devices': [],
            'statistics': {
                'total_ips_pinged': 0,
                'ping_responses': 0, 
                'arp_entries_found': 0,
                'scan_time_seconds': 0,
                'success_rate': 0.0
            },
            'errors': []
        }
    
    def is_enabled(self) -> bool:
        """
        Verifica se il scanner è abilitato.
        
        Returns:
            True se abilitato
        """
        return self.enabled
    
    def get_scanner_info(self) -> Dict[str, Any]:
        """
        Ottiene informazioni sullo scanner.
        
        Returns:
            Dizionario con info scanner
        """
        return {
            'name': 'ARP Scanner',
            'version': '1.0.0',
            'enabled': self.enabled,
            'platform': self.platform,
            'config': self.config
        }
    
    def __str__(self) -> str:
        """Rappresentazione string dell'ARPScanner."""
        return f"ARPScanner(enabled={self.enabled}, platform='{self.platform}')"
    
    def __repr__(self) -> str:
        """Rappresentazione debug dell'ARPScanner."""
        return f"ARPScanner(enabled={self.enabled}, config={self.config})"
