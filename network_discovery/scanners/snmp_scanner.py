"""
SNMP Scanner implementation for Network Discovery Module.

This module implements SNMP-based device discovery using the pysnmp library
to perform SNMP walks and retrieve device information from SNMP-enabled devices.
"""

import asyncio
import time
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

try:
    # pysnmp 7.x - use v3arch.asyncio for async operations
    from pysnmp.hlapi.v3arch.asyncio import (
        SnmpEngine,
        CommunityData,
        UsmUserData,
        UdpTransportTarget,
        ContextData,
        ObjectType,
        ObjectIdentity,
        walk_cmd,
        get_cmd,
        usmNoAuthProtocol,
        usmNoPrivProtocol,
    )
    from pysnmp.error import PySnmpError

    PYSNMP_AVAILABLE = True
except ImportError:
    PYSNMP_AVAILABLE = False

    # Define dummy classes for type hints when pysnmp is not available
    class CommunityData:
        pass

    class SnmpEngine:
        pass

    class UdpTransportTarget:
        pass


from .base_scanner import BaseScanner, ScanResult
from ..core.data_models import DeviceInfo, ScanStatus, DeviceType
from ..config.config_loader import SNMPConfig
from ..utils.logger import Logger


class SNMPScanner(BaseScanner):
    """
    SNMP scanner implementation for discovering and querying SNMP-enabled devices.

    This scanner performs SNMP walks on devices with open SNMP ports (161/UDP)
    to retrieve detailed device information including system info, interfaces,
    and network configuration.
    """

    def __init__(self, logger: Optional[Logger] = None, error_handler=None):
        """
        Initialize the SNMP scanner.

        Args:
            logger: Logger instance for outputting scan progress and errors
            error_handler: ErrorHandler instance for centralized error management
        """
        super().__init__(logger, error_handler)
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
        scan_status = ScanStatus.COMPLETED
        if errors and not devices:
            scan_status = ScanStatus.FAILED
        elif errors:
            scan_status = ScanStatus.PARTIAL

        self._log_info(
            f"SNMP scan completed. Found {len(devices)} devices in {scan_duration:.2f}s"
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
                "max_oids_per_request": config.max_oids_per_request,
                "max_walk_oids": config.max_walk_oids,
                "walk_oids": config.walk_oids,
                "specific_oids_count": len(config.specific_oids),
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

        # Join all raw output with proper separation between devices
        formatted_raw_output = "\n\n".join(all_raw_output)
        return devices, errors, formatted_raw_output

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
        # Try different SNMP versions and communities
        for version in config.versions:
            for community in config.communities:
                try:
                    # Run async SNMP walk in sync context
                    snmp_data, raw_output = asyncio.run(
                        self._async_snmp_walk(target, community, version, config)
                    )

                    if snmp_data:
                        # Create DeviceInfo with SNMP data
                        device = DeviceInfo(
                            ip_address=target,
                            device_type=DeviceType.UNKNOWN,  # Will be classified by DeviceClassifier
                            snmp_data=snmp_data,
                        )

                        # Extract additional info from SNMP data
                        self._enrich_device_info(device, snmp_data)

                        self._log_info(
                            f"SNMP scan successful for {target} (v{version}, {len(snmp_data)} OIDs)"
                        )
                        return device, None, raw_output

                except Exception as e:
                    self._log_debug(
                        f"SNMP v{version}/{community} failed for {target}: {str(e)}"
                    )
                    continue

        # No successful SNMP connection
        error_msg = f"No SNMP response from {target}"
        return None, error_msg, ""

    async def _async_snmp_walk(
        self,
        target: str,
        community: str,
        version: int,
        config: SNMPConfig,
    ) -> Tuple[Dict[str, str], str]:
        """
        Perform async SNMP walk using pysnmp 7.x async API.

        Args:
            target: Target IP address
            community: SNMP community string
            version: SNMP version (1, 2, or 3)
            config: SNMP configuration

        Returns:
            Tuple of (oid_value_dict, raw_output_string)
        """
        snmp_data = {}
        raw_output_lines = []

        try:
            # Configure SNMP version and authentication
            auth_data = self._create_auth_data(community, version)

            # Create transport target using .create() method for pysnmp 7.x
            transport_target = await UdpTransportTarget.create(
                (target, 161), timeout=config.timeout, retries=config.retries
            )

            context_data = ContextData()
            snmp_engine = SnmpEngine()
            try:
                # Walk each configured OID
                for base_oid in config.walk_oids:
                    try:
                        oid_data = await self._async_walk_oid(
                            snmp_engine,
                            auth_data,
                            transport_target,
                            context_data,
                            base_oid,
                            config,
                        )
                        snmp_data |= oid_data

                        # Add to raw output with proper formatting
                        raw_output_lines.append(f"OID Walk: {base_oid}")
                        for oid, value in oid_data.items():
                            raw_output_lines.append(f"  {oid} = {value}")

                    except Exception as e:
                        error_msg = f"Error walking OID {base_oid}: {str(e)}"
                        self._log_debug(error_msg)
                        raw_output_lines.append(
                            f"OID Walk: {base_oid} - ERROR: {error_msg}"
                        )

                # Query specific OIDs
                if config.specific_oids:
                    raw_output_lines.append("Specific OID Queries:")
                    specific_data = await self._async_query_specific_oids(
                        snmp_engine,
                        auth_data,
                        transport_target,
                        context_data,
                        config.specific_oids,
                        config,
                    )

                    # Format output for specific OIDs
                    for oid_info in config.specific_oids:
                        oid = oid_info.get("oid")
                        name = oid_info.get("name", oid)

                        if oid in specific_data:
                            value = specific_data[oid]
                            if len(value) > 100:
                                value = value[:97] + "..."
                            raw_output_lines.append(f"  {name} ({oid}) = {value}")
                        elif oid in snmp_data:
                            specific_data[oid] = snmp_data[oid]
                            value = snmp_data[oid]
                            if len(value) > 100:
                                value = value[:97] + "..."
                            raw_output_lines.append(
                                f"  {name} ({oid}) = {value} (from walk)"
                            )

                    snmp_data |= specific_data

            finally:
                snmp_engine.close_dispatcher()

        except Exception as e:
            error_msg = f"SNMP walk failed for {target}: {str(e)}"
            self._log_debug(error_msg)
            raw_output_lines.append(f"Error: {error_msg}")

        # Join all output lines with proper line breaks
        formatted_output = "\n".join(raw_output_lines)
        return snmp_data, formatted_output

    def _create_auth_data(self, community: str, version: int) -> Any:
        """
        Create authentication data based on SNMP version.

        Args:
            community: SNMP community string or username for v3
            version: SNMP version (1, 2, or 3)

        Returns:
            Authentication data object
        """
        if version == 1:
            return CommunityData(community, mpModel=0)  # SNMPv1
        elif version == 2:
            return CommunityData(community, mpModel=1)  # SNMPv2c
        elif version == 3:
            # SNMPv3 - simplified implementation (noAuthNoPriv)
            return UsmUserData(
                userName=community,
                authKey=None,
                privKey=None,
                authProtocol=usmNoAuthProtocol,
                privProtocol=usmNoPrivProtocol,
            )
        else:
            raise ValueError(f"Unsupported SNMP version: {version}")

    async def _async_walk_oid(
        self,
        snmp_engine: SnmpEngine,
        auth_data: Any,
        transport_target: UdpTransportTarget,
        context_data: ContextData,
        base_oid: str,
        config: SNMPConfig,
    ) -> Dict[str, str]:
        """
        Walk a specific OID tree using async API.

        Args:
            snmp_engine: SNMP engine instance
            auth_data: Authentication data (community or USM)
            transport_target: UDP transport target
            context_data: SNMP context data
            base_oid: Base OID to walk
            config: SNMP configuration

        Returns:
            Dictionary of OID-value pairs
        """
        oid_data = {}

        try:
            # Create async iterator for SNMP walk
            iterator = walk_cmd(
                snmp_engine,
                auth_data,
                transport_target,
                context_data,
                ObjectType(ObjectIdentity(base_oid)),
                lookupMib=False,
                lexicographicMode=False,  # Stop at end of subtree
                ignoreNonIncreasingOid=True,
            )

            # Iterate through results
            async for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                # Check for errors
                if errorIndication:
                    self._log_debug(f"SNMP error indication: {errorIndication}")
                    break

                if errorStatus:
                    problematic = (
                        varBinds[int(errorIndex) - 1][0] if errorIndex else "?"
                    )
                    self._log_debug(
                        f"SNMP error status: {errorStatus.prettyPrint()} at {problematic}"
                    )
                    break

                # Process variable bindings
                for name, value in varBinds:
                    oid_str = name.prettyPrint()
                    value_str = value.prettyPrint()

                    # Stop if we've walked beyond the base OID
                    if not oid_str.startswith(base_oid):
                        break

                    oid_data[oid_str] = value_str

                    # Limit the number of OIDs to prevent excessive data (configurable)
                    max_walk_oids = getattr(config, "max_walk_oids", 1000)
                    if len(oid_data) >= max_walk_oids:
                        self._log_debug(
                            f"Reached OID limit ({max_walk_oids}) for base OID {base_oid}"
                        )
                        return oid_data

        except PySnmpError as e:
            self._log_debug(f"PySnmp error walking {base_oid}: {str(e)}")
        except Exception as e:
            self._log_debug(f"Unexpected error walking {base_oid}: {str(e)}")

        return oid_data

    async def _async_query_specific_oids(
        self,
        snmp_engine: SnmpEngine,
        auth_data: Any,
        transport_target: UdpTransportTarget,
        context_data: ContextData,
        specific_oids: list,
        config: SNMPConfig,
    ) -> Dict[str, str]:
        """
        Query specific OIDs using async GET requests.

        Args:
            snmp_engine: SNMP engine instance
            auth_data: Authentication data (community or USM)
            transport_target: UDP transport target
            context_data: SNMP context data
            specific_oids: List of OID configurations to query
            config: SNMP configuration for batching parameters

        Returns:
            Dictionary of OID-value pairs for successful queries only
        """
        oid_data = {}

        # Process each OID individually using simple GET
        for oid_config in specific_oids:
            oid = oid_config.get("oid")
            name = oid_config.get("name", oid)

            if not oid:
                self._log_debug(
                    f"Skipping OID config without 'oid' field: {oid_config}"
                )
                continue

            try:
                # Use simple GET command
                result = await asyncio.wait_for(
                    get_cmd(
                        snmp_engine,
                        auth_data,
                        transport_target,
                        context_data,
                        ObjectType(ObjectIdentity(oid)),
                        lookupMib=False,
                    ),
                    timeout=5.0,
                )

                errorIndication, errorStatus, errorIndex, varBinds = result

                if errorIndication or errorStatus:
                    continue

                # Process successful response
                for var_name, var_value in varBinds:
                    oid_str = var_name.prettyPrint()
                    value_str = var_value.prettyPrint()

                    if value_str and not value_str.startswith("No Such"):
                        oid_data[oid_str] = value_str

            except (asyncio.TimeoutError, Exception):
                continue

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
        # Extract system description for OS info
        for oid, value in snmp_data.items():
            if oid == "1.3.6.1.2.1.1.1.0":  # sysDescr
                device.os_info = value
            elif oid == "1.3.6.1.2.1.1.5.0":  # sysName
                device.hostname = value

        # Extract manufacturer info
        device.manufacturer = self._extract_manufacturer_from_snmp(snmp_data)

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
        if sys_descr := snmp_data.get("1.3.6.1.2.1.1.1.0", ""):
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
