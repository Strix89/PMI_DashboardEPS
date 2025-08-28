"""
JSON Report Generator for Network Discovery Module.

This module provides functionality to generate structured JSON reports
from network discovery scan results, including proper file naming,
collision handling, and schema compliance.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import asdict

from ..core.data_models import CompleteScanResult, DeviceInfo, DeviceType, ScanStatus
from .logger import get_logger


class JSONReporter:
    """
    Handles generation of JSON reports from network discovery scan results.
    
    This class is responsible for:
    - Converting scan results to JSON format
    - Managing output file naming with timestamp-based collision handling
    - Ensuring JSON schema compliance with design specifications
    - Merging results from multiple scanners into unified device records
    """
    
    def __init__(self, output_directory: str = "network_discovery/results"):
        """
        Initialize the JSON reporter.
        
        Args:
            output_directory: Directory where JSON reports will be saved
        """
        self.output_directory = Path(output_directory)
        self.logger = get_logger(__name__)
        
        # Ensure output directory exists
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
    def generate_report(self, scan_result: CompleteScanResult) -> str:
        """
        Generate a complete JSON report from scan results.
        
        Args:
            scan_result: Complete scan result data structure
            
        Returns:
            str: Path to the generated JSON file
            
        Raises:
            ValueError: If scan_result is invalid
            IOError: If file cannot be written
        """
        if not scan_result:
            raise ValueError("Scan result cannot be None or empty")
            
        self.logger.info(f"Generating JSON report for scan completed at {scan_result.scan_metadata.timestamp}")
        
        # Convert scan result to JSON-serializable format
        json_data = self._convert_to_json_format(scan_result)
        
        # Generate unique filename
        filename = self._generate_filename(scan_result.scan_metadata.timestamp)
        filepath = self.output_directory / filename
        
        # Handle file collision
        filepath = self._handle_file_collision(filepath)
        
        # Write JSON file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
                
            self.logger.info(f"JSON report successfully generated: {filepath}")
            return str(filepath)
            
        except IOError as e:
            self.logger.error(f"Failed to write JSON report to {filepath}: {e}")
            raise
            
    def _convert_to_json_format(self, scan_result: CompleteScanResult) -> Dict[str, Any]:
        """
        Convert CompleteScanResult to JSON-serializable dictionary format.
        
        Args:
            scan_result: Complete scan result data structure
            
        Returns:
            Dict containing JSON-serializable scan data
        """
        # Convert scan metadata
        scan_metadata = {
            "timestamp": scan_result.scan_metadata.timestamp.isoformat() + "Z",
            "scan_duration": scan_result.scan_metadata.scan_duration,
            "network_scanned": scan_result.scan_metadata.network_scanned,
            "host_ip": scan_result.scan_metadata.host_ip,
            "excluded_addresses": scan_result.scan_metadata.excluded_addresses,
            "configurations_used": scan_result.scan_metadata.configurations_used,
            "scan_status": scan_result.scan_metadata.scan_status.value
        }
        
        # Convert scan statistics
        scan_statistics = {
            "total_addresses_scanned": scan_result.scan_statistics.total_addresses_scanned,
            "devices_found": scan_result.scan_statistics.devices_found,
            "scan_times": scan_result.scan_statistics.scan_times,
            "errors_encountered": scan_result.scan_statistics.errors_encountered
        }
        
        # Convert network info
        network_info = {
            "host_ip": scan_result.network_info.host_ip,
            "netmask": scan_result.network_info.netmask,
            "network_address": scan_result.network_info.network_address,
            "broadcast_address": scan_result.network_info.broadcast_address,
            "interface_name": scan_result.network_info.interface_name,
            "scan_range_size": len(scan_result.network_info.scan_range)
        }
        
        # Convert devices
        devices = []
        for device in scan_result.devices:
            device_dict = {
                "ip_address": device.ip_address,
                "mac_address": device.mac_address,
                "hostname": device.hostname,
                "device_type": device.device_type.value,
                "os_info": device.os_info,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "open_ports": sorted(device.open_ports),
                "services": device.services,
                "snmp_data": device.snmp_data
            }
            devices.append(device_dict)
        
        # Sort devices by IP address for consistent output
        devices.sort(key=lambda x: self._ip_sort_key(x["ip_address"]))
        
        return {
            "scan_metadata": scan_metadata,
            "network_info": network_info,
            "scan_statistics": scan_statistics,
            "devices": devices
        }
        
    def _generate_filename(self, timestamp: datetime) -> str:
        """
        Generate a filename based on timestamp.
        
        Args:
            timestamp: Scan timestamp
            
        Returns:
            str: Generated filename
        """
        # Format: network_discovery_YYYYMMDD_HHMMSS.json
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"network_discovery_{timestamp_str}.json"
        
    def _handle_file_collision(self, filepath: Path) -> Path:
        """
        Handle filename collisions by adding incremental suffix.
        
        Args:
            filepath: Original file path
            
        Returns:
            Path: Unique file path
        """
        if not filepath.exists():
            return filepath
            
        # Extract base name and extension
        base_name = filepath.stem
        extension = filepath.suffix
        counter = 1
        
        while True:
            new_name = f"{base_name}_{counter:03d}{extension}"
            new_filepath = filepath.parent / new_name
            
            if not new_filepath.exists():
                self.logger.info(f"File collision detected, using filename: {new_name}")
                return new_filepath
                
            counter += 1
            
            # Safety check to prevent infinite loop
            if counter > 999:
                raise IOError(f"Too many file collisions for {filepath}")
                
    def _ip_sort_key(self, ip_address: str) -> tuple:
        """
        Generate sort key for IP address to enable proper sorting.
        
        Args:
            ip_address: IP address string
            
        Returns:
            tuple: Sort key for IP address
        """
        try:
            return tuple(int(part) for part in ip_address.split('.'))
        except (ValueError, AttributeError):
            # Fallback for invalid IP addresses
            return (999, 999, 999, 999)
            
    def merge_scanner_results(self, arp_results: Dict[str, Any], 
                            nmap_results: Dict[str, Any], 
                            snmp_results: Dict[str, Any]) -> Dict[str, DeviceInfo]:
        """
        Merge results from different scanners into unified device records.
        
        Args:
            arp_results: Results from ARP scanner (IP -> MAC mapping)
            nmap_results: Results from NMAP scanner (IP -> port/service info)
            snmp_results: Results from SNMP scanner (IP -> SNMP data)
            
        Returns:
            Dict mapping IP addresses to unified DeviceInfo objects
        """
        self.logger.info("Merging results from ARP, NMAP, and SNMP scanners")
        
        unified_devices = {}
        
        # Start with ARP results as base (active devices)
        for ip, arp_data in arp_results.items():
            device = DeviceInfo(
                ip_address=ip,
                mac_address=arp_data.get('mac_address'),
                hostname=arp_data.get('hostname')
            )
            unified_devices[ip] = device
            
        # Merge NMAP results
        for ip, nmap_data in nmap_results.items():
            if ip not in unified_devices:
                # Device found by NMAP but not ARP (possible if ARP failed)
                unified_devices[ip] = DeviceInfo(ip_address=ip)
                
            device = unified_devices[ip]
            device.os_info = nmap_data.get('os_info')
            device.open_ports = nmap_data.get('open_ports', [])
            device.services = nmap_data.get('services', {})
            
            # Update hostname if not set and available from NMAP
            if not device.hostname and nmap_data.get('hostname'):
                device.hostname = nmap_data['hostname']
                
        # Merge SNMP results
        for ip, snmp_data in snmp_results.items():
            if ip in unified_devices:
                device = unified_devices[ip]
                device.snmp_data = snmp_data.get('oid_values', {})
                
                # Extract manufacturer and model from SNMP if available
                if device.snmp_data:
                    device.manufacturer = self._extract_manufacturer_from_snmp(device.snmp_data)
                    device.model = self._extract_model_from_snmp(device.snmp_data)
                    
        self.logger.info(f"Successfully merged results for {len(unified_devices)} devices")
        return unified_devices
        
    def _extract_manufacturer_from_snmp(self, snmp_data: Dict[str, str]) -> Optional[str]:
        """
        Extract manufacturer information from SNMP data.
        
        Args:
            snmp_data: Dictionary of SNMP OID-value pairs
            
        Returns:
            Optional[str]: Manufacturer name if found
        """
        # Common OIDs for manufacturer information
        manufacturer_oids = [
            "1.3.6.1.2.1.1.1.0",  # sysDescr
            "1.3.6.1.4.1.9.9.25.1.1.1.2",  # Cisco specific
        ]
        
        for oid in manufacturer_oids:
            if oid in snmp_data:
                value = snmp_data[oid].lower()
                # Simple manufacturer detection
                if "cisco" in value:
                    return "Cisco"
                elif "hp" in value or "hewlett" in value:
                    return "HP"
                elif "dell" in value:
                    return "Dell"
                elif "netgear" in value:
                    return "Netgear"
                elif "d-link" in value:
                    return "D-Link"
                    
        return None
        
    def _extract_model_from_snmp(self, snmp_data: Dict[str, str]) -> Optional[str]:
        """
        Extract model information from SNMP data.
        
        Args:
            snmp_data: Dictionary of SNMP OID-value pairs
            
        Returns:
            Optional[str]: Model name if found
        """
        # Look for model in system description
        sys_descr_oid = "1.3.6.1.2.1.1.1.0"
        if sys_descr_oid in snmp_data:
            descr = snmp_data[sys_descr_oid]
            # Extract model patterns (this is a simplified approach)
            words = descr.split()
            for i, word in enumerate(words):
                if word.lower() in ["model", "series"] and i + 1 < len(words):
                    return words[i + 1]
                    
        return None
        
    def validate_json_schema(self, json_data: Dict[str, Any]) -> bool:
        """
        Validate that the JSON data matches the expected schema.
        
        Args:
            json_data: JSON data to validate
            
        Returns:
            bool: True if schema is valid, False otherwise
        """
        required_top_level_keys = ["scan_metadata", "network_info", "scan_statistics", "devices"]
        
        # Check top-level structure
        for key in required_top_level_keys:
            if key not in json_data:
                self.logger.error(f"Missing required top-level key: {key}")
                return False
                
        # Validate scan_metadata structure
        metadata = json_data["scan_metadata"]
        required_metadata_keys = ["timestamp", "scan_duration", "network_scanned", "host_ip"]
        for key in required_metadata_keys:
            if key not in metadata:
                self.logger.error(f"Missing required metadata key: {key}")
                return False
                
        # Validate devices structure
        devices = json_data["devices"]
        if not isinstance(devices, list):
            self.logger.error("Devices must be a list")
            return False
            
        for device in devices:
            if "ip_address" not in device:
                self.logger.error("Device missing required ip_address field")
                return False
                
        self.logger.info("JSON schema validation passed")
        return True