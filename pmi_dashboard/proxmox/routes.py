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
    ResourceType, 
    ResourceStatus,
    validate_vmid
)
from config import ProxmoxConfigManager

logger = logging.getLogger(__name__)

# Create Blueprint for Proxmox routes
proxmox_bp = Blueprint('proxmox', __name__, url_prefix='/api/proxmox')


def create_error_response(message: str, status_code: int = 400, details: Dict = None, error_code: str = None, help_text: str = None):
    """
    Create standardized error response for Flask with enhanced error handling.
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        error_code: Specific error code for client handling
        help_text: Custom help text for recovery
        
    Returns:
        Flask response tuple (jsonify(response), status_code)
    """
    response = {
        'success': False,
        'error': message,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'request_id': str(uuid.uuid4())[:8]  # Short request ID for tracking
    }
    
    if error_code:
        response['error_code'] = error_code
    
    if details:
        response['details'] = details
    
    # Add helpful information for common errors
    help_messages = {
        400: "Check your request parameters and try again",
        401: "Check your API token credentials and ensure they are valid",
        403: "Your API token may not have sufficient permissions for this operation",
        404: "The requested resource was not found or may have been deleted",
        408: "Request timeout - the operation took too long to complete",
        409: "Resource conflict - the operation cannot be completed in the current state",
        422: "Invalid request data - please check the required fields",
        429: "Too many requests - please wait before trying again",
        500: "Internal server error - please try again later",
        502: "Bad gateway - the Proxmox server may be temporarily unavailable",
        503: "Service temporarily unavailable - check network connectivity and server status",
        504: "Gateway timeout - the Proxmox server took too long to respond"
    }
    
    response['help'] = help_text or help_messages.get(status_code, "Please try again or contact support if the problem persists")
    
    # Add recovery suggestions based on error type
    recovery_suggestions = []
    
    if status_code == 401:
        recovery_suggestions.extend([
            "Verify your API token ID and secret are correct",
            "Check if the API token has expired",
            "Ensure the token has the required permissions"
        ])
    elif status_code == 403:
        recovery_suggestions.extend([
            "Check the API token permissions in Proxmox",
            "Verify the token is assigned to the correct user",
            "Ensure the user has the necessary privileges"
        ])
    elif status_code == 404:
        recovery_suggestions.extend([
            "Verify the resource ID is correct",
            "Check if the resource still exists",
            "Refresh the page to get updated information"
        ])
    elif status_code == 503:
        recovery_suggestions.extend([
            "Check if the Proxmox server is running",
            "Verify network connectivity to the server",
            "Try again in a few moments"
        ])
    elif status_code >= 500:
        recovery_suggestions.extend([
            "Try the operation again in a few moments",
            "Check the Proxmox server logs for more information",
            "Contact your system administrator if the problem persists"
        ])
    
    if recovery_suggestions:
        response['recovery_suggestions'] = recovery_suggestions
    
    # Log error with context
    log_context = {
        'status_code': status_code,
        'error_code': error_code,
        'request_id': response['request_id'],
        'details': details
    }
    
    logger.error(f"API Error ({status_code}): {message}", extra=log_context)
    
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
                                
                                # Get VM and LXC counts
                                try:
                                    vms = client.get_vms(node_name)
                                    node.vm_count = len(vms) if vms else 0
                                except Exception:
                                    node.vm_count = 0
                                
                                try:
                                    containers = client.get_containers(node_name)
                                    node.lxc_count = len(containers) if containers else 0
                                except Exception:
                                    node.lxc_count = 0
                        
                        node.status = 'online'
                    except Exception as e:
                        logger.warning(f"Could not get metrics for node {node.id}: {e}")
                        node.status = 'connected'
                else:
                    node.is_connected = False
                    node.connection_error = message
                    node.status = 'offline'
                    
                    # Clear metrics for disconnected nodes
                    node.cpu_usage = None
                    node.cpu_count = None
                    node.memory_usage = None
                    node.memory_total = None
                    node.memory_percentage = None
                    node.disk_usage = None
                    node.disk_total = None
                    node.disk_percentage = None
                    node.load_average = None
                    node.uptime = None
                    node.version = None
                    node.vm_count = None
                    node.lxc_count = None
                
                client.close()
                
            except Exception as e:
                node.is_connected = False
                node.connection_error = str(e)
                node.status = 'error'
                
                # Clear metrics for error state nodes
                node.cpu_usage = None
                node.cpu_count = None
                node.memory_usage = None
                node.memory_total = None
                node.memory_percentage = None
                node.disk_usage = None
                node.disk_total = None
                node.disk_percentage = None
                node.load_average = None
                node.uptime = None
                node.version = None
                node.vm_count = None
                node.lxc_count = None
            
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
        
        return jsonify(create_success_response(
            {
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
        return create_error_response(f"Connection failed: {str(e)}", 503)
    except ProxmoxAuthenticationError as e:
        return create_error_response(f"Authentication failed: {str(e)}", 401)
    except Exception as e:
        logger.exception(f"Failed to {operation} resource {vmid}")
        return create_error_response(f"Operation failed: {str(e)}", 500)


# Health Check Route

@proxmox_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the Proxmox API."""
    try:
        config_manager = ProxmoxConfigManager()
        nodes = config_manager.get_all_nodes()
        
        health_data = {
            'status': 'healthy',
            'nodes_configured': len(nodes),
            'nodes_enabled': len([n for n in nodes if n.get('enabled', True)]),
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