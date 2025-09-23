"""
Acronis API Client for PMI Dashboard

This module provides a comprehensive client for interacting with Acronis Cyber Protect Cloud API,
including authentication, agent management, workload operations, and backup data retrieval.
"""

import requests
import logging
import json
import time
import functools
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urljoin
from datetime import datetime
import urllib3
from contextlib import contextmanager

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('pmi_dashboard.acronis')

# Performance and error tracking logger
perf_logger = logging.getLogger('pmi_dashboard.performance')
error_logger = logging.getLogger('pmi_dashboard.errors')


class AcronisAPIError(Exception):
    """Custom exception for Acronis API related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None, 
                 recoverable: bool = True, retry_after: int = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()


class AcronisAuthenticationError(AcronisAPIError):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str, error_code: str = "ACRONIS_AUTH_ERROR", 
                 details: Dict = None):
        super().__init__(message, error_code, details, recoverable=True)


class AcronisConnectionError(AcronisAPIError):
    """Exception raised for connection failures."""
    
    def __init__(self, message: str, error_code: str = "ACRONIS_CONNECTION_ERROR", 
                 details: Dict = None, retry_after: int = 30):
        super().__init__(message, error_code, details, recoverable=True, retry_after=retry_after)


class AcronisRateLimitError(AcronisAPIError):
    """Exception raised for rate limiting."""
    
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message, "ACRONIS_RATE_LIMIT", retry_after=retry_after)


class AcronisServerError(AcronisAPIError):
    """Exception raised for server-side errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_code: str = "ACRONIS_SERVER_ERROR"):
        super().__init__(message, error_code, {"status_code": status_code}, recoverable=True)


def log_performance(operation_name: str):
    """Decorator to log performance metrics for API operations."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation_id = f"{operation_name}_{int(start_time * 1000)}"
            
            try:
                logger.debug(f"Starting operation: {operation_name} (ID: {operation_id})")
                result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                perf_logger.info(f"Operation completed: {operation_name} took {duration:.3f}s")
                
                if duration > 5.0:
                    logger.warning(f"Slow operation detected: {operation_name} took {duration:.3f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                error_logger.error(
                    f"Operation failed: {operation_name} after {duration:.3f}s - {str(e)}",
                    extra={
                        'operation': operation_name,
                        'operation_id': operation_id,
                        'duration': duration,
                        'error_type': type(e).__name__
                    }
                )
                raise
                
        return wrapper
    return decorator


def handle_api_errors(operation_name: str, fallback_value=None):
    """Decorator to handle and categorize API errors."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.Timeout as e:
                error_msg = f"Request timeout during {operation_name}"
                logger.error(f"{error_msg}: {str(e)}")
                raise AcronisConnectionError(
                    error_msg,
                    details={"timeout": True, "original_error": str(e)}
                )
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection failed during {operation_name}"
                logger.error(f"{error_msg}: {str(e)}")
                raise AcronisConnectionError(
                    error_msg,
                    details={"connection_error": True, "original_error": str(e)}
                )
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else 0
                if status_code == 401:
                    raise AcronisAuthenticationError(
                        f"Authentication failed during {operation_name}",
                        details={"status_code": status_code}
                    )
                elif status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    raise AcronisRateLimitError(
                        f"Rate limit exceeded during {operation_name}",
                        retry_after=retry_after
                    )
                elif status_code >= 500:
                    raise AcronisServerError(
                        f"Server error during {operation_name}",
                        status_code=status_code
                    )
                else:
                    raise AcronisAPIError(
                        f"HTTP error during {operation_name}: {str(e)}",
                        error_code="ACRONIS_HTTP_ERROR",
                        details={"status_code": status_code}
                    )
            except AcronisAPIError:
                # Re-raise Acronis-specific errors
                raise
            except Exception as e:
                error_msg = f"Unexpected error during {operation_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise AcronisAPIError(
                    error_msg,
                    error_code="ACRONIS_UNEXPECTED_ERROR",
                    details={"error_type": type(e).__name__},
                    recoverable=False
                )
        return wrapper
    return decorator


@contextmanager
def error_context(operation: str, **context):
    """Context manager for enhanced error logging with context."""
    start_time = time.time()
    operation_id = f"{operation}_{int(start_time * 1000)}"
    
    logger.debug(f"Starting {operation} (ID: {operation_id})", extra=context)
    
    try:
        yield operation_id
        duration = time.time() - start_time
        logger.debug(f"Completed {operation} in {duration:.3f}s (ID: {operation_id})")
        
    except Exception as e:
        duration = time.time() - start_time
        error_context = {
            'operation': operation,
            'operation_id': operation_id,
            'duration': duration,
            'error_type': type(e).__name__,
            **context
        }
        
        error_logger.error(
            f"Failed {operation} after {duration:.3f}s: {str(e)}",
            extra=error_context,
            exc_info=True
        )
        raise


