"""
Network validation utilities with comprehensive error handling.

This module provides network-related validation functions that integrate
with the centralized error handling system for robust network operations.
"""

import socket
import ipaddress
import subprocess
import time
from typing import List, Optional, Tuple, Union
from dataclasses import dataclass

from .error_handler import (
    ErrorHandler, ErrorContext, ErrorType, ErrorSeverity,
    NetworkError, ValidationError, with_retry
)
from .logger import Logger, get_logger


@dataclass
class NetworkValidationResult:
    """
    Result of network validation operations.
    
    Attributes:
        is_valid: Whether the validation passed
        error_message: Error message if validation failed
        suggestions: List of suggestions to fix validation issues
        additional_info: Additional context information
    """
    is_valid: bool
    error_message: Optional[str] = None
    suggestions: List[str] = None
    additional_info: dict = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []
        if self.additional_info is None:
            self.additional_info = {}


class NetworkValidator:
    """
    Comprehensive network validation with error handling.
    
    Provides validation for IP addresses, network ranges, connectivity,
    and other network-related operations with integrated error handling.
    """
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None, logger: Optional[Logger] = None):
        """
        Initialize the NetworkValidator.
        
        Args:
            error_handler: ErrorHandler instance for error management
            logger: Logger instance for validation messages
        """
        self.logger = logger or get_logger(__name__)
        self.error_handler = error_handler or ErrorHandler(self.logger)
    
    def validate_ip_address(self, ip_str: str) -> NetworkValidationResult:
        """
        Validate an IP address string.
        
        Args:
            ip_str: IP address string to validate
            
        Returns:
            NetworkValidationResult with validation outcome
        """
        try:
            if not ip_str or not isinstance(ip_str, str):
                return NetworkValidationResult(
                    is_valid=False,
                    error_message="IP address must be a non-empty string",
                    suggestions=["Provide a valid IP address string"]
                )
            
            ip_str = ip_str.strip()
            
            # Try to parse as IPv4 or IPv6
            ip_obj = ipaddress.ip_address(ip_str)
            
            # Additional checks
            if ip_obj.is_loopback:
                return NetworkValidationResult(
                    is_valid=True,
                    additional_info={"type": "loopback", "version": ip_obj.version}
                )
            elif ip_obj.is_private:
                return NetworkValidationResult(
                    is_valid=True,
                    additional_info={"type": "private", "version": ip_obj.version}
                )
            elif ip_obj.is_multicast:
                return NetworkValidationResult(
                    is_valid=False,
                    error_message="Multicast addresses are not supported for scanning",
                    suggestions=["Use unicast IP addresses for network scanning"]
                )
            elif ip_obj.is_reserved:
                return NetworkValidationResult(
                    is_valid=False,
                    error_message="Reserved IP addresses are not valid scan targets",
                    suggestions=["Use valid unicast IP addresses"]
                )
            else:
                return NetworkValidationResult(
                    is_valid=True,
                    additional_info={"type": "public", "version": ip_obj.version}
                )
                
        except ValueError as e:
            context = ErrorContext(
                error_type=ErrorType.VALIDATION_ERROR,
                severity=ErrorSeverity.LOW,
                operation="validate_ip_address",
                component="NetworkValidator",
                additional_info={"ip_string": ip_str}
            )
            
            error = ValidationError(f"Invalid IP address format: {ip_str}")
            self.error_handler.handle_error(error, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Invalid IP address format: {str(e)}",
                suggestions=[
                    "Check IP address format (e.g., 192.168.1.1)",
                    "Ensure no extra spaces or characters",
                    "Verify IPv4 format: xxx.xxx.xxx.xxx where xxx is 0-255"
                ]
            )
    
    def validate_network_range(self, network_str: str) -> NetworkValidationResult:
        """
        Validate a network range in CIDR notation.
        
        Args:
            network_str: Network range string (e.g., "192.168.1.0/24")
            
        Returns:
            NetworkValidationResult with validation outcome
        """
        try:
            if not network_str or not isinstance(network_str, str):
                return NetworkValidationResult(
                    is_valid=False,
                    error_message="Network range must be a non-empty string",
                    suggestions=["Provide a valid CIDR notation (e.g., 192.168.1.0/24)"]
                )
            
            network_str = network_str.strip()
            
            # Parse network
            network_obj = ipaddress.ip_network(network_str, strict=False)
            
            # Check if network is too large
            if network_obj.num_addresses > 65536:  # /16 or larger
                return NetworkValidationResult(
                    is_valid=False,
                    error_message="Network range is too large for efficient scanning",
                    suggestions=[
                        "Use smaller network ranges (/24 or smaller)",
                        "Consider breaking large networks into smaller subnets"
                    ]
                )
            
            return NetworkValidationResult(
                is_valid=True,
                additional_info={
                    "network_address": str(network_obj.network_address),
                    "broadcast_address": str(network_obj.broadcast_address),
                    "num_addresses": network_obj.num_addresses,
                    "prefix_length": network_obj.prefixlen
                }
            )
            
        except ValueError as e:
            context = ErrorContext(
                error_type=ErrorType.VALIDATION_ERROR,
                severity=ErrorSeverity.LOW,
                operation="validate_network_range",
                component="NetworkValidator",
                additional_info={"network_string": network_str}
            )
            
            error = ValidationError(f"Invalid network range format: {network_str}")
            self.error_handler.handle_error(error, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Invalid network range format: {str(e)}",
                suggestions=[
                    "Use CIDR notation (e.g., 192.168.1.0/24)",
                    "Ensure network address is correct",
                    "Check prefix length (0-32 for IPv4, 0-128 for IPv6)"
                ]
            )
    
    @with_retry(max_retries=2, error_types=(socket.error, OSError))
    def test_connectivity(self, target: str, port: int = 80, timeout: float = 5.0) -> NetworkValidationResult:
        """
        Test network connectivity to a target.
        
        Args:
            target: Target IP address or hostname
            port: Port to test (default: 80)
            timeout: Connection timeout in seconds
            
        Returns:
            NetworkValidationResult with connectivity test outcome
        """
        try:
            # Validate target first
            ip_result = self.validate_ip_address(target)
            if not ip_result.is_valid:
                # Try to resolve hostname
                try:
                    resolved_ip = socket.gethostbyname(target)
                    self.logger.debug(f"Resolved {target} to {resolved_ip}")
                except socket.gaierror:
                    return NetworkValidationResult(
                        is_valid=False,
                        error_message=f"Cannot resolve hostname: {target}",
                        suggestions=[
                            "Check hostname spelling",
                            "Verify DNS configuration",
                            "Use IP address instead of hostname"
                        ]
                    )
            
            # Test TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                result = sock.connect_ex((target, port))
                if result == 0:
                    return NetworkValidationResult(
                        is_valid=True,
                        additional_info={"port": port, "response_time": timeout}
                    )
                else:
                    return NetworkValidationResult(
                        is_valid=False,
                        error_message=f"Connection failed to {target}:{port}",
                        suggestions=[
                            "Check if target host is online",
                            "Verify port is open and accessible",
                            "Check firewall settings"
                        ]
                    )
            finally:
                sock.close()
                
        except socket.timeout:
            context = ErrorContext(
                error_type=ErrorType.TIMEOUT_ERROR,
                severity=ErrorSeverity.MEDIUM,
                operation="test_connectivity",
                component="NetworkValidator",
                additional_info={"target": target, "port": port, "timeout": timeout}
            )
            
            error = NetworkError(f"Connection timeout to {target}:{port}")
            self.error_handler.handle_error(error, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Connection timeout to {target}:{port}",
                suggestions=[
                    "Increase timeout value",
                    "Check network latency",
                    "Verify target is reachable"
                ]
            )
            
        except Exception as e:
            context = ErrorContext(
                error_type=ErrorType.NETWORK_ERROR,
                severity=ErrorSeverity.MEDIUM,
                operation="test_connectivity",
                component="NetworkValidator",
                additional_info={"target": target, "port": port}
            )
            
            self.error_handler.handle_error(e, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Network error: {str(e)}",
                suggestions=[
                    "Check network configuration",
                    "Verify target accessibility",
                    "Check for network restrictions"
                ]
            )
    
    def validate_port_range(self, port_range: str) -> NetworkValidationResult:
        """
        Validate a port range specification.
        
        Args:
            port_range: Port range string (e.g., "80", "80-443", "22,80,443")
            
        Returns:
            NetworkValidationResult with validation outcome
        """
        try:
            if not port_range or not isinstance(port_range, str):
                return NetworkValidationResult(
                    is_valid=False,
                    error_message="Port range must be a non-empty string",
                    suggestions=["Provide valid port specification (e.g., 80, 80-443, 22,80,443)"]
                )
            
            port_range = port_range.strip()
            ports = []
            
            # Handle comma-separated ports
            for part in port_range.split(','):
                part = part.strip()
                
                if '-' in part:
                    # Handle range (e.g., "80-443")
                    try:
                        start, end = part.split('-', 1)
                        start_port = int(start.strip())
                        end_port = int(end.strip())
                        
                        if start_port > end_port:
                            return NetworkValidationResult(
                                is_valid=False,
                                error_message=f"Invalid port range: {part} (start > end)",
                                suggestions=["Ensure start port is less than end port"]
                            )
                        
                        if end_port - start_port > 1000:
                            return NetworkValidationResult(
                                is_valid=False,
                                error_message=f"Port range too large: {part}",
                                suggestions=["Use smaller port ranges for efficient scanning"]
                            )
                        
                        ports.extend(range(start_port, end_port + 1))
                        
                    except ValueError:
                        return NetworkValidationResult(
                            is_valid=False,
                            error_message=f"Invalid port range format: {part}",
                            suggestions=["Use format: start-end (e.g., 80-443)"]
                        )
                else:
                    # Handle single port
                    try:
                        port = int(part)
                        ports.append(port)
                    except ValueError:
                        return NetworkValidationResult(
                            is_valid=False,
                            error_message=f"Invalid port number: {part}",
                            suggestions=["Port numbers must be integers"]
                        )
            
            # Validate port numbers
            invalid_ports = [p for p in ports if not (1 <= p <= 65535)]
            if invalid_ports:
                return NetworkValidationResult(
                    is_valid=False,
                    error_message=f"Invalid port numbers: {invalid_ports}",
                    suggestions=["Port numbers must be between 1 and 65535"]
                )
            
            return NetworkValidationResult(
                is_valid=True,
                additional_info={"ports": sorted(set(ports)), "port_count": len(set(ports))}
            )
            
        except Exception as e:
            context = ErrorContext(
                error_type=ErrorType.VALIDATION_ERROR,
                severity=ErrorSeverity.LOW,
                operation="validate_port_range",
                component="NetworkValidator",
                additional_info={"port_range": port_range}
            )
            
            error = ValidationError(f"Port range validation error: {str(e)}")
            self.error_handler.handle_error(error, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Port range validation error: {str(e)}",
                suggestions=[
                    "Check port range format",
                    "Use valid port numbers (1-65535)",
                    "Separate multiple ports with commas"
                ]
            )
    
    def ping_host(self, target: str, count: int = 1, timeout: float = 5.0) -> NetworkValidationResult:
        """
        Ping a host to test basic connectivity.
        
        Args:
            target: Target IP address or hostname
            count: Number of ping packets to send
            timeout: Timeout for ping operation
            
        Returns:
            NetworkValidationResult with ping test outcome
        """
        try:
            # Build ping command based on OS
            import platform
            system = platform.system().lower()
            
            if system == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), target]
            else:
                cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), target]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5  # Add buffer to subprocess timeout
            )
            
            if result.returncode == 0:
                return NetworkValidationResult(
                    is_valid=True,
                    additional_info={
                        "ping_output": result.stdout,
                        "packets_sent": count
                    }
                )
            else:
                return NetworkValidationResult(
                    is_valid=False,
                    error_message=f"Ping failed to {target}",
                    suggestions=[
                        "Check if target host is online",
                        "Verify network connectivity",
                        "Check firewall settings"
                    ],
                    additional_info={"ping_error": result.stderr}
                )
                
        except subprocess.TimeoutExpired:
            context = ErrorContext(
                error_type=ErrorType.TIMEOUT_ERROR,
                severity=ErrorSeverity.MEDIUM,
                operation="ping_host",
                component="NetworkValidator",
                additional_info={"target": target, "timeout": timeout}
            )
            
            error = NetworkError(f"Ping timeout to {target}")
            self.error_handler.handle_error(error, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Ping timeout to {target}",
                suggestions=[
                    "Increase timeout value",
                    "Check network latency",
                    "Verify target is reachable"
                ]
            )
            
        except Exception as e:
            context = ErrorContext(
                error_type=ErrorType.NETWORK_ERROR,
                severity=ErrorSeverity.MEDIUM,
                operation="ping_host",
                component="NetworkValidator",
                additional_info={"target": target}
            )
            
            self.error_handler.handle_error(e, context)
            
            return NetworkValidationResult(
                is_valid=False,
                error_message=f"Ping error: {str(e)}",
                suggestions=[
                    "Check network configuration",
                    "Verify ping command availability",
                    "Check system permissions"
                ]
            )


def validate_scan_targets(targets: List[str], validator: Optional[NetworkValidator] = None) -> Tuple[List[str], List[str]]:
    """
    Validate a list of scan targets and return valid and invalid targets.
    
    Args:
        targets: List of IP addresses or hostnames to validate
        validator: NetworkValidator instance (creates new one if None)
        
    Returns:
        Tuple of (valid_targets, invalid_targets)
    """
    if validator is None:
        validator = NetworkValidator()
    
    valid_targets = []
    invalid_targets = []
    
    for target in targets:
        result = validator.validate_ip_address(target)
        if result.is_valid:
            valid_targets.append(target)
        else:
            invalid_targets.append(target)
            validator.logger.warning(f"Invalid target: {target} - {result.error_message}")
    
    return valid_targets, invalid_targets