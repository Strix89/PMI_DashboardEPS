# PMI Dashboard Development Guide

This guide provides comprehensive information for developers working on the PMI Dashboard project, including setup, coding standards, testing, and contribution guidelines.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Coding Standards](#coding-standards)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Performance Optimization](#performance-optimization)
8. [Contributing](#contributing)
9. [Release Process](#release-process)

## Development Environment Setup

### Prerequisites

- **Python**: 3.8+ (recommended: 3.11+)
- **Node.js**: 16+ (for frontend tooling, optional)
- **Git**: Latest version
- **IDE**: VS Code, PyCharm, or similar with Python support

### Quick Setup

```bash
# Clone repository
git clone <repository-url>
cd pmi_dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Copy configuration
cp .env .env.local

# Run application
python app.py
```

### Development Dependencies

Create `requirements-dev.txt`:
```
# Testing
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-flask>=1.2.0

# Code Quality
flake8>=6.0.0
black>=23.0.0
isort>=5.12.0
mypy>=1.0.0

# Documentation
sphinx>=6.0.0
sphinx-rtd-theme>=1.2.0

# Development Tools
pre-commit>=3.0.0
watchdog>=3.0.0
```

### IDE Configuration

#### VS Code Settings (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".mypy_cache": true
    }
}
```

#### PyCharm Configuration
1. **Interpreter**: Set to `./venv/bin/python`
2. **Code Style**: Configure Black formatter
3. **Inspections**: Enable type checking and PEP 8
4. **Run Configurations**: Create Flask run configuration

### Pre-commit Hooks

Install pre-commit hooks:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## Project Structure

### Backend Architecture

```
pmi_dashboard/
├── app.py                      # Flask application factory
├── config.py                   # Configuration management
├── logging_config.py           # Logging system setup
├── proxmox/                    # Proxmox integration module
│   ├── __init__.py            # Module initialization
│   ├── api_client.py          # Proxmox API client
│   ├── models.py              # Data models
│   ├── routes.py              # Flask routes
│   └── history.py             # Operation history
├── static/                     # Static assets
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript modules
│   └── images/                # Images and icons
├── templates/                  # Jinja2 templates
│   ├── base.html              # Base template
│   ├── index.html             # Main page
│   └── components/            # Reusable components
├── data/                       # Application data
├── logs/                       # Log files
├── tests/                      # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test fixtures
└── docs/                       # Documentation
```

### Module Responsibilities

#### Core Modules
- **app.py**: Application factory, error handling, middleware
- **config.py**: Configuration management, validation
- **logging_config.py**: Multi-level logging system

#### Proxmox Module
- **api_client.py**: Proxmox API communication
- **models.py**: Data models and validation
- **routes.py**: REST API endpoints
- **history.py**: Operation tracking

#### Frontend Modules
- **main.js**: Core dashboard functionality
- **theme.js**: Theme management
- **proxmox.js**: API client
- **notifications.js**: User notifications
- **metrics-*.js**: Real-time metrics

## Coding Standards

### Python Standards

#### PEP 8 Compliance
- Line length: 88 characters (Black default)
- Indentation: 4 spaces
- Import organization: isort with Black profile

#### Type Hints
```python
from typing import Dict, List, Optional, Any, Union

def process_node_data(
    node_config: Dict[str, Any], 
    timeout: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Process node configuration data.
    
    Args:
        node_config: Node configuration dictionary
        timeout: Optional timeout in seconds
        
    Returns:
        List of processed node data
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    # Implementation
```

#### Error Handling
```python
class ProxmoxAPIError(Exception):
    """Base exception for Proxmox API errors."""
    pass

class ProxmoxConnectionError(ProxmoxAPIError):
    """Connection-specific errors."""
    pass

def api_call() -> Dict[str, Any]:
    """Make API call with proper error handling."""
    try:
        response = make_request()
        return response.json()
    except requests.ConnectionError as e:
        raise ProxmoxConnectionError(f"Connection failed: {e}")
    except requests.Timeout as e:
        raise ProxmoxAPIError(f"Request timeout: {e}")
```

#### Docstring Format
```python
def complex_function(param1: str, param2: int, param3: Optional[bool] = None) -> Dict[str, Any]:
    """
    Brief description of the function.
    
    Longer description explaining the function's purpose, behavior,
    and any important implementation details.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        param3: Optional parameter description
        
    Returns:
        Description of return value and its structure
        
    Raises:
        SpecificError: When this specific error occurs
        AnotherError: When this other error occurs
        
    Example:
        >>> result = complex_function("test", 42, True)
        >>> print(result["status"])
        "success"
    """
    # Implementation
```

### JavaScript Standards

#### ES6+ Features
```javascript
// Use modern JavaScript features
class APIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.defaultTimeout = 30000;
    }
    
    async makeRequest(method, endpoint, data = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
            signal: AbortSignal.timeout(this.defaultTimeout)
        };
        
        if (data && ['POST', 'PUT'].includes(method)) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            return await response.json();
        } catch (error) {
            throw new APIError(`Request failed: ${error.message}`);
        }
    }
}
```

#### JSDoc Comments
```javascript
/**
 * Manages theme switching and persistence
 * @class
 */
