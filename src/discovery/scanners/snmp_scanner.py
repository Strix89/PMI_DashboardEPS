"""
PMI Dashboard EPS - Discovery Engine
SNMP Scanner

Implementa la discovery tramite Simple Network Management Protocol (SNMP v1/v2c).
Raccoglie informazioni di sistema, interfacce e metriche di performance.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import concurrent.futures
import time

# Importazioni SNMP
try:
    from pysnmp.hlapi import *
    from pysnmp.carrier.asyncio import dispatch
    from pysnmp import debug
    SNMP_AVAILABLE = True
except ImportError:
    logger.warning("pysnmp non disponibile - SNMP Scanner disabilitato")
    SNMP_AVAILABLE = False

logger = logging.getLogger(__name__)

class SNMPScanner:
    """
    Scanner SNMP per raccolta informazioni dettagliate da dispositivi di rete.
    
    Implementa le seguenti funzionalità:
    - Test connettività SNMP e community string
    - Raccolta informazioni di sistema (sysDescr, sysName, etc.)
    - Walk delle interfacce di rete con statistiche
    - Raccolta metriche di performance (CPU, memoria, temperatura)
    - Supporto per OID vendor-specific (Cisco, HP, etc.)
    """
    
    def __init__(self, config: Dict[str, Any], oids_config: Dict[str, Any]):
        """
        Inizializza l'SNMP Scanner.
        
        Args:
            config: Configurazione SNMP dal ConfigManager
            oids_config: Configurazione OID dal ConfigManager
        """
        self.config = config
        self.oids_config = oids_config
        self.enabled = config.get('enabled', True) and SNMP_AVAILABLE
        
        if not SNMP_AVAILABLE:
            self.enabled = False
            logger.error("SNMP Scanner disabilitato: pysnmp non disponibile")
            return
        
        # Configurazioni SNMP
        self.port = config.get('port', 161)
        self.timeout = config.get('timeout_seconds', 5)
        self.retries = config.get('retries', 3)
        self.max_parallel = config.get('max_parallel', 20)
        self.versions = config.get('versions', ['2c', '1'])
        self.communities = config.get('communities', ['public'])
        
        # OID configurations
        self.system_oids = oids_config.get('standard', {}).get('system', {})
        self.interface_oids = oids_config.get('standard', {}).get('interfaces', {})
        self.vendor_oids = oids_config.get('vendor', {})
        
        logger.info(f"SNMP Scanner inizializzato (abilitato: {self.enabled})")
        logger.debug(f"Community strings: {len(self.communities)}, Versioni: {self.versions}")
    
    def scan(self, target_hosts: List[str]) -> Dict[str, Any]:
        """
        Esegue la scansione SNMP su una lista di host.
        
        Args:
            target_hosts: Lista di indirizzi IP da scansionare
            
        Returns:
            Dizionario con risultati dello scan SNMP
        """
        if not self.enabled:
            logger.info("SNMP Scanner disabilitato")
            return self._create_empty_result()
        
        logger.info(f"Avvio scansione SNMP su {len(target_hosts)} host")
        start_time = datetime.utcnow()
        
        devices = []
        errors = []
        snmp_responsive = 0
        v1_accessible = 0
        v2c_accessible = 0
        total_oids_collected = 0
        
        # Esegue scansioni in parallelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            # Sottomette job per ogni host
            future_to_host = {
                executor.submit(self._scan_single_host, host): host 
                for host in target_hosts
            }
            
            # Raccoglie risultati
            for future in concurrent.futures.as_completed(future_to_host):
                host = future_to_host[future]
                
                try:
                    host_result = future.result()
                    
                    if host_result['device']:
                        devices.append(host_result['device'])
                        snmp_responsive += 1
                        
                        # Conta versioni SNMP
                        snmp_version = host_result['device'].get('snmp_data', {}).get('version', '')
                        if snmp_version == '1':
                            v1_accessible += 1
                        elif snmp_version == '2c':
                            v2c_accessible += 1
                        
                        # Conta OID raccolti
                        oids_collected = host_result.get('oids_collected', 0)
                        total_oids_collected += oids_collected
                    
                    if host_result['errors']:
                        errors.extend(host_result['errors'])
                        
                except Exception as e:
                    logger.error(f"Errore processamento risultato SNMP {host}: {e}")
                    errors.append({
                        'host': host,
                        'error_type': 'processing_error',
                        'message': str(e)
                    })
        
        # Calcola statistiche finali
        end_time = datetime.utcnow()
        scan_duration = (end_time - start_time).total_seconds()
        
        result = {
            'devices': devices,
            'statistics': {
                'hosts_tested': len(target_hosts),
                'snmp_responsive': snmp_responsive,
                'v1_accessible': v1_accessible,
                'v2c_accessible': v2c_accessible,
                'total_oids_collected': total_oids_collected,
                'communities_tested': self.communities,
                'scan_time_seconds': round(scan_duration, 2)
            },
            'errors': errors
        }
        
        logger.info(f"Scansione SNMP completata: {snmp_responsive}/{len(target_hosts)} host accessibili")
        return result
    
    def _scan_single_host(self, host: str) -> Dict[str, Any]:
        """
        Esegue la scansione SNMP su un singolo host.
        
        Args:
            host: Indirizzo IP dell'host
            
        Returns:
            Dizionario con risultati per l'host
        """
        logger.debug(f"Scansione SNMP host: {host}")
        
        result = {
            'device': None,
            'errors': [],
            'oids_collected': 0
        }
        
        try:
            # Test connettività SNMP e trova community valida
            snmp_info = self._test_snmp_connectivity(host)
            
            if not snmp_info['accessible']:
                logger.debug(f"Host {host} non accessibile via SNMP")
                return result
            
            # Raccoglie dati SNMP
            device_data = self._collect_snmp_data(host, snmp_info)
            
            if device_data:
                result['device'] = device_data
                result['oids_collected'] = device_data.get('snmp_data', {}).get('oids_collected', 0)
                
        except Exception as e:
            logger.error(f"Errore scansione SNMP {host}: {e}")
            result['errors'].append({
                'host': host,
                'error_type': 'snmp_scan_error',
                'message': str(e)
            })
        
        return result
    
    def _test_snmp_connectivity(self, host: str) -> Dict[str, Any]:
        """
        Testa la connettività SNMP e trova una community valida.
        
        Args:
            host: Indirizzo IP
            
        Returns:
            Informazioni connettività SNMP
        """
        snmp_info = {
            'accessible': False,
            'version': None,
            'community': None,
            'response_time_ms': None
        }
        
        # Testa ogni versione SNMP configurata
        for version in self.versions:
            for community in self.communities:
                try:
                    start_time = time.time()
                    
                    # Test con sysDescr (OID standard sempre presente)
                    sys_descr_oid = self.system_oids.get('sysDescr', {}).get('oid', '1.3.6.1.2.1.1.1.0')
                    
                    result = self._snmp_get(host, sys_descr_oid, version, community)
                    
                    if result is not None:
                        response_time = (time.time() - start_time) * 1000
                        
                        snmp_info = {
                            'accessible': True,
                            'version': version,
                            'community': community,
                            'response_time_ms': round(response_time, 2)
                        }
                        
                        logger.debug(f"SNMP accessibile {host} - v{version}/{community}")
                        return snmp_info
                        
                except Exception as e:
                    logger.debug(f"Test SNMP fallito {host} v{version}/{community}: {e}")
                    continue
        
        return snmp_info
    
    def _collect_snmp_data(self, host: str, snmp_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Raccoglie tutti i dati SNMP da un host.
        
        Args:
            host: Indirizzo IP
            snmp_info: Informazioni connettività SNMP
            
        Returns:
            Struttura dispositivo con dati SNMP
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'
        version = snmp_info['version']
        community = snmp_info['community']
        oids_collected = 0
        
        # Struttura dispositivo base
        device = {
            'ip_address': host,
            'mac_address': '',
            'hostname': '',
            'device_type': 'network_device',
            'vendor': '',
            'discovery_methods': ['snmp'],
            'response_time_ms': snmp_info['response_time_ms'],
            'first_seen': timestamp,
            'last_seen': timestamp,
            'operating_system': {},
            'services': [
                {
                    'port': self.port,
                    'protocol': 'udp',
                    'service': 'snmp',
                    'version': f'SNMPv{version}',
                    'state': 'open',
                    'community': community if not self.config.get('security', {}).get('mask_communities_in_output', True) else '***'
                }
            ],
            'snmp_data': {
                'accessible': True,
                'version': version,
                'community': community if not self.config.get('security', {}).get('mask_communities_in_output', True) else '***',
                'system_info': {},
                'interfaces': [],
                'performance_metrics': {},
                'vendor_data': {},
                'oids_collected': 0
            },
            'discovery_details': {
                'snmp_discovery': {
                    'accessible': True,
                    'community_found': community if not self.config.get('security', {}).get('mask_communities_in_output', True) else '***',
                    'oids_collected': 0,
                    'walk_duration_ms': 0
                }
            }
        }
        
        walk_start_time = time.time()
        
        try:
            # Raccoglie informazioni di sistema
            system_info, sys_oids = self._collect_system_info(host, version, community)
            device['snmp_data']['system_info'] = system_info
            oids_collected += sys_oids
            
            # Aggiorna informazioni dispositivo da SNMP
            device['hostname'] = system_info.get('sysName', '')
            device['vendor'] = self._guess_vendor_from_snmp(system_info)
            
            # Raccoglie informazioni interfacce
            interfaces, if_oids = self._collect_interface_info(host, version, community)
            device['snmp_data']['interfaces'] = interfaces
            oids_collected += if_oids
            
            # Estrae MAC address dalla prima interfaccia
            if interfaces:
                for interface in interfaces:
                    mac = interface.get('ifPhysAddress', '')
                    if mac and mac != '00:00:00:00:00:00':
                        device['mac_address'] = mac
                        break
            
            # Raccoglie metriche di performance
            perf_metrics, perf_oids = self._collect_performance_metrics(host, version, community, system_info)
            device['snmp_data']['performance_metrics'] = perf_metrics
            oids_collected += perf_oids
            
            # Raccoglie dati vendor-specific
            vendor_data, vendor_oids = self._collect_vendor_data(host, version, community, device['vendor'])
            device['snmp_data']['vendor_data'] = vendor_data
            oids_collected += vendor_oids
            
        except Exception as e:
            logger.error(f"Errore raccolta dati SNMP {host}: {e}")
            return None
        
        # Finalizza statistiche
        walk_duration = (time.time() - walk_start_time) * 1000
        device['snmp_data']['oids_collected'] = oids_collected
        device['discovery_details']['snmp_discovery']['oids_collected'] = oids_collected
        device['discovery_details']['snmp_discovery']['walk_duration_ms'] = round(walk_duration, 2)
        
        logger.debug(f"Dati SNMP raccolti {host}: {oids_collected} OID in {walk_duration:.2f}ms")
        return device
    
    def _collect_system_info(self, host: str, version: str, community: str) -> Tuple[Dict[str, Any], int]:
        """
        Raccoglie informazioni di sistema SNMP.
        
        Args:
            host: Indirizzo IP
            version: Versione SNMP
            community: Community string
            
        Returns:
            Tupla (informazioni_sistema, numero_oids_raccolti)
        """
        system_info = {}
        oids_collected = 0
        
        for key, oid_data in self.system_oids.items():
            try:
                oid = oid_data.get('oid')
                if not oid:
                    continue
                
                value = self._snmp_get(host, oid, version, community)
                if value is not None:
                    # Elabora valori specifici
                    if key == 'sysUpTime':
                        # Converte ticks in formato leggibile
                        if isinstance(value, int):
                            system_info[key] = value
                            system_info['sysUpTimeFormatted'] = self._format_uptime(value)
                        else:
                            system_info[key] = str(value)
                    else:
                        system_info[key] = str(value)
                    
                    oids_collected += 1
                    
            except Exception as e:
                logger.debug(f"Errore raccolta {key} da {host}: {e}")
                continue
        
        return system_info, oids_collected
    
    def _collect_interface_info(self, host: str, version: str, community: str) -> Tuple[List[Dict[str, Any]], int]:
        """
        Raccoglie informazioni sulle interfacce di rete.
        
        Args:
            host: Indirizzo IP
            version: Versione SNMP  
            community: Community string
            
        Returns:
            Tupla (lista_interfacce, numero_oids_raccolti)
        """
        interfaces = []
        oids_collected = 0
        
        try:
            # Prima determina il numero di interfacce
            if_number_oid = self.interface_oids.get('ifNumber', {}).get('oid', '1.3.6.1.2.1.2.1.0')
            if_count = self._snmp_get(host, if_number_oid, version, community)
            
            if if_count is None:
                return interfaces, oids_collected
            
            oids_collected += 1
            interface_count = int(if_count) if isinstance(if_count, (int, str)) else 0
            
            if interface_count == 0:
                return interfaces, oids_collected
            
            # Raccoglie dati per ogni interfaccia
            interface_oids = {
                'ifIndex': '1.3.6.1.2.1.2.2.1.1',
                'ifDescr': '1.3.6.1.2.1.2.2.1.2', 
                'ifType': '1.3.6.1.2.1.2.2.1.3',
                'ifMtu': '1.3.6.1.2.1.2.2.1.4',
                'ifSpeed': '1.3.6.1.2.1.2.2.1.5',
                'ifPhysAddress': '1.3.6.1.2.1.2.2.1.6',
                'ifAdminStatus': '1.3.6.1.2.1.2.2.1.7',
                'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',
                'ifInOctets': '1.3.6.1.2.1.2.2.1.10',
                'ifOutOctets': '1.3.6.1.2.1.2.2.1.16',
                'ifInErrors': '1.3.6.1.2.1.2.2.1.14',
                'ifOutErrors': '1.3.6.1.2.1.2.2.1.20'
            }
            
            # Raccoglie dati per ogni indice interfaccia
            for if_index in range(1, min(interface_count + 1, 50)):  # Limita a 50 interfacce
                interface_data = {'ifIndex': if_index}
                
                for field, base_oid in interface_oids.items():
                    if field == 'ifIndex':
                        continue
                    
                    try:
                        oid = f"{base_oid}.{if_index}"
                        value = self._snmp_get(host, oid, version, community)
                        
                        if value is not None:
                            # Elabora valore in base al tipo
                            if field == 'ifPhysAddress' and isinstance(value, bytes):
                                # Converte MAC address da bytes
                                mac = ':'.join(f'{b:02x}' for b in value)
                                interface_data[field] = mac.lower()
                            elif field in ['ifInOctets', 'ifOutOctets', 'ifInErrors', 'ifOutErrors']:
                                # Contatori - converte in int
                                interface_data[field] = int(value) if isinstance(value, (int, str)) else 0
                            else:
                                interface_data[field] = str(value)
                            
                            oids_collected += 1
                    
                    except Exception as e:
                        logger.debug(f"Errore raccolta {field}.{if_index} da {host}: {e}")
                        continue
                
                # Aggiunge interfaccia solo se ha dati significativi
                if len(interface_data) > 2:  # Più di solo ifIndex
                    interfaces.append(interface_data)
            
        except Exception as e:
            logger.error(f"Errore raccolta interfacce da {host}: {e}")
        
        return interfaces, oids_collected
    
    def _collect_performance_metrics(self, host: str, version: str, community: str, 
                                   system_info: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Raccoglie metriche di performance del dispositivo.
        
        Args:
            host: Indirizzo IP
            version: Versione SNMP
            community: Community string
            system_info: Informazioni di sistema già raccolte
            
        Returns:
            Tupla (metriche, numero_oids_raccolti)
        """
        metrics = {}
        oids_collected = 0
        
        # OID per metriche di performance dal config
        perf_config = self.config.get('oids', {}).get('performance', {})
        
        if not perf_config.get('enabled', True):
            return metrics, oids_collected
        
        # CPU utilization
        cpu_oids = perf_config.get('cpu_oids', [])
        for cpu_oid in cpu_oids:
            try:
                value = self._snmp_get(host, cpu_oid, version, community)
                if value is not None:
                    cpu_value = float(value) if isinstance(value, (int, str)) else 0.0
                    if 'cpu_utilization' not in metrics:
                        metrics['cpu_utilization_5min'] = cpu_value
                        oids_collected += 1
                        break  # Usa il primo OID che risponde
            except Exception as e:
                logger.debug(f"Errore raccolta CPU {cpu_oid} da {host}: {e}")
                continue
        
        # Memory utilization  
        memory_oids = perf_config.get('memory_oids', [])
        memory_values = {}
        
        for memory_oid in memory_oids:
            try:
                value = self._snmp_get(host, memory_oid, version, community)
                if value is not None:
                    memory_value = int(value) if isinstance(value, (int, str)) else 0
                    memory_values[memory_oid] = memory_value
                    oids_collected += 1
            except Exception as e:
                logger.debug(f"Errore raccolta memoria {memory_oid} da {host}: {e}")
                continue
        
        # Calcola percentuali memoria se disponibili valori used/free
        if len(memory_values) >= 2:
            values = list(memory_values.values())
            if len(values) == 2:
                # Assume used, free o free, used
                total = sum(values)
                if total > 0:
                    metrics['memory_pool_used'] = round((values[0] / total) * 100, 2)
                    metrics['memory_pool_free'] = round((values[1] / total) * 100, 2)
        
        return metrics, oids_collected
    
    def _collect_vendor_data(self, host: str, version: str, community: str, 
                           vendor: str) -> Tuple[Dict[str, Any], int]:
        """
        Raccoglie dati vendor-specific.
        
        Args:
            host: Indirizzo IP
            version: Versione SNMP
            community: Community string
            vendor: Vendor identificato
            
        Returns:
            Tupla (dati_vendor, numero_oids_raccolti)
        """
        vendor_data = {}
        oids_collected = 0
        
        if not vendor:
            return vendor_data, oids_collected
        
        vendor_lower = vendor.lower()
        vendor_configs = self.vendor_oids
        
        # Cerca configurazione vendor
        vendor_config = None
        if 'cisco' in vendor_lower:
            vendor_config = vendor_configs.get('cisco', {})
        elif 'hp' in vendor_lower or 'hewlett' in vendor_lower:
            vendor_config = vendor_configs.get('hp', {})
        
        if not vendor_config:
            return vendor_data, oids_collected
        
        # Raccoglie OID vendor-specific
        for category, oids in vendor_config.items():
            category_data = {}
            
            for field, oid_info in oids.items():
                try:
                    oid = oid_info.get('oid')
                    if not oid:
                        continue
                    
                    value = self._snmp_get(host, oid, version, community)
                    if value is not None:
                        category_data[field] = str(value)
                        oids_collected += 1
                        
                except Exception as e:
                    logger.debug(f"Errore raccolta vendor {field} da {host}: {e}")
                    continue
            
            if category_data:
                if vendor_lower.startswith('cisco'):
                    if 'cisco_specific' not in vendor_data:
                        vendor_data['cisco_specific'] = {}
                    vendor_data['cisco_specific'].update(category_data)
                elif 'hp' in vendor_lower:
                    if 'hp_specific' not in vendor_data:
                        vendor_data['hp_specific'] = {}
                    vendor_data['hp_specific'].update(category_data)
        
        return vendor_data, oids_collected
    
    def _snmp_get(self, host: str, oid: str, version: str, community: str) -> Any:
        """
        Esegue una query SNMP GET.
        
        Args:
            host: Indirizzo IP target
            oid: OID da interrogare
            version: Versione SNMP ('1' o '2c')
            community: Community string
            
        Returns:
            Valore OID o None se errore
        """
        try:
            # Determina versione SNMP
            snmp_version = 0 if version == '1' else 1  # 0=v1, 1=v2c
            
            # Esegue query SNMP
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=snmp_version),
                UdpTransportTarget((host, self.port), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                logger.debug(f"SNMP Error Indication {host}/{oid}: {errorIndication}")
                return None
            
            if errorStatus:
                logger.debug(f"SNMP Error Status {host}/{oid}: {errorStatus}")
                return None
            
            # Estrae valore
            for varBind in varBinds:
                return varBind[1]
            
            return None
            
        except Exception as e:
            logger.debug(f"Errore SNMP GET {host}/{oid}: {e}")
            return None
    
    def _format_uptime(self, timeticks: int) -> str:
        """
        Formatta uptime da TimeTicks SNMP in formato leggibile.
        
        Args:
            timeticks: Valore TimeTicks (centesimi di secondo)
            
        Returns:
            Uptime formattato (es. "5 days, 14:23:45.67")
        """
        try:
            # Converte centesimi di secondo in secondi
            total_seconds = timeticks / 100
            
            # Calcola giorni, ore, minuti, secondi
            days = int(total_seconds // 86400)
            remaining = total_seconds % 86400
            hours = int(remaining // 3600)
            remaining = remaining % 3600
            minutes = int(remaining // 60)
            seconds = remaining % 60
            
            # Formatta stringa
            if days > 0:
                return f"{days} days, {hours:02d}:{minutes:02d}:{seconds:05.2f}"
            else:
                return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"
                
        except Exception:
            return str(timeticks)
    
    def _guess_vendor_from_snmp(self, system_info: Dict[str, Any]) -> str:
        """
        Tenta di identificare il vendor dalle informazioni di sistema SNMP.
        
        Args:
            system_info: Informazioni sistema da SNMP
            
        Returns:
            Nome vendor identificato
        """
        sys_descr = system_info.get('sysDescr', '').lower()
        sys_object_id = system_info.get('sysObjectID', '')
        
        # Mapping basato su sysDescr
        vendor_patterns = {
            'cisco': ['cisco', 'ios'],
            'hp': ['hp', 'hewlett', 'procurve', 'aruba'],
            'juniper': ['juniper', 'junos'],
            'dell': ['dell', 'powerconnect'],
            'netgear': ['netgear'],
            'ubiquiti': ['ubiquiti', 'unifi'],
            'mikrotik': ['mikrotik', 'routeros'],
            'fortinet': ['fortinet', 'fortigate'],
            'pfsense': ['pfsense'],
            'linux': ['linux'],
            'windows': ['windows', 'microsoft']
        }
        
        for vendor, patterns in vendor_patterns.items():
            if any(pattern in sys_descr for pattern in patterns):
                return vendor.title()
        
        # Mapping basato su sysObjectID (enterprise OID)  
        if sys_object_id:
            enterprise_oids = {
                '1.3.6.1.4.1.9': 'Cisco',
                '1.3.6.1.4.1.11': 'HP', 
                '1.3.6.1.4.1.2636': 'Juniper',
                '1.3.6.1.4.1.674': 'Dell',
                '1.3.6.1.4.1.4526': 'Netgear',
                '1.3.6.1.4.1.41112': 'Ubiquiti',
                '1.3.6.1.4.1.14988': 'MikroTik'
            }
            
            for oid_prefix, vendor in enterprise_oids.items():
                if sys_object_id.startswith(oid_prefix):
                    return vendor
        
        return ""
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """
        Crea una struttura risultati vuota.
        
        Returns:
            Risultati vuoti
        """
        return {
            'devices': [],
            'statistics': {
                'hosts_tested': 0,
                'snmp_responsive': 0,
                'v1_accessible': 0,
                'v2c_accessible': 0,
                'total_oids_collected': 0,
                'communities_tested': [],
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
        return self.enabled
    
    def get_scanner_info(self) -> Dict[str, Any]:
        """
        Ottiene informazioni sullo scanner.
        
        Returns:
            Dizionario con info scanner
        """
        return {
            'name': 'SNMP Scanner',
            'version': '1.0.0',
            'enabled': self.enabled,
            'snmp_available': SNMP_AVAILABLE,
            'versions_supported': self.versions,
            'communities_configured': len(self.communities),
            'config': self.config
        }
    
    def __str__(self) -> str:
        """Rappresentazione string dell'SNMPScanner."""
        return f"SNMPScanner(enabled={self.enabled}, versions={self.versions})"
    
    def __repr__(self) -> str:
        """Rappresentazione debug dell'SNMPScanner.""" 
        return f"SNMPScanner(enabled={self.enabled}, config={self.config})"
