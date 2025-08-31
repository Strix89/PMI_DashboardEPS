# PMI Dashboard API Documentation

This document provides comprehensive documentation for the PMI Dashboard REST API endpoints.

## Base URL

All API endpoints are prefixed with `/api/proxmox` when running locally:
```
http://localhost:5000/api/proxmox
```

## Authentication

The API uses Proxmox API tokens for authentication. Tokens are configured per node and stored securely in the application configuration.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message",
  "timestamp": "2025-01-31T12:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": { ... },
  "help": "Recovery suggestions",
  "recovery_suggestions": ["suggestion1", "suggestion2"],
  "timestamp": "2025-01-31T12:00:00Z",
  "request_id": "abc12345"
}
```

## Node Management Endpoints

### List All Nodes

Get all configured Proxmox nodes with their current status.

**Endpoint**: `GET /nodes`

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "node-uuid",
      "name": "Production Server",
      "host": "192.168.1.100",
      "port": 8006,
      "status": "online",
      "version": "7.4-3",
      "is_connected": true,
      "cpu_usage": 25.5,
      "cpu_count": 8,
      "memory_usage": 8589934592,
      "memory_total": 17179869184,
      "memory_percentage": 50.0,
      "disk_usage": 107374182400,
      "disk_total": 214748364800,
      "disk_percentage": 50.0,
      "uptime": 86400,
      "last_connected": "2025-01-31T12:00:00Z",
      "last_updated": "2025-01-31T12:00:00Z"
    }
  ]
}
```

**Status Values**:
- `online` - Node is connected and responding
- `offline` - Node is not reachable
- `connected` - Node is reachable but metrics unavailable
- `error` - Connection error occurred

### Add New Node

Add a new Proxmox node configuration.

**Endpoint**: `POST /nodes`

**Request Body**:
```json
{
  "name": "Production Server",
  "host": "192.168.1.100",
  "port": 8006,
  "api_token_id": "root@pam!monitoring",
  "api_token_secret": "your-api-token-secret",
  "ssl_verify": false,
  "timeout": 30
}
```

**Required Fields**:
- `name` - Display name for the node
- `host` - IP address or hostname
- `api_token_id` - Proxmox API token ID
- `api_token_secret` - Proxmox API token secret

**Optional Fields**:
- `port` - API port (default: 8006)
- `ssl_verify` - SSL verification (default: false)
- `timeout` - Connection timeout in seconds (default: 30)

**Response**:
```json
{
  "success": true,
  "data": {
    "node_id": "generated-uuid"
  },
  "message": "Node 'Production Server' added successfully"
}
```

### Update Node

Update an existing Proxmox node configuration.

**Endpoint**: `PUT /nodes/{node_id}`

**Request Body**: Same as Add Node (partial updates supported)

**Response**:
```json
{
  "success": true,
  "message": "Node 'Production Server' updated successfully"
}
```

### Delete Node

Remove a Proxmox node configuration.

**Endpoint**: `DELETE /nodes/{node_id}`

**Response**:
```json
{
  "success": true,
  "message": "Node 'Production Server' deleted successfully"
}
```

### Test Node Connection

Test connection to a specific Proxmox node.

**Endpoint**: `POST /nodes/{node_id}/test`

**Response**:
```json
{
  "success": true,
  "data": {
    "connected": true
  },
  "message": "Connected to Proxmox VE 7.4-3"
}
```

### Test Connection Configuration

Test connection using provided configuration without saving.

**Endpoint**: `POST /test-connection`

**Request Body**: Same as Add Node

**Response**:
```json
{
  "success": true,
  "data": {
    "connected": true
  },
  "message": "Connected to Proxmox VE 7.4-3"
}
```

## Resource Management Endpoints

### Get Node Resources

Get all VMs and LXC containers for a specific node with real-time metrics.

**Endpoint**: `GET /nodes/{node_id}/resources`

