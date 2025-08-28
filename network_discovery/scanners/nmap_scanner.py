"""
NMAP Scanner implementation for Network Discovery Module.

This module provides NMAP-based port scanning, service detection, and OS fingerprinting
capabilities with configurable parameters loaded from YAML configuration files.
"""

import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Set
import re
import time
from pathlib import Path
import tempfile
import os

from .base_scanner import BaseScanner, ScanResult
from ..core.data_models import DeviceInfo, DeviceType, ScanStatus
from ..config.config_loader import NMAPConfig


class NMAPScanner(BaseScanner):
    """
    NMAP-based network scanner for port scanning, service detection, and OS fingerprinting.
    
    This scanner uses the NMAP tool to perform comprehensive network scanning including:
    - Port scanning with configurable scan types
    - Service version detection
    - Operating system fingerprinting
    - SNMP device detection (port 161)
    """
    
    def __init__(self, logger=None):
        """
        Initialize NMAP scanner.
        
        Args:
            logger: Logger instance for outputting scan progress and errors
        """
        super().__init__(logger)
        self.scanner_type = "nmap"
        self.snmp_enabled_devices: Set[str] = set()
    
    def scan(self, targets: List[str], config: NMAPConfig) -> ScanResult:
        """
        Execute NMAP scan on the specified targets.
        
        Args:
            targets: List of IP addresses to scan
            config: NMAPConfig object with scan parameters
            
        Returns:
            ScanResult object containing discovered devices and scan metadata
        """
        self._start_scan_timer()
        self._log_info(f"Starting NMAP scan on {len(targets)} targets")
        
        # Validate targets
        valid_targets = self.validate_targets(targets)
        if not valid_targets:
            return ScanResult(
                scanner_type=self.scanner_type,
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=self._end_scan_timer(),
                errors=["No valid targets provided for NMAP scan"]
            )
        
        errors = []
        devices_found = []
        raw_output = ""
        
        try:
            # Build NMAP command
            nmap_command = self.build_nmap_command(valid_targets, config)
            self._log_debug(f"NMAP command: {' '.join(nmap_command)}")
            
            # Execute NMAP scan
            raw_output, scan_errors = self._execute_nmap_scan(nmap_command, config.timeout)
            
            if scan_errors:
                errors.extend(scan_errors)
            
            # Parse results if we have output
            if raw_output:
                devices_found = self.parse_results(raw_output)
                self._log_info(f"NMAP scan completed. Found {len(devices_found)} devices")
                
                # Identify SNMP-enabled devices
                self._identify_snmp_devices(devices_found)
            else:
                self._log_warning("NMAP scan produced no output")
                errors.append("NMAP scan produced no output")
        
        except Exception as e:
            error_msg = f"NMAP scan failed: {str(e)}"
            self._log_error(error_msg)
            errors.append(error_msg)
        
        # Determine scan status
        scan_status = ScanStatus.COMPLETED
        if errors:
            scan_status = ScanStatus.PARTIAL if devices_found else ScanStatus.FAILED
        
        scan_duration = self._end_scan_timer()
        
        return ScanResult(
            scanner_type=self.scanner_type,
            scan_status=scan_status,
            devices_found=devices_found,
            scan_duration=scan_duration,
            errors=errors,
            raw_output=raw_output,
            metadata={
                'targets_scanned': len(valid_targets),
                'snmp_enabled_devices': len(self.snmp_enabled_devices),
                'command_used': ' '.join(nmap_command) if 'nmap_command' in locals() else None
            }
        )
    
    def build_nmap_command(self, targets: List[str], config: NMAPConfig) -> List[str]:
        """
        Build NMAP command from configuration parameters.
        
        Args:
            targets: List of IP addresses to scan
            config: NMAPConfig object with scan parameters
            
        Returns:
            List of command arguments for subprocess execution
        """
        command = ["nmap"]
        
        # Add scan type
        if config.scan_type:
            command.append(config.scan_type)
        
        # Add port range
        if config.port_range:
            command.append(config.port_range)
        
        # Add timing template
        if config.timing:
            command.append(config.timing)
        
        # Add OS detection
        if config.os_detection:
            command.append(config.os_detection)
        
        # Add service detection
        if config.service_detection:
            command.append(config.service_detection)
        
        # Add additional flags
        if config.additional_flags:
            for flag in config.additional_flags:
                if flag.strip():  # Only add non-empty flags
                    command.append(flag.strip())
        
        # Add XML output for parsing
        command.extend(["-oX", "-"])  # Output XML to stdout
        
        # Add parallel host limit
        if config.max_parallel and config.max_parallel > 0:
            command.extend(["--max-hostgroup", str(config.max_parallel)])
        
        # Add targets
        command.extend(targets)
        
        return command
    
    def _execute_nmap_scan(self, command: List[str], timeout: int) -> tuple[str, List[str]]:
        """
        Execute NMAP command and return output and errors.
        
        Args:
            command: NMAP command as list of arguments
            timeout: Timeout in seconds for the scan
            
        Returns:
            Tuple of (stdout_output, list_of_errors)
        """
        errors = []
        
        try:
            self._log_info(f"Executing NMAP scan with timeout of {timeout} seconds")
            
            # Execute NMAP command
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise exception on non-zero exit code
            )
            
            # Check for errors
            if process.returncode != 0:
                error_msg = f"NMAP exited with code {process.returncode}"
                if process.stderr:
                    error_msg += f": {process.stderr.strip()}"
                errors.append(error_msg)
                self._log_warning(error_msg)
            
            # Log stderr as warnings (NMAP often uses stderr for informational messages)
            if process.stderr:
                stderr_lines = process.stderr.strip().split('\n')
                for line in stderr_lines:
                    if line.strip():
                        self._log_debug(f"NMAP stderr: {line.strip()}")
            
            return process.stdout, errors
        
        except subprocess.TimeoutExpired:
            error_msg = f"NMAP scan timed out after {timeout} seconds"
            self._log_error(error_msg)
            errors.append(error_msg)
            return "", errors
        
        except FileNotFoundError:
            error_msg = "NMAP command not found. Please ensure NMAP is installed and in PATH"
            self._log_error(error_msg)
            errors.append(error_msg)
            return "", errors
        
        except Exception as e:
            error_msg = f"Error executing NMAP command: {str(e)}"
            self._log_error(error_msg)
            errors.append(error_msg)
            return "", errors
    
    def parse_results(self, raw_output: str) -> List[DeviceInfo]:
        """
        Parse NMAP XML output into structured device information.
        
        Args:
            raw_output: Raw XML output from NMAP
            
        Returns:
            List of DeviceInfo objects parsed from the XML output
        """
        devices = []
        
        try:
            # Parse XML output
            root = ET.fromstring(raw_output)
            
            # Process each host
            for host in root.findall('host'):
                device_info = self._parse_host_element(host)
                if device_info:
                    devices.append(device_info)
            
            self._log_debug(f"Parsed {len(devices)} devices from NMAP XML output")
            
        except ET.ParseError as e:
            self._log_error(f"Error parsing NMAP XML output: {e}")
        except Exception as e:
            self._log_error(f"Unexpected error parsing NMAP results: {e}")
        
        return devices
    
    def _parse_host_element(self, host_element) -> Optional[DeviceInfo]:
        """
        Parse a single host element from NMAP XML output.
        
        Args:
            host_element: XML element representing a host
            
        Returns:
            DeviceInfo object or None if parsing fails
        """
        try:
            # Check if host is up
            status = host_element.find('status')
            if status is None or status.get('state') != 'up':
                return None
            
            # Get IP address
            address_elem = host_element.find('address[@addrtype="ipv4"]')
            if address_elem is None:
                return None
            
            ip_address = address_elem.get('addr')
            if not ip_address:
                return None
            
            # Initialize device info
            device_info = DeviceInfo(ip_address=ip_address)
            
            # Get hostname
            hostnames = host_element.find('hostnames')
            if hostnames is not None:
                hostname_elem = hostnames.find('hostname')
                if hostname_elem is not None:
                    device_info.hostname = hostname_elem.get('name')
            
            # Parse ports and services
            ports_elem = host_element.find('ports')
            if ports_elem is not None:
                self._parse_ports(ports_elem, device_info)
            
            # Parse OS information
            os_elem = host_element.find('os')
            if os_elem is not None:
                self._parse_os_info(os_elem, device_info)
            
            # Note: Device classification will be done by DeviceClassifier in orchestrator
            # Set to UNKNOWN for now, will be properly classified later
            device_info.device_type = DeviceType.UNKNOWN
            
            return device_info
        
        except Exception as e:
            self._log_error(f"Error parsing host element: {e}")
            return None
    
    def _parse_ports(self, ports_element, device_info: DeviceInfo) -> None:
        """
        Parse port information from NMAP XML.
        
        Args:
            ports_element: XML element containing port information
            device_info: DeviceInfo object to update
        """
        for port in ports_element.findall('port'):
            try:
                # Get port number and protocol
                port_id = port.get('portid')
                protocol = port.get('protocol', 'tcp')
                
                if not port_id:
                    continue
                
                port_num = int(port_id)
                
                # Check port state
                state = port.find('state')
                if state is None or state.get('state') != 'open':
                    continue
                
                # Add to open ports
                device_info.open_ports.append(port_num)
                
                # Get service information
                service = port.find('service')
                if service is not None:
                    service_name = service.get('name', 'unknown')
                    service_version = service.get('version', '')
                    service_product = service.get('product', '')
                    
                    # Build service description
                    service_desc = service_name
                    if service_product:
                        service_desc += f" ({service_product}"
                        if service_version:
                            service_desc += f" {service_version}"
                        service_desc += ")"
                    elif service_version:
                        service_desc += f" {service_version}"
                    
                    device_info.services[port_num] = service_desc
                
            except (ValueError, AttributeError) as e:
                self._log_debug(f"Error parsing port information: {e}")
                continue
    
    def _parse_os_info(self, os_element, device_info: DeviceInfo) -> None:
        """
        Parse OS information from NMAP XML.
        
        Args:
            os_element: XML element containing OS information
            device_info: DeviceInfo object to update
        """
        try:
            # Look for OS matches
            osmatch = os_element.find('osmatch')
            if osmatch is not None:
                os_name = osmatch.get('name')
                accuracy = osmatch.get('accuracy', '0')
                
                if os_name:
                    device_info.os_info = f"{os_name} (accuracy: {accuracy}%)"
                    return
            
            # Fallback to OS class information
            osclass = os_element.find('osclass')
            if osclass is not None:
                os_family = osclass.get('osfamily', '')
                os_gen = osclass.get('osgen', '')
                accuracy = osclass.get('accuracy', '0')
                
                if os_family:
                    os_info = os_family
                    if os_gen:
                        os_info += f" {os_gen}"
                    os_info += f" (accuracy: {accuracy}%)"
                    device_info.os_info = os_info
        
        except Exception as e:
            self._log_debug(f"Error parsing OS information: {e}")
    

    
    def _identify_snmp_devices(self, devices: List[DeviceInfo]) -> None:
        """
        Identify devices with SNMP enabled (port 161 open).
        
        Args:
            devices: List of DeviceInfo objects to check
        """
        self.snmp_enabled_devices.clear()
        
        for device in devices:
            if 161 in device.open_ports:
                self.snmp_enabled_devices.add(device.ip_address)
                self._log_debug(f"SNMP-enabled device found: {device.ip_address}")
        
        if self.snmp_enabled_devices:
            self._log_info(f"Found {len(self.snmp_enabled_devices)} SNMP-enabled devices")
    
    def get_snmp_enabled_devices(self) -> Set[str]:
        """
        Get the set of IP addresses with SNMP enabled.
        
        Returns:
            Set of IP addresses that have port 161 open
        """
        return self.snmp_enabled_devices.copy()
    
    def validate_nmap_availability(self) -> bool:
        """
        Check if NMAP is available on the system.
        
        Returns:
            True if NMAP is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["nmap", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False