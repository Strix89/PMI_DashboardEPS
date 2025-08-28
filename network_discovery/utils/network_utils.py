"""
Network utility functions for IP address calculations and network operations.

This module provides helper functions for common network operations such as
IP address validation, CIDR calculations, and network range operations.
"""

import ipaddress
import socket
from typing import List, Tuple, Optional


def is_valid_ip(ip_address: str) -> bool:
    """
    Check if a string represents a valid IPv4 address.
    
    Args:
        ip_address: String to validate as IPv4 address
        
    Returns:
        bool: True if valid IPv4 address, False otherwise
    """
    try:
        ipaddress.IPv4Address(ip_address)
        return True
    except ipaddress.AddressValueError:
        return False


def is_valid_network(network: str) -> bool:
    """
    Check if a string represents a valid IPv4 network in CIDR notation.
    
    Args:
        network: String to validate as IPv4 network (e.g., "192.168.1.0/24")
        
    Returns:
        bool: True if valid IPv4 network, False otherwise
    """
    try:
        ipaddress.IPv4Network(network, strict=False)
        return True
    except ipaddress.AddressValueError:
        return False


def cidr_to_netmask(cidr: int) -> str:
    """
    Convert CIDR notation to dotted decimal netmask.
    
    Args:
        cidr: CIDR prefix length (0-32)
        
    Returns:
        str: Dotted decimal netmask (e.g., "255.255.255.0")
        
    Raises:
        ValueError: If CIDR is not in valid range (0-32)
    """
    if not 0 <= cidr <= 32:
        raise ValueError(f"CIDR must be between 0 and 32, got {cidr}")
    
    # Create network with dummy IP to get netmask
    network = ipaddress.IPv4Network(f"0.0.0.0/{cidr}")
    return str(network.netmask)


def netmask_to_cidr(netmask: str) -> int:
    """
    Convert dotted decimal netmask to CIDR notation.
    
    Args:
        netmask: Dotted decimal netmask (e.g., "255.255.255.0")
        
    Returns:
        int: CIDR prefix length
        
    Raises:
        ValueError: If netmask is invalid
    """
    try:
        # Create network with dummy IP to get prefix length
        network = ipaddress.IPv4Network(f"0.0.0.0/{netmask}")
        return network.prefixlen
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid netmask: {netmask}") from e


def get_network_info(ip_address: str, netmask: str) -> Tuple[str, str, str]:
    """
    Get network address, broadcast address, and CIDR from IP and netmask.
    
    Args:
        ip_address: IP address within the network
        netmask: Subnet mask (dotted decimal or CIDR)
        
    Returns:
        Tuple[str, str, str]: Network address, broadcast address, CIDR notation
        
    Raises:
        ValueError: If IP address or netmask is invalid
    """
    try:
        network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
        return (
            str(network.network_address),
            str(network.broadcast_address),
            f"{network.network_address}/{network.prefixlen}"
        )
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid IP or netmask: {ip_address}/{netmask}") from e


def get_host_count(netmask: str) -> int:
    """
    Calculate the number of host addresses in a network.
    
    Args:
        netmask: Subnet mask (dotted decimal or CIDR)
        
    Returns:
        int: Number of host addresses (excluding network and broadcast)
        
    Raises:
        ValueError: If netmask is invalid
    """
    try:
        network = ipaddress.IPv4Network(f"0.0.0.0/{netmask}")
        return network.num_addresses - 2  # Exclude network and broadcast
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid netmask: {netmask}") from e


def ip_in_network(ip_address: str, network: str) -> bool:
    """
    Check if an IP address is within a given network.
    
    Args:
        ip_address: IP address to check
        network: Network in CIDR notation (e.g., "192.168.1.0/24")
        
    Returns:
        bool: True if IP is in network, False otherwise
    """
    try:
        ip = ipaddress.IPv4Address(ip_address)
        net = ipaddress.IPv4Network(network, strict=False)
        return ip in net
    except ipaddress.AddressValueError:
        return False


def generate_ip_range(start_ip: str, end_ip: str) -> List[str]:
    """
    Generate a list of IP addresses between start and end (inclusive).
    
    Args:
        start_ip: Starting IP address
        end_ip: Ending IP address
        
    Returns:
        List[str]: List of IP addresses in the range
        
    Raises:
        ValueError: If IP addresses are invalid or start > end
    """
    try:
        start = ipaddress.IPv4Address(start_ip)
        end = ipaddress.IPv4Address(end_ip)
        
        if start > end:
            raise ValueError(f"Start IP {start_ip} is greater than end IP {end_ip}")
        
        ip_list = []
        current = start
        while current <= end:
            ip_list.append(str(current))
            current += 1
            
        return ip_list
        
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid IP address: {e}")


