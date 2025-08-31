# PMI Dashboard Configuration Guide

This guide explains how to configure the PMI Dashboard application using the configuration management system.

## Overview

The PMI Dashboard uses a two-tier configuration system:

1. **Environment Variables** (`.env` file) - Application settings, Flask configuration, and defaults
2. **JSON Configuration Files** - Dynamic data like Proxmox node connections

## Environment Configuration (.env file)

### Setup

1. Copy the `.env` file to create your configuration
2. Modify the values according to your environment
3. Never commit your actual `.env` file to version control

### Key Configuration Sections

#### Flask Application Settings
```bash
SECRET_KEY=your-secret-key-here          # CRITICAL: Change in production!
FLASK_HOST=127.0.0.1                     # Server bind address
FLASK_PORT=5000                          # Server port
FLASK_DEBUG=True                         # Debug mode (False for production)
```

#### Data Storage
```bash
DATA_DIR=./data                          # Directory for application data
PROXMOX_CONFIG_FILE=proxmox_config.json  # Proxmox configuration file name
```

#### Proxmox Defaults
```bash
PROXMOX_DEFAULT_PORT=8006                # Default Proxmox API port
PROXMOX_SSL_VERIFY=False                 # SSL certificate verification
PROXMOX_TIMEOUT=30                       # API connection timeout (seconds)
```

#### Monitoring Settings
```bash
METRICS_REFRESH_INTERVAL=10              # Real-time metrics refresh interval (seconds)
```

### Configuration Validation

The system automatically validates configuration on startup:
- **Errors**: Will prevent the application from starting
- **Warnings**: Will be logged but won't stop the application

Common validation messages:
- `WARNING: Using default SECRET_KEY` - Change the secret key for production
- `ERROR: Invalid PORT value` - Port must be between 1-65535
- `WARNING: PROXMOX_TIMEOUT value seems unusual` - Timeout outside recommended range

## Proxmox Node Configuration

### Automatic Management

The system automatically creates and manages the Proxmox configuration file:
- Creates `data/proxmox_config.json` on first run
- Validates node configurations when added/updated
- Maintains metadata (creation time, last modified)

### Configuration Structure

```json
{
  "nodes": [
    {
      "id": "unique-node-id",
      "name": "Display Name",
      "host": "192.168.1.100",
      "port": 8006,
      "api_token_id": "root@pam!monitoring",
      "api_token_secret": "your-api-token-secret",
      "ssl_verify": false,
      "enabled": true,
      "created_at": "2025-01-01T00:00:00Z",
      "last_connected": null
    }
  ],
  "metadata": {
    "version": "1.0",
    "created_at": "2025-01-01T00:00:00Z",
    "last_modified": "2025-01-01T00:00:00Z"
  }
}
```

### Required Fields

- `name`: Display name for the node
- `host`: IP address or hostname
- `api_token_id`: Proxmox API token ID
- `api_token_secret`: Proxmox API token secret

### Optional Fields

- `port`: API port (defaults to PROXMOX_DEFAULT_PORT)
- `ssl_verify`: SSL verification (defaults to PROXMOX_SSL_VERIFY)
- `enabled`: Whether the node is active (defaults to true)

### Validation Rules

- **Host**: Must be valid IP address or hostname
- **Port**: Must be between 1-65535
- **Name**: Cannot be empty
- **API Token**: Both ID and secret are required

## Using the Configuration System

### In Python Code

```python
from config import Config, ProxmoxConfigManager

# Access application configuration
print(f"Server will run on {Config.HOST}:{Config.PORT}")
print(f"Data directory: {Config.DATA_DIR}")

# Manage Proxmox nodes
manager = ProxmoxConfigManager()

# Get all nodes
nodes = manager.get_all_nodes()

# Add a new node
node_config = {
    "name": "Production Server",
    "host": "192.168.1.100",
    "api_token_id": "root@pam!monitoring",
    "api_token_secret": "your-secret-here"
}
node_id = manager.add_node(node_config)

# Update a node
manager.update_node(node_id, {"name": "Updated Name"})

# Remove a node
manager.remove_node(node_id)
```

### Configuration Validation

```python
from config import Config

# Validate current configuration
messages = Config.validate_configuration()
for message in messages:
    if message.startswith("ERROR"):
        print(f"Configuration error: {message}")
    else:
        print(f"Configuration warning: {message}")
```

## Environment-Specific Examples

### Development Environment
```bash
SECRET_KEY=dev-key-not-for-production
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

### Production Environment
```bash
SECRET_KEY=your-very-secure-random-key-here
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
FLASK_DEBUG=False
FORCE_HTTPS=True
LOG_LEVEL=INFO
LOG_FILE=/var/log/pmi-dashboard/app.log
```

### Docker Environment
```bash
FLASK_HOST=0.0.0.0
DATA_DIR=/app/data
LOG_FILE=/app/logs/pmi-dashboard.log
```

## Security Considerations

### Production Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Set `FLASK_DEBUG=False`
- [ ] Use `FORCE_HTTPS=True` with proper SSL setup
- [ ] Set appropriate `SESSION_TIMEOUT`
- [ ] Use `PROXMOX_SSL_VERIFY=True` with valid certificates
- [ ] Secure file permissions on configuration files
- [ ] Use environment variables for sensitive data

### API Token Security

- Create dedicated API tokens for the dashboard
- Use minimal required permissions
- Rotate tokens regularly
- Store tokens securely (never in code or logs)

## Troubleshooting

### Common Issues

1. **Configuration file not found**
   - The system creates it automatically on first run
   - Check DATA_DIR permissions

2. **Invalid JSON in configuration file**
   - Validate JSON syntax
   - Check for trailing commas or missing quotes

3. **Connection validation errors**
   - Verify host/IP address format
   - Check port ranges (1-65535)
   - Ensure required fields are present

4. **Permission errors**
   - Check file/directory permissions
   - Ensure DATA_DIR is writable

### Debug Mode

Enable debug logging to troubleshoot configuration issues:
```bash
LOG_LEVEL=DEBUG
```

This will provide detailed information about configuration loading and validation.