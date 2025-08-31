/**
 * Real-time Metrics Monitoring System
 * 
 * This module provides real-time monitoring capabilities for Proxmox nodes and resources,
 * including AJAX polling, metrics visualization, and efficient data update strategies.
 */

class MetricsMonitor {
    constructor(options = {}) {
        this.options = {
            defaultInterval: options.defaultInterval || 5000, // 5 seconds
            maxRetries: options.maxRetries || 3,
            retryDelay: options.retryDelay || 2000,
            enableAutoRefresh: options.enableAutoRefresh !== false,
            batchUpdates: options.batchUpdates !== false,
            ...options
        };

        this.activePollers = new Map();
        this.retryCounters = new Map();
        this.lastUpdateTimes = new Map();
        this.isVisible = true;
        this.globalPaused = false;

        this.init();
    }

    /**
     * Initialize the metrics monitor
     */
    init() {
        this.setupVisibilityHandling();
        this.setupEventListeners();
        console.log('MetricsMonitor initialized');
    }

    /**
     * Setup page visibility handling to pause/resume monitoring
     */
    setupVisibilityHandling() {
        document.addEventListener('visibilitychange', () => {
            this.isVisible = !document.hidden;
            
            if (this.isVisible) {
                console.log('Page visible - resuming metrics monitoring');
                this.resumeAll();
            } else {
                console.log('Page hidden - pausing metrics monitoring');
                this.pauseAll();
            }
        });
    }

    /**
     * Setup event listeners for user interactions
     */
    setupEventListeners() {
        // Listen for tab changes to optimize polling
        document.addEventListener('tabchange', (e) => {
            if (e.detail.tab === 'proxmox') {
                this.resumeAll();
            } else {
                this.pauseAll();
            }
        });

        // Listen for network status changes
        window.addEventListener('online', () => {
            console.log('Network online - resuming metrics monitoring');
            this.resumeAll();
        });

        window.addEventListener('offline', () => {
            console.log('Network offline - pausing metrics monitoring');
            this.pauseAll();
        });
    }

    /**
     * Start monitoring a node's metrics
     * @param {string} nodeId - Node ID
     * @param {Object} options - Monitoring options
     */
    startNodeMonitoring(nodeId, options = {}) {
        const pollerId = `node-${nodeId}`;
        
        if (this.activePollers.has(pollerId)) {
            console.log(`Node monitoring already active for ${nodeId}`);
            return;
        }

        const config = {
            type: 'node',
            nodeId: nodeId,
            interval: options.interval || this.options.defaultInterval,
            callback: options.callback || this.defaultNodeCallback.bind(this),
            errorCallback: options.errorCallback || this.defaultErrorCallback.bind(this),
            ...options
        };

        this.startPoller(pollerId, config);
        console.log(`Started node monitoring for ${nodeId}`);
    }

    /**
     * Start monitoring a resource's metrics
     * @param {string} nodeId - Node ID
     * @param {number} vmid - VM/Container ID
     * @param {Object} options - Monitoring options
     */
    startResourceMonitoring(nodeId, vmid, options = {}) {
        const pollerId = `resource-${nodeId}-${vmid}`;
        
        if (this.activePollers.has(pollerId)) {
            console.log(`Resource monitoring already active for ${nodeId}/${vmid}`);
            return;
        }

        const config = {
            type: 'resource',
            nodeId: nodeId,
            vmid: vmid,
            interval: options.interval || this.options.defaultInterval,
            callback: options.callback || this.defaultResourceCallback.bind(this),
            errorCallback: options.errorCallback || this.defaultErrorCallback.bind(this),
            ...options
        };

        this.startPoller(pollerId, config);
        console.log(`Started resource monitoring for ${nodeId}/${vmid}`);
    }

    /**
     * Start monitoring all resources for a node
     * @param {string} nodeId - Node ID
     * @param {Object} options - Monitoring options
     */
    startNodeResourcesMonitoring(nodeId, options = {}) {
        const pollerId = `node-resources-${nodeId}`;
        
        if (this.activePollers.has(pollerId)) {
            console.log(`Node resources monitoring already active for ${nodeId}`);
            return;
        }

        const config = {
            type: 'node-resources',
            nodeId: nodeId,
            interval: options.interval || 3000, // 3 seconds for smoother updates
            callback: options.callback || this.defaultNodeResourcesCallback.bind(this),
            errorCallback: options.errorCallback || this.defaultErrorCallback.bind(this),
            silent: options.silent !== false, // Default to silent updates
            ...options
        };

        this.startPoller(pollerId, config);
        console.log(`Started node resources monitoring for ${nodeId}`);
    }

