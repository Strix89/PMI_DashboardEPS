/**
 * VM/LXC Resource Management JavaScript
 * 
 * This module handles the VM and LXC container management interface,
 * including real-time metrics updates, control operations, and UI interactions.
 */

class ResourceManager {
    constructor() {
        this.currentNodeId = null;
        this.currentNodeName = null;
        this.refreshInterval = null;
        this.refreshIntervalMs = 10000; // 10 seconds
        this.isAutoRefreshEnabled = true;
        this.resources = { vms: [], containers: [] };
        
        this.initializeEventListeners();
    }

    /**
     * Initialize event listeners for the resource management interface
     */
    initializeEventListeners() {
        // Back to nodes button
        const backBtn = document.getElementById('back-to-nodes-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.hideResourcesSection());
        }

        // Refresh resources button
        const refreshBtn = document.getElementById('refresh-resources-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshResources());
        }

        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-resources-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.isAutoRefreshEnabled = e.target.checked;
                if (this.isAutoRefreshEnabled) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // Retry resources button
        const retryBtn = document.getElementById('retry-resources-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.loadResources());
        }

        // Modal event listeners
        this.initializeModalEventListeners();
    }

    /**
     * Initialize modal event listeners
     */
    initializeModalEventListeners() {
        const modal = document.getElementById('operation-modal');
        if (!modal) return;

        // Close modal buttons
        const closeButtons = modal.querySelectorAll('.btn-close, .cancel-operation');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.hideOperationModal());
        });

        // Confirm operation button
        const confirmBtn = modal.querySelector('.confirm-operation');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmOperation());
        }

        // Close modal on backdrop click
        const backdrop = modal.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', () => this.hideOperationModal());
        }
    }

    /**
     * Show resources section for a specific node
     * @param {string} nodeId - Node ID
     * @param {string} nodeName - Node display name
     */
    showResourcesSection(nodeId, nodeName) {
        this.currentNodeId = nodeId;
        this.currentNodeName = nodeName;

        // Update section title
        const titleElement = document.getElementById('resources-node-name');
        if (titleElement) {
            titleElement.textContent = `${nodeName} Resources`;
        }

        // Hide node configuration and show resources section
        const nodeConfigSection = document.querySelector('.node-config-section');
        const resourcesSection = document.getElementById('resources-section');
        
        if (nodeConfigSection) {
            nodeConfigSection.style.display = 'none';
        }
        
        if (resourcesSection) {
            resourcesSection.style.display = 'block';
        }

        // Load resources
        this.loadResources();
        
        // Start auto-refresh if enabled
        if (this.isAutoRefreshEnabled) {
            this.startAutoRefresh();
        }
    }

    /**
     * Hide resources section and return to node configuration
     */
    hideResourcesSection() {
        // Stop auto-refresh
        this.stopAutoRefresh();

        // Show node configuration and hide resources section
        const nodeConfigSection = document.querySelector('.node-config-section');
        const resourcesSection = document.getElementById('resources-section');
        
        if (nodeConfigSection) {
            nodeConfigSection.style.display = 'block';
        }
        
        if (resourcesSection) {
            resourcesSection.style.display = 'none';
        }

        // Clear current node
        this.currentNodeId = null;
        this.currentNodeName = null;
        this.resources = { vms: [], containers: [] };
    }

    /**
     * Load resources for the current node
     */
    async loadResources(silent = false) {
        if (!this.currentNodeId) return;

        if (!silent) {
            this.showLoadingState();
        } else {
            this.showRefreshIndicator(true);
        }

        try {
            const response = await proxmoxAPI.getNodeResources(this.currentNodeId);
            
            if (response.success) {
                this.resources = response.data;
                this.renderResources();
                if (!silent) {
                    this.hideLoadingState();
                } else {
                    this.showRefreshIndicator(false);
                }
            } else {
                throw new Error(response.error || 'Failed to load resources');
            }
        } catch (error) {
            console.error('Failed to load resources:', error);
            if (!silent) {
                this.showEmptyState();
                showNotification(`Failed to load resources: ${error.message}`, 'error');
            } else {
                this.showRefreshIndicator(false);
            }
        }
    }

    /**
     * Refresh resources data
     */
    async refreshResources() {
        if (!this.currentNodeId) return;

        const refreshBtn = document.getElementById('refresh-resources-btn');
        if (refreshBtn) {
            const icon = refreshBtn.querySelector('i');
            if (icon) {
                icon.classList.add('fa-spin');
            }
        }

        try {
            await this.loadResources();
        } finally {
            if (refreshBtn) {
                const icon = refreshBtn.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-spin');
                }
            }
        }
    }

    /**
     * Refresh resources silently without showing loading state
     */
    async refreshResourcesSilently() {
        if (!this.currentNodeId) return;

        // Show refresh indicator
        this.showRefreshIndicator(true);

        try {
            const response = await proxmoxAPI.getNodeResources(this.currentNodeId);
            
            if (response.success) {
                // Update resources data without showing loading state
                this.resources = response.data;
                this.updateResourcesInPlace();
                this.markResourcesAsOnline();
            } else {
                console.warn('Silent refresh failed:', response.error);
                // Mark resources as offline if connection failed
                this.markResourcesAsOffline(response.error);
            }
        } catch (error) {
            console.warn('Silent refresh error:', error.message);
            // Mark resources as offline if connection failed
            this.markResourcesAsOffline(error.message);
        } finally {
            // Hide refresh indicator
            this.showRefreshIndicator(false);
        }
    }

    /**
     * Mark all resource cards as online
     */
    markResourcesAsOnline() {
        const resourceCards = document.querySelectorAll('.resource-card');
        resourceCards.forEach(card => {
            card.classList.remove('resource-offline');
            card.classList.add('resource-online');
            
            // Re-enable control buttons
            const buttons = card.querySelectorAll('.start-btn, .stop-btn, .restart-btn');
            buttons.forEach(btn => {
                btn.classList.remove('btn-disabled');
            });
        });
    }

    /**
     * Mark all resource cards as offline
     */
    markResourcesAsOffline(errorMessage) {
        const resourceCards = document.querySelectorAll('.resource-card');
        resourceCards.forEach(card => {
            card.classList.remove('resource-online');
            card.classList.add('resource-offline');
            
            // Disable control buttons
            const buttons = card.querySelectorAll('.start-btn, .stop-btn, .restart-btn');
            buttons.forEach(btn => {
                btn.classList.add('btn-disabled');
                btn.disabled = true;
            });

            // Update status badge to show offline
            const statusBadge = card.querySelector('.resource-status-badge');
            if (statusBadge) {
                statusBadge.textContent = 'Offline';
                statusBadge.className = 'resource-status-badge offline';
            }

            // Update connection info
            const updateTime = card.querySelector('.update-time');
            if (updateTime) {
                updateTime.textContent = 'Connection Lost';
                updateTime.style.color = 'var(--danger-color)';
            }
        });

        // Show notification about connection loss
        if (typeof showNotification === 'function') {
            showNotification(`Node connection lost: ${errorMessage}`, 'warning', 5000);
        }
    }

    /**
     * Update resources in place without clearing the container
     */
    updateResourcesInPlace() {
        this.updateVMsInPlace();
        this.updateContainersInPlace();
        this.updateResourceCounts();
    }

    /**
     * Update VMs in place without clearing container
     */
    updateVMsInPlace() {
        const container = document.getElementById('vms-container');
        if (!container) return;

        const existingCards = container.querySelectorAll('.resource-card[data-resource-type="vm"]');
        const existingVmids = new Set();

        // Update existing VM cards
        existingCards.forEach(card => {
            const vmid = parseInt(card.getAttribute('data-vmid'));
            existingVmids.add(vmid);
            
            const vmData = this.resources.vms?.find(vm => vm.vmid === vmid);
            if (vmData) {
                this.updateResourceCardInPlace(card, vmData);
            } else {
                // VM was removed, remove the card with animation
                this.removeResourceCardAnimated(card);
            }
        });

        // Add new VMs that don't exist yet
        if (this.resources.vms) {
            this.resources.vms.forEach(vm => {
                if (!existingVmids.has(vm.vmid)) {
                    const card = this.createResourceCard(vm, 'vm');
                    this.addResourceCardAnimated(container, card);
                }
            });
        }
    }

    /**
     * Update containers in place without clearing container
     */
    updateContainersInPlace() {
        const container = document.getElementById('lxc-container');
        if (!container) return;

        const existingCards = container.querySelectorAll('.resource-card[data-resource-type="lxc"]');
        const existingVmids = new Set();

        // Update existing container cards
        existingCards.forEach(card => {
            const vmid = parseInt(card.getAttribute('data-vmid'));
            existingVmids.add(vmid);
            
            const lxcData = this.resources.containers?.find(lxc => lxc.vmid === vmid);
            if (lxcData) {
                this.updateResourceCardInPlace(card, lxcData);
            } else {
                // Container was removed, remove the card with animation
                this.removeResourceCardAnimated(card);
            }
        });

        // Add new containers that don't exist yet
        if (this.resources.containers) {
            this.resources.containers.forEach(lxc => {
                if (!existingVmids.has(lxc.vmid)) {
                    const card = this.createResourceCard(lxc, 'lxc');
                    this.addResourceCardAnimated(container, card);
                }
            });
        }
    }

    /**
     * Update a resource card in place with new data
     */
    updateResourceCardInPlace(card, resource) {
        // Update status badge with animation
        const statusBadge = card.querySelector('.resource-status-badge');
        if (statusBadge) {
            const currentStatus = statusBadge.textContent.toLowerCase();
            const newStatus = resource.status || 'unknown';
            
            if (currentStatus !== newStatus) {
                statusBadge.style.transition = 'all 0.3s ease';
                statusBadge.textContent = newStatus;
                statusBadge.className = `resource-status-badge ${newStatus}`;
            }
        }

        // Update metrics with smooth animations
        this.updateResourceMetricsAnimated(card, resource);

        // Update control buttons state
        this.updateResourceControlsState(card, resource);

        // Update last updated time
        const updateTime = card.querySelector('.update-time');
        if (updateTime) {
            const lastUpdated = resource.last_updated ? new Date(resource.last_updated) : new Date();
            const newTime = lastUpdated.toLocaleTimeString();
            if (updateTime.textContent !== newTime) {
                updateTime.textContent = newTime;
                // Brief highlight to show update
                updateTime.style.transition = 'color 0.3s ease';
                updateTime.style.color = 'var(--primary-orange)';
                setTimeout(() => {
                    updateTime.style.color = '';
                }, 1000);
            }
        }
    }

    /**
     * Update resource metrics with smooth animations
     */
    updateResourceMetricsAnimated(card, resource) {
        // CPU usage
        const cpuProgress = card.querySelector('.cpu-progress');
        const cpuUsage = card.querySelector('.cpu-usage');
        if (cpuProgress && cpuUsage) {
            const cpuPercent = resource.cpu_usage || 0;
            const currentWidth = parseFloat(cpuProgress.style.width) || 0;
            
            if (Math.abs(currentWidth - cpuPercent) > 0.1) {
                cpuProgress.style.transition = 'width 0.5s ease';
                cpuProgress.style.width = `${cpuPercent}%`;
                cpuProgress.setAttribute('aria-valuenow', cpuPercent);
                cpuUsage.textContent = `${cpuPercent.toFixed(1)}%`;
            }
        }

        // Memory usage
        const memoryProgress = card.querySelector('.memory-progress');
        const memoryUsage = card.querySelector('.memory-usage');
        if (memoryProgress && memoryUsage) {
            const memoryPercent = resource.memory_percentage || 0;
            const currentWidth = parseFloat(memoryProgress.style.width) || 0;
            
            if (Math.abs(currentWidth - memoryPercent) > 0.1) {
                memoryProgress.style.transition = 'width 0.5s ease';
                memoryProgress.style.width = `${memoryPercent}%`;
                memoryProgress.setAttribute('aria-valuenow', memoryPercent);
                memoryUsage.textContent = `${memoryPercent.toFixed(1)}%`;
            }
        }

        // Disk usage
        const diskProgress = card.querySelector('.disk-progress');
        const diskUsage = card.querySelector('.disk-usage');
        if (diskProgress && diskUsage) {
            const diskPercent = resource.disk_percentage || 0;
            const currentWidth = parseFloat(diskProgress.style.width) || 0;
            
            if (Math.abs(currentWidth - diskPercent) > 0.1) {
                diskProgress.style.transition = 'width 0.5s ease';
                diskProgress.style.width = `${diskPercent}%`;
                diskProgress.setAttribute('aria-valuenow', diskPercent);
                diskUsage.textContent = `${diskPercent.toFixed(1)}%`;
            }
        }

        // Network I/O
        const networkIn = card.querySelector('.network-in');
        const networkOut = card.querySelector('.network-out');
        if (networkIn && resource.network_in !== undefined) {
            const newValue = formatBytes(resource.network_in || 0);
            if (networkIn.textContent !== newValue) {
                networkIn.textContent = newValue;
            }
        }
        if (networkOut && resource.network_out !== undefined) {
            const newValue = formatBytes(resource.network_out || 0);
            if (networkOut.textContent !== newValue) {
                networkOut.textContent = newValue;
            }
        }

        // Status and uptime
        const resourceStatus = card.querySelector('.resource-status');
        const resourceUptime = card.querySelector('.resource-uptime');
        if (resourceStatus) {
            const status = resource.status || 'unknown';
            const statusText = status.charAt(0).toUpperCase() + status.slice(1);
            if (resourceStatus.textContent !== statusText) {
                resourceStatus.textContent = statusText;
                resourceStatus.className = `status-value resource-status ${status}`;
            }
        }
        if (resourceUptime) {
            const uptimeText = formatUptime(resource.uptime || 0);
            if (resourceUptime.textContent !== uptimeText) {
                resourceUptime.textContent = uptimeText;
            }
        }
    }

    /**
     * Update resource control buttons state
     */
    updateResourceControlsState(card, resource) {
        const startBtn = card.querySelector('.start-btn');
        const stopBtn = card.querySelector('.stop-btn');
        const restartBtn = card.querySelector('.restart-btn');

        const isRunning = resource.status === 'running';
        const isStopped = resource.status === 'stopped';
        const isOffline = resource.status === 'offline' || resource.error || !this.isNodeConnected();

        if (startBtn) {
            startBtn.disabled = isRunning || isOffline;
            if (isOffline) {
                startBtn.classList.add('btn-disabled');
                startBtn.title = 'Node is offline - resource not available';
            } else {
                startBtn.classList.remove('btn-disabled');
                startBtn.title = isRunning ? 'Already running' : 'Start resource';
            }
        }
        
        if (stopBtn) {
            stopBtn.disabled = isStopped || isOffline;
            if (isOffline) {
                stopBtn.classList.add('btn-disabled');
                stopBtn.title = 'Node is offline - resource not available';
            } else {
                stopBtn.classList.remove('btn-disabled');
                stopBtn.title = isStopped ? 'Already stopped' : 'Stop resource';
            }
        }
        
        if (restartBtn) {
            restartBtn.disabled = isStopped || isOffline;
            if (isOffline) {
                restartBtn.classList.add('btn-disabled');
                restartBtn.title = 'Node is offline - resource not available';
            } else {
                restartBtn.classList.remove('btn-disabled');
                restartBtn.title = isStopped ? 'Cannot restart stopped resource' : 'Restart resource';
            }
        }
    }

    /**
     * Add a new resource card with animation
     */
    addResourceCardAnimated(container, card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        container.appendChild(card);
        
        requestAnimationFrame(() => {
            card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        });
    }

    /**
     * Remove a resource card with animation
     */
    removeResourceCardAnimated(card) {
        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        card.style.opacity = '0';
        card.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            if (card.parentNode) {
                card.parentNode.removeChild(card);
            }
        }, 300);
    }

    /**
     * Start auto-refresh interval
     */
    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear any existing interval
        
        if (this.isAutoRefreshEnabled && this.currentNodeId) {
            this.refreshInterval = setInterval(() => {
                // Use silent refresh to avoid loading states and page jumping
                this.refreshResourcesSilently();
            }, this.refreshIntervalMs);
        }
    }

    /**
     * Stop auto-refresh interval
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const loadingElement = document.getElementById('resources-loading');
        const containerElement = document.getElementById('resources-container');
        const emptyStateElement = document.getElementById('resources-empty-state');

        if (loadingElement) loadingElement.style.display = 'block';
        if (containerElement) containerElement.style.display = 'none';
        if (emptyStateElement) emptyStateElement.style.display = 'none';
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const loadingElement = document.getElementById('resources-loading');
        const containerElement = document.getElementById('resources-container');

        if (loadingElement) loadingElement.style.display = 'none';
        if (containerElement) containerElement.style.display = 'block';
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        const loadingElement = document.getElementById('resources-loading');
        const containerElement = document.getElementById('resources-container');
        const emptyStateElement = document.getElementById('resources-empty-state');

        if (loadingElement) loadingElement.style.display = 'none';
        if (containerElement) containerElement.style.display = 'none';
        if (emptyStateElement) emptyStateElement.style.display = 'block';
    }

    /**
     * Render resources in the UI
     */
    renderResources() {
        this.renderVMs();
        this.renderContainers();
        this.updateResourceCounts();
    }

    /**
     * Render VMs
     */
    renderVMs() {
        const container = document.getElementById('vms-container');
        if (!container) return;

        container.innerHTML = '';

        if (this.resources.vms && this.resources.vms.length > 0) {
            this.resources.vms.forEach(vm => {
                const card = this.createResourceCard(vm, 'vm');
                container.appendChild(card);
            });
        }
    }

    /**
     * Render LXC containers
     */
    renderContainers() {
        const container = document.getElementById('lxc-container');
        if (!container) return;

        container.innerHTML = '';

        if (this.resources.containers && this.resources.containers.length > 0) {
            this.resources.containers.forEach(lxc => {
                const card = this.createResourceCard(lxc, 'lxc');
                container.appendChild(card);
            });
        }
    }

    /**
     * Create a resource card element
     * @param {Object} resource - Resource data
     * @param {string} type - Resource type ('vm' or 'lxc')
     * @returns {HTMLElement} Resource card element
     */
    createResourceCard(resource, type) {
        const template = document.getElementById('resource-card-template');
        if (!template) return null;

        const card = template.content.cloneNode(true);
        const cardElement = card.querySelector('.resource-card');

        // Set data attributes
        cardElement.setAttribute('data-vmid', resource.vmid);
        cardElement.setAttribute('data-resource-type', type);

        // Set resource icon
        const icon = card.querySelector('.resource-icon');
        if (icon) {
            icon.className = `resource-icon fas ${type === 'vm' ? 'fa-desktop' : 'fa-cube'}`;
        }

        // Set resource name and details
        const nameText = card.querySelector('.name-text');
        if (nameText) {
            nameText.textContent = resource.name || `${type.toUpperCase()}-${resource.vmid}`;
        }

        const resourceId = card.querySelector('.resource-id');
        if (resourceId) {
            resourceId.textContent = `ID: ${resource.vmid}`;
        }

        // Set status badge
        const statusBadge = card.querySelector('.resource-status-badge');
        if (statusBadge) {
            const status = resource.status || 'unknown';
            statusBadge.textContent = status;
            statusBadge.className = `resource-status-badge ${status}`;
        }

        // Update metrics
        this.updateResourceMetrics(card, resource);

        // Set up control buttons
        this.setupResourceControls(card, resource, type);

        return cardElement;
    }

    /**
     * Update resource metrics in the card
     * @param {HTMLElement} card - Card element
     * @param {Object} resource - Resource data
     */
    updateResourceMetrics(card, resource) {
        // CPU usage
        const cpuProgress = card.querySelector('.cpu-progress');
        const cpuUsage = card.querySelector('.cpu-usage');
        if (cpuProgress && cpuUsage) {
            const cpuPercent = resource.cpu_usage || 0;
            cpuProgress.style.width = `${cpuPercent}%`;
            cpuProgress.setAttribute('aria-valuenow', cpuPercent);
            cpuUsage.textContent = `${cpuPercent.toFixed(1)}%`;
        }

        // Memory usage
        const memoryProgress = card.querySelector('.memory-progress');
        const memoryUsage = card.querySelector('.memory-usage');
        if (memoryProgress && memoryUsage) {
            const memoryPercent = resource.memory_percentage || 0;
            memoryProgress.style.width = `${memoryPercent}%`;
            memoryProgress.setAttribute('aria-valuenow', memoryPercent);
            memoryUsage.textContent = `${memoryPercent.toFixed(1)}%`;
        }

        // Disk usage
        const diskProgress = card.querySelector('.disk-progress');
        const diskUsage = card.querySelector('.disk-usage');
        if (diskProgress && diskUsage) {
            const diskPercent = resource.disk_percentage || 0;
            diskProgress.style.width = `${diskPercent}%`;
            diskProgress.setAttribute('aria-valuenow', diskPercent);
            diskUsage.textContent = `${diskPercent.toFixed(1)}%`;
        }

        // Network I/O
        const networkIn = card.querySelector('.network-in');
        const networkOut = card.querySelector('.network-out');
        if (networkIn) {
            networkIn.textContent = formatBytes(resource.network_in || 0);
        }
        if (networkOut) {
            networkOut.textContent = formatBytes(resource.network_out || 0);
        }

        // Status and uptime
        const resourceStatus = card.querySelector('.resource-status');
        const resourceUptime = card.querySelector('.resource-uptime');
        if (resourceStatus) {
            const status = resource.status || 'unknown';
            resourceStatus.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            resourceStatus.className = `status-value resource-status ${status}`;
        }
        if (resourceUptime) {
            resourceUptime.textContent = formatUptime(resource.uptime || 0);
        }

        // Last updated
        const updateTime = card.querySelector('.update-time');
        if (updateTime) {
            const lastUpdated = resource.last_updated ? new Date(resource.last_updated) : new Date();
            updateTime.textContent = lastUpdated.toLocaleTimeString();
        }
    }

    /**
     * Set up resource control buttons
     * @param {HTMLElement} card - Card element
     * @param {Object} resource - Resource data
     * @param {string} type - Resource type
     */
    setupResourceControls(card, resource, type) {
        const startBtn = card.querySelector('.start-btn');
        const stopBtn = card.querySelector('.stop-btn');
        const restartBtn = card.querySelector('.restart-btn');

        const isRunning = resource.status === 'running';
        const isStopped = resource.status === 'stopped';
        const isOffline = resource.status === 'offline' || resource.error;

        // Enable/disable buttons based on status and connection
        if (startBtn) {
            startBtn.disabled = isRunning || isOffline;
            if (isOffline) {
                startBtn.classList.add('btn-disabled');
                startBtn.title = 'Node is offline - resource not available';
            } else {
                startBtn.classList.remove('btn-disabled');
                startBtn.title = isRunning ? 'Already running' : 'Start resource';
            }
            startBtn.addEventListener('click', () => {
                if (!startBtn.disabled && !isOffline) {
                    this.showOperationModal(resource, type, 'start');
                }
            });
        }

        if (stopBtn) {
            stopBtn.disabled = isStopped || isOffline;
            if (isOffline) {
                stopBtn.classList.add('btn-disabled');
                stopBtn.title = 'Node is offline - resource not available';
            } else {
                stopBtn.classList.remove('btn-disabled');
                stopBtn.title = isStopped ? 'Already stopped' : 'Stop resource';
            }
            stopBtn.addEventListener('click', () => {
                if (!stopBtn.disabled && !isOffline) {
                    this.showOperationModal(resource, type, 'stop');
                }
            });
        }

        if (restartBtn) {
            restartBtn.disabled = isStopped || isOffline;
            if (isOffline) {
                restartBtn.classList.add('btn-disabled');
                restartBtn.title = 'Node is offline - resource not available';
            } else {
                restartBtn.classList.remove('btn-disabled');
                restartBtn.title = isStopped ? 'Cannot restart stopped resource' : 'Restart resource';
            }
            restartBtn.addEventListener('click', () => {
                if (!restartBtn.disabled && !isOffline) {
                    this.showOperationModal(resource, type, 'restart');
                }
            });
        }
    }

    /**
     * Update resource count badges
     */
    updateResourceCounts() {
        const vmCountBadge = document.getElementById('vm-count-badge');
        const lxcCountBadge = document.getElementById('lxc-count-badge');

        if (vmCountBadge) {
            vmCountBadge.textContent = this.resources.vms ? this.resources.vms.length : 0;
        }

        if (lxcCountBadge) {
            lxcCountBadge.textContent = this.resources.containers ? this.resources.containers.length : 0;
        }
    }

    /**
     * Check if the current node is connected
     * @returns {boolean} True if node is connected
     */
    isNodeConnected() {
        // Check if we have a valid node ID and if the node dashboard indicates it's connected
        if (!this.currentNodeId) return false;
        
        // Try to get node status from the node dashboard
        if (window.nodeDashboard && window.nodeDashboard.nodes) {
            const nodeData = window.nodeDashboard.nodes.get(this.currentNodeId);
            return nodeData && nodeData.is_connected;
        }
        
        // Fallback: check if we can load resources (if we got here, likely connected)
        return true;
    }

    /**
     * Show operation confirmation modal
     * @param {Object} resource - Resource data
     * @param {string} type - Resource type
     * @param {string} operation - Operation type
     */
    showOperationModal(resource, type, operation) {
        const modal = document.getElementById('operation-modal');
        if (!modal) return;

        // Store operation details
        this.pendingOperation = {
            resource,
            type,
            operation,
            vmid: resource.vmid
        };

        // Update modal content
        const resourceName = document.getElementById('modal-resource-name');
        const operationSpan = document.getElementById('modal-operation');
        const forceOption = modal.querySelector('.force-option');
        const operationIcon = modal.querySelector('.operation-icon i');

        if (resourceName) {
            resourceName.textContent = `${type.toUpperCase()}-${resource.vmid}: ${resource.name}`;
        }

        if (operationSpan) {
            operationSpan.textContent = operation.charAt(0).toUpperCase() + operation.slice(1);
        }

        // Show/hide force option for stop and restart operations
        if (forceOption) {
            forceOption.style.display = (operation === 'stop' || operation === 'restart') ? 'block' : 'none';
        }

        // Update icon based on operation
        if (operationIcon) {
            const iconClass = {
                'start': 'fa-play text-success',
                'stop': 'fa-stop text-warning',
                'restart': 'fa-redo text-info'
            }[operation] || 'fa-question-circle';
            
            operationIcon.className = `fas ${iconClass}`;
        }

        // Show modal
        modal.style.display = 'flex';
    }

    /**
     * Hide operation confirmation modal
     */
    hideOperationModal() {
        const modal = document.getElementById('operation-modal');
        if (modal) {
            modal.style.display = 'none';
        }

        // Clear pending operation
        this.pendingOperation = null;

        // Reset force checkbox
        const forceCheckbox = document.getElementById('force-operation');
        if (forceCheckbox) {
            forceCheckbox.checked = false;
        }
    }

    /**
     * Confirm and execute the pending operation
     */
    async confirmOperation() {
        if (!this.pendingOperation) return;

        const { resource, type, operation, vmid } = this.pendingOperation;
        const forceCheckbox = document.getElementById('force-operation');
        const force = forceCheckbox ? forceCheckbox.checked : false;

        // Hide modal
        this.hideOperationModal();

        // Show loading overlay on the resource card
        this.showResourceLoading(vmid, `${operation}ing...`);

        try {
            let response;
            
            switch (operation) {
                case 'start':
                    response = await proxmoxAPI.startResource(this.currentNodeId, vmid);
                    break;
                case 'stop':
                    response = await proxmoxAPI.stopResource(this.currentNodeId, vmid, force);
                    break;
                case 'restart':
                    response = await proxmoxAPI.restartResource(this.currentNodeId, vmid, force);
                    break;
                default:
                    throw new Error(`Unknown operation: ${operation}`);
            }

            if (response.success) {
                showNotification(
                    `Successfully ${operation}ed ${type.toUpperCase()}-${vmid}`,
                    'success'
                );
                
                // Refresh resources after a short delay to allow the operation to take effect
                setTimeout(() => {
                    this.refreshResourcesSilently();
                }, 2000);
            } else {
                throw new Error(response.error || `Failed to ${operation} resource`);
            }
        } catch (error) {
            console.error(`Failed to ${operation} resource:`, error);
            showNotification(
                `Failed to ${operation} ${type.toUpperCase()}-${vmid}: ${error.message}`,
                'error'
            );
        } finally {
            this.hideResourceLoading(vmid);
        }
    }

    /**
     * Show loading overlay on a specific resource card
     * @param {number} vmid - VM/Container ID
     * @param {string} message - Loading message
     */
    showResourceLoading(vmid, message = 'Processing...') {
        const card = document.querySelector(`[data-vmid="${vmid}"]`);
        if (!card) return;

        const overlay = card.querySelector('.resource-loading-overlay');
        const loadingText = card.querySelector('.loading-text');
        
        if (overlay) {
            overlay.style.display = 'flex';
        }
        
        if (loadingText) {
            loadingText.textContent = message;
        }
    }

    /**
     * Hide loading overlay on a specific resource card
     * @param {number} vmid - VM/Container ID
     */
    hideResourceLoading(vmid) {
        const card = document.querySelector(`[data-vmid="${vmid}"]`);
        if (!card) return;

        const overlay = card.querySelector('.resource-loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    /**
     * Show/hide refresh indicator
     */
    showRefreshIndicator(show) {
        const indicator = document.getElementById('refresh-resources-indicator');
        if (indicator) {
            if (show) {
                indicator.style.display = 'flex';
                indicator.classList.add('show');
            } else {
                indicator.classList.remove('show');
                // Hide after transition
                setTimeout(() => {
                    if (!indicator.classList.contains('show')) {
                        indicator.style.display = 'none';
                    }
                }, 300);
            }
        }
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ResourceManager
    };
}

// Create global instance only if ResourceManager doesn't exist
if (typeof window !== 'undefined' && !window.resourceManager) {
    window.resourceManager = new ResourceManager();
}