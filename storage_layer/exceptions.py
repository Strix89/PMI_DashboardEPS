"""
Custom exception hierarchy for Infrastructure Monitoring Storage Layer

This module defines all custom exceptions used throughout the storage system,
providing specific error types for different failure scenarios with detailed
context information for debugging and error handling.
"""

from typing import Optional, Dict, Any


class StorageManagerError(Exception):
    """
    Base exception class for all StorageManager-related errors.
    
    This is the root exception that all other storage-related exceptions inherit from.
    It provides a common interface for error handling and includes context information
    to help with debugging and error reporting.
    
    Attributes:
        message: Human-readable error message
        context: Additional context information about the error
        original_error: The original exception that caused this error (if any)
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 original_error: Optional[Exception] = None) -> None:
        """
        Initialize the StorageManagerError.
        
        Args:
            message: Human-readable error message
            context: Additional context information about the error
            original_error: The original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error
    
    def __str__(self) -> str:
        """Return a detailed string representation of the error."""
        error_str = self.message
        
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            error_str += f" (Context: {context_str})"
        
        if self.original_error:
            error_str += f" (Caused by: {type(self.original_error).__name__}: {self.original_error})"
        
        return error_str
    
    def add_context(self, key: str, value: Any) -> None:
        """Add additional context information to the error."""
        self.context[key] = value


class ConnectionError(StorageManagerError):
    """
    Exception raised for MongoDB connection-related errors.
    
    This exception is raised when there are issues establishing, maintaining,
    or using MongoDB connections. It includes specific information about
    connection parameters and failure reasons.
    """
    
    def __init__(self, message: str, connection_string: Optional[str] = None,
                 database_name: Optional[str] = None, 
                 original_error: Optional[Exception] = None) -> None:
        """
        Initialize the ConnectionError.
        
        Args:
            message: Human-readable error message
            connection_string: MongoDB connection string (sanitized)
            database_name: Name of the database being accessed
            original_error: The original exception that caused this error
        """
        context = {}
        if connection_string:
            # Sanitize connection string to remove credentials
            sanitized_conn = self._sanitize_connection_string(connection_string)
            context["connection_string"] = sanitized_conn
        if database_name:
            context["database_name"] = database_name
        
        super().__init__(message, context, original_error)
    
    @staticmethod
    def _sanitize_connection_string(conn_str: str) -> str:
        """
        Remove credentials from connection string for safe logging.
        
        Args:
            conn_str: Original connection string
            
        Returns:
            Sanitized connection string with credentials removed
        """
        import re
        # Replace username:password@ with ***:***@
        sanitized = re.sub(r'://([^:]+):([^@]+)@', r'://***:***@', conn_str)
        return sanitized


class ValidationError(StorageManagerError):
    """
    Exception raised for data validation errors.
    
    This exception is raised when data fails validation checks, either at the
    model level or during database operations. It includes information about
    which fields failed validation and why.
    """
    
    def __init__(self, message: str, field_name: Optional[str] = None,
                 field_value: Optional[Any] = None, validation_rule: Optional[str] = None,
                 original_error: Optional[Exception] = None) -> None:
        """
        Initialize the ValidationError.
        
        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            field_value: Value that failed validation (will be truncated if too long)
            validation_rule: Description of the validation rule that failed
            original_error: The original exception that caused this error
        """
        context = {}
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            # Truncate long values for readability
            str_value = str(field_value)
            if len(str_value) > 100:
                str_value = str_value[:97] + "..."
            context["field_value"] = str_value
        if validation_rule:
            context["validation_rule"] = validation_rule
        
        super().__init__(message, context, original_error)


