"""
Configuration loader for Network Discovery Module.
Handles loading and validation of YAML configuration files with fallback to defaults.
"""

import yaml
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from ..utils.logger import Logger


@dataclass
class ARPConfig:
    """Configuration for ARP scanning."""
    timeout: int = 2
    retries: int = 3
    interface: Optional[str] = None
    method: str = "ping"  # arping, scapy, ping
    parallel_threads: int = 10


@dataclass
class NMAPConfig:
    """Configuration for NMAP scanning."""
    scan_type: str = "-sS"
    port_range: str = "-F"
    timing: str = "-T4"
    os_detection: str = "-O"
    service_detection: str = "-sV"
    additional_flags: list = None
    timeout: int = 300
    max_parallel: int = 50
    
    def __post_init__(self):
        if self.additional_flags is None:
            self.additional_flags = ["--script=default", "--script=vuln"]


@dataclass
class SNMPConfig:
    """Configuration for SNMP scanning."""
    versions: list = None
    communities: list = None
    timeout: int = 5
    retries: int = 2
    max_oids_per_request: int = 10
    walk_oids: list = None
    
    def __post_init__(self):
        if self.versions is None:
            self.versions = [1, 2]
        if self.communities is None:
            self.communities = ["public", "private", "admin"]
        if self.walk_oids is None:
            self.walk_oids = [
                "1.3.6.1.2.1.1",  # System info
                "1.3.6.1.2.1.2",  # Interfaces
                "1.3.6.1.2.1.4"   # IP info
            ]


