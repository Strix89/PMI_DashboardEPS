"""
Flask routes for Proxmox management functionality.

This module provides REST API endpoints for managing Proxmox nodes,
VMs, LXC containers, and retrieving real-time metrics and operation history.
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

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
    validate_vmid
)
from .history import get_history_manager, create_operation
from config import ProxmoxConfigManager

logger = logging.getLogger(__name__)

# Create Blueprint for Proxmox routes
proxmox_bp = Blueprint('proxmox', __name__, url_prefix='/api/proxmox')


def create_error_response(message: str, status_code: int = 400, details: Dict = None, error_code: str = None):
    """
    Create standardized error response for Flask.
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        error_code: Specific error code for client handling
        
    Returns:
        Flask response tuple (jsonify(response), status_code)
    """
    response = {
        'success': False,
        'error': message,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if error_code:
        response['error_code'] = error_code
    
    if details:
        response['details'] = details
    
    # Add helpful information for common errors
    if status_code == 401:
        response['help'] = "Check your API token credentials"
    elif status_code == 403:
        response['help'] = "Insufficient permissions for this operation"
    elif status_code == 404:
        response['help'] = "The requested resource was not found"
    elif status_code == 503:
        response['help'] = "Service temporarily unavailable, check network connectivity"
    
    logger.error(f"API Error ({status_code}): {message}")
    return jsonify(response), status_code


def create_success_response(data: Any = None, message: str = None) -> Dict[str, Any]:
    """
    Create standardized success response.
    
    Args:
        data: Response data
        message: Success message
        
    Returns:
        Response dictionary
    """
    response = {
        'success': True,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return response


def log_operation(node: str, resource_type: ResourceType, resource_id: Optional[int],
                 resource_name: Optional[str], operation: OperationType, 
                 status: OperationStatus, error_message: Optional[str] = None,
                 duration: Optional[float] = None, user: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None) -> str:
    """
    Log an operation to the operation history.
    
    Args:
        node: Node name
        resource_type: Type of resource
        resource_id: Resource ID (None for node operations)
        resource_name: Resource name
        operation: Operation type
        status: Operation status
        error_message: Error message if operation failed
        duration: Operation duration in seconds
        user: User who performed the operation
        details: Additional operation details
        
    Returns:
        Operation ID
    """
    # Create operation history entry
    operation_entry = create_operation(
        node=node,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        operation=operation,
        status=status,
        user=user,
        error_message=error_message,
        duration=duration,
        details=details
    )
    
    # Save to history
    history_manager = get_history_manager()
    operation_id = history_manager.add_operation(operation_entry)
    
    # Also log to application logs
    logger.info(f"Operation {operation_id}: {operation.value} {resource_type.value} "
               f"{resource_id or node} - Status: {status.value}")
    
    if error_message:
        logger.error(f"Operation {operation_id} failed: {error_message}")
    
    return operation_id


# Node Management Routes

@proxmox_bp.route('/nodes', methods=['GET'])
def get_nodes():
    """Get all configured Proxmox nodes with their current status."""
    try:
        config_manager = ProxmoxConfigManager()
        nodes_config = config_manager.get_all_nodes()
        
        nodes_with_status = []
        
        for node_config in nodes_config:
            if not node_config.get('enabled', True):
                # Skip disabled nodes
                continue
                
            node = ProxmoxNode.from_dict(node_config)
            
            # Test connection and get status
            try:
                client = create_client_from_config(node_config)
                success, message = client.test_connection()
                
                if success:
                    node.is_connected = True
                    node.connection_error = None
                    node.last_connected = datetime.utcnow().isoformat() + 'Z'
                    
                    # Get node metrics
                    try:
                        # Extract node name from cluster status or use first available node
                        cluster_status = client.get_cluster_status()
                        if isinstance(cluster_status, list) and cluster_status:
                            # Find the node entry in cluster status
                            node_name = None
                            for item in cluster_status:
                                if item.get('type') == 'node':
                                    node_name = item.get('name')
                                    break
                            
                            if node_name:
                                metrics = client.get_node_metrics(node_name)
                                node.cpu_usage = metrics.get('cpu_usage', 0)
                                node.cpu_count = metrics.get('cpu_count', 0)
                                node.memory_usage = metrics.get('memory_usage', 0)
                                node.memory_total = metrics.get('memory_total', 0)
                                node.memory_percentage = metrics.get('memory_percentage', 0)
                                node.disk_usage = metrics.get('disk_usage', 0)
                                node.disk_total = metrics.get('disk_total', 0)
                                node.disk_percentage = metrics.get('disk_percentage', 0)
                                node.load_average = metrics.get('load_average', [0, 0, 0])
                                node.uptime = metrics.get('uptime', 0)
                                node.version = metrics.get('status', 'unknown')
                        
                        node.status = 'online'
                    except Exception as e:
                        logger.warning(f"Could not get metrics for node {node.id}: {e}")
                        node.status = 'connected'
                else:
                    node.is_connected = False
                    node.connection_error = message
                    node.status = 'offline'
                
                client.close()
                
            except Exception as e:
                node.is_connected = False
                node.connection_error = str(e)
                node.status = 'error'
            
            node.last_updated = datetime.utcnow().isoformat() + 'Z'
            nodes_with_status.append(node.to_dict())
        
        return jsonify(create_success_response(nodes_with_status))
        
    except Exception as e:
        logger.exception("Failed to get nodes")
        return create_error_response(f"Failed to get nodes: {str(e)}", 500)


@proxmox_bp.route('/nodes', methods=['POST'])
def add_node():
    """Add a new Proxmox node configuration."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        # Validate required fields
        required_fields = ['name', 'host']
        for field in required_fields:
            if not data.get(field):
                return create_error_response(f"Missing required field: {field}", 400)
        
        # Test connection before adding
        test_config = {
            'host': data['host'],
            'port': data.get('port', 8006),
            'api_token_id': data.get('api_token_id'),
            'api_token_secret': data.get('api_token_secret'),
            'ssl_verify': data.get('ssl_verify', False),
            'timeout': data.get('timeout', 30)
        }
        
        try:
            client = create_client_from_config(test_config)
            success, message = client.test_connection()
            client.close()
            
            if not success:
                return create_error_response(f"Connection test failed: {message}", 400)
                
        except Exception as e:
            return create_error_response(f"Connection test failed: {str(e)}", 400)
        
        # Add node to configuration
        config_manager = ProxmoxConfigManager()
        node_id = config_manager.add_node(data)
        
        # Log operation
        log_operation(
            node=data['name'],
            resource_type=ResourceType.NODE,
            resource_id=None,
            resource_name=data['name'],
            operation=OperationType.START,  # Using START to represent "add"
            status=OperationStatus.SUCCESS
        )
        
        return jsonify(create_success_response(
            {'node_id': node_id}, 
            f"Node '{data['name']}' added successfully"
        ))
        
    except Exception as e:
        logger.exception("Failed to add node")
        return create_error_response(f"Failed to add node: {str(e)}", 500)


