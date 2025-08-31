# PMI Dashboard Architecture Documentation

This document provides a comprehensive overview of the PMI Dashboard architecture, design patterns, and implementation details.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Performance Considerations](#performance-considerations)
8. [Scalability Design](#scalability-design)
9. [Error Handling Strategy](#error-handling-strategy)
10. [Logging Architecture](#logging-architecture)

## System Overview

PMI Dashboard is a modern web application built with Flask (Python) backend and vanilla JavaScript frontend, designed for managing Proxmox VE infrastructure with real-time monitoring capabilities.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser  │  Mobile App  │  PWA  │  API Clients            │
└─────────────────────────────────────────────────────────────────┘
                                │
                               HTTPS
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Static Assets  │  Templates  │  JavaScript Modules            │
│  (CSS, JS, Images)  │  (Jinja2)  │  (ES6+ Modules)            │
└─────────────────────────────────────────────────────────────────┘
                                │
                          Flask Routes
                                │
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  Flask App  │  Blueprints  │  Middleware  │  Error Handlers    │
│  (app.py)   │  (routes.py) │  (logging)   │  (global)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                          Service Calls
                                │
┌─────────────────────────────────────────────────────────────────┐
│                     Business Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  API Clients  │  Models  │  History Mgr  │  Config Mgr        │
│  (api_client) │ (models) │  (history)    │  (config)          │
└─────────────────────────────────────────────────────────────────┘
                                │
                          API Calls / File I/O
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  JSON Files  │  Log Files  │  Proxmox API  │  Browser Storage  │
│  (config)    │  (logs)     │  (external)   │  (localStorage)   │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture Patterns

### 1. Application Factory Pattern

The Flask application uses the factory pattern for better testability and configuration management:

```python
def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize components
    Config.init_app(app)
    setup_logging(app)
    
    # Register blueprints
    from proxmox.routes import proxmox_bp
    app.register_blueprint(proxmox_bp)
    
    return app
```

### 2. Blueprint Pattern

Modular organization using Flask Blueprints:

```python
# proxmox/routes.py
proxmox_bp = Blueprint('proxmox', __name__, url_prefix='/api/proxmox')

@proxmox_bp.route('/nodes', methods=['GET'])
def get_nodes():
    # Implementation
```

### 3. Repository Pattern

Data access abstraction through manager classes:

```python
class ProxmoxConfigManager:
    """Abstracts JSON file operations for node configuration"""
    
    def get_all_nodes(self) -> List[Dict]:
        """Get all configured nodes"""
    
    def add_node(self, config: Dict) -> str:
        """Add new node configuration"""
```

### 4. Factory Pattern for API Clients

Dynamic client creation based on configuration:

```python
def create_client_from_config(node_config: Dict) -> ProxmoxAPIClient:
    """Create API client from node configuration"""
    return ProxmoxAPIClient(
        host=node_config["host"],
        port=node_config.get("port", 8006),
        # ... other parameters
    )
```

### 5. Observer Pattern

Event-driven frontend architecture:

```javascript
// Theme change events
document.addEventListener('themechange', (e) => {
    console.log('Theme changed to:', e.detail.theme);
});

// Custom event dispatch
const event = new CustomEvent('themechange', {
    detail: { theme: newTheme }
});
document.dispatchEvent(event);
```

## Backend Architecture

### Flask Application Structure

```
app.py                          # Application factory and main entry point
├── create_app()               # Flask app factory function
├── Error Handlers             # Global exception handling
├── Request Middleware         # Timing, security, logging
└── Blueprint Registration     # Modular route organization

config.py                      # Configuration management
├── Config                     # Environment variable handling
├── ProxmoxConfigManager      # JSON configuration management
└── Validation                # Configuration validation

logging_config.py             # Comprehensive logging system
├── Multiple Loggers          # App, error, API, security, performance
├── Structured Logging        # Context-aware log formatting
└── Log Rotation             # Automatic log file management

proxmox/                      # Proxmox integration module
├── __init__.py              # Module exports and initialization
├── api_client.py            # Proxmox API communication
├── models.py                # Data models and validation
├── routes.py                # REST API endpoints
└── history.py               # Operation history management
```

### Data Models

The application uses dataclasses for type-safe data modeling:

```python
@dataclass
class ProxmoxNode:
    """Data model for Proxmox node configuration and status"""
    id: str
    name: str
    host: str
    port: int = 8006
    # ... additional fields with type hints
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxmoxNode':
        """Create instance from dictionary"""
```

### API Client Architecture

The Proxmox API client implements:

- **Connection Management**: Session reuse and connection pooling
- **Error Handling**: Comprehensive exception hierarchy
- **Retry Logic**: Automatic retry with exponential backoff
- **Timeout Management**: Configurable timeouts per operation
- **SSL Handling**: Flexible SSL verification options

```python
class ProxmoxAPIClient:
    """Comprehensive Proxmox API client"""
    
    def __init__(self, host, port, api_token_id, api_token_secret, ...):
        self.session = requests.Session()
        # Configure authentication, SSL, timeouts
    
    def _make_request(self, method, endpoint, data=None):
        """Core request method with error handling"""
        # Implement retry logic, error handling, logging
    
    def get_vm_metrics(self, node, vmid):
        """Get real-time VM metrics"""
        # Combine multiple API calls for comprehensive metrics
```

## Frontend Architecture

### Module Organization

```
static/js/
├── main.js                   # Core dashboard functionality
├── theme.js                  # Theme management system
├── proxmox.js               # Proxmox API client
├── notifications.js         # Toast notification system
├── error-handler.js         # Error handling and recovery
├── metrics-init.js          # Metrics system initialization
├── metrics-monitor.js       # Real-time metrics monitoring
├── metrics-visualizer.js    # Metrics visualization components
├── node-config.js           # Node configuration management
├── node-dashboard.js        # Node dashboard components
├── operation-history.js     # Operation history display
├── resource-manager.js      # VM/LXC resource management
└── resources.js             # Resource display components
```

### Component Architecture

Each JavaScript module follows a class-based architecture:

```javascript
class PMIDashboard {
    constructor() {
        this.currentTab = 'proxmox';
        this.isMobile = this.detectMobile();
        this.init();
    }
    
    init() {
        this.setupNavigation();
        this.setupEventListeners();
        this.setupAccessibility();
        this.setupMobileOptimizations();
    }
    
    // Method implementations...
}
```

### State Management

The frontend uses a combination of:

- **DOM State**: Current UI state stored in DOM attributes
- **Local Storage**: Persistent user preferences (theme, settings)
- **Memory State**: Runtime state in JavaScript objects
- **Server State**: Real-time data fetched from API

### Event System

Custom event system for component communication:

```javascript
// Event dispatch
document.dispatchEvent(new CustomEvent('tabchange', {
    detail: { tab: tabName, previousTab: this.currentTab }
}));

// Event listening
document.addEventListener('tabchange', (e) => {
    // Handle tab change
});
```

## Data Flow

### Request Flow

1. **Client Request**: Browser/mobile app makes HTTP request
2. **Flask Routing**: Request routed to appropriate blueprint
3. **Middleware Processing**: Logging, security checks, timing
4. **Business Logic**: Service layer processes request
5. **Data Access**: Configuration files or Proxmox API calls
6. **Response Formation**: Data formatted and returned
7. **Client Processing**: Frontend updates UI with response

### Real-time Metrics Flow

```
Frontend Timer → API Request → Flask Route → API Client → Proxmox API
     ↑                                                        ↓
UI Update ← Response Processing ← JSON Response ← Data Processing
```

### Configuration Flow

```
Environment Variables → Config Class → Validation → Application Setup
JSON Files → ConfigManager → CRUD Operations → API Responses
```

## Security Architecture

### Authentication & Authorization

- **API Tokens**: Proxmox API token-based authentication
- **Session Management**: Flask session handling with secure cookies
- **CSRF Protection**: Built-in Flask-WTF CSRF protection
- **Input Validation**: Comprehensive input sanitization

### Security Headers

```python
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if app.config.get('FORCE_HTTPS'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response
```

### Data Protection

- **Sensitive Data**: API tokens encrypted at rest
- **Logging**: Sensitive information filtered from logs
- **File Permissions**: Restricted access to configuration files
- **SSL/TLS**: HTTPS enforcement in production

## Performance Considerations

### Backend Optimizations

- **Connection Pooling**: Reuse HTTP connections to Proxmox
- **Caching**: In-memory caching of frequently accessed data
- **Async Operations**: Non-blocking operations where possible
- **Database Indexing**: Efficient data retrieval (future enhancement)

### Frontend Optimizations

- **Lazy Loading**: Load components on demand
- **Debouncing**: Prevent excessive API calls
- **Efficient DOM Updates**: Minimize DOM manipulation
- **Resource Compression**: Minified CSS/JS in production

### Network Optimizations

- **HTTP/2**: Support for multiplexed connections
- **Compression**: Gzip compression for responses
- **CDN**: Static asset delivery (future enhancement)
- **Caching Headers**: Appropriate cache control headers

## Scalability Design

### Horizontal Scaling

- **Stateless Design**: Application can run multiple instances
- **Load Balancing**: Support for load balancer deployment
- **Session Storage**: External session storage (Redis, future)
- **Database**: Scalable database backend (future enhancement)

### Vertical Scaling

- **Resource Monitoring**: Built-in performance monitoring
- **Memory Management**: Efficient memory usage patterns
- **CPU Optimization**: Optimized algorithms and data structures
- **I/O Optimization**: Efficient file and network operations

### Future Enhancements

- **Microservices**: Split into smaller services
- **Message Queues**: Async task processing
- **Caching Layer**: Redis/Memcached integration
- **Database**: PostgreSQL/MySQL support

## Error Handling Strategy

### Exception Hierarchy

```python
class ProxmoxAPIError(Exception):
    """Base exception for Proxmox API errors"""

class ProxmoxAuthenticationError(ProxmoxAPIError):
    """Authentication-specific errors"""

class ProxmoxConnectionError(ProxmoxAPIError):
    """Connection-specific errors"""
```

### Error Recovery

- **Retry Logic**: Automatic retry with exponential backoff
- **Graceful Degradation**: Partial functionality when services fail
- **User Feedback**: Clear error messages with recovery suggestions
- **Logging**: Comprehensive error logging with context

### Frontend Error Handling

```javascript
class ErrorHandler {
    static handleApiError(error, operation, retryCallback) {
        // Categorize error
        // Show appropriate user message
        // Provide recovery options
        // Log for debugging
    }
}
```

## Logging Architecture

### Multi-Level Logging

```python
# Application logs - General operation
app_logger = logging.getLogger('pmi_dashboard')

# Error logs - Errors with full context
error_logger = logging.getLogger('pmi_dashboard.errors')

# API logs - Request/response logging
api_logger = logging.getLogger('pmi_dashboard.api')

# Security logs - Security events
security_logger = logging.getLogger('pmi_dashboard.security')

# Performance logs - Timing and metrics
perf_logger = logging.getLogger('pmi_dashboard.performance')
```

### Structured Logging

```python
# Context-aware logging
logger.error("Operation failed", extra={
    'method': request.method,
    'url': request.url,
    'user_agent': request.headers.get('User-Agent'),
    'remote_addr': request.remote_addr,
    'operation_id': operation_id
})
```

### Log Rotation

- **Size-based**: Rotate when files reach size limit
- **Time-based**: Daily/weekly rotation schedules
- **Retention**: Configurable retention periods
- **Compression**: Automatic compression of old logs

## Deployment Architecture

### Development Environment

```
Developer Machine
├── Python Virtual Environment
├── Local Flask Development Server
├── File-based Configuration
└── Console Logging
```

### Production Environment

```
Production Server
├── WSGI Server (Gunicorn/uWSGI)
├── Reverse Proxy (Nginx/Apache)
├── SSL Termination
├── Log Aggregation
├── Monitoring & Alerting
└── Backup & Recovery
```

### Container Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
```

This architecture provides a solid foundation for a scalable, maintainable, and secure infrastructure management dashboard.