def get_network_hosts(network: str, exclude_addresses: Optional[List[str]] = None) -> List[str]:
    """
    Get all host addresses in a network, optionally excluding specific addresses.
    
    Args:
        network: Network in CIDR notation (e.g., "192.168.1.0/24")
        exclude_addresses: List of IP addresses to exclude from the result
        
    Returns:
        List[str]: List of host IP addresses
        
    Raises:
        ValueError: If network is invalid
    """
    try:
        net = ipaddress.IPv4Network(network, strict=False)
        hosts = [str(ip) for ip in net.hosts()]
        
        if exclude_addresses:
            # Filter out excluded addresses
            exclude_set = set(exclude_addresses)
            hosts = [ip for ip in hosts if ip not in exclude_set]
        
        return hosts
        
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid network: {network}") from e


def is_private_ip(ip_address: str) -> bool:
    """
    Check if an IP address is in a private network range.
    
    Private ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
    
    Args:
        ip_address: IP address to check
        
    Returns:
        bool: True if IP is private, False otherwise
    """
    try:
        ip = ipaddress.IPv4Address(ip_address)
        return ip.is_private
    except ipaddress.AddressValueError:
        return False


def is_loopback_ip(ip_address: str) -> bool:
    """
    Check if an IP address is a loopback address.
    
    Args:
        ip_address: IP address to check
        
    Returns:
        bool: True if IP is loopback, False otherwise
    """
    try:
        ip = ipaddress.IPv4Address(ip_address)
        return ip.is_loopback
    except ipaddress.AddressValueError:
        return False


def resolve_hostname(ip_address: str, timeout: float = 2.0) -> Optional[str]:
    """
    Attempt to resolve an IP address to a hostname.
    
    Args:
        ip_address: IP address to resolve
        timeout: Timeout in seconds for the resolution attempt
        
    Returns:
        Optional[str]: Hostname if resolution successful, None otherwise
    """
    try:
        socket.setdefaulttimeout(timeout)
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, socket.gaierror, socket.timeout):
        return None
    finally:
        socket.setdefaulttimeout(None)


def ping_host(ip_address: str, timeout: int = 3) -> bool:
    """
    Ping a host to check if it's reachable.
    
    Args:
        ip_address: IP address to ping
        timeout: Timeout in seconds
        
    Returns:
        bool: True if host is reachable, False otherwise
    """
    import subprocess
    import platform
    
    system = platform.system().lower()
    
    try:
        if system == "windows":
            # Windows ping command
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), ip_address]
        else:
            # Unix-like systems
            cmd = ["ping", "-c", "1", "-W", str(timeout), ip_address]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        
        return result.returncode == 0
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False


def calculate_network_size(cidr: int) -> Tuple[int, int]:
    """
    Calculate total addresses and host addresses for a given CIDR.
    
    Args:
        cidr: CIDR prefix length (0-32)
        
    Returns:
        Tuple[int, int]: Total addresses, host addresses
        
    Raises:
        ValueError: If CIDR is not in valid range
    """
    if not 0 <= cidr <= 32:
        raise ValueError(f"CIDR must be between 0 and 32, got {cidr}")
    
    total_addresses = 2 ** (32 - cidr)
    host_addresses = max(0, total_addresses - 2)  # Exclude network and broadcast
    
    return total_addresses, host_addresses


def get_subnet_info(ip_address: str, netmask: str) -> dict:
    """
    Get comprehensive subnet information for an IP address and netmask.
    
    Args:
        ip_address: IP address within the subnet
        netmask: Subnet mask (dotted decimal or CIDR)
        
    Returns:
        dict: Dictionary containing subnet information
        
    Raises:
        ValueError: If IP address or netmask is invalid
    """
    try:
        network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
        
        total_addresses, host_addresses = calculate_network_size(network.prefixlen)
        
        return {
            'network_address': str(network.network_address),
            'broadcast_address': str(network.broadcast_address),
            'netmask': str(network.netmask),
            'cidr': network.prefixlen,
            'cidr_notation': str(network),
            'total_addresses': total_addresses,
            'host_addresses': host_addresses,
            'first_host': str(list(network.hosts())[0]) if host_addresses > 0 else None,
            'last_host': str(list(network.hosts())[-1]) if host_addresses > 0 else None,
            'is_private': network.is_private
        }
        
    except ipaddress.AddressValueError as e:
        raise ValueError(f"Invalid IP or netmask: {ip_address}/{netmask}") from e