@proxmox_bp.route('/nodes/<node_id>', methods=['PUT'])
def update_node(node_id: str):
    """Update an existing Proxmox node configuration."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("No data provided", 400)
        
        config_manager = ProxmoxConfigManager()
        
        # Check if node exists
        existing_node = config_manager.get_node_by_id(node_id)
        if not existing_node:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        # Test connection if connection details are being updated
        connection_fields = ['host', 'port', 'api_token_id', 'api_token_secret', 'ssl_verify', 'timeout']
        if any(field in data for field in connection_fields):
            test_config = {**existing_node, **data}
            
            try:
                client = create_client_from_config(test_config)
                success, message = client.test_connection()
                client.close()
                
                if not success:
                    return create_error_response(f"Connection test failed: {message}", 400)
                    
            except Exception as e:
                return create_error_response(f"Connection test failed: {str(e)}", 400)
        
        # Update node
        success = config_manager.update_node(node_id, data)
        if not success:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        return jsonify(create_success_response(
            message=f"Node '{existing_node.get('name', node_id)}' updated successfully"
        ))
        
    except Exception as e:
        logger.exception("Failed to update node")
        return create_error_response(f"Failed to update node: {str(e)}", 500)


@proxmox_bp.route('/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id: str):
    """Delete a Proxmox node configuration."""
    try:
        config_manager = ProxmoxConfigManager()
        
        # Get node info before deletion for logging
        existing_node = config_manager.get_node_by_id(node_id)
        if not existing_node:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        # Remove node
        success = config_manager.remove_node(node_id)
        if not success:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        # Log operation
        log_operation(
            node=existing_node.get('name', node_id),
            resource_type=ResourceType.NODE,
            resource_id=None,
            resource_name=existing_node.get('name'),
            operation=OperationType.DELETE,
            status=OperationStatus.SUCCESS
        )
        
        return jsonify(create_success_response(
            message=f"Node '{existing_node.get('name', node_id)}' deleted successfully"
        ))
        
    except Exception as e:
        logger.exception("Failed to delete node")
        return create_error_response(f"Failed to delete node: {str(e)}", 500)


@proxmox_bp.route('/nodes/<node_id>/test', methods=['POST'])
def test_node_connection(node_id: str):
    """Test connection to a specific Proxmox node."""
    try:
        config_manager = ProxmoxConfigManager()
        node_config = config_manager.get_node_by_id(node_id)
        
        if not node_config:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        client = create_client_from_config(node_config)
        success, message = client.test_connection()
        client.close()
        
        if success:
            return jsonify(create_success_response({'connected': True}, message))
        else:
            return jsonify(create_success_response({'connected': False}, message))
            
    except Exception as e:
        logger.exception("Failed to test node connection")
        return create_error_response(f"Connection test failed: {str(e)}", 500)


@proxmox_bp.route('/test-connection', methods=['POST'])
def test_connection_config():
    """Test connection using provided configuration without saving."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("No configuration provided", 400)
        
        # Validate required fields
        required_fields = ['host']
        for field in required_fields:
            if not data.get(field):
                return create_error_response(f"Missing required field: {field}", 400)
        
        # Create test configuration
        test_config = {
            'host': data['host'],
            'port': data.get('port', 8006),
            'api_token_id': data.get('api_token_id'),
            'api_token_secret': data.get('api_token_secret'),
            'ssl_verify': data.get('ssl_verify', False),
            'timeout': data.get('timeout', 30)
        }
        
        client = create_client_from_config(test_config)
        success, message = client.test_connection()
        client.close()
        
        if success:
            return jsonify(create_success_response({'connected': True}, message))
        else:
            return jsonify(create_success_response({'connected': False}, message))
            
    except Exception as e:
        logger.exception("Failed to test connection configuration")
        return create_error_response(f"Connection test failed: {str(e)}", 500)


