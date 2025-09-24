# Acronis API Documentation

## Overview

This document provides detailed information about all API endpoints available in the Acronis Backup Integration module. All endpoints follow REST conventions and return JSON responses.

## Base URL

All API endpoints are prefixed with `/api/acronis/`

## Authentication

The API endpoints use the configured Acronis credentials for authentication with the Acronis Cyber Protect Cloud API. No additional authentication is required for the PMI Dashboard API endpoints themselves.

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "timestamp": "2025-01-31T12:00:00Z"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ACRONIS_ERROR_CODE",
  "timestamp": "2025-01-31T12:00:00Z",
  "help": "Suggested solution or next steps",
  "details": {
    "technical_error": "Detailed technical error information"
  }
}
```

## Configuration Endpoints

### GET /api/acronis/config

Retrieve the current Acronis API configuration status.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": {
    "base_url": "https://ecs.evolumia.cloud/api/",
    "client_id": "client-id-here",
    "configured": true,
    "last_updated": "2025-01-31T10:00:00Z"
  }
}
```

**Error Codes:**
- `ACRONIS_CONFIG_MISSING`: No configuration found

---

### POST /api/acronis/config

Save a new Acronis API configuration.

**Request Body:**
```json
{
  "base_url": "https://ecs.evolumia.cloud/api/",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "grant_type": "client_credentials"
}
```

**Validation Rules:**
- `base_url`: Required, must be a valid URL
- `client_id`: Required, non-empty string
- `client_secret`: Required, non-empty string
- `grant_type`: Optional, defaults to "client_credentials"

**Response:**
```json
{
  "success": true,
  "message": "Configuration saved successfully",
  "data": {
    "configured": true
  }
}
```

**Error Codes:**
- `ACRONIS_INVALID_CONFIG`: Invalid configuration data
- `ACRONIS_VALIDATION_ERROR`: Validation failed
- `ACRONIS_SAVE_ERROR`: Failed to save configuration

---

### PUT /api/acronis/config

Update an existing Acronis API configuration.

**Request Body:** Same as POST

**Response:** Same as POST

**Error Codes:** Same as POST

---

### DELETE /api/acronis/config

Delete the current Acronis API configuration.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "message": "Configuration deleted successfully"
}
```

**Error Codes:**
- `ACRONIS_CONFIG_NOT_FOUND`: No configuration to delete
- `ACRONIS_DELETE_ERROR`: Failed to delete configuration

## Data Endpoints

### GET /api/acronis/agents

Retrieve all Acronis agents with their status information.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id_agent": "550e8400-e29b-41d4-a716-446655440000",
      "hostname": "SERVER-01",
      "id_tenant": "123e4567-e89b-12d3-a456-426614174000",
      "online": true,
      "uptime": "5 days, 3 hours, 20 minutes",
      "uptime_timestamp": 1706789123.456,
      "platform": {
        "family": "Windows",
        "arch": "x64",
        "name": "Windows Server 2019",
        "version": "10.0.17763"
      }
    }
  ],
  "count": 1
}
```

**Error Codes:**
- `ACRONIS_AUTH_FAILED`: Authentication with Acronis API failed
- `ACRONIS_CONNECTION_ERROR`: Cannot connect to Acronis API
- `ACRONIS_API_ERROR`: Acronis API returned an error

---

### GET /api/acronis/workloads

Retrieve all Acronis workloads.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id_workload": "550e8400-e29b-41d4-a716-446655440001",
      "hostname": "SERVER-01",
      "id_tenant": "123e4567-e89b-12d3-a456-426614174000",
      "type": "machine",
      "status": "active"
    }
  ],
  "count": 1
}
```

**Error Codes:** Same as agents endpoint

---

### GET /api/acronis/associations

Retrieve agent-workload associations.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "agent_id": "550e8400-e29b-41d4-a716-446655440000",
      "workload_id": "550e8400-e29b-41d4-a716-446655440001",
      "hostname": "SERVER-01",
      "association_type": "direct"
    }
  ],
  "count": 1
}
```

