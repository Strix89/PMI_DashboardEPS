"""
PMI Dashboard - Main Flask Application with Enhanced Error Handling

This module provides the main Flask application factory and configuration for the
PMI Dashboard. It includes comprehensive error handling, logging, security features,
and integration with the Proxmox management module.

Key Features:
- Flask application factory pattern
- Comprehensive error handling with context logging
- Multi-level logging system (app, error, API, security, performance)
- Security event monitoring and logging
- Request/response timing and performance monitoring
- Health check endpoint for monitoring
- Blueprint registration for modular architecture

The application supports both development and production configurations with
appropriate security measures and logging levels.

Example:
    Basic usage:
        app = create_app()
        app.run(host='0.0.0.0', port=5000)
    
    Production usage with WSGI:
        from app import create_app
        application = create_app()

Author: PMI Dashboard Team
Version: 1.0.0
"""
import os
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import HTTPException
from config import Config
from logging_config import setup_logging, log_api_request, log_security_event, LoggingMiddleware


def create_app():
    """
    Create and configure the Flask application with enhanced error handling.
    
    This function implements the Flask application factory pattern, creating
    and configuring a Flask application instance with comprehensive error
    handling, logging, security features, and blueprint registration.
    
    Features configured:
    - Configuration loading and validation
    - Multi-level logging system setup
    - Global error handlers for exceptions and HTTP errors
    - Request/response middleware for timing and security
    - Blueprint registration for modular architecture
    - Health check endpoint
    - Security event monitoring
    
    Returns:
        Flask: Configured Flask application instance ready for deployment
        
    Raises:
        ConfigurationError: If configuration validation fails
        ImportError: If required modules cannot be imported
        
    Example:
        >>> app = create_app()
        >>> app.run(host='127.0.0.1', port=5000, debug=True)
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize configuration (validates settings and creates directories)
    Config.init_app(app)
    
    # Set up comprehensive logging
    app_logger, error_logger, api_logger, security_logger, perf_logger, acronis_logger = setup_logging(app)
    
    # Store loggers in app context for easy access
    app.app_logger = app_logger
    app.error_logger = error_logger
    app.api_logger = api_logger
    app.security_logger = security_logger
    app.perf_logger = perf_logger
    app.acronis_logger = acronis_logger
    
    # Global error handlers with enhanced logging
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions with comprehensive logging."""
        
        # Log the error with full context
        error_context = {
            'method': request.method,
            'url': request.url,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'remote_addr': request.remote_addr,
            'extra_info': f"Exception: {type(e).__name__}: {str(e)}\nStack trace available in logs"
        }
        
        error_logger.error(f"Unhandled exception: {str(e)}", extra=error_context, exc_info=True)
        
        # Log security event for suspicious activity
        if e.__class__.__name__ in ['SecurityError', 'Forbidden', 'Unauthorized']:
            log_security_event(
                security_logger,
                'SECURITY_EXCEPTION',
                f"Security-related exception: {str(e)}",
                {
                    'method': request.method,
                    'url': request.url,
                    'user_agent': request.headers.get('User-Agent'),
                    'remote_addr': request.remote_addr
                },
                'ERROR'
            )
        
        # Return JSON error for API requests
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'An internal server error occurred',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'help': 'Please try again later or contact support if the problem persists',
                'error_code': 'INTERNAL_ERROR'
            }), 500
        
        # Return HTML error page for regular requests
        return render_template('error.html', error='Internal Server Error'), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle HTTP exceptions with detailed logging."""
        
        error_context = {
            'method': request.method,
            'url': request.url,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'remote_addr': request.remote_addr,
            'extra_info': f"HTTP Exception: {e.code} - {e.description}"
        }
        
        # Log based on severity
        if e.code >= 500:
            error_logger.error(f"HTTP {e.code}: {e.description}", extra=error_context)
        elif e.code >= 400:
            error_logger.warning(f"HTTP {e.code}: {e.description}", extra=error_context)
        
        # Log security events for authentication/authorization errors
        if e.code in [401, 403]:
            log_security_event(
                security_logger,
                'AUTH_ERROR',
                f"Authentication/Authorization error: {e.code} - {e.description}",
                {
                    'method': request.method,
                    'url': request.url,
                    'user_agent': request.headers.get('User-Agent'),
                    'remote_addr': request.remote_addr
                },
                'WARNING'
            )
        
        # Return JSON error for API requests
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': e.description,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'help': 'Please check your request and try again',
                'error_code': f'HTTP_{e.code}'
            }), e.code
        
        # Return HTML error page for regular requests
        return render_template('error.html', error=e.description), e.code
    
    @app.before_request
    def before_request():
        """Log request information and perform security checks."""
        # Store request start time for performance monitoring
        request.start_time = time.time()
        
        # Log detailed request info for debugging
        if app.config.get('DEBUG'):
            app_logger.debug(f"Request: {request.method} {request.url}")
        
        # Basic security logging for suspicious patterns
        user_agent = request.headers.get('User-Agent', '')
        if any(pattern in user_agent.lower() for pattern in ['bot', 'crawler', 'scanner', 'hack']):
            log_security_event(
                security_logger,
                'SUSPICIOUS_USER_AGENT',
                f"Suspicious user agent detected: {user_agent}",
                {
                    'method': request.method,
                    'url': request.url,
                    'user_agent': user_agent,
                    'remote_addr': request.remote_addr
                },
                'INFO'
            )
    
    @app.after_request
    def after_request(response):
        """Log response information and performance metrics."""
        # Calculate request duration
        duration = time.time() - getattr(request, 'start_time', time.time())
        
        # Log API requests with timing
        if request.path.startswith('/api/'):
            log_api_request(
                api_logger,
                request.method,
                request.path,
                response.status_code,
                duration,
                request.headers.get('User-Agent'),
                request.remote_addr
            )
        
        # Log slow requests
        if duration > 2.0:
            perf_logger.warning(
                f"Slow request: {request.method} {request.path} took {duration:.3f}s"
            )
        
        # Debug logging
        if app.config.get('DEBUG'):
            app_logger.debug(f"Response: {response.status_code} ({duration:.3f}s)")
        
        return response
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0'
        })
    
    # Register blueprints
    from proxmox.routes import proxmox_bp
    app.register_blueprint(proxmox_bp)
    
    from acronis.routes import acronis_bp
    app.register_blueprint(acronis_bp)
    app_logger.info("Acronis blueprint registered successfully")
    
    @app.route('/')
    def index():
        """Main dashboard route."""
        return render_template('index.html')
    
    # Wrap with logging middleware
    app.wsgi_app = LoggingMiddleware(app.wsgi_app, api_logger, error_logger, security_logger)
    
    app_logger.info("PMI Dashboard application created successfully")
    app_logger.info(f"Debug mode: {app.config.get('DEBUG', False)}")
    app_logger.info(f"Environment: {app.config.get('ENV', 'production')}")
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=app.config.get('HOST', '127.0.0.1'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )