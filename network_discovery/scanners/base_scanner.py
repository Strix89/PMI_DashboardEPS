"""
Base scanner interface for Network Discovery Module.

This module defines the abstract base class that all scanners must implement,
providing a consistent interface for different scanning methods (ARP, NMAP, SNMP).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.data_models import DeviceInfo, ScanStatus


@dataclass
class ScanResult:
    """
    Base class for scan results from any scanner type.
    
    Attributes:
        scanner_type: Type of scanner that produced this result
        scan_status: Status of the scan operation
        devices_found: List of devices discovered during the scan
        scan_duration: Time taken to complete the scan in seconds
        errors: List of errors encountered during scanning
        raw_output: Raw output from the scanning tool (for debugging)
        metadata: Additional metadata specific to the scanner type
    """
    scanner_type: str
    scan_status: ScanStatus
    devices_found: List[DeviceInfo]
    scan_duration: float = 0.0
    errors: List[str] = None
    raw_output: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


class BaseScanner(ABC):
    """
    Abstract base class for all network scanners.
    
    This class defines the interface that all scanner implementations must follow,
    ensuring consistency across different scanning methods and enabling polymorphic
    usage in the scanner orchestrator.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the base scanner.
        
        Args:
            logger: Logger instance for outputting scan progress and errors
        """
        self.logger = logger
        self.scan_start_time: Optional[datetime] = None
        self.scan_end_time: Optional[datetime] = None
    
    @abstractmethod
    def scan(self, targets: List[str], config: Any) -> ScanResult:
        """
        Execute the scan on the specified targets.
        
        This method must be implemented by all concrete scanner classes.
        It should perform the actual scanning operation and return structured results.
        
        Args:
            targets: List of IP addresses or hostnames to scan
            config: Configuration object specific to the scanner type
            
        Returns:
            ScanResult object containing discovered devices and scan metadata
            
        Raises:
            NotImplementedError: If not implemented by concrete class
        """
        pass
    
    @abstractmethod
    def parse_results(self, raw_output: str) -> List[DeviceInfo]:
        """
        Parse raw scanner output into structured device information.
        
        This method must be implemented by all concrete scanner classes.
        It should convert the raw text output from scanning tools into
        structured DeviceInfo objects.
        
        Args:
            raw_output: Raw text output from the scanning tool
            
        Returns:
            List of DeviceInfo objects parsed from the raw output
            
        Raises:
            NotImplementedError: If not implemented by concrete class
        """
        pass
    
    def _start_scan_timer(self) -> None:
        """Start the scan timing measurement."""
        self.scan_start_time = datetime.now()
    
    def _end_scan_timer(self) -> float:
        """
        End the scan timing measurement and return duration.
        
        Returns:
            Scan duration in seconds as a float
        """
        self.scan_end_time = datetime.now()
        if self.scan_start_time:
            return (self.scan_end_time - self.scan_start_time).total_seconds()
        return 0.0
    
    def _log_info(self, message: str) -> None:
        """Log an info message if logger is available."""
        if self.logger:
            self.logger.info(message)
    
    def _log_warning(self, message: str) -> None:
        """Log a warning message if logger is available."""
        if self.logger:
            self.logger.warning(message)
    
    def _log_error(self, message: str) -> None:
        """Log an error message if logger is available."""
        if self.logger:
            self.logger.error(message)
    
    def _log_debug(self, message: str) -> None:
        """Log a debug message if logger is available."""
        if self.logger:
            self.logger.debug(message)
    
    def validate_targets(self, targets: List[str]) -> List[str]:
        """
        Validate and filter the list of scan targets.
        
        Args:
            targets: List of IP addresses or hostnames to validate
            
        Returns:
            List of valid targets after filtering
        """
        if not targets:
            self._log_warning("No targets provided for scanning")
            return []
        
        valid_targets = []
        for target in targets:
            if self._is_valid_target(target):
                valid_targets.append(target)
            else:
                self._log_warning(f"Invalid target skipped: {target}")
        
        self._log_info(f"Validated {len(valid_targets)} out of {len(targets)} targets")
        return valid_targets
    
    def _is_valid_target(self, target: str) -> bool:
        """
        Check if a target is valid for scanning.
        
        Args:
            target: IP address or hostname to validate
            
        Returns:
            True if target is valid, False otherwise
        """
        if not target or not isinstance(target, str):
            return False
        
        # Basic validation - can be enhanced in concrete implementations
        target = target.strip()
        if not target:
            return False
        
        # Check for basic IP address format (simple validation)
        parts = target.split('.')
        if len(parts) == 4:
            try:
                for part in parts:
                    num = int(part)
                    if not 0 <= num <= 255:
                        return False
                return True
            except ValueError:
                return False
        
        # If not IP format, assume it's a hostname (basic check)
        return len(target) > 0 and not target.isspace()