# Resource Management Routes

@proxmox_bp.route('/nodes/<node_id>/resources', methods=['GET'])
def get_node_resources(node_id: str):
    """Get all VMs and LXC containers for a specific node with real-time metrics."""
    try:
        config_manager = ProxmoxConfigManager()
        node_config = config_manager.get_node_by_id(node_id)
        
        if not node_config:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        if not node_config.get('enabled', True):
            return create_error_response(f"Node '{node_id}' is disabled", 400)
        
        client = create_client_from_config(node_config)
        
        # Get cluster status to find the actual node name
        cluster_status = client.get_cluster_status()
        node_name = None
        
        if isinstance(cluster_status, list):
            for item in cluster_status:
                if item.get('type') == 'node':
                    node_name = item.get('name')
                    break
        
        if not node_name:
            # Fallback: try to get nodes list
            nodes = client.get_nodes()
            if nodes:
                node_name = nodes[0].get('node', 'localhost')
        
        if not node_name:
            client.close()
            return create_error_response("Could not determine node name", 500)
        
        # Get all resources with metrics
        resources_data = client.get_all_resources_with_metrics(node_name)
        client.close()
        
        return jsonify(create_success_response(resources_data))
        
    except ProxmoxConnectionError as e:
        return create_error_response(f"Connection failed: {str(e)}", 503)
    except ProxmoxAuthenticationError as e:
        return create_error_response(f"Authentication failed: {str(e)}", 401)
    except Exception as e:
        logger.exception("Failed to get node resources")
        return create_error_response(f"Failed to get resources: {str(e)}", 500)


@proxmox_bp.route('/nodes/<node_id>/resources/<int:vmid>/metrics', methods=['GET'])
def get_resource_metrics(node_id: str, vmid: int):
    """Get real-time metrics for a specific VM or LXC container."""
    try:
        # Validate VMID
        vmid = validate_vmid(vmid)
        
        config_manager = ProxmoxConfigManager()
        node_config = config_manager.get_node_by_id(node_id)
        
        if not node_config:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        client = create_client_from_config(node_config)
        
        # Get cluster status to find the actual node name
        cluster_status = client.get_cluster_status()
        node_name = None
        
        if isinstance(cluster_status, list):
            for item in cluster_status:
                if item.get('type') == 'node':
                    node_name = item.get('name')
                    break
        
        if not node_name:
            nodes = client.get_nodes()
            if nodes:
                node_name = nodes[0].get('node', 'localhost')
        
        if not node_name:
            client.close()
            return create_error_response("Could not determine node name", 500)
        
        # Try to get VM metrics first, then container metrics
        try:
            metrics = client.get_vm_metrics(node_name, vmid)
        except ProxmoxAPIError:
            try:
                metrics = client.get_container_metrics(node_name, vmid)
            except ProxmoxAPIError:
                client.close()
                return create_error_response(f"Resource {vmid} not found", 404)
        
        client.close()
        return jsonify(create_success_response(metrics))
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.exception("Failed to get resource metrics")
        return create_error_response(f"Failed to get metrics: {str(e)}", 500)


