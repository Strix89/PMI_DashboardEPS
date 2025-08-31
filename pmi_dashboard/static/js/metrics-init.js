/**
 * Metrics System Initialization
 * 
 * This module initializes the real-time metrics monitoring system
 * and integrates it with the existing node dashboard functionality.
 */

class MetricsInitializer {
    constructor() {
        this.initialized = false;
        this.nodeMonitoringActive = new Set();
        
        this.init();
    }

    /**
     * Initialize the metrics system
     */
    init() {
        if (this.initialized) return;

        // Wait for DOM and all dependencies to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    /**
     * Setup the metrics system
     */
    setup() {
        // Ensure all required dependencies are available
        if (!this.checkDependencies()) {
            console.warn('Metrics system dependencies not ready, retrying...');
            setTimeout(() => this.setup(), 1000);
            return;
        }

        this.setupEventListeners();
        this.enhanceExistingNodes();
        this.initialized = true;

        console.log('Metrics system initialized successfully');
    }

    /**
     * Check if all required dependencies are available
     * @returns {boolean} True if all dependencies are ready
     */
    checkDependencies() {
        return (
            typeof metricsMonitor !== 'undefined' &&
            typeof metricsVisualizer !== 'undefined' &&
            typeof resourceManager !== 'undefined' &&
            typeof proxmoxAPI !== 'undefined'
        );
    }

    /**
     * Setup event listeners for metrics integration
     */
    setupEventListeners() {
        // Listen for nodes being loaded/updated
        document.addEventListener('nodesLoaded', (e) => {
            this.handleNodesLoaded(e.detail.nodes);
        });

        // Listen for individual node updates
        document.addEventListener('nodeUpdated', (e) => {
            this.handleNodeUpdated(e.detail.node);
        });

        // Listen for tab changes to manage monitoring
        document.addEventListener('tabchange', (e) => {
            if (e.detail.tab === 'proxmox') {
                this.startAllNodeMonitoring();
            } else {
                this.pauseAllNodeMonitoring();
            }
        });

        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAllNodeMonitoring();
            } else if (this.isProxmoxTabActive()) {
                this.startAllNodeMonitoring();
            }
        });

        // Listen for resource section events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.resources-btn')) {
                this.handleResourcesButtonClick(e);
            }
        });

        // Initialize operation history manager if available
        this.initializeHistoryManager();
    }

    /**
     * Handle nodes being loaded
     * @param {Array} nodes - Array of node objects
     */
    handleNodesLoaded(nodes) {
        if (!Array.isArray(nodes)) return;

        console.log(`Nodes loaded: ${nodes.length} nodes`);
        
        // Node monitoring is handled by the existing node-dashboard.js
        // We only need to enhance the node cards for resource viewing
        this.enhanceExistingNodes();
    }

    /**
     * Handle individual node update
     * @param {Object} node - Node object
     */
    handleNodeUpdated(node) {
        if (!node || !node.id) return;

        // Node updates are handled by the existing node-dashboard.js
        // We just need to ensure the node card is properly enhanced
        const nodeCard = document.querySelector(`[data-node-id="${node.id}"]`);
        if (nodeCard) {
            this.enhanceNodeCard(nodeCard);
        }
    }

    /**
     * Node monitoring is handled by the existing node-dashboard.js system
     * These functions are kept for compatibility but don't perform node monitoring
     */
    startNodeMonitoring(nodeId) {
        // Node monitoring is handled by node-dashboard.js
        console.log(`Node monitoring for ${nodeId} is handled by node-dashboard.js`);
    }

    stopNodeMonitoring(nodeId) {
        // Node monitoring is handled by node-dashboard.js
        console.log(`Node monitoring for ${nodeId} is handled by node-dashboard.js`);
    }

    startAllNodeMonitoring() {
        // Node monitoring is handled by node-dashboard.js
        console.log('Node monitoring is handled by node-dashboard.js');
    }

    pauseAllNodeMonitoring() {
        // Node monitoring is handled by node-dashboard.js
        console.log('Node monitoring is handled by node-dashboard.js');
    }

    /**
     * Node metrics updates are handled by the existing node-dashboard.js system
     */
    handleNodeMetricsUpdate(nodeId, data) {
        // Node metrics updates are handled by node-dashboard.js
        console.log(`Node metrics update for ${nodeId} is handled by node-dashboard.js`);
    }

    handleNodeMetricsError(nodeId, error) {
        // Node metrics errors are handled by node-dashboard.js
        console.log(`Node metrics error for ${nodeId} is handled by node-dashboard.js`);
    }

    /**
     * Update node card with new metrics
     * @param {HTMLElement} nodeCard - Node card element
     * @param {Object} data - Metrics data
     */
    updateNodeCardMetrics(nodeCard, data) {
        // Update CPU usage
        if (data.cpu_usage !== undefined) {
            this.updateNodeMetric(nodeCard, 'cpu', data.cpu_usage);
        }

        // Update memory usage
        if (data.memory_usage !== undefined && data.memory_total > 0) {
            const memoryPercentage = (data.memory_usage / data.memory_total) * 100;
            this.updateNodeMetric(nodeCard, 'memory', memoryPercentage);
        }

        // Update disk usage
        if (data.disk_usage !== undefined && data.disk_total > 0) {
            const diskPercentage = (data.disk_usage / data.disk_total) * 100;
            this.updateNodeMetric(nodeCard, 'disk', diskPercentage);
        }

        // Update last updated timestamp
        const lastUpdated = nodeCard.querySelector('.last-updated small');
        if (lastUpdated) {
            lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }

        // Remove error state if present
        nodeCard.classList.remove('connection-error');
    }

    /**
     * Update a specific metric on a node card
     * @param {HTMLElement} nodeCard - Node card element
     * @param {string} metricType - Type of metric (cpu, memory, disk)
     * @param {number} percentage - Usage percentage
     */
    updateNodeMetric(nodeCard, metricType, percentage) {
        const metricElement = nodeCard.querySelector(`.metric.${metricType}, .metric[data-metric="${metricType}"]`);
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
     * Show connection error on node card
     * @param {HTMLElement} nodeCard - Node card element
     */
    showNodeConnectionError(nodeCard) {
        nodeCard.classList.add('connection-error');
        
        const statusIndicator = nodeCard.querySelector('.status-indicator');
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator error';
            const statusIcon = statusIndicator.querySelector('i');
            const statusText = statusIndicator.lastChild;
            
            if (statusIcon) {
                statusIcon.className = 'fas fa-exclamation-triangle';
            }
            if (statusText && statusText.nodeType === Node.TEXT_NODE) {
                statusText.textContent = ' Error';
            }
        }
    }

    /**
     * Handle resources button click
     * @param {Event} e - Click event
     */
    handleResourcesButtonClick(e) {
        const nodeCard = e.target.closest('.node-card');
        if (!nodeCard) return;

        const nodeId = nodeCard.getAttribute('data-node-id');
        const nodeName = nodeCard.querySelector('.node-name')?.textContent || 'Unknown Node';

        if (nodeId && resourceManager) {
            resourceManager.showResourcesSection(nodeId, nodeName);
        }
    }

    /**
     * Enhance existing node cards with real-time capabilities
     */
    enhanceExistingNodes() {
        const nodeCards = document.querySelectorAll('.node-card[data-node-id]');
        
        nodeCards.forEach(card => {
            this.enhanceNodeCard(card);
        });
    }

    /**
     * Enhance a node card with real-time capabilities
     * @param {HTMLElement} nodeCard - Node card element
     */
    enhanceNodeCard(nodeCard) {
        // Ensure metrics have proper structure for updates
        this.ensureMetricStructure(nodeCard);
    }

    /**
     * Ensure node card has proper metric structure
     * @param {HTMLElement} nodeCard - Node card element
     */
    ensureMetricStructure(nodeCard) {
        const metrics = ['cpu', 'memory', 'disk'];
        
        metrics.forEach(metricType => {
            const metricElement = nodeCard.querySelector(`.metric.${metricType}, .metric[data-metric="${metricType}"]`);
            if (!metricElement) return;

            // Ensure progress bar has proper classes
            const progressFill = metricElement.querySelector('.progress-fill');
            if (progressFill && !progressFill.classList.contains('bg-success')) {
                progressFill.classList.add('bg-success');
            }

            // Ensure metric text element exists
            if (!metricElement.querySelector('.metric-text')) {
                const metricValue = metricElement.querySelector('.metric-value');
                if (metricValue) {
                    const metricText = document.createElement('span');
                    metricText.className = 'metric-text';
                    metricText.textContent = '0%';
                    metricValue.appendChild(metricText);
                }
            }
        });
    }

    /**
     * Check if Proxmox tab is currently active
     * @returns {boolean} True if Proxmox tab is active
     */
    isProxmoxTabActive() {
        const activeTab = document.querySelector('.nav-link.active');
        return activeTab && activeTab.getAttribute('data-tab') === 'proxmox';
    }

    /**
     * Initialize operation history manager
     */
    initializeHistoryManager() {
        // Check if operation history manager is available
        if (typeof OperationHistoryManager !== 'undefined' && !window.operationHistoryManager) {
            // Initialize the history manager
            window.operationHistoryManager = new OperationHistoryManager();
            console.log('Operation history manager initialized');
            
            // Set up integration with resource manager
            this.setupHistoryIntegration();
        }
    }

    /**
     * Setup integration between history manager and resource manager
     */
    setupHistoryIntegration() {
        // Listen for resource manager events to update history context
        document.addEventListener('resourceSectionShown', (e) => {
            const { nodeId } = e.detail;
            if (window.operationHistoryManager && nodeId) {
                window.operationHistoryManager.setNodeId(nodeId);
            }
        });

        // Listen for resource operations to refresh history
        document.addEventListener('resourceOperationCompleted', (e) => {
            if (window.operationHistoryManager) {
                // Refresh history after a short delay to allow backend to process
                setTimeout(() => {
                    window.operationHistoryManager.refreshHistory();
                }, 1000);
            }
        });
    }

    /**
     * Get monitoring status
     * @returns {Object} Status information
     */
    getStatus() {
        return {
            initialized: this.initialized,
            activeNodes: Array.from(this.nodeMonitoringActive),
            monitoringCount: this.nodeMonitoringActive.size,
            historyManagerAvailable: typeof window.operationHistoryManager !== 'undefined'
        };
    }
}

// Initialize when DOM is ready
let metricsInitializer;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        metricsInitializer = new MetricsInitializer();
    });
} else {
    metricsInitializer = new MetricsInitializer();
}

// Export for use in other modules
window.MetricsInitializer = MetricsInitializer;
window.metricsInitializer = metricsInitializer;