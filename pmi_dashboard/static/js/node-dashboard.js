/**
 * Node Dashboard Management
 * 
 * This module handles the display and real-time updates of Proxmox node dashboard cards.
 * It provides functionality for loading nodes, displaying metrics, and managing real-time updates.
 */

class NodeDashboard {
    constructor() {
        this.nodes = new Map();
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.refreshIntervalMs = 10000; // 10 seconds
        this.isLoading = false;
        
        this.init();
    }

    /**
     * Initialize the node dashboard
     */
    init() {
        this.bindEvents();
        this.loadNodes();
        this.startAutoRefresh();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-nodes-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshNodes());
        }

        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.autoRefreshEnabled = e.target.checked;
                if (this.autoRefreshEnabled) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // Listen for tab changes to pause/resume updates
        document.addEventListener('tabchange', (e) => {
            if (e.detail.tab === 'proxmox') {
                if (this.autoRefreshEnabled) {
                    this.startAutoRefresh();
                }
            } else {
                this.stopAutoRefresh();
            }
        });
    }

    /**
     * Load all nodes from the API (initial load)
     */
    async loadNodes(silent = false) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        
        // Show appropriate loading indicators
        if (!silent) {
            this.showLoading();
        } else {
            this.showRefreshIndicator(true);
        }

        try {
            const response = await proxmoxAPI.getNodes();
            
            if (response.success) {
                if (silent) {
                    this.updateNodesDataSilently(response.data);
                } else {
                    this.updateNodesDisplay(response.data);
                }
            } else {
                if (!silent) {
                    this.showError('Failed to load nodes: ' + (response.error || 'Unknown error'));
                } else {
                    console.warn('Silent refresh failed:', response.error);
                }
            }
        } catch (error) {
            console.error('Failed to load nodes:', error);
            if (!silent) {
                this.showError('Failed to load nodes: ' + error.message);
            }
        } finally {
            this.isLoading = false;
            if (silent) {
                this.showRefreshIndicator(false);
            }
        }
    }

    /**
     * Refresh nodes data (manual refresh)
     */
    async refreshNodes() {
        const refreshBtn = document.getElementById('refresh-nodes-btn');
        const originalContent = refreshBtn?.innerHTML;
        
        if (refreshBtn) {
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
            refreshBtn.disabled = true;
        }

        try {
            // Use silent refresh to avoid page jumping
            await this.loadNodes(true);
            
            // Show success notification
            showNotification('Nodes refreshed successfully', 'success', 2000);
        } catch (error) {
            showNotification('Failed to refresh nodes: ' + error.message, 'error');
        } finally {
            if (refreshBtn) {
                refreshBtn.innerHTML = originalContent;
                refreshBtn.disabled = false;
            }
        }
    }

    /**
     * Update nodes data silently without affecting page layout or scroll position
     * @param {Array} nodesData - Array of node data
     */
    updateNodesDataSilently(nodesData) {
        const container = document.getElementById('nodes-container');
        const emptyState = document.getElementById('nodes-empty-state');
        
        if (!container) return;

        // If no nodes exist and we have data, do a full update
        if (container.children.length === 0 || container.querySelector('.loading-placeholder') || container.querySelector('.error-placeholder')) {
            this.updateNodesDisplay(nodesData);
            return;
        }

        // Handle empty state
        if (!nodesData || nodesData.length === 0) {
            container.style.display = 'none';
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            return;
        }

        // Show container and hide empty state
        container.style.display = 'grid';
        if (emptyState) {
            emptyState.style.display = 'none';
        }

        // Create a map of new node data for quick lookup
        const newNodesMap = new Map();
        nodesData.forEach(node => {
            newNodesMap.set(node.id, node);
        });

        // Get existing cards
        const existingCards = container.querySelectorAll('.node-card[data-node-id]');
        const existingNodeIds = new Set();

        // Update existing cards
        existingCards.forEach(cardElement => {
            const nodeId = cardElement.getAttribute('data-node-id');
            existingNodeIds.add(nodeId);
            
            const newNodeData = newNodesMap.get(nodeId);
            if (newNodeData) {
                this.updateExistingNodeCard(cardElement, newNodeData);
                this.nodes.set(nodeId, newNodeData);
            } else {
                // Node was removed, remove the card with animation
                this.removeNodeCard(cardElement);
                this.nodes.delete(nodeId);
            }
        });

        // Add new nodes that don't exist yet
        nodesData.forEach(nodeData => {
            if (!existingNodeIds.has(nodeData.id)) {
                const nodeCard = this.createNodeCard(nodeData);
                nodeCard.style.opacity = '0';
                nodeCard.style.transform = 'translateY(20px)';
                container.appendChild(nodeCard);
                
                // Animate in the new card
                requestAnimationFrame(() => {
                    nodeCard.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    nodeCard.style.opacity = '1';
                    nodeCard.style.transform = 'translateY(0)';
                });
                
                this.nodes.set(nodeData.id, nodeData);
            }
        });
    }

    /**
     * Update an existing node card with new data
     * @param {HTMLElement} cardElement - Existing card element
     * @param {Object} nodeData - New node data
     */
    updateExistingNodeCard(cardElement, nodeData) {
        // Update node info
        const nameText = cardElement.querySelector('.name-text');
        const nodeHost = cardElement.querySelector('.node-host');
        const statusBadge = cardElement.querySelector('.node-status-badge');
        
        if (nameText) nameText.textContent = nodeData.name || 'Unknown Node';
        if (nodeHost) nodeHost.textContent = `${nodeData.host}:${nodeData.port || 8006}`;
        
        // Update status badge with animation
        this.updateStatusBadgeAnimated(statusBadge, nodeData.status, nodeData.is_connected);
        
        // Update metrics with animation
        this.updateNodeMetricsAnimated(cardElement, nodeData);
        
        // Update connection info
        this.updateConnectionInfoAnimated(cardElement, nodeData);
        
        // Update VM/LXC counts
        this.updateResourceCountsAnimated(cardElement, nodeData);
    }

    /**
     * Update status badge with smooth animation
     * @param {HTMLElement} badge - Status badge element
     * @param {string} status - Node status
     * @param {boolean} isConnected - Connection status
     */
    updateStatusBadgeAnimated(badge, status, isConnected) {
        if (!badge) return;
        
        const currentText = badge.textContent;
        let statusText = 'Unknown';
        let statusClass = 'status-unknown';
        
        if (isConnected) {
            switch (status) {
                case 'online':
                    statusText = 'Online';
                    statusClass = 'status-online';
                    break;
                case 'connected':
                    statusText = 'Connected';
                    statusClass = 'status-connected';
                    break;
                default:
                    statusText = 'Connected';
                    statusClass = 'status-connected';
            }
        } else {
            switch (status) {
                case 'offline':
                    statusText = 'Offline';
                    statusClass = 'status-offline';
                    break;
                case 'error':
                    statusText = 'Error';
                    statusClass = 'status-error';
                    break;
                default:
                    statusText = 'Offline';
                    statusClass = 'status-offline';
            }
        }
        
        // Only update if changed
        if (currentText !== statusText) {
            badge.style.transition = 'all 0.3s ease';
            badge.className = 'node-status-badge ' + statusClass;
            badge.textContent = statusText;
        }
    }

    /**
     * Update node metrics with smooth animations
     * @param {HTMLElement} cardElement - Card element
     * @param {Object} nodeData - Node data
     */
    updateNodeMetricsAnimated(cardElement, nodeData) {
        // CPU metrics
        const cpuUsage = cardElement.querySelector('.cpu-usage');
        const cpuProgress = cardElement.querySelector('.cpu-progress');
        
        if (nodeData.is_connected && nodeData.cpu_usage !== undefined) {
            const cpuPercent = Math.round(nodeData.cpu_usage * 100);
            if (cpuUsage && cpuUsage.textContent !== `${cpuPercent}%`) {
                cpuUsage.textContent = `${cpuPercent}%`;
            }
            if (cpuProgress) {
                cpuProgress.style.transition = 'width 0.5s ease';
                cpuProgress.style.width = `${cpuPercent}%`;
                cpuProgress.setAttribute('aria-valuenow', cpuPercent);
                cpuProgress.className = `metric-progress cpu-progress ${this.getProgressColorClass(cpuPercent)}`;
            }
        } else {
            if (cpuUsage && cpuUsage.textContent !== '--') {
                cpuUsage.textContent = '--';
            }
            if (cpuProgress) {
                cpuProgress.style.transition = 'width 0.5s ease';
                cpuProgress.style.width = '0%';
                cpuProgress.setAttribute('aria-valuenow', 0);
                cpuProgress.className = 'metric-progress cpu-progress';
            }
        }

        // Memory metrics
        const memoryUsage = cardElement.querySelector('.memory-usage');
        const memoryProgress = cardElement.querySelector('.memory-progress');
        
        if (nodeData.is_connected && nodeData.memory_percentage !== undefined) {
            const memPercent = Math.round(nodeData.memory_percentage);
            if (memoryUsage && memoryUsage.textContent !== `${memPercent}%`) {
                memoryUsage.textContent = `${memPercent}%`;
            }
            if (memoryProgress) {
                memoryProgress.style.transition = 'width 0.5s ease';
                memoryProgress.style.width = `${memPercent}%`;
                memoryProgress.setAttribute('aria-valuenow', memPercent);
                memoryProgress.className = `metric-progress memory-progress ${this.getProgressColorClass(memPercent)}`;
            }
        } else {
            if (memoryUsage && memoryUsage.textContent !== '--') {
                memoryUsage.textContent = '--';
            }
            if (memoryProgress) {
                memoryProgress.style.transition = 'width 0.5s ease';
                memoryProgress.style.width = '0%';
                memoryProgress.setAttribute('aria-valuenow', 0);
                memoryProgress.className = 'metric-progress memory-progress';
            }
        }

        // Disk metrics
        const diskUsage = cardElement.querySelector('.disk-usage');
        const diskProgress = cardElement.querySelector('.disk-progress');
        
        if (nodeData.is_connected && nodeData.disk_percentage !== undefined) {
            const diskPercent = Math.round(nodeData.disk_percentage);
            if (diskUsage && diskUsage.textContent !== `${diskPercent}%`) {
                diskUsage.textContent = `${diskPercent}%`;
            }
            if (diskProgress) {
                diskProgress.style.transition = 'width 0.5s ease';
                diskProgress.style.width = `${diskPercent}%`;
                diskProgress.setAttribute('aria-valuenow', diskPercent);
                diskProgress.className = `metric-progress disk-progress ${this.getProgressColorClass(diskPercent)}`;
            }
        } else {
            if (diskUsage && diskUsage.textContent !== '--') {
                diskUsage.textContent = '--';
            }
            if (diskProgress) {
                diskProgress.style.transition = 'width 0.5s ease';
                diskProgress.style.width = '0%';
                diskProgress.setAttribute('aria-valuenow', 0);
                diskProgress.className = 'metric-progress disk-progress';
            }
        }
    }

    /**
     * Update connection info with animation
     * @param {HTMLElement} cardElement - Card element
     * @param {Object} nodeData - Node data
     */
    updateConnectionInfoAnimated(cardElement, nodeData) {
        const connectionIcon = cardElement.querySelector('.connection-icon');
        const connectionText = cardElement.querySelector('.connection-text');
        const updateTime = cardElement.querySelector('.update-time');
        
        if (connectionIcon && connectionText) {
            const currentConnected = connectionIcon.classList.contains('text-success');
            const newConnected = nodeData.is_connected;
            
            if (currentConnected !== newConnected) {
                connectionIcon.style.transition = 'color 0.3s ease';
                connectionText.style.transition = 'color 0.3s ease';
                
                if (nodeData.is_connected) {
                    connectionIcon.className = 'connection-icon fas fa-circle text-success';
                    connectionText.textContent = 'Connected';
                    connectionText.className = 'connection-text text-success';
                } else {
                    connectionIcon.className = 'connection-icon fas fa-times-circle text-danger';
                    connectionText.textContent = nodeData.connection_error || 'Disconnected';
                    connectionText.className = 'connection-text text-danger';
                }
            }
        }
        
        if (updateTime) {
            if (nodeData.last_updated) {
                const lastUpdate = new Date(nodeData.last_updated);
                const newTime = lastUpdate.toLocaleTimeString();
                if (updateTime.textContent !== newTime) {
                    updateTime.textContent = newTime;
                    // Brief highlight to show update
                    updateTime.style.transition = 'color 0.3s ease';
                    updateTime.style.color = 'var(--primary-orange)';
                    setTimeout(() => {
                        updateTime.style.color = '';
                    }, 1000);
                }
            } else {
                updateTime.textContent = '--';
            }
        }
    }

    /**
     * Update resource counts with animation
     * @param {HTMLElement} cardElement - Card element
     * @param {Object} nodeData - Node data
     */
    updateResourceCountsAnimated(cardElement, nodeData) {
        const vmCountText = cardElement.querySelector('.vm-count-text');
        const lxcCountText = cardElement.querySelector('.lxc-count-text');
        
        if (vmCountText) {
            const newVmCount = nodeData.vm_count || 0;
            if (vmCountText.textContent !== newVmCount.toString()) {
                vmCountText.style.transition = 'color 0.3s ease';
                vmCountText.textContent = newVmCount;
                vmCountText.style.color = 'var(--primary-orange)';
                setTimeout(() => {
                    vmCountText.style.color = '';
                }, 500);
            }
        }
        
        if (lxcCountText) {
            const newLxcCount = nodeData.lxc_count || 0;
            if (lxcCountText.textContent !== newLxcCount.toString()) {
                lxcCountText.style.transition = 'color 0.3s ease';
                lxcCountText.textContent = newLxcCount;
                lxcCountText.style.color = 'var(--primary-orange)';
                setTimeout(() => {
                    lxcCountText.style.color = '';
                }, 500);
            }
        }
    }

    /**
     * Remove a node card with animation
     * @param {HTMLElement} cardElement - Card element to remove
     */
    removeNodeCard(cardElement) {
        cardElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        cardElement.style.opacity = '0';
        cardElement.style.transform = 'translateY(-20px)';
        
        setTimeout(() => {
            if (cardElement.parentNode) {
                cardElement.parentNode.removeChild(cardElement);
            }
        }, 300);
    }

    /**
     * Update the nodes display with new data
     * @param {Array} nodesData - Array of node data
     */
    updateNodesDisplay(nodesData) {
        const container = document.getElementById('nodes-container');
        const emptyState = document.getElementById('nodes-empty-state');
        
        if (!container) return;

        // Clear existing content
        container.innerHTML = '';

        if (!nodesData || nodesData.length === 0) {
            container.style.display = 'none';
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            return;
        }

        // Show container and hide empty state
        container.style.display = 'grid';
        if (emptyState) {
            emptyState.style.display = 'none';
        }

        // Create node cards
        nodesData.forEach(nodeData => {
            const nodeCard = this.createNodeCard(nodeData);
            container.appendChild(nodeCard);
            
            // Store node data
            this.nodes.set(nodeData.id, nodeData);
        });
    }

    /**
     * Create a node card element
     * @param {Object} nodeData - Node data
     * @returns {HTMLElement} Node card element
     */
    createNodeCard(nodeData) {
        const template = document.getElementById('node-card-template');
        if (!template) {
            console.error('Node card template not found');
            return document.createElement('div');
        }

        const card = template.content.cloneNode(true);
        const cardElement = card.querySelector('.node-card');
        
        // Set node ID and initial state
        cardElement.setAttribute('data-node-id', nodeData.id);
        cardElement.classList.add('node-card-loading');
        
        // Update node info
        const nameText = card.querySelector('.name-text');
        const nodeHost = card.querySelector('.node-host');
        const statusBadge = card.querySelector('.node-status-badge');
        
        if (nameText) nameText.textContent = nodeData.name || 'Unknown Node';
        if (nodeHost) nodeHost.textContent = `${nodeData.host}:${nodeData.port || 8006}`;
        
        // Update status badge
        this.updateStatusBadge(statusBadge, nodeData.status, nodeData.is_connected);
        
        // Update metrics
        this.updateNodeMetrics(card, nodeData);
        
        // Update connection info
        this.updateConnectionInfo(card, nodeData);
        
        // Update VM/LXC counts
        this.updateResourceCounts(card, nodeData);
        
        // Bind card events
        this.bindCardEvents(card, nodeData);
        
        // Remove loading state after a brief delay to ensure smooth rendering
        setTimeout(() => {
            cardElement.classList.remove('node-card-loading');
            cardElement.classList.add('node-card-ready');
        }, 100);
        
        return card;
    }

    /**
     * Update status badge
     * @param {HTMLElement} badge - Status badge element
     * @param {string} status - Node status
     * @param {boolean} isConnected - Connection status
     */
    updateStatusBadge(badge, status, isConnected) {
        if (!badge) return;
        
        // Clear existing classes
        badge.className = 'node-status-badge';
        
        let statusText = 'Unknown';
        let statusClass = 'status-unknown';
        
        if (isConnected) {
            switch (status) {
                case 'online':
                    statusText = 'Online';
                    statusClass = 'status-online';
                    break;
                case 'connected':
                    statusText = 'Connected';
                    statusClass = 'status-connected';
                    break;
                default:
                    statusText = 'Connected';
                    statusClass = 'status-connected';
            }
        } else {
            switch (status) {
                case 'offline':
                    statusText = 'Offline';
                    statusClass = 'status-offline';
                    break;
                case 'error':
                    statusText = 'Error';
                    statusClass = 'status-error';
                    break;
                default:
                    statusText = 'Offline';
                    statusClass = 'status-offline';
            }
        }
        
        badge.textContent = statusText;
        badge.classList.add(statusClass);
    }

    /**
     * Update node metrics display
     * @param {DocumentFragment|HTMLElement} card - Card element
     * @param {Object} nodeData - Node data
     */
    updateNodeMetrics(card, nodeData) {
        // CPU metrics
        const cpuUsage = card.querySelector('.cpu-usage');
        const cpuProgress = card.querySelector('.cpu-progress');
        
        if (nodeData.is_connected && nodeData.cpu_usage !== undefined) {
            const cpuPercent = Math.round(nodeData.cpu_usage * 100);
            if (cpuUsage) cpuUsage.textContent = `${cpuPercent}%`;
            if (cpuProgress) {
                cpuProgress.style.width = `${cpuPercent}%`;
                cpuProgress.setAttribute('aria-valuenow', cpuPercent);
                cpuProgress.className = `metric-progress cpu-progress ${this.getProgressColorClass(cpuPercent)}`;
            }
        } else {
            if (cpuUsage) cpuUsage.textContent = '--';
            if (cpuProgress) {
                cpuProgress.style.width = '0%';
                cpuProgress.setAttribute('aria-valuenow', 0);
                cpuProgress.className = 'metric-progress cpu-progress';
            }
        }

        // Memory metrics
        const memoryUsage = card.querySelector('.memory-usage');
        const memoryProgress = card.querySelector('.memory-progress');
        
        if (nodeData.is_connected && nodeData.memory_percentage !== undefined) {
            const memPercent = Math.round(nodeData.memory_percentage);
            if (memoryUsage) memoryUsage.textContent = `${memPercent}%`;
            if (memoryProgress) {
                memoryProgress.style.width = `${memPercent}%`;
                memoryProgress.setAttribute('aria-valuenow', memPercent);
                memoryProgress.className = `metric-progress memory-progress ${this.getProgressColorClass(memPercent)}`;
            }
        } else {
            if (memoryUsage) memoryUsage.textContent = '--';
            if (memoryProgress) {
                memoryProgress.style.width = '0%';
                memoryProgress.setAttribute('aria-valuenow', 0);
                memoryProgress.className = 'metric-progress memory-progress';
            }
        }

        // Disk metrics
        const diskUsage = card.querySelector('.disk-usage');
        const diskProgress = card.querySelector('.disk-progress');
        
        if (nodeData.is_connected && nodeData.disk_percentage !== undefined) {
            const diskPercent = Math.round(nodeData.disk_percentage);
            if (diskUsage) diskUsage.textContent = `${diskPercent}%`;
            if (diskProgress) {
                diskProgress.style.width = `${diskPercent}%`;
                diskProgress.setAttribute('aria-valuenow', diskPercent);
                diskProgress.className = `metric-progress disk-progress ${this.getProgressColorClass(diskPercent)}`;
            }
        } else {
            if (diskUsage) diskUsage.textContent = '--';
            if (diskProgress) {
                diskProgress.style.width = '0%';
                diskProgress.setAttribute('aria-valuenow', 0);
                diskProgress.className = 'metric-progress disk-progress';
            }
        }
    }

    /**
     * Update connection info
     * @param {DocumentFragment|HTMLElement} card - Card element
     * @param {Object} nodeData - Node data
     */
    updateConnectionInfo(card, nodeData) {
        const connectionIcon = card.querySelector('.connection-icon');
        const connectionText = card.querySelector('.connection-text');
        const updateTime = card.querySelector('.update-time');
        
        if (connectionIcon && connectionText) {
            if (nodeData.is_connected) {
                connectionIcon.className = 'connection-icon fas fa-circle text-success';
                connectionText.textContent = 'Connected';
                connectionText.className = 'connection-text text-success';
            } else {
                connectionIcon.className = 'connection-icon fas fa-times-circle text-danger';
                connectionText.textContent = nodeData.connection_error || 'Disconnected';
                connectionText.className = 'connection-text text-danger';
            }
        }
        
        if (updateTime) {
            if (nodeData.last_updated) {
                const lastUpdate = new Date(nodeData.last_updated);
                updateTime.textContent = lastUpdate.toLocaleTimeString();
            } else {
                updateTime.textContent = '--';
            }
        }
    }

    /**
     * Update resource counts (VMs and LXC containers)
     * @param {DocumentFragment|HTMLElement} card - Card element
     * @param {Object} nodeData - Node data
     */
    updateResourceCounts(card, nodeData) {
        const vmCountText = card.querySelector('.vm-count-text');
        const lxcCountText = card.querySelector('.lxc-count-text');
        
        if (vmCountText) {
            vmCountText.textContent = nodeData.vm_count || 0;
        }
        
        if (lxcCountText) {
            lxcCountText.textContent = nodeData.lxc_count || 0;
        }
    }

    /**
     * Bind events to card elements
     * @param {DocumentFragment|HTMLElement} card - Card element
     * @param {Object} nodeData - Node data
     */
    bindCardEvents(card, nodeData) {
        // Dashboard link button
        const dashboardBtn = card.querySelector('.dashboard-link-btn');
        if (dashboardBtn) {
            dashboardBtn.addEventListener('click', () => {
                this.openProxmoxDashboard(nodeData);
            });
        }

        // Test connection button
        const testBtn = card.querySelector('.test-node-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => {
                this.testNodeConnection(nodeData.id, testBtn);
            });
        }

        // Edit button
        const editBtn = card.querySelector('.edit-node-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                this.editNode(nodeData);
            });
        }

        // Delete button
        const deleteBtn = card.querySelector('.delete-node-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                this.deleteNode(nodeData);
            });
        }

        // Resources button
        const resourcesBtn = card.querySelector('.resources-btn');
        if (resourcesBtn) {
            resourcesBtn.addEventListener('click', () => {
                this.viewNodeResources(nodeData);
            });
        }
    }

    /**
     * Open Proxmox web dashboard
     * @param {Object} nodeData - Node data
     */
    openProxmoxDashboard(nodeData) {
        const protocol = nodeData.ssl_verify !== false ? 'https' : 'https'; // Always use HTTPS for Proxmox
        const port = nodeData.port || 8006;
        const url = `${protocol}://${nodeData.host}:${port}`;
        
        // Open in new tab/window
        window.open(url, '_blank', 'noopener,noreferrer');
        
        // Log the action
        console.log(`Opening Proxmox dashboard for ${nodeData.name}: ${url}`);
    }

    /**
     * Test node connection
     * @param {string} nodeId - Node ID
     * @param {HTMLElement} button - Test button element
     */
    async testNodeConnection(nodeId, button) {
        const originalContent = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;

        try {
            const response = await proxmoxAPI.testNodeConnection(nodeId);
            
            if (response.success) {
                if (response.data.connected) {
                    showNotification('Connection test successful', 'success');
                } else {
                    showNotification('Connection test failed: ' + response.message, 'warning');
                }
            } else {
                showNotification('Connection test failed: ' + response.error, 'error');
            }
        } catch (error) {
            console.error('Connection test failed:', error);
            showNotification('Connection test failed: ' + error.message, 'error');
        } finally {
            button.innerHTML = originalContent;
            button.disabled = false;
        }
    }

    /**
     * Edit node configuration
     * @param {Object} nodeData - Node data
     */
    editNode(nodeData) {
        // Trigger the node configuration form via the config manager
        if (window.nodeConfigManager) {
            window.nodeConfigManager.showEditNodeForm(nodeData);
        } else {
            console.log('Edit node:', nodeData);
            showNotification('Node configuration manager not available', 'error');
        }
    }

    /**
     * Delete node
     * @param {Object} nodeData - Node data
     */
    async deleteNode(nodeData) {
        if (!confirm(`Are you sure you want to delete the node "${nodeData.name}"?`)) {
            return;
        }

        try {
            const response = await proxmoxAPI.deleteNode(nodeData.id);
            
            if (response.success) {
                showNotification(`Node "${nodeData.name}" deleted successfully`, 'success');
                this.refreshNodes();
            } else {
                showNotification('Failed to delete node: ' + response.error, 'error');
            }
        } catch (error) {
            console.error('Failed to delete node:', error);
            showNotification('Failed to delete node: ' + error.message, 'error');
        }
    }

    /**
     * View node resources
     * @param {Object} nodeData - Node data
     */
    viewNodeResources(nodeData) {
        // This would show VM/LXC resources for the node
        // For now, just log the action
        console.log('View resources for node:', nodeData);
        showNotification('Resource view will be implemented in a future task', 'info');
    }

    /**
     * Get progress bar color class based on percentage
     * @param {number} percentage - Usage percentage
     * @returns {string} CSS class name
     */
    getProgressColorClass(percentage) {
        if (percentage >= 90) return 'progress-danger';
        if (percentage >= 75) return 'progress-warning';
        if (percentage >= 50) return 'progress-info';
        return 'progress-success';
    }

    /**
     * Show loading state
     */
    showLoading() {
        const container = document.getElementById('nodes-container');
        const emptyState = document.getElementById('nodes-empty-state');
        
        if (container) {
            container.innerHTML = `
                <div class="loading-placeholder">
                    <i class="fas fa-spinner fa-spin"></i>
                    Loading nodes...
                </div>
            `;
            container.style.display = 'block';
        }
        
        if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    /**
     * Show error state
     * @param {string} message - Error message
     */
    showError(message) {
        const container = document.getElementById('nodes-container');
        const emptyState = document.getElementById('nodes-empty-state');
        
        if (container) {
            container.innerHTML = `
                <div class="error-placeholder">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="nodeDashboard.refreshNodes()">
                        <i class="fas fa-sync-alt"></i>
                        Retry
                    </button>
                </div>
            `;
            container.style.display = 'block';
        }
        
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        
        showNotification(message, 'error');
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.autoRefreshEnabled) {
            this.refreshInterval = setInterval(() => {
                // Only refresh if the Proxmox tab is active
                const proxmoxPanel = document.getElementById('proxmox-panel');
                if (proxmoxPanel && !proxmoxPanel.hidden && proxmoxPanel.classList.contains('active')) {
                    // Use silent refresh for auto-refresh to avoid disturbing the user
                    this.loadNodes(true);
                }
            }, this.refreshIntervalMs);
        }
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Show or hide the refresh indicator
     * @param {boolean} show - Whether to show the indicator
     */
    showRefreshIndicator(show) {
        const indicator = document.getElementById('refresh-indicator');
        if (!indicator) return;
        
        if (show) {
            indicator.style.display = 'flex';
            // Small delay to ensure the element is rendered before adding the class
            requestAnimationFrame(() => {
                indicator.classList.add('show');
            });
        } else {
            indicator.classList.remove('show');
            // Hide after transition completes
            setTimeout(() => {
                if (!indicator.classList.contains('show')) {
                    indicator.style.display = 'none';
                }
            }, 300);
        }
    }

    /**
     * Destroy the dashboard (cleanup)
     */
    destroy() {
        this.stopAutoRefresh();
        this.nodes.clear();
    }
}

// Global instance
let nodeDashboard;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the Proxmox tab
    const proxmoxPanel = document.getElementById('proxmox-panel');
    if (proxmoxPanel) {
        nodeDashboard = new NodeDashboard();
        // Expose globally for other modules
        window.nodeDashboard = nodeDashboard;
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NodeDashboard };
}