# VM/LXC Control Operations

@proxmox_bp.route('/nodes/<node_id>/resources/<int:vmid>/start', methods=['POST'])
def start_resource(node_id: str, vmid: int):
    """Start a VM or LXC container."""
    try:
        # Validate VMID early
        vmid = validate_vmid(vmid)
        return _control_resource(node_id, vmid, 'start')
    except ValueError as e:
        return create_error_response(str(e), 400)


@proxmox_bp.route('/nodes/<node_id>/resources/<int:vmid>/stop', methods=['POST'])
def stop_resource(node_id: str, vmid: int):
    """Stop a VM or LXC container."""
    try:
        # Validate VMID early
        vmid = validate_vmid(vmid)
        
        # Parse request data safely
        data = request.get_json() or {}
        force = data.get('force', False)
        
        if not isinstance(force, bool):
            return create_error_response("'force' parameter must be a boolean", 400)
        
        return _control_resource(node_id, vmid, 'stop', force=force)
    except ValueError as e:
        return create_error_response(str(e), 400)


@proxmox_bp.route('/nodes/<node_id>/resources/<int:vmid>/restart', methods=['POST'])
def restart_resource(node_id: str, vmid: int):
    """Restart a VM or LXC container."""
    try:
        # Validate VMID early
        vmid = validate_vmid(vmid)
        
        # Parse request data safely
        data = request.get_json() or {}
        force = data.get('force', False)
        
        if not isinstance(force, bool):
            return create_error_response("'force' parameter must be a boolean", 400)
        
        return _control_resource(node_id, vmid, 'restart', force=force)
    except ValueError as e:
        return create_error_response(str(e), 400)


