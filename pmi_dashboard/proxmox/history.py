"""
Operation history management for Proxmox operations.

This module provides functionality to store and retrieve operation history
using a file-based storage system.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from .models import OperationHistory, ResourceType, OperationType, OperationStatus
from config import Config


class OperationHistoryManager:
    """Manager for storing and retrieving operation history."""
    
    def __init__(self, history_file_path: Optional[str] = None):
        """
        Initialize the operation history manager.
        
        Args:
            history_file_path: Path to the history file. If None, uses default path.
        """
        if history_file_path is None:
            history_file_path = os.path.join(Config.DATA_DIR, 'operation_history.json')
        
        self.history_file_path = history_file_path
        self._ensure_history_file_exists()
    
    def _ensure_history_file_exists(self):
        """Ensure the history file exists with proper structure."""
        if not os.path.exists(self.history_file_path) or os.path.getsize(self.history_file_path) == 0:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.history_file_path), exist_ok=True)
            
            # Create empty history file
            default_history = {
                "operations": [],
                "metadata": {
                    "version": "1.0",
                    "created_at": datetime.utcnow().isoformat() + 'Z',
                    "last_modified": None
                }
            }
            self._save_history(default_history)
    
    def _load_history(self) -> Dict[str, Any]:
        """Load operation history from JSON file."""
        try:
            with open(self.history_file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # Validate basic structure
            if not isinstance(history, dict):
                history = {"operations": [], "metadata": {}}
            
            if "operations" not in history:
                history["operations"] = []
            
            if "metadata" not in history:
                history["metadata"] = {
                    "version": "1.0",
                    "created_at": datetime.utcnow().isoformat() + 'Z',
                    "last_modified": None
                }
            
            return history
            
        except (json.JSONDecodeError, IOError):
            # If file is corrupted or missing, create new one
            return {
                "operations": [],
                "metadata": {
                    "version": "1.0",
                    "created_at": datetime.utcnow().isoformat() + 'Z',
                    "last_modified": None
                }
            }
    
    def _save_history(self, history: Dict[str, Any]):
        """Save operation history to JSON file."""
        try:
            # Update metadata
            history["metadata"]["last_modified"] = datetime.utcnow().isoformat() + 'Z'
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.history_file_path), exist_ok=True)
            
            # Write history with proper formatting
            with open(self.history_file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except IOError as e:
            # Log error but don't raise to avoid breaking operations
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save operation history: {e}")
    
    def add_operation(self, operation: OperationHistory) -> str:
        """
        Add a new operation to the history.
        
        Args:
            operation: OperationHistory instance to add
            
        Returns:
            Operation ID
        """
        history = self._load_history()
        
        # Convert operation to dictionary
        operation_dict = operation.to_dict()
        
        # Add to history (newest first)
        history["operations"].insert(0, operation_dict)
        
        # Limit history size to prevent file from growing too large
        max_operations = 1000
        if len(history["operations"]) > max_operations:
            history["operations"] = history["operations"][:max_operations]
        
        self._save_history(history)
        return operation.id
    
    def update_operation(self, operation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing operation in the history.
        
        Args:
            operation_id: ID of the operation to update
            updates: Dictionary of fields to update
            
        Returns:
            True if operation was updated, False if not found
        """
        history = self._load_history()
        
        for operation in history["operations"]:
            if operation.get("id") == operation_id:
                operation.update(updates)
                self._save_history(history)
                return True
        
        return False
    
    def get_operations(self, 
                      node: Optional[str] = None,
                      resource_type: Optional[ResourceType] = None,
                      operation_type: Optional[OperationType] = None,
                      status: Optional[OperationStatus] = None,
                      limit: int = 100,
                      offset: int = 0) -> Dict[str, Any]:
        """
        Get operations with optional filtering.
        
        Args:
            node: Filter by node name
            resource_type: Filter by resource type
            operation_type: Filter by operation type
            status: Filter by operation status
            limit: Maximum number of operations to return
            offset: Number of operations to skip
            
        Returns:
            Dictionary with operations list and metadata
        """
        history = self._load_history()
        operations = history["operations"]
        
        # Apply filters
        if node:
            operations = [op for op in operations if op.get("node") == node]
        
        if resource_type:
            operations = [op for op in operations if op.get("resource_type") == resource_type.value]
        
        if operation_type:
            operations = [op for op in operations if op.get("operation") == operation_type.value]
        
        if status:
            operations = [op for op in operations if op.get("status") == status.value]
        
        # Apply pagination
        total = len(operations)
        operations = operations[offset:offset + limit]
        
        return {
            "operations": operations,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "node": node,
                "resource_type": resource_type.value if resource_type else None,
                "operation_type": operation_type.value if operation_type else None,
                "status": status.value if status else None
            }
        }
    
    def get_node_operations(self, node: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get operations for a specific node.
        
        Args:
            node: Node name
            limit: Maximum number of operations to return
            offset: Number of operations to skip
            
        Returns:
            Dictionary with operations list and metadata
        """
        return self.get_operations(node=node, limit=limit, offset=offset)
    
    def cleanup_old_operations(self, days: int = 30):
        """
        Remove operations older than specified days.
        
        Args:
            days: Number of days to keep operations
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat() + 'Z'
        
        history = self._load_history()
        original_count = len(history["operations"])
        
        # Keep operations newer than cutoff date
        history["operations"] = [
            op for op in history["operations"]
            if op.get("timestamp", "") > cutoff_iso
        ]
        
        removed_count = original_count - len(history["operations"])
        
        if removed_count > 0:
            self._save_history(history)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Cleaned up {removed_count} old operations (older than {days} days)")


def create_operation(node: str, resource_type: ResourceType, resource_id: Optional[int],
                    resource_name: Optional[str], operation: OperationType, 
                    status: OperationStatus = OperationStatus.IN_PROGRESS,
                    user: Optional[str] = None, error_message: Optional[str] = None,
                    duration: Optional[float] = None, details: Optional[Dict[str, Any]] = None) -> OperationHistory:
    """
    Create a new OperationHistory instance.
    
    Args:
        node: Node name
        resource_type: Type of resource
        resource_id: Resource ID (None for node operations)
        resource_name: Resource name
        operation: Operation type
        status: Operation status
        user: User who performed the operation
        error_message: Error message if operation failed
        duration: Operation duration in seconds
        details: Additional operation details
        
    Returns:
        OperationHistory instance
    """
    return OperationHistory(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat() + 'Z',
        node=node,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        operation=operation,
        status=status,
        user=user,
        error_message=error_message,
        duration=duration,
        details=details or {}
    )


# Global instance for easy access
_history_manager = None

def get_history_manager() -> OperationHistoryManager:
    """Get the global operation history manager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = OperationHistoryManager()
    return _history_manager