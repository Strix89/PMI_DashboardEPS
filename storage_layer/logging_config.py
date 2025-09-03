"""
Logging configuration for Infrastructure Monitoring Storage Layer

This module provides centralized logging configuration with structured logging,
multiple output formats, and configurable log levels for different components.
"""

import logging
import logging.config
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime, UTC


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    This formatter creates JSON-structured log entries that are easier to parse
    and analyze in log aggregation systems like ELK stack or similar tools.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                'filename', 'module', 'lineno', 'funcName', 'created', 
                'msecs', 'relativeCreated', 'thread', 'threadName', 
                'processName', 'process', 'getMessage', 'exc_info', 
                'exc_text', 'stack_info'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Console formatter with color coding for different log levels.
    
    This formatter adds ANSI color codes to console output to make logs
    more readable during development and debugging.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with color coding.
        
        Args:
            record: Log record to format
            
        Returns:
            Color-formatted log string
        """
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']
        
        # Create colored level name
        colored_levelname = f"{level_color}{record.levelname}{reset_color}"
        
        # Temporarily replace levelname for formatting
        original_levelname = record.levelname
        record.levelname = colored_levelname
        
        try:
            formatted = super().format(record)
        finally:
            # Restore original levelname
            record.levelname = original_levelname
        
        return formatted


def setup_logging(
    level: str = "INFO",
    format_type: str = "console",
    log_file: Optional[str] = None,
    enable_structured_logging: bool = False
) -> None:
    """
    Set up logging configuration for the storage layer.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ('console', 'json', 'detailed')
        log_file: Optional file path for file logging
        enable_structured_logging: Whether to enable structured JSON logging
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure formatters
    formatters = {
        'console': ColoredConsoleFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        'detailed': logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ),
        'json': StructuredFormatter(),
        'simple': logging.Formatter('%(levelname)s - %(message)s')
    }
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if enable_structured_logging:
        console_handler.setFormatter(formatters['json'])
    else:
        console_handler.setFormatter(formatters.get(format_type, formatters['console']))
    
    # Configure root logger
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # Set up file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        
        # Always use structured logging for files
        file_handler.setFormatter(formatters['json'])
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_storage_loggers(numeric_level)


def configure_storage_loggers(level: int) -> None:
    """
    Configure specific loggers for storage layer components.
    
    Args:
        level: Numeric logging level
    """
    # Storage layer loggers
    storage_loggers = [
        'storage_layer.storage_manager',
        'storage_layer.models',
        'storage_layer.exceptions',
        'pymongo',
        'pymongo.command',
        'pymongo.connection'
    ]
    
    for logger_name in storage_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        
        # Reduce verbosity for pymongo loggers unless debug level
        if logger_name.startswith('pymongo') and level > logging.DEBUG:
            logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_operation_start(logger: logging.Logger, operation: str, **kwargs) -> None:
    """
    Log the start of a database operation with context.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        **kwargs: Additional context information
    """
    logger.info(
        f"Starting operation: {operation}",
        extra={
            "operation": operation,
            "operation_phase": "start",
            **kwargs
        }
    )


def log_operation_success(logger: logging.Logger, operation: str, 
                         duration: Optional[float] = None, **kwargs) -> None:
    """
    Log successful completion of a database operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Operation duration in seconds
        **kwargs: Additional context information
    """
    extra_data = {
        "operation": operation,
        "operation_phase": "success",
        **kwargs
    }
    
    if duration is not None:
        extra_data["duration_seconds"] = round(duration, 3)
    
    logger.info(
        f"Operation completed successfully: {operation}",
        extra=extra_data
    )


def log_operation_error(logger: logging.Logger, operation: str, error: Exception,
                       duration: Optional[float] = None, **kwargs) -> None:
    """
    Log error during a database operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        error: Exception that occurred
        duration: Operation duration in seconds before error
        **kwargs: Additional context information
    """
    extra_data = {
        "operation": operation,
        "operation_phase": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs
    }
    
    if duration is not None:
        extra_data["duration_seconds"] = round(duration, 3)
    
    logger.error(
        f"Operation failed: {operation}",
        extra=extra_data,
        exc_info=True
    )


def create_operation_logger(base_logger: logging.Logger, operation: str) -> 'OperationLogger':
    """
    Create an operation-specific logger for tracking operation lifecycle.
    
    Args:
        base_logger: Base logger instance
        operation: Name of the operation
        
    Returns:
        OperationLogger instance
    """
    return OperationLogger(base_logger, operation)


class OperationLogger:
    """
    Context manager for logging database operations with timing and error handling.
    
    This class provides a convenient way to log the start, success, or failure
    of database operations with automatic timing and structured context.
    """
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        """
        Initialize operation logger.
        
        Args:
            logger: Base logger instance
            operation: Name of the operation
            **context: Additional context information
        """
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> 'OperationLogger':
        """Start operation logging."""
        self.start_time = datetime.now(UTC).timestamp()
        log_operation_start(self.logger, self.operation, **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Complete operation logging."""
        duration = None
        if self.start_time:
            duration = datetime.now(UTC).timestamp() - self.start_time
        
        if exc_type is None:
            log_operation_success(self.logger, self.operation, duration, **self.context)
        else:
            log_operation_error(self.logger, self.operation, exc_val, duration, **self.context)
    
    def add_context(self, **kwargs) -> None:
        """Add additional context to the operation logger."""
        self.context.update(kwargs)
    
    def log_progress(self, message: str, **kwargs) -> None:
        """Log progress during the operation."""
        self.logger.info(
            f"Operation progress: {self.operation} - {message}",
            extra={
                "operation": self.operation,
                "operation_phase": "progress",
                **self.context,
                **kwargs
            }
        )


# Default logging configuration
DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'json': {
            '()': StructuredFormatter
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'storage_layer': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'pymongo': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    }
}


def apply_default_config() -> None:
    """Apply the default logging configuration."""
    logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)