def _control_resource(node_id: str, vmid: int, operation: str, force: bool = False):
    """
    Internal function to control VM/LXC resources.
    
    Args:
        node_id: Node ID
        vmid: VM/Container ID
        operation: Operation to perform ('start', 'stop', 'restart')
        force: Force operation
        
    Returns:
        JSON response
    """
    start_time = datetime.utcnow()
    operation_id = None
    
    try:
        # Validate VMID
        vmid = validate_vmid(vmid)
        
        config_manager = ProxmoxConfigManager()
        node_config = config_manager.get_node_by_id(node_id)
        
        if not node_config:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        client = create_client_from_config(node_config)
        
        # Get cluster status to find the actual node name
        cluster_status = client.get_cluster_status()
        node_name = None
        
        if isinstance(cluster_status, list):
            for item in cluster_status:
                if item.get('type') == 'node':
                    node_name = item.get('name')
                    break
        
        if not node_name:
            nodes = client.get_nodes()
            if nodes:
                node_name = nodes[0].get('node', 'localhost')
        
        if not node_name:
            client.close()
            return create_error_response("Could not determine node name", 500)
        
        # Determine resource type and get current status
        resource_type = None
        resource_name = None
        
        try:
            # Try VM first
            vm_status = client.get_vm_status(node_name, vmid)
            resource_type = ResourceType.VM
            resource_name = vm_status.get('name', f'VM-{vmid}')
        except ProxmoxAPIError:
            try:
                # Try container
                container_status = client.get_container_status(node_name, vmid)
                resource_type = ResourceType.LXC
                resource_name = container_status.get('name', f'CT-{vmid}')
            except ProxmoxAPIError:
                client.close()
                return create_error_response(f"Resource {vmid} not found", 404)
        
        # Log operation start
        operation_type = OperationType(operation.upper())
        operation_id = log_operation(
            node=node_name,
            resource_type=resource_type,
            resource_id=vmid,
            resource_name=resource_name,
            operation=operation_type,
            status=OperationStatus.IN_PROGRESS,
            details={'force': force}
        )
        
        # Perform the operation
        result = None
        
        if resource_type == ResourceType.VM:
            if operation == 'start':
                result = client.start_vm(node_name, vmid)
            elif operation == 'stop':
                result = client.stop_vm(node_name, vmid, force=force)
            elif operation == 'restart':
                result = client.restart_vm(node_name, vmid, force=force)
        else:  # LXC
            if operation == 'start':
                result = client.start_container(node_name, vmid)
            elif operation == 'stop':
                result = client.stop_container(node_name, vmid, force=force)
            elif operation == 'restart':
                result = client.restart_container(node_name, vmid, force=force)
        
        client.close()
        
        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Update operation as successful
        if operation_id:
            history_manager = get_history_manager()
            history_manager.update_operation(operation_id, {
                'status': OperationStatus.SUCCESS.value,
                'duration': duration,
                'details': {'force': force, 'result': result}
            })
        
        return jsonify(create_success_response(
            {
                'operation_id': operation_id,
                'vmid': vmid,
                'operation': operation,
                'force': force,
                'result': result
            },
            f"Successfully {operation}ed {resource_type.value.upper()}-{vmid}"
        ))
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except ProxmoxConnectionError as e:
        error_msg = f"Connection failed: {str(e)}"
        if operation_id:
            duration = (datetime.utcnow() - start_time).total_seconds()
            history_manager = get_history_manager()
            history_manager.update_operation(operation_id, {
                'status': OperationStatus.FAILED.value,
                'error_message': error_msg,
                'duration': duration
            })
        return create_error_response(error_msg, 503)
    except ProxmoxAuthenticationError as e:
        error_msg = f"Authentication failed: {str(e)}"
        if operation_id:
            duration = (datetime.utcnow() - start_time).total_seconds()
            history_manager = get_history_manager()
            history_manager.update_operation(operation_id, {
                'status': OperationStatus.FAILED.value,
                'error_message': error_msg,
                'duration': duration
            })
        return create_error_response(error_msg, 401)
    except Exception as e:
        error_msg = f"Operation failed: {str(e)}"
        logger.exception(f"Failed to {operation} resource {vmid}")
        if operation_id:
            duration = (datetime.utcnow() - start_time).total_seconds()
            history_manager = get_history_manager()
            history_manager.update_operation(operation_id, {
                'status': OperationStatus.FAILED.value,
                'error_message': error_msg,
                'duration': duration
            })
        return create_error_response(error_msg, 500)


# Operation History Routes