class AcronisAPIClient:
    """
    Acronis Cyber Protect Cloud API client with comprehensive functionality for agent management,
    workload operations, and backup data retrieval.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        grant_type: str = "client_credentials",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the Acronis API client.

        Args:
            base_url (str): Base URL for the Acronis API
            client_id (str): Client ID for authentication
            client_secret (str): Client secret for authentication
            grant_type (str): Grant type for OAuth2 authentication
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type = grant_type
        self.timeout = timeout
        self.max_retries = max_retries
        self.token = None
        self.token_expires_at = None
        self.session = requests.Session()
        
        # Error tracking
        self.consecutive_failures = 0
        self.last_error_time = None
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time = None
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0.0

        # Set default headers
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        # Log initialization with sanitized info
        logger.info(
            f"Initialized Acronis API client for {self.base_url}",
            extra={
                'base_url': self.base_url,
                'client_id': self.client_id[:8] + '...' if len(self.client_id) > 8 else self.client_id,
                'grant_type': self.grant_type,
                'timeout': self.timeout,
                'max_retries': self.max_retries
            }
        )

    def __del__(self):
        """Clean up the session when the client is destroyed."""
        if hasattr(self, "session"):
            self.session.close()
            
        # Log final statistics
        if hasattr(self, 'request_count') and self.request_count > 0:
            avg_request_time = self.total_request_time / self.request_count
            error_rate = (self.error_count / self.request_count) * 100
            
            logger.info(
                f"Acronis API client destroyed - Stats: {self.request_count} requests, "
                f"{self.error_count} errors ({error_rate:.1f}%), "
                f"avg response time: {avg_request_time:.3f}s"
            )
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open (preventing requests)."""
        if not self.circuit_breaker_open:
            return False
            
        # Check if it's time to reset the circuit breaker
        if (self.circuit_breaker_reset_time and 
            time.time() >= self.circuit_breaker_reset_time):
            self.circuit_breaker_open = False
            self.circuit_breaker_reset_time = None
            self.consecutive_failures = 0
            logger.info("Circuit breaker reset - allowing requests to resume")
            return False
            
        return True
    
    def _handle_request_success(self):
        """Handle successful request for circuit breaker logic."""
        if self.consecutive_failures > 0:
            logger.info(f"Request succeeded after {self.consecutive_failures} failures - resetting error count")
            
        self.consecutive_failures = 0
        self.last_error_time = None
        
        if self.circuit_breaker_open:
            self.circuit_breaker_open = False
            self.circuit_breaker_reset_time = None
            logger.info("Circuit breaker closed after successful request")
    
    def _handle_request_failure(self, error: Exception):
        """Handle failed request for circuit breaker logic."""
        self.consecutive_failures += 1
        self.last_error_time = time.time()
        self.error_count += 1
        
        # Open circuit breaker after 5 consecutive failures
        if self.consecutive_failures >= 5 and not self.circuit_breaker_open:
            self.circuit_breaker_open = True
            self.circuit_breaker_reset_time = time.time() + 300  # 5 minutes
            
            logger.error(
                f"Circuit breaker opened after {self.consecutive_failures} consecutive failures. "
                f"Will retry in 5 minutes.",
                extra={
                    'consecutive_failures': self.consecutive_failures,
                    'error_type': type(error).__name__,
                    'error_message': str(error)
                }
            )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the API client."""
        now = time.time()
        
        status = {
            'healthy': not self.circuit_breaker_open,
            'circuit_breaker_open': self.circuit_breaker_open,
            'consecutive_failures': self.consecutive_failures,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': (self.error_count / max(self.request_count, 1)) * 100,
            'avg_response_time': self.total_request_time / max(self.request_count, 1),
            'last_error_time': self.last_error_time,
            'time_since_last_error': now - self.last_error_time if self.last_error_time else None,
            'circuit_breaker_reset_in': max(0, self.circuit_breaker_reset_time - now) if self.circuit_breaker_reset_time else None
        }
        
        return status

    @handle_api_errors("HTTP request")
    @log_performance("http_request")
    def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request with comprehensive error handling and retry logic.

        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            Optional[requests.Response]: Response object or None if failed
        """
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            reset_time = self.circuit_breaker_reset_time - time.time() if self.circuit_breaker_reset_time else 0
            raise AcronisConnectionError(
                f"Circuit breaker is open. Service unavailable for {reset_time:.0f} more seconds.",
                error_code="ACRONIS_CIRCUIT_BREAKER_OPEN",
                details={"reset_in_seconds": reset_time},
                retry_after=int(reset_time)
            )
        
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        request_start_time = time.time()

        # Set timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        # Disable SSL verification for self-signed certificates
        kwargs["verify"] = False
        
        # Add request tracking
        self.request_count += 1
        request_id = f"req_{self.request_count}_{int(request_start_time * 1000)}"

        with error_context("http_request", 
                          method=method, 
                          url=url, 
                          request_id=request_id,
                          attempt_number=0) as operation_id:
            
            last_exception = None
            
            for attempt in range(self.max_retries + 1):
                attempt_start_time = time.time()
                
                try:
                    logger.debug(
                        f"Making {method} request to {url} (attempt {attempt + 1}/{self.max_retries + 1})",
                        extra={
                            'method': method,
                            'url': url,
                            'attempt': attempt + 1,
                            'max_attempts': self.max_retries + 1,
                            'request_id': request_id,
                            'operation_id': operation_id
                        }
                    )
                    
                    response = self.session.request(method, url, **kwargs)
                    
                    # Track timing
                    request_duration = time.time() - request_start_time
                    self.total_request_time += request_duration
                    
                    # Log successful response
                    logger.debug(
                        f"Response: {response.status_code} for {method} {url} in {request_duration:.3f}s",
                        extra={
                            'method': method,
                            'url': url,
                            'status_code': response.status_code,
                            'duration': request_duration,
                            'request_id': request_id,
                            'attempt': attempt + 1
                        }
                    )
                    
                    # Handle successful request
                    self._handle_request_success()
                    
                    return response

                except requests.exceptions.Timeout as e:
                    attempt_duration = time.time() - attempt_start_time
                    last_exception = e
                    
                    logger.warning(
                        f"Timeout on {method} {url} (attempt {attempt + 1}/{self.max_retries + 1}) after {attempt_duration:.3f}s",
                        extra={
                            'method': method,
                            'url': url,
                            'attempt': attempt + 1,
                            'duration': attempt_duration,
                            'request_id': request_id,
                            'timeout': kwargs.get('timeout', self.timeout)
                        }
                    )
                    
                    if attempt == self.max_retries:
                        self._handle_request_failure(e)
                        raise AcronisConnectionError(
                            f"Request timeout after {self.max_retries + 1} attempts",
                            error_code="ACRONIS_TIMEOUT",
                            details={
                                "attempts": self.max_retries + 1,
                                "timeout": kwargs.get('timeout', self.timeout),
                                "total_duration": time.time() - request_start_time
                            }
                        )
                    
                    # Exponential backoff for retries
                    backoff_time = min(2 ** attempt, 30)  # Max 30 seconds
                    logger.debug(f"Waiting {backoff_time}s before retry")
                    time.sleep(backoff_time)

                except requests.exceptions.ConnectionError as e:
                    attempt_duration = time.time() - attempt_start_time
                    last_exception = e
                    
                    logger.warning(
                        f"Connection error on {method} {url} (attempt {attempt + 1}/{self.max_retries + 1}): {e}",
                        extra={
                            'method': method,
                            'url': url,
                            'attempt': attempt + 1,
                            'duration': attempt_duration,
                            'request_id': request_id,
                            'error_type': type(e).__name__
                        }
                    )
                    
                    if attempt == self.max_retries:
                        self._handle_request_failure(e)
                        raise AcronisConnectionError(
                            f"Connection failed after {self.max_retries + 1} attempts: {e}",
                            error_code="ACRONIS_CONNECTION_FAILED",
                            details={
                                "attempts": self.max_retries + 1,
                                "original_error": str(e),
                                "total_duration": time.time() - request_start_time
                            }
                        )
                    
                    # Exponential backoff for retries
                    backoff_time = min(2 ** attempt, 30)  # Max 30 seconds
                    logger.debug(f"Waiting {backoff_time}s before retry")
                    time.sleep(backoff_time)

                except requests.exceptions.RequestException as e:
                    attempt_duration = time.time() - attempt_start_time
                    last_exception = e
                    
                    logger.error(
                        f"Request error on {method} {url}: {e}",
                        extra={
                            'method': method,
                            'url': url,
                            'attempt': attempt + 1,
                            'duration': attempt_duration,
                            'request_id': request_id,
                            'error_type': type(e).__name__
                        }
                    )
                    
                    self._handle_request_failure(e)
                    raise AcronisAPIError(
                        f"Request failed: {e}",
                        error_code="ACRONIS_REQUEST_ERROR",
                        details={
                            "original_error": str(e),
                            "error_type": type(e).__name__
                        }
                    )

            # This should never be reached, but just in case
            if last_exception:
                self._handle_request_failure(last_exception)
                raise AcronisAPIError(
                    f"Request failed after all retries: {last_exception}",
                    error_code="ACRONIS_MAX_RETRIES_EXCEEDED"
                )
            
            return None

    @handle_api_errors("token_request")
    @log_performance("get_token")
    def get_token(self) -> Optional[str]:
        """
        Get authentication token from Acronis API with comprehensive error handling.

        Returns:
            Optional[str]: Authentication token or None if failed
        """
        with error_context("get_token", 
                          client_id=self.client_id[:8] + '...',
                          grant_type=self.grant_type) as operation_id:
            
            # Check if current token is still valid
            if self.token and self.token_expires_at:
                time_until_expiry = self.token_expires_at - time.time()
                
                if time_until_expiry > 60:  # Refresh 1 minute before expiry
                    logger.debug(
                        f"Using existing valid token (expires in {time_until_expiry:.0f}s)",
                        extra={'operation_id': operation_id, 'time_until_expiry': time_until_expiry}
                    )
                    return self.token
                else:
                    logger.debug(
                        f"Token expires soon ({time_until_expiry:.0f}s), requesting new token",
                        extra={'operation_id': operation_id, 'time_until_expiry': time_until_expiry}
                    )

            logger.info(
                f"Requesting new authentication token from {self.base_url}",
                extra={'operation_id': operation_id, 'grant_type': self.grant_type}
            )

            token_data = {
                "grant_type": self.grant_type,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            try:
                # Try different OAuth2 endpoints that Acronis might use
                # Based on working implementation: 2/idp/token is the correct endpoint
                oauth_endpoints = ["/2/idp/token", "/api/2/idp/token", "/oauth2/token", "/idp/token"]
                response = None
                
                for endpoint in oauth_endpoints:
                    try:
                        full_url = f"{self.base_url.rstrip('/')}{endpoint}"
                        logger.info(f"Trying OAuth2 endpoint: {full_url}")
                        logger.debug(f"Token data: grant_type={token_data['grant_type']}, client_id={token_data['client_id'][:8]}...")
                        
                        # OAuth2 token requests require application/x-www-form-urlencoded
                        response = self._make_request(
                            "POST", 
                            endpoint, 
                            data=token_data,  # This will be form-encoded
                            headers={"Content-Type": "application/x-www-form-urlencoded"}
                        )
                        
                        if response and response.status_code == 200:
                            logger.info(f"Successfully authenticated using endpoint: {endpoint}")
                            break
                        elif response and response.status_code == 404:
                            logger.warning(f"Endpoint {endpoint} not found (404), trying next...")
                            continue
                        else:
                            # Other error, log details and break
                            status = response.status_code if response else "No response"
                            logger.error(f"Endpoint {endpoint} failed with status: {status}")
                            if response:
                                logger.error(f"Response text: {response.text[:200]}")
                            break
                            
                    except Exception as e:
                        logger.error(f"Exception with endpoint {endpoint}: {e}")
                        if endpoint == oauth_endpoints[-1]:  # Last endpoint
                            raise
                        continue

                if response and response.status_code == 200:
                    try:
                        token_response = response.json()
                        self.token = token_response.get("access_token")

                        if not self.token:
                            raise AcronisAuthenticationError(
                                "No access token in response",
                                error_code="ACRONIS_NO_TOKEN",
                                details={"response_keys": list(token_response.keys())}
                            )

                        # Calculate token expiration time
                        expires_in = token_response.get("expires_in", 3600)  # Default 1 hour
                        self.token_expires_at = time.time() + expires_in

                        # Update session headers with new token
                        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

                        logger.info(
                            f"Successfully obtained authentication token (expires in {expires_in}s)",
                            extra={
                                'operation_id': operation_id,
                                'expires_in': expires_in,
                                'token_length': len(self.token) if self.token else 0
                            }
                        )
                        return self.token
                        
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON in token response: {e}"
                        logger.error(error_msg, extra={'operation_id': operation_id})
                        raise AcronisAuthenticationError(
                            error_msg,
                            error_code="ACRONIS_INVALID_TOKEN_RESPONSE",
                            details={"json_error": str(e)}
                        )
                        
                else:
                    status_code = response.status_code if response else 0
                    error_msg = f"Token request failed with status {status_code}"
                    error_details = {"status_code": status_code}
                    
                    if response:
                        try:
                            error_data = response.json()
                            error_description = error_data.get('error_description', 
                                                             error_data.get('error', 'Unknown error'))
                            error_msg += f": {error_description}"
                            error_details.update(error_data)
                        except json.JSONDecodeError:
                            error_msg += f": {response.text[:200]}"  # Limit error text length
                            error_details["response_text"] = response.text[:200]

                    logger.error(error_msg, extra={'operation_id': operation_id, **error_details})
                    
                    # Categorize authentication errors
                    if status_code == 401:
                        raise AcronisAuthenticationError(
                            "Invalid API credentials",
                            error_code="ACRONIS_INVALID_CREDENTIALS",
                            details=error_details
                        )
                    elif status_code == 403:
                        raise AcronisAuthenticationError(
                            "API credentials do not have sufficient permissions",
                            error_code="ACRONIS_INSUFFICIENT_PERMISSIONS",
                            details=error_details
                        )
                    else:
                        raise AcronisAuthenticationError(
                            error_msg,
                            error_code="ACRONIS_TOKEN_REQUEST_FAILED",
                            details=error_details
                        )

            except AcronisAuthenticationError:
                raise
            except AcronisAPIError:
                raise
            except Exception as e:
                error_msg = f"Unexpected error during token request: {e}"
                logger.error(error_msg, extra={'operation_id': operation_id}, exc_info=True)
                raise AcronisAuthenticationError(
                    error_msg,
                    error_code="ACRONIS_TOKEN_UNEXPECTED_ERROR",
                    details={"error_type": type(e).__name__}
                )

    def _ensure_authenticated(self) -> bool:
        """
        Ensure the client is authenticated with a valid token.

        Returns:
            bool: True if authenticated, False otherwise
        """
        try:
            token = self.get_token()
            return token is not None
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    @handle_api_errors("authenticated_request")
    @log_performance("authenticated_request")
    def _make_authenticated_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict]:
        """
        Make an authenticated API request with comprehensive error handling and automatic token refresh.

        Args:
            method (str): HTTP method
            endpoint (str): API endpoint
            **kwargs: Additional request arguments

        Returns:
            Optional[Dict]: JSON response data or None if failed
        """
        with error_context("authenticated_request", 
                          method=method, 
                          endpoint=endpoint) as operation_id:
            
            # Ensure we have valid authentication
            if not self._ensure_authenticated():
                raise AcronisAuthenticationError(
                    "Failed to authenticate before making request",
                    error_code="ACRONIS_AUTH_REQUIRED"
                )

            max_auth_retries = 2  # Allow one token refresh retry
            
            for auth_attempt in range(max_auth_retries):
                try:
                    response = self._make_request(method, endpoint, **kwargs)

                    if response is None:
                        logger.warning(
                            f"No response received for {method} {endpoint}",
                            extra={'operation_id': operation_id, 'auth_attempt': auth_attempt + 1}
                        )
                        return None

                    # Handle different response status codes
                    if response.status_code == 200:
                        try:
                            json_data = response.json()
                            logger.debug(
                                f"Successful API response for {method} {endpoint}",
                                extra={
                                    'operation_id': operation_id,
                                    'status_code': response.status_code,
                                    'response_size': len(str(json_data)) if json_data else 0
                                }
                            )
                            return json_data
                            
                        except json.JSONDecodeError as e:
                            error_msg = f"Failed to parse JSON response from {method} {endpoint}: {e}"
                            logger.error(
                                error_msg,
                                extra={
                                    'operation_id': operation_id,
                                    'response_text': response.text[:500],  # First 500 chars
                                    'content_type': response.headers.get('content-type')
                                }
                            )
                            raise AcronisAPIError(
                                error_msg,
                                error_code="ACRONIS_INVALID_JSON_RESPONSE",
                                details={
                                    "content_type": response.headers.get('content-type'),
                                    "response_preview": response.text[:200]
                                }
                            )
                    
                    elif response.status_code == 401:
                        if auth_attempt == 0:  # First attempt, try token refresh
                            logger.warning(
                                f"Received 401 for {method} {endpoint}, attempting token refresh",
                                extra={'operation_id': operation_id, 'auth_attempt': auth_attempt + 1}
                            )
                            
                            # Force token refresh
                            self.token = None
                            self.token_expires_at = None

                            if self._ensure_authenticated():
                                logger.info("Token refreshed successfully, retrying request")
                                continue  # Retry the request with new token
                            else:
                                raise AcronisAuthenticationError(
                                    "Failed to refresh authentication token after 401 response",
                                    error_code="ACRONIS_TOKEN_REFRESH_FAILED"
                                )
                        else:
                            # Second attempt also failed
                            raise AcronisAuthenticationError(
                                f"Authentication failed for {method} {endpoint} after token refresh",
                                error_code="ACRONIS_AUTH_FAILED_AFTER_REFRESH"
                            )
                    
                    elif response.status_code == 403:
                        raise AcronisAuthenticationError(
                            f"Access forbidden for {method} {endpoint} - insufficient permissions",
                            error_code="ACRONIS_INSUFFICIENT_PERMISSIONS",
                            details={"endpoint": endpoint, "method": method}
                        )
                    
                    elif response.status_code == 404:
                        raise AcronisAPIError(
                            f"Resource not found: {method} {endpoint}",
                            error_code="ACRONIS_RESOURCE_NOT_FOUND",
                            details={"endpoint": endpoint, "method": method}
                        )
                    
                    elif response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        raise AcronisRateLimitError(
                            f"Rate limit exceeded for {method} {endpoint}",
                            retry_after=retry_after
                        )
                    
                    elif response.status_code >= 500:
                        error_msg = f"Server error for {method} {endpoint}: HTTP {response.status_code}"
                        
                        try:
                            error_data = response.json()
                            error_msg += f" - {error_data.get('message', error_data.get('error', 'Unknown server error'))}"
                        except json.JSONDecodeError:
                            error_msg += f" - {response.text[:200]}"
                        
                        raise AcronisServerError(
                            error_msg,
                            status_code=response.status_code
                        )
                    
                    else:
                        # Other client errors (4xx)
                        error_msg = f"API request failed: {method} {endpoint} - HTTP {response.status_code}"
                        error_details = {"status_code": response.status_code, "endpoint": endpoint, "method": method}
                        
                        try:
                            error_data = response.json()
                            error_msg += f" - {error_data.get('message', error_data.get('error', 'Unknown error'))}"
                            error_details.update(error_data)
                        except json.JSONDecodeError:
                            error_msg += f" - {response.text[:200]}"
                            error_details["response_text"] = response.text[:200]

                        logger.error(
                            error_msg,
                            extra={'operation_id': operation_id, **error_details}
                        )
                        
                        raise AcronisAPIError(
                            error_msg,
                            error_code="ACRONIS_CLIENT_ERROR",
                            details=error_details
                        )

                except (AcronisAuthenticationError, AcronisAPIError, AcronisRateLimitError, AcronisServerError):
                    # Re-raise Acronis-specific errors
                    raise
                except Exception as e:
                    error_msg = f"Unexpected error during API request {method} {endpoint}: {e}"
                    logger.error(
                        error_msg,
                        extra={'operation_id': operation_id, 'auth_attempt': auth_attempt + 1},
                        exc_info=True
                    )
                    raise AcronisAPIError(
                        error_msg,
                        error_code="ACRONIS_UNEXPECTED_REQUEST_ERROR",
                        details={"error_type": type(e).__name__},
                        recoverable=False
                    )
            
            # This should never be reached
            raise AcronisAPIError(
                f"Request failed after {max_auth_retries} authentication attempts",
                error_code="ACRONIS_MAX_AUTH_RETRIES_EXCEEDED"
            )

    @handle_api_errors("fetch_agents")
    @log_performance("fetch_agents")
    def fetch_all_agents(self) -> Optional[List[Dict]]:
        """
        Fetch all agents from Acronis API with comprehensive error handling.

        Returns:
            Optional[List[Dict]]: List of agent data or None if failed
        """
        with error_context("fetch_agents") as operation_id:
            logger.info(
                "Fetching all agents from Acronis API",
                extra={'operation_id': operation_id}
            )

            try:
                response_data = self._make_authenticated_request("GET", "/agent_manager/v2/agents")

                if response_data is None:
                    logger.warning(
                        "No response data received for agents request",
                        extra={'operation_id': operation_id}
                    )
                    return None

                if "items" in response_data:
                    agents = response_data["items"]
                    total_count = response_data.get("total", len(agents))
                    
                    logger.info(
                        f"Successfully fetched {len(agents)} agents (total: {total_count})",
                        extra={
                            'operation_id': operation_id,
                            'agents_count': len(agents),
                            'total_count': total_count,
                            'has_pagination': total_count > len(agents)
                        }
                    )
                    
                    # Log agent status summary
                    if agents:
                        online_count = sum(1 for agent in agents if agent.get('online', False))
                        offline_count = len(agents) - online_count
                        
                        logger.debug(
                            f"Agent status summary: {online_count} online, {offline_count} offline",
                            extra={
                                'operation_id': operation_id,
                                'online_agents': online_count,
                                'offline_agents': offline_count
                            }
                        )
                    
                    return agents
                else:
                    logger.warning(
                        "No 'items' field found in agents response",
                        extra={
                            'operation_id': operation_id,
                            'response_keys': list(response_data.keys()) if response_data else []
                        }
                    )
                    return []

            except AcronisAPIError as e:
                logger.error(
                    f"API error while fetching agents: {e}",
                    extra={
                        'operation_id': operation_id,
                        'error_code': e.error_code,
                        'recoverable': e.recoverable
                    }
                )
                # Return None to indicate failure, but don't re-raise to allow fallback behavior
                return None
            except Exception as e:
                logger.error(
                    f"Unexpected error while fetching agents: {e}",
                    extra={'operation_id': operation_id},
                    exc_info=True
                )
                return None

    def fetch_all_workloads(self) -> Optional[List[Dict]]:
        """
        Fetch all workloads from Acronis API.

        Returns:
            Optional[List[Dict]]: List of workload data or None if failed
        """
        logger.info("Fetching all workloads from Acronis API")

        try:
            response_data = self._make_authenticated_request("GET", "/workload_management/v5/workloads")

            if response_data and "items" in response_data:
                workloads = response_data["items"]
                logger.info(f"Successfully fetched {len(workloads)} workloads")
                return workloads
            else:
                logger.warning("No workloads data found in response")
                return []

        except Exception as e:
            logger.error(f"Failed to fetch workloads: {e}")
            return None

    def association_workload_agent(self) -> Optional[List[Dict]]:
        """
        Fetch workload-agent associations from Acronis API.

        Returns:
            Optional[List[Dict]]: List of association data or None if failed
        """
        logger.info("Fetching workload-agent associations from Acronis API")

        try:
            # Get both agents and workloads to create associations
            agents = self.fetch_all_agents()
            workloads = self.fetch_all_workloads()

            if agents is None or workloads is None:
                logger.error("Failed to fetch agents or workloads for association")
                return None

            associations = []

            # Create associations based on matching criteria (e.g., hostname, tenant)
            for workload in workloads:
                workload_hostname = workload.get("name", "").lower()
                workload_tenant = workload.get("tenant_id", "")

                for agent in agents:
                    agent_hostname = agent.get("hostname", "").lower()
                    agent_tenant = agent.get("tenant_id", "")

                    # Match by hostname and tenant
                    if (
                        workload_hostname == agent_hostname
                        and workload_tenant == agent_tenant
                    ):
                        association = {
                            "agent_id": agent.get("id"),
                            "workload_id": workload.get("id"),
                            "hostname": agent.get("hostname"),
                            "tenant_id": agent_tenant,
                        }
                        associations.append(association)
                        break

            logger.info(
                f"Successfully created {len(associations)} workload-agent associations"
            )
            return associations

        except Exception as e:
            logger.error(f"Failed to create workload-agent associations: {e}")
            return None

    def all_backup_info_workloads(self) -> Optional[Dict]:
        """
        Fetch backup information for all workloads.
        
        Returns:
            Optional[Dict]: Backup information for all workloads or None if failed
        """
        logger.info("Fetching backup information for all workloads")
        
        try:
            # Simplified approach: get backup activities directly without associations
            logger.info("Fetching backup activities directly")
            
            # Fetch backup activities for the last week (configurable)
            from datetime import datetime, timedelta
            
            # Get configurable time window (default 7 days)
            days_back = getattr(self, 'backup_days_window', 7)
            start_date = datetime.utcnow() - timedelta(days=days_back)
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            endpoint = f"/task_manager/v2/activities?order=desc(completedAt)&policyType=backup&completedAt=ge({start_date_str})"
            response_data = self._make_authenticated_request("GET", endpoint)
            
            if not response_data or "items" not in response_data:
                logger.warning("No backup activities found")
                return {
                    "summary": {"num_backups": 0, "success": 0, "failed": 0},
                    "workload_data": {}
                }
            
            workload_data = {}
            num_backups = 0
            success = 0
            
            # Process backup activities (simplified approach - show all backups)
            for item in response_data.get('items', []):
                # Only process parent activities (not sub-activities)
                if item.get("parentActivityId", None) is None:
                    
                    started_at = item.get('startedAt')
                    completed_at = item.get('completedAt')
                    
                    # Format timestamps
                    formatted_started_at = self.format_timestamp(started_at)
                    formatted_completed_at = self.format_timestamp(completed_at)
                    
                    num_backups += 1
                    result_code = item.get('result', {}).get('code', 'N/A')
                    success += 1 if result_code == 'ok' else 0
                    
                    backup_obj = {
                        'started_at': formatted_started_at,
                        'completed_at': formatted_completed_at,
                        'state': item.get('state', 'unknown'),
                        'run_mode': item.get('context', {}).get('runMode', 'N/A'),
                        'bytes_saved': item.get('progress', {}).get('bytesSaved', 0),
                        'result': result_code
                    }
                    
                    # Use resource ID as workload ID
                    resource_info = item.get('resource', {})
                    workload_id = resource_info.get('id', 'unknown')
                    workload_name = resource_info.get('name', 'Unknown')
                    
                    if workload_id not in workload_data:
                        workload_data[workload_id] = {
                            'backups': [],
                            'id_tenant': 'unknown',
                            'hostname': workload_name
                        }
                    
                    workload_data[workload_id]['backups'].append(backup_obj)
            
            # Return structure expected by routes.py
            result = {
                "summary": {
                    "num_backups": num_backups,
                    "success": success,
                    "failed": num_backups - success
                },
                "workload_data": workload_data
            }
            
            logger.info(f"Successfully processed {num_backups} backup activities")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch backup information for all workloads: {e}")
            return None

    def backup_info_workload(self, workload_id: str) -> Optional[Dict]:
        """
        Fetch backup information for a specific workload.

        Args:
            workload_id (str): Workload ID

        Returns:
            Optional[Dict]: Backup data for the workload or None if failed
        """
        logger.debug(f"Fetching backup information for workload {workload_id}")

        try:
            # Fetch backup activities for the workload using correct endpoint
            endpoint = f"/task_manager/v2/activities?resourceId={workload_id}&policyType=backup&order=desc(completedAt)"
            response_data = self._make_authenticated_request("GET", endpoint)

            if response_data and "items" in response_data:
                activities = response_data["items"]

                # Process backup activities into structured format
                backups = []
                for activity in activities:
                    # Only process parent activities (no parentActivityId)
                    if activity.get("parentActivityId") is None:
                        backup = {
                            "started_at": self.format_timestamp(activity.get("startedAt", "")),
                            "completed_at": self.format_timestamp(activity.get("completedAt", "")),
                            "state": activity.get("state", "unknown"),
                            "run_mode": activity.get("context", {}).get("runMode", "unknown"),
                            "bytes_saved": activity.get("progress", {}).get("bytesSaved", 0),
                            "result": activity.get("result", {}).get("code", "unknown"),
                        }
                        backups.append(backup)

                # Get workload details from associations
                associations = self.association_workload_agent()
                workload_name = "Unknown"
                tenant_id = "Unknown"
                
                for assoc in associations or []:
                    if assoc.get('id_workload') == workload_id:
                        workload_name = assoc.get('hostname', 'Unknown')
                        tenant_id = assoc.get('id_tenant', 'Unknown')
                        break

                result = {
                    "hostname": workload_name,
                    "id_tenant": tenant_id,
                    "backups": backups,
                }

                logger.debug(
                    f"Successfully fetched {len(backups)} backups for workload {workload_id}"
                )
                return result
            else:
                logger.debug(f"No backup activities found for workload {workload_id}")
                return {"hostname": "Unknown", "id_tenant": "Unknown", "backups": []}

        except Exception as e:
            logger.error(f"Failed to fetch backup info for workload {workload_id}: {e}")
            return None

    def format_timestamp(self, timestamp: str) -> str:
        """
        Format timestamp string to a consistent format.

        Args:
            timestamp (str): ISO timestamp string

        Returns:
            str: Formatted timestamp string
        """
        if not timestamp:
            return "N/A"

        try:
            from datetime import datetime, timedelta
            # Try to convert considering nanoseconds or milliseconds
            dt = datetime.strptime(timestamp[:-1][:26], "%Y-%m-%dT%H:%M:%S.%f")
            dt = dt + timedelta(hours=1)  # Adjust timezone as in working code
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            return 'N/A'

    @handle_api_errors("test_connection")
    @log_performance("test_connection")
    def test_connection(self) -> bool:
        """
        Test the connection to Acronis API with comprehensive diagnostics.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        with error_context("test_connection", base_url=self.base_url) as operation_id:
            logger.info(
                "Testing connection to Acronis API",
                extra={
                    'operation_id': operation_id,
                    'base_url': self.base_url,
                    'client_id': self.client_id[:8] + '...' if len(self.client_id) > 8 else self.client_id
                }
            )

            connection_details = {
                'token_obtained': False,
                'api_accessible': False,
                'tenants_accessible': False,
                'error_details': None
            }

            try:
                # Step 1: Test token acquisition
                logger.debug("Step 1: Testing token acquisition", extra={'operation_id': operation_id})
                token = self.get_token()
                
                if not token:
                    logger.error(
                        "Connection test failed: Could not obtain authentication token",
                        extra={'operation_id': operation_id, **connection_details}
                    )
                    return False
                
                connection_details['token_obtained'] = True
                logger.debug("Token acquisition successful", extra={'operation_id': operation_id})

                # Step 2: Test basic API accessibility
                logger.debug("Step 2: Testing basic API accessibility", extra={'operation_id': operation_id})
                
                try:
                    # Try to fetch agents as a basic connectivity test (based on working implementation)
                    response_data = self._make_authenticated_request("GET", "/agent_manager/v2/agents")
                    
                    if response_data is not None:
                        connection_details['api_accessible'] = True
                        connection_details['agents_accessible'] = True
                        
                        # Log additional connection info
                        agent_count = len(response_data.get('items', [])) if isinstance(response_data, dict) else 0
                        
                        logger.info(
                            f"Connection test successful - API accessible, {agent_count} agents found",
                            extra={
                                'operation_id': operation_id,
                                'agent_count': agent_count,
                                **connection_details
                            }
                        )
                        return True
                    else:
                        logger.warning(
                            "Connection test partial success: Token obtained but API returned no data",
                            extra={'operation_id': operation_id, **connection_details}
                        )
                        return False
                        
                except AcronisAuthenticationError as e:
                    connection_details['error_details'] = {
                        'type': 'authentication',
                        'message': str(e),
                        'error_code': e.error_code
                    }
                    logger.error(
                        f"Connection test failed: Authentication error - {e}",
                        extra={'operation_id': operation_id, **connection_details}
                    )
                    return False
                    
                except AcronisConnectionError as e:
                    connection_details['error_details'] = {
                        'type': 'connection',
                        'message': str(e),
                        'error_code': e.error_code
                    }
                    logger.error(
                        f"Connection test failed: Connection error - {e}",
                        extra={'operation_id': operation_id, **connection_details}
                    )
                    return False

            except AcronisAuthenticationError as e:
                connection_details['error_details'] = {
                    'type': 'authentication',
                    'message': str(e),
                    'error_code': e.error_code
                }
                logger.error(
                    f"Connection test failed: Authentication error during token acquisition - {e}",
                    extra={'operation_id': operation_id, **connection_details}
                )
                return False
                
            except AcronisConnectionError as e:
                connection_details['error_details'] = {
                    'type': 'connection',
                    'message': str(e),
                    'error_code': e.error_code
                }
                logger.error(
                    f"Connection test failed: Connection error - {e}",
                    extra={'operation_id': operation_id, **connection_details}
                )
                return False
                
            except Exception as e:
                connection_details['error_details'] = {
                    'type': 'unexpected',
                    'message': str(e),
                    'error_type': type(e).__name__
                }
                logger.error(
                    f"Connection test failed: Unexpected error - {e}",
                    extra={'operation_id': operation_id, **connection_details},
                    exc_info=True
                )
                return False
