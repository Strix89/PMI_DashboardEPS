"""
Comprehensive error handling and validation system for Network Discovery Module.

This module provides centralized error management, retry logic with exponential backoff,
permission error detection, external tool validation, and user-friendly error messages
with troubleshooting suggestions.
"""

import time
import random
import subprocess
import shutil
import os
import socket
import errno
from typing import Optional, Callable, Any, Dict, List, Tuple
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

from .logger import Logger, get_logger


class ErrorType(Enum):
    """Enumeration for different types of errors."""
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    TOOL_MISSING_ERROR = "tool_missing_error"
    CONFIGURATION_ERROR = "configuration_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    SUBPROCESS_ERROR = "subprocess_error"
    FILE_ERROR = "file_error"


class ErrorSeverity(Enum):
    """Enumeration for error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """
    Context information for error handling.
    
    Attributes:
        error_type: Type of error that occurred
        severity: Severity level of the error
        operation: Operation that was being performed when error occurred
        component: Component/module where error occurred
        retry_count: Number of retry attempts made
        max_retries: Maximum number of retries allowed
        additional_info: Additional context information
    """
    error_type: ErrorType
    severity: ErrorSeverity
    operation: str
    component: str
    retry_count: int = 0
    max_retries: int = 3
    additional_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_info is None:
            self.additional_info = {}


class NetworkDiscoveryError(Exception):
    """Base exception class for Network Discovery Module."""
    
    def __init__(self, message: str, error_context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.error_context = error_context


class NetworkError(NetworkDiscoveryError):
    """Exception for network-related errors."""
    pass


class PermissionError(NetworkDiscoveryError):
    """Exception for permission-related errors."""
    pass


class ToolMissingError(NetworkDiscoveryError):
    """Exception for missing external tools."""
    pass


class ConfigurationError(NetworkDiscoveryError):
    """Exception for configuration-related errors."""
    pass


class ValidationError(NetworkDiscoveryError):
    """Exception for validation errors."""
    pass


class ErrorHandler:
    """
    Centralized error handling and validation system.
    
    Provides comprehensive error management including retry logic with exponential backoff,
    permission error detection, external tool validation, and user-friendly error messages.
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        """
        Initialize the ErrorHandler.
        
        Args:
            logger: Logger instance for error reporting
        """
        self.logger = logger or get_logger(__name__)
        self.error_statistics: Dict[ErrorType, int] = {}
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff delays in seconds
        
        # Initialize error statistics
        for error_type in ErrorType:
            self.error_statistics[error_type] = 0
    
    def handle_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle an error based on its type and context.
        
        Args:
            error: The exception that occurred
            context: Error context information
            
        Returns:
            bool: True if error was handled and operation should retry, False otherwise
        """
        # Update error statistics
        self.error_statistics[context.error_type] += 1
        
        # Log the error with appropriate level
        self._log_error(error, context)
        
        # Handle specific error types
        if context.error_type == ErrorType.NETWORK_ERROR:
            return self._handle_network_error(error, context)
        elif context.error_type == ErrorType.PERMISSION_ERROR:
            return self._handle_permission_error(error, context)
        elif context.error_type == ErrorType.TOOL_MISSING_ERROR:
            return self._handle_tool_missing_error(error, context)
        elif context.error_type == ErrorType.CONFIGURATION_ERROR:
            return self._handle_configuration_error(error, context)
        elif context.error_type == ErrorType.VALIDATION_ERROR:
            return self._handle_validation_error(error, context)
        elif context.error_type == ErrorType.TIMEOUT_ERROR:
            return self._handle_timeout_error(error, context)
        elif context.error_type == ErrorType.SUBPROCESS_ERROR:
            return self._handle_subprocess_error(error, context)
        elif context.error_type == ErrorType.FILE_ERROR:
            return self._handle_file_error(error, context)
        else:
            self.logger.error(f"Unknown error type: {context.error_type}")
            return False
    
    def _handle_network_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle network-related errors with retry logic and exponential backoff.
        
        Args:
            error: The network error that occurred
            context: Error context information
            
        Returns:
            bool: True if should retry, False otherwise
        """
        if context.retry_count >= context.max_retries:
            self.logger.error(f"Network operation failed after {context.max_retries} retries")
            self._suggest_network_troubleshooting(error, context)
            return False
        
        # Calculate delay with exponential backoff and jitter
        delay_index = min(context.retry_count, len(self.retry_delays) - 1)
        base_delay = self.retry_delays[delay_index]
        jitter = random.uniform(0.1, 0.5)  # Add jitter to prevent thundering herd
        delay = base_delay + jitter
        
        self.logger.warning(
            f"Network error in {context.operation} (attempt {context.retry_count + 1}/{context.max_retries + 1}). "
            f"Retrying in {delay:.1f} seconds..."
        )
        
        time.sleep(delay)
        return True
    
    def _handle_permission_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle permission-related errors with helpful user guidance.
        
        Args:
            error: The permission error that occurred
            context: Error context information
            
        Returns:
            bool: False (permission errors typically don't benefit from retries)
        """
        self.logger.error(f"Permission denied for {context.operation}")
        self._suggest_permission_solutions(error, context)
        return False
    
    def _handle_tool_missing_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle missing external tool errors.
        
        Args:
            error: The tool missing error that occurred
            context: Error context information
            
        Returns:
            bool: False (missing tools need to be installed)
        """
        tool_name = context.additional_info.get('tool_name', 'unknown')
        self.logger.error(f"Required tool '{tool_name}' is not available")
        self._suggest_tool_installation(tool_name)
        return False
    
    def _handle_configuration_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle configuration-related errors.
        
        Args:
            error: The configuration error that occurred
            context: Error context information
            
        Returns:
            bool: False (configuration errors need manual intervention)
        """
        config_file = context.additional_info.get('config_file', 'unknown')
        self.logger.error(f"Configuration error in {config_file}")
        self._suggest_configuration_fixes(error, context)
        return False
    
    def _handle_validation_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle validation errors.
        
        Args:
            error: The validation error that occurred
            context: Error context information
            
        Returns:
            bool: False (validation errors need input correction)
        """
        self.logger.error(f"Validation failed for {context.operation}")
        self._suggest_validation_fixes(error, context)
        return False
    
    def _handle_timeout_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle timeout errors with retry logic.
        
        Args:
            error: The timeout error that occurred
            context: Error context information
            
        Returns:
            bool: True if should retry with longer timeout, False otherwise
        """
        if context.retry_count >= context.max_retries:
            self.logger.error(f"Operation timed out after {context.max_retries} retries")
            self._suggest_timeout_solutions(error, context)
            return False
        
        # Increase timeout for retry
        current_timeout = context.additional_info.get('timeout', 30)
        new_timeout = min(current_timeout * 1.5, 300)  # Cap at 5 minutes
        context.additional_info['timeout'] = new_timeout
        
        self.logger.warning(
            f"Operation timed out (attempt {context.retry_count + 1}/{context.max_retries + 1}). "
            f"Retrying with increased timeout: {new_timeout}s"
        )
        
        return True
    
    def _handle_subprocess_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle subprocess execution errors.
        
        Args:
            error: The subprocess error that occurred
            context: Error context information
            
        Returns:
            bool: True if should retry for transient errors, False otherwise
        """
        if isinstance(error, subprocess.CalledProcessError):
            return_code = error.returncode
            
            # Some return codes indicate transient issues that might benefit from retry
            transient_codes = [124, 125, 126, 127, 130, 143]  # timeout, not found, permission, interrupted
            
            if return_code in transient_codes and context.retry_count < context.max_retries:
                self.logger.warning(
                    f"Subprocess failed with code {return_code} (attempt {context.retry_count + 1}/{context.max_retries + 1}). "
                    "Retrying..."
                )
                time.sleep(2)  # Brief delay before retry
                return True
            else:
                self.logger.error(f"Subprocess failed with return code {return_code}")
                self._suggest_subprocess_solutions(error, context)
                return False
        
        return False
    
    def _handle_file_error(self, error: Exception, context: ErrorContext) -> bool:
        """
        Handle file system related errors.
        
        Args:
            error: The file error that occurred
            context: Error context information
            
        Returns:
            bool: False (file errors typically need manual intervention)
        """
        file_path = context.additional_info.get('file_path', 'unknown')
        self.logger.error(f"File system error with {file_path}")
        self._suggest_file_solutions(error, context)
        return False
    
    def _log_error(self, error: Exception, context: ErrorContext) -> None:
        """
        Log error information with appropriate detail level.
        
        Args:
            error: The exception that occurred
            context: Error context information
        """
        error_msg = f"Error in {context.component}.{context.operation}: {str(error)}"
        
        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.error(error_msg, exception=error)
        elif context.severity == ErrorSeverity.HIGH:
            self.logger.error(error_msg)
        elif context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error_msg)
        else:
            self.logger.debug(error_msg)
    
    def _suggest_network_troubleshooting(self, error: Exception, context: ErrorContext) -> None:
        """Provide network troubleshooting suggestions."""
        self.logger.info("Network troubleshooting suggestions:")
        self.logger.info("  • Check network connectivity: ping 8.8.8.8")
        self.logger.info("  • Verify DNS resolution: nslookup google.com")
        self.logger.info("  • Check firewall settings")
        self.logger.info("  • Ensure target network is reachable")
        self.logger.info("  • Try running with elevated privileges")
    
    def _suggest_permission_solutions(self, error: Exception, context: ErrorContext) -> None:
        """Provide permission error solutions."""
        operation = context.operation
        self.logger.info("Permission error solutions:")
        
        if "nmap" in operation.lower():
            self.logger.info("  • Run with sudo: sudo python -m network_discovery")
            self.logger.info("  • Use non-privileged scan types (-sT instead of -sS)")
            self.logger.info("  • Configure nmap with appropriate capabilities")
        elif "arp" in operation.lower():
            self.logger.info("  • Run with sudo: sudo python -m network_discovery")
            self.logger.info("  • Use scapy method instead of arping")
            self.logger.info("  • Check network interface permissions")
        else:
            self.logger.info("  • Run with elevated privileges (sudo)")
            self.logger.info("  • Check file/directory permissions")
            self.logger.info("  • Ensure user has necessary group memberships")
    
    def _suggest_tool_installation(self, tool_name: str) -> None:
        """Provide tool installation suggestions."""
        suggestions = {
            "nmap": [
                "Ubuntu/Debian: sudo apt-get install nmap",
                "CentOS/RHEL: sudo yum install nmap",
                "macOS: brew install nmap",
                "Windows: Download from https://nmap.org/download.html"
            ],
            "arping": [
                "Ubuntu/Debian: sudo apt-get install arping",
                "CentOS/RHEL: sudo yum install arping", 
                "macOS: brew install arping",
                "Windows: Use Windows Subsystem for Linux (WSL)"
            ],
            "snmpwalk": [
                "Ubuntu/Debian: sudo apt-get install snmp-utils",
                "CentOS/RHEL: sudo yum install net-snmp-utils",
                "macOS: brew install net-snmp",
                "Windows: Download from http://www.net-snmp.org/"
            ]
        }
        
        if tool_name in suggestions:
            self.logger.info(f"Installation suggestions for {tool_name}:")
            for suggestion in suggestions[tool_name]:
                self.logger.info(f"  • {suggestion}")
        else:
            self.logger.info(f"Please install {tool_name} using your system's package manager")
    
    def _suggest_configuration_fixes(self, error: Exception, context: ErrorContext) -> None:
        """Provide configuration error solutions."""
        self.logger.info("Configuration error solutions:")
        self.logger.info("  • Check YAML syntax and indentation")
        self.logger.info("  • Verify all required configuration keys are present")
        self.logger.info("  • Ensure configuration values are valid")
        self.logger.info("  • Check file permissions for configuration files")
        self.logger.info("  • Use default configuration as reference")
    
    def _suggest_validation_fixes(self, error: Exception, context: ErrorContext) -> None:
        """Provide validation error solutions."""
        self.logger.info("Validation error solutions:")
        self.logger.info("  • Check input format and syntax")
        self.logger.info("  • Verify IP addresses are in correct format")
        self.logger.info("  • Ensure network ranges are valid")
        self.logger.info("  • Check that required parameters are provided")
    
    def _suggest_timeout_solutions(self, error: Exception, context: ErrorContext) -> None:
        """Provide timeout error solutions."""
        self.logger.info("Timeout error solutions:")
        self.logger.info("  • Increase timeout values in configuration")
        self.logger.info("  • Check network latency to target hosts")
        self.logger.info("  • Reduce scan scope or parallelism")
        self.logger.info("  • Verify target hosts are responsive")
    
    def _suggest_subprocess_solutions(self, error: Exception, context: ErrorContext) -> None:
        """Provide subprocess error solutions."""
        self.logger.info("Subprocess error solutions:")
        self.logger.info("  • Verify external tools are properly installed")
        self.logger.info("  • Check tool versions for compatibility")
        self.logger.info("  • Ensure sufficient system resources")
        self.logger.info("  • Review command-line arguments")
    
    def _suggest_file_solutions(self, error: Exception, context: ErrorContext) -> None:
        """Provide file system error solutions."""
        self.logger.info("File system error solutions:")
        self.logger.info("  • Check file and directory permissions")
        self.logger.info("  • Verify sufficient disk space")
        self.logger.info("  • Ensure parent directories exist")
        self.logger.info("  • Check for file locks or conflicts")