@proxmox_bp.route('/history', methods=['GET'])
def get_operation_history():
    """Get operation history with optional filtering."""
    try:
        # Get query parameters for filtering
        node = request.args.get('node')
        resource_type_str = request.args.get('resource_type')
        operation_type_str = request.args.get('operation_type')
        status_str = request.args.get('status')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Convert string parameters to enums
        resource_type = None
        if resource_type_str:
            try:
                resource_type = ResourceType(resource_type_str)
            except ValueError:
                return create_error_response(f"Invalid resource_type: {resource_type_str}", 400)
        
        operation_type = None
        if operation_type_str:
            try:
                operation_type = OperationType(operation_type_str.upper())
            except ValueError:
                return create_error_response(f"Invalid operation_type: {operation_type_str}", 400)
        
        status = None
        if status_str:
            try:
                status = OperationStatus(status_str.upper())
            except ValueError:
                return create_error_response(f"Invalid status: {status_str}", 400)
        
        # Get history from manager
        history_manager = get_history_manager()
        history_data = history_manager.get_operations(
            node=node,
            resource_type=resource_type,
            operation_type=operation_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return jsonify(create_success_response(history_data))
        
    except Exception as e:
        logger.exception("Failed to get operation history")
        return create_error_response(f"Failed to get history: {str(e)}", 500)


@proxmox_bp.route('/nodes/<node_id>/history', methods=['GET'])
def get_node_operation_history(node_id: str):
    """Get operation history for a specific node."""
    try:
        config_manager = ProxmoxConfigManager()
        node_config = config_manager.get_node_by_id(node_id)
        
        if not node_config:
            return create_error_response(f"Node with ID '{node_id}' not found", 404)
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        resource_type_str = request.args.get('resource_type')
        operation_type_str = request.args.get('operation_type')
        status_str = request.args.get('status')
        
        # Convert string parameters to enums
        resource_type = None
        if resource_type_str:
            try:
                resource_type = ResourceType(resource_type_str)
            except ValueError:
                return create_error_response(f"Invalid resource_type: {resource_type_str}", 400)
        
        operation_type = None
        if operation_type_str:
            try:
                operation_type = OperationType(operation_type_str.upper())
            except ValueError:
                return create_error_response(f"Invalid operation_type: {operation_type_str}", 400)
        
        status = None
        if status_str:
            try:
                status = OperationStatus(status_str.upper())
            except ValueError:
                return create_error_response(f"Invalid status: {status_str}", 400)
        
        # Get history from manager using node name
        node_name = node_config.get('name', node_id)
        history_manager = get_history_manager()
        
        # Get operations with additional filtering
        history_data = history_manager.get_operations(
            node=node_name,
            resource_type=resource_type,
            operation_type=operation_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Add node information to response
        history_data['node_id'] = node_id
        history_data['node_name'] = node_name
        
        return jsonify(create_success_response(history_data))
        
    except Exception as e:
        logger.exception("Failed to get node operation history")
        return create_error_response(f"Failed to get node history: {str(e)}", 500)


# Health Check Route

@proxmox_bp.route('/history/stats', methods=['GET'])
def get_operation_statistics():
    """Get operation statistics and summary."""
    try:
        history_manager = get_history_manager()
        
        # Get all operations for statistics
        all_operations = history_manager.get_operations(limit=10000)  # Large limit to get all
        operations = all_operations['operations']
        
        # Calculate statistics
        stats = {
            'total_operations': len(operations),
            'operations_by_status': {},
            'operations_by_type': {},
            'operations_by_resource_type': {},
            'operations_by_node': {},
            'recent_operations': operations[:10],  # Last 10 operations
            'success_rate': 0.0
        }
        
        # Count by status
        for op in operations:
            status = op.get('status', 'unknown')
            stats['operations_by_status'][status] = stats['operations_by_status'].get(status, 0) + 1
        
        # Count by operation type
        for op in operations:
            op_type = op.get('operation', 'unknown')
            stats['operations_by_type'][op_type] = stats['operations_by_type'].get(op_type, 0) + 1
        
        # Count by resource type
        for op in operations:
            resource_type = op.get('resource_type', 'unknown')
            stats['operations_by_resource_type'][resource_type] = stats['operations_by_resource_type'].get(resource_type, 0) + 1
        
        # Count by node
        for op in operations:
            node = op.get('node', 'unknown')
            stats['operations_by_node'][node] = stats['operations_by_node'].get(node, 0) + 1
        
        # Calculate success rate
        successful_ops = stats['operations_by_status'].get('success', 0)
        if len(operations) > 0:
            stats['success_rate'] = (successful_ops / len(operations)) * 100
        
        return jsonify(create_success_response(stats))
        
    except Exception as e:
        logger.exception("Failed to get operation statistics")
        return create_error_response(f"Failed to get statistics: {str(e)}", 500)


@proxmox_bp.route('/history/cleanup', methods=['POST'])
def cleanup_operation_history():
    """Clean up old operation history entries."""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        # Validate days parameter
        if not isinstance(days, int) or days < 1 or days > 365:
            return create_error_response("Days must be an integer between 1 and 365", 400)
        
        history_manager = get_history_manager()
        history_manager.cleanup_old_operations(days)
        
        return jsonify(create_success_response(
            message=f"Successfully cleaned up operations older than {days} days"
        ))
        
    except Exception as e:
        logger.exception("Failed to cleanup operation history")
        return create_error_response(f"Failed to cleanup history: {str(e)}", 500)


@proxmox_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the Proxmox API."""
    try:
        config_manager = ProxmoxConfigManager()
        nodes = config_manager.get_all_nodes()
        
        # Get operation history stats
        history_manager = get_history_manager()
        recent_operations = history_manager.get_operations(limit=10)
        
        health_data = {
            'status': 'healthy',
            'nodes_configured': len(nodes),
            'nodes_enabled': len([n for n in nodes if n.get('enabled', True)]),
            'recent_operations_count': len(recent_operations['operations']),
            'total_operations': recent_operations['total'],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(create_success_response(health_data))
        
    except Exception as e:
        logger.exception("Health check failed")
        return create_error_response(f"Health check failed: {str(e)}", 500)


# Error Handlers

@proxmox_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return create_error_response("Bad request", 400)


@proxmox_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return create_error_response("Resource not found", 404)


@proxmox_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return create_error_response("Internal server error", 500)