class ThemeManager {
    /**
     * Create a theme manager
     * @param {string} storageKey - LocalStorage key for theme preference
     * @param {string} defaultTheme - Default theme to use
     */
    constructor(storageKey = 'theme', defaultTheme = 'dark') {
        this.storageKey = storageKey;
        this.defaultTheme = defaultTheme;
    }
    
    /**
     * Toggle between light and dark themes
     * @returns {string} The new active theme
     */
    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        return newTheme;
    }
}
```

### CSS Standards

#### BEM Methodology
```css
/* Block */
.node-card {
    display: flex;
    flex-direction: column;
    border-radius: 8px;
}

/* Element */
.node-card__header {
    padding: 16px;
    border-bottom: 1px solid var(--border-color);
}

.node-card__title {
    font-size: 1.2rem;
    font-weight: 600;
}

/* Modifier */
.node-card--offline {
    opacity: 0.6;
    border-color: var(--error-color);
}

.node-card--loading {
    pointer-events: none;
}
```

#### CSS Custom Properties
```css
:root {
    /* Color System */
    --primary-color: #ff6b35;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --error-color: #dc3545;
    
    /* Theme Colors */
    --bg-primary: #ffffff;
    --bg-secondary: #f8f9fa;
    --text-primary: #212529;
    --text-secondary: #6c757d;
    
    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
}

[data-theme="dark"] {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #ffffff;
    --text-secondary: #b0b0b0;
}
```

## Development Workflow

### Git Workflow

#### Branch Strategy
```bash
# Main branches
main                    # Production-ready code
develop                 # Integration branch

# Feature branches
feature/node-management # New features
bugfix/api-timeout     # Bug fixes
hotfix/security-patch  # Critical fixes
```

#### Commit Messages
```bash
# Format: type(scope): description

feat(api): add node metrics endpoint
fix(ui): resolve mobile navigation issue
docs(readme): update installation instructions
style(css): improve button hover states
refactor(config): simplify validation logic
test(api): add integration tests for node management
chore(deps): update Flask to 2.3.3
```

#### Pull Request Process
1. **Create Feature Branch**: `git checkout -b feature/new-feature`
2. **Implement Changes**: Follow coding standards
3. **Add Tests**: Ensure test coverage
4. **Update Documentation**: Update relevant docs
5. **Run Tests**: `pytest` and `flake8`
6. **Create PR**: Detailed description with testing notes
7. **Code Review**: Address feedback
8. **Merge**: Squash and merge to develop

### Development Commands

#### Common Tasks
```bash
# Run application
python app.py

# Run with auto-reload
export FLASK_DEBUG=True
python app.py

# Run tests
pytest

# Run tests with coverage
pytest --cov=pmi_dashboard --cov-report=html

# Code formatting
black .
isort .

# Linting
flake8 .
mypy .

# Type checking
mypy pmi_dashboard/

# Generate documentation
cd docs && make html
```

#### Database Operations (Future)
```bash
# Initialize database
flask db init

# Create migration
flask db migrate -m "Add user table"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## Testing

### Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── unit/                       # Unit tests
│   ├── test_config.py         # Configuration tests
│   ├── test_api_client.py     # API client tests
│   └── test_models.py         # Model tests
├── integration/                # Integration tests
│   ├── test_api_endpoints.py  # API endpoint tests
│   └── test_workflows.py      # Complete workflow tests
├── fixtures/                   # Test data
│   ├── node_configs.json     # Sample configurations
│   └── api_responses.json     # Mock API responses
└── utils/                      # Test utilities
    └── helpers.py             # Test helper functions
```

### Unit Tests

#### Configuration Tests
```python
# tests/unit/test_config.py
import pytest
from config import Config, ProxmoxConfigManager, ConfigurationError

class TestConfig:
    def test_default_values(self):
        """Test default configuration values."""
        assert Config.PORT == 5000
        assert Config.PROXMOX_DEFAULT_PORT == 8006
        
    def test_validation_errors(self):
        """Test configuration validation."""
        # Test invalid port
        Config.PORT = 70000
        messages = Config.validate_configuration()
        assert any("Invalid PORT value" in msg for msg in messages)

