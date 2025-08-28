"""
Network detection functionality for automatically detecting host network configuration.

This module provides the NetworkDetector class which automatically detects the host's
network configuration including IP address, subnet mask, default interface, and
calculates the appropriate scan range while excluding reserved addresses.
"""

import socket
import subprocess
import ipaddress
import platform
from typing import List, Optional, Tuple
from .data_models import NetworkInfo
from ..utils import logger


class NetworkDetector:
    """
    Detects host network configuration and calculates scan ranges.
    
    This class automatically detects the host's network configuration by finding
    the default network interface, IP address, and subnet mask. It then calculates
    the appropriate IP range for scanning while excluding the host IP, network
    address, and broadcast address.
    """
    
    def __init__(self):
        """Initialize the NetworkDetector."""
        self.logger = logger
    
    def get_host_network_info(self) -> NetworkInfo:
        """
        Detect and return the host's network configuration.
        
        Automatically detects the default network interface, IP address, and
        subnet mask of the host machine. Uses the default route to determine
        which interface to use for network scanning.
        
        Returns:
            NetworkInfo: Complete network configuration including scan range
            
        Raises:
            RuntimeError: If network configuration cannot be detected
        """
        try:
            # Get default interface and IP
            interface_name, host_ip = self._get_default_interface_and_ip()
            self.logger.info(f"Detected default interface: {interface_name}")
            self.logger.info(f"Host IP address: {host_ip}")
            
            # Get subnet mask for the interface
            netmask = self._get_interface_netmask(interface_name, host_ip)
            self.logger.info(f"Network mask: {netmask}")
            
            # Calculate network and broadcast addresses
            network = ipaddress.IPv4Network(f"{host_ip}/{netmask}", strict=False)
            network_address = str(network.network_address)
            broadcast_address = str(network.broadcast_address)
            
            self.logger.info(f"Network address: {network_address}")
            self.logger.info(f"Broadcast address: {broadcast_address}")
            
            # Calculate scan range (exclude host, network, and broadcast)
            scan_range = self.calculate_scan_range(host_ip, netmask)
            
            return NetworkInfo(
                host_ip=host_ip,
                netmask=netmask,
                network_address=network_address,
                broadcast_address=broadcast_address,
                interface_name=interface_name,
                scan_range=scan_range
            )
            
        except Exception as e:
            self.logger.error(f"Failed to detect network configuration: {e}")
            raise RuntimeError(f"Network detection failed: {e}")
    
    def calculate_scan_range(self, host_ip: str, netmask: str) -> List[str]:
        """
        Calculate the IP range to scan, excluding reserved addresses.
        
        Creates a list of IP addresses to scan within the network, excluding:
        - Host IP address (the scanning machine)
        - Network address (e.g., 192.168.1.0)
        - Broadcast address (e.g., 192.168.1.255)
        
        Args:
            host_ip: IP address of the host machine
            netmask: Network subnet mask (e.g., "255.255.255.0" or "24")
            
        Returns:
            List[str]: List of IP addresses to scan
        """
        try:
            # Create network object
            network = ipaddress.IPv4Network(f"{host_ip}/{netmask}", strict=False)
            
            # Get all addresses in the network
            all_addresses = list(network.hosts())
            
            # Convert host IP to IPv4Address for comparison
            host_addr = ipaddress.IPv4Address(host_ip)
            
            # Filter out the host IP
            scan_addresses = [str(addr) for addr in all_addresses if addr != host_addr]
            
            # Log exclusions
            excluded = [str(network.network_address), host_ip, str(network.broadcast_address)]
            self.logger.info(f"Excluded addresses: {excluded}")
            self.logger.info(f"Scan range: {len(scan_addresses)} addresses from {scan_addresses[0] if scan_addresses else 'N/A'} to {scan_addresses[-1] if scan_addresses else 'N/A'}")
            
            return scan_addresses
            
        except Exception as e:
            self.logger.error(f"Failed to calculate scan range: {e}")
            raise RuntimeError(f"Scan range calculation failed: {e}")
    
    def _get_default_interface_and_ip(self) -> Tuple[str, str]:
        """
        Get the default network interface and its IP address.
        
        Uses the default route to determine which interface is used for
        external network communication.
        
        Returns:
            Tuple[str, str]: Interface name and IP address
            
        Raises:
            RuntimeError: If default interface cannot be determined
        """
        system = platform.system().lower()
        
        try:
            if system == "windows":
                return self._get_windows_default_interface()
            else:
                return self._get_unix_default_interface()
        except Exception as e:
            self.logger.error(f"Failed to get default interface: {e}")
            raise RuntimeError(f"Could not determine default interface: {e}")
    
    def _get_windows_default_interface(self) -> Tuple[str, str]:
        """Get default interface on Windows systems."""
        try:
            # First, get all network interfaces and cache them
            interfaces = self._get_all_windows_interfaces()
            self._cached_interfaces = interfaces  # Cache for later use
            
            if not interfaces:
                self.logger.warning("No network interfaces found, using socket method")
                return self._get_interface_via_socket()
            
            # If only one interface, use it
            if len(interfaces) == 1:
                interface = interfaces[0]
                self.logger.info(f"Single interface found: {interface['name']}")
                return interface['name'], interface['ip']
            
            # Multiple interfaces - try to find the best one
            best_interface = self._select_best_interface(interfaces)
            if best_interface:
                return best_interface['name'], best_interface['ip']
            
            # Fallback: use socket method
            return self._get_interface_via_socket()
            
        except Exception as e:
            self.logger.warning(f"Interface detection failed: {e}")
            return self._get_interface_via_socket()
    
    def _get_unix_default_interface(self) -> Tuple[str, str]:
        """Get default interface on Unix-like systems (Linux, macOS)."""
        try:
            # Try ip route first (Linux)
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output: "default via 192.168.1.1 dev eth0"
            for line in result.stdout.split('\n'):
                if 'default' in line and 'dev' in line:
                    parts = line.split()
                    if 'dev' in parts:
                        dev_index = parts.index('dev')
                        if dev_index + 1 < len(parts):
                            interface_name = parts[dev_index + 1]
                            # Get IP for this interface
                            interface_ip = self._get_interface_ip_unix(interface_name)
                            return interface_name, interface_ip
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try route command (macOS/older systems)
            try:
                result = subprocess.run(
                    ["route", "-n", "get", "default"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                interface_name = None
                for line in result.stdout.split('\n'):
                    if 'interface:' in line:
                        interface_name = line.split(':')[1].strip()
                        break
                
                if interface_name:
                    interface_ip = self._get_interface_ip_unix(interface_name)
                    return interface_name, interface_ip
                    
            except subprocess.CalledProcessError:
                pass
        
        # Fallback: use socket method
        return self._get_interface_via_socket()
    
    def _get_interface_via_socket(self) -> Tuple[str, str]:
        """
        Fallback method to get interface using socket connection.
        
        Creates a socket connection to an external address to determine
        which local interface would be used.
        """
        try:
            # Connect to a public DNS server to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            
            # Interface name might not be easily determinable this way
            interface_name = "auto-detected"
            
            self.logger.info(f"Using socket method, detected IP: {local_ip}")
            return interface_name, local_ip
            
        except Exception as e:
            raise RuntimeError(f"Socket method failed: {e}")
    
    def _get_interface_netmask(self, interface_name: str, ip_address: str) -> str:
        """
        Get the subnet mask for the specified interface.
        
        Args:
            interface_name: Name of the network interface
            ip_address: IP address of the interface
            
        Returns:
            str: Subnet mask in CIDR notation (e.g., "24")
        """
        system = platform.system().lower()
        
        try:
            if system == "windows":
                # Use cached interfaces if available to avoid duplicate calls
                if hasattr(self, '_cached_interfaces') and self._cached_interfaces:
                    for iface in self._cached_interfaces:
                        if iface['ip'] == ip_address:
                            return iface['subnet']
                
                # Fallback to original method
                return self._get_windows_netmask(ip_address)
            else:
                return self._get_unix_netmask(interface_name, ip_address)
        except Exception as e:
            self.logger.warning(f"Could not determine netmask, using default /24: {e}")
            return "24"  # Default to /24 if detection fails
    
    def _get_windows_netmask(self, ip_address: str) -> str:
        """Get netmask on Windows using ipconfig."""
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                check=True
            )
            
            lines = result.stdout.split('\n')
            found_ip = False
            
            for line in lines:
                if ip_address in line and 'IPv4' in line:
                    found_ip = True
                elif found_ip and 'Subnet Mask' in line:
                    # Extract subnet mask
                    mask = line.split(':')[1].strip()
                    # Convert to CIDR notation
                    return self._netmask_to_cidr(mask)
            
            return "24"  # Default fallback
            
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            return "24"
    
    def _get_unix_netmask(self, interface_name: str, ip_address: str) -> str:
        """Get netmask on Unix systems using ip or ifconfig."""
        try:
            # Try ip command first
            result = subprocess.run(
                ["ip", "addr", "show", interface_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.split('\n'):
                if ip_address in line and '/' in line:
                    # Extract CIDR notation: "192.168.1.100/24"
                    parts = line.split()
                    for part in parts:
                        if ip_address in part and '/' in part:
                            return part.split('/')[1]
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try ifconfig as fallback
            try:
                result = subprocess.run(
                    ["ifconfig", interface_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                for line in result.stdout.split('\n'):
                    if 'netmask' in line.lower():
                        # Extract netmask and convert to CIDR
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if 'netmask' in part.lower() and i + 1 < len(parts):
                                mask = parts[i + 1]
                                return self._netmask_to_cidr(mask)
                
            except subprocess.CalledProcessError:
                pass
        
        return "24"  # Default fallback
    
    def _get_windows_interface_name(self, ip_address: str) -> str:
        """Get Windows interface name for given IP address."""
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                check=True
            )
            
            lines = result.stdout.split('\n')
            current_adapter = None
            
            for line in lines:
                if 'adapter' in line.lower() and ':' in line:
                    current_adapter = line.strip()
                elif ip_address in line and current_adapter:
                    return current_adapter
            
            return "Unknown Interface"
            
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            return "Unknown Interface"
    
    def _get_interface_ip_unix(self, interface_name: str) -> str:
        """Get IP address for Unix interface."""
        try:
            # Try ip command
            result = subprocess.run(
                ["ip", "addr", "show", interface_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.split('\n'):
                if 'inet ' in line and not '127.0.0.1' in line:
                    # Extract IP: "inet 192.168.1.100/24"
                    parts = line.split()
                    for part in parts:
                        if '.' in part and '/' in part:
                            return part.split('/')[0]
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Try ifconfig
            try:
                result = subprocess.run(
                    ["ifconfig", interface_name],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and not '127.0.0.1' in line:
                        parts = line.split()
                        for part in parts:
                            if self._is_valid_ip(part):
                                return part
                
            except subprocess.CalledProcessError:
                pass
        
        raise RuntimeError(f"Could not get IP for interface {interface_name}")
    
    def _netmask_to_cidr(self, netmask: str) -> str:
        """Convert dotted decimal netmask to CIDR notation."""
        try:
            # Handle hex format (0xffffff00)
            if netmask.startswith('0x'):
                netmask_int = int(netmask, 16)
                return str(bin(netmask_int).count('1'))
            
            # Handle dotted decimal format (255.255.255.0)
            if '.' in netmask:
                network = ipaddress.IPv4Network(f"0.0.0.0/{netmask}")
                return str(network.prefixlen)
            
            # Already in CIDR format
            return netmask
            
        except Exception:
            return "24"  # Default fallback
    
    def _get_all_windows_interfaces(self) -> List[dict]:
        """Get all network interfaces on Windows with their details."""
        interfaces = []
        
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                check=True
            )
            
            lines = result.stdout.split('\n')
            current_adapter = None
            current_ip = None
            current_subnet = None
            
            for line in lines:
                line = line.strip()
                
                # New adapter section
                if 'adapter' in line.lower() and ':' in line:
                    # Save previous adapter if it had valid IP
                    if current_adapter and current_ip and self._is_valid_interface_ip(current_ip):
                        interfaces.append({
                            'name': current_adapter,
                            'ip': current_ip,
                            'subnet': current_subnet or '24'
                        })
                    
                    current_adapter = line
                    current_ip = None
                    current_subnet = None
                
                # IPv4 address
                elif 'IPv4' in line and ':' in line:
                    ip_part = line.split(':')[1].strip()
                    # Remove any parenthetical info like "(Preferred)"
                    if '(' in ip_part:
                        ip_part = ip_part.split('(')[0].strip()
                    if self._is_valid_ip(ip_part):
                        current_ip = ip_part
                
                # Subnet mask
                elif 'Subnet Mask' in line and ':' in line:
                    mask = line.split(':')[1].strip()
                    current_subnet = self._netmask_to_cidr(mask)
            
            # Don't forget the last adapter
            if current_adapter and current_ip and self._is_valid_interface_ip(current_ip):
                interfaces.append({
                    'name': current_adapter,
                    'ip': current_ip,
                    'subnet': current_subnet or '24'
                })
            
            self.logger.info(f"Found {len(interfaces)} valid network interfaces")
            for i, iface in enumerate(interfaces):
                self.logger.info(f"  {i+1}. {iface['name'][:50]}... - IP: {iface['ip']}")
            
            return interfaces
            
        except (subprocess.CalledProcessError, UnicodeDecodeError) as e:
            self.logger.error(f"Failed to get Windows interfaces: {e}")
            return []
    
    def _select_best_interface(self, interfaces: List[dict]) -> Optional[dict]:
        """Select the best interface from available options."""
        if not interfaces:
            return None
        
        # Score interfaces based on priority
        scored_interfaces = []
        
        for iface in interfaces:
            name_lower = iface['name'].lower()
            ip = iface['ip']
            score = 0
            
            # Negative scores for virtual/unwanted interfaces
            virtual_keywords = [
                'virtualbox', 'vmware', 'hyper-v', 'docker', 'vethernet',
                'wi-fi direct', 'teredo', 'isatap', 'bluetooth'
            ]
            
            if any(keyword in name_lower for keyword in virtual_keywords):
                score -= 100
            
            # Positive scores for real interfaces
            if 'ethernet' in name_lower:
                score += 50
            elif 'wi-fi' in name_lower or 'wireless' in name_lower:
                score += 30
            
            # Prefer common network ranges
            if ip.startswith('192.168.1.'):
                score += 20
            elif ip.startswith('192.168.'):
                score += 15
            elif ip.startswith('10.'):
                score += 10
            
            # Avoid host-only networks
            if 'host-only' in name_lower:
                score -= 50
            
            scored_interfaces.append((score, iface))
        
        # Sort by score (highest first)
        scored_interfaces.sort(key=lambda x: x[0], reverse=True)
        
        # Log scoring results
        self.logger.info("Interface scoring results:")
        for score, iface in scored_interfaces:
            self.logger.info(f"  Score {score:3d}: {iface['name'][:50]}... - IP: {iface['ip']}")
        
        # Select the highest scored interface
        selected = scored_interfaces[0][1]
        self.logger.info(f"Selected interface: {selected['name'][:50]}... - IP: {selected['ip']}")
        return selected
    
    def _is_valid_interface_ip(self, ip: str) -> bool:
        """Check if IP is valid for network interface (not loopback, not APIPA)."""
        if not self._is_valid_ip(ip):
            return False
        
        try:
            ip_addr = ipaddress.IPv4Address(ip)
            
            # Skip loopback
            if ip_addr.is_loopback:
                return False
            
            # Skip APIPA (169.254.x.x)
            if ip.startswith('169.254.'):
                return False
            
            # Skip multicast
            if ip_addr.is_multicast:
                return False
            
            return True
            
        except ipaddress.AddressValueError:
            return False
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if string is a valid IPv4 address."""
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False