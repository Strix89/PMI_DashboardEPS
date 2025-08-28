"""
Scanner Orchestrator for Network Discovery Module.

This module provides the ScannerOrchestrator class that manages the complete
scan pipeline, coordinating ARP → NMAP → SNMP sequence, merging results,
and handling errors with recovery mechanisms.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import asdict

from .data_models import (
    CompleteScanResult,
    ScanMetadata,
    ScanStatistics,
    DeviceInfo,
    NetworkInfo,
    ScanStatus,
    DeviceType,
)
from .network_detector import NetworkDetector
from .device_classifier import DeviceClassifier
from ..scanners.arp_scanner import ARPScanner
from ..scanners.nmap_scanner import NMAPScanner
from ..scanners.snmp_scanner import SNMPScanner
from ..scanners.base_scanner import ScanResult
from ..config.config_loader import ConfigLoader, ARPConfig, NMAPConfig, SNMPConfig
from ..utils.logger import Logger, get_logger
from ..utils.json_reporter import JSONReporter


class ScannerOrchestrator:
    """
    Orchestrates the complete network discovery scan pipeline.

    This class manages the execution of ARP → NMAP → SNMP scanning sequence,
    merges results from different scanners by IP address, provides progress
    tracking and logging throughout the pipeline, and handles error recovery
    for failed scan phases.
    """

    def __init__(
        self,
        config_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        skip_arp: bool = False,
    ):
        """
        Initialize the scanner orchestrator.

        Args:
            config_dir: Directory containing configuration files (optional)
            output_dir: Directory for output files (optional)
            skip_arp: Skip ARP scan phase (optional)
        """
        self.logger = get_logger(__name__)

        # Initialize components
        self.network_detector = NetworkDetector()
        self.device_classifier = DeviceClassifier()
        self.config_loader = ConfigLoader(config_dir)
        self.json_reporter = JSONReporter(output_dir or "network_discovery/results")

        # Initialize scanners
        self.arp_scanner = ARPScanner(self.logger)
        self.nmap_scanner = NMAPScanner(self.logger)
        self.snmp_scanner = SNMPScanner(self.logger)

        # Skip flags
        self.skip_arp = skip_arp

        # Scan state
        self.scan_start_time: Optional[datetime] = None
        self.network_info: Optional[NetworkInfo] = None
        self.configurations: Dict[str, Any] = {}

    def execute_full_scan(self) -> CompleteScanResult:
        """
        Execute the complete scan pipeline: ARP → NMAP → SNMP.

        Performs network detection, loads configurations, executes all scan phases,
        merges results, classifies devices, and generates the final report.

        Returns:
            CompleteScanResult: Complete scan results with all discovered devices

        Raises:
            RuntimeError: If critical scan phases fail
        """
        self.logger.section("NETWORK DISCOVERY SCAN")
        self.scan_start_time = datetime.now()

        try:
            # Phase 1: Network Detection and Configuration
            self.logger.info("Phase 1: Network detection and configuration loading")
            self._detect_network_configuration()
            self._load_configurations()

            # Phase 2: Execute scan pipeline
            self.logger.info("Phase 2: Executing scan pipeline")

            # Execute ARP scan (or skip)
            if self.skip_arp:
                self.logger.info("Skipping ARP scan phase as requested")
                arp_results = ScanResult(
                    scanner_type="arp",
                    scan_status=ScanStatus.COMPLETED,
                    devices_found=[],
                    scan_duration=0.0,
                    errors=["ARP scan skipped by user"],
                )
            else:
                arp_results = self._execute_arp_scan()

            # Execute NMAP scan - always scan full range now
            nmap_results = self._execute_nmap_scan_full_range()

            # Execute SNMP scan
            snmp_results = self._execute_snmp_scan(nmap_results)

            # Phase 3: Merge and classify results
            self.logger.info("Phase 3: Merging results and classifying devices")
            merged_devices = self._merge_scan_results(
                arp_results, nmap_results, snmp_results
            )
            classified_devices = self._classify_devices(merged_devices)

            # Phase 4: Generate final report
            self.logger.info("Phase 4: Generating final report")
            scan_result = self._create_complete_scan_result(
                classified_devices, arp_results, nmap_results, snmp_results
            )

            # Generate JSON report
            report_path = self.json_reporter.generate_report(scan_result)
            self.logger.success(
                f"Scan completed successfully. Report saved to: {report_path}"
            )

            return scan_result

        except Exception as e:
            self.logger.error(f"Scan pipeline failed: {str(e)}", exception=e)
            # Create a failed scan result for partial data
            return self._create_failed_scan_result(str(e))

    def _detect_network_configuration(self) -> None:
        """Detect network configuration and prepare scan targets."""
        self.logger.progress_start("Detecting network configuration")

        try:
            self.network_info = self.network_detector.get_host_network_info()

            # Display network information
            self.logger.network_info(
                network=f"{self.network_info.network_address}/{self.network_info.netmask}",
                host_ip=self.network_info.host_ip,
                excluded=[
                    self.network_info.network_address,
                    self.network_info.host_ip,
                    self.network_info.broadcast_address,
                ],
            )

            self.logger.progress_end(
                f"Network detection completed. Scan range: {len(self.network_info.scan_range)} addresses"
            )

        except Exception as e:
            self.logger.progress_end()
            self.logger.error(f"Network detection failed: {str(e)}", exception=e)
            raise RuntimeError(
                f"Cannot proceed without network configuration: {str(e)}"
            )

    def _load_configurations(self) -> None:
        """Load scanner configurations from YAML files."""
        self.logger.progress_start("Loading scanner configurations")

        try:
            # Load all configurations
            arp_config = self.config_loader.load_arp_config()
            nmap_config = self.config_loader.load_nmap_config()
            snmp_config = self.config_loader.load_snmp_config()

            # Store configurations for metadata
            self.configurations = {
                "arp": asdict(arp_config),
                "nmap": asdict(nmap_config),
                "snmp": asdict(snmp_config),
            }

            self.logger.progress_end("Configuration loading completed")
            self.logger.info(
                f"Loaded configurations: ARP ({arp_config.method}), NMAP ({nmap_config.scan_type}), SNMP (v{snmp_config.versions})"
            )

        except Exception as e:
            self.logger.progress_end()
            self.logger.error(f"Configuration loading failed: {str(e)}", exception=e)
            raise RuntimeError(f"Cannot proceed without valid configurations: {str(e)}")

    def _execute_arp_scan(self) -> ScanResult:
        """
        Execute ARP scan phase.

        Returns:
            ScanResult: ARP scan results
        """
        self.logger.section("ARP SCAN PHASE")

        try:
            arp_config = self.config_loader.load_arp_config()

            self.logger.info(
                f"Starting ARP scan of {len(self.network_info.scan_range)} targets"
            )
            self.logger.progress_start(f"ARP scanning using {arp_config.method} method")

            arp_results = self.arp_scanner.scan(
                self.network_info.scan_range, arp_config
            )

            self.logger.progress_end()

            if arp_results.scan_status == ScanStatus.FAILED:
                self.logger.warning(
                    "ARP scan failed completely - will use NMAP for discovery"
                )
                if arp_results.errors:
                    for error in arp_results.errors:
                        self.logger.warning(f"ARP Warning: {error}")

            elif arp_results.scan_status == ScanStatus.PARTIAL:
                self.logger.warning(
                    f"ARP scan completed with errors. Found {len(arp_results.devices_found)} devices"
                )
                for error in arp_results.errors:
                    self.logger.warning(f"ARP Warning: {error}")

            else:
                self.logger.success(
                    f"ARP scan completed successfully. Found {len(arp_results.devices_found)} active devices"
                )

            # Log discovered devices
            if arp_results.devices_found:
                self.logger.info("Active devices discovered:")
                for device in arp_results.devices_found:
                    mac_info = f" ({device.mac_address})" if device.mac_address else ""
                    self.logger.info(f"  • {device.ip_address}{mac_info}")

            return arp_results

        except Exception as e:
            self.logger.error(f"ARP scan phase failed: {str(e)}", exception=e)
            raise

    def _execute_nmap_scan(self, arp_results: ScanResult) -> ScanResult:
        """
        Execute NMAP scan phase on devices discovered by ARP.

        Args:
            arp_results: Results from ARP scan

        Returns:
            ScanResult: NMAP scan results
        """
        self.logger.section("NMAP SCAN PHASE")

        # If ARP found no devices, use NMAP for discovery on the full network range
        if not arp_results.devices_found:
            self.logger.info(
                "No devices from ARP scan - using NMAP for full network discovery"
            )
            target_ips = self.network_info.scan_range  # Scan the entire network range
            self.logger.info(
                f"NMAP will scan {len(target_ips)} addresses for discovery"
            )
        else:
            # Extract IP addresses from ARP results
            target_ips = [device.ip_address for device in arp_results.devices_found]
            self.logger.info(f"NMAP will scan {len(target_ips)} devices found by ARP")

        try:
            nmap_config = self.config_loader.load_nmap_config()

            self.logger.info(f"Starting NMAP scan of {len(target_ips)} targets")
            self.logger.progress_start(
                f"NMAP scanning with {nmap_config.scan_type} scan type"
            )

            nmap_results = self.nmap_scanner.scan(target_ips, nmap_config)

            self.logger.progress_end()

            if nmap_results.scan_status == ScanStatus.FAILED:
                self.logger.error("NMAP scan failed completely")
                if nmap_results.errors:
                    for error in nmap_results.errors:
                        self.logger.error(f"NMAP Error: {error}")
                # Don't raise exception - continue with ARP-only data

            elif nmap_results.scan_status == ScanStatus.PARTIAL:
                self.logger.warning(
                    f"NMAP scan completed with errors. Scanned {len(nmap_results.devices_found)} devices"
                )
                for error in nmap_results.errors:
                    self.logger.warning(f"NMAP Warning: {error}")

            else:
                self.logger.success(
                    f"NMAP scan completed successfully. Scanned {len(nmap_results.devices_found)} devices"
                )

            # All devices found by NMAP will be tested for SNMP
            if nmap_results.devices_found:
                self.logger.info(
                    f"Found {len(nmap_results.devices_found)} devices - all will be tested for SNMP"
                )

            return nmap_results

        except Exception as e:
            self.logger.error(f"NMAP scan phase failed: {str(e)}", exception=e)
            # Return empty result instead of failing completely
            return ScanResult(
                scanner_type="nmap",
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=0.0,
                errors=[f"NMAP scan failed: {str(e)}"],
            )

    def _execute_nmap_scan_full_range(self) -> ScanResult:
        """
        Execute NMAP scan on the full network range (not just ARP results).

        Returns:
            ScanResult: NMAP scan results
        """
        self.logger.section("NMAP SCAN PHASE")

        try:
            nmap_config = self.config_loader.load_nmap_config()

            # Use the full scan range from network detection
            target_ips = self.network_info.scan_range

            self.logger.info(
                f"NMAP will scan the full network range ({len(target_ips)} addresses)"
            )
            self.logger.info(f"Starting NMAP scan of {len(target_ips)} targets")
            self.logger.progress_start(
                f"NMAP scanning full range with {nmap_config.scan_type} scan type"
            )

            nmap_results = self.nmap_scanner.scan(target_ips, nmap_config)

            self.logger.progress_end()

            if nmap_results.scan_status == ScanStatus.FAILED:
                self.logger.error("NMAP scan failed completely")
                if nmap_results.errors:
                    for error in nmap_results.errors:
                        self.logger.error(f"NMAP Error: {error}")

            elif nmap_results.scan_status == ScanStatus.PARTIAL:
                self.logger.warning(
                    f"NMAP scan completed with errors. Scanned {len(nmap_results.devices_found)} devices"
                )
                for error in nmap_results.errors:
                    self.logger.warning(f"NMAP Warning: {error}")

            else:
                self.logger.success(
                    f"NMAP scan completed successfully. Found {len(nmap_results.devices_found)} devices"
                )

            # Log SNMP-enabled devices
            snmp_devices = self.nmap_scanner.get_snmp_enabled_devices()
            if snmp_devices:
                self.logger.info(
                    f"Found {len(snmp_devices)} SNMP-enabled devices for detailed scanning"
                )

            return nmap_results

        except Exception as e:
            self.logger.error(f"NMAP scan phase failed: {str(e)}", exception=e)
            # Return empty result instead of failing completely
            return ScanResult(
                scanner_type="nmap",
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=0.0,
                errors=[f"NMAP scan failed: {str(e)}"],
            )

    def _execute_snmp_scan(self, nmap_results: ScanResult) -> ScanResult:
        """
        Execute SNMP scan phase on devices with SNMP enabled.

        Args:
            nmap_results: Results from NMAP scan

        Returns:
            ScanResult: SNMP scan results
        """
        self.logger.section("SNMP SCAN PHASE")

        # Use all devices found by NMAP for SNMP scanning (not just port 161)
        if nmap_results.devices_found:
            snmp_targets = [device.ip_address for device in nmap_results.devices_found]
            self.logger.info(
                f"Will attempt SNMP scan on all {len(snmp_targets)} devices found by NMAP"
            )
        else:
            self.logger.info("No devices found by NMAP - skipping SNMP scan")
            return ScanResult(
                scanner_type="snmp",
                scan_status=ScanStatus.COMPLETED,
                devices_found=[],
                scan_duration=0.0,
                errors=[],
            )

        try:
            snmp_config = self.config_loader.load_snmp_config()

            self.logger.info(
                f"Starting SNMP scan of {len(snmp_targets)} SNMP-enabled devices"
            )
            self.logger.progress_start(
                f"SNMP scanning with versions {snmp_config.versions}"
            )

            snmp_results = self.snmp_scanner.scan(snmp_targets, snmp_config)

            self.logger.progress_end()

            if snmp_results.scan_status == ScanStatus.FAILED:
                self.logger.warning("SNMP scan failed completely")
                if snmp_results.errors:
                    for error in snmp_results.errors:
                        self.logger.warning(f"SNMP Error: {error}")

            elif snmp_results.scan_status == ScanStatus.PARTIAL:
                self.logger.warning(
                    f"SNMP scan completed with errors. Retrieved data from {len(snmp_results.devices_found)} devices"
                )
                for error in snmp_results.errors:
                    self.logger.warning(f"SNMP Warning: {error}")

            else:
                self.logger.success(
                    f"SNMP scan completed successfully. Retrieved data from {len(snmp_results.devices_found)} devices"
                )

            return snmp_results

        except Exception as e:
            self.logger.error(f"SNMP scan phase failed: {str(e)}", exception=e)
            # Return empty result instead of failing completely
            return ScanResult(
                scanner_type="snmp",
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=0.0,
                errors=[f"SNMP scan failed: {str(e)}"],
            )

    def _merge_scan_results(
        self,
        arp_results: ScanResult,
        nmap_results: ScanResult,
        snmp_results: ScanResult,
    ) -> Dict[str, DeviceInfo]:
        """
        Merge results from different scanners by IP address.

        Args:
            arp_results: ARP scan results
            nmap_results: NMAP scan results
            snmp_results: SNMP scan results

        Returns:
            Dict mapping IP addresses to merged DeviceInfo objects
        """
        self.logger.progress_start("Merging scan results")

        merged_devices = {}

        # Start with ARP results as the base (active devices)
        for device in arp_results.devices_found:
            merged_devices[device.ip_address] = DeviceInfo(
                ip_address=device.ip_address,
                mac_address=device.mac_address,
                hostname=device.hostname,
                device_type=DeviceType.UNKNOWN,
            )

        # Merge NMAP results
        for device in nmap_results.devices_found:
            ip = device.ip_address

            if ip not in merged_devices:
                # Device found by NMAP but not ARP (shouldn't happen in normal flow)
                merged_devices[ip] = DeviceInfo(
                    ip_address=ip, device_type=DeviceType.UNKNOWN
                )

            # Update with NMAP data
            merged_device = merged_devices[ip]
            merged_device.os_info = device.os_info
            merged_device.open_ports = device.open_ports.copy()
            merged_device.services = device.services.copy()

            # Update hostname if not set and available from NMAP
            if not merged_device.hostname and device.hostname:
                merged_device.hostname = device.hostname

        # Merge SNMP results
        for device in snmp_results.devices_found:
            ip = device.ip_address

            if ip in merged_devices:
                merged_device = merged_devices[ip]
                merged_device.snmp_data = device.snmp_data

                # Update manufacturer and model from SNMP if available
                if device.manufacturer:
                    merged_device.manufacturer = device.manufacturer
                if device.model:
                    merged_device.model = device.model

        self.logger.progress_end(f"Merged results for {len(merged_devices)} devices")
        return merged_devices

    def _classify_devices(self, devices: Dict[str, DeviceInfo]) -> List[DeviceInfo]:
        """
        Classify devices using the device classifier.

        Args:
            devices: Dictionary of merged device information

        Returns:
            List of DeviceInfo objects with classifications
        """
        self.logger.progress_start("Classifying devices")

        classified_devices = []

        for ip, device in devices.items():
            # Classify the device
            device.device_type = self.device_classifier.classify_device(device)

            # If we have SNMP data and it's network equipment, try to get manufacturer/model
            if (
                device.device_type == DeviceType.NETWORK_EQUIPMENT
                and device.snmp_data
                and not device.manufacturer
            ):

                manufacturer, model = self.device_classifier.identify_network_equipment(
                    device.snmp_data
                )
                if manufacturer:
                    device.manufacturer = manufacturer
                if model:
                    device.model = model

            classified_devices.append(device)

        # Sort devices by IP address for consistent output
        classified_devices.sort(
            key=lambda d: tuple(int(part) for part in d.ip_address.split("."))
        )

        self.logger.progress_end(f"Classified {len(classified_devices)} devices")

        # Log classification summary
        type_counts = {}
        for device in classified_devices:
            device_type = device.device_type.value
            type_counts[device_type] = type_counts.get(device_type, 0) + 1

        self.logger.info("Device classification summary:")
        for device_type, count in type_counts.items():
            self.logger.info(f"  • {device_type}: {count} devices")

        return classified_devices

    def _create_complete_scan_result(
        self,
        devices: List[DeviceInfo],
        arp_results: ScanResult,
        nmap_results: ScanResult,
        snmp_results: ScanResult,
    ) -> CompleteScanResult:
        """
        Create the complete scan result structure.

        Args:
            devices: List of classified devices
            arp_results: ARP scan results
            nmap_results: NMAP scan results
            snmp_results: SNMP scan results

        Returns:
            CompleteScanResult: Complete scan result structure
        """
        scan_end_time = datetime.now()
        total_duration = (scan_end_time - self.scan_start_time).total_seconds()

        # Create scan metadata
        scan_metadata = ScanMetadata(
            timestamp=self.scan_start_time,
            scan_duration=total_duration,
            network_scanned=f"{self.network_info.network_address}/{self.network_info.netmask}",
            host_ip=self.network_info.host_ip,
            excluded_addresses=[
                self.network_info.network_address,
                self.network_info.host_ip,
                self.network_info.broadcast_address,
            ],
            configurations_used=self.configurations,
            scan_status=ScanStatus.COMPLETED,
        )

        # Create scan statistics
        scan_statistics = ScanStatistics(
            total_addresses_scanned=len(self.network_info.scan_range),
            devices_found={
                "arp": len(arp_results.devices_found),
                "nmap": len(nmap_results.devices_found),
                "snmp": len(snmp_results.devices_found),
                "total": len(devices),
            },
            scan_times={
                "arp_duration": arp_results.scan_duration,
                "nmap_duration": nmap_results.scan_duration,
                "snmp_duration": snmp_results.scan_duration,
                "total_duration": total_duration,
            },
            errors_encountered=arp_results.errors
            + nmap_results.errors
            + snmp_results.errors,
        )

        return CompleteScanResult(
            scan_metadata=scan_metadata,
            network_info=self.network_info,
            devices=devices,
            scan_statistics=scan_statistics,
        )

    def _create_failed_scan_result(self, error_message: str) -> CompleteScanResult:
        """
        Create a failed scan result for error cases.

        Args:
            error_message: Error message describing the failure

        Returns:
            CompleteScanResult: Failed scan result structure
        """
        scan_end_time = datetime.now()
        total_duration = (
            (scan_end_time - self.scan_start_time).total_seconds()
            if self.scan_start_time
            else 0.0
        )

        # Create minimal metadata for failed scan
        scan_metadata = ScanMetadata(
            timestamp=self.scan_start_time or datetime.now(),
            scan_duration=total_duration,
            network_scanned="",
            host_ip="",
            excluded_addresses=[],
            configurations_used=self.configurations,
            scan_status=ScanStatus.FAILED,
        )

        # Create minimal statistics for failed scan
        scan_statistics = ScanStatistics(
            total_addresses_scanned=0,
            devices_found={"total": 0},
            scan_times={"total_duration": total_duration},
            errors_encountered=[error_message],
        )

        # Create minimal network info
        network_info = self.network_info or NetworkInfo(
            host_ip="",
            netmask="",
            network_address="",
            broadcast_address="",
            interface_name="",
            scan_range=[],
        )

        return CompleteScanResult(
            scan_metadata=scan_metadata,
            network_info=network_info,
            devices=[],
            scan_statistics=scan_statistics,
        )
