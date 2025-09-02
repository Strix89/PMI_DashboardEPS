"""
Acronis Data Models for PMI Dashboard

This module defines data models for Acronis entities including agents, workloads,
backups, and statistics used throughout the PMI Dashboard Acronis integration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class AcronisAgent:
    """Data model for Acronis agent information."""

    id_agent: str
    hostname: str
    id_tenant: str
    online: bool
    uptime: str
    uptime_timestamp: float
    platform: Dict[str, str] = field(default_factory=dict)

    def get_status_display(self) -> str:
        """Get human-readable status."""
        return "Online" if self.online else "Offline"

    def get_platform_display(self) -> str:
        """Get formatted platform information."""
        if not self.platform:
            return "Unknown"

        family = self.platform.get("family", "")
        name = self.platform.get("name", "")
        arch = self.platform.get("arch", "")

        parts = [part for part in [family, name, arch] if part]
        return " ".join(parts) if parts else "Unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id_agent": self.id_agent,
            "hostname": self.hostname,
            "id_tenant": self.id_tenant,
            "online": self.online,
            "uptime": self.uptime,
            "uptime_timestamp": self.uptime_timestamp,
            "platform": self.platform,
            "status_display": self.get_status_display(),
            "platform_display": self.get_platform_display(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcronisAgent":
        """Create instance from dictionary."""
        return cls(
            id_agent=data.get("id_agent", ""),
            hostname=data.get("hostname", ""),
            id_tenant=data.get("id_tenant", ""),
            online=data.get("online", False),
            uptime=data.get("uptime", ""),
            uptime_timestamp=data.get("uptime_timestamp", 0.0),
            platform=data.get("platform", {}),
        )


@dataclass
class AcronisWorkload:
    """Data model for Acronis workload information."""

    id_workload: str
    hostname: str
    id_tenant: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id_workload": self.id_workload,
            "hostname": self.hostname,
            "id_tenant": self.id_tenant,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcronisWorkload":
        """Create instance from dictionary."""
        return cls(
            id_workload=data.get("id_workload", ""),
            hostname=data.get("hostname", ""),
            id_tenant=data.get("id_tenant", ""),
        )


@dataclass
class AcronisBackup:
    """Data model for Acronis backup information."""

    started_at: str
    completed_at: str
    state: str
    run_mode: str
    bytes_saved: int
    result: str
    activities: Optional[List[Dict]] = None

    def get_duration(self) -> str:
        """Calculate and format backup duration."""
        try:
            if not self.started_at or not self.completed_at:
                return "Unknown"

            # Parse timestamps
            start_dt = None
            end_dt = None

            for fmt in ["%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    start_dt = datetime.strptime(self.started_at, fmt)
                    end_dt = datetime.strptime(self.completed_at, fmt)
                    break
                except ValueError:
                    continue

            if not start_dt or not end_dt:
                return "Unknown"

            duration = end_dt - start_dt
            total_seconds = int(duration.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds} seconds"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                if minutes > 0:
                    return f"{hours}h {minutes}m"
                else:
                    return f"{hours} hour{'s' if hours != 1 else ''}"

        except Exception as e:
            logger.warning(f"Failed to calculate backup duration: {e}")
            return "Unknown"

    def get_bytes_saved_display(self) -> str:
        """Get formatted bytes saved."""
        return format_bytes(self.bytes_saved)

    def get_result_display(self) -> str:
        """Get human-readable result status."""
        result_map = {
            "ok": "Success",
            "success": "Success",
            "completed": "Success",
            "failed": "Failed",
            "error": "Error",
            "cancelled": "Cancelled",
            "running": "Running",
            "pending": "Pending",
        }
        return result_map.get(self.result.lower(), self.result.title())

    def is_successful(self) -> bool:
        """Check if backup was successful."""
        return self.result.lower() in ["ok", "success", "completed"]

    def get_activity_count(self) -> int:
        """Get number of activities."""
        return len(self.activities) if self.activities else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "state": self.state,
            "run_mode": self.run_mode,
            "bytes_saved": self.bytes_saved,
            "result": self.result,
            "activities": self.activities or [],
            "duration": self.get_duration(),
            "bytes_saved_display": self.get_bytes_saved_display(),
            "result_display": self.get_result_display(),
            "is_successful": self.is_successful(),
            "activity_count": self.get_activity_count(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcronisBackup":
        """Create instance from dictionary."""
        return cls(
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            state=data.get("state", ""),
            run_mode=data.get("run_mode", ""),
            bytes_saved=data.get("bytes_saved", 0),
            result=data.get("result", ""),
            activities=data.get("activities"),
        )


@dataclass
class BackupStatistics:
    """Data model for aggregated backup statistics."""

    total_backups: int
    success: int
    failed: int
    total_activities: int = 0

    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_backups == 0:
            return 0.0
        return (self.success / self.total_backups) * 100

    def get_failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        if self.total_backups == 0:
            return 0.0
        return (self.failed / self.total_backups) * 100

    def get_other_count(self) -> int:
        """Get count of backups that are neither success nor failed."""
        return max(0, self.total_backups - self.success - self.failed)

    def get_other_rate(self) -> float:
        """Calculate rate of other backups as percentage."""
        if self.total_backups == 0:
            return 0.0
        return (self.get_other_count() / self.total_backups) * 100

    def has_backups(self) -> bool:
        """Check if there are any backups."""
        return self.total_backups > 0

    def get_status_summary(self) -> str:
        """Get human-readable status summary."""
        if self.total_backups == 0:
            return "No backups"

        if self.failed == 0:
            return f"All {self.total_backups} backups successful"
        elif self.success == 0:
            return f"All {self.total_backups} backups failed"
        else:
            return f"{self.success} successful, {self.failed} failed out of {self.total_backups}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_backups": self.total_backups,
            "success": self.success,
            "failed": self.failed,
            "other": self.get_other_count(),
            "total_activities": self.total_activities,
            "success_rate": round(self.get_success_rate(), 1),
            "failure_rate": round(self.get_failure_rate(), 1),
            "other_rate": round(self.get_other_rate(), 1),
            "has_backups": self.has_backups(),
            "status_summary": self.get_status_summary(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupStatistics":
        """Create instance from dictionary."""
        return cls(
            total_backups=data.get("total_backups", 0),
            success=data.get("success", 0),
            failed=data.get("failed", 0),
            total_activities=data.get("total_activities", 0),
        )


# Utility Functions for Data Formatting and Validation


def format_timestamp(
    timestamp: Union[str, int, float], format_type: str = "display"
) -> str:
    """
    Format timestamp for display or API usage.

    Args:
        timestamp: Timestamp in various formats (ISO string, Unix timestamp, etc.)
        format_type: Type of formatting ("display", "api", "short")

    Returns:
        Formatted timestamp string
    """
    try:
        # Handle different timestamp formats
        if isinstance(timestamp, str):
            # Try to parse ISO format first
            if "T" in timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                # Try common date formats
                for fmt in [
                    "%d/%m/%Y %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                ]:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return timestamp  # Return original if can't parse
        elif isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            return str(timestamp)

        # Format based on type
        if format_type == "display":
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        elif format_type == "api":
            return dt.isoformat()
        elif format_type == "short":
            return dt.strftime("%d/%m %H:%M")
        else:
            return dt.strftime("%d/%m/%Y %H:%M:%S")

    except Exception as e:
        logger.warning(f"Failed to format timestamp {timestamp}: {e}")
        return str(timestamp)


def format_bytes(bytes_value: Union[int, str]) -> str:
    """
    Format bytes value to human-readable format.

    Args:
        bytes_value: Number of bytes

    Returns:
        Human-readable string (e.g., "1.5 GB")
    """
    try:
        if isinstance(bytes_value, str):
            bytes_value = int(bytes_value)

        if bytes_value == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        unit_index = 0
        size = float(bytes_value)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to format bytes {bytes_value}: {e}")
        return str(bytes_value)


def format_uptime(uptime_seconds: Union[int, float, str]) -> str:
    """
    Format uptime seconds to human-readable format.

    Args:
        uptime_seconds: Uptime in seconds

    Returns:
        Human-readable uptime string (e.g., "5 days, 3 hours, 20 minutes")
    """
    try:
        if isinstance(uptime_seconds, str):
            uptime_seconds = float(uptime_seconds)

        seconds = int(uptime_seconds)

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        if not parts:
            return "Less than a minute"

        return ", ".join(parts)

    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to format uptime {uptime_seconds}: {e}")
        return str(uptime_seconds)


def validate_agent_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate agent data structure and required fields.

    Args:
        data: Agent data dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    required_fields = ["id_agent", "hostname", "id_tenant", "online"]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Field {field} cannot be None")

    # Validate specific field types
    if "online" in data and not isinstance(data["online"], bool):
        errors.append("Field 'online' must be boolean")

    if "uptime_timestamp" in data and data["uptime_timestamp"] is not None:
        try:
            float(data["uptime_timestamp"])
        except (ValueError, TypeError):
            errors.append("Field 'uptime_timestamp' must be numeric")

    return errors


def validate_backup_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate backup data structure and required fields.

    Args:
        data: Backup data dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    required_fields = ["started_at", "state", "result"]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Field {field} cannot be None")

    # Validate bytes_saved if present
    if "bytes_saved" in data and data["bytes_saved"] is not None:
        try:
            int(data["bytes_saved"])
        except (ValueError, TypeError):
            errors.append("Field 'bytes_saved' must be numeric")

    return errors


def transform_agent_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw agent data from API to standardized format.

    Args:
        raw_data: Raw agent data from Acronis API

    Returns:
        Transformed agent data
    """
    try:
        transformed = {
            "id_agent": raw_data.get("id", ""),
            "hostname": raw_data.get("hostname", "Unknown"),
            "id_tenant": raw_data.get("tenant_id", ""),
            "online": raw_data.get("online", False),
            "uptime": "",
            "uptime_timestamp": 0.0,
            "platform": raw_data.get("platform", {}),
        }

        # Handle uptime formatting
        if "uptime" in raw_data and raw_data["uptime"] is not None:
            if isinstance(raw_data["uptime"], (int, float)):
                transformed["uptime_timestamp"] = float(raw_data["uptime"])
                transformed["uptime"] = format_uptime(raw_data["uptime"])
            else:
                transformed["uptime"] = str(raw_data["uptime"])

        return transformed

    except Exception as e:
        logger.error(f"Failed to transform agent data: {e}")
        return raw_data


