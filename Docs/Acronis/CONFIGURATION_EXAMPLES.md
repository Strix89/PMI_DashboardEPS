# Acronis Configuration Examples

## Overview

This document provides comprehensive examples for configuring the Acronis Backup Integration module in various scenarios and environments.

## Environment Variables Configuration

### Basic .env Configuration

Create or update your `.env` file in the `pmi_dashboard` directory:

```env
# Acronis API Configuration
ACRONIS_BASE_URL=https://ecs.evolumia.cloud/api/
ACRONIS_CLIENT_ID=your-client-id-here
ACRONIS_CLIENT_SECRET=your-client-secret-here
ACRONIS_GRANT_TYPE=client_credentials

# Optional: Acronis API Settings
ACRONIS_TIMEOUT=30
ACRONIS_RETRY_ATTEMPTS=3
ACRONIS_CACHE_TTL=300
```

### Production Environment

```env
# Production Acronis Configuration
ACRONIS_BASE_URL=https://prod-acronis.company.com/api/
ACRONIS_CLIENT_ID=prod_client_12345
ACRONIS_CLIENT_SECRET=prod_secret_abcdef123456
ACRONIS_GRANT_TYPE=client_credentials

# Production-specific settings
ACRONIS_TIMEOUT=60
ACRONIS_RETRY_ATTEMPTS=5
ACRONIS_CACHE_TTL=600
ACRONIS_LOG_LEVEL=INFO
```

### Development Environment

```env
# Development Acronis Configuration
ACRONIS_BASE_URL=https://dev-acronis.company.com/api/
ACRONIS_CLIENT_ID=dev_client_12345
ACRONIS_CLIENT_SECRET=dev_secret_abcdef123456
ACRONIS_GRANT_TYPE=client_credentials

# Development-specific settings
ACRONIS_TIMEOUT=15
ACRONIS_RETRY_ATTEMPTS=2
ACRONIS_CACHE_TTL=60
ACRONIS_LOG_LEVEL=DEBUG
ACRONIS_DEBUG_MODE=true
```

### Multi-Tenant Configuration

```env
# Primary Tenant
ACRONIS_BASE_URL=https://ecs.evolumia.cloud/api/
ACRONIS_CLIENT_ID=tenant1_client_id
ACRONIS_CLIENT_SECRET=tenant1_client_secret

# Optional: Secondary tenant (for future multi-tenant support)
ACRONIS_TENANT2_BASE_URL=https://tenant2.acronis.com/api/
ACRONIS_TENANT2_CLIENT_ID=tenant2_client_id
ACRONIS_TENANT2_CLIENT_SECRET=tenant2_client_secret
```

## JSON Configuration Files

### Basic JSON Configuration

Create `data/acronis_config.json`:

```json
{
  "base_url": "https://ecs.evolumia.cloud/api/",
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here",
  "grant_type": "client_credentials"
}
```

### Advanced JSON Configuration

Create `data/acronis_config.json` with additional settings:

```json
{
  "base_url": "https://ecs.evolumia.cloud/api/",
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here",
  "grant_type": "client_credentials",
  "settings": {
    "timeout": 30,
    "retry_attempts": 3,
    "cache_ttl": 300,
    "max_backups_per_request": 100,
    "enable_websocket": false,
    "log_level": "INFO"
  },
  "features": {
    "auto_refresh": true,
    "refresh_interval": 60,
    "enable_charts": true,
    "enable_notifications": true
  }
}
```

### Environment-Specific JSON Configurations

#### Production Configuration
Create `data/acronis_config_prod.json`:

```json
{
  "base_url": "https://prod-acronis.company.com/api/",
  "client_id": "prod_client_12345",
  "client_secret": "prod_secret_abcdef123456",
  "grant_type": "client_credentials",
  "settings": {
    "timeout": 60,
    "retry_attempts": 5,
    "cache_ttl": 600,
    "max_backups_per_request": 200,
    "enable_websocket": true,
    "log_level": "WARN"
  },
  "features": {
    "auto_refresh": true,
    "refresh_interval": 120,
    "enable_charts": true,
    "enable_notifications": true,
    "enable_email_alerts": true
  },
  "monitoring": {
    "health_check_interval": 300,
    "alert_on_failure": true,
    "max_consecutive_failures": 3
  }
}
```

#### Development Configuration
Create `data/acronis_config_dev.json`:

```json
{
  "base_url": "https://dev-acronis.company.com/api/",
  "client_id": "dev_client_12345",
  "client_secret": "dev_secret_abcdef123456",
  "grant_type": "client_credentials",
  "settings": {
    "timeout": 15,
    "retry_attempts": 2,
    "cache_ttl": 60,
    "max_backups_per_request": 50,
    "enable_websocket": false,
    "log_level": "DEBUG"
  },
  "features": {
    "auto_refresh": true,
    "refresh_interval": 30,
    "enable_charts": true,
    "enable_notifications": false,
    "debug_mode": true
  },
  "development": {
    "mock_data": false,
    "verbose_logging": true,
    "enable_profiling": true
  }
}
```

