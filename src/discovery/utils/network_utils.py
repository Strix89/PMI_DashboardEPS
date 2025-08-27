"""
PMI Dashboard EPS - Discovery Engine
Network Utils

Utilità per operazioni di rete, inclusa l'identificazione degli IP locali
della macchina che esegue la discovery.

Author: PMI Dashboard EPS Team
Date: 27 Agosto 2025
"""

import socket
import ipaddress
import psutil
import logging
from typing import List, Set, Dict, Any, Optional

logger = logging.getLogger(__name__)

class NetworkUtils:
    """
    Utilità per operazioni di rete e identificazione IP locali.
    
    Fornisce metodi per:
    - Rilevamento IP locali della macchina
    - Validazione range di rete
    - Esclusione automatica IP locali dai target
    """
    
    @staticmethod
    def get_local_ip_addresses() -> Set[str]:
        """
        Ottiene tutti gli indirizzi IP locali della macchina.
        
        Returns:
            Set di indirizzi IP locali come stringhe
        """
        local_ips = set()
        
        try:
            # Metodo 1: Usa psutil per ottenere interfacce di rete
            for interface_name, addresses in psutil.net_if_addrs().items():
                for address in addresses:
                    if address.family == socket.AF_INET:  # IPv4
                        ip = address.address
                        
                        # Esclude indirizzi loopback e non validi
                        if ip and ip != '127.0.0.1' and not ip.startswith('127.'):
                            try:
                                # Verifica che sia un IP valido
                                ipaddress.IPv4Address(ip)
                                local_ips.add(ip)
                                logger.debug(f"IP locale trovato su {interface_name}: {ip}")
                            except ipaddress.AddressValueError:
                                logger.debug(f"IP non valido ignorato: {ip}")
            
            # Metodo 2: Fallback usando socket (per completezza)
            if not local_ips:
                logger.warning("Nessun IP trovato con psutil, usando fallback socket")
                
                try:
                    # Connessione temporanea per ottenere IP locale principale
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        # Connessione a IP esterno (non invia realmente pacchetti)
                        s.connect(("8.8.8.8", 80))
                        primary_ip = s.getsockname()[0]
                        if primary_ip and primary_ip != '127.0.0.1':
                            local_ips.add(primary_ip)
                            logger.debug(f"IP principale trovato con socket: {primary_ip}")
                except Exception as e:
                    logger.debug(f"Fallback socket fallito: {e}")
            
            # Aggiungi sempre localhost per sicurezza
            local_ips.add('127.0.0.1')
            
            logger.info(f"IP locali identificati: {sorted(local_ips)}")
            return local_ips
            
        except Exception as e:
            logger.error(f"Errore rilevamento IP locali: {e}")
            # Fallback di sicurezza
            return {'127.0.0.1'}
    
    @staticmethod
    def get_primary_local_ip() -> Optional[str]:
        """
        Ottiene l'IP locale primario della macchina.
        
        Returns:
            IP locale principale o None se non trovato
        """
        try:
            # Usa il trucco della connessione socket per trovare IP principale
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                primary_ip = s.getsockname()[0]
                
                if primary_ip and primary_ip != '127.0.0.1':
                    logger.debug(f"IP primario identificato: {primary_ip}")
                    return primary_ip
                    
        except Exception as e:
            logger.debug(f"Errore rilevamento IP primario: {e}")
        
        # Fallback: cerca il primo IP non-loopback
        local_ips = NetworkUtils.get_local_ip_addresses()
        for ip in sorted(local_ips):
            if ip != '127.0.0.1':
                return ip
        
        return None
    
    @staticmethod
    def get_network_interfaces() -> Dict[str, List[Dict[str, Any]]]:
        """
        Ottiene informazioni dettagliate sulle interfacce di rete.
        
        Returns:
            Dizionario con interfacce e relativi indirizzi
        """
        interfaces = {}
        
        try:
            for interface_name, addresses in psutil.net_if_addrs().items():
                interface_info = []
                
                for address in addresses:
                    addr_info = {
                        'family': address.family,
                        'address': address.address,
                        'netmask': getattr(address, 'netmask', None),
                        'broadcast': getattr(address, 'broadcast', None)
                    }
                    
                    # Aggiunge tipo leggibile
                    if address.family == socket.AF_INET:
                        addr_info['type'] = 'IPv4'
                    elif address.family == socket.AF_INET6:
                        addr_info['type'] = 'IPv6'
                    elif hasattr(socket, 'AF_PACKET') and address.family == socket.AF_PACKET:
                        addr_info['type'] = 'MAC'
                    else:
                        addr_info['type'] = 'Unknown'
                    
                    interface_info.append(addr_info)
                
                interfaces[interface_name] = interface_info
            
            logger.debug(f"Interfacce di rete: {list(interfaces.keys())}")
            return interfaces
            
        except Exception as e:
            logger.error(f"Errore rilevamento interfacce: {e}")
            return {}
    
    @staticmethod
    def is_ip_in_local_network(ip: str, local_ips: Set[str] = None) -> bool:
        """
        Verifica se un IP appartiene alla stessa rete di un IP locale.
        
        Args:
            ip: IP da verificare
            local_ips: Set di IP locali (se None, viene rilevato automaticamente)
            
        Returns:
            True se l'IP è nella stessa rete di un IP locale
        """
        if local_ips is None:
            local_ips = NetworkUtils.get_local_ip_addresses()
        
        try:
            target_ip = ipaddress.IPv4Address(ip)
            
            # Ottiene interfacce per controllo subnet
            interfaces = NetworkUtils.get_network_interfaces()
            
            for interface_name, addresses in interfaces.items():
                for addr_info in addresses:
                    if addr_info['type'] == 'IPv4':
                        local_ip = addr_info['address']
                        netmask = addr_info.get('netmask')
                        
                        if local_ip in local_ips and netmask:
                            try:
                                # Crea network dalla combinazione IP/netmask
                                network = ipaddress.IPv4Network(f"{local_ip}/{netmask}", strict=False)
                                
                                if target_ip in network:
                                    logger.debug(f"IP {ip} è nella rete locale {network}")
                                    return True
                                    
                            except Exception as e:
                                logger.debug(f"Errore verifica rete {local_ip}/{netmask}: {e}")
            
            return False
            
        except Exception as e:
            logger.debug(f"Errore verifica IP in rete locale: {e}")
            return False
    
    @staticmethod
    def exclude_local_ips_from_targets(target_range: str, additional_excludes: List[str] = None) -> List[str]:
        """
        Esclude automaticamente gli IP locali e indirizzi di rete dalla lista target.
        
        Args:
            target_range: Range di rete target in formato CIDR
            additional_excludes: Esclusioni aggiuntive da configurazione
            
        Returns:
            Lista di range/IP da escludere (include IP locali e indirizzi di rete)
        """
        exclude_list = additional_excludes.copy() if additional_excludes else []
        
        try:
            # Ottiene IP locali
            local_ips = NetworkUtils.get_local_ip_addresses()
            
            # Verifica network range
            target_network = ipaddress.ip_network(target_range, strict=False)
            
            # Esclude automaticamente l'indirizzo di rete
            network_address = str(target_network.network_address)
            if network_address not in exclude_list:
                exclude_list.append(network_address)
                logger.info(f"Indirizzo di rete {network_address} escluso automaticamente")
            
            # Esclude automaticamente l'indirizzo broadcast (se non è /32)
            if target_network.num_addresses > 1:
                broadcast_address = str(target_network.broadcast_address)
                if broadcast_address not in exclude_list:
                    exclude_list.append(broadcast_address)
                    logger.info(f"Indirizzo broadcast {broadcast_address} escluso automaticamente")
            
            # Verifica quali IP locali sono nel range target
            for local_ip in local_ips:
                try:
                    local_ip_obj = ipaddress.IPv4Address(local_ip)
                    
                    if local_ip_obj in target_network and local_ip not in exclude_list:
                        # Aggiunge IP locale agli esclusi
                        exclude_list.append(local_ip)
                        logger.info(f"IP locale {local_ip} aggiunto alle esclusioni automatiche")
                        
                except Exception as e:
                    logger.debug(f"Errore verifica IP locale {local_ip}: {e}")
            
            # Rimuove duplicati mantenendo ordine
            seen = set()
            unique_excludes = []
            for item in exclude_list:
                if item not in seen:
                    seen.add(item)
                    unique_excludes.append(item)
            
            if unique_excludes != (additional_excludes or []):
                logger.info(f"Esclusioni finali: {unique_excludes}")
            
            return unique_excludes
            
        except Exception as e:
            logger.error(f"Errore esclusione IP locali: {e}")
            return additional_excludes or []
    
    @staticmethod
    def validate_network_range(network_range: str) -> bool:
        """
        Valida un range di rete CIDR.
        
        Args:
            network_range: Range in formato CIDR
            
        Returns:
            True se valido
        """
        try:
            ipaddress.ip_network(network_range, strict=False)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_network_info_summary() -> Dict[str, Any]:
        """
        Ottiene un riassunto delle informazioni di rete locali.
        
        Returns:
            Dizionario con informazioni di rete
        """
        try:
            local_ips = NetworkUtils.get_local_ip_addresses()
            primary_ip = NetworkUtils.get_primary_local_ip()
            interfaces = NetworkUtils.get_network_interfaces()
            
            # Conta interfacce attive
            active_interfaces = 0
            ipv4_addresses = 0
            
            for interface_name, addresses in interfaces.items():
                has_ipv4 = any(addr['type'] == 'IPv4' and addr['address'] != '127.0.0.1' 
                              for addr in addresses)
                if has_ipv4:
                    active_interfaces += 1
                
                ipv4_addresses += sum(1 for addr in addresses 
                                     if addr['type'] == 'IPv4' and addr['address'] != '127.0.0.1')
            
            return {
                'local_ips': sorted(list(local_ips)),
                'primary_ip': primary_ip,
                'total_interfaces': len(interfaces),
                'active_interfaces': active_interfaces,
                'ipv4_addresses': ipv4_addresses,
                'interface_names': list(interfaces.keys())
            }
            
        except Exception as e:
            logger.error(f"Errore summary informazioni rete: {e}")
            return {
                'local_ips': ['127.0.0.1'],
                'primary_ip': None,
                'total_interfaces': 0,
                'active_interfaces': 0,
                'ipv4_addresses': 0,
                'interface_names': []
            }
