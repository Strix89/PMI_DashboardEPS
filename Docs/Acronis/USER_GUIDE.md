# Acronis Backup Integration - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Initial Setup](#initial-setup)
3. [Dashboard Overview](#dashboard-overview)
4. [Managing Configurations](#managing-configurations)
5. [Monitoring Agents](#monitoring-agents)
6. [Viewing Backup Details](#viewing-backup-details)
7. [Understanding Charts and Statistics](#understanding-charts-and-statistics)
8. [Troubleshooting](#troubleshooting)
9. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

The Acronis Backup Integration allows you to monitor your Acronis Cyber Protect Cloud backup infrastructure directly from the PMI Dashboard. This integration provides real-time visibility into your backup agents, workloads, and backup job statuses.

### Prerequisites

Before using the Acronis integration, ensure you have:

- Access to the PMI Dashboard
- Acronis Cyber Protect Cloud account
- API credentials (Client ID and Client Secret) from Acronis
- Appropriate permissions to view backup data in Acronis

### Accessing the Acronis Tab

1. Open your web browser and navigate to the PMI Dashboard
2. Log in with your credentials
3. Click on the **"Acronis"** tab in the main navigation bar

## Initial Setup

### First-Time Configuration

When you first access the Acronis tab, you'll see a configuration screen if no credentials are set up.

#### Step 1: Gather Your Acronis API Credentials

1. Log in to your Acronis Cyber Protect Cloud console
2. Navigate to **Settings** → **API Clients**
3. Create a new API client or use an existing one
4. Note down:
   - **Base URL**: Your Acronis instance URL (e.g., `https://ecs.evolumia.cloud/api/`)
   - **Client ID**: Your API client identifier
   - **Client Secret**: Your API client secret

#### Step 2: Configure the Integration

1. In the Acronis tab, you'll see a configuration form
2. Fill in the required fields:
   - **Base URL**: Enter your Acronis API base URL
   - **Client ID**: Enter your API client ID
   - **Client Secret**: Enter your API client secret
   - **Grant Type**: Leave as "client_credentials" (default)

3. Click **"Save Configuration"**

#### Step 3: Verify Configuration

After saving, the system will:
- Validate your credentials
- Test the connection to Acronis
- Display a success message if everything is working
- Show the main dashboard if configuration is successful

### Alternative Configuration Methods

#### Using Environment Variables

System administrators can pre-configure the integration by setting environment variables:

```env
ACRONIS_BASE_URL=https://ecs.evolumia.cloud/api/
ACRONIS_CLIENT_ID=your-client-id
ACRONIS_CLIENT_SECRET=your-client-secret
```

#### Using JSON Configuration File

Place a configuration file at `data/acronis_config.json`:

```json
{
  "base_url": "https://ecs.evolumia.cloud/api/",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "grant_type": "client_credentials"
}
```

## Dashboard Overview

Once configured, the Acronis dashboard displays three main sections:

### 1. Statistics Summary

At the top of the dashboard, you'll see:
- **Total Backups**: Total number of backup jobs
- **Successful Backups**: Number of successful backup jobs
- **Failed Backups**: Number of failed backup jobs
- **Success Rate**: Percentage of successful backups

### 2. Charts Section

Visual representations of your backup data:
- **Success/Failure Pie Chart**: Shows the ratio of successful to failed backups
- **Run Mode Chart**: Displays distribution of scheduled vs manual backups
- **Timeline Chart**: Shows backup frequency over time

### 3. Agents Grid

A grid of cards showing all your Acronis agents, each displaying:
- **Hostname**: The server or workstation name
- **Agent ID**: Unique identifier for the agent
- **Tenant ID**: Acronis tenant identifier
- **Online Status**: Green indicator for online, red for offline
- **Uptime**: How long the agent has been running
- **Platform**: Operating system information
- **Backup Statistics**: Mini pie chart showing backup success/failure ratio
- **View Details Button**: Click to see detailed backup information

## Managing Configurations

### Viewing Current Configuration

To see your current configuration:
1. The dashboard will show if you're properly configured
2. Configuration details are visible in the browser's developer tools (Network tab)

### Updating Configuration

To modify your API credentials:
1. Use the API endpoints directly or
2. Update the environment variables/JSON file and restart the application

### Deleting Configuration

To remove the current configuration:
1. Delete the JSON configuration file, or
2. Remove environment variables and restart the application

## Monitoring Agents

### Understanding Agent Status

Each agent card provides comprehensive information:

#### Online Status Indicators
- **Green Circle**: Agent is online and communicating
- **Red Circle**: Agent is offline or not responding
- **Yellow Circle**: Agent has connectivity issues

#### Platform Information
- **Family**: Operating system family (Windows, Linux, macOS)
- **Architecture**: System architecture (x64, x86)
- **Name**: Specific OS version
- **Version**: OS version number

#### Uptime Information
- Displays how long the agent has been running
- Format: "X days, Y hours, Z minutes"
- Helps identify agents that may need attention

### Agent Actions

#### View Details
Click the **"View Details"** button on any agent card to:
- See detailed backup history for that agent
- View individual backup job information
- Analyze backup activities and results

#### Refresh Data
The dashboard automatically refreshes every 60 seconds, but you can:
- Switch to another tab and back to force a refresh
- Wait for the automatic refresh cycle

## Viewing Backup Details

### Accessing Backup Details

1. Click **"View Details"** on any agent card
2. The view will switch to show detailed backup information for that agent

### Understanding Backup Information

Each backup entry shows:

#### Basic Information
- **Started At**: When the backup job began
- **Completed At**: When the backup job finished
- **Duration**: How long the backup took
- **State**: Current state (completed, failed, running)
- **Result**: Final result (ok, error, warning)

#### Technical Details
- **Run Mode**: How the backup was triggered
  - **Scheduled**: Automatic backup based on schedule
  - **Manual**: User-initiated backup
- **Bytes Saved**: Amount of data backed up
- **Formatted Size**: Human-readable size (e.g., "1.2 GB")

#### Activities Section
Click on a backup to expand and see:
- Individual backup activities
- Activity types (file backup, database backup, etc.)
- Activity status and results
- Detailed error messages if applicable

### Navigation

#### Returning to Main View
- Click the **"Torna indietro"** (Go Back) button
- This returns you to the main dashboard with all agents

#### Breadcrumb Navigation
The interface shows your current location:
- Main Dashboard → Agent Details → Backup Details

## Understanding Charts and Statistics

### Success/Failure Pie Chart

This chart shows:
- **Green Section**: Successful backups
- **Red Section**: Failed backups
- **Percentage Labels**: Exact percentages for each category
- **Hover Information**: Detailed numbers when you hover over sections

### Run Mode Distribution Chart

This chart displays:
- **Blue Section**: Scheduled backups
- **Orange Section**: Manual backups
- **Helps identify**: Whether your backup strategy relies too heavily on manual intervention

### Timeline Chart

This chart shows:
- **X-Axis**: Time periods (days, weeks, months)
- **Y-Axis**: Number of backups
- **Trend Analysis**: Helps identify patterns in backup frequency
- **Anomaly Detection**: Spots unusual spikes or drops in backup activity

### Statistics Interpretation

#### Success Rate Analysis
- **Above 95%**: Excellent backup health
- **90-95%**: Good, but monitor failed backups
- **85-90%**: Needs attention, investigate failures
- **Below 85%**: Critical, immediate action required

#### Backup Frequency
- **Daily Backups**: Look for consistent daily patterns
- **Weekly Patterns**: Identify if weekend backups are running
- **Monthly Trends**: Spot seasonal variations or issues

## Troubleshooting

### Common Issues and Solutions

#### 1. Configuration Not Working

**Symptoms:**
- Configuration form keeps appearing
- "Authentication failed" messages

**Solutions:**
1. Verify your Acronis credentials are correct
2. Check that the Base URL includes `/api/` at the end
3. Ensure your API client has appropriate permissions
4. Test credentials directly in Acronis console

#### 2. No Agents Showing

**Symptoms:**
- Dashboard loads but shows no agents
- Empty agent grid

**Solutions:**
1. Verify agents are registered in Acronis
2. Check agent connectivity in Acronis console
3. Ensure API client has permission to view agents
4. Check browser console for JavaScript errors

#### 3. No Backup Data

**Symptoms:**
- Agents show but no backup statistics
- Charts are empty

**Solutions:**
1. Verify backup jobs are configured in Acronis
2. Check if backup jobs have run recently
3. Ensure workloads are properly associated with agents
4. Verify API permissions include backup data access

#### 4. Slow Loading

**Symptoms:**
- Dashboard takes long time to load
- Timeout errors

**Solutions:**
1. Check network connectivity to Acronis servers
2. Verify Acronis API server performance
3. Consider reducing refresh frequency
4. Check for large amounts of backup data

#### 5. Charts Not Displaying

**Symptoms:**
- Statistics show but charts are missing
- JavaScript errors in console

**Solutions:**
1. Ensure Google Charts library is loading
2. Check for ad blockers interfering
3. Clear browser cache
4. Try a different browser

### Getting Help

If you continue to experience issues:

1. **Check Browser Console**: Press F12 and look for error messages
2. **Review Network Tab**: Check for failed API requests
3. **Test API Directly**: Use tools like curl to test Acronis API
4. **Contact Administrator**: Provide specific error messages and steps to reproduce

## Tips and Best Practices

### Monitoring Best Practices

1. **Regular Monitoring**: Check the dashboard daily for backup health
2. **Investigate Failures**: Don't ignore failed backups, investigate immediately
3. **Monitor Trends**: Look for patterns in backup success rates
4. **Agent Health**: Keep an eye on agent uptime and connectivity

### Performance Optimization

1. **Browser Performance**: 
   - Close other tabs when monitoring large environments
   - Use modern browsers for best performance
   - Clear cache if experiencing issues

2. **Data Management**:
   - Large environments may load slowly
   - Consider filtering options if available
   - Monitor during off-peak hours for better performance

### Security Considerations

1. **Credential Management**:
   - Don't share API credentials
   - Rotate credentials regularly
   - Use least-privilege access

2. **Access Control**:
   - Limit dashboard access to authorized personnel
   - Log out when finished
   - Use secure connections (HTTPS)

### Maintenance Tasks

#### Daily Tasks
- [ ] Check overall backup success rate
- [ ] Review any failed backups
- [ ] Verify all critical agents are online

#### Weekly Tasks
- [ ] Review backup trends and patterns
- [ ] Check for agents with consistently poor performance
- [ ] Verify backup schedules are running as expected

#### Monthly Tasks
- [ ] Review and update API credentials if needed
- [ ] Analyze backup frequency trends
- [ ] Plan for capacity or schedule adjustments

### Advanced Usage

#### Keyboard Shortcuts
- **F5**: Refresh the current view
- **Ctrl+F5**: Hard refresh (clears cache)
- **F12**: Open browser developer tools

#### URL Parameters
You can bookmark specific views:
- Main dashboard: `/dashboard#acronis`
- Agent details: `/dashboard#acronis/agent/{agent-id}`

#### Integration with Other Tools
The dashboard can be:
- Embedded in other monitoring systems
- Used alongside other PMI Dashboard modules
- Integrated with alerting systems via API

### Customization Options

While the interface is standardized, you can:
- Adjust browser zoom for better visibility
- Use browser bookmarks for quick access
- Set up browser notifications for the tab

## Conclusion

The Acronis Backup Integration provides comprehensive monitoring capabilities for your backup infrastructure. By following this guide, you should be able to:

- Successfully configure the integration
- Monitor your backup environment effectively
- Identify and resolve issues quickly
- Maintain optimal backup performance

For additional support or advanced configuration options, consult the technical documentation or contact your system administrator.