### Multi-Tenant JSON Configuration

Create `data/acronis_config_multi.json`:

```json
{
  "default_tenant": "tenant1",
  "tenants": {
    "tenant1": {
      "name": "Primary Tenant",
      "base_url": "https://tenant1.acronis.com/api/",
      "client_id": "tenant1_client_id",
      "client_secret": "tenant1_client_secret",
      "grant_type": "client_credentials",
      "enabled": true
    },
    "tenant2": {
      "name": "Secondary Tenant",
      "base_url": "https://tenant2.acronis.com/api/",
      "client_id": "tenant2_client_id",
      "client_secret": "tenant2_client_secret",
      "grant_type": "client_credentials",
      "enabled": false
    }
  },
  "global_settings": {
    "timeout": 30,
    "retry_attempts": 3,
    "cache_ttl": 300
  }
}
```

## Docker Configuration

### Docker Compose Environment

```yaml
version: '3.8'
services:
  pmi-dashboard:
    build: .
    environment:
      - ACRONIS_BASE_URL=https://ecs.evolumia.cloud/api/
      - ACRONIS_CLIENT_ID=${ACRONIS_CLIENT_ID}
      - ACRONIS_CLIENT_SECRET=${ACRONIS_CLIENT_SECRET}
      - ACRONIS_GRANT_TYPE=client_credentials
      - ACRONIS_TIMEOUT=30
      - ACRONIS_CACHE_TTL=300
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "5000:5000"
```

### Docker Environment File

Create `.env.docker`:

```env
# Docker-specific Acronis configuration
ACRONIS_BASE_URL=https://ecs.evolumia.cloud/api/
ACRONIS_CLIENT_ID=docker_client_id
ACRONIS_CLIENT_SECRET=docker_client_secret
ACRONIS_GRANT_TYPE=client_credentials

# Docker networking
ACRONIS_TIMEOUT=45
ACRONIS_RETRY_ATTEMPTS=4
```

## Kubernetes Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: acronis-config
data:
  ACRONIS_BASE_URL: "https://ecs.evolumia.cloud/api/"
  ACRONIS_GRANT_TYPE: "client_credentials"
  ACRONIS_TIMEOUT: "30"
  ACRONIS_RETRY_ATTEMPTS: "3"
  ACRONIS_CACHE_TTL: "300"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: acronis-credentials
type: Opaque
data:
  ACRONIS_CLIENT_ID: <base64-encoded-client-id>
  ACRONIS_CLIENT_SECRET: <base64-encoded-client-secret>
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pmi-dashboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pmi-dashboard
  template:
    metadata:
      labels:
        app: pmi-dashboard
    spec:
      containers:
      - name: pmi-dashboard
        image: pmi-dashboard:latest
        envFrom:
        - configMapRef:
            name: acronis-config
        - secretRef:
            name: acronis-credentials
        volumeMounts:
        - name: config-volume
          mountPath: /app/data
      volumes:
      - name: config-volume
        configMap:
          name: acronis-json-config
```

## Cloud Provider Configurations

### AWS Configuration

Using AWS Systems Manager Parameter Store:

```bash
# Store credentials in Parameter Store
aws ssm put-parameter \
  --name "/pmi-dashboard/acronis/client-id" \
  --value "your-client-id" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/pmi-dashboard/acronis/client-secret" \
  --value "your-client-secret" \
  --type "SecureString"
```

Python code to retrieve:

```python
import boto3

