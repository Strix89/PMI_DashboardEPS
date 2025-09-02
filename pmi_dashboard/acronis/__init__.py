"""
Acronis module for PMI Dashboard

This module provides comprehensive Acronis Cyber Protect Cloud integration including:
- API client for communication with Acronis Cloud servers
- Data models for agents, workloads, and backup operations
- Configuration management and validation
"""

from .api_client import (
    AcronisAPIClient,
    AcronisAPIError,
    AcronisAuthenticationError,
    AcronisConnectionError
)

from .models import (
    AcronisAgent,
    AcronisWorkload,
    AcronisBackup,
    BackupStatistics
)

from .config_manager import (
    AcronisConfigManager,
    AcronisConfigurationError
)

from .routes import acronis_bp

__all__ = [
    # API Client
    'AcronisAPIClient',
    'AcronisAPIError',
    'AcronisAuthenticationError',
    'AcronisConnectionError',
    
    # Models
    'AcronisAgent',
    'AcronisWorkload',
    'AcronisBackup',
    'BackupStatistics',
    
    # Configuration Management
    'AcronisConfigManager',
    'AcronisConfigurationError',
    
    # Flask Blueprint
    'acronis_bp'
]