"""
ARP Scanner implementation for Network Discovery Module.

This module implements ARP-based device discovery using either arping command
or scapy library, with parallel scanning capabilities and configurable parameters.
"""

import subprocess
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
import time

from .base_scanner import BaseScanner, ScanResult
from ..core.data_models import DeviceInfo, ScanStatus, DeviceType
from ..config.config_loader import ARPConfig
from ..utils.logger import Logger


class ARPScanner(BaseScanner):
    """
    ARP scanner implementation supporting both arping and scapy methods.
    
    This scanner discovers active devices on the network by sending ARP requests
    and parsing the responses to extract IP and MAC addresses. It supports
    parallel scanning for improved performance.
    """
    
    def __init__(self, logger: Optional[Logger] = None, error_handler=None):
        """
        Initialize the ARP scanner.
        
        Args:
            logger: Logger instance for outputting scan progress and errors
            error_handler: ErrorHandler instance for centralized error management
        """
        super().__init__(logger, error_handler)
        self.scanner_type = "ARP"
        self._lock = threading.Lock()
        self._scapy_available = self._check_scapy_availability()
    
    def scan(self, targets: List[str], config: ARPConfig) -> ScanResult:
        """
        Execute ARP scan on the specified targets.
        
        Args:
            targets: List of IP addresses to scan
            config: ARP configuration object
            
        Returns:
            ScanResult containing discovered devices and scan metadata
        """
        self._log_info(f"Starting ARP scan of {len(targets)} targets using {config.method} method")
        self._start_scan_timer()
        
        # Validate targets
        valid_targets = self.validate_targets(targets)
        if not valid_targets:
            return ScanResult(
                scanner_type=self.scanner_type,
                scan_status=ScanStatus.FAILED,
                devices_found=[],
                scan_duration=self._end_scan_timer(),
                errors=["No valid targets to scan"]
            )
        
        # Choose scanning method based on configuration
        if config.method == "scapy" and self._scapy_available:
            devices, errors, raw_output = self._scan_with_scapy(valid_targets, config)
        elif config.method == "ping":
            devices, errors, raw_output = self._scan_with_ping(valid_targets, config)
        else:
            if config.method == "scapy" and not self._scapy_available:
                self._log_warning("Scapy not available, falling back to ping method")
            devices, errors, raw_output = self._scan_with_ping(valid_targets, config)
        
        scan_duration = self._end_scan_timer()
        
        # Determine scan status
        if errors and not devices:
            scan_status = ScanStatus.FAILED
        elif errors and devices:
            scan_status = ScanStatus.PARTIAL
        else:
            scan_status = ScanStatus.COMPLETED
        
        self._log_info(f"ARP scan completed. Found {len(devices)} devices in {scan_duration:.2f} seconds")
        
        return ScanResult(
            scanner_type=self.scanner_type,
            scan_status=scan_status,
            devices_found=devices,
            scan_duration=scan_duration,
            errors=errors,
            raw_output=raw_output,
            metadata={
                "method_used": config.method if config.method != "scapy" or self._scapy_available else "arping",
                "parallel_threads": config.parallel_threads,
                "targets_scanned": len(valid_targets),
                "timeout": config.timeout,
                "retries": config.retries
            }
        )
    
    def _scan_with_arping(self, targets: List[str], config: ARPConfig) -> Tuple[List[DeviceInfo], List[str], str]:
        """
        Perform ARP scan using arping command.
        
        Args:
            targets: List of IP addresses to scan
            config: ARP configuration
            
        Returns:
            Tuple of (devices_found, errors, raw_output)
        """
        devices = []
        errors = []
        all_raw_output = []
        
        # Use ThreadPoolExecutor for parallel scanning
        with ThreadPoolExecutor(max_workers=config.parallel_threads) as executor:
            # Submit all scan tasks
            future_to_target = {
                executor.submit(self._arping_single_target, target, config): target 
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
                        all_raw_output.append(f"=== {target} ===\n{raw_output}")
                except Exception as e:
                    error_msg = f"Exception scanning {target}: {str(e)}"
                    errors.append(error_msg)
                    self._log_error(error_msg)
        
        return devices, errors, "\n".join(all_raw_output)
    
    def _arping_single_target(self, target: str, config: ARPConfig) -> Tuple[Optional[DeviceInfo], Optional[str], str]:
        """
        Perform ARP scan on a single target using arping.
        
        Args:
            target: IP address to scan
            config: ARP configuration
            
        Returns:
            Tuple of (device_info, error_message, raw_output)
        """
        try:
            # Build arping command
            cmd = ["arping", "-c", str(config.retries), "-W", str(config.timeout)]
            
            # Add interface if specified
            if config.interface:
                cmd.extend(["-I", config.interface])
            
            cmd.append(target)
            
            # Execute arping command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout * config.retries + 5  # Add buffer time
            )
            
            raw_output = result.stdout + result.stderr
            
            # Parse arping output
            if result.returncode == 0 and result.stdout:
                device = self._parse_arping_output(target, result.stdout)
                if device:
                    return device, None, raw_output
                else:
                    return None, "Could not parse arping output", raw_output
            else:
                # No response or error
                return None, None, raw_output
                
        except subprocess.TimeoutExpired:
            return None, f"Timeout after {config.timeout * config.retries + 5} seconds", ""
        except FileNotFoundError:
            return None, "arping command not found. Please install iputils-arping or equivalent", ""
        except Exception as e:
            return None, f"Error executing arping: {str(e)}", ""
    
    def _scan_with_scapy(self, targets: List[str], config: ARPConfig) -> Tuple[List[DeviceInfo], List[str], str]:
        """
        Perform ARP scan using scapy library.
        
        Args:
            targets: List of IP addresses to scan
            config: ARP configuration
            
        Returns:
            Tuple of (devices_found, errors, raw_output)
        """
        try:
            from scapy.all import ARP, Ether, srp
            
            devices = []
            errors = []
            all_responses = []
            
            # Create ARP request packet for all targets
            # We'll scan in chunks to avoid overwhelming the network
            chunk_size = min(50, len(targets))  # Scan max 50 IPs at once
            
            for i in range(0, len(targets), chunk_size):
                chunk = targets[i:i + chunk_size]
                
                try:
                    # Create broadcast ARP request for the chunk
                    target_range = f"{chunk[0]}-{chunk[-1]}" if len(chunk) > 1 else chunk[0]
                    
                    # Create ARP request
                    arp_request = ARP(pdst=target_range)
                    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
                    arp_request_broadcast = broadcast / arp_request
                    
                    # Send request and receive response
                    answered_list = srp(arp_request_broadcast, timeout=config.timeout, verbose=False)[0]
                    
                    # Parse responses
                    for element in answered_list:
                        ip = element[1].psrc
                        mac = element[1].hwsrc
                        
                        device = DeviceInfo(
                            ip_address=ip,
                            mac_address=mac,
                            device_type=DeviceType.UNKNOWN
                        )
                        devices.append(device)
                        all_responses.append(f"IP: {ip}, MAC: {mac}")
                        
                        self._log_debug(f"ARP response: {ip} -> {mac}")
                
                except Exception as e:
                    error_msg = f"Error scanning chunk {i//chunk_size + 1}: {str(e)}"
                    errors.append(error_msg)
                    self._log_error(error_msg)
            
            raw_output = "\n".join(all_responses)
            return devices, errors, raw_output
            
        except ImportError:
            error_msg = "Scapy library not available"
            self._log_error(error_msg)
            return [], [error_msg], ""
        except Exception as e:
            error_msg = f"Error in scapy ARP scan: {str(e)}"
            self._log_error(error_msg)
            return [], [error_msg], ""
    
    def _scan_with_ping(self, targets: List[str], config: ARPConfig) -> Tuple[List[DeviceInfo], List[str], str]:
        """
        Perform ARP-like scan using ping + arp table lookup (Windows native).
        
        This method uses ping to check if hosts are alive, then queries the
        ARP table to get MAC addresses for responding hosts.
        
        Args:
            targets: List of IP addresses to scan
            config: ARP configuration
            
        Returns:
            Tuple of (devices_found, errors, raw_output)
        """
        devices = []
        errors = []
        all_raw_output = []
        
        self._log_info("Using ping + ARP table method for device discovery")
        
        # Use ThreadPoolExecutor for parallel ping scanning
        with ThreadPoolExecutor(max_workers=config.parallel_threads) as executor:
            # Submit all ping tasks
            future_to_target = {
                executor.submit(self._ping_single_target, target, config): target 
                for target in targets
            }
            
            # Collect results as they complete
            alive_ips = []
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    is_alive, error, raw_output = future.result()
                    if is_alive:
                        alive_ips.append(target)
                    if error:
                        errors.append(f"{target}: {error}")
                    if raw_output:
                        all_raw_output.append(f"=== {target} ===\n{raw_output}")
                except Exception as e:
                    error_msg = f"Exception pinging {target}: {str(e)}"
                    errors.append(error_msg)
                    self._log_error(error_msg)
        
        # Now get MAC addresses for alive IPs from ARP table
        if alive_ips:
            self._log_info(f"Found {len(alive_ips)} responding hosts, querying ARP table for MAC addresses")
            arp_table = self._get_arp_table()
            
            for ip in alive_ips:
                mac_address = arp_table.get(ip)
                device = DeviceInfo(
                    ip_address=ip,
                    mac_address=mac_address,
                    device_type=DeviceType.UNKNOWN
                )
                devices.append(device)
                
                mac_info = f" (MAC: {mac_address})" if mac_address else " (MAC: unknown)"
                all_raw_output.append(f"Active: {ip}{mac_info}")
        
        return devices, errors, "\n".join(all_raw_output)
    
    def _ping_single_target(self, target: str, config: ARPConfig) -> Tuple[bool, Optional[str], str]:
        """
        Ping a single target to check if it's alive.
        
        Args:
            target: IP address to ping
            config: ARP configuration
            
        Returns:
            Tuple of (is_alive, error_message, raw_output)
        """
        try:
            # Use ping command appropriate for the OS
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                # Windows ping: ping -n 1 -w 1000 IP
                cmd = ["ping", "-n", "1", "-w", str(config.timeout * 1000), target]
            else:
                # Unix ping: ping -c 1 -W 1 IP
                cmd = ["ping", "-c", "1", "-W", str(config.timeout), target]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout + 2
            )
            
            raw_output = result.stdout + result.stderr
            
            # Analyze the actual ping output instead of just return code
            is_alive = self._analyze_ping_output(raw_output, target, system)
            
            if is_alive:
                self._log_debug(f"Ping successful: {target}")
            else:
                self._log_debug(f"Ping failed or no response: {target}")
            
            return is_alive, None, raw_output
            
        except subprocess.TimeoutExpired:
            return False, "Ping timeout", ""
        except Exception as e:
            return False, f"Ping failed: {str(e)}", ""
    
    def _analyze_ping_output(self, output: str, target: str, system: str) -> bool:
        """
        Analyze ping output to determine if the host is actually responding.
        
        Args:
            output: Raw ping command output
            target: Target IP address
            system: Operating system (windows/linux/etc)
            
        Returns:
            bool: True if host is actually responding, False otherwise
        """
        if not output:
            return False
        
        output_lower = output.lower()
        
        if system == "windows":
            # Windows ping analysis
            
            # Definitive failure indicators
            failure_indicators = [
                "destination host unreachable",
                "request timed out",
                "could not find host",
                "ping request could not find host",
                "general failure",
                "transmit failed",
                "unable to contact ip driver"
            ]
            
            for indicator in failure_indicators:
                if indicator in output_lower:
                    return False
            
            # Success indicators - look for actual reply
            success_indicators = [
                f"reply from {target}",
                "bytes=32",  # Standard Windows ping reply size
                "time<1ms",
                "time=",
                "ttl="
            ]
            
            # Must have at least one success indicator
            has_success = any(indicator in output_lower for indicator in success_indicators)
            
            # Additional check: look for statistics showing received packets
            if "packets: sent = 1, received = 1" in output_lower:
                has_success = True
            elif "packets: sent = 1, received = 0" in output_lower:
                return False
            
            return has_success
            
        else:
            # Unix/Linux ping analysis
            
            # Definitive failure indicators
            failure_indicators = [
                "destination host unreachable",
                "no route to host",
                "network is unreachable",
                "name or service not known",
                "temporary failure in name resolution"
            ]
            
            for indicator in failure_indicators:
                if indicator in output_lower:
                    return False
            
            # Success indicators
            success_indicators = [
                f"64 bytes from {target}",
                "bytes from",
                "time=",
                "ttl="
            ]
            
            has_success = any(indicator in output_lower for indicator in success_indicators)
            
            # Check packet statistics
            if "1 packets transmitted, 1 received" in output_lower:
                has_success = True
            elif "1 packets transmitted, 0 received" in output_lower:
                return False
            
            return has_success
    
    def _get_arp_table(self) -> Dict[str, str]:
        """
        Get the system ARP table to map IP addresses to MAC addresses.
        
        Returns:
            Dictionary mapping IP addresses to MAC addresses
        """
        arp_table = {}
        
        try:
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                # Windows: arp -a
                result = subprocess.run(
                    ["arp", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Parse Windows ARP output
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if not line or 'Interface:' in line or 'Internet Address' in line:
                            continue
                        
                        # Format: "192.168.1.1          00-11-22-33-44-55     dynamic"
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            mac = parts[1].replace('-', ':')  # Convert to standard format
                            if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                                arp_table[ip] = mac
            else:
                # Unix: arp -a or ip neigh
                try:
                    result = subprocess.run(
                        ["arp", "-a"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        # Parse Unix ARP output
                        for line in result.stdout.split('\n'):
                            # Format: "hostname (192.168.1.1) at 00:11:22:33:44:55 [ether] on eth0"
                            if '(' in line and ')' in line and ' at ' in line:
                                ip_part = line.split('(')[1].split(')')[0]
                                mac_part = line.split(' at ')[1].split()[0]
                                if self._is_valid_ip(ip_part) and self._is_valid_mac(mac_part):
                                    arp_table[ip_part] = mac_part
                
                except subprocess.CalledProcessError:
                    # Try ip neigh as fallback
                    try:
                        result = subprocess.run(
                            ["ip", "neigh"],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if result.returncode == 0:
                            for line in result.stdout.split('\n'):
                                # Format: "192.168.1.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE"
                                parts = line.split()
                                if len(parts) >= 5 and 'lladdr' in parts:
                                    ip = parts[0]
                                    mac_idx = parts.index('lladdr') + 1
                                    if mac_idx < len(parts):
                                        mac = parts[mac_idx]
                                        if self._is_valid_ip(ip) and self._is_valid_mac(mac):
                                            arp_table[ip] = mac
                    
                    except subprocess.CalledProcessError:
                        pass
        
        except Exception as e:
            self._log_warning(f"Failed to get ARP table: {str(e)}")
        
        self._log_debug(f"ARP table contains {len(arp_table)} entries")
        return arp_table
    
    def _is_valid_mac(self, mac: str) -> bool:
        """Check if string is a valid MAC address."""
        if not mac or len(mac) != 17:
            return False
        
        # Check format: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
        import re
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(pattern, mac))
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if string is a valid IPv4 address."""
        try:
            import ipaddress
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False
    
    def parse_results(self, raw_output: str) -> List[DeviceInfo]:
        """
        Parse raw ARP scanner output into DeviceInfo objects.
        
        Args:
            raw_output: Raw output from ARP scanning
            
        Returns:
            List of DeviceInfo objects
        """
        devices = []
        
        # Split by target sections if present
        sections = raw_output.split("=== ")
        
        for section in sections:
            if not section.strip():
                continue
            
            # Extract IP from section header if present
            lines = section.split('\n')
            target_ip = None
            
            if lines[0].strip().endswith(" ==="):
                target_ip = lines[0].replace(" ===", "").strip()
                content = '\n'.join(lines[1:])
            else:
                content = section
            
            # Parse arping output format
            device = self._parse_arping_output(target_ip, content)
            if device:
                devices.append(device)
        
        return devices
    
    def _parse_arping_output(self, target_ip: Optional[str], output: str) -> Optional[DeviceInfo]:
        """
        Parse arping command output to extract device information.
        
        Args:
            target_ip: Target IP address (if known)
            output: Raw arping output
            
        Returns:
            DeviceInfo object if parsing successful, None otherwise
        """
        if not output:
            return None
        
        # Common arping output patterns
        patterns = [
            # Standard arping format: "ARPING 192.168.1.1 from 192.168.1.100 eth0"
            # Response: "Unicast reply from 192.168.1.1 [aa:bb:cc:dd:ee:ff]"
            r'Unicast reply from\s+(\d+\.\d+\.\d+\.\d+)\s+\[([a-fA-F0-9:]{17})\]',
            
            # Alternative format: "Reply from 192.168.1.1 [aa:bb:cc:dd:ee:ff]"
            r'Reply from\s+(\d+\.\d+\.\d+\.\d+)\s+\[([a-fA-F0-9:]{17})\]',
            
            # Another format: "192.168.1.1 is at aa:bb:cc:dd:ee:ff"
            r'(\d+\.\d+\.\d+\.\d+)\s+is at\s+([a-fA-F0-9:]{17})',
            
            # Scapy-like format: "IP: 192.168.1.1, MAC: aa:bb:cc:dd:ee:ff"
            r'IP:\s*(\d+\.\d+\.\d+\.\d+),\s*MAC:\s*([a-fA-F0-9:]{17})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                ip = match.group(1)
                mac = match.group(2).lower()
                
                # Validate IP matches target if provided
                if target_ip and ip != target_ip:
                    continue
                
                return DeviceInfo(
                    ip_address=ip,
                    mac_address=mac,
                    device_type=DeviceType.UNKNOWN
                )
        
        return None
    
    def _check_scapy_availability(self) -> bool:
        """
        Check if scapy library is available.
        
        Returns:
            True if scapy is available, False otherwise
        """
        try:
            import scapy
            return True
        except ImportError:
            return False
    
    def _is_valid_target(self, target: str) -> bool:
        """
        Enhanced target validation for ARP scanner.
        
        Args:
            target: IP address to validate
            
        Returns:
            True if target is a valid IP address, False otherwise
        """
        if not super()._is_valid_target(target):
            return False
        
        # ARP scanner only works with IP addresses
        parts = target.strip().split('.')
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