    /**
     * Start a generic poller
     * @param {string} pollerId - Unique poller ID
     * @param {Object} config - Poller configuration
     */
    startPoller(pollerId, config) {
        if (this.activePollers.has(pollerId)) {
            this.stopPoller(pollerId);
        }

        const poller = {
            config: config,
            intervalId: null,
            isRunning: false,
            isPaused: false
        };

        this.activePollers.set(pollerId, poller);
        this.retryCounters.set(pollerId, 0);

        if (this.isVisible && !this.globalPaused) {
            this.resumePoller(pollerId);
        }
    }

    /**
     * Resume a specific poller
     * @param {string} pollerId - Poller ID
     */
    resumePoller(pollerId) {
        const poller = this.activePollers.get(pollerId);
        if (!poller || poller.isRunning) return;

        poller.isPaused = false;
        poller.isRunning = true;

        // Execute immediately, then start interval
        this.executePoller(pollerId);

        poller.intervalId = setInterval(() => {
            if (!poller.isPaused && this.isVisible && !this.globalPaused) {
                this.executePoller(pollerId);
            }
        }, poller.config.interval);

        console.log(`Resumed poller: ${pollerId}`);
    }

    /**
     * Pause a specific poller
     * @param {string} pollerId - Poller ID
     */
    pausePoller(pollerId) {
        const poller = this.activePollers.get(pollerId);
        if (!poller) return;

        poller.isPaused = true;
        poller.isRunning = false;

        if (poller.intervalId) {
            clearInterval(poller.intervalId);
            poller.intervalId = null;
        }

        console.log(`Paused poller: ${pollerId}`);
    }

    /**
     * Stop and remove a poller
     * @param {string} pollerId - Poller ID
     */
    stopPoller(pollerId) {
        this.pausePoller(pollerId);
        this.activePollers.delete(pollerId);
        this.retryCounters.delete(pollerId);
        this.lastUpdateTimes.delete(pollerId);
        console.log(`Stopped poller: ${pollerId}`);
    }

    /**
     * Execute a poller's data fetch
     * @param {string} pollerId - Poller ID
     */
    async executePoller(pollerId) {
        const poller = this.activePollers.get(pollerId);
        if (!poller || poller.isPaused) return;

        const { config } = poller;

        try {
            let data;

            switch (config.type) {
                case 'node':
                    data = await this.fetchNodeMetrics(config.nodeId);
                    break;
                case 'resource':
                    data = await this.fetchResourceMetrics(config.nodeId, config.vmid);
                    break;
                case 'node-resources':
                    data = await this.fetchNodeResources(config.nodeId);
                    break;
                default:
                    throw new Error(`Unknown poller type: ${config.type}`);
            }

            // Reset retry counter on success
            this.retryCounters.set(pollerId, 0);
            this.lastUpdateTimes.set(pollerId, Date.now());

            // Call success callback
            if (config.callback) {
                config.callback(data, pollerId, config);
            }

        } catch (error) {
            console.error(`Poller ${pollerId} failed:`, error);

            const retryCount = this.retryCounters.get(pollerId) || 0;
            this.retryCounters.set(pollerId, retryCount + 1);

            // Call error callback
            if (config.errorCallback) {
                config.errorCallback(error, pollerId, config, retryCount);
            }

            // Stop poller if max retries exceeded
            if (retryCount >= this.options.maxRetries) {
                console.error(`Poller ${pollerId} exceeded max retries, stopping`);
                this.stopPoller(pollerId);
            }
        }
    }

    /**
     * Fetch node metrics from API
     * @param {string} nodeId - Node ID
     * @returns {Promise} Node metrics data
     */
    async fetchNodeMetrics(nodeId) {
        // Get all nodes and find the specific one
        const response = await proxmoxAPI.makeRequest('GET', '/nodes');
        if (response.success && response.data) {
            const node = response.data.find(n => n.id === nodeId);
            return node || null;
        }
        return null;
    }

    /**
     * Fetch resource metrics from API
     * @param {string} nodeId - Node ID
     * @param {number} vmid - VM/Container ID
     * @returns {Promise} Resource metrics data
     */
    async fetchResourceMetrics(nodeId, vmid) {
        const response = await proxmoxAPI.makeRequest('GET', `/nodes/${nodeId}/resources/${vmid}/metrics`);
        return response.data;
    }

