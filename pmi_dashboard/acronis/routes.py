"""
Flask routes for Acronis backup management functionality.

This module provides REST API endpoints for managing Acronis API configuration,
retrieving agent information, workload data, backup statistics, and health monitoring.
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from .api_client import (
    AcronisAPIClient,
    AcronisAPIError,
    AcronisAuthenticationError,
    AcronisConnectionError,
)
from .models import (
    AcronisAgent,
    AcronisWorkload,
    AcronisBackup,
    BackupStatistics,
    validate_agent_data,
    validate_backup_data,
    transform_agent_data,
    transform_backup_data,
    create_backup_statistics,
)
from .config_manager import AcronisConfigManager, AcronisConfigurationError

logger = logging.getLogger(__name__)

# Create Blueprint for Acronis routes
acronis_bp = Blueprint("acronis", __name__, url_prefix="/api/acronis")


def create_error_response(
    message: str,
    status_code: int = 400,
    details: Dict = None,
    error_code: str = None,
    help_text: str = None,
    recoverable: bool = True,
    retry_after: int = None,
    operation: str = None
):
    """
    Create standardized error response for Flask with comprehensive error handling.

    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        error_code: Specific error code for client handling
        help_text: Custom help text for recovery
        recoverable: Whether the error is recoverable
        retry_after: Seconds to wait before retrying
        operation: Operation that failed

    Returns:
        Flask response tuple (jsonify(response), status_code)
    """
    request_id = str(uuid.uuid4())[:8]
    
    response = {
        "success": False,
        "error": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
        "recoverable": recoverable
    }

    if error_code:
        response["error_code"] = error_code
        
    if retry_after:
        response["retry_after"] = retry_after

    if details:
        response["details"] = details
        
    if operation:
        response["operation"] = operation

    # Add helpful information for common errors
    help_messages = {
        400: "Check your request parameters and try again",
        401: "Check your API credentials and ensure they are valid",
        403: "Your API credentials may not have sufficient permissions for this operation",
        404: "The requested resource was not found or may have been deleted",
        408: "Request timeout - the operation took too long to complete",
        409: "Resource conflict - the operation cannot be completed in the current state",
        422: "Invalid request data - please check the required fields",
        429: "Too many requests - please wait before trying again",
        500: "Internal server error - please try again later",
        502: "Bad gateway - the Acronis server may be temporarily unavailable",
        503: "Service temporarily unavailable - check network connectivity and server status",
        504: "Gateway timeout - the Acronis server took too long to respond",
    }

    response["help"] = help_text or help_messages.get(
        status_code, "Please try again or contact support if the problem persists"
    )

    # Add recovery suggestions based on error type and code
    recovery_suggestions = []
    troubleshooting_steps = []

    if error_code == "ACRONIS_NOT_CONFIGURED":
        recovery_suggestions.extend([
            "Configure your Acronis API credentials in the configuration tab",
            "Ensure you have valid Client ID and Client Secret from Acronis",
            "Verify the Base URL points to your Acronis server"
        ])
        troubleshooting_steps.extend([
            "Go to the Acronis configuration tab",
            "Enter your API credentials",
            "Test the connection before saving"
        ])
    elif error_code == "ACRONIS_AUTH_ERROR" or status_code == 401:
        recovery_suggestions.extend([
            "Verify your API client ID and secret are correct",
            "Check if the API credentials have expired",
            "Ensure the credentials have the required permissions",
            "Try regenerating your API credentials in Acronis"
        ])
        troubleshooting_steps.extend([
            "Check your Acronis API credentials",
            "Verify the Client ID and Client Secret are correct",
            "Ensure the credentials haven't expired",
            "Test the connection in the configuration tab"
        ])
    elif error_code == "ACRONIS_CONNECTION_ERROR" or status_code == 503:
        recovery_suggestions.extend([
            "Check if the Acronis server is running and accessible",
            "Verify network connectivity to the server",
            "Check if the Base URL is correct",
            "Try again in a few moments"
        ])
        troubleshooting_steps.extend([
            "Verify the Base URL in your configuration",
            "Check network connectivity to the Acronis server",
            "Ensure the server is running and accessible",
            "Try the connection test in the configuration tab"
        ])
    elif error_code == "ACRONIS_RATE_LIMIT" or status_code == 429:
        recovery_suggestions.extend([
            f"Wait {retry_after or 60} seconds before trying again",
            "Reduce the frequency of requests",
            "Consider implementing request throttling"
        ])
        troubleshooting_steps.extend([
            "Wait before making another request",
            "Check if auto-refresh is enabled and consider disabling it temporarily",
            "Try refreshing data manually instead of automatically"
        ])
    elif error_code == "ACRONIS_CIRCUIT_BREAKER_OPEN":
        recovery_suggestions.extend([
            f"Wait {retry_after or 300} seconds for the circuit breaker to reset",
            "Check the Acronis server status",
            "Verify network connectivity"
        ])
        troubleshooting_steps.extend([
            "Wait for the service to recover automatically",
            "Check the Acronis server logs for issues",
            "Verify network connectivity is stable"
        ])
    elif status_code == 403:
        recovery_suggestions.extend([
            "Check the API credentials permissions in Acronis",
            "Verify the credentials are assigned to the correct tenant",
            "Ensure the user has the necessary privileges for this operation"
        ])
        troubleshooting_steps.extend([
            "Review your API credentials permissions in Acronis",
            "Ensure the credentials have access to the required resources",
            "Contact your Acronis administrator if needed"
        ])
    elif status_code == 404:
        recovery_suggestions.extend([
            "Verify the resource ID is correct",
            "Check if the resource still exists",
            "Refresh the page to get updated information"
        ])
        troubleshooting_steps.extend([
            "Refresh the data to get the latest information",
            "Check if the resource was deleted or moved",
            "Verify you have access to the resource"
        ])
    elif status_code >= 500:
        recovery_suggestions.extend([
            "Try the operation again in a few moments",
            "Check the Acronis server status",
            "Contact your system administrator if the problem persists"
        ])
        troubleshooting_steps.extend([
            "Wait a moment and try again",
            "Check if other Acronis operations are working",
            "Contact support if the issue continues"
        ])

    if recovery_suggestions:
        response["recovery_suggestions"] = recovery_suggestions
        
    if troubleshooting_steps:
        response["troubleshooting_steps"] = troubleshooting_steps

    # Add user-friendly error categories
    error_category = "unknown"
    if status_code == 401 or error_code in ["ACRONIS_AUTH_ERROR", "ACRONIS_INVALID_CREDENTIALS"]:
        error_category = "authentication"
    elif status_code == 403:
        error_category = "authorization"
    elif status_code in [502, 503, 504] or error_code in ["ACRONIS_CONNECTION_ERROR", "ACRONIS_TIMEOUT"]:
        error_category = "connectivity"
    elif status_code == 429 or error_code == "ACRONIS_RATE_LIMIT":
        error_category = "rate_limit"
    elif status_code == 404:
        error_category = "not_found"
    elif status_code >= 500:
        error_category = "server_error"
    elif status_code >= 400:
        error_category = "client_error"
        
    response["error_category"] = error_category

    # Log error with comprehensive context
    log_context = {
        "status_code": status_code,
        "error_code": error_code,
        "error_category": error_category,
        "request_id": request_id,
        "operation": operation,
        "recoverable": recoverable,
        "retry_after": retry_after,
        "details": details,
        "user_agent": request.headers.get('User-Agent', 'Unknown') if request else 'Unknown',
        "remote_addr": request.remote_addr if request else 'Unknown'
    }

    # Use appropriate logger based on severity
    if status_code >= 500:
        error_logger.error(f"Server Error ({status_code}): {message}", extra=log_context)
    elif status_code >= 400:
        logger.warning(f"Client Error ({status_code}): {message}", extra=log_context)
    else:
        logger.info(f"API Response ({status_code}): {message}", extra=log_context)

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
    response = {"success": True, "timestamp": datetime.utcnow().isoformat() + "Z"}

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    return response


def handle_acronis_api_error(error: Exception, operation: str) -> tuple:
    """
    Handle Acronis API errors and convert them to appropriate HTTP responses.
    
    Args:
        error: The exception that occurred
        operation: Description of the operation that failed
        
    Returns:
        Tuple of (response, status_code) for Flask
    """
    if isinstance(error, AcronisAuthenticationError):
        return create_error_response(
            f"Authentication failed: {str(error)}",
            401,
            error_code=error.error_code or "ACRONIS_AUTH_ERROR",
            details=error.details,
            operation=operation,
            recoverable=error.recoverable
        )
    elif isinstance(error, AcronisConnectionError):
        return create_error_response(
            f"Connection failed: {str(error)}",
            503,
            error_code=error.error_code or "ACRONIS_CONNECTION_ERROR",
            details=error.details,
            operation=operation,
            recoverable=error.recoverable,
            retry_after=error.retry_after
        )
    elif isinstance(error, AcronisRateLimitError):
        return create_error_response(
            f"Rate limit exceeded: {str(error)}",
            429,
            error_code="ACRONIS_RATE_LIMIT",
            details=error.details,
            operation=operation,
            recoverable=error.recoverable,
            retry_after=error.retry_after
        )
    elif isinstance(error, AcronisServerError):
        return create_error_response(
            f"Server error: {str(error)}",
            error.details.get('status_code', 500),
            error_code=error.error_code or "ACRONIS_SERVER_ERROR",
            details=error.details,
            operation=operation,
            recoverable=error.recoverable
        )
    elif isinstance(error, AcronisAPIError):
        # Generic API error
        status_code = 500 if not error.recoverable else 503
        return create_error_response(
            f"API error: {str(error)}",
            status_code,
            error_code=error.error_code or "ACRONIS_API_ERROR",
            details=error.details,
            operation=operation,
            recoverable=error.recoverable,
            retry_after=error.retry_after
        )
    else:
        # Unexpected error
        logger.error(f"Unexpected error in {operation}: {error}", exc_info=True)
        return create_error_response(
            f"Unexpected error during {operation}",
            500,
            error_code="ACRONIS_UNEXPECTED_ERROR",
            details={"error_type": type(error).__name__},
            operation=operation,
            recoverable=False
        )


def create_client_from_config() -> Optional[AcronisAPIClient]:
    """
    Create Acronis API client from current configuration with enhanced error handling.

    Returns:
        AcronisAPIClient instance or None if configuration is not available
    """
    try:
        config_manager = AcronisConfigManager()
        config = config_manager.get_config()

        if not config:
            logger.debug("No Acronis configuration found")
            return None

        # Validate required configuration fields
        required_fields = ['base_url', 'client_id', 'client_secret']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            logger.error(f"Missing required configuration fields: {missing_fields}")
            return None

        client = AcronisAPIClient(
            base_url=config["base_url"],
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            grant_type=config.get("grant_type", "client_credentials"),
        )
        
        logger.debug("Successfully created Acronis API client from configuration")
        return client
        
    except Exception as e:
        logger.error(f"Failed to create Acronis API client: {e}", exc_info=True)
        return None


# Configuration Management Routes


@acronis_bp.route("/config", methods=["GET"])
def get_config():
    """Get current Acronis API configuration (without sensitive data)."""
    try:
        config_manager = AcronisConfigManager()
        config = config_manager.get_config()

        if not config:
            return jsonify(
                create_success_response(
                    {"configured": False, "message": "No Acronis configuration found"}
                )
            )

        # Return configuration without sensitive data
        safe_config = {
            "configured": True,
            "base_url": config.get("base_url", ""),
            "client_id": config.get("client_id", ""),
            "grant_type": config.get("grant_type", "client_credentials"),
            "client_secret_configured": bool(config.get("client_secret")),
        }

        return jsonify(create_success_response(safe_config))

    except Exception as e:
        logger.exception("Failed to get Acronis configuration")
        return create_error_response(f"Failed to get configuration: {str(e)}", 500)


@acronis_bp.route("/config", methods=["POST"])
def save_config():
    """Save new Acronis API configuration."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("No configuration data provided", 400)

        config_manager = AcronisConfigManager()

        # Validate configuration
        validation_errors = config_manager.validate_config(data)
        if validation_errors:
            return create_error_response(
                "Invalid configuration",
                400,
                details={"validation_errors": validation_errors},
            )

        # Test connection before saving
        try:
            test_client = AcronisAPIClient(
                base_url=data["base_url"],
                client_id=data["client_id"],
                client_secret=data["client_secret"],
                grant_type=data.get("grant_type", "client_credentials"),
            )

            if not test_client.test_connection():
                return create_error_response(
                    "Connection test failed with provided credentials",
                    400,
                    error_code="ACRONIS_CONNECTION_TEST_FAILED",
                )

        except Exception as e:
            return create_error_response(
                f"Connection test failed: {str(e)}",
                400,
                error_code="ACRONIS_CONNECTION_ERROR",
            )

        # Save configuration
        config_manager.save_config(data)

        return jsonify(
            create_success_response(
                {"configured": True}, "Acronis configuration saved successfully"
            )
        )

    except AcronisConfigurationError as e:
        return create_error_response(str(e), 400, error_code="ACRONIS_CONFIG_ERROR")
    except Exception as e:
        logger.exception("Failed to save Acronis configuration")
        return create_error_response(f"Failed to save configuration: {str(e)}", 500)


