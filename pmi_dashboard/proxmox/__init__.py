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
    ResourceType,
    ResourceStatus,
    format_bytes,
    format_uptime,
    validate_vmid
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
    'ResourceType',
    'ResourceStatus',
    
    # Utilities
    'format_bytes',
    'format_uptime',
    'validate_vmid'
]