class TestProxmoxConfigManager:
    def test_add_node(self, tmp_path):
        """Test adding a new node."""
        config_file = tmp_path / "test_config.json"
        manager = ProxmoxConfigManager(str(config_file))
        
        node_config = {
            "name": "Test Node",
            "host": "192.168.1.100",
            "api_token_id": "test@pam!token",
            "api_token_secret": "secret"
        }
        
        node_id = manager.add_node(node_config)
        assert node_id is not None
        
        nodes = manager.get_all_nodes()
        assert len(nodes) == 1
        assert nodes[0]["name"] == "Test Node"
```

#### API Client Tests
```python
# tests/unit/test_api_client.py
import pytest
from unittest.mock import Mock, patch
from proxmox.api_client import ProxmoxAPIClient, ProxmoxConnectionError

class TestProxmoxAPIClient:
    def test_initialization(self):
        """Test client initialization."""
        client = ProxmoxAPIClient(
            host="test.example.com",
            port=8006,
            api_token_id="test@pam!token",
            api_token_secret="secret"
        )
        
        assert client.host == "test.example.com"
        assert client.port == 8006
        assert "test@pam!token" in client.session.headers["Authorization"]
    
    @patch('requests.Session.request')
    def test_successful_request(self, mock_request):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"version": "7.4-3"}}
        mock_request.return_value = mock_response
        
        client = ProxmoxAPIClient("test.com", 8006, "token", "secret")
        result = client._make_request("GET", "/version")
        
        assert result["version"] == "7.4-3"
    
    @patch('requests.Session.request')
    def test_connection_error(self, mock_request):
        """Test connection error handling."""
        mock_request.side_effect = ConnectionError("Connection failed")
        
        client = ProxmoxAPIClient("test.com", 8006, "token", "secret")
        
        with pytest.raises(ProxmoxConnectionError):
            client._make_request("GET", "/version")
```

### Integration Tests

#### API Endpoint Tests
```python
# tests/integration/test_api_endpoints.py
import pytest
from app import create_app

@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestNodeEndpoints:
    def test_get_nodes_empty(self, client):
        """Test getting nodes when none configured."""
        response = client.get('/api/proxmox/nodes')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []
    
    def test_add_node_success(self, client):
        """Test adding a new node."""
        node_data = {
            "name": "Test Node",
            "host": "192.168.1.100",
            "api_token_id": "test@pam!token",
            "api_token_secret": "secret"
        }
        
        response = client.post('/api/proxmox/nodes', json=node_data)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'node_id' in data['data']
    
    def test_add_node_validation_error(self, client):
        """Test node validation errors."""
        invalid_data = {"name": "Test"}  # Missing required fields
        
        response = client.post('/api/proxmox/nodes', json=invalid_data)
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert 'Missing required field' in data['error']
```

### Test Fixtures

#### conftest.py
```python
# tests/conftest.py
import pytest
import tempfile
import os
from app import create_app
from config import ProxmoxConfigManager

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "DATA_DIR": tempfile.mkdtemp(),
    })
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def temp_config_file():
    """Create temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"nodes": [], "metadata": {}}')
        temp_file = f.name
    
    yield temp_file
    
    os.unlink(temp_file)

@pytest.fixture
def sample_node_config():
    """Sample node configuration for testing."""
    return {
        "name": "Test Node",
        "host": "192.168.1.100",
        "port": 8006,
        "api_token_id": "test@pam!token",
        "api_token_secret": "test-secret",
        "ssl_verify": False
    }
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_config.py

# Run with coverage
pytest --cov=pmi_dashboard --cov-report=html

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf

# Run tests matching pattern
pytest -k "test_node"
```

## Debugging

### Debug Configuration

#### Flask Debug Mode
```python
# .env.local
FLASK_DEBUG=True
LOG_LEVEL=DEBUG

# Enable detailed error pages and auto-reload
```

#### Logging Configuration
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Log API requests
logger = logging.getLogger('pmi_dashboard.api')
logger.setLevel(logging.DEBUG)
```

### Debugging Tools

#### Python Debugger
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()

# Debug specific function
def problematic_function():
    import pdb; pdb.set_trace()
    # Code to debug
```

#### VS Code Debugging
Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask Debug",
            "type": "python",
            "request": "launch",
            "program": "app.py",
            "env": {
                "FLASK_DEBUG": "1"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

#### Browser Developer Tools
```javascript
// Add console debugging
console.log('Debug info:', data);
console.error('Error occurred:', error);
console.table(arrayData);

// Add breakpoints
debugger;

// Performance monitoring
console.time('API Call');
await apiCall();
console.timeEnd('API Call');
```

### Common Issues

#### Configuration Problems
```bash
# Check configuration validation
python -c "from config import Config; print(Config.validate_configuration())"

# Check environment variables
python -c "import os; print(os.environ.get('SECRET_KEY'))"
```

#### API Connection Issues
```bash
# Test Proxmox connectivity
curl -k https://proxmox-server:8006/api2/json/version

# Check API token
curl -k -H "Authorization: PVEAPIToken=user@realm!tokenid=secret" \
  https://proxmox-server:8006/api2/json/version
```

#### Frontend Issues
```javascript
// Check API responses
fetch('/api/proxmox/nodes')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error(error));

// Check theme system
console.log(document.documentElement.getAttribute('data-theme'));
```

## Performance Optimization

### Backend Optimization

#### Database Queries (Future)
```python
# Use query optimization
from sqlalchemy.orm import joinedload

def get_nodes_with_resources():
    return session.query(Node).options(
        joinedload(Node.resources)
    ).all()
```

#### Caching
```python
from functools import lru_cache
from flask_caching import Cache

# Memory caching
@lru_cache(maxsize=128)
def get_node_metrics(node_id: str) -> Dict:
    """Cache node metrics for 30 seconds."""
    return fetch_metrics_from_api(node_id)

# Redis caching (future)
cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@cache.memoize(timeout=30)
def get_cached_data(key: str) -> Any:
    return expensive_operation(key)
```

#### Async Operations
```python
import asyncio
import aiohttp

async def fetch_multiple_nodes(node_configs: List[Dict]) -> List[Dict]:
    """Fetch data from multiple nodes concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_node_data(session, config) 
            for config in node_configs
        ]
        return await asyncio.gather(*tasks)