class OperationError(StorageManagerError):
    """
    Exception raised for database operation errors.
    
    This exception is raised when database operations fail due to issues
    other than connection or validation problems. This includes query errors,
    index issues, transaction failures, etc.
    """
    
    def __init__(self, message: str, operation: Optional[str] = None,
                 collection: Optional[str] = None, query: Optional[Dict[str, Any]] = None,
                 original_error: Optional[Exception] = None) -> None:
        """
        Initialize the OperationError.
        
        Args:
            message: Human-readable error message
            operation: Name of the operation that failed (e.g., 'insert', 'find', 'update')
            collection: Name of the collection being operated on
            query: Query or filter that was being executed (will be truncated if too long)
            original_error: The original exception that caused this error
        """
        context = {}
        if operation:
            context["operation"] = operation
        if collection:
            context["collection"] = collection
        if query:
            # Truncate long queries for readability
            query_str = str(query)
            if len(query_str) > 200:
                query_str = query_str[:197] + "..."
            context["query"] = query_str
        
        super().__init__(message, context, original_error)


class RetryExhaustedError(OperationError):
    """
    Exception raised when retry attempts are exhausted.
    
    This exception is raised when an operation fails repeatedly and all
    retry attempts have been exhausted. It includes information about
    the number of attempts made and the final error.
    """
    
    def __init__(self, message: str, attempts: int, max_attempts: int,
                 last_error: Optional[Exception] = None, operation: Optional[str] = None) -> None:
        """
        Initialize the RetryExhaustedError.
        
        Args:
            message: Human-readable error message
            attempts: Number of attempts made
            max_attempts: Maximum number of attempts allowed
            last_error: The last error that occurred before giving up
            operation: Name of the operation that was being retried
        """
        context = {
            "attempts": attempts,
            "max_attempts": max_attempts
        }
        
        super().__init__(message, operation=operation, original_error=last_error)
        self.add_context("attempts", attempts)
        self.add_context("max_attempts", max_attempts)


class ConfigurationError(StorageManagerError):
    """
    Exception raised for configuration-related errors.
    
    This exception is raised when there are issues with system configuration,
    such as missing required settings, invalid configuration values, or
    incompatible configuration combinations.
    """
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 config_value: Optional[Any] = None, expected_type: Optional[str] = None,
                 original_error: Optional[Exception] = None) -> None:
        """
        Initialize the ConfigurationError.
        
        Args:
            message: Human-readable error message
            config_key: Name of the configuration key that caused the error
            config_value: Value of the configuration that caused the error
            expected_type: Expected type or format for the configuration value
            original_error: The original exception that caused this error
        """
        context = {}
        if config_key:
            context["config_key"] = config_key
        if config_value is not None:
            context["config_value"] = str(config_value)
        if expected_type:
            context["expected_type"] = expected_type
        
        super().__init__(message, context, original_error)


# Convenience functions for creating common exceptions

def create_connection_error(message: str, connection_string: Optional[str] = None,
                          database_name: Optional[str] = None,
                          original_error: Optional[Exception] = None) -> ConnectionError:
    """
    Create a ConnectionError with standard formatting.
    
    Args:
        message: Error message
        connection_string: MongoDB connection string
        database_name: Database name
        original_error: Original exception
        
    Returns:
        Configured ConnectionError instance
    """
    return ConnectionError(message, connection_string, database_name, original_error)


def create_validation_error(message: str, field_name: Optional[str] = None,
                          field_value: Optional[Any] = None,
                          validation_rule: Optional[str] = None) -> ValidationError:
    """
    Create a ValidationError with standard formatting.
    
    Args:
        message: Error message
        field_name: Name of the field that failed validation
        field_value: Value that failed validation
        validation_rule: Description of the validation rule
        
    Returns:
        Configured ValidationError instance
    """
    return ValidationError(message, field_name, field_value, validation_rule)


def create_operation_error(message: str, operation: Optional[str] = None,
                         collection: Optional[str] = None,
                         original_error: Optional[Exception] = None) -> OperationError:
    """
    Create an OperationError with standard formatting.
    
    Args:
        message: Error message
        operation: Name of the operation that failed
        collection: Name of the collection
        original_error: Original exception
        
    Returns:
        Configured OperationError instance
    """
    return OperationError(message, operation, collection, original_error=original_error)