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
     * Make an HTTP request to the API with enhanced error handling
     * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @param {number} timeout - Request timeout in milliseconds
     * @param {number} retries - Number of retry attempts
     * @returns {Promise} Response promise
     */
    async makeRequest(method, endpoint, data = null, timeout = this.defaultTimeout, retries = 0) {
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
            
            // Handle different response types
            let result;
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                result = await response.json();
            } else {
                result = { message: await response.text() };
            }

            if (!response.ok) {
                const error = new Error(result.error || result.message || `HTTP ${response.status}: ${response.statusText}`);
                error.status = response.status;
                error.response = result;
                throw error;
            }

            return result;
        } catch (error) {
            // Handle specific error types
            if (error.name === 'AbortError') {
                const timeoutError = new Error('Request timeout - the server took too long to respond');
                timeoutError.code = 'TIMEOUT';
                throw timeoutError;
            }
            
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                const networkError = new Error('Network error - unable to connect to server');
                networkError.code = 'NETWORK_ERROR';
                throw networkError;
            }

            // Add error context
            error.endpoint = endpoint;
            error.method = method;
            
            // Retry logic for certain errors
            if (retries > 0 && this.shouldRetry(error)) {
                console.warn(`Request failed, retrying... (${retries} attempts left)`, error.message);
                await this.delay(1000 * (3 - retries)); // Exponential backoff
                return this.makeRequest(method, endpoint, data, timeout, retries - 1);
            }
            
            throw error;
        }
    }

    /**
     * Determine if a request should be retried
     * @param {Error} error - Error object
     * @returns {boolean} True if should retry
     */
    shouldRetry(error) {
        // Retry on network errors, timeouts, and 5xx server errors
        return (
            error.code === 'NETWORK_ERROR' ||
            error.code === 'TIMEOUT' ||
            (error.status >= 500 && error.status < 600)
        );
    }

    /**
     * Delay utility for retry logic
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise} Delay promise
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Node Management Methods

    /**
     * Get all configured Proxmox nodes with status
     * @param {boolean} withRetry - Enable retry on failure
     * @returns {Promise} Nodes data
     */
    async getNodes(withRetry = true) {
        const retries = withRetry ? 2 : 0;
        return this.makeRequest('GET', '/nodes', null, this.defaultTimeout, retries);
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
     * @param {boolean} withRetry - Enable retry on failure
     * @returns {Promise} Resources data
     */
    async getNodeResources(nodeId, withRetry = true) {
        const retries = withRetry ? 2 : 0;
        return this.makeRequest('GET', `/nodes/${nodeId}/resources`, null, this.defaultTimeout, retries);
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
 * Handle API errors with enhanced error handling and recovery suggestions
 * @param {Error} error - Error object
 * @param {string} operation - Operation that failed
 * @param {Function} retryCallback - Optional retry callback
 */
function handleApiError(error, operation = 'operation', retryCallback = null) {
    // Use the enhanced error handler from notifications.js
    if (typeof ErrorHandler !== 'undefined') {
        return ErrorHandler.handleApiError(error, operation, retryCallback);
    }
    
    // Fallback to basic error handling if ErrorHandler is not available
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

    if (typeof showError !== 'undefined') {
        return showError(message, { retryCallback });
    } else if (typeof showNotification !== 'undefined') {
        return showNotification(message, 'error');
    } else {
        console.error(`API Error [${operation}]:`, error);
    }
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
// Integration with Resource Manager is now handled by metrics-init.js

/**
 * Enhanced notification system with toast-style notifications
 * @param {string} message - Message text
 * @param {string} type - Message type (success, error, warning, info)
 * @param {number} duration - Display duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;

    // Set icon based on type
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${icons[type] || icons.info}"></i>
            <span class="notification-message">${message}</span>
        </div>
        <button class="notification-close" aria-label="Close notification">
            <i class="fas fa-times"></i>
        </button>
    `;

    // Add to container
    container.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.add('notification-show');
    }, 10);

    // Set up close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.addEventListener('click', () => {
        removeNotification(notification);
    });

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            removeNotification(notification);
        }, duration);
    }

    return notification;
}

/**
 * Remove a notification with animation
 * @param {HTMLElement} notification - Notification element to remove
 */
function removeNotification(notification) {
    if (!notification || !notification.parentNode) return;

    notification.classList.add('notification-hide');

    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
}

// Add notification styles to the page
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        .notification-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            pointer-events: none;
        }

        .notification {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 4px 16px var(--shadow-medium);
            margin-bottom: 10px;
            padding: 16px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            transform: translateX(100%);
            opacity: 0;
            transition: all 0.3s ease;
            pointer-events: auto;
            max-width: 100%;
            word-wrap: break-word;
        }

        .notification-show {
            transform: translateX(0);
            opacity: 1;
        }

        .notification-hide {
            transform: translateX(100%);
            opacity: 0;
        }

        .notification-content {
            display: flex;
            align-items: flex-start;
            gap: 8px;
            flex: 1;
        }

        .notification-content i {
            font-size: 16px;
            margin-top: 2px;
            flex-shrink: 0;
        }

        .notification-message {
            color: var(--text-primary);
            font-size: 14px;
            line-height: 1.4;
        }

        .notification-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0;
            font-size: 14px;
            flex-shrink: 0;
            transition: color 0.2s ease;
        }

        .notification-close:hover {
            color: var(--text-primary);
        }

        .notification-success {
            border-left: 4px solid var(--success-color);
        }

        .notification-success .notification-content i {
            color: var(--success-color);
        }

        .notification-error {
            border-left: 4px solid var(--error-color);
        }

        .notification-error .notification-content i {
            color: var(--error-color);
        }

        .notification-warning {
            border-left: 4px solid var(--warning-color);
        }

        .notification-warning .notification-content i {
            color: var(--warning-color);
        }

        .notification-info {
            border-left: 4px solid var(--info-color);
        }

        .notification-info .notification-content i {
            color: var(--info-color);
        }

        @media (max-width: 768px) {
            .notification-container {
                top: 10px;
                right: 10px;
                left: 10px;
                max-width: none;
            }

            .notification {
                margin-bottom: 8px;
                padding: 12px;
            }
        }
    `;
    document.head.appendChild(style);
}