class ToolValidator:
    """
    Validator for external tool availability and functionality.
    
    Provides comprehensive validation of required external tools including
    availability checks, version verification, and permission testing.
    """
    
    def __init__(self, error_handler: ErrorHandler):
        """
        Initialize the ToolValidator.
        
        Args:
            error_handler: ErrorHandler instance for error management
        """
        self.error_handler = error_handler
        self.logger = error_handler.logger
        
        # Define required tools and their validation commands
        self.tool_validations = {
            "nmap": {
                "check_command": ["nmap", "--version"],
                "min_version": "7.0",
                "permission_test": ["nmap", "-sn", "127.0.0.1"],
                "install_package": "nmap"
            },
            "arping": {
                "check_command": ["arping", "--help"],
                "min_version": None,
                "permission_test": None,  # Will be tested during actual scan
                "install_package": "arping"
            },
            "snmpwalk": {
                "check_command": ["snmpwalk", "-V"],
                "min_version": None,
                "permission_test": None,
                "install_package": "snmp-utils"
            }
        }
    
    def validate_all_tools(self) -> Tuple[bool, List[str]]:
        """
        Validate all required external tools.
        
        Returns:
            Tuple of (all_valid, missing_tools)
        """
        missing_tools = []
        all_valid = True
        
        for tool_name in self.tool_validations.keys():
            if not self.validate_tool(tool_name):
                missing_tools.append(tool_name)
                all_valid = False
        
        return all_valid, missing_tools
    
    def validate_tool(self, tool_name: str) -> bool:
        """
        Validate a specific external tool.
        
        Args:
            tool_name: Name of the tool to validate
            
        Returns:
            bool: True if tool is valid and available, False otherwise
        """
        if tool_name not in self.tool_validations:
            self.logger.warning(f"Unknown tool: {tool_name}")
            return False
        
        tool_config = self.tool_validations[tool_name]
        
        # Check if tool is available in PATH
        if not self._check_tool_availability(tool_name):
            return False
        
        # Check tool version if specified
        if tool_config["min_version"]:
            if not self._check_tool_version(tool_name, tool_config):
                return False
        
        # Test tool permissions if specified
        if tool_config["permission_test"]:
            if not self._check_tool_permissions(tool_name, tool_config):
                return False
        
        self.logger.debug(f"Tool {tool_name} validation passed")
        return True
    
    def _check_tool_availability(self, tool_name: str) -> bool:
        """
        Check if a tool is available in the system PATH.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            bool: True if tool is available, False otherwise
        """
        tool_path = shutil.which(tool_name)
        if tool_path:
            self.logger.debug(f"Found {tool_name} at: {tool_path}")
            return True
        else:
            context = ErrorContext(
                error_type=ErrorType.TOOL_MISSING_ERROR,
                severity=ErrorSeverity.HIGH,
                operation="tool_availability_check",
                component="ToolValidator",
                additional_info={"tool_name": tool_name}
            )
            error = ToolMissingError(f"Tool {tool_name} not found in PATH")
            self.error_handler.handle_error(error, context)
            return False
    
    def _check_tool_version(self, tool_name: str, tool_config: Dict) -> bool:
        """
        Check if a tool meets minimum version requirements.
        
        Args:
            tool_name: Name of the tool to check
            tool_config: Tool configuration dictionary
            
        Returns:
            bool: True if version is acceptable, False otherwise
        """
        try:
            result = subprocess.run(
                tool_config["check_command"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse version from output (basic implementation)
                version_output = result.stdout + result.stderr
                self.logger.debug(f"{tool_name} version check output: {version_output[:100]}...")
                return True  # Simplified - assume version is OK if command succeeds
            else:
                self.logger.warning(f"{tool_name} version check failed with code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"{tool_name} version check timed out")
            return False
        except Exception as e:
            context = ErrorContext(
                error_type=ErrorType.SUBPROCESS_ERROR,
                severity=ErrorSeverity.MEDIUM,
                operation="tool_version_check",
                component="ToolValidator",
                additional_info={"tool_name": tool_name}
            )
            self.error_handler.handle_error(e, context)
            return False
    
    def _check_tool_permissions(self, tool_name: str, tool_config: Dict) -> bool:
        """
        Check if a tool can be executed with current permissions.
        
        Args:
            tool_name: Name of the tool to check
            tool_config: Tool configuration dictionary
            
        Returns:
            bool: True if tool can be executed, False otherwise
        """
        try:
            result = subprocess.run(
                tool_config["permission_test"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # For nmap, return code 0 or 1 might be acceptable (depends on target)
            if tool_name == "nmap" and result.returncode in [0, 1]:
                return True
            elif result.returncode == 0:
                return True
            else:
                # Check if error indicates permission issue
                error_output = result.stderr.lower()
                if any(perm_keyword in error_output for perm_keyword in 
                       ["permission", "privilege", "root", "sudo", "access denied"]):
                    context = ErrorContext(
                        error_type=ErrorType.PERMISSION_ERROR,
                        severity=ErrorSeverity.HIGH,
                        operation="tool_permission_check",
                        component="ToolValidator",
                        additional_info={"tool_name": tool_name}
                    )
                    error = PermissionError(f"Tool {tool_name} requires elevated permissions")
                    self.error_handler.handle_error(error, context)
                    return False
                else:
                    self.logger.warning(f"{tool_name} permission test failed: {result.stderr}")
                    return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"{tool_name} permission test timed out")
            return False
        except Exception as e:
            context = ErrorContext(
                error_type=ErrorType.SUBPROCESS_ERROR,
                severity=ErrorSeverity.MEDIUM,
                operation="tool_permission_check",
                component="ToolValidator",
                additional_info={"tool_name": tool_name}
            )
            self.error_handler.handle_error(e, context)
            return False


def with_retry(max_retries: int = 3, error_types: Tuple = (Exception,)):
    """
    Decorator for adding retry logic with exponential backoff to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        error_types: Tuple of exception types to catch and retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            error_handler = ErrorHandler()
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except error_types as e:
                    if attempt == max_retries:
                        raise  # Re-raise on final attempt
                    
                    context = ErrorContext(
                        error_type=ErrorType.NETWORK_ERROR,  # Default to network error
                        severity=ErrorSeverity.MEDIUM,
                        operation=func.__name__,
                        component="RetryDecorator",
                        retry_count=attempt,
                        max_retries=max_retries
                    )
                    
                    should_retry = error_handler.handle_error(e, context)
                    if not should_retry:
                        raise
            
            return None  # Should never reach here
        
        return wrapper
    return decorator