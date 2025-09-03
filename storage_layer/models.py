"""
Data models for Infrastructure Monitoring Storage Layer

This module defines the core data structures used throughout the storage system,
including MetricDocument for time-series data and AssetDocument for infrastructure assets.
"""

from typing import Dict, List, Optional, Union, Literal, Any
from datetime import datetime, UTC
from dataclasses import dataclass, field
import re


# Type definitions for asset types and service status
AssetType = Literal["proxmox_node", "vm", "container", "physical_host", "acronis_backup_job", "service"]
ServiceStatus = Literal["running", "stopped", "degraded", "unknown"]


@dataclass
class MetricDocument:
    """
    Represents a time-series metric data point.
    
    This class encapsulates performance metrics with timestamp, asset identification,
    metric name, and value. Designed for efficient storage in MongoDB time-series collections.
    
    Attributes:
        timestamp: When the metric was recorded
        asset_id: Unique identifier of the asset being monitored
        metric_name: Name of the metric (e.g., 'cpu_usage', 'memory_usage')
        value: Numeric value of the metric
    """
    timestamp: datetime
    asset_id: str
    metric_name: str
    value: float
    
    def __post_init__(self) -> None:
        """Validate the metric document after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate the metric document fields.
        
        Raises:
            ValueError: If any field is invalid
        """
        if not self.asset_id or not isinstance(self.asset_id, str):
            raise ValueError("asset_id must be a non-empty string")
        
        if not self.metric_name or not isinstance(self.metric_name, str):
            raise ValueError("metric_name must be a non-empty string")
        
        if not isinstance(self.value, (int, float)):
            raise ValueError("value must be a numeric type")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        
        # Validate metric name format (alphanumeric with underscores)
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', self.metric_name):
            raise ValueError("metric_name must start with a letter and contain only alphanumeric characters and underscores")
    
    def to_mongo_dict(self) -> Dict[str, Any]:
        """
        Convert the metric document to MongoDB time-series format.
        
        Returns:
            Dictionary formatted for MongoDB time-series collection insertion
        """
        return {
            "timestamp": self.timestamp,
            "meta": {
                "asset_id": self.asset_id,
                "metric_name": self.metric_name
            },
            "value": float(self.value)
        }


@dataclass  
class AssetDocument:
    """
    Represents an infrastructure asset (machine, service, etc.).
    
    This class encapsulates all types of infrastructure assets including physical hosts,
    virtual machines, containers, services, and backup jobs. Supports hierarchical
    relationships through parent_asset_id for services.
    
    Attributes:
        asset_id: Unique identifier for the asset
        asset_type: Type of asset from AssetType literal
        hostname: Optional hostname for machine-type assets
        service_name: Optional service name for service-type assets
        data: Flexible dictionary for asset-specific metadata
        last_updated: Timestamp of last update (auto-set if None)
    """
    asset_id: str
    asset_type: AssetType
    data: Dict[str, Any]
    hostname: Optional[str] = None
    service_name: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate the asset document after initialization."""
        if self.last_updated is None:
            self.last_updated = datetime.now(UTC)
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate the asset document fields.
        
        Raises:
            ValueError: If any field is invalid
        """
        if not self.asset_id or not isinstance(self.asset_id, str):
            raise ValueError("asset_id must be a non-empty string")
        
        if not isinstance(self.data, dict):
            raise ValueError("data must be a dictionary")
        
        # Validate asset_id format (alphanumeric with hyphens and underscores)
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', self.asset_id):
            raise ValueError("asset_id must start with alphanumeric character and contain only alphanumeric, hyphens, and underscores")
        
        # Service-specific validations
        if self.asset_type == "service":
            if not self.service_name:
                raise ValueError("service_name is required for service type assets")
            
            if "parent_asset_id" not in self.data:
                raise ValueError("parent_asset_id is required in data for service type assets")
            
            parent_id = self.data.get("parent_asset_id")
            if not parent_id or not isinstance(parent_id, str):
                raise ValueError("parent_asset_id must be a non-empty string for service assets")
        
        # Hostname validation for machine-type assets
        machine_types = ["proxmox_node", "vm", "container", "physical_host"]
        if self.asset_type in machine_types and self.hostname:
            if not isinstance(self.hostname, str) or not self.hostname.strip():
                raise ValueError("hostname must be a non-empty string for machine-type assets")
    
    def to_mongo_dict(self) -> Dict[str, Any]:
        """
        Convert the asset document to MongoDB format.
        
        Returns:
            Dictionary formatted for MongoDB collection insertion
        """
        doc = {
            "_id": self.asset_id,
            "asset_type": self.asset_type,
            "last_updated": self.last_updated,
            "data": self.data.copy()
        }
        
        if self.hostname:
            doc["hostname"] = self.hostname
        
        if self.service_name:
            doc["service_name"] = self.service_name
        
        return doc
    
    def validate_service_status(self) -> bool:
        """
        Validate that service status is one of the allowed values.
        
        Returns:
            True if status is valid or not present, False otherwise
        """
        if "status" in self.data:
            status = self.data["status"]
            valid_statuses = ["running", "stopped", "degraded", "unknown"]
            return status in valid_statuses
        return True
    
    def is_service(self) -> bool:
        """Check if this asset is a service type."""
        return self.asset_type == "service"
    
    def get_parent_asset_id(self) -> Optional[str]:
        """Get the parent asset ID for service-type assets."""
        if self.is_service():
            return self.data.get("parent_asset_id")
        return None


def create_metric_document(timestamp: datetime, asset_id: str, 
                          metric_name: str, value: float) -> MetricDocument:
    """
    Factory function to create a validated MetricDocument.
    
    Args:
        timestamp: When the metric was recorded
        asset_id: Unique identifier of the asset
        metric_name: Name of the metric
        value: Numeric value of the metric
    
    Returns:
        Validated MetricDocument instance
    
    Raises:
        ValueError: If any parameter is invalid
    """
    return MetricDocument(
        timestamp=timestamp,
        asset_id=asset_id,
        metric_name=metric_name,
        value=value
    )


def create_asset_document(asset_id: str, asset_type: AssetType, 
                         data: Dict[str, Any], hostname: Optional[str] = None,
                         service_name: Optional[str] = None) -> AssetDocument:
    """
    Factory function to create a validated AssetDocument.
    
    Args:
        asset_id: Unique identifier for the asset
        asset_type: Type of asset
        data: Asset-specific metadata
        hostname: Optional hostname for machine-type assets
        service_name: Optional service name for service-type assets
    
    Returns:
        Validated AssetDocument instance
    
    Raises:
        ValueError: If any parameter is invalid
    """
    return AssetDocument(
        asset_id=asset_id,
        asset_type=asset_type,
        data=data,
        hostname=hostname,
        service_name=service_name
    )