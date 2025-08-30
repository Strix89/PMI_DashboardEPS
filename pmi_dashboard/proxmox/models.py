"""
Data models for Proxmox resources and operations.

This module defines data classes and models for representing Proxmox nodes,
VMs, LXC containers, and operation history.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json


class ResourceType(Enum):
    """Enumeration for resource types."""
    NODE = "node"
    VM = "vm"
    LXC = "lxc"
    QEMU = "qemu"


class ResourceStatus(Enum):
    """Enumeration for resource status."""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class OperationType(Enum):
    """Enumeration for operation types."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"
    SUSPEND = "suspend"
    RESUME = "resume"
    BACKUP = "backup"
    RESTORE = "restore"
    MIGRATE = "migrate"
    CLONE = "clone"
    DELETE = "delete"


class OperationStatus(Enum):
    """Enumeration for operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class ProxmoxNode:
    """
    Data model for a Proxmox node configuration and status.
    """
    id: str
    name: str
    host: str
    port: int = 8006
    api_token_id: Optional[str] = None
    api_token_secret: Optional[str] = None
    ssl_verify: bool = False
    enabled: bool = True
    timeout: int = 30
    
    # Status information
    status: str = "unknown"
    version: Optional[str] = None
    uptime: int = 0
    cpu_usage: float = 0.0
    cpu_count: int = 0
    memory_usage: int = 0
    memory_total: int = 0
    memory_percentage: float = 0.0
    disk_usage: int = 0
    disk_total: int = 0
    disk_percentage: float = 0.0
    load_average: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    
    # Timestamps
    created_at: Optional[str] = None
    last_connected: Optional[str] = None
    last_updated: Optional[str] = None
    
    # Connection info
    connection_error: Optional[str] = None
    is_connected: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'api_token_id': self.api_token_id,
            'api_token_secret': self.api_token_secret,
            'ssl_verify': self.ssl_verify,
            'enabled': self.enabled,
            'timeout': self.timeout,
            'status': self.status,
            'version': self.version,
            'uptime': self.uptime,
            'cpu_usage': self.cpu_usage,
            'cpu_count': self.cpu_count,
            'memory_usage': self.memory_usage,
            'memory_total': self.memory_total,
            'memory_percentage': self.memory_percentage,
            'disk_usage': self.disk_usage,
            'disk_total': self.disk_total,
            'disk_percentage': self.disk_percentage,
            'load_average': self.load_average,
            'created_at': self.created_at,
            'last_connected': self.last_connected,
            'last_updated': self.last_updated,
            'connection_error': self.connection_error,
            'is_connected': self.is_connected
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxmoxNode':
        """Create node from dictionary representation."""
        return cls(
            id=data['id'],
            name=data['name'],
            host=data['host'],
            port=data.get('port', 8006),
            api_token_id=data.get('api_token_id'),
            api_token_secret=data.get('api_token_secret'),
            ssl_verify=data.get('ssl_verify', False),
            enabled=data.get('enabled', True),
            timeout=data.get('timeout', 30),
            status=data.get('status', 'unknown'),
            version=data.get('version'),
            uptime=data.get('uptime', 0),
            cpu_usage=data.get('cpu_usage', 0.0),
            cpu_count=data.get('cpu_count', 0),
            memory_usage=data.get('memory_usage', 0),
            memory_total=data.get('memory_total', 0),
            memory_percentage=data.get('memory_percentage', 0.0),
            disk_usage=data.get('disk_usage', 0),
            disk_total=data.get('disk_total', 0),
            disk_percentage=data.get('disk_percentage', 0.0),
            load_average=data.get('load_average', [0.0, 0.0, 0.0]),
            created_at=data.get('created_at'),
            last_connected=data.get('last_connected'),
            last_updated=data.get('last_updated'),
            connection_error=data.get('connection_error'),
            is_connected=data.get('is_connected', False)
        )
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get configuration dictionary for API client."""
        return {
            'host': self.host,
            'port': self.port,
            'api_token_id': self.api_token_id,
            'api_token_secret': self.api_token_secret,
            'ssl_verify': self.ssl_verify,
            'timeout': self.timeout
        }