class ConfigLoader:
    """
    Loads and validates YAML configuration files for network discovery scanners.
    Provides fallback to default configurations when files are missing.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize ConfigLoader.
        
        Args:
            config_dir: Directory containing configuration files. 
                       Defaults to the config directory relative to this file.
        """
        if config_dir is None:
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = Path(config_dir)
        
        self.logger = Logger()
    
    def load_arp_config(self, config_file: str = "arp_config.yml") -> ARPConfig:
        """
        Load ARP configuration from YAML file.
        
        Args:
            config_file: Name of the ARP configuration file
            
        Returns:
            ARPConfig object with loaded or default configuration
        """
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            self.logger.warning(f"ARP config file not found at {config_path}. Using default configuration.")
            return ARPConfig()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'arp' not in config_data:
                self.logger.warning(f"Invalid ARP config structure in {config_path}. Using default configuration.")
                return ARPConfig()
            
            arp_data = config_data['arp']
            
            # Validate and create ARPConfig
            return ARPConfig(
                timeout=self._validate_positive_int(arp_data.get('timeout', 2), 'timeout', 2),
                retries=self._validate_positive_int(arp_data.get('retries', 3), 'retries', 3),
                interface=arp_data.get('interface'),
                method=self._validate_method(arp_data.get('method', 'arping')),
                parallel_threads=self._validate_positive_int(arp_data.get('parallel_threads', 10), 'parallel_threads', 10)
            )
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing ARP config file {config_path}: {e}")
            self.logger.warning("Using default ARP configuration.")
            return ARPConfig()
        except Exception as e:
            self.logger.error(f"Unexpected error loading ARP config: {e}")
            self.logger.warning("Using default ARP configuration.")
            return ARPConfig()
    
    def load_nmap_config(self, config_file: str = "nmap_config.yml") -> NMAPConfig:
        """
        Load NMAP configuration from YAML file.
        
        Args:
            config_file: Name of the NMAP configuration file
            
        Returns:
            NMAPConfig object with loaded or default configuration
        """
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            self.logger.warning(f"NMAP config file not found at {config_path}. Using default configuration.")
            return NMAPConfig()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'nmap' not in config_data:
                self.logger.warning(f"Invalid NMAP config structure in {config_path}. Using default configuration.")
                return NMAPConfig()
            
            nmap_data = config_data['nmap']
            
            # Validate and create NMAPConfig
            return NMAPConfig(
                scan_type=nmap_data.get('scan_type', '-sS'),
                port_range=nmap_data.get('port_range', '-F'),
                timing=nmap_data.get('timing', '-T4'),
                os_detection=nmap_data.get('os_detection', '-O'),
                service_detection=nmap_data.get('service_detection', '-sV'),
                additional_flags=nmap_data.get('additional_flags', ["--script=default", "--script=vuln"]),
                timeout=self._validate_positive_int(nmap_data.get('timeout', 300), 'timeout', 300),
                max_parallel=self._validate_positive_int(nmap_data.get('max_parallel', 50), 'max_parallel', 50)
            )
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing NMAP config file {config_path}: {e}")
            self.logger.warning("Using default NMAP configuration.")
            return NMAPConfig()
        except Exception as e:
            self.logger.error(f"Unexpected error loading NMAP config: {e}")
            self.logger.warning("Using default NMAP configuration.")
            return NMAPConfig()
    
    def load_snmp_config(self, config_file: str = "snmp_config.yml") -> SNMPConfig:
        """
        Load SNMP configuration from YAML file.
        
        Args:
            config_file: Name of the SNMP configuration file
            
        Returns:
            SNMPConfig object with loaded or default configuration
        """
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            self.logger.warning(f"SNMP config file not found at {config_path}. Using default configuration.")
            return SNMPConfig()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'snmp' not in config_data:
                self.logger.warning(f"Invalid SNMP config structure in {config_path}. Using default configuration.")
                return SNMPConfig()
            
            snmp_data = config_data['snmp']
            
            # Validate and create SNMPConfig
            return SNMPConfig(
                versions=self._validate_snmp_versions(snmp_data.get('versions', [1, 2])),
                communities=snmp_data.get('communities', ["public", "private", "admin"]),
                timeout=self._validate_positive_int(snmp_data.get('timeout', 5), 'timeout', 5),
                retries=self._validate_positive_int(snmp_data.get('retries', 2), 'retries', 2),
                max_oids_per_request=self._validate_positive_int(snmp_data.get('max_oids_per_request', 10), 'max_oids_per_request', 10),
                walk_oids=snmp_data.get('walk_oids', [
                    "1.3.6.1.2.1.1",  # System info
                    "1.3.6.1.2.1.2",  # Interfaces
                    "1.3.6.1.2.1.4"   # IP info
                ])
            )
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing SNMP config file {config_path}: {e}")
            self.logger.warning("Using default SNMP configuration.")
            return SNMPConfig()
        except Exception as e:
            self.logger.error(f"Unexpected error loading SNMP config: {e}")
            self.logger.warning("Using default SNMP configuration.")
            return SNMPConfig()
    
    def _validate_positive_int(self, value: Any, field_name: str, default: int) -> int:
        """
        Validate that a value is a positive integer.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error messages
            default: Default value to use if validation fails
            
        Returns:
            Validated integer value or default
        """
        try:
            int_value = int(value)
            if int_value <= 0:
                self.logger.warning(f"Invalid {field_name}: {value}. Must be positive. Using default: {default}")
                return default
            return int_value
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid {field_name}: {value}. Must be an integer. Using default: {default}")
            return default
    
    def _validate_method(self, method: str) -> str:
        """
        Validate ARP scanning method.
        
        Args:
            method: Method to validate
            
        Returns:
            Validated method or default
        """
        valid_methods = ["arping", "scapy", "ping"]
        if method not in valid_methods:
            self.logger.warning(f"Invalid ARP method: {method}. Must be one of {valid_methods}. Using default: ping")
            return "ping"
        return method
    
    def _validate_snmp_versions(self, versions: Any) -> list:
        """
        Validate SNMP versions list.
        
        Args:
            versions: Versions to validate
            
        Returns:
            Validated versions list or default
        """
        if not isinstance(versions, list):
            self.logger.warning(f"Invalid SNMP versions: {versions}. Must be a list. Using default: [1, 2]")
            return [1, 2]
        
        valid_versions = []
        for version in versions:
            if version in [1, 2, 3]:
                valid_versions.append(version)
            else:
                self.logger.warning(f"Invalid SNMP version: {version}. Skipping.")
        
        if not valid_versions:
            self.logger.warning("No valid SNMP versions found. Using default: [1, 2]")
            return [1, 2]
        
        return valid_versions
    
    def create_default_configs(self) -> None:
        """
        Create default configuration files if they don't exist.
        """
        self._create_default_arp_config()
        self._create_default_nmap_config()
        self._create_default_snmp_config()
    
    def _create_default_arp_config(self) -> None:
        """Create default ARP configuration file."""
        config_path = self.config_dir / "arp_config.yml"
        if config_path.exists():
            return
        
        default_config = {
            'arp': {
                'timeout': 2,
                'retries': 3,
                'interface': None,
                'method': 'arping',
                'parallel_threads': 10
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Created default ARP config at {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to create default ARP config: {e}")
    
    def _create_default_nmap_config(self) -> None:
        """Create default NMAP configuration file."""
        config_path = self.config_dir / "nmap_config.yml"
        if config_path.exists():
            return
        
        default_config = {
            'nmap': {
                'scan_type': '-sS',
                'port_range': '-F',
                'timing': '-T4',
                'os_detection': '-O',
                'service_detection': '-sV',
                'additional_flags': [
                    '--script=default',
                    '--script=vuln'
                ],
                'timeout': 300,
                'max_parallel': 50
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Created default NMAP config at {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to create default NMAP config: {e}")
    
    def _create_default_snmp_config(self) -> None:
        """Create default SNMP configuration file."""
        config_path = self.config_dir / "snmp_config.yml"
        if config_path.exists():
            return
        
        default_config = {
            'snmp': {
                'versions': [1, 2],
                'communities': [
                    'public',
                    'private',
                    'admin'
                ],
                'timeout': 5,
                'retries': 2,
                'max_oids_per_request': 10,
                'walk_oids': [
                    '1.3.6.1.2.1.1',  # System info
                    '1.3.6.1.2.1.2',  # Interfaces
                    '1.3.6.1.2.1.4'   # IP info
                ]
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Created default SNMP config at {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to create default SNMP config: {e}")