    /**
     * Fetch all resources for a node
     * @param {string} nodeId - Node ID
     * @returns {Promise} Node resources data
     */
    async fetchNodeResources(nodeId) {
        const response = await proxmoxAPI.makeRequest('GET', `/nodes/${nodeId}/resources`);
        return response.data;
    }

    /**
     * Default callback for node metrics updates
     * @param {Object} data - Node metrics data
     * @param {string} pollerId - Poller ID
     * @param {Object} config - Poller configuration
     */
    defaultNodeCallback(data, pollerId, config) {
        const nodeCard = document.querySelector(`[data-node-id="${config.nodeId}"]`);
        if (nodeCard) {
            this.updateNodeCard(nodeCard, data);
        }
    }

    /**
     * Default callback for resource metrics updates
     * @param {Object} data - Resource metrics data
     * @param {string} pollerId - Poller ID
     * @param {Object} config - Poller configuration
     */
    defaultResourceCallback(data, pollerId, config) {
        const resourceCard = document.querySelector(`[data-resource-id="${config.vmid}"]`);
        if (resourceCard) {
            this.updateResourceCard(resourceCard, data);
        }
    }

    /**
     * Default callback for node resources updates
     * @param {Object} data - Node resources data
     * @param {string} pollerId - Poller ID
     * @param {Object} config - Poller configuration
     */
    defaultNodeResourcesCallback(data, pollerId, config) {
        if (data && Array.isArray(data)) {
            data.forEach(resource => {
                const resourceCard = document.querySelector(`[data-resource-id="${resource.vmid}"]`);
                if (resourceCard) {
                    this.updateResourceCard(resourceCard, resource);
                }
            });
        }
    }

    /**
     * Default error callback
     * @param {Error} error - Error object
     * @param {string} pollerId - Poller ID
     * @param {Object} config - Poller configuration
     * @param {number} retryCount - Current retry count
     */
    defaultErrorCallback(error, pollerId, config, retryCount) {
        console.warn(`Poller ${pollerId} error (retry ${retryCount}):`, error.message);

        // Update UI to show connection issues
        if (config.type === 'node') {
            const nodeCard = document.querySelector(`[data-node-id="${config.nodeId}"]`);
            if (nodeCard) {
                this.showNodeError(nodeCard, error.message);
            }
        }
    }

    /**
     * Update node card with new metrics data
     * @param {HTMLElement} nodeCard - Node card element
     * @param {Object} data - Node metrics data
     */
    updateNodeCard(nodeCard, data) {
        // Update connection status
        const statusIndicator = nodeCard.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.className = `status-indicator ${data.status || 'offline'}`;
            const statusIcon = statusIndicator.querySelector('i');
            const statusText = statusIndicator.querySelector('.status-text') || statusIndicator.lastChild;
            
            if (statusIcon) {
                statusIcon.className = data.status === 'online' ? 'fas fa-circle' : 'fas fa-times-circle';
            }
            if (statusText) {
                statusText.textContent = (data.status || 'offline').charAt(0).toUpperCase() + (data.status || 'offline').slice(1);
            }
        }

        // Update CPU usage
        this.updateMetricBar(nodeCard, 'cpu', data.cpu_usage || 0);

        // Update memory usage
        if (data.memory_total && data.memory_total > 0) {
            const memoryPercentage = (data.memory_usage / data.memory_total) * 100;
            this.updateMetricBar(nodeCard, 'memory', memoryPercentage);
        }

        // Update disk usage
        if (data.disk_total && data.disk_total > 0) {
            const diskPercentage = (data.disk_usage / data.disk_total) * 100;
            this.updateMetricBar(nodeCard, 'disk', diskPercentage);
        }

        // Update last updated timestamp
        const lastUpdated = nodeCard.querySelector('.last-updated small');
        if (lastUpdated) {
            lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }

