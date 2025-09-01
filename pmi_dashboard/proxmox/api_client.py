"""
Proxmox API Client for PMI Dashboard

This module provides a comprehensive client for interacting with Proxmox VE API,
including authentication, node management, VM/LXC operations, and metrics retrieval.
"""

import requests
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin
from datetime import datetime
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ProxmoxAPIError(Exception):
    """Custom exception for Proxmox API related errors."""

    pass


class ProxmoxAuthenticationError(ProxmoxAPIError):
    """Exception raised for authentication failures."""

    pass


class ProxmoxConnectionError(ProxmoxAPIError):
    """Exception raised for connection failures."""

    pass


class ProxmoxAPIClient:
    """
    Proxmox VE API client with comprehensive functionality for node management,
    VM/LXC operations, and real-time metrics retrieval.
    """

    def __init__(
        self,
        host: str,
        port: int = 8006,
        api_token_id: str = None,
        api_token_secret: str = None,
        ssl_verify: bool = False,
        timeout: int = 30,
    ):
        """
        Initialize Proxmox API client.

        Args:
            host: Proxmox server hostname or IP address
            port: Proxmox API port (default: 8006)
            api_token_id: API token ID for authentication
            api_token_secret: API token secret for authentication
            ssl_verify: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.api_token_id = api_token_id
        self.api_token_secret = api_token_secret
        self.ssl_verify = ssl_verify
        self.timeout = timeout

        # Build base URL
        protocol = "https" if port == 8006 else "http"
        self.base_url = f"{protocol}://{host}:{port}/api2/json"

        # Session for connection reuse
        self.session = requests.Session()

        # Set up authentication headers if tokens provided
        if api_token_id and api_token_secret:
            self.session.headers.update(
                {"Authorization": f"PVEAPIToken={api_token_id}={api_token_secret}"}
            )

        # Configure SSL verification
        self.session.verify = ssl_verify

        logger.debug(f"Initialized Proxmox API client for {host}:{port}")

    def _make_request(
        self, method: str, endpoint: str, data: Dict = None, params: Dict = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Proxmox API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without /api2/json prefix)
            data: Request body data
            params: URL parameters

        Returns:
            Response data dictionary

        Raises:
            ProxmoxConnectionError: For connection issues
            ProxmoxAuthenticationError: For authentication failures
            ProxmoxAPIError: For other API errors
        """
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))

        try:
            logger.debug(f"Making {method} request to {url}")

            response = self.session.request(
                method=method,
                url=url,
                json=data if method in ["POST", "PUT"] else None,
                params=params,
                timeout=self.timeout,
            )

            # Check for HTTP errors
            if response.status_code == 401:
                raise ProxmoxAuthenticationError(
                    "Authentication failed - check API token"
                )
            elif response.status_code == 403:
                raise ProxmoxAuthenticationError(
                    "Access denied - insufficient permissions"
                )
            elif response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise ProxmoxAPIError(error_msg)

            # Parse JSON response
            try:
                result = response.json()
            except json.JSONDecodeError:
                raise ProxmoxAPIError(f"Invalid JSON response: {response.text}")

            # Check for Proxmox API errors
            if "errors" in result:
                error_msg = "; ".join(result["errors"])
                raise ProxmoxAPIError(f"Proxmox API error: {error_msg}")

            return result.get("data", result)

        except requests.exceptions.ConnectTimeout:
            raise ProxmoxConnectionError(
                f"Connection timeout to {self.host}:{self.port}"
            )
        except requests.exceptions.ConnectionError as e:
            raise ProxmoxConnectionError(
                f"Connection failed to {self.host}:{self.port}: {str(e)}"
            )
        except requests.exceptions.Timeout:
            raise ProxmoxConnectionError(f"Request timeout to {self.host}:{self.port}")
        except requests.exceptions.RequestException as e:
            raise ProxmoxConnectionError(f"Request failed: {str(e)}")

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Proxmox server and validate authentication.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Try to get version information - this requires minimal permissions
            result = self._make_request("GET", "/version")

            if result and "version" in result:
                version = result["version"]
                logger.info(f"Successfully connected to Proxmox VE {version}")
                return True, f"Connected to Proxmox VE {version}"
            else:
                return False, "Connected but received unexpected response"

        except ProxmoxAuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            return False, f"Authentication failed: {str(e)}"
        except ProxmoxConnectionError as e:
            logger.error(f"Connection failed: {e}")
            return False, f"Connection failed: {str(e)}"
        except ProxmoxAPIError as e:
            logger.error(f"API error: {e}")
            return False, f"API error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, f"Unexpected error: {str(e)}"

    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get cluster status and node information.

        Returns:
            Cluster status information
        """
        try:
            return self._make_request("GET", "/cluster/status")
        except ProxmoxAPIError:
            # If cluster API fails, try nodes endpoint
            return self._make_request("GET", "/nodes")

    def get_nodes(self) -> List[Dict[str, Any]]:
        """
        Get list of all nodes in the cluster.

        Returns:
            List of node information dictionaries
        """
        return self._make_request("GET", "/nodes")

    def get_node_status(self, node: str) -> Dict[str, Any]:
        """
        Get detailed status information for a specific node.

        Args:
            node: Node name

        Returns:
            Node status information
        """
        return self._make_request("GET", f"/nodes/{node}/status")

    def get_node_resources(self, node: str) -> List[Dict[str, Any]]:
        """
        Get all resources (VMs, LXCs, storage) for a specific node.

        Args:
            node: Node name

        Returns:
            List of resource information
        """
        return self._make_request("GET", f"/nodes/{node}/qemu") + self._make_request(
            "GET", f"/nodes/{node}/lxc"
        )

    def get_vms(self, node: str) -> List[Dict[str, Any]]:
        """
        Get list of VMs (QEMU) on a specific node.

        Args:
            node: Node name

        Returns:
            List of VM information
        """
        return self._make_request("GET", f"/nodes/{node}/qemu")

    def get_containers(self, node: str) -> List[Dict[str, Any]]:
        """
        Get list of LXC containers on a specific node.

        Args:
            node: Node name

        Returns:
            List of container information
        """
        return self._make_request("GET", f"/nodes/{node}/lxc")

    def get_vm_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get detailed status for a specific VM.

        Args:
            node: Node name
            vmid: VM ID

        Returns:
            VM status information
        """
        return self._make_request("GET", f"/nodes/{node}/qemu/{vmid}/status/current")

    def get_container_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get detailed status for a specific LXC container.

        Args:
            node: Node name
            vmid: Container ID

        Returns:
            Container status information
        """
        return self._make_request("GET", f"/nodes/{node}/lxc/{vmid}/status/current")

    def start_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Start a VM.

        Args:
            node: Node name
            vmid: VM ID

        Returns:
            Operation result
        """
        logger.info(f"Starting VM {vmid} on node {node}")
        return self._make_request("POST", f"/nodes/{node}/qemu/{vmid}/status/start")

    def stop_vm(self, node: str, vmid: int, force: bool = False) -> Dict[str, Any]:
        """
        Stop a VM.

        Args:
            node: Node name
            vmid: VM ID
            force: Force stop (equivalent to power off)

        Returns:
            Operation result
        """
        logger.info(f"Stopping VM {vmid} on node {node} (force={force})")
        data = {"forceStop": 1} if force else {}
        return self._make_request(
            "POST", f"/nodes/{node}/qemu/{vmid}/status/stop", data=data
        )

    def restart_vm(self, node: str, vmid: int, force: bool = False) -> Dict[str, Any]:
        """
        Restart a VM.

        Args:
            node: Node name
            vmid: VM ID
            force: Force restart

        Returns:
            Operation result
        """
        logger.info(f"Restarting VM {vmid} on node {node} (force={force})")
        data = {"forceStop": 1} if force else {}
        return self._make_request(
            "POST", f"/nodes/{node}/qemu/{vmid}/status/reboot", data=data
        )

    def start_container(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Start an LXC container.

        Args:
            node: Node name
            vmid: Container ID

        Returns:
            Operation result
        """
        logger.info(f"Starting container {vmid} on node {node}")
        return self._make_request("POST", f"/nodes/{node}/lxc/{vmid}/status/start")

    def stop_container(
        self, node: str, vmid: int, force: bool = False
    ) -> Dict[str, Any]:
        """
        Stop an LXC container.

        Args:
            node: Node name
            vmid: Container ID
            force: Force stop

        Returns:
            Operation result
        """
        logger.info(f"Stopping container {vmid} on node {node} (force={force})")
        data = {"forceStop": 1} if force else {}
        return self._make_request(
            "POST", f"/nodes/{node}/lxc/{vmid}/status/stop", data=data
        )

    def restart_container(
        self, node: str, vmid: int, force: bool = False
    ) -> Dict[str, Any]:
        """
        Restart an LXC container.

        Args:
            node: Node name
            vmid: Container ID
            force: Force restart

        Returns:
            Operation result
        """
        logger.info(f"Restarting container {vmid} on node {node} (force={force})")
        data = {"forceStop": 1} if force else {}
        return self._make_request(
            "POST", f"/nodes/{node}/lxc/{vmid}/status/reboot", data=data
        )

    def get_vm_metrics(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get real-time metrics for a VM.

        Args:
            node: Node name
            vmid: VM ID

        Returns:
            VM metrics including CPU, memory, disk, and network usage
        """
        try:
            # Get current status which includes basic metrics
            status = self.get_vm_status(node, vmid)

            # Calculate disk usage using blockstat data
            disk_usage, disk_total = self._calculate_vm_disk_usage(status)

            # Use basic metrics from status (no slow RRD or cluster calls)
            metrics = {
                "vmid": vmid,
                "name": status.get("name", f"VM-{vmid}"),
                "status": status.get("status", "unknown"),
                "uptime": status.get("uptime", 0),
                "cpu_usage": status.get("cpu", 0) * 100,  # Convert from 0-1 to 0-100 percentage
                "memory_usage": status.get("mem", 0),
                "memory_total": status.get("maxmem", 0),
                "memory_percentage": (
                    (status.get("mem", 0) / status.get("maxmem", 1)) * 100
                    if status.get("maxmem")
                    else 0
                ),
                "disk_usage": disk_usage,
                "disk_total": disk_total,
                "disk_percentage": (
                    (disk_usage / disk_total * 100)
                    if disk_total > 0
                    else 0
                ),
                "network_in": status.get("netin", 0),
                "network_out": status.get("netout", 0),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

            return metrics

        except ProxmoxAPIError as e:
            logger.error(f"Failed to get VM {vmid} metrics: {e}")
            return {
                "vmid": vmid,
                "name": f"VM-{vmid}",
                "status": "unknown",
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

    def get_container_metrics(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get real-time metrics for an LXC container.

        Args:
            node: Node name
            vmid: Container ID

        Returns:
            Container metrics including CPU, memory, disk, and network usage
        """
        try:
            # Get current status which includes basic metrics
            status = self.get_container_status(node, vmid)

            # Use basic metrics from status (no slow RRD or cluster calls)
            metrics = {
                "vmid": vmid,
                "name": status.get("name", f"CT-{vmid}"),
                "status": status.get("status", "unknown"),
                "uptime": status.get("uptime", 0),
                "cpu_usage": status.get("cpu", 0) * 100,  # Convert from 0-1 to 0-100 percentage
                "memory_usage": status.get("mem", 0),
                "memory_total": status.get("maxmem", 0),
                "memory_percentage": (
                    (status.get("mem", 0) / status.get("maxmem", 1)) * 100
                    if status.get("maxmem")
                    else 0
                ),
                "disk_usage": status.get("disk", 0),
                "disk_total": status.get("maxdisk", 0),
                "disk_percentage": (
                    (status.get("disk", 0) / status.get("maxdisk", 1)) * 100
                    if status.get("maxdisk")
                    else 0
                ),
                "network_in": status.get("netin", 0),
                "network_out": status.get("netout", 0),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

            return metrics

        except ProxmoxAPIError as e:
            logger.error(f"Failed to get container {vmid} metrics: {e}")
            return {
                "vmid": vmid,
                "name": f"CT-{vmid}",
                "status": "unknown",
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

    def get_node_metrics(self, node: str) -> Dict[str, Any]:
        """
        Get real-time metrics for a node.

        Args:
            node: Node name

        Returns:
            Node metrics including CPU, memory, and disk usage
        """
        try:
            status = self.get_node_status(node)

            # Calculate percentages
            cpu_percentage = status.get("cpu", 0)  # Already in percentage
            memory_percentage = (
                status.get("memory", {}).get("used", 0)
                / status.get("memory", {}).get("total", 1)
            ) * 100

            # Get root filesystem info
            rootfs = status.get("rootfs", {})
            disk_percentage = (rootfs.get("used", 0) / rootfs.get("total", 1)) * 100

            metrics = {
                "node": node,
                "status": status.get("pveversion", "unknown"),
                "uptime": status.get("uptime", 0),
                "cpu_usage": cpu_percentage,
                "cpu_count": status.get("cpuinfo", {}).get("cpus", 0),
                "memory_usage": status.get("memory", {}).get("used", 0),
                "memory_total": status.get("memory", {}).get("total", 0),
                "memory_percentage": memory_percentage,
                "disk_usage": rootfs.get("used", 0),
                "disk_total": rootfs.get("total", 0),
                "disk_percentage": disk_percentage,
                "load_average": status.get("loadavg", [0, 0, 0]),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

            return metrics

        except ProxmoxAPIError as e:
            logger.error(f"Failed to get node {node} metrics: {e}")
            return {
                "node": node,
                "status": "unknown",
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat() + "Z",
            }

    def get_resource_disk_info(self, node: str, vmid: int, resource_type: str) -> Dict[str, int]:
        """
        Get detailed disk information for a VM or container.
        
        Args:
            node: Node name
            vmid: VM/Container ID
            resource_type: 'qemu' for VMs or 'lxc' for containers
            
        Returns:
            Dictionary with disk_usage and disk_total in bytes
        """
        disk_usage = 0
        disk_total = 0
        
        try:
            # Try to get disk usage from the cluster resources API
            cluster_resources = self._make_request("GET", "/cluster/resources", params={"type": resource_type})
            
            for resource in cluster_resources:
                if resource.get("vmid") == vmid and resource.get("node") == node:
                    disk_usage = resource.get("disk", 0)
                    disk_total = resource.get("maxdisk", 0)
                    break
            
            # If still no disk info, try alternative methods
            if disk_total == 0:
                if resource_type == "qemu":
                    # For VMs, check the configuration
                    config = self._make_request("GET", f"/nodes/{node}/qemu/{vmid}/config")
                    for key, value in config.items():
                        if key.startswith(('scsi', 'ide', 'sata', 'virtio')) and isinstance(value, str):
                            if 'size=' in value:
                                size_part = value.split('size=')[1].split(',')[0]
                                if size_part.endswith('G'):
                                    disk_total += int(size_part[:-1]) * 1024 * 1024 * 1024
                                elif size_part.endswith('M'):
                                    disk_total += int(size_part[:-1]) * 1024 * 1024
                else:
                    # For containers, check rootfs
                    config = self._make_request("GET", f"/nodes/{node}/lxc/{vmid}/config")
                    if 'rootfs' in config:
                        rootfs = config['rootfs']
                        if 'size=' in rootfs:
                            size_part = rootfs.split('size=')[1].split(',')[0]
                            if size_part.endswith('G'):
                                disk_total = int(size_part[:-1]) * 1024 * 1024 * 1024
                            elif size_part.endswith('M'):
                                disk_total = int(size_part[:-1]) * 1024 * 1024
                                
        except ProxmoxAPIError:
            # If all methods fail, return zeros
            pass
            
        return {"disk_usage": disk_usage, "disk_total": disk_total}

    def get_all_resources_with_metrics(
        self, node: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all VMs and containers with their current metrics for a node.
        Optimized version that uses basic status info instead of detailed metrics
        to avoid slow RRD and cluster resource calls.

        Args:
            node: Node name

        Returns:
            Dictionary with 'vms' and 'containers' lists containing resource info with metrics
        """
        result = {"vms": [], "containers": []}

        try:
            # Get VMs with basic metrics (no RRD calls)
            vms = self.get_vms(node)
            for vm in vms:
                vmid = vm.get("vmid")
                if vmid:
                    try:
                        # Get basic status without RRD data for speed
                        status = self.get_vm_status(node, vmid)
                        vm_metrics = self._create_basic_vm_metrics(vmid, status, node)
                        result["vms"].append(vm_metrics)
                    except ProxmoxAPIError as e:
                        logger.warning(f"Failed to get VM {vmid} status: {e}")
                        # Add basic info even if status fails
                        result["vms"].append({
                            "vmid": vmid,
                            "name": vm.get("name", f"VM-{vmid}"),
                            "status": "unknown",
                            "error": str(e),
                            "last_updated": datetime.utcnow().isoformat() + "Z"
                        })

            # Get containers with basic metrics (no RRD calls)
            containers = self.get_containers(node)
            for container in containers:
                vmid = container.get("vmid")
                if vmid:
                    try:
                        # Get basic status without RRD data for speed
                        status = self.get_container_status(node, vmid)
                        container_metrics = self._create_basic_container_metrics(vmid, status, node)
                        result["containers"].append(container_metrics)
                    except ProxmoxAPIError as e:
                        logger.warning(f"Failed to get container {vmid} status: {e}")
                        # Add basic info even if status fails
                        result["containers"].append({
                            "vmid": vmid,
                            "name": container.get("name", f"CT-{vmid}"),
                            "status": "unknown",
                            "error": str(e),
                            "last_updated": datetime.utcnow().isoformat() + "Z"
                        })

        except ProxmoxAPIError as e:
            logger.error(f"Failed to get resources for node {node}: {e}")

        return result

    def _calculate_vm_disk_usage(self, status: Dict[str, Any]) -> tuple[int, int]:
        """
        Calculate VM disk usage from blockstat data.
        
        Args:
            status: VM status data from API
            
        Returns:
            Tuple of (disk_usage_bytes, disk_total_bytes)
        """
        disk_usage = 0
        disk_total = status.get("maxdisk", 0)
        
        # Try to get disk usage from blockstat if available
        blockstat = status.get("blockstat", {})
        if blockstat:
            # Look for primary disk (usually scsi0, ide0, virtio0, etc.)
            primary_disks = ["scsi0", "virtio0", "ide0", "sata0"]
            
            for disk_name in primary_disks:
                if disk_name in blockstat:
                    disk_info = blockstat[disk_name]
                    # Use wr_highest_offset as it indicates the highest written offset
                    if "wr_highest_offset" in disk_info and disk_info["wr_highest_offset"] > 0:
                        disk_usage = disk_info["wr_highest_offset"]
                        break
        
        # Fallback to the disk field if blockstat is not available or gives 0
        if disk_usage == 0:
            disk_usage = status.get("disk", 0)
        
        return disk_usage, disk_total

    def _create_basic_vm_metrics(self, vmid: int, status: Dict[str, Any], node: str = None) -> Dict[str, Any]:
        """
        Create basic VM metrics from status data without slow RRD/cluster calls.
        
        Args:
            vmid: VM ID
            status: VM status data from API
            node: Node name (optional, for disk info extraction)
            
        Returns:
            Basic VM metrics dictionary
        """
        # Calculate disk usage using blockstat data
        disk_usage, disk_total = self._calculate_vm_disk_usage(status)
        
        return {
            "vmid": vmid,
            "name": status.get("name", f"VM-{vmid}"),
            "status": status.get("status", "unknown"),
            "uptime": status.get("uptime", 0),
            "cpu_usage": status.get("cpu", 0) * 100,  # Convert from 0-1 to 0-100 percentage
            "memory_usage": status.get("mem", 0),
            "memory_total": status.get("maxmem", 0),
            "memory_percentage": (
                (status.get("mem", 0) / status.get("maxmem", 1)) * 100
                if status.get("maxmem")
                else 0
            ),
            "disk_usage": disk_usage,
            "disk_total": disk_total,
            "disk_percentage": (
                (disk_usage / disk_total * 100)
                if disk_total > 0
                else 0
            ),
            "network_in": status.get("netin", 0),
            "network_out": status.get("netout", 0),
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

    def _create_basic_container_metrics(self, vmid: int, status: Dict[str, Any], node: str = None) -> Dict[str, Any]:
        """
        Create basic container metrics from status data without slow RRD/cluster calls.
        
        Args:
            vmid: Container ID
            status: Container status data from API
            node: Node name (optional, for disk info extraction)
            
        Returns:
            Basic container metrics dictionary
        """
        return {
            "vmid": vmid,
            "name": status.get("name", f"CT-{vmid}"),
            "status": status.get("status", "unknown"),
            "uptime": status.get("uptime", 0),
            "cpu_usage": status.get("cpu", 0) * 100,  # Convert from 0-1 to 0-100 percentage
            "memory_usage": status.get("mem", 0),
            "memory_total": status.get("maxmem", 0),
            "memory_percentage": (
                (status.get("mem", 0) / status.get("maxmem", 1)) * 100
                if status.get("maxmem")
                else 0
            ),
            "disk_usage": status.get("disk", 0),
            "disk_total": status.get("maxdisk", 0),
            "disk_percentage": (
                (status.get("disk", 0) / status.get("maxdisk", 1)) * 100
                if status.get("maxdisk")
                else 0
            ),
            "network_in": status.get("netin", 0),
            "network_out": status.get("netout", 0),
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

    def close(self):
        """Close the HTTP session."""
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_client_from_config(node_config: Dict[str, Any]) -> ProxmoxAPIClient:
    """
    Create a ProxmoxAPIClient instance from a node configuration dictionary.

    Args:
        node_config: Node configuration dictionary

    Returns:
        Configured ProxmoxAPIClient instance

    Raises:
        ValueError: If required configuration is missing
    """
    required_fields = ["host"]
    for field in required_fields:
        if field not in node_config:
            raise ValueError(f"Missing required configuration field: {field}")

    return ProxmoxAPIClient(
        host=node_config["host"],
        port=node_config.get("port", 8006),
        api_token_id=node_config.get("api_token_id"),
        api_token_secret=node_config.get("api_token_secret"),
        ssl_verify=node_config.get("ssl_verify", False),
        timeout=node_config.get("timeout", 30),
    )
