"""
Main entry point for the Network Discovery Module.

This module provides the command-line interface for the network discovery tool,
including argument parsing, pre-flight checks, and graceful shutdown handling.
"""

import argparse
import os
import sys
import signal
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .core.scanner_orchestrator import ScannerOrchestrator
from .utils.logger import Logger, LogLevel, get_logger, set_log_level


class NetworkDiscoveryApp:
    """
    Main application class for Network Discovery Module.
    
    Handles CLI interface, pre-flight checks, and application lifecycle.
    """
    
    def __init__(self):
        """Initialize the application."""
        self.logger = get_logger(__name__)
        self.orchestrator: Optional[ScannerOrchestrator] = None
        self.shutdown_requested = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_names = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}
        signal_name = signal_names.get(signum, f"Signal {signum}")
        
        if not self.shutdown_requested:
            self.logger.warning(f"Received {signal_name} - initiating graceful shutdown...")
            self.shutdown_requested = True
            self._cleanup()
            sys.exit(0)
        else:
            self.logger.error("Force shutdown requested - terminating immediately")
            sys.exit(1)
    
    def _cleanup(self) -> None:
        """Perform cleanup operations before shutdown."""
        self.logger.info("Performing cleanup operations...")
        
        # Add any cleanup logic here if needed
        # For now, just log the cleanup
        self.logger.info("Cleanup completed")
    
    def _check_tool_availability(self, tool_name: str) -> bool:
        """
        Check if a required external tool is available.
        
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
            self.logger.error(f"Required tool '{tool_name}' not found in PATH")
            return False
    
    def _check_tool_permissions(self, tool_name: str) -> bool:
        """
        Check if we can execute a tool and if it requires elevated permissions.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            bool: True if tool can be executed, False otherwise
        """
        try:
            # Try to run the tool with --help or --version to check permissions
            if tool_name == "nmap":
                result = subprocess.run(
                    [tool_name, "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
            elif tool_name == "arping":
                result = subprocess.run(
                    [tool_name, "--help"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
            else:
                return True  # Skip permission check for unknown tools
            
            if result.returncode == 0:
                self.logger.debug(f"Tool {tool_name} is executable")
                return True
            else:
                self.logger.warning(f"Tool {tool_name} returned error code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Tool {tool_name} check timed out")
            return False
        except FileNotFoundError:
            self.logger.error(f"Tool {tool_name} not found")
            return False
        except Exception as e:
            self.logger.warning(f"Could not check {tool_name} permissions: {str(e)}")
            return True  # Assume it's okay and let the scanner handle it
    
    def _perform_preflight_checks(self) -> bool:
        """
        Perform pre-flight checks for required external tools.
        
        Returns:
            bool: True if all checks pass, False otherwise
        """
        self.logger.section("PRE-FLIGHT CHECKS")
        
        required_tools = ["nmap", "arping"]
        all_checks_passed = True
        
        for tool in required_tools:
            self.logger.info(f"Checking availability of {tool}...")
            
            # Check if tool is available
            if not self._check_tool_availability(tool):
                all_checks_passed = False
                self._suggest_tool_installation(tool)
                continue
            
            # Check if tool can be executed
            if not self._check_tool_permissions(tool):
                self.logger.warning(f"Tool {tool} may require elevated permissions")
                self._suggest_permission_solution(tool)
        
        # Check Python dependencies
        self.logger.info("Checking Python dependencies...")
        missing_deps = self._check_python_dependencies()
        if missing_deps:
            all_checks_passed = False
            self.logger.error(f"Missing Python dependencies: {', '.join(missing_deps)}")
            self.logger.info("Install missing dependencies with: pip install -r requirements.txt")
        
        if all_checks_passed:
            self.logger.success("All pre-flight checks passed")
        else:
            self.logger.error("Some pre-flight checks failed - see messages above")
        
        return all_checks_passed
    
    def _check_python_dependencies(self) -> list:
        """
        Check if required Python packages are available.
        
        Returns:
            list: List of missing package names
        """
        required_packages = [
            "colorama",
            "yaml", 
            "pysnmp",
            "scapy"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                self.logger.debug(f"Python package {package} is available")
            except ImportError:
                missing_packages.append(package)
                self.logger.debug(f"Python package {package} is missing")
        
        return missing_packages
    
    def _suggest_tool_installation(self, tool_name: str) -> None:
        """
        Provide installation suggestions for missing tools.
        
        Args:
            tool_name: Name of the missing tool
        """
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
            ]
        }
        
        if tool_name in suggestions:
            self.logger.info(f"Installation suggestions for {tool_name}:")
            for suggestion in suggestions[tool_name]:
                self.logger.info(f"  • {suggestion}")
    
    def _suggest_permission_solution(self, tool_name: str) -> None:
        """
        Provide permission solutions for tools that need elevated access.
        
        Args:
            tool_name: Name of the tool needing permissions
        """
        solutions = {
            "nmap": [
                "Run with sudo: sudo python -m network_discovery",
                "Or use non-privileged scan types in nmap_config.yml (-sT instead of -sS)"
            ],
            "arping": [
                "Run with sudo: sudo python -m network_discovery",
                "Or configure to use scapy method in arp_config.yml"
            ]
        }
        
        if tool_name in solutions:
            self.logger.info(f"Permission solutions for {tool_name}:")
            for solution in solutions[tool_name]:
                self.logger.info(f"  • {solution}")
    
    def _validate_paths(self, config_dir: Optional[str], output_dir: Optional[str]) -> tuple:
        """
        Validate and prepare configuration and output directories.
        
        Args:
            config_dir: Configuration directory path
            output_dir: Output directory path
            
        Returns:
            tuple: (validated_config_dir, validated_output_dir)
        """
        # Validate config directory
        if config_dir:
            config_path = Path(config_dir)
            if not config_path.exists():
                self.logger.error(f"Configuration directory does not exist: {config_dir}")
                sys.exit(1)
            if not config_path.is_dir():
                self.logger.error(f"Configuration path is not a directory: {config_dir}")
                sys.exit(1)
            validated_config_dir = str(config_path.resolve())
        else:
            # Use default config directory
            default_config = Path(__file__).parent / "config"
            validated_config_dir = str(default_config.resolve())
        
        # Validate/create output directory
        if output_dir:
            output_path = Path(output_dir)
            try:
                output_path.mkdir(parents=True, exist_ok=True)
                validated_output_dir = str(output_path.resolve())
            except Exception as e:
                self.logger.error(f"Cannot create output directory {output_dir}: {str(e)}")
                sys.exit(1)
        else:
            # Use default output directory
            default_output = Path(__file__).parent / "results"
            try:
                default_output.mkdir(parents=True, exist_ok=True)
                validated_output_dir = str(default_output.resolve())
            except Exception as e:
                self.logger.error(f"Cannot create default output directory: {str(e)}")
                sys.exit(1)
        
        self.logger.info(f"Using configuration directory: {validated_config_dir}")
        self.logger.info(f"Using output directory: {validated_output_dir}")
        
        return validated_config_dir, validated_output_dir
    
    def run(self, args: argparse.Namespace) -> int:
        """
        Run the network discovery application.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        try:
            # Perform pre-flight checks
            if not self._perform_preflight_checks():
                if not args.skip_checks:
                    self.logger.error("Pre-flight checks failed. Use --skip-checks to bypass.")
                    return 1
                else:
                    self.logger.warning("Skipping pre-flight checks as requested")
            
            # Validate paths
            config_dir, output_dir = self._validate_paths(args.config_dir, args.output_dir)
            
            # Initialize orchestrator
            self.logger.info("Initializing network discovery orchestrator...")
            self.orchestrator = ScannerOrchestrator(
                config_dir=config_dir,
                output_dir=output_dir,
                skip_arp=args.skip_arp
            )
            
            # Check for shutdown request before starting scan
            if self.shutdown_requested:
                self.logger.info("Shutdown requested before scan start")
                return 0
            
            # Execute the scan
            self.logger.info("Starting network discovery scan...")
            scan_result = self.orchestrator.execute_full_scan()
            
            # Check if scan completed successfully
            if scan_result.scan_metadata.scan_status.value == "completed":
                self.logger.success("Network discovery completed successfully!")
                return 0
            else:
                self.logger.error("Network discovery completed with errors")
                return 1
                
        except KeyboardInterrupt:
            self.logger.warning("Scan interrupted by user")
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            self.logger.error(f"Network discovery failed: {str(e)}", exception=e)
            return 1
        finally:
            self._cleanup()


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="network_discovery",
        description="Network Discovery Module - Automated network scanning using ARP, NMAP, and SNMP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m network_discovery                           # Run with default settings
  python -m network_discovery --config-dir ./configs   # Use custom config directory
  python -m network_discovery --output-dir ./reports   # Use custom output directory
  python -m network_discovery --skip-checks            # Skip pre-flight checks
  python -m network_discovery --verbose                # Enable verbose logging
  python -m network_discovery --skip-arp               # Skip ARP scan, run only NMAP+SNMP
        """
    )
    
    parser.add_argument(
        "--config-dir",
        type=str,
        help="Directory containing configuration files (arp_config.yml, nmap_config.yml, snmp_config.yml). "
             "Defaults to network_discovery/config/"
    )
    
    parser.add_argument(
        "--output-dir", 
        type=str,
        help="Directory for output JSON reports. Defaults to network_discovery/results/"
    )
    
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pre-flight checks for external tools (nmap, arping)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Enable verbose logging output"
    )
    
    parser.add_argument(
        "--skip-arp",
        action="store_true",
        help="Skip ARP scan phase"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Network Discovery Module 1.0.0"
    )
    
    return parser


def main() -> int:
    """
    Main entry point for the Network Discovery Module.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        set_log_level(LogLevel.DEBUG)
    
    # Create and run the application
    app = NetworkDiscoveryApp()
    return app.run(args)


if __name__ == "__main__":
    sys.exit(main())