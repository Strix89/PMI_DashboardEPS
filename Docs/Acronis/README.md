# Acronis Backup Integration Documentation

## Overview

The Acronis Backup Integration module provides comprehensive monitoring and management of Acronis Cyber Protect Cloud backups within the PMI Dashboard. This integration allows administrators to view backup statistics, monitor agent status, and manage API configurations through a unified web interface.

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [Configuration](#configuration)
3. [API Endpoints](#api-endpoints)
4. [User Guide](#user-guide)
5. [Troubleshooting](#troubleshooting)
6. [Development](#development)

## Installation and Setup

### Prerequisites

- PMI Dashboard application running
- Acronis Cyber Protect Cloud account with API access
- Valid Acronis API credentials (Client ID, Client Secret)

### Integration Steps

1. The Acronis module is automatically integrated when the PMI Dashboard starts
2. Navigate to the Acronis tab in the dashboard
3. Configure your API credentials (see Configuration section)
4. Start monitoring your backup infrastructure

## Configuration

### Environment Variables Configuration

The Acronis module supports configuration through environment variables in the `.env` file:

```env
# Acronis API Configuration
ACRONIS_BASE_URL=https://your-acronis-instance.com/api/
ACRONIS_CLIENT_ID=your-client-id
ACRONIS_CLIENT_SECRET=your-client-secret
ACRONIS_GRANT_TYPE=client_credentials
```

### JSON Configuration File

Alternatively, you can use a JSON configuration file in the `data/` directory:

```json
{
  "base_url": "https://your-acronis-instance.com/api/",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "grant_type": "client_credentials"
}
```

Save this as `data/acronis_config.json` and the system will automatically detect and use it.

### Configuration Priority

1. JSON file in `data/` directory (highest priority)
2. Environment variables in `.env` file
3. System environment variables (lowest priority)

## API Endpoints

### Configuration Endpoints

#### GET /api/acronis/config
Retrieve current Acronis API configuration.

**Response:**
```json
{
  "success": true,
  "data": {
    "base_url": "https://your-acronis-instance.com/api/",
    "client_id": "your-client-id",
    "configured": true
  }
}
```

#### POST /api/acronis/config
Save new Acronis API configuration.

**Request Body:**
```json
{
  "base_url": "https://your-acronis-instance.com/api/",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "grant_type": "client_credentials"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration saved successfully"
}
```

#### PUT /api/acronis/config
Update existing Acronis API configuration.

**Request Body:** Same as POST
**Response:** Same as POST

#### DELETE /api/acronis/config
Delete current Acronis API configuration.

**Response:**
```json
{
  "success": true,
  "message": "Configuration deleted successfully"
}
```

### Data Endpoints

#### GET /api/acronis/agents
Retrieve all Acronis agents.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id_agent": "uuid-string",
      "hostname": "server-name",
      "id_tenant": "tenant-uuid",
      "online": true,
      "uptime": "5 days, 3 hours, 20 minutes",
      "uptime_timestamp": 1706789123.456,
      "platform": {
        "family": "Windows",
        "arch": "x64",
        "name": "Windows Server 2019"
      }
    }
  ]
}
```

#### GET /api/acronis/workloads
Retrieve all Acronis workloads.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id_workload": "uuid-string",
      "hostname": "server-name",
      "id_tenant": "tenant-uuid"
    }
  ]
}
```

#### GET /api/acronis/associations
Retrieve agent-workload associations.

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "agent_id": "agent-uuid",
      "workload_id": "workload-uuid",
      "hostname": "server-name"
    }
  ]
}
```

#### GET /api/acronis/backups
Retrieve backup statistics for all workloads.

**Response:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "num_backups": 150,
      "success": 145,
      "failed": 5
    },
    "workload_data": {
      "workload-uuid": {
        "hostname": "server-name",
        "id_tenant": "tenant-uuid",
        "backups": [
          {
            "started_at": "31/01/2025 10:00:00",
            "completed_at": "31/01/2025 10:30:00",
            "state": "completed",
            "run_mode": "Scheduled",
            "bytes_saved": 1073741824,
            "result": "ok",
            "activities": []
          }
        ]
      }
    }
  }
}
```