**Response**:
```json
{
  "success": true,
  "data": {
    "vms": [
      {
        "vmid": 100,
        "name": "web-server",
        "status": "running",
        "uptime": 86400,
        "cpu_usage": 15.5,
        "memory_usage": 2147483648,
        "memory_total": 4294967296,
        "memory_percentage": 50.0,
        "disk_usage": 10737418240,
        "disk_total": 21474836480,
        "disk_percentage": 50.0,
        "network_in": 1048576,
        "network_out": 2097152,
        "last_updated": "2025-01-31T12:00:00Z"
      }
    ],
    "containers": [
      {
        "vmid": 200,
        "name": "database-ct",
        "status": "running",
        "uptime": 43200,
        "cpu_usage": 8.2,
        "memory_usage": 1073741824,
        "memory_total": 2147483648,
        "memory_percentage": 50.0,
        "disk_usage": 5368709120,
        "disk_total": 10737418240,
        "disk_percentage": 50.0,
        "network_in": 524288,
        "network_out": 1048576,
        "last_updated": "2025-01-31T12:00:00Z"
      }
    ]
  }
}
```

**Resource Status Values**:
- `running` - Resource is active and running
- `stopped` - Resource is stopped
- `paused` - Resource is paused
- `suspended` - Resource is suspended
- `unknown` - Status cannot be determined

### Get Resource Metrics

Get real-time metrics for a specific VM or LXC container.

**Endpoint**: `GET /nodes/{node_id}/resources/{vmid}/metrics`

**Response**:
```json
{
  "success": true,
  "data": {
    "vmid": 100,
    "name": "web-server",
    "status": "running",
    "uptime": 86400,
    "cpu_usage": 15.5,
    "memory_usage": 2147483648,
    "memory_total": 4294967296,
    "memory_percentage": 50.0,
    "disk_usage": 10737418240,
    "disk_total": 21474836480,
    "disk_percentage": 50.0,
    "network_in": 1048576,
    "network_out": 2097152,
    "last_updated": "2025-01-31T12:00:00Z"
  }
}
```

## Resource Control Endpoints

### Start Resource

Start a VM or LXC container.

**Endpoint**: `POST /nodes/{node_id}/resources/{vmid}/start`

**Response**:
```json
{
  "success": true,
  "data": {
    "operation_id": "op-uuid",
    "status": "success"
  },
  "message": "VM 100 started successfully"
}
```

### Stop Resource

Stop a VM or LXC container.

**Endpoint**: `POST /nodes/{node_id}/resources/{vmid}/stop`

**Request Body** (optional):
```json
{
  "force": false
}
```

**Parameters**:
- `force` - Force stop (equivalent to power off)

**Response**:
```json
{
  "success": true,
  "data": {
    "operation_id": "op-uuid",
    "status": "success"
  },
  "message": "VM 100 stopped successfully"
}
```

### Restart Resource

Restart a VM or LXC container.

**Endpoint**: `POST /nodes/{node_id}/resources/{vmid}/restart`

**Request Body** (optional):
```json
{
  "force": false
}
```

**Parameters**:
- `force` - Force restart

**Response**:
```json
{
  "success": true,
  "data": {
    "operation_id": "op-uuid",
    "status": "success"
  },
  "message": "VM 100 restarted successfully"
}
```

## Operation History Endpoints

### Get Operation History

Get operation history with optional filtering.

**Endpoint**: `GET /history`

**Query Parameters**:
- `node` - Filter by node name
- `resource_type` - Filter by resource type (vm, lxc, node)
- `operation_type` - Filter by operation (start, stop, restart)
- `status` - Filter by status (success, failed, in_progress)
- `limit` - Maximum results (default: 100)
- `offset` - Skip results (default: 0)

**Example**: `GET /history?node=production&limit=50&status=failed`

**Response**:
```json
{
  "success": true,
  "data": {
    "operations": [
      {
        "id": "op-uuid",
        "timestamp": "2025-01-31T12:00:00Z",
        "node": "production",
        "resource_type": "vm",
        "resource_id": 100,
        "resource_name": "web-server",
        "operation": "start",
        "status": "success",
        "duration": 5.2,
        "user": null,
        "error_message": null,
        "details": {}
      }
    ],
    "total": 150,
    "limit": 100,
    "offset": 0,
    "filters": {
      "node": null,
      "resource_type": null,
      "operation_type": null,
      "status": null
    }
  }
}
```