```

### Frontend Optimization

#### Lazy Loading
```javascript
// Lazy load components
const loadComponent = async (componentName) => {
    const module = await import(`./components/${componentName}.js`);
    return module.default;
};

// Intersection Observer for lazy loading
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            loadComponent(entry.target.dataset.component);
        }
    });
});
```

#### Debouncing
```javascript
// Debounce API calls
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

const debouncedSearch = debounce(searchFunction, 300);
```

#### Virtual Scrolling
```javascript
// Virtual scrolling for large lists
class VirtualScrollList {
    constructor(container, itemHeight, items) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.items = items;
        this.visibleStart = 0;
        this.visibleEnd = 0;
        this.init();
    }
    
    init() {
        this.container.addEventListener('scroll', () => {
            this.updateVisibleItems();
        });
        this.updateVisibleItems();
    }
    
    updateVisibleItems() {
        const scrollTop = this.container.scrollTop;
        const containerHeight = this.container.clientHeight;
        
        this.visibleStart = Math.floor(scrollTop / this.itemHeight);
        this.visibleEnd = Math.min(
            this.visibleStart + Math.ceil(containerHeight / this.itemHeight) + 1,
            this.items.length
        );
        
        this.render();
    }
}
```

## Contributing

### Contribution Guidelines

1. **Fork Repository**: Create personal fork
2. **Create Branch**: Use descriptive branch names
3. **Follow Standards**: Adhere to coding standards
4. **Add Tests**: Include comprehensive tests
5. **Update Docs**: Update relevant documentation
6. **Submit PR**: Create detailed pull request

### Code Review Checklist

#### Functionality
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error handling implemented
- [ ] Performance considerations addressed

#### Code Quality
- [ ] Follows coding standards
- [ ] Proper type hints (Python)
- [ ] Comprehensive docstrings
- [ ] No code duplication

#### Testing
- [ ] Unit tests added/updated
- [ ] Integration tests included
- [ ] Test coverage maintained
- [ ] All tests pass

#### Documentation
- [ ] Code comments added
- [ ] API documentation updated
- [ ] README updated if needed
- [ ] Changelog entry added

### Issue Reporting

#### Bug Reports
```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: Ubuntu 22.04
- Python: 3.11.0
- Browser: Chrome 108

**Additional Context**
Any additional information
```

#### Feature Requests
```markdown
**Feature Description**
Clear description of the proposed feature

**Use Case**
Why is this feature needed?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other approaches considered

**Additional Context**
Any additional information
```

## Release Process

### Version Management

#### Semantic Versioning
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

Example: `1.2.3`
- Major: 1
- Minor: 2
- Patch: 3

#### Release Branches
```bash
# Create release branch
git checkout -b release/1.2.0 develop

# Finalize release
git checkout main
git merge --no-ff release/1.2.0
git tag -a v1.2.0 -m "Release version 1.2.0"

# Merge back to develop
git checkout develop
git merge --no-ff release/1.2.0
```

### Release Checklist

#### Pre-Release
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Changelog updated
- [ ] Security review completed

#### Release
- [ ] Create release branch
- [ ] Final testing
- [ ] Tag release
- [ ] Build artifacts
- [ ] Deploy to staging

#### Post-Release
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Update documentation
- [ ] Announce release

This development guide provides comprehensive information for contributing to the PMI Dashboard project while maintaining high code quality and consistency.