def transform_backup_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw backup data from API to standardized format.

    Args:
        raw_data: Raw backup data from Acronis API

    Returns:
        Transformed backup data
    """
    try:
        # Transform activities to expected format
        activities = []
        raw_activities = raw_data.get("activities", [])
        
        if isinstance(raw_activities, list):
            for activity in raw_activities:
                if isinstance(activity, dict):
                    transformed_activity = {
                        "name": activity.get("name") or activity.get("type") or activity.get("operation") or "Unknown Activity",
                        "status": activity.get("status") or activity.get("state") or activity.get("result") or "unknown",
                        "time": format_timestamp(activity.get("started_at") or activity.get("timestamp") or activity.get("time") or "")
                    }
                    activities.append(transformed_activity)
        
        transformed = {
            "started_at": format_timestamp(raw_data.get("started_at", "")),
            "completed_at": format_timestamp(raw_data.get("completed_at", "")),
            "state": raw_data.get("state", "unknown"),
            "run_mode": raw_data.get("run_mode", "Unknown"),
            "bytes_saved": int(raw_data.get("bytes_saved", 0)),
            "result": raw_data.get("result", "unknown"),
            "activities": activities,
        }

        return transformed

    except Exception as e:
        logger.error(f"Failed to transform backup data: {e}")
        return raw_data


def create_backup_statistics(backup_data: List[Dict[str, Any]]) -> BackupStatistics:
    """
    Create backup statistics from a list of backup data.

    Args:
        backup_data: List of backup dictionaries

    Returns:
        BackupStatistics object with aggregated data
    """
    total_backups = len(backup_data)
    success = 0
    failed = 0
    total_activities = 0

    for backup in backup_data:
        result = backup.get("result", "").lower()
        if result in ["ok", "success", "completed"]:
            success += 1
        elif result in ["failed", "error", "cancelled"]:
            failed += 1

        activities = backup.get("activities", [])
        if isinstance(activities, list):
            total_activities += len(activities)

    return BackupStatistics(
        total_backups=total_backups,
        success=success,
        failed=failed,
        total_activities=total_activities,
    )