### Get Node Operation History

Get operation history for a specific node.

**Endpoint**: `GET /nodes/{node_id}/history`

**Query Parameters**: Same as Get Operation History

**Response**: Same format as Get Operation History

## Health Check Endpoint

### Get API Health

Get API health status.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-31T12:00:00Z",
  "version": "1.0.0"
}
```

## Error Codes

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (authentication failed)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource not found)
- `408` - Request Timeout
- `409` - Conflict (resource state conflict)
- `422` - Unprocessable Entity (validation failed)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `502` - Bad Gateway (Proxmox server error)
- `503` - Service Unavailable (Proxmox server unavailable)
- `504` - Gateway Timeout (Proxmox server timeout)

### Application Error Codes

- `INTERNAL_ERROR` - General internal error
- `HTTP_{status}` - HTTP error with status code
- `VALIDATION_ERROR` - Input validation failed
- `CONNECTION_ERROR` - Network connection failed
- `AUTH_ERROR` - Authentication failed
- `TIMEOUT_ERROR` - Request timeout
- `RESOURCE_NOT_FOUND` - Requested resource not found
- `OPERATION_FAILED` - Operation execution failed

## Rate Limiting

The API implements basic rate limiting to prevent abuse:
- 100 requests per minute per IP address
- 10 concurrent requests per IP address
- Longer timeouts for resource control operations

## Data Types and Formats

### Timestamps
All timestamps are in ISO 8601 format with UTC timezone:
```
2025-01-31T12:00:00Z
```

### Byte Values
Memory and disk values are in bytes:
```json
{
  "memory_usage": 2147483648,  // 2 GB
  "disk_total": 21474836480    // 20 GB
}
```

### Percentages
Percentage values are decimal numbers (0-100):
```json
{
  "cpu_usage": 25.5,           // 25.5%
  "memory_percentage": 50.0    // 50.0%
}
```

### Duration
Duration values are in seconds (decimal):
```json
{
  "duration": 5.2,             // 5.2 seconds
  "uptime": 86400              // 24 hours
}
```

## SDK and Client Libraries

### JavaScript Client
The frontend includes a comprehensive JavaScript client:

```javascript
// Initialize client
const api = new ProxmoxAPI();

// Get nodes
const nodes = await api.getNodes();

// Start a VM
await api.startResource('node-id', 100);

// Get metrics
const metrics = await api.getResourceMetrics('node-id', 100);
```

### Python Client Example
```python
import requests

class PMIDashboardClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def get_nodes(self):
        response = requests.get(f"{self.base_url}/api/proxmox/nodes")
        return response.json()
    
    def start_resource(self, node_id, vmid):
        response = requests.post(
            f"{self.base_url}/api/proxmox/nodes/{node_id}/resources/{vmid}/start"
        )
        return response.json()
```

## Webhooks and Events

The API supports real-time updates through:
- Server-Sent Events (SSE) for live metrics
- WebSocket connections for real-time notifications
- Polling endpoints with efficient caching

## Security Considerations

### API Token Security
- Use dedicated API tokens with minimal required permissions
- Rotate tokens regularly
- Never log or expose token secrets
- Use HTTPS in production

### Input Validation
- All inputs are validated and sanitized
- SQL injection protection (when database is used)
- XSS prevention in responses
- CSRF protection for state-changing operations

### Rate Limiting
- Implement rate limiting to prevent abuse
- Monitor for suspicious activity
- Log security events

## Troubleshooting

### Common Issues

**Authentication Errors (401/403)**:
- Verify API token credentials
- Check token permissions in Proxmox
- Ensure token hasn't expired

**Connection Errors (502/503)**:
- Verify Proxmox server is running
- Check network connectivity
- Validate SSL certificate settings

**Timeout Errors (408/504)**:
- Increase timeout values
- Check network latency
- Verify Proxmox server performance

**Validation Errors (422)**:
- Check required fields
- Validate data types and formats
- Review parameter constraints

### Debug Mode

Enable debug logging for detailed API information:
```bash
export LOG_LEVEL=DEBUG
```

This will log all API requests, responses, and error details.