def get_acronis_config():
    ssm = boto3.client('ssm')
    
    client_id = ssm.get_parameter(
        Name='/pmi-dashboard/acronis/client-id',
        WithDecryption=True
    )['Parameter']['Value']
    
    client_secret = ssm.get_parameter(
        Name='/pmi-dashboard/acronis/client-secret',
        WithDecryption=True
    )['Parameter']['Value']
    
    return {
        'base_url': 'https://ecs.evolumia.cloud/api/',
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
```

### Azure Configuration

Using Azure Key Vault:

```bash
# Store credentials in Key Vault
az keyvault secret set \
  --vault-name "pmi-dashboard-kv" \
  --name "acronis-client-id" \
  --value "your-client-id"

az keyvault secret set \
  --vault-name "pmi-dashboard-kv" \
  --name "acronis-client-secret" \
  --value "your-client-secret"
```

### Google Cloud Configuration

Using Google Secret Manager:

```bash
# Store credentials in Secret Manager
echo -n "your-client-id" | gcloud secrets create acronis-client-id --data-file=-
echo -n "your-client-secret" | gcloud secrets create acronis-client-secret --data-file=-
```

## Configuration Validation

### Validation Script

Create `scripts/validate_acronis_config.py`:

```python
#!/usr/bin/env python3
import os
import json
import requests
from urllib.parse import urljoin

def validate_config():
    """Validate Acronis configuration"""
    
    # Try to load configuration
    config = None
    
    # Check JSON file first
    json_path = 'data/acronis_config.json'
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            config = json.load(f)
        print("✓ Found JSON configuration")
    else:
        # Check environment variables
        config = {
            'base_url': os.getenv('ACRONIS_BASE_URL'),
            'client_id': os.getenv('ACRONIS_CLIENT_ID'),
            'client_secret': os.getenv('ACRONIS_CLIENT_SECRET'),
            'grant_type': os.getenv('ACRONIS_GRANT_TYPE', 'client_credentials')
        }
        
        if not all([config['base_url'], config['client_id'], config['client_secret']]):
            print("✗ No valid configuration found")
            return False
        
        print("✓ Found environment configuration")
    
    # Validate required fields
    required_fields = ['base_url', 'client_id', 'client_secret']
    for field in required_fields:
        if not config.get(field):
            print(f"✗ Missing required field: {field}")
            return False
    
    print("✓ All required fields present")
    
    # Test API connectivity
    try:
        token_url = urljoin(config['base_url'], '2/idp/token')
        
        data = {
            'grant_type': config['grant_type'],
            'client_id': config['client_id'],
            'client_secret': config['client_secret']
        }
        
        response = requests.post(
            token_url,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        if response.status_code == 200:
            print("✓ API authentication successful")
            return True
        else:
            print(f"✗ API authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ API connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    if validate_config():
        print("\n✓ Configuration is valid!")
        exit(0)
    else:
        print("\n✗ Configuration validation failed!")
        exit(1)
```

### Configuration Template

Create `templates/acronis_config_template.json`:

```json
{
  "_comment": "Acronis Backup Integration Configuration Template",
  "_instructions": [
    "1. Copy this file to data/acronis_config.json",
    "2. Replace placeholder values with your actual Acronis credentials",
    "3. Adjust settings as needed for your environment",
    "4. Run validation script to test configuration"
  ],
  
  "base_url": "https://your-acronis-instance.com/api/",
  "client_id": "YOUR_CLIENT_ID_HERE",
  "client_secret": "YOUR_CLIENT_SECRET_HERE",
  "grant_type": "client_credentials",
  
  "settings": {
    "_comment": "Optional settings - remove if not needed",
    "timeout": 30,
    "retry_attempts": 3,
    "cache_ttl": 300,
    "max_backups_per_request": 100,
    "log_level": "INFO"
  },
  
  "features": {
    "_comment": "Feature toggles - remove if not needed",
    "auto_refresh": true,
    "refresh_interval": 60,
    "enable_charts": true,
    "enable_notifications": true
  }
}
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

1. **Invalid Base URL**
   ```json
   // Wrong
   "base_url": "https://ecs.evolumia.cloud"
   
   // Correct
   "base_url": "https://ecs.evolumia.cloud/api/"
   ```

2. **Missing Trailing Slash**
   ```json
   // Wrong
   "base_url": "https://ecs.evolumia.cloud/api"
   
   // Correct
   "base_url": "https://ecs.evolumia.cloud/api/"
   ```

3. **Incorrect Grant Type**
   ```json
   // Wrong
   "grant_type": "authorization_code"
   
   // Correct
   "grant_type": "client_credentials"
   ```

### Configuration Priority

The system loads configuration in this order (highest to lowest priority):

1. JSON file in `data/` directory
2. Environment variables in `.env` file
3. System environment variables
4. Default values

### Testing Configuration

Use the validation script to test your configuration:

```bash
# Make script executable
chmod +x scripts/validate_acronis_config.py

# Run validation
python scripts/validate_acronis_config.py
```

Or test manually with curl:

```bash
curl -X POST "https://your-acronis-instance.com/api/2/idp/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

## Security Best Practices

1. **Never commit credentials to version control**
2. **Use environment variables in production**
3. **Rotate credentials regularly**
4. **Use least-privilege API permissions**
5. **Monitor API usage and access logs**
6. **Use HTTPS for all API communications**
7. **Store secrets in secure key management systems**

## Configuration Migration

### From Environment Variables to JSON

```python
import os
import json

# Read from environment
config = {
    'base_url': os.getenv('ACRONIS_BASE_URL'),
    'client_id': os.getenv('ACRONIS_CLIENT_ID'),
    'client_secret': os.getenv('ACRONIS_CLIENT_SECRET'),
    'grant_type': os.getenv('ACRONIS_GRANT_TYPE', 'client_credentials')
}

# Write to JSON
with open('data/acronis_config.json', 'w') as f:
    json.dump(config, f, indent=2)
```

### From JSON to Environment Variables

```bash
# Read JSON and export to environment
eval $(python -c "
import json
with open('data/acronis_config.json') as f:
    config = json.load(f)
for key, value in config.items():
    if isinstance(value, str):
        print(f'export ACRONIS_{key.upper()}=\"{value}\"')
")
```