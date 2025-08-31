"""
Comprehensive Logging Configuration for PMI Dashboard

This module provides centralized logging configuration with different handlers
for various types of events and errors.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any


class ContextFilter(logging.Filter):
    """Add context information to log records."""
    
    def filter(self, record):
        # Add timestamp in ISO format
        record.iso_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Add process and thread info
        record.process_name = 'pmi_dashboard'
        
        return True


class ErrorContextFilter(logging.Filter):
    """Add error-specific context to log records."""
    
    def filter(self, record):
        # Add default values for error context
        if not hasattr(record, 'method'):
            record.method = 'N/A'
        if not hasattr(record, 'url'):
            record.url = 'N/A'
        if not hasattr(record, 'user_agent'):
            record.user_agent = 'N/A'
        if not hasattr(record, 'remote_addr'):
            record.remote_addr = 'N/A'
        if not hasattr(record, 'extra_info'):
            record.extra_info = ''
            
        return True


def setup_logging(app, log_level=None):
    """
    Set up comprehensive logging for the application.
    
    Args:
        app: Flask application instance
        log_level: Override log level
        
    Returns:
        Tuple of (app_logger, error_logger, api_logger, security_logger)
    """
    
    # Determine log level
    if log_level is None:
        log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    
    # Create logs directory
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(iso_timestamp)s [%(levelname)s] %(process_name)s [%(filename)s:%(lineno)d] '
        '%(funcName)s(): %(message)s'
    )
    
    error_formatter = logging.Formatter(
        '%(iso_timestamp)s [%(levelname)s] %(process_name)s [%(filename)s:%(lineno)d]\n'
        'Function: %(funcName)s()\n'
        'Message: %(message)s\n'
        'Request: %(method)s %(url)s\n'
        'User Agent: %(user_agent)s\n'
        'Remote Address: %(remote_addr)s\n'
        '%(extra_info)s\n'
        '---'
    )
    
    api_formatter = logging.Formatter(
        '%(iso_timestamp)s [%(levelname)s] API: %(message)s'
    )
    
    security_formatter = logging.Formatter(
        '%(iso_timestamp)s [SECURITY] [%(levelname)s] %(message)s\n'
        'Request: %(method)s %(url)s\n'
        'User Agent: %(user_agent)s\n'
        'Remote Address: %(remote_addr)s\n'
        '---'
    )
    
    # Create filters
    context_filter = ContextFilter()
    error_context_filter = ErrorContextFilter()
    
    # Application Logger
    app_logger = logging.getLogger('pmi_dashboard')
    app_logger.setLevel(log_level)
    app_logger.handlers.clear()
    
    app_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    app_handler.setFormatter(detailed_formatter)
    app_handler.addFilter(context_filter)
    app_logger.addHandler(app_handler)
    
    # Console handler for development
    if app.config.get('DEBUG'):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))
        app_logger.addHandler(console_handler)
    
    # Error Logger
    error_logger = logging.getLogger('pmi_dashboard.errors')
    error_logger.setLevel(logging.WARNING)
    error_logger.handlers.clear()
    
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'errors.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    error_handler.setFormatter(error_formatter)
    error_handler.addFilter(context_filter)
    error_handler.addFilter(error_context_filter)
    error_logger.addHandler(error_handler)
    
    # API Logger
    api_logger = logging.getLogger('pmi_dashboard.api')
    api_logger.setLevel(logging.INFO)
    api_logger.handlers.clear()
    
    api_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'api.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    api_handler.setFormatter(api_formatter)
    api_handler.addFilter(context_filter)
    api_logger.addHandler(api_handler)
    
    # Security Logger
    security_logger = logging.getLogger('pmi_dashboard.security')
    security_logger.setLevel(logging.WARNING)
    security_logger.handlers.clear()
    
    security_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'security.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    security_handler.setFormatter(security_formatter)
    security_handler.addFilter(context_filter)
    security_handler.addFilter(error_context_filter)
    security_logger.addHandler(security_handler)
    
    # Performance Logger
    perf_logger = logging.getLogger('pmi_dashboard.performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.handlers.clear()
    
    perf_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'performance.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    perf_handler.setFormatter(detailed_formatter)
    perf_handler.addFilter(context_filter)
    perf_logger.addHandler(perf_handler)
    
    # Set up Flask's logger
    app.logger.handlers.clear()
    app.logger.addHandler(app_handler)
    app.logger.setLevel(log_level)
    
    # Log startup
    app_logger.info("Logging system initialized")
    app_logger.info(f"Log level: {logging.getLevelName(log_level)}")
    app_logger.info(f"Log directory: {log_dir}")
    
    return app_logger, error_logger, api_logger, security_logger, perf_logger


def log_api_request(logger, method: str, endpoint: str, status_code: int, 
                   duration: float, user_agent: str = None, remote_addr: str = None):
    """
    Log API request with timing information.
    
    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        duration: Request duration in seconds
        user_agent: User agent string
        remote_addr: Remote IP address
    """
    level = logging.INFO
    if status_code >= 400:
        level = logging.WARNING
    if status_code >= 500:
        level = logging.ERROR
    
    message = f"{method} {endpoint} - {status_code} ({duration:.3f}s)"
    
    extra = {
        'method': method,
        'endpoint': endpoint,
        'status_code': status_code,
        'duration': duration,
        'user_agent': user_agent or 'Unknown',
        'remote_addr': remote_addr or 'Unknown'
    }
    
    logger.log(level, message, extra=extra)


def log_security_event(logger, event_type: str, message: str, 
                      request_info: Dict[str, Any] = None, severity: str = 'WARNING'):
    """
    Log security-related events.
    
    Args:
        logger: Security logger instance
        event_type: Type of security event
        message: Event message
        request_info: Request information
        severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
    """
    level = getattr(logging, severity.upper(), logging.WARNING)
    
    full_message = f"[{event_type}] {message}"
    
    extra = {
        'event_type': event_type,
        'method': request_info.get('method', 'N/A') if request_info else 'N/A',
        'url': request_info.get('url', 'N/A') if request_info else 'N/A',
        'user_agent': request_info.get('user_agent', 'N/A') if request_info else 'N/A',
        'remote_addr': request_info.get('remote_addr', 'N/A') if request_info else 'N/A',
        'extra_info': f"Event Type: {event_type}"
    }
    
    logger.log(level, full_message, extra=extra)


def log_performance_metric(logger, operation: str, duration: float, 
                          context: Dict[str, Any] = None):
    """
    Log performance metrics.
    
    Args:
        logger: Performance logger instance
        operation: Operation name
        duration: Operation duration in seconds
        context: Additional context
    """
    message = f"Performance: {operation} took {duration:.3f}s"
    
    if context:
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
        message += f" ({context_str})"
    
    # Log as warning if operation is slow
    level = logging.WARNING if duration > 5.0 else logging.INFO
    
    logger.log(level, message)


class LoggingMiddleware:
    """Middleware for logging requests and responses."""
    
    def __init__(self, app, api_logger, error_logger, security_logger):
        self.app = app
        self.api_logger = api_logger
        self.error_logger = error_logger
        self.security_logger = security_logger
    
    def __call__(self, environ, start_response):
        """WSGI middleware implementation."""
        import time
        from flask import request
        
        start_time = time.time()
        
        def new_start_response(status, response_headers, exc_info=None):
            duration = time.time() - start_time
            
            # Log API request
            if environ.get('PATH_INFO', '').startswith('/api/'):
                log_api_request(
                    self.api_logger,
                    environ.get('REQUEST_METHOD', 'GET'),
                    environ.get('PATH_INFO', ''),
                    int(status.split()[0]),
                    duration,
                    environ.get('HTTP_USER_AGENT'),
                    environ.get('REMOTE_ADDR')
                )
            
            # Log slow requests
            if duration > 2.0:
                self.error_logger.warning(
                    f"Slow request: {environ.get('REQUEST_METHOD')} "
                    f"{environ.get('PATH_INFO')} took {duration:.3f}s"
                )
            
            return start_response(status, response_headers, exc_info)
        
        return self.app(environ, new_start_response)