**Error Codes:** Same as agents endpoint

---

### GET /api/acronis/backups

Retrieve backup statistics and data for all workloads.

**Parameters:**
- `limit` (optional): Maximum number of backups per workload (default: 50)
- `days` (optional): Number of days to look back (default: 30)

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "num_backups": 150,
      "success": 145,
      "failed": 5,
      "success_rate": 96.67,
      "total_bytes_saved": 107374182400
    },
    "workload_data": {
      "550e8400-e29b-41d4-a716-446655440001": {
        "hostname": "SERVER-01",
        "id_tenant": "123e4567-e89b-12d3-a456-426614174000",
        "backup_count": 30,
        "success_count": 29,
        "failed_count": 1,
        "backups": [
          {
            "started_at": "31/01/2025 10:00:00",
            "completed_at": "31/01/2025 10:30:00",
            "state": "completed",
            "run_mode": "Scheduled",
            "bytes_saved": 1073741824,
            "result": "ok",
            "duration_minutes": 30,
            "activities": []
          }
        ]
      }
    }
  }
}
```

**Error Codes:** Same as agents endpoint

---

### GET /api/acronis/agent/{agent_id}/backups

Retrieve detailed backup information for a specific agent.

**Parameters:**
- `agent_id` (path): The UUID of the agent
- `limit` (optional): Maximum number of backups to return (default: 100)
- `include_activities` (optional): Include backup activities (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "agent_info": {
      "id_agent": "550e8400-e29b-41d4-a716-446655440000",
      "hostname": "SERVER-01",
      "online": true
    },
    "backup_summary": {
      "total_backups": 30,
      "successful": 29,
      "failed": 1,
      "success_rate": 96.67
    },
    "backups": [
      {
        "backup_id": "backup-uuid-here",
        "started_at": "31/01/2025 10:00:00",
        "completed_at": "31/01/2025 10:30:00",
        "state": "completed",
        "run_mode": "Scheduled",
        "bytes_saved": 1073741824,
        "bytes_saved_formatted": "1.0 GB",
        "result": "ok",
        "duration_minutes": 30,
        "activities": [
          {
            "activity_id": "activity-uuid-here",
            "type": "backup",
            "status": "completed",
            "started_at": "31/01/2025 10:00:00",
            "completed_at": "31/01/2025 10:25:00",
            "details": "File system backup completed successfully",
            "bytes_processed": 1073741824
          }
        ]
      }
    ]
  }
}
```

**Error Codes:**
- `ACRONIS_AGENT_NOT_FOUND`: Agent ID not found
- `ACRONIS_INVALID_AGENT_ID`: Invalid agent ID format
- Same as other data endpoints

---

### GET /api/acronis/health

