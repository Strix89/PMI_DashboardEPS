/**
 * Proxmox API client for frontend interactions
 * 
 * This module provides functions to interact with the Proxmox management API
 * endpoints, including node management, resource control, and real-time metrics.
 */

class ProxmoxAPI {
    constructor() {
        this.baseUrl = '/api/proxmox';
        this.defaultTimeout = 30000; // 30 seconds
    }

    /**
     * Make an HTTP request to the API
     * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @param {number} timeout - Request timeout in milliseconds
     * @returns {Promise} Response promise
     */
    async makeRequest(method, endpoint, data = null, timeout = this.defaultTimeout) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(timeout)
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return result;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    // Node Management Methods

    /**
     * Get all configured Proxmox nodes with status
     * @returns {Promise} Nodes data
     */
    async getNodes() {
        return this.makeRequest('GET', '/nodes');
    }

    /**
     * Add a new Proxmox node
     * @param {Object} nodeConfig - Node configuration
     * @returns {Promise} Add result
     */
    async addNode(nodeConfig) {
        return this.makeRequest('POST', '/nodes', nodeConfig);
    }

    /**
     * Update an existing Proxmox node
     * @param {string} nodeId - Node ID
     * @param {Object} updates - Updates to apply
     * @returns {Promise} Update result
     */
    async updateNode(nodeId, updates) {
        return this.makeRequest('PUT', `/nodes/${nodeId}`, updates);
    }

    /**
     * Delete a Proxmox node
     * @param {string} nodeId - Node ID
     * @returns {Promise} Delete result
     */
    async deleteNode(nodeId) {
        return this.makeRequest('DELETE', `/nodes/${nodeId}`);
    }

    /**
     * Test connection to a Proxmox node
     * @param {string} nodeId - Node ID
     * @returns {Promise} Connection test result
     */
    async testNodeConnection(nodeId) {
        return this.makeRequest('POST', `/nodes/${nodeId}/test`);
    }

    /**
     * Test connection using configuration without saving
     * @param {Object} config - Node configuration
     * @returns {Promise} Connection test result
     */
    async testConnectionConfig(config) {
        return this.makeRequest('POST', '/test-connection', config);
    }

    // Resource Management Methods

    /**
     * Get all resources (VMs and containers) for a node
     * @param {string} nodeId - Node ID
     * @returns {Promise} Resources data
     */
    async getNodeResources(nodeId) {
        return this.makeRequest('GET', `/nodes/${nodeId}/resources`);
    }

    /**
     * Get real-time metrics for a specific resource
     * @param {string} nodeId - Node ID
     * @param {number} vmid - VM/Container ID
     * @returns {Promise} Metrics data
     */
    async getResourceMetrics(nodeId, vmid) {
        return this.makeRequest('GET', `/nodes/${nodeId}/resources/${vmid}/metrics`);
    }

    // Resource Control Methods

    /**
     * Start a VM or container
     * @param {string} nodeId - Node ID
     * @param {number} vmid - VM/Container ID
     * @returns {Promise} Operation result
     */
    async startResource(nodeId, vmid) {
        return this.makeRequest('POST', `/nodes/${nodeId}/resources/${vmid}/start`);
    }

    /**
     * Stop a VM or container
     * @param {string} nodeId - Node ID
     * @param {number} vmid - VM/Container ID
     * @param {boolean} force - Force stop
     * @returns {Promise} Operation result
     */
    async stopResource(nodeId, vmid, force = false) {
        return this.makeRequest('POST', `/nodes/${nodeId}/resources/${vmid}/stop`, { force });
    }

    /**
     * Restart a VM or container
     * @param {string} nodeId - Node ID
     * @param {number} vmid - VM/Container ID
     * @param {boolean} force - Force restart
     * @returns {Promise} Operation result
     */
    async restartResource(nodeId, vmid, force = false) {
        return this.makeRequest('POST', `/nodes/${nodeId}/resources/${vmid}/restart`, { force });
    }

