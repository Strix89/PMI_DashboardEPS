"""
Proxmox module for PMI Dashboard

This module provides comprehensive Proxmox VE integration including:
- API client for communication with Proxmox servers
- Data models for nodes, VMs, containers, and operations
- Configuration management and validation
"""

from .api_client import (
    ProxmoxAPIClient,
    ProxmoxAPIError,
    ProxmoxAuthenticationError,
    ProxmoxConnectionError,
    create_client_from_config
)

from .models import (
    ProxmoxNode,
    ProxmoxResource,
    OperationHistory,
    ResourceType,
    ResourceStatus,
    OperationType,
    OperationStatus,
    format_bytes,
    format_uptime,
    validate_vmid
)

from .history import (
    OperationHistoryManager,
    get_history_manager,
    create_operation
)

__all__ = [
    # API Client
    'ProxmoxAPIClient',
    'ProxmoxAPIError',
    'ProxmoxAuthenticationError',
    'ProxmoxConnectionError',
    'create_client_from_config',
    
    # Models
    'ProxmoxNode',
    'ProxmoxResource',
    'OperationHistory',
    'ResourceType',
    'ResourceStatus',
    'OperationType',
    'OperationStatus',
    
    # History Management
    'OperationHistoryManager',
    'get_history_manager',
    'create_operation',
    
    # Utilities
    'format_bytes',
    'format_uptime',
    'validate_vmid'
]