@acronis_bp.route("/config", methods=["PUT"])
def update_config():
    """Update existing Acronis API configuration."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response("No configuration data provided", 400)

        config_manager = AcronisConfigManager()

        # Get existing configuration
        existing_config = config_manager.get_config()
        if not existing_config:
            return create_error_response("No existing configuration found", 404)

        # Merge with existing configuration
        updated_config = {**existing_config, **data}

        # Validate updated configuration
        validation_errors = config_manager.validate_config(updated_config)
        if validation_errors:
            return create_error_response(
                "Invalid configuration",
                400,
                details={"validation_errors": validation_errors},
            )

        # Test connection if credentials are being updated
        connection_fields = ["base_url", "client_id", "client_secret", "grant_type"]
        if any(field in data for field in connection_fields):
            try:
                test_client = AcronisAPIClient(
                    base_url=updated_config["base_url"],
                    client_id=updated_config["client_id"],
                    client_secret=updated_config["client_secret"],
                    grant_type=updated_config.get("grant_type", "client_credentials"),
                )

                if not test_client.test_connection():
                    return create_error_response(
                        "Connection test failed with updated credentials",
                        400,
                        error_code="ACRONIS_CONNECTION_TEST_FAILED",
                    )

            except Exception as e:
                return create_error_response(
                    f"Connection test failed: {str(e)}",
                    400,
                    error_code="ACRONIS_CONNECTION_ERROR",
                )

        # Save updated configuration
        config_manager.save_config(updated_config)

        return jsonify(
            create_success_response(
                {"configured": True}, "Acronis configuration updated successfully"
            )
        )

    except AcronisConfigurationError as e:
        return create_error_response(str(e), 400, error_code="ACRONIS_CONFIG_ERROR")
    except Exception as e:
        logger.exception("Failed to update Acronis configuration")
        return create_error_response(f"Failed to update configuration: {str(e)}", 500)


@acronis_bp.route("/config", methods=["DELETE"])
def delete_config():
    """Delete Acronis API configuration."""
    try:
        config_manager = AcronisConfigManager()

        # Check if configuration exists
        existing_config = config_manager.get_config()
        if not existing_config:
            return create_error_response("No configuration found to delete", 404)

        # Delete configuration
        config_manager.delete_config()

        return jsonify(
            create_success_response(
                {"configured": False}, "Acronis configuration deleted successfully"
            )
        )

    except AcronisConfigurationError as e:
        return create_error_response(str(e), 400, error_code="ACRONIS_CONFIG_ERROR")
    except Exception as e:
        logger.exception("Failed to delete Acronis configuration")
        return create_error_response(f"Failed to delete configuration: {str(e)}", 500)


# Data Retrieval Routes


@acronis_bp.route("/agents", methods=["GET"])
def get_agents():
    """Get all Acronis agents with their current status."""
    try:
        client = create_client_from_config()
        if not client:
            return create_error_response(
                "Acronis not configured. Please configure API credentials first.",
                400,
                error_code="ACRONIS_NOT_CONFIGURED",
            )

        # Fetch agents from API
        agents_data = client.fetch_all_agents()
        if agents_data is None:
            return create_error_response(
                "Failed to fetch agents from Acronis API",
                503,
                error_code="ACRONIS_API_ERROR",
            )

        # Transform and validate agent data
        processed_agents = []
        for agent_data in agents_data:
            try:
                # Transform raw API data
                transformed_data = transform_agent_data(agent_data)

                # Validate data
                validation_errors = validate_agent_data(transformed_data)
                if validation_errors:
                    logger.warning(f"Agent data validation failed: {validation_errors}")
                    continue

                # Create agent model
                agent = AcronisAgent.from_dict(transformed_data)
                processed_agents.append(agent.to_dict())

            except Exception as e:
                logger.warning(f"Failed to process agent data: {e}")
                continue

        return jsonify(
            create_success_response(
                {"agents": processed_agents, "total_count": len(processed_agents)}
            )
        )

    except AcronisConnectionError as e:
        return create_error_response(
            f"Connection failed: {str(e)}", 503, error_code="ACRONIS_CONNECTION_ERROR"
        )
    except AcronisAuthenticationError as e:
        return create_error_response(
            f"Authentication failed: {str(e)}", 401, error_code="ACRONIS_AUTH_ERROR"
        )
    except Exception as e:
        logger.exception("Failed to get Acronis agents")
        return create_error_response(f"Failed to get agents: {str(e)}", 500)


@acronis_bp.route("/workloads", methods=["GET"])
def get_workloads():
    """Get all Acronis workloads."""
    try:
        client = create_client_from_config()
        if not client:
            return create_error_response(
                "Acronis not configured. Please configure API credentials first.",
                400,
                error_code="ACRONIS_NOT_CONFIGURED",
            )

        # Fetch workloads from API
        workloads_data = client.fetch_all_workloads()
        if workloads_data is None:
            return create_error_response(
                "Failed to fetch workloads from Acronis API",
                503,
                error_code="ACRONIS_API_ERROR",
            )

        # Process workload data
        processed_workloads = []
        for workload_data in workloads_data:
            try:
                workload = AcronisWorkload(
                    id_workload=workload_data.get("id", ""),
                    hostname=workload_data.get("name", "Unknown"),
                    id_tenant=workload_data.get("tenant_id", ""),
                )
                processed_workloads.append(workload.to_dict())

            except Exception as e:
                logger.warning(f"Failed to process workload data: {e}")
                continue

        return jsonify(
            create_success_response(
                {
                    "workloads": processed_workloads,
                    "total_count": len(processed_workloads),
                }
            )
        )

    except AcronisConnectionError as e:
        return create_error_response(
            f"Connection failed: {str(e)}", 503, error_code="ACRONIS_CONNECTION_ERROR"
        )
    except AcronisAuthenticationError as e:
        return create_error_response(
            f"Authentication failed: {str(e)}", 401, error_code="ACRONIS_AUTH_ERROR"
        )
    except Exception as e:
        logger.exception("Failed to get Acronis workloads")
        return create_error_response(f"Failed to get workloads: {str(e)}", 500)


@acronis_bp.route("/associations", methods=["GET"])
def get_associations():
    """Get agent-workload associations."""
    try:
        client = create_client_from_config()
        if not client:
            return create_error_response(
                "Acronis not configured. Please configure API credentials first.",
                400,
                error_code="ACRONIS_NOT_CONFIGURED",
            )

        # Fetch associations from API
        associations_data = client.association_workload_agent()
        if associations_data is None:
            return create_error_response(
                "Failed to fetch associations from Acronis API",
                503,
                error_code="ACRONIS_API_ERROR",
            )

        return jsonify(
            create_success_response(
                {
                    "associations": associations_data,
                    "total_count": len(associations_data),
                }
            )
        )

    except AcronisConnectionError as e:
        return create_error_response(
            f"Connection failed: {str(e)}", 503, error_code="ACRONIS_CONNECTION_ERROR"
        )
    except AcronisAuthenticationError as e:
        return create_error_response(
            f"Authentication failed: {str(e)}", 401, error_code="ACRONIS_AUTH_ERROR"
        )
    except Exception as e:
        logger.exception("Failed to get Acronis associations")
        return create_error_response(f"Failed to get associations: {str(e)}", 500)


@acronis_bp.route("/backups", methods=["GET"])
def get_all_backups():
    """Get backup information for all workloads with statistics."""
    try:
        client = create_client_from_config()
        if not client:
            return create_error_response(
                "Acronis not configured. Please configure API credentials first.",
                400,
                error_code="ACRONIS_NOT_CONFIGURED",
            )

        # Fetch all backup information
        backup_data = client.all_backup_info_workloads()
        if backup_data is None:
            return create_error_response(
                "Failed to fetch backup information from Acronis API",
                503,
                error_code="ACRONIS_API_ERROR",
            )

        # Process backup data and create statistics
        processed_data = {
            "summary": backup_data.get("summary", {}),
            "workload_data": {},
            "statistics": None,
        }

        all_backups = []

        for workload_id, workload_info in backup_data.get("workload_data", {}).items():
            processed_workload = {
                "hostname": workload_info.get("hostname", "Unknown"),
                "id_tenant": workload_info.get("id_tenant", ""),
                "backups": [],
            }

            for backup_data_item in workload_info.get("backups", []):
                try:
                    # Transform and validate backup data
                    transformed_backup = transform_backup_data(backup_data_item)
                    validation_errors = validate_backup_data(transformed_backup)

                    if validation_errors:
                        logger.warning(
                            f"Backup data validation failed: {validation_errors}"
                        )
                        continue

                    backup = AcronisBackup.from_dict(transformed_backup)
                    backup_dict = backup.to_dict()
                    processed_workload["backups"].append(backup_dict)
                    all_backups.append(backup_dict)

                except Exception as e:
                    logger.warning(f"Failed to process backup data: {e}")
                    continue

            processed_data["workload_data"][workload_id] = processed_workload

        # Create overall statistics
        if all_backups:
            statistics = create_backup_statistics(all_backups)
            processed_data["statistics"] = statistics.to_dict()

        return jsonify(create_success_response(processed_data))

    except AcronisConnectionError as e:
        return create_error_response(
            f"Connection failed: {str(e)}", 503, error_code="ACRONIS_CONNECTION_ERROR"
        )
    except AcronisAuthenticationError as e:
        return create_error_response(
            f"Authentication failed: {str(e)}", 401, error_code="ACRONIS_AUTH_ERROR"
        )
    except Exception as e:
        logger.exception("Failed to get Acronis backup information")
        return create_error_response(f"Failed to get backup information: {str(e)}", 500)


@acronis_bp.route("/agent/<agent_id>/backups", methods=["GET"])
def get_agent_backups(agent_id: str):
    """Get backup information for a specific agent."""
    try:
        client = create_client_from_config()
        if not client:
            return create_error_response(
                "Acronis not configured. Please configure API credentials first.",
                400,
                error_code="ACRONIS_NOT_CONFIGURED",
            )

        # First, get all associations to find workloads for this agent
        associations = client.association_workload_agent()
        if associations is None:
            return create_error_response(
                "Failed to fetch associations from Acronis API",
                503,
                error_code="ACRONIS_API_ERROR",
            )

        # Find workloads associated with this agent
        agent_workloads = [
            assoc["workload_id"]
            for assoc in associations
            if assoc.get("agent_id") == agent_id
        ]

        if not agent_workloads:
            return jsonify(
                create_success_response(
                    {
                        "agent_id": agent_id,
                        "backups": [],
                        "statistics": BackupStatistics(0, 0, 0).to_dict(),
                        "message": "No workloads found for this agent",
                    }
                )
            )

        # Get backup information for each workload
        all_backups = []
        workload_data = {}

        for workload_id in agent_workloads:
            backup_info = client.backup_info_workload(workload_id)
            if backup_info:
                workload_data[workload_id] = backup_info

                for backup_data_item in backup_info.get("backups", []):
                    try:
                        transformed_backup = transform_backup_data(backup_data_item)
                        validation_errors = validate_backup_data(transformed_backup)

                        if validation_errors:
                            logger.warning(
                                f"Backup data validation failed: {validation_errors}"
                            )
                            continue

                        backup = AcronisBackup.from_dict(transformed_backup)
                        all_backups.append(backup.to_dict())

                    except Exception as e:
                        logger.warning(f"Failed to process backup data: {e}")
                        continue

        # Create statistics
        statistics = create_backup_statistics(all_backups)

        return jsonify(
            create_success_response(
                {
                    "agent_id": agent_id,
                    "workload_data": workload_data,
                    "backups": all_backups,
                    "statistics": statistics.to_dict(),
                    "total_workloads": len(agent_workloads),
                }
            )
        )

    except AcronisConnectionError as e:
        return create_error_response(
            f"Connection failed: {str(e)}", 503, error_code="ACRONIS_CONNECTION_ERROR"
        )
    except AcronisAuthenticationError as e:
        return create_error_response(
            f"Authentication failed: {str(e)}", 401, error_code="ACRONIS_AUTH_ERROR"
        )
    except Exception as e:
        logger.exception(f"Failed to get backup information for agent {agent_id}")
        return create_error_response(
            f"Failed to get agent backup information: {str(e)}", 500
        )


# Connection Testing Route


@acronis_bp.route("/test-connection", methods=["POST"])
def test_connection():
    """Test connection to Acronis API with provided credentials."""
    try:
        data = request.get_json()
        if not data:
            return create_error_response(
                "No configuration data provided for connection test", 
                400,
                error_code="ACRONIS_NO_CONFIG_DATA"
            )

        # Validate required fields
        required_fields = ["base_url", "client_id", "client_secret"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return create_error_response(
                f"Missing required fields: {', '.join(missing_fields)}",
                400,
                error_code="ACRONIS_MISSING_FIELDS",
                details={"missing_fields": missing_fields}
            )

        # Create test client
        try:
            test_client = AcronisAPIClient(
                base_url=data["base_url"],
                client_id=data["client_id"],
                client_secret=data["client_secret"],
                grant_type=data.get("grant_type", "client_credentials"),
            )
        except Exception as e:
            return create_error_response(
                f"Failed to create API client: {str(e)}",
                400,
                error_code="ACRONIS_CLIENT_CREATION_ERROR"
            )

        # Test connection
        try:
            connection_result = test_client.test_connection()
            
            if connection_result:
                return jsonify(create_success_response(
                    {
                        "connection_status": "success",
                        "message": "Successfully connected to Acronis API",
                        "server_url": data["base_url"]
                    },
                    "Connection test successful"
                ))
            else:
                return create_error_response(
                    "Connection test failed - unable to authenticate with Acronis API",
                    401,
                    error_code="ACRONIS_CONNECTION_TEST_FAILED",
                    help_text="Please verify your API credentials and server URL"
                )
                
        except AcronisAuthenticationError as e:
            return create_error_response(
                f"Authentication failed: {str(e)}",
                401,
                error_code="ACRONIS_AUTH_ERROR",
                help_text="Please check your Client ID and Client Secret"
            )
        except AcronisConnectionError as e:
            return create_error_response(
                f"Connection failed: {str(e)}",
                503,
                error_code="ACRONIS_CONNECTION_ERROR",
                help_text="Please check the Base URL and network connectivity"
            )
        except Exception as e:
            return create_error_response(
                f"Connection test error: {str(e)}",
                500,
                error_code="ACRONIS_TEST_ERROR"
            )

    except Exception as e:
        logger.exception("Connection test failed")
        return create_error_response(
            f"Connection test failed: {str(e)}", 
            500,
            error_code="ACRONIS_TEST_INTERNAL_ERROR"
        )


# Health Check Route


@acronis_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for the Acronis API."""
    try:
        config_manager = AcronisConfigManager()
        config = config_manager.get_config()

        health_data = {
            "status": "healthy",
            "configured": bool(config),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        # Test API connection if configured
        if config:
            try:
                client = create_client_from_config()
                if client and client.test_connection():
                    health_data["api_connection"] = "connected"
                    health_data["connection_message"] = "Successfully connected to Acronis API"
                else:
                    health_data["api_connection"] = "failed"
                    health_data["connection_message"] = "Failed to connect to Acronis API"
                    health_data["status"] = "degraded"
            except AcronisAuthenticationError as e:
                health_data["api_connection"] = "authentication_failed"
                health_data["connection_message"] = f"Authentication failed: {str(e)}"
                health_data["status"] = "degraded"
            except AcronisConnectionError as e:
                health_data["api_connection"] = "connection_failed"
                health_data["connection_message"] = f"Connection failed: {str(e)}"
                health_data["status"] = "degraded"
            except Exception as e:
                health_data["api_connection"] = "error"
                health_data["connection_message"] = f"Connection error: {str(e)}"
                health_data["status"] = "degraded"
        else:
            health_data["api_connection"] = "not_configured"
            health_data["connection_message"] = "Acronis API not configured"

        return jsonify(create_success_response(health_data))

    except Exception as e:
        logger.exception("Health check failed")
        return create_error_response(f"Health check failed: {str(e)}", 500)


# Error Handlers


@acronis_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return create_error_response("Bad request", 400)


@acronis_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return create_error_response("Resource not found", 404)


@acronis_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return create_error_response("Internal server error", 500)