    // Operation History Methods

    /**
     * Get operation history
     * @param {Object} filters - Filter options
     * @returns {Promise} History data
     */
    async getOperationHistory(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `/history${params.toString() ? '?' + params.toString() : ''}`;
        return this.makeRequest('GET', endpoint);
    }

    /**
     * Get operation history for a specific node
     * @param {string} nodeId - Node ID
     * @param {Object} filters - Filter options
     * @returns {Promise} History data
     */
    async getNodeOperationHistory(nodeId, filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `/nodes/${nodeId}/history${params.toString() ? '?' + params.toString() : ''}`;
        return this.makeRequest('GET', endpoint);
    }

    // Health Check

    /**
     * Get API health status
     * @returns {Promise} Health data
     */
    async getHealth() {
        return this.makeRequest('GET', '/health');
    }
}

// Utility Functions

/**
 * Format bytes to human readable string
 * @param {number} bytes - Bytes value
 * @returns {string} Formatted string
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let value = bytes;
    
    while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024;
        unitIndex++;
    }
    
    return unitIndex === 0 ? 
        `${Math.round(value)} ${units[unitIndex]}` : 
        `${value.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Format uptime to human readable string
 * @param {number} seconds - Uptime in seconds
 * @returns {string} Formatted string
 */
function formatUptime(seconds) {
    if (seconds === 0) return '0s';
    
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    
    return parts.length > 0 ? parts.join(' ') : `${seconds}s`;
}

/**
 * Format percentage with proper styling
 * @param {number} percentage - Percentage value
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted percentage
 */
function formatPercentage(percentage, decimals = 1) {
    return `${percentage.toFixed(decimals)}%`;
}

/**
 * Get status color class based on resource status
 * @param {string} status - Resource status
 * @returns {string} CSS class name
 */
function getStatusColor(status) {
    const statusColors = {
        'running': 'text-success',
        'stopped': 'text-secondary',
        'paused': 'text-warning',
        'suspended': 'text-warning',
        'error': 'text-danger',
        'unknown': 'text-muted',
        'online': 'text-success',
        'offline': 'text-danger',
        'connected': 'text-success'
    };
    
    return statusColors[status] || 'text-muted';
}

/**
 * Get progress bar color class based on percentage
 * @param {number} percentage - Usage percentage
 * @returns {string} CSS class name
 */
function getProgressColor(percentage) {
    if (percentage >= 90) return 'bg-danger';
    if (percentage >= 75) return 'bg-warning';
    if (percentage >= 50) return 'bg-info';
    return 'bg-success';
}

/**
 * Show notification message
 * @param {string} message - Message text
 * @param {string} type - Message type (success, error, warning, info)
 * @param {number} duration - Display duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 5000) {
    // This would integrate with the notification system
    // For now, just log to console
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // In a real implementation, this would create and show a toast notification
    // Example implementation would create a toast element and add it to the DOM
}

/**
 * Handle API errors with user-friendly messages
 * @param {Error} error - Error object
 * @param {string} operation - Operation that failed
 */
function handleApiError(error, operation = 'operation') {
    let message = `Failed to ${operation}`;
    
    if (error.message) {
        if (error.message.includes('timeout')) {
            message += ': Request timeout. Please check your connection.';
        } else if (error.message.includes('Authentication failed')) {
            message += ': Authentication failed. Please check your API credentials.';
        } else if (error.message.includes('Connection failed')) {
            message += ': Cannot connect to Proxmox server. Please check the server status.';
        } else {
            message += `: ${error.message}`;
        }
    }
    
    showNotification(message, 'error');
    console.error(`API Error [${operation}]:`, error);
}

// Create global instance
const proxmoxAPI = new ProxmoxAPI();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ProxmoxAPI,
        proxmoxAPI,
        formatBytes,
        formatUptime,
        formatPercentage,
        getStatusColor,
        getProgressColor,
        showNotification,
        handleApiError
    };
}