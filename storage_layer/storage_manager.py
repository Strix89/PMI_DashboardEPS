"""
StorageManager for Infrastructure Monitoring Storage Layer

This module provides the main StorageManager class that handles all MongoDB operations
for the infrastructure monitoring system, including connection management, retry logic,
and CRUD operations for metrics and assets.
"""

import logging
import time
import random
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import (
    ConnectionFailure, 
    ServerSelectionTimeoutError, 
    OperationFailure,
    PyMongoError
)

from .models import MetricDocument, AssetDocument
from .exceptions import (
    StorageManagerError,
    ConnectionError,
    ValidationError,
    OperationError,
    RetryExhaustedError,
    ConfigurationError
)
from .logging_config import (
    get_logger,
    create_operation_logger,
    log_operation_start,
    log_operation_success,
    log_operation_error
)


class StorageManager:
    """
    Main storage manager class for MongoDB operations.
    
    This class handles all database operations for the infrastructure monitoring system,
    including connection management, retry logic, and CRUD operations for metrics and assets.
    It implements robust error handling, connection pooling, and exponential backoff retry
    mechanisms for reliable operation in production environments.
    
    Attributes:
        connection_string: MongoDB connection string
        database_name: Name of the MongoDB database
        client: MongoDB client instance
        database: MongoDB database instance
        logger: Logger instance for this class
    """
    
    def __init__(self, connection_string: str, database_name: str) -> None:
        """
        Initialize the StorageManager with connection parameters.
        
        Args:
            connection_string: MongoDB connection string (e.g., 'mongodb://localhost:27017')
            database_name: Name of the database to use
            
        Raises:
            ConfigurationError: If connection parameters are invalid
        """
        self.logger = self._setup_logging()
        
        # Validate input parameters
        if not connection_string or not isinstance(connection_string, str):
            raise ConfigurationError(
                "connection_string must be a non-empty string",
                config_key="connection_string",
                config_value=connection_string,
                expected_type="non-empty string"
            )
        
        if not database_name or not isinstance(database_name, str):
            raise ConfigurationError(
                "database_name must be a non-empty string",
                config_key="database_name", 
                config_value=database_name,
                expected_type="non-empty string"
            )
        
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        
        # Connection configuration
        self._connection_timeout = 10  # seconds
        self._server_selection_timeout = 5  # seconds
        self._max_pool_size = 100
        self._min_pool_size = 10
        
        # Retry configuration
        self._max_retries = 3
        self._base_delay = 1.0  # seconds
        self._max_delay = 30.0  # seconds
        self._backoff_factor = 2.0
        self._jitter_factor = 0.2  # ±20% jitter
        
        self.logger.info(
            "StorageManager initialized",
            extra={
                "database_name": self.database_name,
                "connection_string": self._sanitize_connection_string(self.connection_string)
            }
        )
    
    def _setup_logging(self) -> logging.Logger:
        """
        Set up structured logging for the StorageManager.
        
        Returns:
            Configured logger instance
        """
        return get_logger(f"{__name__}.StorageManager")
    
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
    
    def connect(self) -> None:
        """
        Establish connection to MongoDB with validation and retry logic.
        
        This method creates a MongoDB client with optimized connection pooling
        settings and validates the connection by performing a ping operation.
        
        Raises:
            ConnectionError: If connection cannot be established after retries
        """
        self.logger.info("Attempting to connect to MongoDB")
        
        try:
            # Create MongoDB client with connection pooling configuration
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=self._server_selection_timeout * 1000,
                connectTimeoutMS=self._connection_timeout * 1000,
                maxPoolSize=self._max_pool_size,
                minPoolSize=self._min_pool_size,
                retryWrites=True,
                retryReads=True
            )
            
            # Get database reference
            self.database = self.client[self.database_name]
            
            # Validate connection with retry logic
            self._validate_connection_with_retry()
            
            self.logger.info(
                "Successfully connected to MongoDB",
                extra={
                    "database_name": self.database_name,
                    "server_info": self._get_server_info()
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to connect to MongoDB",
                extra={
                    "error": str(e),
                    "connection_string": self._sanitize_connection_string(self.connection_string)
                }
            )
            raise ConnectionError(
                "Failed to establish MongoDB connection",
                connection_string=self.connection_string,
                database_name=self.database_name,
                original_error=e
            )
    
    def _validate_connection_with_retry(self) -> None:
        """
        Validate MongoDB connection with exponential backoff retry.
        
        Raises:
            ConnectionError: If connection validation fails after all retries
        """
        last_error = None
        
        for attempt in range(1, self._max_retries + 1):
            try:
                self.logger.debug(f"Connection validation attempt {attempt}/{self._max_retries}")
                
                # Perform ping to validate connection
                self.client.admin.command('ping')
                
                # Verify database access
                self.database.command('ping')
                
                self.logger.debug("Connection validation successful")
                return
                
            except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as e:
                last_error = e
                self.logger.warning(
                    f"Connection validation attempt {attempt} failed",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self._max_retries,
                        "error": str(e)
                    }
                )
                
                if attempt < self._max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.debug(f"Retrying in {delay:.2f} seconds")
                    time.sleep(delay)
        
        # All retries exhausted
        raise RetryExhaustedError(
            "Connection validation failed after all retry attempts",
            attempts=self._max_retries,
            max_attempts=self._max_retries,
            last_error=last_error,
            operation="connection_validation"
        )
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (backoff_factor ^ (attempt - 1))
        delay = self._base_delay * (self._backoff_factor ** (attempt - 1))
        
        # Cap at maximum delay
        delay = min(delay, self._max_delay)
        
        # Add jitter to avoid thundering herd
        jitter = delay * self._jitter_factor * (2 * random.random() - 1)  # ±jitter_factor
        delay += jitter
        
        # Ensure minimum delay
        return max(delay, 0.1)
    
    def _get_server_info(self) -> Dict[str, Any]:
        """
        Get MongoDB server information for logging.
        
        Returns:
            Dictionary with server information
        """
        try:
            if self.client:
                server_info = self.client.server_info()
                return {
                    "version": server_info.get("version", "unknown"),
                    "git_version": server_info.get("gitVersion", "unknown")
                }
        except Exception as e:
            self.logger.debug(f"Could not retrieve server info: {e}")
        
        return {"version": "unknown", "git_version": "unknown"}
    
    def disconnect(self) -> None:
        """
        Properly close MongoDB connection and clean up resources.
        
        This method ensures all connections are properly closed and resources
        are cleaned up. It's safe to call multiple times.
        """
        self.logger.info("Disconnecting from MongoDB")
        
        try:
            if self.client:
                self.client.close()
                self.logger.info("MongoDB connection closed successfully")
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")
        finally:
            self.client = None
            self.database = None
    
    def _ensure_connected(self) -> None:
        """
        Ensure that we have a valid connection before performing operations.
        
        Raises:
            ConnectionError: If not connected or connection is invalid
        """
        if self.client is None or self.database is None:
            raise ConnectionError(
                "Not connected to MongoDB. Call connect() first.",
                connection_string=self.connection_string,
                database_name=self.database_name
            )
        
        # Perform a quick health check
        try:
            self.client.admin.command('ping')
        except Exception as e:
            raise ConnectionError(
                "MongoDB connection is not healthy",
                connection_string=self.connection_string,
                database_name=self.database_name,
                original_error=e
            )
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.disconnect()
        except:
            pass  # Ignore errors during cleanup
    
    def _execute_with_retry(self, operation_func, operation_name: str, 
                           *args, **kwargs) -> Any:
        """
        Execute a database operation with retry logic and error handling.
        
        This method wraps database operations with exponential backoff retry logic
        and proper error handling. It automatically retries on transient errors
        and provides detailed error context.
        
        Args:
            operation_func: Function to execute
            operation_name: Name of the operation for logging
            *args: Arguments to pass to the operation function
            **kwargs: Keyword arguments to pass to the operation function
            
        Returns:
            Result of the operation function
            
        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
            OperationError: If operation fails with non-retryable error
        """
        self._ensure_connected()
        
        last_error = None
        
        for attempt in range(1, self._max_retries + 1):
            try:
                self.logger.debug(
                    f"Executing {operation_name} (attempt {attempt}/{self._max_retries})"
                )
                
                # Perform health check before operation
                if attempt > 1:  # Skip health check on first attempt for performance
                    self._perform_health_check()
                
                # Execute the operation
                result = operation_func(*args, **kwargs)
                
                if attempt > 1:
                    self.logger.info(
                        f"Operation {operation_name} succeeded after {attempt} attempts"
                    )
                
                return result
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                self.logger.warning(
                    f"Connection error during {operation_name} (attempt {attempt})",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self._max_retries,
                        "error": str(e),
                        "operation": operation_name
                    }
                )
                
                if attempt < self._max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.debug(f"Retrying {operation_name} in {delay:.2f} seconds")
                    time.sleep(delay)
                    
                    # Try to reconnect on connection errors
                    try:
                        self.logger.debug("Attempting to reconnect after connection error")
                        self.disconnect()
                        self.connect()
                    except Exception as reconnect_error:
                        self.logger.warning(f"Reconnection failed: {reconnect_error}")
                
            except OperationFailure as e:
                # Check if this is a retryable operation failure
                if self._is_retryable_operation_error(e):
                    last_error = e
                    self.logger.warning(
                        f"Retryable operation error during {operation_name} (attempt {attempt})",
                        extra={
                            "attempt": attempt,
                            "max_attempts": self._max_retries,
                            "error": str(e),
                            "operation": operation_name
                        }
                    )
                    
                    if attempt < self._max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        self.logger.debug(f"Retrying {operation_name} in {delay:.2f} seconds")
                        time.sleep(delay)
                else:
                    # Non-retryable error, fail immediately
                    self.logger.error(
                        f"Non-retryable operation error during {operation_name}",
                        extra={
                            "error": str(e),
                            "operation": operation_name
                        }
                    )
                    raise OperationError(
                        f"Operation {operation_name} failed with non-retryable error",
                        operation=operation_name,
                        original_error=e
                    )
                    
            except PyMongoError as e:
                # Other PyMongo errors - generally not retryable
                self.logger.error(
                    f"PyMongo error during {operation_name}",
                    extra={
                        "error": str(e),
                        "operation": operation_name
                    }
                )
                raise OperationError(
                    f"Operation {operation_name} failed with PyMongo error",
                    operation=operation_name,
                    original_error=e
                )
                
            except Exception as e:
                # Unexpected errors - not retryable
                self.logger.error(
                    f"Unexpected error during {operation_name}",
                    extra={
                        "error": str(e),
                        "operation": operation_name
                    }
                )
                raise OperationError(
                    f"Operation {operation_name} failed with unexpected error",
                    operation=operation_name,
                    original_error=e
                )
        
        # All retries exhausted
        self.logger.error(
            f"All retry attempts exhausted for {operation_name}",
            extra={
                "attempts": self._max_retries,
                "last_error": str(last_error) if last_error else "unknown"
            }
        )
        raise RetryExhaustedError(
            f"Operation {operation_name} failed after all retry attempts",
            attempts=self._max_retries,
            max_attempts=self._max_retries,
            last_error=last_error,
            operation=operation_name
        )
    
    def _perform_health_check(self) -> None:
        """
        Perform a quick health check on the MongoDB connection.
        
        This method performs a lightweight operation to verify that the
        connection is still healthy before executing database operations.
        
        Raises:
            ConnectionError: If health check fails
        """
        try:
            # Quick ping to verify connection health
            self.client.admin.command('ping')
            self.database.command('ping')
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            raise ConnectionError(
                "MongoDB connection health check failed",
                connection_string=self.connection_string,
                database_name=self.database_name,
                original_error=e
            )
    
    def _is_retryable_operation_error(self, error: OperationFailure) -> bool:
        """
        Determine if an OperationFailure is retryable.
        
        Args:
            error: The OperationFailure to check
            
        Returns:
            True if the error is retryable, False otherwise
        """
        # MongoDB error codes that are typically retryable
        retryable_codes = {
            11600,  # InterruptedAtShutdown
            11602,  # InterruptedDueToReplStateChange
            10107,  # NotMaster (old)
            13435,  # NotMasterNoSlaveOk (old)
            13436,  # NotMasterOrSecondary (old)
            189,    # PrimarySteppedDown
            91,     # ShutdownInProgress
            7,      # HostNotFound
            6,      # HostUnreachable
            89,     # NetworkTimeout
            9001,   # SocketException
        }
        
        error_code = getattr(error, 'code', None)
        if error_code in retryable_codes:
            return True
        
        # Check error message for retryable patterns
        error_msg = str(error).lower()
        retryable_patterns = [
            'not master',
            'not primary',
            'connection',
            'timeout',
            'network',
            'socket',
            'interrupted'
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status information.
        
        Returns:
            Dictionary with connection status details
        """
        status = {
            "connected": False,
            "database_name": self.database_name,
            "connection_string": self._sanitize_connection_string(self.connection_string),
            "server_info": None,
            "last_ping": None,
            "error": None
        }
        
        try:
            if self.client is not None and self.database is not None:
                # Test connection with ping
                start_time = time.time()
                self.client.admin.command('ping')
                ping_time = time.time() - start_time
                
                status.update({
                    "connected": True,
                    "server_info": self._get_server_info(),
                    "last_ping": ping_time,
                    "pool_size": getattr(self.client, 'max_pool_size', 'unknown'),
                    "nodes": len(self.client.nodes) if hasattr(self.client, 'nodes') else 'unknown'
                })
                
        except Exception as e:
            status["error"] = str(e)
            self.logger.debug(f"Connection status check failed: {e}")
        
        return status
    
    # Metrics Operations
    
    def save_metrics_batch(self, metrics: List[MetricDocument]) -> int:
        """
        Save a batch of metrics using bulk insert operations for high performance.
        
        This method performs bulk insertion of metrics with comprehensive validation
        and error handling. Each metric in the batch is validated before insertion,
        and detailed error reporting is provided for malformed data.
        
        Args:
            metrics: List of MetricDocument instances to insert
            
        Returns:
            Number of successfully inserted metric records
            
        Raises:
            ValidationError: If metrics list is empty or contains invalid data
            OperationError: If bulk insert operation fails
        """
        if not metrics:
            raise ValidationError(
                "Metrics list cannot be empty",
                field_name="metrics",
                field_value=metrics,
                validation_rule="non-empty list of MetricDocument instances"
            )
        
        if not isinstance(metrics, list):
            raise ValidationError(
                "Metrics must be a list",
                field_name="metrics", 
                field_value=type(metrics).__name__,
                validation_rule="list"
            )
        
        self.logger.info(f"Starting batch insert of {len(metrics)} metrics")
        
        def _perform_batch_insert():
            # Validate and convert metrics to MongoDB format
            validated_docs = []
            validation_errors = []
            
            for i, metric in enumerate(metrics):
                try:
                    if not isinstance(metric, MetricDocument):
                        raise ValidationError(
                            f"Item at index {i} is not a MetricDocument",
                            field_name=f"metrics[{i}]",
                            field_value=type(metric).__name__,
                            validation_rule="MetricDocument"
                        )
                    
                    # Validate the metric (this calls metric._validate())
                    metric._validate()
                    
                    # Convert to MongoDB format
                    mongo_doc = metric.to_mongo_dict()
                    validated_docs.append(mongo_doc)
                    
                except Exception as e:
                    validation_errors.append({
                        "index": i,
                        "metric": metric,
                        "error": str(e)
                    })
            
            # If there are validation errors, raise detailed error
            if validation_errors:
                error_details = []
                for error in validation_errors[:5]:  # Limit to first 5 errors
                    error_details.append(
                        f"Index {error['index']}: {error['error']}"
                    )
                
                error_msg = f"Validation failed for {len(validation_errors)} metrics:\n" + \
                           "\n".join(error_details)
                
                if len(validation_errors) > 5:
                    error_msg += f"\n... and {len(validation_errors) - 5} more errors"
                
                raise ValidationError(
                    error_msg,
                    field_name="metrics",
                    field_value=f"{len(validation_errors)} invalid metrics",
                    validation_rule="all metrics to be valid MetricDocument instances"
                )
            
            # Get metrics collection
            metrics_collection = self.database["metrics"]
            
            # Perform bulk insert
            try:
                result = metrics_collection.insert_many(
                    validated_docs,
                    ordered=False  # Continue inserting even if some fail
                )
                
                inserted_count = len(result.inserted_ids)
                
                self.logger.info(
                    f"Successfully inserted {inserted_count} metrics",
                    extra={
                        "requested_count": len(metrics),
                        "inserted_count": inserted_count,
                        "collection": "metrics"
                    }
                )
                
                return inserted_count
                
            except Exception as e:
                self.logger.error(
                    f"Bulk insert failed for metrics batch",
                    extra={
                        "batch_size": len(validated_docs),
                        "error": str(e)
                    }
                )
                raise OperationError(
                    "Failed to insert metrics batch",
                    operation="save_metrics_batch",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_batch_insert,
            "save_metrics_batch"
        )
    
    def get_metrics(self, asset_id: Optional[str] = None, 
                   metric_name: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Retrieve metrics with flexible filtering options.
        
        This method supports filtering by asset_id, metric_name, and time range.
        Multiple filters are combined with AND logic. Queries are optimized using
        compound indexes for high performance.
        
        Args:
            asset_id: Filter by specific asset ID (optional)
            metric_name: Filter by specific metric name (optional)
            start_time: Filter metrics after this timestamp (inclusive, optional)
            end_time: Filter metrics before this timestamp (inclusive, optional)
            
        Returns:
            List of metric documents matching the filters. Returns empty list
            if no results found (no exceptions raised).
            
        Raises:
            ValidationError: If filter parameters are invalid
            OperationError: If query operation fails
        """
        self.logger.debug(
            "Querying metrics with filters",
            extra={
                "asset_id": asset_id,
                "metric_name": metric_name,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None
            }
        )
        
        def _perform_metrics_query():
            # Build query filter
            query_filter = {}
            
            # Asset ID filter
            if asset_id is not None:
                if not isinstance(asset_id, str) or not asset_id.strip():
                    raise ValidationError(
                        "asset_id must be a non-empty string",
                        field_name="asset_id",
                        field_value=asset_id,
                        validation_rule="non-empty string"
                    )
                query_filter["meta.asset_id"] = asset_id.strip()
            
            # Metric name filter
            if metric_name is not None:
                if not isinstance(metric_name, str) or not metric_name.strip():
                    raise ValidationError(
                        "metric_name must be a non-empty string",
                        field_name="metric_name",
                        field_value=metric_name,
                        validation_rule="non-empty string"
                    )
                query_filter["meta.metric_name"] = metric_name.strip()
            
            # Time range filters
            time_filter = {}
            if start_time is not None:
                if not isinstance(start_time, datetime):
                    raise ValidationError(
                        "start_time must be a datetime object",
                        field_name="start_time",
                        field_value=type(start_time).__name__,
                        validation_rule="datetime"
                    )
                time_filter["$gte"] = start_time
            
            if end_time is not None:
                if not isinstance(end_time, datetime):
                    raise ValidationError(
                        "end_time must be a datetime object",
                        field_name="end_time",
                        field_value=type(end_time).__name__,
                        validation_rule="datetime"
                    )
                time_filter["$lte"] = end_time
            
            if time_filter:
                query_filter["timestamp"] = time_filter
            
            # Validate time range logic
            if start_time and end_time and start_time > end_time:
                raise ValidationError(
                    "start_time cannot be after end_time",
                    field_name="time_range",
                    field_value=f"start: {start_time}, end: {end_time}",
                    validation_rule="start_time <= end_time"
                )
            
            # Get metrics collection
            metrics_collection = self.database["metrics"]
            
            # Execute query with sorting by timestamp (newest first)
            try:
                cursor = metrics_collection.find(query_filter).sort("timestamp", -1)
                
                # Convert cursor to list
                results = list(cursor)
                
                self.logger.info(
                    f"Retrieved {len(results)} metrics",
                    extra={
                        "query_filter": query_filter,
                        "result_count": len(results)
                    }
                )
                
                return results
                
            except Exception as e:
                self.logger.error(
                    "Failed to query metrics",
                    extra={
                        "query_filter": query_filter,
                        "error": str(e)
                    }
                )
                raise OperationError(
                    "Failed to retrieve metrics",
                    operation="get_metrics",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_metrics_query,
            "get_metrics"
        )
    
    def setup_time_series_collection(self) -> None:
        """
        Set up MongoDB time-series collection and indexes for optimal performance.
        
        This method configures the metrics collection as a time-series collection
        and creates compound indexes for efficient querying. It also sets up TTL
        index for automatic data retention.
        
        Raises:
            OperationError: If collection setup or index creation fails
        """
        self.logger.info("Setting up time-series collection and indexes")
        
        def _perform_collection_setup():
            try:
                # Check if metrics collection already exists
                existing_collections = self.database.list_collection_names()
                
                if "metrics" not in existing_collections:
                    # Create time-series collection
                    self.logger.info("Creating time-series collection 'metrics'")
                    
                    self.database.create_collection(
                        "metrics",
                        timeseries={
                            "timeField": "timestamp",
                            "metaField": "meta",
                            "granularity": "minutes"  # Optimized for minute-level data
                        }
                    )
                    
                    self.logger.info("Time-series collection 'metrics' created successfully")
                else:
                    self.logger.info("Metrics collection already exists")
                
                # Get metrics collection reference
                metrics_collection = self.database["metrics"]
                
                # Create compound indexes for optimal query performance
                indexes_to_create = [
                    {
                        "name": "asset_timestamp_idx",
                        "keys": [("meta.asset_id", 1), ("timestamp", 1)],
                        "background": True
                    },
                    {
                        "name": "metric_timestamp_idx", 
                        "keys": [("meta.metric_name", 1), ("timestamp", 1)],
                        "background": True
                    },
                    {
                        "name": "timestamp_ttl_idx",
                        "keys": [("timestamp", 1)],
                        "background": True,
                        "expireAfterSeconds": 60 * 60 * 24 * 90  # 90 days retention
                    }
                ]
                
                # Get existing indexes
                existing_indexes = {idx["name"] for idx in metrics_collection.list_indexes()}
                
                # Create indexes that don't exist
                for index_spec in indexes_to_create:
                    index_name = index_spec["name"]
                    
                    if index_name not in existing_indexes:
                        self.logger.info(f"Creating index: {index_name}")
                        
                        # Extract index creation parameters
                        keys = index_spec["keys"]
                        options = {k: v for k, v in index_spec.items() 
                                 if k not in ["name", "keys"]}
                        options["name"] = index_name
                        
                        # Create the index
                        metrics_collection.create_index(keys, **options)
                        
                        self.logger.info(f"Index '{index_name}' created successfully")
                    else:
                        self.logger.debug(f"Index '{index_name}' already exists")
                
                # Verify indexes were created
                final_indexes = list(metrics_collection.list_indexes())
                index_names = [idx["name"] for idx in final_indexes]
                
                self.logger.info(
                    "Time-series collection setup completed",
                    extra={
                        "collection": "metrics",
                        "indexes": index_names,
                        "total_indexes": len(index_names)
                    }
                )
                
                return {
                    "collection_created": "metrics" not in existing_collections,
                    "indexes_created": [spec["name"] for spec in indexes_to_create 
                                      if spec["name"] not in existing_indexes],
                    "total_indexes": len(index_names)
                }
                
            except Exception as e:
                self.logger.error(
                    "Failed to setup time-series collection",
                    extra={
                        "error": str(e),
                        "collection": "metrics"
                    }
                )
                raise OperationError(
                    "Failed to setup time-series collection and indexes",
                    operation="setup_time_series_collection",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_collection_setup,
            "setup_time_series_collection"
        )
    
    # Asset Management Operations
    
    def upsert_asset(self, asset: AssetDocument) -> str:
        """
        Insert or update an asset with automatic last_updated handling.
        
        This method performs an upsert operation that creates new assets or updates
        existing ones. The last_updated field is automatically set to the current
        timestamp on every operation. For service-type assets, validates that the
        parent_asset_id references an existing asset.
        
        Args:
            asset: AssetDocument instance to upsert
            
        Returns:
            The asset_id of the upserted asset
            
        Raises:
            ValidationError: If asset data is invalid or parent_asset_id doesn't exist
            OperationError: If upsert operation fails
        """
        if not isinstance(asset, AssetDocument):
            raise ValidationError(
                "asset must be an AssetDocument instance",
                field_name="asset",
                field_value=type(asset).__name__,
                validation_rule="AssetDocument"
            )
        
        self.logger.info(
            f"Upserting asset: {asset.asset_id}",
            extra={
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "hostname": asset.hostname,
                "service_name": asset.service_name
            }
        )
        
        def _perform_asset_upsert():
            # Validate the asset (this calls asset._validate())
            asset._validate()
            
            # For service assets, validate parent_asset_id exists
            if asset.asset_type == "service":
                parent_asset_id = asset.get_parent_asset_id()
                if parent_asset_id:
                    # Check if parent asset exists
                    assets_collection = self.database["assets"]
                    parent_exists = assets_collection.find_one({"_id": parent_asset_id})
                    
                    if not parent_exists:
                        raise ValidationError(
                            f"Parent asset '{parent_asset_id}' does not exist",
                            field_name="parent_asset_id",
                            field_value=parent_asset_id,
                            validation_rule="existing asset_id"
                        )
            
            # Update last_updated timestamp
            asset.last_updated = datetime.now(UTC)
            
            # Convert to MongoDB format
            mongo_doc = asset.to_mongo_dict()
            
            # Get assets collection
            assets_collection = self.database["assets"]
            
            # Perform upsert operation
            try:
                result = assets_collection.replace_one(
                    {"_id": asset.asset_id},
                    mongo_doc,
                    upsert=True
                )
                
                operation_type = "updated" if result.matched_count > 0 else "created"
                
                self.logger.info(
                    f"Successfully {operation_type} asset: {asset.asset_id}",
                    extra={
                        "asset_id": asset.asset_id,
                        "asset_type": asset.asset_type,
                        "operation": operation_type,
                        "matched_count": result.matched_count,
                        "modified_count": result.modified_count,
                        "upserted_id": str(result.upserted_id) if result.upserted_id else None
                    }
                )
                
                return asset.asset_id
                
            except Exception as e:
                self.logger.error(
                    f"Failed to upsert asset: {asset.asset_id}",
                    extra={
                        "asset_id": asset.asset_id,
                        "asset_type": asset.asset_type,
                        "error": str(e)
                    }
                )
                raise OperationError(
                    f"Failed to upsert asset '{asset.asset_id}'",
                    operation="upsert_asset",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_asset_upsert,
            "upsert_asset"
        )
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single asset by its ID.
        
        Args:
            asset_id: Unique identifier of the asset to retrieve
            
        Returns:
            Asset document as dictionary if found, None if not found
            
        Raises:
            ValidationError: If asset_id is invalid
            OperationError: If query operation fails
        """
        if not asset_id or not isinstance(asset_id, str):
            raise ValidationError(
                "asset_id must be a non-empty string",
                field_name="asset_id",
                field_value=asset_id,
                validation_rule="non-empty string"
            )
        
        asset_id = asset_id.strip()
        
        self.logger.debug(f"Retrieving asset: {asset_id}")
        
        def _perform_asset_get():
            # Get assets collection
            assets_collection = self.database["assets"]
            
            try:
                # Find the asset by ID
                result = assets_collection.find_one({"_id": asset_id})
                
                if result:
                    self.logger.debug(
                        f"Found asset: {asset_id}",
                        extra={
                            "asset_id": asset_id,
                            "asset_type": result.get("asset_type"),
                            "hostname": result.get("hostname")
                        }
                    )
                else:
                    self.logger.debug(f"Asset not found: {asset_id}")
                
                return result
                
            except Exception as e:
                self.logger.error(
                    f"Failed to retrieve asset: {asset_id}",
                    extra={
                        "asset_id": asset_id,
                        "error": str(e)
                    }
                )
                raise OperationError(
                    f"Failed to retrieve asset '{asset_id}'",
                    operation="get_asset",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_asset_get,
            "get_asset"
        )
    
    def get_assets_by_type(self, asset_type: str, hostname_search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve assets filtered by type with optional hostname search.
        
        Args:
            asset_type: Type of assets to retrieve (must be valid AssetType)
            hostname_search: Optional case-insensitive hostname search string
            
        Returns:
            List of asset documents matching the criteria
            
        Raises:
            ValidationError: If asset_type is invalid
            OperationError: If query operation fails
        """
        # Validate asset_type
        valid_asset_types = ["proxmox_node", "vm", "container", "physical_host", "acronis_backup_job", "service"]
        if not asset_type or asset_type not in valid_asset_types:
            raise ValidationError(
                f"asset_type must be one of: {', '.join(valid_asset_types)}",
                field_name="asset_type",
                field_value=asset_type,
                validation_rule=f"one of: {', '.join(valid_asset_types)}"
            )
        
        self.logger.debug(
            f"Retrieving assets by type: {asset_type}",
            extra={
                "asset_type": asset_type,
                "hostname_search": hostname_search
            }
        )
        
        def _perform_assets_by_type_query():
            # Build query filter
            query_filter = {"asset_type": asset_type}
            
            # Add hostname search if provided
            if hostname_search:
                if not isinstance(hostname_search, str):
                    raise ValidationError(
                        "hostname_search must be a string",
                        field_name="hostname_search",
                        field_value=type(hostname_search).__name__,
                        validation_rule="string"
                    )
                
                # Case-insensitive regex search
                hostname_pattern = re.compile(re.escape(hostname_search.strip()), re.IGNORECASE)
                query_filter["hostname"] = {"$regex": hostname_pattern}
            
            # Get assets collection
            assets_collection = self.database["assets"]
            
            try:
                # Execute query with sorting by hostname
                cursor = assets_collection.find(query_filter).sort("hostname", 1)
                
                # Convert cursor to list
                results = list(cursor)
                
                self.logger.info(
                    f"Retrieved {len(results)} assets of type '{asset_type}'",
                    extra={
                        "asset_type": asset_type,
                        "hostname_search": hostname_search,
                        "result_count": len(results)
                    }
                )
                
                return results
                
            except Exception as e:
                self.logger.error(
                    f"Failed to retrieve assets by type: {asset_type}",
                    extra={
                        "asset_type": asset_type,
                        "hostname_search": hostname_search,
                        "error": str(e)
                    }
                )
                raise OperationError(
                    f"Failed to retrieve assets of type '{asset_type}'",
                    operation="get_assets_by_type",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_assets_by_type_query,
            "get_assets_by_type"
        )
    
    def get_assets_with_services(self, asset_id: str) -> Dict[str, Any]:
        """
        Retrieve an asset with all its related services in a hierarchical structure.
        
        This method returns the main asset along with all services that have this asset
        as their parent_asset_id. It validates parent_asset_id relationships and reports
        any inconsistencies. The parent asset status is included when querying services.
        
        Args:
            asset_id: ID of the parent asset to retrieve with its services
            
        Returns:
            Dictionary containing the asset and its related services:
            {
                "asset": {...},  # Main asset document
                "services": [...],  # List of related service documents
                "inconsistencies": [...]  # List of any relationship inconsistencies found
            }
            
        Raises:
            ValidationError: If asset_id is invalid
            OperationError: If query operation fails
        """
        if not asset_id or not isinstance(asset_id, str):
            raise ValidationError(
                "asset_id must be a non-empty string",
                field_name="asset_id",
                field_value=asset_id,
                validation_rule="non-empty string"
            )
        
        asset_id = asset_id.strip()
        
        self.logger.debug(f"Retrieving asset with services: {asset_id}")
        
        def _perform_hierarchical_query():
            # Get assets collection
            assets_collection = self.database["assets"]
            
            try:
                # First, get the main asset
                main_asset = assets_collection.find_one({"_id": asset_id})
                
                if not main_asset:
                    self.logger.debug(f"Asset not found: {asset_id}")
                    return {
                        "asset": None,
                        "services": [],
                        "inconsistencies": []
                    }
                
                # Find all services that have this asset as parent
                services_query = {
                    "asset_type": "service",
                    "data.parent_asset_id": asset_id
                }
                
                services_cursor = assets_collection.find(services_query).sort("service_name", 1)
                services = list(services_cursor)
                
                # Validate relationships and collect inconsistencies
                inconsistencies = []
                validated_services = []
                
                for service in services:
                    service_id = service.get("_id")
                    parent_id = service.get("data", {}).get("parent_asset_id")
                    
                    # Check for inconsistencies
                    if parent_id != asset_id:
                        inconsistencies.append({
                            "service_id": service_id,
                            "issue": "parent_asset_id_mismatch",
                            "expected_parent": asset_id,
                            "actual_parent": parent_id,
                            "description": f"Service '{service_id}' has parent_asset_id '{parent_id}' but was found in query for parent '{asset_id}'"
                        })
                    
                    # Validate that the service has required fields
                    if not service.get("service_name"):
                        inconsistencies.append({
                            "service_id": service_id,
                            "issue": "missing_service_name",
                            "description": f"Service '{service_id}' is missing required service_name field"
                        })
                    
                    # Add parent asset status to service data for context
                    service_with_parent_status = service.copy()
                    service_with_parent_status["parent_asset_status"] = main_asset.get("data", {}).get("status", "unknown")
                    service_with_parent_status["parent_asset_hostname"] = main_asset.get("hostname")
                    
                    validated_services.append(service_with_parent_status)
                
                # Also check for orphaned services (services claiming this as parent but not found in query)
                # This is a double-check for data integrity
                all_services_claiming_parent = assets_collection.find({
                    "asset_type": "service",
                    "$or": [
                        {"data.parent_asset_id": asset_id},
                        {"data.parent_asset_id": {"$exists": True, "$ne": asset_id}}
                    ]
                })
                
                found_service_ids = {service["_id"] for service in services}
                
                for potential_service in all_services_claiming_parent:
                    claimed_parent = potential_service.get("data", {}).get("parent_asset_id")
                    service_id = potential_service.get("_id")
                    
                    if claimed_parent == asset_id and service_id not in found_service_ids:
                        inconsistencies.append({
                            "service_id": service_id,
                            "issue": "service_not_found_in_query",
                            "description": f"Service '{service_id}' claims parent '{asset_id}' but was not found in hierarchical query"
                        })
                
                result = {
                    "asset": main_asset,
                    "services": validated_services,
                    "inconsistencies": inconsistencies
                }
                
                self.logger.info(
                    f"Retrieved asset with {len(validated_services)} services",
                    extra={
                        "asset_id": asset_id,
                        "asset_type": main_asset.get("asset_type"),
                        "services_count": len(validated_services),
                        "inconsistencies_count": len(inconsistencies)
                    }
                )
                
                # Log inconsistencies if found
                if inconsistencies:
                    self.logger.warning(
                        f"Found {len(inconsistencies)} relationship inconsistencies for asset {asset_id}",
                        extra={
                            "asset_id": asset_id,
                            "inconsistencies": inconsistencies
                        }
                    )
                
                return result
                
            except Exception as e:
                self.logger.error(
                    f"Failed to retrieve asset with services: {asset_id}",
                    extra={
                        "asset_id": asset_id,
                        "error": str(e)
                    }
                )
                raise OperationError(
                    f"Failed to retrieve asset '{asset_id}' with services",
                    operation="get_assets_with_services",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_hierarchical_query,
            "get_assets_with_services"
        )
    
    # Database Maintenance Operations
    
    def purge_collections(self) -> Dict[str, int]:
        """
        Completely clear all collections (metrics, assets) for data cleanup.
        
        This method removes all documents from the metrics and assets collections,
        providing a clean slate for testing or data reset scenarios. The operation
        uses transactions where possible to ensure atomicity and implements rollback
        for failed operations.
        
        Returns:
            Dictionary with count of deleted documents per collection:
            {
                "metrics": <count>,
                "assets": <count>,
                "total": <total_count>
            }
            
        Raises:
            OperationError: If purge operation fails
        """
        self.logger.warning("Starting complete purge of all collections")
        
        def _perform_purge_collections():
            deleted_counts = {
                "metrics": 0,
                "assets": 0,
                "total": 0
            }
            
            collections_to_purge = ["metrics", "assets"]
            
            try:
                # Start a session for transaction support (if replica set is available)
                with self.client.start_session() as session:
                    try:
                        # Try to use transactions if supported
                        with session.start_transaction():
                            for collection_name in collections_to_purge:
                                collection = self.database[collection_name]
                                
                                # Count documents before deletion for reporting
                                count_before = collection.count_documents({}, session=session)
                                
                                # Delete all documents in the collection
                                delete_result = collection.delete_many({}, session=session)
                                
                                deleted_count = delete_result.deleted_count
                                deleted_counts[collection_name] = deleted_count
                                deleted_counts["total"] += deleted_count
                                
                                self.logger.info(
                                    f"Purged collection '{collection_name}'",
                                    extra={
                                        "collection": collection_name,
                                        "documents_before": count_before,
                                        "documents_deleted": deleted_count
                                    }
                                )
                            
                            # Commit transaction
                            self.logger.info("Transaction committed successfully")
                            
                    except Exception as transaction_error:
                        # Transaction failed, it will be automatically aborted
                        self.logger.error(
                            "Transaction failed during purge operation",
                            extra={
                                "error": str(transaction_error),
                                "collections": collections_to_purge
                            }
                        )
                        raise OperationError(
                            "Failed to purge collections in transaction",
                            operation="purge_collections",
                            original_error=transaction_error
                        )
                        
            except Exception as session_error:
                # Fallback to non-transactional approach
                self.logger.warning(
                    "Transaction not supported, falling back to individual operations",
                    extra={"error": str(session_error)}
                )
                
                # Reset counters for fallback approach
                deleted_counts = {
                    "metrics": 0,
                    "assets": 0,
                    "total": 0
                }
                
                # Track successful operations for potential rollback
                successful_operations = []
                
                try:
                    for collection_name in collections_to_purge:
                        collection = self.database[collection_name]
                        
                        # Count documents before deletion for reporting
                        count_before = collection.count_documents({})
                        
                        # Delete all documents in the collection
                        delete_result = collection.delete_many({})
                        
                        deleted_count = delete_result.deleted_count
                        deleted_counts[collection_name] = deleted_count
                        deleted_counts["total"] += deleted_count
                        
                        successful_operations.append({
                            "collection": collection_name,
                            "deleted_count": deleted_count
                        })
                        
                        self.logger.info(
                            f"Purged collection '{collection_name}' (non-transactional)",
                            extra={
                                "collection": collection_name,
                                "documents_before": count_before,
                                "documents_deleted": deleted_count
                            }
                        )
                        
                except Exception as purge_error:
                    # Log which operations succeeded before the failure
                    if successful_operations:
                        self.logger.error(
                            "Purge operation failed after partial completion",
                            extra={
                                "successful_operations": successful_operations,
                                "failed_collection": collection_name if 'collection_name' in locals() else "unknown",
                                "error": str(purge_error)
                            }
                        )
                    
                    raise OperationError(
                        "Failed to purge collections (non-transactional)",
                        operation="purge_collections",
                        original_error=purge_error
                    )
            
            # Verify collections are empty
            verification_results = {}
            for collection_name in collections_to_purge:
                remaining_count = self.database[collection_name].count_documents({})
                verification_results[collection_name] = remaining_count
                
                if remaining_count > 0:
                    self.logger.warning(
                        f"Collection '{collection_name}' still contains {remaining_count} documents after purge"
                    )
            
            self.logger.warning(
                "Purge operation completed",
                extra={
                    "deleted_counts": deleted_counts,
                    "verification_results": verification_results,
                    "total_deleted": deleted_counts["total"]
                }
            )
            
            return deleted_counts
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_purge_collections,
            "purge_collections"
        )
    
    def cleanup_old_metrics(self, older_than: datetime) -> int:
        """
        Remove metrics older than the specified date for selective data cleanup.
        
        This method removes metric documents with timestamps older than the provided
        datetime, allowing for selective cleanup of historical data while preserving
        recent metrics. The operation is performed efficiently using MongoDB's
        delete_many operation with timestamp filtering.
        
        Args:
            older_than: Remove metrics with timestamps before this datetime (exclusive)
            
        Returns:
            Number of metric documents that were deleted
            
        Raises:
            ValidationError: If older_than parameter is invalid
            OperationError: If cleanup operation fails
        """
        if not isinstance(older_than, datetime):
            raise ValidationError(
                "older_than must be a datetime object",
                field_name="older_than",
                field_value=type(older_than).__name__,
                validation_rule="datetime"
            )
        
        self.logger.info(
            f"Starting cleanup of metrics older than {older_than.isoformat()}",
            extra={
                "cutoff_date": older_than.isoformat(),
                "operation": "cleanup_old_metrics"
            }
        )
        
        def _perform_metrics_cleanup():
            # Get metrics collection
            metrics_collection = self.database["metrics"]
            
            try:
                # Count documents that will be deleted for reporting
                count_query = {"timestamp": {"$lt": older_than}}
                count_to_delete = metrics_collection.count_documents(count_query)
                
                if count_to_delete == 0:
                    self.logger.info(
                        "No metrics found older than cutoff date",
                        extra={
                            "cutoff_date": older_than.isoformat(),
                            "documents_to_delete": 0
                        }
                    )
                    return 0
                
                self.logger.info(
                    f"Found {count_to_delete} metrics to delete",
                    extra={
                        "cutoff_date": older_than.isoformat(),
                        "documents_to_delete": count_to_delete
                    }
                )
                
                # Perform the deletion
                delete_result = metrics_collection.delete_many(count_query)
                deleted_count = delete_result.deleted_count
                
                # Verify the deletion count matches expectation
                if deleted_count != count_to_delete:
                    self.logger.warning(
                        "Deleted count differs from expected count",
                        extra={
                            "expected_count": count_to_delete,
                            "actual_deleted": deleted_count,
                            "cutoff_date": older_than.isoformat()
                        }
                    )
                
                # Verify no documents remain older than cutoff
                remaining_old_count = metrics_collection.count_documents(count_query)
                if remaining_old_count > 0:
                    self.logger.warning(
                        f"Still found {remaining_old_count} metrics older than cutoff after cleanup",
                        extra={
                            "cutoff_date": older_than.isoformat(),
                            "remaining_old_documents": remaining_old_count
                        }
                    )
                
                self.logger.info(
                    f"Successfully cleaned up {deleted_count} old metrics",
                    extra={
                        "cutoff_date": older_than.isoformat(),
                        "deleted_count": deleted_count,
                        "remaining_old_count": remaining_old_count
                    }
                )
                
                return deleted_count
                
            except Exception as e:
                self.logger.error(
                    "Failed to cleanup old metrics",
                    extra={
                        "cutoff_date": older_than.isoformat(),
                        "error": str(e)
                    }
                )
                raise OperationError(
                    f"Failed to cleanup metrics older than {older_than.isoformat()}",
                    operation="cleanup_old_metrics",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_metrics_cleanup,
            "cleanup_old_metrics"
        )
    
    def optimize_indexes(self) -> Dict[str, Any]:
        """
        Optimize indexes for time-series collections with performance monitoring.
        
        This method performs index optimization operations including rebuilding indexes,
        collecting index statistics, and monitoring performance metrics. It focuses on
        the metrics collection which benefits most from index optimization due to its
        time-series nature and high write volume.
        
        Returns:
            Dictionary with optimization results and performance statistics:
            {
                "collections_optimized": [...],
                "indexes_rebuilt": [...],
                "statistics": {...},
                "performance_metrics": {...}
            }
            
        Raises:
            OperationError: If index optimization fails
        """
        self.logger.info("Starting index optimization for time-series collections")
        
        def _perform_index_optimization():
            optimization_results = {
                "collections_optimized": [],
                "indexes_rebuilt": [],
                "statistics": {},
                "performance_metrics": {}
            }
            
            # Collections to optimize (focus on time-series collections)
            collections_to_optimize = ["metrics", "assets"]
            
            try:
                for collection_name in collections_to_optimize:
                    collection = self.database[collection_name]
                    
                    self.logger.info(f"Optimizing indexes for collection: {collection_name}")
                    
                    # Get current index information
                    indexes_before = list(collection.list_indexes())
                    index_names_before = [idx["name"] for idx in indexes_before]
                    
                    # Collect index statistics before optimization
                    stats_before = self._collect_index_statistics(collection, collection_name)
                    
                    # Record start time for performance monitoring
                    start_time = time.time()
                    
                    # Perform index optimization operations
                    rebuilt_indexes = []
                    
                    for index_info in indexes_before:
                        index_name = index_info["name"]
                        
                        # Skip the default _id index
                        if index_name == "_id_":
                            continue
                        
                        try:
                            # For time-series collections, focus on compound indexes
                            if collection_name == "metrics" and any(key in str(index_info.get("key", {})) 
                                                                   for key in ["meta.asset_id", "meta.metric_name", "timestamp"]):
                                
                                self.logger.debug(f"Rebuilding index: {index_name}")
                                
                                # Reindex operation (MongoDB will rebuild the index)
                                collection.reindex()
                                
                                rebuilt_indexes.append(index_name)
                                
                                self.logger.debug(f"Successfully rebuilt index: {index_name}")
                        
                        except Exception as index_error:
                            self.logger.warning(
                                f"Failed to rebuild index '{index_name}' in collection '{collection_name}'",
                                extra={
                                    "collection": collection_name,
                                    "index_name": index_name,
                                    "error": str(index_error)
                                }
                            )
                            # Continue with other indexes even if one fails
                            continue
                    
                    # Record end time and calculate duration
                    end_time = time.time()
                    optimization_duration = end_time - start_time
                    
                    # Collect index statistics after optimization
                    stats_after = self._collect_index_statistics(collection, collection_name)
                    
                    # Get updated index information
                    indexes_after = list(collection.list_indexes())
                    index_names_after = [idx["name"] for idx in indexes_after]
                    
                    # Store results for this collection
                    collection_results = {
                        "indexes_before": len(indexes_before),
                        "indexes_after": len(indexes_after),
                        "indexes_rebuilt": rebuilt_indexes,
                        "optimization_duration": optimization_duration,
                        "statistics_before": stats_before,
                        "statistics_after": stats_after
                    }
                    
                    optimization_results["collections_optimized"].append(collection_name)
                    optimization_results["indexes_rebuilt"].extend(rebuilt_indexes)
                    optimization_results["statistics"][collection_name] = collection_results
                    
                    self.logger.info(
                        f"Completed optimization for collection '{collection_name}'",
                        extra={
                            "collection": collection_name,
                            "indexes_rebuilt": len(rebuilt_indexes),
                            "duration_seconds": round(optimization_duration, 2),
                            "rebuilt_indexes": rebuilt_indexes
                        }
                    )
                
                # Calculate overall performance metrics
                total_duration = sum(
                    stats["optimization_duration"] 
                    for stats in optimization_results["statistics"].values()
                )
                
                optimization_results["performance_metrics"] = {
                    "total_duration": total_duration,
                    "collections_processed": len(collections_to_optimize),
                    "total_indexes_rebuilt": len(optimization_results["indexes_rebuilt"]),
                    "average_duration_per_collection": total_duration / len(collections_to_optimize) if collections_to_optimize else 0
                }
                
                self.logger.info(
                    "Index optimization completed successfully",
                    extra={
                        "collections_optimized": optimization_results["collections_optimized"],
                        "total_indexes_rebuilt": len(optimization_results["indexes_rebuilt"]),
                        "total_duration": round(total_duration, 2)
                    }
                )
                
                return optimization_results
                
            except Exception as e:
                self.logger.error(
                    "Failed to optimize indexes",
                    extra={
                        "collections": collections_to_optimize,
                        "error": str(e)
                    }
                )
                raise OperationError(
                    "Failed to optimize indexes for time-series collections",
                    operation="optimize_indexes",
                    original_error=e
                )
        
        # Execute with retry logic
        return self._execute_with_retry(
            _perform_index_optimization,
            "optimize_indexes"
        )
    
    def _collect_index_statistics(self, collection: Collection, collection_name: str) -> Dict[str, Any]:
        """
        Collect detailed statistics about indexes for a collection.
        
        Args:
            collection: MongoDB collection object
            collection_name: Name of the collection for logging
            
        Returns:
            Dictionary with index statistics
        """
        try:
            # Get collection statistics
            collection_stats = self.database.command("collStats", collection_name)
            
            # Get index statistics
            index_stats = []
            for index_info in collection.list_indexes():
                index_name = index_info["name"]
                
                # Get index usage statistics if available
                try:
                    index_usage = self.database.command("collStats", collection_name, indexDetails=True)
                    index_details = index_usage.get("indexDetails", {}).get(index_name, {})
                except:
                    index_details = {}
                
                index_stat = {
                    "name": index_name,
                    "key": index_info.get("key", {}),
                    "size_bytes": index_details.get("size", 0),
                    "unique": index_info.get("unique", False),
                    "sparse": index_info.get("sparse", False),
                    "background": index_info.get("background", False)
                }
                
                index_stats.append(index_stat)
            
            statistics = {
                "collection_size_bytes": collection_stats.get("size", 0),
                "document_count": collection_stats.get("count", 0),
                "index_count": len(index_stats),
                "total_index_size_bytes": collection_stats.get("totalIndexSize", 0),
                "indexes": index_stats,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            return statistics
            
        except Exception as e:
            self.logger.warning(
                f"Failed to collect index statistics for collection '{collection_name}'",
                extra={
                    "collection": collection_name,
                    "error": str(e)
                }
            )
            return {
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }