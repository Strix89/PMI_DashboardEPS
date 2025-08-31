/**
 * Enhanced Resource Manager with Real-time Metrics
 * 
 * This module manages VM/LXC resources with real-time monitoring,
 * integrating with the metrics monitor and visualization components.
 */

class EnhancedResourceManager {
    constructor() {
        this.currentNodeId = null;
        this.currentNodeName = null;
        this.resources = new Map();
        this.isVisible = false;
        this.refreshInterval = 2000; // 2 seconds for real-time updates
        this.operationInProgress = new Set();
        
        this.init();
    }

    /**
     * Initialize the resource manager
     */
    init() {
        this.setupEventListeners();
        console.log('ResourceManager initialized');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for resource control button clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.resource-control-btn')) {
                this.handleResourceControl(e);
            }
            
            if (e.target.closest('.refresh-resources-btn')) {
                this.refreshResources();
            }
            
            if (e.target.closest('.close-resources-btn')) {
                this.hideResourcesSection();
            }
        });

        // Listen for tab changes to manage monitoring
        document.addEventListener('tabchange', (e) => {
            if (e.detail.tab !== 'proxmox' && this.isVisible) {
                this.pauseMonitoring();
            } else if (e.detail.tab === 'proxmox' && this.isVisible) {
                this.resumeMonitoring();
            }
        });
    }

    /**
     * Show resources section for a specific node
     * @param {string} nodeId - Node ID
     * @param {string} nodeName - Node display name
     */
    async showResourcesSection(nodeId, nodeName) {
        this.currentNodeId = nodeId;
        this.currentNodeName = nodeName;
        this.isVisible = true;

        // Create or update resources section
        this.createResourcesSection();
        
        // Load initial resources
        await this.loadResources();
        
        // Start real-time monitoring
        this.startMonitoring();
        
        // Scroll to resources section
        const resourcesSection = document.getElementById('resources-section');
        if (resourcesSection) {
            resourcesSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    /**
     * Hide resources section
     */
    hideResourcesSection() {
        this.isVisible = false;
        this.stopMonitoring();
        
        const resourcesSection = document.getElementById('resources-section');
        if (resourcesSection) {
            resourcesSection.style.display = 'none';
        }
        
        this.currentNodeId = null;
        this.currentNodeName = null;
        this.resources.clear();
    }

    /**
     * Create the resources section HTML
     */
    createResourcesSection() {
        let resourcesSection = document.getElementById('resources-section');
        
        if (!resourcesSection) {
            resourcesSection = document.createElement('div');
            resourcesSection.id = 'resources-section';
            resourcesSection.className = 'resources-section';
            
            // Insert after the nodes grid
            const nodesGrid = document.querySelector('.nodes-grid');
            if (nodesGrid && nodesGrid.parentNode) {
                nodesGrid.parentNode.insertBefore(resourcesSection, nodesGrid.nextSibling);
            } else {
                // Fallback: append to proxmox tab content
                const proxmoxTab = document.getElementById('proxmox-tab');
                if (proxmoxTab) {
                    proxmoxTab.appendChild(resourcesSection);
                }
            }
        }

        resourcesSection.style.display = 'block';
        resourcesSection.innerHTML = `
            <div class="resources-header">
                <div class="resources-title">
                    <h3>
                        <i class="fas fa-server"></i>
                        ${this.currentNodeName} Resources
                    </h3>
                    <div class="resources-controls">
                        <button class="btn btn-secondary refresh-resources-btn" title="Refresh Resources">
                            <i class="fas fa-sync-alt"></i>
                            Refresh
                        </button>
                        <button class="btn btn-secondary close-resources-btn" title="Close Resources View">
                            <i class="fas fa-times"></i>
                            Close
                        </button>
                    </div>
                </div>
                <div class="resources-stats">
                    <div class="stat-item">
                        <span class="stat-label">Total Resources:</span>
                        <span class="stat-value" id="total-resources">-</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Running:</span>
                        <span class="stat-value running" id="running-resources">-</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Stopped:</span>
                        <span class="stat-value stopped" id="stopped-resources">-</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Last Updated:</span>
                        <span class="stat-value" id="resources-last-updated">Never</span>
                    </div>
                </div>
            </div>
            <div class="resources-content">
                <div class="resources-loading" id="resources-loading">
                    <div class="loading-spinner"></div>
                    <span>Loading resources...</span>
                </div>
                <div class="resources-grid" id="resources-grid" style="display: none;">
                    <!-- Resources will be populated here -->
                </div>
                <div class="resources-empty" id="resources-empty" style="display: none;">
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <h4>No Resources Found</h4>
                        <p>This node doesn't have any VMs or LXC containers.</p>
                    </div>
                </div>
                <div class="resources-error" id="resources-error" style="display: none;">
                    <div class="error-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <h4>Failed to Load Resources</h4>
                        <p id="resources-error-message">An error occurred while loading resources.</p>
                        <button class="btn btn-primary retry-resources-btn">
                            <i class="fas fa-redo"></i>
                            Retry
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add retry button listener
        const retryBtn = resourcesSection.querySelector('.retry-resources-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.loadResources());
        }
    }

    /**
     * Load resources from the API
     */
    async loadResources() {
        if (!this.currentNodeId) return;

        this.showLoadingState();

        try {
            const response = await proxmoxAPI.getNodeResources(this.currentNodeId);
            
            if (response.success && response.data) {
                this.resources.clear();
                
                // Store resources in map for quick access
                response.data.forEach(resource => {
                    this.resources.set(resource.vmid, resource);
                });
                
                this.renderResources(response.data);
                this.updateResourcesStats(response.data);
            } else {
                throw new Error(response.error || 'Failed to load resources');
            }
            
        } catch (error) {
            console.error('Failed to load resources:', error);
            this.showErrorState(error.message);
            if (typeof handleApiError === 'function') {
                handleApiError(error, 'load resources');
            }
        }
    }

    /**
     * Refresh resources silently without showing loading state
     */
    async refreshResourcesSilently() {
        if (!this.currentNodeId) return;

        try {
            // Store current scroll position
            const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;
            
            const response = await proxmoxAPI.getNodeResources(this.currentNodeId);
            
            if (response.success && response.data) {
                // Update existing resources silently
                response.data.forEach(resource => {
                    const existingResource = this.resources.get(resource.vmid);
                    if (existingResource) {
                        // Only update if there are actual changes
                        if (this.hasResourceChanged(existingResource, resource)) {
                            this.resources.set(resource.vmid, resource);
                            this.updateResourceCardSilently(resource.vmid, resource);
                        }
                    } else {
                        // New resource - add it
                        this.resources.set(resource.vmid, resource);
                        this.addNewResourceCard(resource);
                    }
                });

                // Remove resources that no longer exist
                const currentVmids = new Set(response.data.map(r => r.vmid));
                for (const [vmid] of this.resources) {
                    if (!currentVmids.has(vmid)) {
                        this.removeResourceCard(vmid);
                        this.resources.delete(vmid);
                    }
                }

                // Update stats silently
                this.updateResourcesStatsSilently(response.data);
            }

            // Restore scroll position if it changed
            const newScrollPosition = window.pageYOffset || document.documentElement.scrollTop;
            if (Math.abs(newScrollPosition - scrollPosition) > 5) {
                window.scrollTo(0, scrollPosition);
            }
            
        } catch (error) {
            console.error('Silent refresh failed:', error);
            // Don't show error notifications for silent refresh failures
        }
    }

    /**
     * Check if a resource has changed significantly
     * @param {Object} oldResource - Previous resource data
     * @param {Object} newResource - New resource data
     * @returns {boolean} True if resource has changed
     */
    hasResourceChanged(oldResource, newResource) {
        const significantFields = ['status', 'cpu_usage', 'memory_usage', 'disk_usage', 'uptime'];
        
        return significantFields.some(field => {
            const oldValue = oldResource[field];
            const newValue = newResource[field];
            
            // For numeric values, check if change is significant (> 1%)
            if (typeof oldValue === 'number' && typeof newValue === 'number') {
                const percentChange = Math.abs((newValue - oldValue) / (oldValue || 1)) * 100;
                return percentChange > 1;
            }
            
            // For other values, check exact equality
            return oldValue !== newValue;
        });
    }

    /**
     * Add a new resource card with animation
     * @param {Object} resource - Resource data
     */
    addNewResourceCard(resource) {
        const resourcesGrid = document.getElementById('resources-grid');
        if (!resourcesGrid) return;

        const resourceCard = document.createElement('div');
        resourceCard.innerHTML = this.createResourceCard(resource);
        resourceCard.style.opacity = '0';
        resourceCard.style.transform = 'translateY(20px)';
        
        resourcesGrid.appendChild(resourceCard.firstElementChild);
        
        // Animate in
        requestAnimationFrame(() => {
            const addedCard = resourcesGrid.lastElementChild;
            addedCard.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            addedCard.style.opacity = '1';
            addedCard.style.transform = 'translateY(0)';
        });
    }

    /**
     * Remove a resource card with animation
     * @param {number} vmid - VM/Container ID
     */
    removeResourceCard(vmid) {
        const resourceCard = document.querySelector(`[data-resource-id="${vmid}"]`);
        if (!resourceCard) return;

        resourceCard.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        resourceCard.style.opacity = '0';
        resourceCard.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            if (resourceCard.parentNode) {
                resourceCard.parentNode.removeChild(resourceCard);
            }
        }, 300);
    }

    /**
     * Render resources in the grid
     * @param {Array} resources - Array of resource objects
     */
    renderResources(resources) {
        const resourcesGrid = document.getElementById('resources-grid');
        if (!resourcesGrid) return;

        if (!resources || resources.length === 0) {
            this.showEmptyState();
            return;
        }

        // Render resources and show grid
        resourcesGrid.innerHTML = resources.map(resource => this.createResourceCard(resource)).join('');
        this.showResourcesGrid();
    }

    /**
     * Create a resource card HTML
     * @param {Object} resource - Resource object
     * @returns {string} HTML string
     */
    createResourceCard(resource) {
        const statusClass = this.getStatusClass(resource.status);
        const typeIcon = resource.type === 'qemu' ? 'fa-desktop' : 'fa-cube';
        const typeLabel = resource.type === 'qemu' ? 'VM' : 'LXC';
        
        const isRunning = resource.status === 'running';
        const inProgress = this.operationInProgress.has(resource.vmid);

        return `
            <div class="resource-card" data-resource-id="${resource.vmid}" data-resource-type="${resource.type}">
                <div class="resource-card-header">
                    <div class="resource-info">
                        <div class="resource-title">
                            <i class="fas ${typeIcon}"></i>
                            <span class="resource-name">${resource.name || `${typeLabel}-${resource.vmid}`}</span>
                            <span class="resource-id">#${resource.vmid}</span>
                        </div>
                        <div class="resource-type-badge">${typeLabel}</div>
                    </div>
                    <div class="resource-status">
                        ${metricsVisualizer.createStatusIndicator({
                            status: resource.status,
                            size: 'small',
                            animated: isRunning
                        }).outerHTML}
                    </div>
                </div>

                <div class="resource-card-body">
                    <div class="resource-metrics">
                        <div class="metric-row">
                            <div class="metric cpu-metric" data-metric="cpu">
                                <div class="metric-label">
                                    <i class="fas fa-microchip"></i>
                                    CPU
                                </div>
                                <div class="metric-value">
                                    ${this.createMetricBar('cpu', resource.cpu_usage || 0)}
                                    <span class="metric-text">${(resource.cpu_usage || 0).toFixed(1)}%</span>
                                </div>
                            </div>
                        </div>

                        <div class="metric-row">
                            <div class="metric memory-metric" data-metric="memory">
                                <div class="metric-label">
                                    <i class="fas fa-memory"></i>
                                    Memory
                                </div>
                                <div class="metric-value">
                                    ${this.createMetricBar('memory', this.calculatePercentage(resource.memory_usage, resource.memory_total))}
                                    <span class="metric-text">${this.formatMemory(resource.memory_usage, resource.memory_total)}</span>
                                </div>
                            </div>
                        </div>

                        <div class="metric-row">
                            <div class="metric disk-metric" data-metric="disk">
                                <div class="metric-label">
                                    <i class="fas fa-hdd"></i>
                                    Disk
                                </div>
                                <div class="metric-value">
                                    ${this.createMetricBar('disk', this.calculatePercentage(resource.disk_usage, resource.disk_total))}
                                    <span class="metric-text">${this.formatDisk(resource.disk_usage, resource.disk_total)}</span>
                                </div>
                            </div>
                        </div>

                        ${resource.uptime ? `
                            <div class="metric-row">
                                <div class="metric uptime-metric">
                                    <div class="metric-label">
                                        <i class="fas fa-clock"></i>
                                        Uptime
                                    </div>
                                    <div class="metric-value">
                                        <span class="uptime-value">${formatUptime(resource.uptime)}</span>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>

                <div class="resource-card-footer">
                    <div class="resource-controls">
                        ${this.createControlButtons(resource, inProgress)}
                    </div>
                    <div class="resource-info-extra">
                        <small class="text-muted">
                            Node: ${resource.node || 'Unknown'} | 
                            Last updated: <span class="last-updated-time">${new Date().toLocaleTimeString()}</span>
                        </small>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create metric progress bar HTML
     * @param {string} type - Metric type
     * @param {number} percentage - Usage percentage
     * @returns {string} HTML string
     */
    createMetricBar(type, percentage) {
        const colorClass = getProgressColor(percentage);
        return `
            <div class="progress-track">
                <div class="progress-fill ${colorClass}" style="width: ${Math.min(100, Math.max(0, percentage))}%"></div>
            </div>
        `;
    }

    /**
     * Create control buttons for a resource
     * @param {Object} resource - Resource object
     * @param {boolean} inProgress - Whether operation is in progress
     * @returns {string} HTML string
     */
    createControlButtons(resource, inProgress) {
        const isRunning = resource.status === 'running';
        const isStopped = resource.status === 'stopped';
        
        if (inProgress) {
            return `
                <div class="control-buttons">
                    <button class="btn btn-secondary" disabled>
                        <div class="loading-spinner small"></div>
                        Processing...
                    </button>
                </div>
            `;
        }

        return `
            <div class="control-buttons">
                ${isStopped ? `
                    <button class="btn btn-success resource-control-btn" 
                            data-action="start" 
                            data-vmid="${resource.vmid}"
                            title="Start ${resource.type === 'qemu' ? 'VM' : 'Container'}">
                        <i class="fas fa-play"></i>
                        Start
                    </button>
                ` : ''}
                
                ${isRunning ? `
                    <button class="btn btn-warning resource-control-btn" 
                            data-action="restart" 
                            data-vmid="${resource.vmid}"
                            title="Restart ${resource.type === 'qemu' ? 'VM' : 'Container'}">
                        <i class="fas fa-redo"></i>
                        Restart
                    </button>
                    <button class="btn btn-danger resource-control-btn" 
                            data-action="stop" 
                            data-vmid="${resource.vmid}"
                            title="Stop ${resource.type === 'qemu' ? 'VM' : 'Container'}">
                        <i class="fas fa-stop"></i>
                        Stop
                    </button>
                ` : ''}
            </div>
        `;
    }

    /**
     * Handle resource control button clicks
     * @param {Event} e - Click event
     */
    async handleResourceControl(e) {
        e.preventDefault();
        
        const button = e.target.closest('.resource-control-btn');
        if (!button) return;

        const action = button.getAttribute('data-action');
        const vmid = parseInt(button.getAttribute('data-vmid'));
        
        if (!action || !vmid || !this.currentNodeId) return;

        // Prevent multiple operations on the same resource
        if (this.operationInProgress.has(vmid)) {
            showNotification('Operation already in progress for this resource', 'warning');
            return;
        }

        await this.performResourceOperation(vmid, action);
    }

    /**
     * Perform a resource operation
     * @param {number} vmid - VM/Container ID
     * @param {string} action - Action to perform
     */
    async performResourceOperation(vmid, action) {
        const resource = this.resources.get(vmid);
        if (!resource) return;

        const resourceName = resource.name || `${resource.type === 'qemu' ? 'VM' : 'LXC'}-${vmid}`;
        
        // Mark operation as in progress
        this.operationInProgress.add(vmid);
        this.updateResourceCardControls(vmid, true);

        try {
            let response;
            
            switch (action) {
                case 'start':
                    response = await proxmoxAPI.startResource(this.currentNodeId, vmid);
                    break;
                case 'stop':
                    response = await proxmoxAPI.stopResource(this.currentNodeId, vmid);
                    break;
                case 'restart':
                    response = await proxmoxAPI.restartResource(this.currentNodeId, vmid);
                    break;
                default:
                    throw new Error(`Unknown action: ${action}`);
            }

            if (response.success) {
                showNotification(`Successfully ${action}ed ${resourceName}`, 'success');
                
                // Refresh resource data after a short delay
                setTimeout(() => {
                    this.refreshSingleResource(vmid);
                }, 2000);
            } else {
                throw new Error(response.error || `Failed to ${action} resource`);
            }

        } catch (error) {
            console.error(`Failed to ${action} resource ${vmid}:`, error);
            showNotification(`Failed to ${action} ${resourceName}: ${error.message}`, 'error');
            handleApiError(error, `${action} resource`);
        } finally {
            // Remove operation in progress flag
            this.operationInProgress.delete(vmid);
            this.updateResourceCardControls(vmid, false);
        }
    }

    /**
     * Update resource card controls
     * @param {number} vmid - VM/Container ID
     * @param {boolean} inProgress - Whether operation is in progress
     */
    updateResourceCardControls(vmid, inProgress) {
        const resourceCard = document.querySelector(`[data-resource-id="${vmid}"]`);
        if (!resourceCard) return;

        const controlsContainer = resourceCard.querySelector('.resource-controls');
        if (!controlsContainer) return;

        const resource = this.resources.get(vmid);
        if (!resource) return;

        controlsContainer.innerHTML = this.createControlButtons(resource, inProgress);
    }

    /**
     * Refresh a single resource
     * @param {number} vmid - VM/Container ID
     */
    async refreshSingleResource(vmid) {
        try {
            const response = await proxmoxAPI.getResourceMetrics(this.currentNodeId, vmid);
            
            if (response.success && response.data) {
                // Update resource in map
                const existingResource = this.resources.get(vmid);
                if (existingResource) {
                    const updatedResource = { ...existingResource, ...response.data };
                    this.resources.set(vmid, updatedResource);
                    
                    // Update the resource card
                    this.updateResourceCard(vmid, updatedResource);
                }
            }
        } catch (error) {
            console.error(`Failed to refresh resource ${vmid}:`, error);
        }
    }

    /**
     * Update a resource card with new data
     * @param {number} vmid - VM/Container ID
     * @param {Object} resource - Updated resource data
     */
    updateResourceCard(vmid, resource) {
        const resourceCard = document.querySelector(`[data-resource-id="${vmid}"]`);
        if (!resourceCard) return;

        // Update status indicator
        const statusIndicator = resourceCard.querySelector('.resource-status .status-indicator');
        if (statusIndicator) {
            const newStatus = metricsVisualizer.createStatusIndicator({
                status: resource.status,
                size: 'small',
                animated: resource.status === 'running'
            });
            statusIndicator.replaceWith(newStatus);
        }

        // Update metrics using the metrics monitor
        if (metricsMonitor) {
            metricsMonitor.updateResourceCard(resourceCard, resource);
        }

        // Update controls
        this.updateResourceCardControls(vmid, this.operationInProgress.has(vmid));

        // Update last updated time
        const lastUpdatedTime = resourceCard.querySelector('.last-updated-time');
        if (lastUpdatedTime) {
            lastUpdatedTime.textContent = new Date().toLocaleTimeString();
        }
    }

    /**
     * Update a resource card silently without animations
     * @param {number} vmid - VM/Container ID
     * @param {Object} resource - Updated resource data
     */
    updateResourceCardSilently(vmid, resource) {
        const resourceCard = document.querySelector(`[data-resource-id="${vmid}"]`);
        if (!resourceCard) return;

        // Update status indicator only if status changed
        const statusIndicator = resourceCard.querySelector('.resource-status .status-indicator');
        if (statusIndicator && !statusIndicator.classList.contains(resource.status)) {
            statusIndicator.className = `status-indicator ${resource.status} small`;
            const statusIcon = statusIndicator.querySelector('i');
            const statusText = statusIndicator.querySelector('.status-text');
            
            if (statusIcon) {
                statusIcon.className = this.getStatusIcon(resource.status);
            }
            if (statusText) {
                statusText.textContent = resource.status.toUpperCase();
            }
        }

        // Update metrics silently
        this.updateResourceMetricsSilently(resourceCard, resource);

        // Update controls only if operation status changed
        if (!this.operationInProgress.has(vmid)) {
            this.updateResourceCardControls(vmid, false);
        }
    }

    /**
     * Update resource metrics silently
     * @param {HTMLElement} resourceCard - Resource card element
     * @param {Object} resource - Resource data
     */
    updateResourceMetricsSilently(resourceCard, resource) {
        // Update CPU usage
        if (resource.cpu_usage !== undefined) {
            this.updateMetricSilently(resourceCard, 'cpu', resource.cpu_usage);
        }

        // Update memory usage
        if (resource.memory_usage !== undefined && resource.memory_total > 0) {
            const memoryPercentage = (resource.memory_usage / resource.memory_total) * 100;
            this.updateMetricSilently(resourceCard, 'memory', memoryPercentage);
        }

        // Update disk usage
        if (resource.disk_usage !== undefined && resource.disk_total > 0) {
            const diskPercentage = (resource.disk_usage / resource.disk_total) * 100;
            this.updateMetricSilently(resourceCard, 'disk', diskPercentage);
        }

        // Update uptime
        const uptimeElement = resourceCard.querySelector('.uptime-value');
        if (uptimeElement && resource.uptime !== undefined) {
            uptimeElement.textContent = formatUptime(resource.uptime);
        }
    }

    /**
     * Update a single metric silently
     * @param {HTMLElement} container - Container element
     * @param {string} metricType - Type of metric (cpu, memory, disk)
     * @param {number} percentage - Usage percentage
     */
    updateMetricSilently(container, metricType, percentage) {
        const metricElement = container.querySelector(`.metric.${metricType}-metric, .metric[data-metric="${metricType}"]`);
        if (!metricElement) return;

        const progressBar = metricElement.querySelector('.progress-fill');
        const metricText = metricElement.querySelector('.metric-text');

        if (progressBar) {
            const currentWidth = parseFloat(progressBar.style.width) || 0;
            const newWidth = Math.min(100, Math.max(0, percentage));
            
            // Only update if there's a significant change (> 0.5%)
            if (Math.abs(currentWidth - newWidth) > 0.5) {
                progressBar.style.width = `${newWidth}%`;
                
                // Update color based on usage level
                const colorClass = this.getProgressColor(percentage);
                progressBar.className = `progress-fill ${colorClass}`;
            }
        }

        if (metricText) {
            const newText = `${percentage.toFixed(1)}%`;
            if (metricText.textContent !== newText) {
                metricText.textContent = newText;
            }
        }
    }

    /**
     * Get progress color class based on percentage
     * @param {number} percentage - Usage percentage
     * @returns {string} Color class
     */
    getProgressColor(percentage) {
        if (percentage >= 90) return 'bg-danger';
        if (percentage >= 75) return 'bg-warning';
        if (percentage >= 50) return 'bg-info';
        return 'bg-success';
    }

    /**
     * Get status icon based on status
     * @param {string} status - Status value
     * @returns {string} Icon class
     */
    getStatusIcon(status) {
        const icons = {
            running: 'fas fa-play-circle',
            stopped: 'fas fa-stop-circle',
            paused: 'fas fa-pause-circle',
            error: 'fas fa-exclamation-triangle'
        };
        return icons[status] || 'fas fa-question-circle';
    }

    /**
     * Update a resource card silently without animations or layout shifts
     * @param {number} vmid - VM/Container ID
     * @param {Object} resource - Updated resource data
     */
    updateResourceCardSilently(vmid, resource) {
        const resourceCard = document.querySelector(`[data-resource-id="${vmid}"]`);
        if (!resourceCard) return;

        // Update status badge text only if changed
        const statusBadge = resourceCard.querySelector('.status-badge');
        if (statusBadge) {
            const newStatusText = (resource.status || 'unknown').toUpperCase();
            if (statusBadge.textContent !== newStatusText) {
                statusBadge.textContent = newStatusText;
                statusBadge.className = `status-badge status-${resource.status || 'unknown'}`;
                
                // Subtle color flash to indicate update
                statusBadge.style.transition = 'background-color 0.3s ease';
                statusBadge.style.backgroundColor = 'var(--primary-orange-subtle)';
                setTimeout(() => {
                    statusBadge.style.backgroundColor = '';
                }, 500);
            }
        }

        // Update metrics silently
        this.updateMetricsSilently(resourceCard, resource);

        // Update uptime if present
        const uptimeElement = resourceCard.querySelector('.uptime-value');
        if (uptimeElement && resource.uptime !== undefined) {
            const newUptime = formatUptime(resource.uptime);
            if (uptimeElement.textContent !== newUptime) {
                uptimeElement.textContent = newUptime;
            }
        }

        // Update last updated time with subtle highlight
        const lastUpdatedTime = resourceCard.querySelector('.last-updated-time');
        if (lastUpdatedTime) {
            const newTime = new Date().toLocaleTimeString();
            if (lastUpdatedTime.textContent !== newTime) {
                lastUpdatedTime.style.transition = 'color 0.3s ease';
                lastUpdatedTime.textContent = newTime;
                lastUpdatedTime.style.color = 'var(--primary-orange)';
                setTimeout(() => {
                    lastUpdatedTime.style.color = '';
                }, 800);
            }
        }
    }

    /**
     * Update metrics silently with smooth transitions
     * @param {HTMLElement} resourceCard - Resource card element
     * @param {Object} resource - Resource data
     */
    updateMetricsSilently(resourceCard, resource) {
        // Update CPU usage
        if (resource.cpu_usage !== undefined) {
            this.updateMetricBarSilently(resourceCard, 'cpu', resource.cpu_usage);
        }

        // Update memory usage
        if (resource.memory_usage !== undefined && resource.memory_total > 0) {
            const memoryPercentage = (resource.memory_usage / resource.memory_total) * 100;
            this.updateMetricBarSilently(resourceCard, 'memory', memoryPercentage);
            
            // Update memory text
            const memoryText = resourceCard.querySelector('.memory-metric .metric-text');
            if (memoryText) {
                const newText = this.formatMemory(resource.memory_usage, resource.memory_total);
                if (memoryText.textContent !== newText) {
                    memoryText.textContent = newText;
                }
            }
        }

        // Update disk usage
        if (resource.disk_usage !== undefined && resource.disk_total > 0) {
            const diskPercentage = (resource.disk_usage / resource.disk_total) * 100;
            this.updateMetricBarSilently(resourceCard, 'disk', diskPercentage);
            
            // Update disk text
            const diskText = resourceCard.querySelector('.disk-metric .metric-text');
            if (diskText) {
                const newText = this.formatDisk(resource.disk_usage, resource.disk_total);
                if (diskText.textContent !== newText) {
                    diskText.textContent = newText;
                }
            }
        }
    }

    /**
     * Update a metric progress bar silently
     * @param {HTMLElement} container - Container element
     * @param {string} metricType - Type of metric (cpu, memory, disk)
     * @param {number} percentage - Usage percentage
     */
    updateMetricBarSilently(container, metricType, percentage) {
        const metricElement = container.querySelector(`.metric.${metricType}-metric, .metric[data-metric="${metricType}"]`);
        if (!metricElement) return;

        const progressBar = metricElement.querySelector('.progress-fill');
        const metricText = metricElement.querySelector('.metric-text');

        if (progressBar) {
            const currentWidth = parseFloat(progressBar.style.width) || 0;
            const newWidth = Math.min(100, Math.max(0, percentage));
            
            // Only update if there's a significant change
            if (Math.abs(currentWidth - newWidth) > 0.5) {
                progressBar.style.transition = 'width 0.8s ease, background-color 0.3s ease';
                progressBar.style.width = `${newWidth}%`;
                
                // Update color based on usage level
                const colorClass = getProgressColor(newWidth);
                if (!progressBar.classList.contains(colorClass)) {
                    progressBar.className = `progress-fill ${colorClass}`;
                }
            }
        }

        if (metricText && metricType === 'cpu') {
            const newText = `${percentage.toFixed(1)}%`;
            if (metricText.textContent !== newText) {
                metricText.textContent = newText;
            }
        }
    }

    /**
     * Start real-time monitoring
     */
    startMonitoring() {
        if (!this.currentNodeId || !metricsMonitor) return;

        // Start monitoring all resources for this node
        metricsMonitor.startNodeResourcesMonitoring(this.currentNodeId, {
            interval: this.refreshInterval,
            callback: (data) => this.handleResourcesUpdate(data),
            silent: true // Enable silent updates to prevent page jumping
        });

        console.log(`Started real-time monitoring for node ${this.currentNodeId}`);
    }

    /**
     * Stop real-time monitoring
     */
    stopMonitoring() {
        if (!this.currentNodeId || !metricsMonitor) return;

        metricsMonitor.stopPoller(`node-resources-${this.currentNodeId}`);
        console.log(`Stopped real-time monitoring for node ${this.currentNodeId}`);
    }

    /**
     * Pause monitoring
     */
    pauseMonitoring() {
        if (!this.currentNodeId || !metricsMonitor) return;

        metricsMonitor.pausePoller(`node-resources-${this.currentNodeId}`);
    }

    /**
     * Resume monitoring
     */
    resumeMonitoring() {
        if (!this.currentNodeId || !metricsMonitor) return;

        metricsMonitor.resumePoller(`node-resources-${this.currentNodeId}`);
    }

    /**
     * Handle resources update from monitoring
     * @param {Array} data - Updated resources data
     */
    handleResourcesUpdate(data) {
        if (!Array.isArray(data)) return;

        // Update resources in map and UI silently
        data.forEach(resource => {
            this.resources.set(resource.vmid, resource);
            this.updateResourceCardSilently(resource.vmid, resource);
        });

        // Update stats silently
        this.updateResourcesStatsSilently(data);

        // Update last updated timestamp
        const lastUpdated = document.getElementById('resources-last-updated');
        if (lastUpdated) {
            lastUpdated.textContent = new Date().toLocaleTimeString();
        }
    }

    /**
     * Update resources statistics
     * @param {Array} resources - Resources array
     */
    updateResourcesStats(resources) {
        const totalElement = document.getElementById('total-resources');
        const runningElement = document.getElementById('running-resources');
        const stoppedElement = document.getElementById('stopped-resources');

        if (!totalElement || !runningElement || !stoppedElement) return;

        const total = resources.length;
        const running = resources.filter(r => r.status === 'running').length;
        const stopped = resources.filter(r => r.status === 'stopped').length;

        totalElement.textContent = total;
        runningElement.textContent = running;
        stoppedElement.textContent = stopped;
    }

    /**
     * Update resources statistics silently
     * @param {Array} resources - Resources array
     */
    updateResourcesStatsSilently(resources) {
        const totalElement = document.getElementById('total-resources');
        const runningElement = document.getElementById('running-resources');
        const stoppedElement = document.getElementById('stopped-resources');

        if (!totalElement || !runningElement || !stoppedElement) return;

        const total = resources.length;
        const running = resources.filter(r => r.status === 'running').length;
        const stopped = resources.filter(r => r.status === 'stopped').length;

        // Only update if values changed
        if (totalElement.textContent !== total.toString()) {
            totalElement.textContent = total;
        }
        if (runningElement.textContent !== running.toString()) {
            runningElement.textContent = running;
        }
        if (stoppedElement.textContent !== stopped.toString()) {
            stoppedElement.textContent = stopped;
        }
    }

    /**
     * Update resources statistics silently with subtle animations
     * @param {Array} resources - Resources array
     */
    updateResourcesStatsSilently(resources) {
        const totalElement = document.getElementById('total-resources');
        const runningElement = document.getElementById('running-resources');
        const stoppedElement = document.getElementById('stopped-resources');

        if (!totalElement || !runningElement || !stoppedElement) return;

        const total = resources.length;
        const running = resources.filter(r => r.status === 'running').length;
        const stopped = resources.filter(r => r.status === 'stopped').length;

        // Update with subtle highlight if values changed
        this.updateStatElementSilently(totalElement, total);
        this.updateStatElementSilently(runningElement, running);
        this.updateStatElementSilently(stoppedElement, stopped);
    }

    /**
     * Update a stat element silently with highlight if changed
     * @param {HTMLElement} element - Stat element
     * @param {number} newValue - New value
     */
    updateStatElementSilently(element, newValue) {
        const currentValue = parseInt(element.textContent) || 0;
        if (currentValue !== newValue) {
            element.style.transition = 'color 0.3s ease, transform 0.2s ease';
            element.textContent = newValue;
            element.style.color = 'var(--primary-orange)';
            element.style.transform = 'scale(1.05)';
            
            setTimeout(() => {
                element.style.color = '';
                element.style.transform = 'scale(1)';
            }, 600);
        }
    }

    /**
     * Refresh all resources
     */
    async refreshResources() {
        const refreshBtn = document.querySelector('.refresh-resources-btn');
        if (refreshBtn) {
            const icon = refreshBtn.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
            }
            refreshBtn.disabled = true;
        }

        try {
            // Use silent refresh to avoid page jumping and loading states
            await this.refreshResourcesSilently();
            
            // Show subtle success indication
            if (refreshBtn) {
                refreshBtn.style.background = 'linear-gradient(135deg, var(--success-color), #45a049)';
                setTimeout(() => {
                    refreshBtn.style.background = '';
                }, 1000);
            }
            
        } catch (error) {
            console.error('Manual refresh failed:', error);
            showNotification('Failed to refresh resources', 'error', 3000);
        } finally {
            if (refreshBtn) {
                const icon = refreshBtn.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-spin');
                }
                refreshBtn.disabled = false;
            }
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const loading = document.getElementById('resources-loading');
        const grid = document.getElementById('resources-grid');
        const empty = document.getElementById('resources-empty');
        const error = document.getElementById('resources-error');

        if (loading) loading.style.display = 'flex';
        if (grid) grid.style.display = 'none';
        if (empty) empty.style.display = 'none';
        if (error) error.style.display = 'none';
    }

    /**
     * Show resources grid
     */
    showResourcesGrid() {
        const loading = document.getElementById('resources-loading');
        const grid = document.getElementById('resources-grid');
        const empty = document.getElementById('resources-empty');
        const error = document.getElementById('resources-error');

        if (loading) loading.style.display = 'none';
        if (grid) grid.style.display = 'grid';
        if (empty) empty.style.display = 'none';
        if (error) error.style.display = 'none';
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        const loading = document.getElementById('resources-loading');
        const grid = document.getElementById('resources-grid');
        const empty = document.getElementById('resources-empty');
        const error = document.getElementById('resources-error');

        if (loading) loading.style.display = 'none';
        if (grid) grid.style.display = 'none';
        if (empty) empty.style.display = 'flex';
        if (error) error.style.display = 'none';
    }

    /**
     * Show error state
     * @param {string} message - Error message
     */
    showErrorState(message) {
        const loading = document.getElementById('resources-loading');
        const grid = document.getElementById('resources-grid');
        const empty = document.getElementById('resources-empty');
        const error = document.getElementById('resources-error');
        const errorMessage = document.getElementById('resources-error-message');

        if (loading) loading.style.display = 'none';
        if (grid) grid.style.display = 'none';
        if (empty) empty.style.display = 'none';
        if (error) error.style.display = 'flex';
        if (errorMessage) errorMessage.textContent = message;
    }

    /**
     * Get status CSS class
     * @param {string} status - Resource status
     * @returns {string} CSS class
     */
    getStatusClass(status) {
        const statusClasses = {
            running: 'status-running',
            stopped: 'status-stopped',
            paused: 'status-paused',
            suspended: 'status-suspended',
            error: 'status-error'
        };
        return statusClasses[status] || 'status-unknown';
    }

    /**
     * Calculate percentage
     * @param {number} used - Used value
     * @param {number} total - Total value
     * @returns {number} Percentage
     */
    calculatePercentage(used, total) {
        if (!total || total === 0) return 0;
        return (used / total) * 100;
    }

    /**
     * Format memory display
     * @param {number} used - Used memory
     * @param {number} total - Total memory
     * @returns {string} Formatted string
     */
    formatMemory(used, total) {
        if (!total) return 'N/A';
        const percentage = this.calculatePercentage(used, total);
        return `${formatBytes(used)} / ${formatBytes(total)} (${percentage.toFixed(1)}%)`;
    }

    /**
     * Format disk display
     * @param {number} used - Used disk
     * @param {number} total - Total disk
     * @returns {string} Formatted string
     */
    formatDisk(used, total) {
        if (!total) return 'N/A';
        const percentage = this.calculatePercentage(used, total);
        return `${formatBytes(used)} / ${formatBytes(total)} (${percentage.toFixed(1)}%)`;
    }
}

// Create global instance
const enhancedResourceManager = new EnhancedResourceManager();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        EnhancedResourceManager,
        enhancedResourceManager
    };
}

// Make available globally
window.EnhancedResourceManager = EnhancedResourceManager;
window.enhancedResourceManager = enhancedResourceManager;