@dataclass
class ProxmoxResource:
    """
    Data model for a Proxmox VM or LXC container.
    """
    vmid: int
    name: str
    node: str
    resource_type: ResourceType
    status: ResourceStatus = ResourceStatus.UNKNOWN
    
    # Resource specifications
    cpu_cores: int = 0
    memory_total: int = 0
    disk_total: int = 0
    
    # Current metrics
    cpu_usage: float = 0.0
    memory_usage: int = 0
    memory_percentage: float = 0.0
    disk_usage: int = 0
    disk_percentage: float = 0.0
    network_in: int = 0
    network_out: int = 0
    uptime: int = 0
    
    # Additional information
    template: bool = False
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    
    # Timestamps
    last_updated: Optional[str] = None
    
    # Error information
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary representation."""
        return {
            'vmid': self.vmid,
            'name': self.name,
            'node': self.node,
            'resource_type': self.resource_type.value,
            'status': self.status.value,
            'cpu_cores': self.cpu_cores,
            'memory_total': self.memory_total,
            'disk_total': self.disk_total,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'memory_percentage': self.memory_percentage,
            'disk_usage': self.disk_usage,
            'disk_percentage': self.disk_percentage,
            'network_in': self.network_in,
            'network_out': self.network_out,
            'uptime': self.uptime,
            'template': self.template,
            'tags': self.tags,
            'description': self.description,
            'last_updated': self.last_updated,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxmoxResource':
        """Create resource from dictionary representation."""
        return cls(
            vmid=data['vmid'],
            name=data['name'],
            node=data['node'],
            resource_type=ResourceType(data.get('resource_type', 'vm')),
            status=ResourceStatus(data.get('status', 'unknown')),
            cpu_cores=data.get('cpu_cores', 0),
            memory_total=data.get('memory_total', 0),
            disk_total=data.get('disk_total', 0),
            cpu_usage=data.get('cpu_usage', 0.0),
            memory_usage=data.get('memory_usage', 0),
            memory_percentage=data.get('memory_percentage', 0.0),
            disk_usage=data.get('disk_usage', 0),
            disk_percentage=data.get('disk_percentage', 0.0),
            network_in=data.get('network_in', 0),
            network_out=data.get('network_out', 0),
            uptime=data.get('uptime', 0),
            template=data.get('template', False),
            tags=data.get('tags', []),
            description=data.get('description'),
            last_updated=data.get('last_updated'),
            error=data.get('error')
        )
    
    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any], node: str, 
                         resource_type: ResourceType) -> 'ProxmoxResource':
        """
        Create resource from Proxmox API response data.
        
        Args:
            api_data: Raw API response data
            node: Node name
            resource_type: Type of resource (VM or LXC)
            
        Returns:
            ProxmoxResource instance
        """
        # Map API status to our enum
        api_status = api_data.get('status', 'unknown')
        try:
            status = ResourceStatus(api_status)
        except ValueError:
            status = ResourceStatus.UNKNOWN
        
        # Extract metrics with safe defaults
        cpu_usage = api_data.get('cpu', 0) * 100 if api_data.get('cpu') else 0
        memory_usage = api_data.get('mem', 0)
        memory_total = api_data.get('maxmem', 0)
        memory_percentage = (memory_usage / memory_total * 100) if memory_total > 0 else 0
        
        disk_usage = api_data.get('disk', 0)
        disk_total = api_data.get('maxdisk', 0)
        disk_percentage = (disk_usage / disk_total * 100) if disk_total > 0 else 0
        
        return cls(
            vmid=api_data.get('vmid', 0),
            name=api_data.get('name', f'{resource_type.value.upper()}-{api_data.get("vmid", 0)}'),
            node=node,
            resource_type=resource_type,
            status=status,
            cpu_cores=api_data.get('cpus', 0),
            memory_total=memory_total,
            disk_total=disk_total,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            memory_percentage=memory_percentage,
            disk_usage=disk_usage,
            disk_percentage=disk_percentage,
            network_in=api_data.get('netin', 0),
            network_out=api_data.get('netout', 0),
            uptime=api_data.get('uptime', 0),
            template=api_data.get('template', 0) == 1,
            tags=api_data.get('tags', '').split(',') if api_data.get('tags') else [],
            last_updated=datetime.utcnow().isoformat() + 'Z'
        )
    
    def is_running(self) -> bool:
        """Check if resource is currently running."""
        return self.status == ResourceStatus.RUNNING
    
    def is_stopped(self) -> bool:
        """Check if resource is currently stopped."""
        return self.status == ResourceStatus.STOPPED
    
    def get_display_name(self) -> str:
        """Get display name for the resource."""
        prefix = "VM" if self.resource_type == ResourceType.VM else "CT"
        return f"{prefix}-{self.vmid}: {self.name}"


@dataclass
class OperationHistory:
    """
    Data model for tracking operations performed on Proxmox resources.
    """
    id: str
    timestamp: str
    node: str
    resource_type: ResourceType
    resource_id: Optional[int]  # None for node operations
    resource_name: Optional[str]
    operation: OperationType
    status: OperationStatus
    user: Optional[str] = None
    error_message: Optional[str] = None
    duration: Optional[float] = None  # Duration in seconds
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary representation."""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'node': self.node,
            'resource_type': self.resource_type.value,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'operation': self.operation.value,
            'status': self.status.value,
            'user': self.user,
            'error_message': self.error_message,
            'duration': self.duration,
            'details': self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationHistory':
        """Create operation from dictionary representation."""
        return cls(
            id=data['id'],
            timestamp=data['timestamp'],
            node=data['node'],
            resource_type=ResourceType(data['resource_type']),
            resource_id=data.get('resource_id'),
            resource_name=data.get('resource_name'),
            operation=OperationType(data['operation']),
            status=OperationStatus(data['status']),
            user=data.get('user'),
            error_message=data.get('error_message'),
            duration=data.get('duration'),
            details=data.get('details', {})
        )
    
    def get_display_text(self) -> str:
        """Get human-readable display text for the operation."""
        resource_text = f"{self.resource_type.value.upper()}-{self.resource_id}" if self.resource_id else self.node
        if self.resource_name:
            resource_text += f" ({self.resource_name})"
        
        operation_text = self.operation.value.replace('_', ' ').title()
        
        return f"{operation_text} {resource_text}"
    
    def is_completed(self) -> bool:
        """Check if operation is completed (success or failed)."""
        return self.status in [OperationStatus.SUCCESS, OperationStatus.FAILED]
    
    def is_successful(self) -> bool:
        """Check if operation completed successfully."""
        return self.status == OperationStatus.SUCCESS
    
    def is_failed(self) -> bool:
        """Check if operation failed."""
        return self.status == OperationStatus.FAILED
    
    def is_in_progress(self) -> bool:
        """Check if operation is currently in progress."""
        return self.status == OperationStatus.IN_PROGRESS


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes value to human-readable string.
    
    Args:
        bytes_value: Value in bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    if bytes_value == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    value = float(bytes_value)
    
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    else:
        return f"{value:.1f} {units[unit_index]}"


def format_uptime(seconds: int) -> str:
    """
    Format uptime seconds to human-readable string.
    
    Args:
        seconds: Uptime in seconds
        
    Returns:
        Formatted string (e.g., "2d 3h 45m")
    """
    if seconds == 0:
        return "0s"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else f"{seconds}s"


def validate_vmid(vmid: Union[int, str]) -> int:
    """
    Validate and convert VMID to integer.
    
    Args:
        vmid: VMID value to validate
        
    Returns:
        Valid VMID as integer
        
    Raises:
        ValueError: If VMID is invalid
    """
    try:
        vmid_int = int(vmid)
        if vmid_int < 100 or vmid_int > 999999999:
            raise ValueError(f"VMID must be between 100 and 999999999: {vmid_int}")
        return vmid_int
    except (ValueError, TypeError):
        raise ValueError(f"Invalid VMID format: {vmid}")