#### GET /api/acronis/agent/{agent_id}/backups
Retrieve backup details for a specific agent.

**Parameters:**
- `agent_id`: The UUID of the agent

**Response:**
```json
{
  "success": true,
  "data": {
    "agent_info": {
      "id_agent": "agent-uuid",
      "hostname": "server-name"
    },
    "backups": [
      {
        "started_at": "31/01/2025 10:00:00",
        "completed_at": "31/01/2025 10:30:00",
        "state": "completed",
        "run_mode": "Scheduled",
        "bytes_saved": 1073741824,
        "result": "ok",
        "activities": [
          {
            "activity_id": "activity-uuid",
            "type": "backup",
            "status": "completed",
            "details": "Backup completed successfully"
          }
        ]
      }
    ]
  }
}
```

#### GET /api/acronis/health
Check Acronis API connectivity and health.

**Response:**
```json
{
  "success": true,
  "data": {
    "api_status": "connected",
    "last_check": "2025-01-31T12:00:00Z",
    "response_time_ms": 250
  }
}
```

### Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ACRONIS_ERROR_CODE",
  "timestamp": "2025-01-31T12:00:00Z",
  "help": "Suggested solution or next steps"
}
```

Common error codes:
- `ACRONIS_AUTH_FAILED`: Authentication failed
- `ACRONIS_CONFIG_MISSING`: Configuration not found
- `ACRONIS_CONNECTION_ERROR`: Network connectivity issues
- `ACRONIS_INVALID_REQUEST`: Invalid request parameters
- `ACRONIS_SERVER_ERROR`: Acronis API server error

## User Guide

### Getting Started

1. **Access the Acronis Tab**
   - Open the PMI Dashboard in your web browser
   - Click on the "Acronis" tab in the main navigation

2. **Initial Configuration**
   - If not configured, you'll see a configuration form
   - Enter your Acronis API credentials:
     - Base URL: Your Acronis instance URL
     - Client ID: Your API client ID
     - Client Secret: Your API client secret
   - Click "Save Configuration"

3. **Dashboard Overview**
   - After configuration, you'll see the main dashboard with:
     - Backup statistics summary
     - Success/failure pie charts
     - Agent grid with status information

### Using the Dashboard

#### Viewing Agent Information

Each agent card displays:
- **Hostname**: The server name
- **Agent ID**: Unique identifier
- **Tenant ID**: Tenant identifier
- **Online Status**: Green (online) or Red (offline)
- **Uptime**: How long the agent has been running
- **Platform**: Operating system information
- **Backup Statistics**: Pie chart showing success/failure ratio

#### Viewing Backup Details

1. Click "View Details" on any agent card
2. You'll see a detailed list of backups for that agent
3. Each backup shows:
   - Start and completion times
   - Backup status and result
   - Run mode (Scheduled/Manual)
   - Bytes saved
   - Expandable activities list

4. Click "Torna indietro" to return to the main dashboard

#### Understanding Charts

- **Success/Failure Pie Chart**: Shows overall backup success rate
- **Run Mode Chart**: Shows distribution of scheduled vs manual backups
- **Timeline Chart**: Shows backup frequency over time

### Automatic Updates

- Data refreshes automatically every 60 seconds when the Acronis tab is active
- Updates pause when you switch to other tabs
- Updates resume when you return to the Acronis tab
- Loading indicators show when data is being refreshed

### Configuration Management

#### Updating Configuration

1. Click the configuration icon (if available) or access via API
2. Modify the required fields
3. Save the updated configuration
4. The system will validate and apply the new settings

#### Deleting Configuration

1. Use the DELETE endpoint or configuration interface
2. Confirm the deletion
3. You'll be returned to the initial configuration screen

## Troubleshooting

### Common Issues

#### 1. "Configuration not found" Error

**Symptoms:**
- Configuration form appears instead of dashboard
- Error message about missing configuration

**Solutions:**
1. Check if `.env` file contains Acronis configuration variables
2. Verify JSON configuration file exists in `data/` directory
3. Ensure configuration variables are correctly named
4. Restart the PMI Dashboard application

#### 2. Authentication Failed

**Symptoms:**
- "Authentication failed" error messages
- Unable to load agent or backup data
- HTTP 401 errors in browser console

**Solutions:**
1. Verify Client ID and Client Secret are correct
2. Check if API credentials have expired
3. Ensure Base URL is correct and accessible
4. Test credentials directly with Acronis API
5. Check network connectivity to Acronis servers

#### 3. No Data Displayed

**Symptoms:**
- Dashboard loads but shows no agents or backups
- Empty charts and statistics

**Solutions:**
1. Verify agents are properly registered in Acronis
2. Check if workloads are associated with agents
3. Ensure backup jobs have been configured and run
4. Check API permissions for data access
5. Review browser console for JavaScript errors

#### 4. Slow Loading or Timeouts

**Symptoms:**
- Long loading times
- Timeout errors
- Incomplete data loading

**Solutions:**
1. Check network connectivity to Acronis servers
2. Verify Acronis API server performance
3. Reduce refresh frequency if needed
4. Check for large datasets that might need pagination
5. Monitor server resources (CPU, memory)

#### 5. Charts Not Displaying

**Symptoms:**
- Missing or broken charts
- JavaScript errors related to Google Charts

**Solutions:**
1. Ensure Google Charts library is loaded
2. Check browser console for JavaScript errors
3. Verify chart data format is correct
4. Clear browser cache and reload
5. Check if ad blockers are interfering

### Debug Mode

Enable debug mode by setting environment variable:
```env
FLASK_DEBUG=1
```

This provides:
- Detailed error messages
- Request/response logging
- Stack traces for debugging

### Log Files

Check application logs for detailed error information:
- Application logs: `logs/app.log`
- Acronis module logs: Look for entries with `[ACRONIS]` prefix
- Error logs: `logs/error.log`

### API Testing

Test API endpoints directly using curl or Postman:

```bash
# Test health endpoint
curl -X GET http://localhost:5000/api/acronis/health