        // Remove any error states
        nodeCard.classList.remove('connection-error');
    }

    /**
     * Update resource card with new metrics data
     * @param {HTMLElement} resourceCard - Resource card element
     * @param {Object} data - Resource metrics data
     */
    updateResourceCard(resourceCard, data) {
        // Update status
        const statusBadge = resourceCard.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `status-badge status-${data.status || 'unknown'}`;
            statusBadge.textContent = (data.status || 'unknown').toUpperCase();
        }

        // Update CPU usage
        if (data.cpu_usage !== undefined) {
            this.updateMetricBar(resourceCard, 'cpu', data.cpu_usage);
        }

        // Update memory usage
        if (data.memory_usage !== undefined && data.memory_total > 0) {
            const memoryPercentage = (data.memory_usage / data.memory_total) * 100;
            this.updateMetricBar(resourceCard, 'memory', memoryPercentage);
        }

        // Update disk usage
        if (data.disk_usage !== undefined && data.disk_total > 0) {
            const diskPercentage = (data.disk_usage / data.disk_total) * 100;
            this.updateMetricBar(resourceCard, 'disk', diskPercentage);
        }

        // Update uptime
        const uptimeElement = resourceCard.querySelector('.uptime-value');
        if (uptimeElement && data.uptime !== undefined) {
            uptimeElement.textContent = formatUptime(data.uptime);
        }
    }

    /**
     * Update a metric progress bar
     * @param {HTMLElement} container - Container element
     * @param {string} metricType - Type of metric (cpu, memory, disk)
     * @param {number} percentage - Usage percentage
     */
    updateMetricBar(container, metricType, percentage) {
        const metricElement = container.querySelector(`.metric.${metricType}, .metric[data-metric="${metricType}"]`);
        if (!metricElement) return;

        const progressBar = metricElement.querySelector('.progress-fill');
        const metricText = metricElement.querySelector('.metric-text');

        if (progressBar) {
            // Animate the progress bar
            progressBar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
            
            // Update color based on usage level
            const colorClass = getProgressColor(percentage);
            progressBar.className = `progress-fill ${colorClass}`;
        }

        if (metricText) {
            metricText.textContent = `${percentage.toFixed(1)}%`;
        }
    }

    /**
     * Show error state on node card
     * @param {HTMLElement} nodeCard - Node card element
     * @param {string} errorMessage - Error message
     */
    showNodeError(nodeCard, errorMessage) {
        nodeCard.classList.add('connection-error');
        
        const statusIndicator = nodeCard.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator error';
            const statusIcon = statusIndicator.querySelector('i');
            const statusText = statusIndicator.querySelector('.status-text') || statusIndicator.lastChild;
            
            if (statusIcon) {
                statusIcon.className = 'fas fa-exclamation-triangle';
            }
            if (statusText) {
                statusText.textContent = 'Error';
            }
        }
    }

    /**
     * Resume all active pollers
     */
    resumeAll() {
        this.globalPaused = false;
        for (const [pollerId, poller] of this.activePollers) {
            if (!poller.isRunning) {
                this.resumePoller(pollerId);
            }
        }
    }

    /**
     * Pause all active pollers
     */
    pauseAll() {
        this.globalPaused = true;
        for (const [pollerId] of this.activePollers) {
            this.pausePoller(pollerId);
        }
    }

    /**
     * Stop all pollers and clean up
     */
    stopAll() {
        for (const [pollerId] of this.activePollers) {
            this.stopPoller(pollerId);
        }
        console.log('All metrics monitoring stopped');
    }

    /**
     * Get monitoring status
     * @returns {Object} Status information
     */
    getStatus() {
        return {
            activePollers: this.activePollers.size,
            isVisible: this.isVisible,
            globalPaused: this.globalPaused,
            pollers: Array.from(this.activePollers.keys())
        };
    }

    /**
     * Update polling interval for a specific poller
     * @param {string} pollerId - Poller ID
     * @param {number} newInterval - New interval in milliseconds
     */
    updatePollerInterval(pollerId, newInterval) {
        const poller = this.activePollers.get(pollerId);
        if (!poller) return;

        poller.config.interval = newInterval;
        
        if (poller.isRunning) {
            this.pausePoller(pollerId);
            this.resumePoller(pollerId);
        }
    }

    /**
     * Get last update time for a poller
     * @param {string} pollerId - Poller ID
     * @returns {number|null} Last update timestamp
     */
    getLastUpdateTime(pollerId) {
        return this.lastUpdateTimes.get(pollerId) || null;
    }
}

// Create global instance
const metricsMonitor = new MetricsMonitor();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MetricsMonitor,
        metricsMonitor
    };
}

// Make available globally
window.MetricsMonitor = MetricsMonitor;
window.metricsMonitor = metricsMonitor;