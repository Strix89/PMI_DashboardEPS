"""
SNMP Scanner implementation for Network Discovery Module.

This module implements SNMP-based device discovery using the pysnmp library
to perform SNMP walks and retrieve device information from SNMP-enabled devices.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

try:
    from pysnmp.hlapi import *
    from pysnmp.error import PySnmpError

    PYSNMP_AVAILABLE = True
except ImportError:
    PYSNMP_AVAILABLE = False

    # Define dummy classes for type hints when pysnmp is not available
    class CommunityData:
        pass


from .base_scanner import BaseScanner, ScanResult
from ..core.data_models import DeviceInfo, ScanStatus, DeviceType
from ..config.config_loader import SNMPConfig
from ..utils.logger import Logger


@dataclass
class SNMPResponse:
    """Container for SNMP response data."""

    oid: str
    value: str
    value_type: str


class SNMPScanner(BaseScanner):
    """
    SNMP scanner implementation for discovering and querying SNMP-enabled devices.

    This scanner performs SNMP walks on devices with open SNMP ports (161/UDP)
    to retrieve detailed device information including system info, interfaces,
    and network configuration.
    """

    def __init__(self, logger: Optional[Logger] = None):
        """
        Initialize the SNMP scanner.

        Args:
            logger: Logger instance for outputting scan progress and errors
        """
        super().__init__(logger)
        self.scanner_type = "SNMP"
        self._lock = threading.Lock()

        if not PYSNMP_AVAILABLE:
            self._log_error(
                "pysnmp library not available. SNMP scanning will be disabled."
            )

    def scan(self, targets: List[str], config: SNMPConfig) -> ScanResult:
        """
        Execute SNMP scan on the specified targets.

        Args:
            targets: List of IP addresses to scan (should have SNMP port open)
            config: SNMP configuration object

        Returns:
            ScanResult containing SNMP data and scan metadata
        """
        if not PYSNMP_AVAILABLE:
            return ScanResult(
                scanner_type=self.scanner_type,
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=0.0,
                errors=[
                    "pysnmp library not available. Install with: pip install pysnmp"
                ],
            )

        self._log_info(f"Starting SNMP scan of {len(targets)} targets")
        self._start_scan_timer()

        # Validate targets
        valid_targets = self.validate_targets(targets)
        if not valid_targets:
            return ScanResult(
                scanner_type=self.scanner_type,
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=self._end_scan_timer(),
                errors=["No valid targets to scan"],
            )

        devices, errors, raw_output = self._scan_targets(valid_targets, config)
        scan_duration = self._end_scan_timer()

        # Determine scan status
        if errors and not devices:
            scan_status = ScanStatus.FAILED
        elif errors and devices:
            scan_status = ScanStatus.PARTIAL
        else:
            scan_status = ScanStatus.COMPLETED

        self._log_info(
            f"SNMP scan completed. Retrieved data from {len(devices)} devices in {scan_duration:.2f} seconds"
        )

        return ScanResult(
            scanner_type=self.scanner_type,
            scan_status=scan_status,
            devices_found=devices,
            scan_duration=scan_duration,
            errors=errors,
            raw_output=raw_output,
            metadata={
                "versions_tried": config.versions,
                "communities_tried": config.communities,
                "targets_scanned": len(valid_targets),
                "timeout": config.timeout,
                "retries": config.retries,
                "walk_oids": config.walk_oids,
            },
        )

    def _scan_targets(
        self, targets: List[str], config: SNMPConfig
    ) -> Tuple[List[DeviceInfo], List[str], str]:
        """
        Perform SNMP scan on multiple targets.

        Args:
            targets: List of IP addresses to scan
            config: SNMP configuration

        Returns:
            Tuple of (devices_found, errors, raw_output)
        """
        devices = []
        errors = []
        all_raw_output = []

        # Use ThreadPoolExecutor for parallel scanning (limited concurrency for SNMP)
        max_workers = min(5, len(targets))  # Limit SNMP concurrent requests

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scan tasks
            future_to_target = {
                executor.submit(self._scan_single_target, target, config): target
                for target in targets
            }

            # Collect results as they complete
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    device, error, raw_output = future.result()
                    if device:
                        devices.append(device)
                    if error:
                        errors.append(f"{target}: {error}")
                    if raw_output:
                        all_raw_output.append(
                            f"=== SNMP Scan: {target} ===\n{raw_output}"
                        )
                except Exception as e:
                    error_msg = f"Exception scanning {target}: {str(e)}"
                    errors.append(error_msg)
                    self._log_error(error_msg)

        return devices, errors, "\n\n".join(all_raw_output)

    def _scan_single_target(
        self, target: str, config: SNMPConfig
    ) -> Tuple[Optional[DeviceInfo], Optional[str], str]:
        """
        Perform SNMP scan on a single target.

        Args:
            target: IP address to scan
            config: SNMP configuration

        Returns:
            Tuple of (device_info, error_message, raw_output)
        """
        self._log_debug(f"Starting SNMP scan of {target}")

        # Try different SNMP versions and communities
        for version in config.versions:
            for community in config.communities:
                try:
                    snmp_data, raw_output = self.snmp_walk(
                        target, community, version, config
                    )

                    if snmp_data:
                        # Create DeviceInfo with SNMP data
                        device = DeviceInfo(
                            ip_address=target,
                            device_type=DeviceType.UNKNOWN,  # Will be classified by DeviceClassifier
                            snmp_data=snmp_data,
                        )

                        # Try to extract additional info from SNMP data
                        self._enrich_device_info(device, snmp_data)

                        self._log_info(
                            f"SNMP scan successful for {target} (v{version}, community: {community})"
                        )
                        return device, None, raw_output

                except Exception as e:
                    self._log_debug(
                        f"SNMP v{version} with community '{community}' failed for {target}: {str(e)}"
                    )
                    continue

        # No successful SNMP connection
        error_msg = f"No SNMP response from {target} (tried versions {config.versions} with communities {config.communities})"
        self._log_debug(error_msg)
        return None, error_msg, ""

    def snmp_walk(
        self,
        target: str,
        community: str,
        version: int = 2,
        config: Optional[SNMPConfig] = None,
    ) -> Tuple[Dict[str, str], str]:
        """
        Perform SNMP walk on a target device.

        Args:
            target: IP address of the target device
            community: SNMP community string
            version: SNMP version (1, 2, or 3)
            config: SNMP configuration (optional, uses defaults if not provided)

        Returns:
            Tuple of (oid_value_dict, raw_output_string)
        """
        if not PYSNMP_AVAILABLE:
            raise ImportError("pysnmp library not available")

        if config is None:
            config = SNMPConfig()

        snmp_data = {}
        raw_output_lines = []

        # Configure SNMP version
        if version == 1:
            snmp_version = CommunityData(community, mpModel=0)
        elif version == 2:
            snmp_version = CommunityData(community, mpModel=1)
        elif version == 3:
            # SNMPv3 requires additional authentication - simplified implementation
            snmp_version = CommunityData(community, mpModel=1)  # Fallback to v2c
        else:
            raise ValueError(f"Unsupported SNMP version: {version}")

        # Walk each configured OID
        for base_oid in config.walk_oids:
            try:
                self._log_debug(f"Walking OID {base_oid} on {target}")

                oid_data = self._walk_oid(target, snmp_version, base_oid, config)
                snmp_data.update(oid_data)

                # Add to raw output
                raw_output_lines.append(f"OID Walk: {base_oid}")
                for oid, value in oid_data.items():
                    raw_output_lines.append(f"  {oid} = {value}")

            except Exception as e:
                error_msg = f"Error walking OID {base_oid}: {str(e)}"
                self._log_debug(error_msg)
                raw_output_lines.append(f"OID Walk: {base_oid} - ERROR: {error_msg}")

        return snmp_data, "\n".join(raw_output_lines)

    def _walk_oid(
        self, target: str, snmp_version: Any, base_oid: str, config: SNMPConfig
    ) -> Dict[str, str]:
        """
        Walk a specific OID tree.

        Args:
            target: Target IP address
            snmp_version: SNMP version configuration
            base_oid: Base OID to walk
            config: SNMP configuration

        Returns:
            Dictionary of OID-value pairs
        """
        oid_data = {}

        try:
            # Perform SNMP walk
            for errorIndication, errorStatus, errorIndex, varBinds in nextCmd(
                SnmpEngine(),
                snmp_version,
                UdpTransportTarget(
                    (target, 161), timeout=config.timeout, retries=config.retries
                ),
                ContextData(),
                ObjectType(ObjectIdentity(base_oid)),
                lexicographicMode=False,
                ignoreNonIncreasingOid=True,
                maxRows=config.max_oids_per_request,
            ):

                # Check for errors
                if errorIndication:
                    self._log_debug(f"SNMP error indication: {errorIndication}")
                    break

                if errorStatus:
                    self._log_debug(
                        f"SNMP error status: {errorStatus.prettyPrint()} at {errorIndex and varBinds[int(errorIndex) - 1][0] or '?'}"
                    )
                    break

                # Process variable bindings
                for varBind in varBinds:
                    oid_str = str(varBind[0])
                    value_str = str(varBind[1])

                    # Stop if we've walked beyond the base OID
                    if not oid_str.startswith(base_oid):
                        break

                    oid_data[oid_str] = value_str

                    # Limit the number of OIDs to prevent excessive data
                    if len(oid_data) >= 1000:  # Reasonable limit
                        self._log_debug(
                            f"Reached OID limit (1000) for base OID {base_oid}"
                        )
                        break

        except PySnmpError as e:
            self._log_debug(f"PySnmp error walking {base_oid}: {str(e)}")
        except Exception as e:
            self._log_debug(f"Unexpected error walking {base_oid}: {str(e)}")

        return oid_data

    def _enrich_device_info(
        self, device: DeviceInfo, snmp_data: Dict[str, str]
    ) -> None:
        """
        Enrich device information using SNMP data.

        Args:
            device: DeviceInfo object to enrich
            snmp_data: SNMP OID-value pairs
        """
        # Common SNMP OIDs for device information
        system_oids = {
            "1.3.6.1.2.1.1.1.0": "sysDescr",  # System description
            "1.3.6.1.2.1.1.5.0": "sysName",  # System name
            "1.3.6.1.2.1.1.4.0": "sysContact",  # System contact
            "1.3.6.1.2.1.1.6.0": "sysLocation",  # System location
        }

        # Extract system description for OS info
        for oid, value in snmp_data.items():
            if oid == "1.3.6.1.2.1.1.1.0":  # sysDescr
                device.os_info = value
                # Try to extract manufacturer from system description
                self._extract_manufacturer_from_sysdescr(device, value)
            elif oid == "1.3.6.1.2.1.1.5.0":  # sysName
                device.hostname = value

        # Note: Device classification will be done by DeviceClassifier in orchestrator
        # Just extract manufacturer info here
        device.manufacturer = self._extract_manufacturer_from_snmp(snmp_data)

    def _extract_manufacturer_from_sysdescr(
        self, device: DeviceInfo, sys_descr: str
    ) -> None:
        """
        Extract manufacturer information from system description.

        Args:
            device: DeviceInfo object to update
            sys_descr: System description string
        """
        # Common manufacturer patterns in system descriptions
        manufacturers = {
            "cisco": ["Cisco", "IOS"],
            "hp": ["HP", "Hewlett", "Packard"],
            "dell": ["Dell"],
            "juniper": ["Juniper", "JUNOS"],
            "netgear": ["NETGEAR", "Netgear"],
            "linksys": ["Linksys"],
            "dlink": ["D-Link", "DLink"],
            "tplink": ["TP-Link", "TP-LINK"],
            "ubiquiti": ["Ubiquiti", "UniFi"],
            "mikrotik": ["MikroTik", "RouterOS"],
            "fortinet": ["Fortinet", "FortiGate"],
            "paloalto": ["Palo Alto", "PAN-OS"],
            "aruba": ["Aruba"],
            "extreme": ["Extreme", "ExtremeXOS"],
        }

        sys_descr_lower = sys_descr.lower()

        for manufacturer, patterns in manufacturers.items():
            for pattern in patterns:
                if pattern.lower() in sys_descr_lower:
                    device.manufacturer = manufacturer.title()
                    return

    def _extract_manufacturer_from_snmp(
        self, snmp_data: Dict[str, str]
    ) -> Optional[str]:
        """
        Extract manufacturer information from SNMP data.

        Args:
            snmp_data: SNMP OID-value pairs

        Returns:
            Manufacturer name or None
        """
        # Get system description (most informative OID)
        sys_descr = snmp_data.get("1.3.6.1.2.1.1.1.0", "")

        if sys_descr:
            # Common manufacturer patterns in system descriptions
            manufacturers = {
                "cisco": ["Cisco", "IOS"],
                "hp": ["HP", "Hewlett", "Packard"],
                "dell": ["Dell"],
                "juniper": ["Juniper", "JUNOS"],
                "netgear": ["NETGEAR", "Netgear"],
                "linksys": ["Linksys"],
                "dlink": ["D-Link", "DLink"],
                "tplink": ["TP-Link", "TP-LINK"],
                "ubiquiti": ["Ubiquiti", "UniFi"],
                "mikrotik": ["MikroTik", "RouterOS"],
                "fortinet": ["Fortinet", "FortiGate"],
                "paloalto": ["Palo Alto", "PAN-OS"],
                "aruba": ["Aruba"],
                "extreme": ["Extreme", "ExtremeXOS"],
            }

            sys_descr_lower = sys_descr.lower()

            for manufacturer, patterns in manufacturers.items():
                for pattern in patterns:
                    if pattern.lower() in sys_descr_lower:
                        return manufacturer.title()

        return None

    def parse_results(self, raw_output: str) -> List[DeviceInfo]:
        """
        Parse raw SNMP scanner output into DeviceInfo objects.

        Args:
            raw_output: Raw output from SNMP scanning

        Returns:
            List of DeviceInfo objects
        """
        devices = []

        # Split by device sections
        sections = raw_output.split("=== SNMP Scan: ")

        for section in sections[1:]:  # Skip first empty section
            if not section.strip():
                continue

            lines = section.split("\n")
            if not lines:
                continue

            # Extract IP address from section header
            header = lines[0].strip()
            if header.endswith(" ==="):
                ip_address = header.replace(" ===", "").strip()
            else:
                # If no closing ===, assume the whole header is the IP
                ip_address = header.strip()

            # Parse SNMP data from the section
            snmp_data = {}
            current_oid_base = None

            for line in lines[1:]:
                if not line.strip():
                    continue

                if line.strip().startswith("OID Walk:"):
                    current_oid_base = line.replace("OID Walk:", "").strip()
                elif line.startswith("  ") and " = " in line:
                    # Parse OID-value pair
                    oid_value = line.strip()
                    if " = " in oid_value:
                        oid, value = oid_value.split(" = ", 1)
                        snmp_data[oid] = value

            if snmp_data:
                device = DeviceInfo(
                    ip_address=ip_address,
                    device_type=DeviceType.NETWORK_EQUIPMENT,
                    snmp_data=snmp_data,
                )
                self._enrich_device_info(device, snmp_data)
                devices.append(device)

        return devices

    def _is_valid_target(self, target: str) -> bool:
        """
        Enhanced target validation for SNMP scanner.

        Args:
            target: IP address to validate

        Returns:
            True if target is a valid IP address, False otherwise
        """
        if not super()._is_valid_target(target):
            return False

        # SNMP scanner only works with IP addresses
        parts = target.strip().split(".")
        if len(parts) != 4:
            return False

        try:
            for part in parts:
                num = int(part)
                if not 0 <= num <= 255:
                    return False
            return True
        except ValueError:
            return False
