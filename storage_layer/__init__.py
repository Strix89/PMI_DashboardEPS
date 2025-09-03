"""
Infrastructure Monitoring Storage Layer

A MongoDB-based storage solution for infrastructure monitoring data including
time-series metrics, asset management, and service monitoring.
"""

__version__ = "1.0.0"
__author__ = "Infrastructure Monitoring Team"

# Import main classes for easy access
from .storage_manager import StorageManager
from .models import MetricDocument, AssetDocument, AssetType, ServiceStatus
from .exceptions import StorageManagerError, ConnectionError, ValidationError, OperationError
from .logging_config import setup_logging, get_logger

__all__ = [
    "StorageManager",
    "MetricDocument", 
    "AssetDocument",
    "AssetType",
    "ServiceStatus",
    "StorageManagerError",
    "ConnectionError", 
    "ValidationError",
    "OperationError",
    "setup_logging",
    "get_logger"
]