# Test configuration
curl -X GET http://localhost:5000/api/acronis/config

# Test agents endpoint
curl -X GET http://localhost:5000/api/acronis/agents
```

### Network Diagnostics

1. **Test Acronis API connectivity:**
   ```bash
   curl -X POST https://your-acronis-instance.com/api/2/idp/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
   ```

2. **Check DNS resolution:**
   ```bash
   nslookup your-acronis-instance.com
   ```

3. **Test port connectivity:**
   ```bash
   telnet your-acronis-instance.com 443
   ```

### Performance Optimization

If experiencing performance issues:

1. **Reduce refresh frequency:**
   - Modify the 60-second refresh interval in `acronis.js`
   - Consider implementing smart refresh based on data changes

2. **Implement caching:**
   - Add server-side caching for frequently requested data
   - Use browser caching for static resources

3. **Optimize API calls:**
   - Batch multiple requests where possible
   - Implement pagination for large datasets

### Getting Help

If issues persist:

1. Check the PMI Dashboard logs for detailed error information
2. Verify Acronis API documentation for any changes
3. Test with minimal configuration to isolate issues
4. Contact system administrator for infrastructure-related problems

## Development

### Module Structure

```
pmi_dashboard/acronis/
├── __init__.py          # Module exports
├── api_client.py        # Acronis API client
├── models.py            # Data models
├── routes.py            # Flask blueprint
├── config_manager.py    # Configuration management
└── README.md            # This documentation
```

### Adding New Features

1. Follow the existing code patterns
2. Add appropriate error handling
3. Update API documentation
4. Add unit tests
5. Update this documentation