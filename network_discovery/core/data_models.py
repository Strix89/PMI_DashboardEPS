"""
Core data models and enums for the Network Discovery Module.

This module defines the data structures used throughout the network discovery process,
including device information, scan results, and metadata.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class DeviceType(Enum):
    """Enumeration of device types that can be detected during network scanning."""
    IOT = "IoT"
    WINDOWS = "Windows"
    LINUX = "Linux"
    NETWORK_EQUIPMENT = "NetworkEquipment"
    UNKNOWN = "Unknown"


class ScanStatus(Enum):
    """Enumeration of possible scan statuses."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class NetworkInfo:
    """
    Information about the host network configuration.
    
    Attributes:
        host_ip: IP address of the scanning host
        netmask: Network subnet mask
        network_address: Network address (e.g., 192.168.1.0)
        broadcast_address: Broadcast address (e.g., 192.168.1.255)
        interface_name: Name of the network interface used
        scan_range: List of IP addresses to be scanned
    """
    host_ip: str
    netmask: str
    network_address: str
    broadcast_address: str
    interface_name: str
    scan_range: List[str] = field(default_factory=list)


@dataclass
class DeviceInfo:
    """
    Information about a discovered network device.
    
    Attributes:
        ip_address: IP address of the device
        mac_address: MAC address (if available from ARP)
        hostname: Device hostname (if resolvable)
        os_info: Operating system information from NMAP
        device_type: Classified device type
        manufacturer: Device manufacturer (from SNMP if available)
        model: Device model (from SNMP if available)
        open_ports: List of open TCP/UDP ports
        services: Mapping of port numbers to service names
        snmp_data: SNMP OID-value pairs (if SNMP scan was successful)
    """
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    os_info: Optional[str] = None
    device_type: DeviceType = DeviceType.UNKNOWN
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    open_ports: List[int] = field(default_factory=list)
    services: Dict[int, str] = field(default_factory=dict)
    snmp_data: Optional[Dict[str, str]] = None


@dataclass
class ScanStatistics:
    """
    Statistics about the completed scan operations.
    
    Attributes:
        total_addresses_scanned: Total number of IP addresses scanned
        devices_found: Dictionary with count of devices found by each scanner
        scan_times: Dictionary with duration of each scan phase
        errors_encountered: List of errors that occurred during scanning
    """
    total_addresses_scanned: int = 0
    devices_found: Dict[str, int] = field(default_factory=dict)
    scan_times: Dict[str, float] = field(default_factory=dict)
    errors_encountered: List[str] = field(default_factory=list)


@dataclass
class ScanMetadata:
    """
    Metadata about the scan execution.
    
    Attributes:
        timestamp: When the scan was started
        scan_duration: Total duration of the complete scan in seconds
        network_scanned: Network range that was scanned (CIDR notation)
        host_ip: IP address of the scanning host
        excluded_addresses: List of addresses excluded from scanning
        configurations_used: Dictionary of configurations used for each scanner
        scan_status: Overall status of the scan
    """
    timestamp: datetime
    scan_duration: float = 0.0
    network_scanned: str = ""
    host_ip: str = ""
    excluded_addresses: List[str] = field(default_factory=list)
    configurations_used: Dict[str, Any] = field(default_factory=dict)
    scan_status: ScanStatus = ScanStatus.NOT_STARTED


@dataclass
class CompleteScanResult:
    """
    Complete result of a network discovery scan.
    
    This is the top-level data structure that contains all information
    about a completed scan, including metadata, network info, discovered
    devices, and statistics.
    
    Attributes:
        scan_metadata: Metadata about the scan execution
        network_info: Information about the scanned network
        devices: List of all discovered devices
        scan_statistics: Statistics about the scan performance
    """
    scan_metadata: ScanMetadata
    network_info: NetworkInfo
    devices: List[DeviceInfo] = field(default_factory=list)
    scan_statistics: ScanStatistics = field(default_factory=ScanStatistics)