Check the health and connectivity of the Acronis API integration.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": {
    "api_status": "connected",
    "last_check": "2025-01-31T12:00:00Z",
    "response_time_ms": 250,
    "token_valid": true,
    "endpoints_tested": [
      {
        "endpoint": "/agents",
        "status": "ok",
        "response_time_ms": 180
      },
      {
        "endpoint": "/workloads",
        "status": "ok",
        "response_time_ms": 220
      }
    ],
    "configuration": {
      "base_url": "https://ecs.evolumia.cloud/api/",
      "configured": true
    }
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Acronis API health check failed",
  "error_code": "ACRONIS_HEALTH_CHECK_FAILED",
  "data": {
    "api_status": "disconnected",
    "last_check": "2025-01-31T12:00:00Z",
    "errors": [
      "Authentication failed",
      "Connection timeout"
    ],
    "configuration": {
      "configured": false
    }
  }
}
```

## Error Codes Reference

### Configuration Errors
- `ACRONIS_CONFIG_MISSING`: Configuration not found
- `ACRONIS_CONFIG_INVALID`: Configuration data is invalid
- `ACRONIS_CONFIG_VALIDATION_ERROR`: Configuration validation failed
- `ACRONIS_CONFIG_SAVE_ERROR`: Failed to save configuration
- `ACRONIS_CONFIG_DELETE_ERROR`: Failed to delete configuration

### Authentication Errors
- `ACRONIS_AUTH_FAILED`: Authentication with Acronis API failed
- `ACRONIS_TOKEN_EXPIRED`: API token has expired
- `ACRONIS_TOKEN_INVALID`: API token is invalid
- `ACRONIS_CREDENTIALS_INVALID`: API credentials are invalid

### Connection Errors
- `ACRONIS_CONNECTION_ERROR`: Cannot connect to Acronis API
- `ACRONIS_TIMEOUT_ERROR`: Request to Acronis API timed out
- `ACRONIS_NETWORK_ERROR`: Network connectivity issues

### API Errors
- `ACRONIS_API_ERROR`: General Acronis API error
- `ACRONIS_SERVER_ERROR`: Acronis API server error (5xx)
- `ACRONIS_CLIENT_ERROR`: Client error (4xx)
- `ACRONIS_RATE_LIMITED`: API rate limit exceeded

### Data Errors
- `ACRONIS_DATA_ERROR`: Error processing Acronis data
- `ACRONIS_AGENT_NOT_FOUND`: Specified agent not found
- `ACRONIS_WORKLOAD_NOT_FOUND`: Specified workload not found
- `ACRONIS_INVALID_AGENT_ID`: Invalid agent ID format
- `ACRONIS_INVALID_WORKLOAD_ID`: Invalid workload ID format

### System Errors
- `ACRONIS_INTERNAL_ERROR`: Internal system error
- `ACRONIS_VALIDATION_ERROR`: Request validation error
- `ACRONIS_PERMISSION_ERROR`: Insufficient permissions

## Rate Limiting

The Acronis API may implement rate limiting. The integration handles this by:

1. Implementing exponential backoff for retries
2. Caching responses where appropriate
3. Batching requests when possible

If rate limiting occurs, you'll receive:
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "error_code": "ACRONIS_RATE_LIMITED",
  "retry_after": 60
}
```

## Caching

The API implements intelligent caching for:
- Agent information (5 minutes)
- Workload data (5 minutes)
- Backup statistics (2 minutes)
- Configuration data (until changed)

Cache headers are included in responses:
```json
{
  "success": true,
  "data": {...},
  "cache_info": {
    "cached": true,
    "cache_age": 120,
    "expires_in": 180
  }
}
```

## Pagination

For endpoints that may return large datasets, pagination is supported:

**Request Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50, max: 200)

**Response Format:**
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

## WebSocket Support

For real-time updates, the API supports WebSocket connections:

**Connection:** `ws://localhost:5000/api/acronis/ws`

**Message Format:**
```json
{
  "type": "backup_status_update",
  "data": {
    "agent_id": "agent-uuid",
    "backup_id": "backup-uuid",
    "status": "completed",
    "timestamp": "2025-01-31T12:00:00Z"
  }
}
```

## Testing the API

### Using curl

```bash
# Test health endpoint
curl -X GET "http://localhost:5000/api/acronis/health"

# Get configuration
curl -X GET "http://localhost:5000/api/acronis/config"

# Save configuration
curl -X POST "http://localhost:5000/api/acronis/config" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://your-instance.com/api/",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
  }'

# Get agents
curl -X GET "http://localhost:5000/api/acronis/agents"

# Get agent backups
curl -X GET "http://localhost:5000/api/acronis/agent/550e8400-e29b-41d4-a716-446655440000/backups"
```

### Using Python requests

```python
import requests

base_url = "http://localhost:5000/api/acronis"

# Test health
response = requests.get(f"{base_url}/health")
print(response.json())

# Get agents
response = requests.get(f"{base_url}/agents")
if response.json()["success"]:
    agents = response.json()["data"]
    print(f"Found {len(agents)} agents")
```

### Using JavaScript fetch

```javascript
// Test health
fetch('/api/acronis/health')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log('API is healthy:', data.data);
    } else {
      console.error('API health check failed:', data.error);
    }
  });

// Get agents
fetch('/api/acronis/agents')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log('Agents:', data.data);
    }
  });
```