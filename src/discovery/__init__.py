"""
PMI Dashboard EPS - Discovery Engine Module

Modulo di discovery per la identificazione automatica di dispositivi di rete
utilizzando protocolli ARP, NMAP e SNMP (v1/v2c).

Author: PMI Dashboard EPS Team
Version: 1.0.0
Date: 27 Agosto 2025
"""

__version__ = "1.0.0"
__author__ = "PMI Dashboard EPS Team"
__email__ = "support@pmi-dashboard.com"
__description__ = "Network Discovery Engine per PMI Dashboard EPS"

from .discovery_engine import DiscoveryEngine
from .scanners.arp_scanner import ARPScanner
from .scanners.nmap_scanner import NMapScanner  
from .scanners.snmp_scanner import SNMPScanner
from .utils.config_manager import ConfigManager
from .utils.output_manager import OutputManager

__all__ = [
    'DiscoveryEngine',
    'ARPScanner',
    'NMapScanner',
    'SNMPScanner', 
    'ConfigManager',
    'OutputManager'
]
