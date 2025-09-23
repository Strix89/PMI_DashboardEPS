/**
 * Acronis Backup Management JavaScript Module
 * 
 * This module provides functionality for the Acronis tab including:
 * - View management and navigation
 * - Agent loading and display with status indicators
 * - Automatic data refresh
 * - Integration with PMI Dashboard notification system
 */

class AcronisManager {
    constructor() {
        this.baseUrl = '/api/acronis';
        this.currentView = 'dashboard'; // dashboard, config, details
        this.currentAgentId = null;
        this.refreshInterval = null;
        this.refreshRate = 30000; // 30 seconds for more frequent updates
        this.isActive = false;
        this.agents = [];
        this.workloads = [];
        this.statistics = {};

        // Enhanced resource management
        this.activeRequests = new Map(); // Track active requests for cleanup
        this.retryTimeout = null;
        this.refreshTimeouts = new Set(); // Track all timeouts for cleanup
        this.lastRefreshTime = null;
        this.refreshBackoffMultiplier = 1;
        this.maxBackoffMultiplier = 8;
        this.consecutiveErrors = 0;
        this.maxConsecutiveErrors = 3;

        // Performance monitoring
        this.performanceMetrics = {
            requestCount: 0,
            errorCount: 0,
            averageResponseTime: 0,
            lastSuccessfulRefresh: null
        };

        this.init();
    }

    /**
     * Initialize the Acronis manager
     */
    init() {
        this.setupEventListeners();
        this.setupViewManagement();
        this.checkInitialConfiguration();

        console.log('Acronis Manager initialized');
    }

    /**
     * Setup event listeners for UI interactions
     */
    setupEventListeners() {
        // Configuration button
        const configBtn = document.getElementById('acronis-config-btn');
        if (configBtn) {
            configBtn.addEventListener('click', () => this.showConfigurationView());
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-acronis-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }

        // Auto-refresh toggle with enhanced handling
        const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    // Reset error state when manually enabling
                    this.consecutiveErrors = 0;
                    this.refreshBackoffMultiplier = 1;
                    this.startAutoRefresh();

                    // Show confirmation
                    this.showNotification('Auto-refresh enabled', 'success', 2000);
                } else {
                    this.stopAutoRefresh();
                    this.showNotification('Auto-refresh disabled', 'info', 2000);
                }
            });
        }

        // Back to dashboard button
        const backBtn = document.getElementById('back-to-dashboard-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.showDashboardView());
        }

        // Refresh details button
        const refreshDetailsBtn = document.getElementById('refresh-details-btn');
        if (refreshDetailsBtn) {
            refreshDetailsBtn.addEventListener('click', () => this.refreshAgentDetails());
        }

        // Retry buttons
        const retryAgentsBtn = document.getElementById('retry-agents-btn');
        if (retryAgentsBtn) {
            retryAgentsBtn.addEventListener('click', () => this.loadAgents());
        }

        const retryBackupsBtn = document.getElementById('retry-backups-btn');
        if (retryBackupsBtn) {
            retryBackupsBtn.addEventListener('click', () => this.loadAgentBackups(this.currentAgentId));
        }

        // Listen for tab changes with enhanced handling
        document.addEventListener('tabchange', (e) => {
            if (e.detail.tab === 'acronis') {
                this.onTabActivated(e.detail.previousTab);
            } else if (e.detail.previousTab === 'acronis') {
                this.onTabDeactivated(e.detail.tab);
            }
        });

        // Listen for app pause/resume events (mobile optimization)
        document.addEventListener('apppaused', () => this.onAppPaused());
        document.addEventListener('appresumed', () => this.onAppResumed());

        // Listen for page visibility changes for better resource management
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.onPageHidden();
            } else {
                this.onPageVisible();
            }
        });

        // Listen for beforeunload to cleanup resources
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });

        // Listen for network status changes
        window.addEventListener('online', () => this.onNetworkOnline());
        window.addEventListener('offline', () => this.onNetworkOffline());
    }

    /**
     * Setup view management
     */
    setupViewManagement() {
        // Initially show dashboard view if configuration exists
        this.showView('dashboard');
    }

    /**
     * Check if initial configuration exists
     * @param {boolean} silent - Whether to load data silently without notifications
     */
    async checkInitialConfiguration() {
        try {
            const response = await this.makeRequest('GET', '/config');
            if (response && response.success && response.data && response.data.configured) {
                // Configuration exists, show dashboard
                this.showDashboardView();
                this.loadInitialData();
            } else {
                // No configuration, show config view
                this.showConfigurationView();
            }
        } catch (error) {
            console.warn('Could not check configuration:', error.message);
            // Show configuration view as fallback
            this.showConfigurationView();
        }
    }

    /**
     * Show a specific view
     * @param {string} viewName - Name of the view to show
     */
    showView(viewName) {
        const views = ['config', 'dashboard', 'details'];

        views.forEach(view => {
            const element = document.getElementById(`acronis-${view}-view`);
            if (element) {
                element.style.display = view === viewName ? 'block' : 'none';
            }
        });

        this.currentView = viewName;
    }

    /**
     * Show configuration view
     */
    showConfigurationView() {
        this.showView('config');
        this.stopAutoRefresh();

        // Load existing configuration if available
        if (window.acronisConfigManager) {
            window.acronisConfigManager.loadConfiguration();
        }
    }

    /**
     * Show dashboard view
     */
    showDashboardView() {
        console.log(`showDashboardView called, isActive=${this.isActive}`);
        this.showView('dashboard');
        if (this.isActive) {
            console.log('Loading initial data and starting auto-refresh...');
            this.loadInitialData();
            this.startAutoRefresh();
        } else {
            console.log('Tab not active, skipping data load');
        }
    }

    /**
     * Show agent details view
     * @param {string} agentId - ID of the agent to show details for
     */
    showDetailsView(agentId) {
        this.currentAgentId = agentId;
        this.showView('details');
        this.loadAgentDetails(agentId);
        this.loadAgentBackups(agentId);
    }

    /**
     * Load initial data for dashboard
     */
    async loadInitialData() {
        await Promise.all([
            this.loadStatistics(),
            this.loadAgents(),
            this.loadWorkloads()
        ]);
    }

    /**
     * Load backup statistics with enhanced status indicators
     */
    async loadStatistics() {
        // Removed loading notification - keep only visual indicators

        try {
            const response = await this.makeRequest('GET', '/backups');

            if (response && response.success) {
                this.statistics = response.data.summary || {};
                this.updateStatisticsDisplay();

                // Load charts if chart module is available
                if (window.acronisCharts) {
                    window.acronisCharts.updateCharts(response.data);
                }

                // Removed connection status notification
            }
        } catch (error) {
            this.handleError(error, 'load backup statistics');
            this.showEmptyStatistics();
        }
    }

    /**
     * Load agents list with enhanced status indicators
     */
    async loadAgents() {
        // Add loading class for visual feedback
        const container = document.getElementById('agents-container');
        if (container) {
            container.classList.add('loading');
        }
        
        this.showAgentsLoading(true);

        try {
            const response = await this.makeRequest('GET', '/agents');

            if (response && response.success) {
                this.agents = response.data.agents || [];
                this.displayAgents();
                this.updateAgentsCount();

                if (this.agents.length === 0) {
                    this.showNotification('No Acronis agents found', 'info', 3000, {
                        helpText: 'Make sure agents are properly configured and connected to your Acronis account'
                    });
                }
            } else {
                this.showAgentsEmptyState();
            }
        } catch (error) {
            this.handleError(error, 'load agents');
            this.showAgentsEmptyState();
        } finally {
            this.showAgentsLoading(false);
            if (container) {
                container.classList.remove('loading');
            }
        }
    }

    /**
     * Load workloads list
     */
    async loadWorkloads() {
        try {
            const response = await this.makeRequest('GET', '/workloads');

            if (response && response.success) {
                this.workloads = response.data.workloads || [];
                this.updateWorkloadsCount();
            } else {
                this.workloads = [];
                this.updateWorkloadsCount();
            }
        } catch (error) {
            this.handleError(error, 'load workloads');
            this.workloads = [];
            this.updateWorkloadsCount();
        }
    }

    /**
     * Update workloads count display
     */
    updateWorkloadsCount() {
        const totalWorkloads = document.getElementById('total-workloads');
        if (totalWorkloads) {
            totalWorkloads.textContent = this.workloads ? this.workloads.length : '--';
        }
    }

    /**
     * Load agent details
     * @param {string} agentId - Agent ID
     */
    async loadAgentDetails(agentId) {
        const agent = this.agents.find(a => a.id_agent === agentId);

        if (agent) {
            this.displayAgentInfo(agent);
        } else {
            // Try to fetch agent details from API
            try {
                const response = await this.makeRequest('GET', `/agents/${agentId}`);
                if (response && response.success) {
                    this.displayAgentInfo(response.data);
                }
            } catch (error) {
                this.handleError(error, 'load agent details');
            }
        }
    }

    /**
     * Load agent backup details
     * @param {string} agentId - Agent ID
     */
    async loadAgentBackups(agentId) {
        this.showBackupsLoading(true);

        try {
            const response = await this.makeRequest('GET', `/agent/${agentId}/backups`);

            console.log('Agent backups response:', response); // Debug log

            if (response && response.success) {
                console.log('Backup data:', response.data); // Debug log
                console.log('Number of backups:', response.data.backups ? response.data.backups.length : 0); // Debug log
                this.displayAgentBackups(response.data);
            } else {
                console.log('No success in response or no response'); // Debug log
                this.showBackupsEmptyState();
            }
        } catch (error) {
            console.error('Error loading agent backups:', error); // Debug log
            this.handleError(error, 'load agent backups');
            this.showBackupsEmptyState();
        } finally {
            this.showBackupsLoading(false);
        }
    }

    /**
     * Display agents in the grid
     */
    displayAgents() {
        const container = document.getElementById('agents-container');
        const template = document.getElementById('agent-card-template');

        if (!container || !template) return;

        // Clear existing content
        container.innerHTML = '';

        if (this.agents.length === 0) {
            this.showAgentsEmptyState();
            return;
        }

        this.agents.forEach(agent => {
            const card = this.createAgentCard(agent, template);
            container.appendChild(card);
        });

        // Hide empty state
        const emptyState = document.getElementById('agents-empty-state');
        if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    /**
     * Create an agent card element
     * @param {Object} agent - Agent data
     * @param {HTMLElement} template - Card template
     * @returns {HTMLElement} Agent card element
     */
    createAgentCard(agent, template) {
        const card = template.content.cloneNode(true);
        const cardElement = card.querySelector('.agent-card');

        // Set agent ID
        cardElement.setAttribute('data-agent-id', agent.id_agent);

        // Fill in agent data
        card.querySelector('.agent-hostname').textContent = agent.hostname || '--';
        card.querySelector('.agent-id').textContent = agent.id_agent || '--';
        card.querySelector('.agent-tenant').textContent = agent.id_tenant || '--';
        card.querySelector('.agent-uptime').textContent = agent.uptime || '--';

        // Set platform info
        const platformElement = card.querySelector('.agent-platform');
        if (agent.platform && agent.platform.name) {
            platformElement.textContent = `${agent.platform.name} (${agent.platform.arch || 'unknown'})`;
        } else {
            platformElement.textContent = '--';
        }

        // Set status
        const statusElement = card.querySelector('.agent-status');
        const status = agent.online ? 'online' : 'offline';
        statusElement.textContent = status;
        statusElement.className = `status-indicator ${this.getStatusClass(status)}`;

        // Setup view details button
        const viewDetailsBtn = card.querySelector('.view-details-btn');
        if (viewDetailsBtn) {
            viewDetailsBtn.addEventListener('click', () => {
                this.showDetailsView(agent.id_agent);
            });
        }

        // Chart containers removed - agent cards now show only basic info

        return cardElement;
    }

    /**
     * Display agent information in details view
     * @param {Object} agent - Agent data
     */
    displayAgentInfo(agent) {
        document.getElementById('details-agent-name').textContent = `${agent.hostname} - Backup Details`;
        document.getElementById('agent-hostname').textContent = agent.hostname || '--';
        document.getElementById('agent-id').textContent = agent.id_agent || '--';
        document.getElementById('agent-tenant').textContent = agent.id_tenant || '--';
        document.getElementById('agent-uptime').textContent = agent.uptime || '--';

        // Set platform info
        const platformElement = document.getElementById('agent-platform');
        if (agent.platform && agent.platform.name) {
            platformElement.textContent = `${agent.platform.name} (${agent.platform.arch || 'unknown'})`;
        } else {
            platformElement.textContent = '--';
        }

        // Set status
        const statusElement = document.getElementById('agent-status');
        const status = agent.online ? 'online' : 'offline';
        statusElement.textContent = status;
        statusElement.className = `status-indicator ${this.getStatusClass(status)}`;
    }

    /**
     * Display agent backups in details view
     * @param {Object} backupData - Backup data
     */
    displayAgentBackups(backupData) {
        const container = document.getElementById('backups-container');
        const template = document.getElementById('backup-item-template');

        if (!container || !template) return;

        // Clear existing content
        container.innerHTML = '';

        const backups = backupData.backups || [];

        if (backups.length === 0) {
            this.showBackupsEmptyState();
            return;
        }

        backups.forEach((backup, index) => {
            const item = this.createBackupItem(backup, template, index);
            container.appendChild(item);
        });

        // Update backups count
        const countBadge = document.getElementById('backups-count-badge');
        if (countBadge) {
            countBadge.textContent = backups.length;
        }

        // Hide empty state
        const emptyState = document.getElementById('backups-empty-state');
        if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    /**
     * Create a backup item element
     * @param {Object} backup - Backup data
     * @param {HTMLElement} template - Item template
     * @param {number} index - Item index
     * @returns {HTMLElement} Backup item element
     */
    createBackupItem(backup, template, index) {
        const item = template.content.cloneNode(true);
        const itemElement = item.querySelector('.backup-item');

        // Set backup ID
        itemElement.setAttribute('data-backup-id', `backup-${index}`);

        // Fill in backup data
        item.querySelector('.backup-started').textContent = backup.started_at || '--';
        item.querySelector('.backup-completed').textContent = backup.completed_at || '--';
        item.querySelector('.backup-state').textContent = backup.state || '--';
        item.querySelector('.backup-result').textContent = backup.result || '--';
        item.querySelector('.backup-mode').textContent = backup.run_mode || '--';

        // Format backup size
        const sizeElement = item.querySelector('.backup-size');
        if (backup.bytes_saved) {
            sizeElement.textContent = this.formatBytes(backup.bytes_saved);
        } else {
            sizeElement.textContent = '--';
        }

        // Calculate duration
        const durationElement = item.querySelector('.backup-duration');
        if (backup.started_at && backup.completed_at) {
            const duration = this.calculateDuration(backup.started_at, backup.completed_at);
            durationElement.textContent = `(${duration})`;
        } else {
            durationElement.textContent = '';
        }

        // Set status classes
        const stateElement = item.querySelector('.backup-state');
        stateElement.className = `backup-state ${this.getBackupStateClass(backup.state)}`;

        const resultElement = item.querySelector('.backup-result');
        resultElement.className = `backup-result ${this.getBackupResultClass(backup.result)}`;

        // Setup expand/collapse for activities
        const expandBtn = item.querySelector('.expand-backup-btn');
        const activitiesSection = item.querySelector('.backup-activities');

        if (expandBtn && activitiesSection) {
            // Update button title with activity count
            const activityCount = backup.activities ? backup.activities.length : 0;
            expandBtn.title = activityCount > 0 ?
                `Show ${activityCount} activit${activityCount === 1 ? 'y' : 'ies'}` :
                'Show activities';

            expandBtn.addEventListener('click', () => {
                const isExpanded = activitiesSection.style.display !== 'none';
                activitiesSection.style.display = isExpanded ? 'none' : 'block';

                const icon = expandBtn.querySelector('i');
                if (icon) {
                    icon.className = isExpanded ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
                }

                // Update button title
                expandBtn.title = isExpanded ?
                    (activityCount > 0 ? `Show ${activityCount} activit${activityCount === 1 ? 'y' : 'ies'}` : 'Show activities') :
                    'Hide activities';

                // Load activities if not loaded yet
                if (!isExpanded) {
                    this.displayBackupActivities(activitiesSection, backup.activities || []);
                }
            });
        }

        return itemElement;
    }

    /**
     * Display backup activities
     * @param {HTMLElement} container - Activities container
     * @param {Array} activities - Activities data
     */
    displayBackupActivities(container, activities) {
        const activitiesContainer = container.querySelector('.activities-container');
        const template = document.getElementById('activity-item-template');

        if (!activitiesContainer || !template) return;

        // Clear existing content
        activitiesContainer.innerHTML = '';

        if (!activities || activities.length === 0) {
            // Show no activities message
            const noActivitiesMsg = document.createElement('div');
            noActivitiesMsg.className = 'no-activities-message';
            noActivitiesMsg.innerHTML = `
                <div style="text-align: center; padding: 1rem; color: var(--text-muted); font-size: 0.875rem;">
                    <i class="fas fa-info-circle" style="margin-right: 0.5rem;"></i>
                    No detailed activities available for this backup
                </div>
            `;
            activitiesContainer.appendChild(noActivitiesMsg);
            return;
        }

        activities.forEach(activity => {
            const item = template.content.cloneNode(true);

            item.querySelector('.activity-name').textContent = activity.name || '--';
            item.querySelector('.activity-status').textContent = activity.status || '--';
            item.querySelector('.activity-time').textContent = activity.time || '--';

            activitiesContainer.appendChild(item);
        });
    }

    /**
     * Update statistics display
     */
    updateStatisticsDisplay() {
        const stats = this.statistics;

        document.getElementById('total-backups').textContent = stats.num_backups || '--';
        document.getElementById('successful-backups').textContent = stats.success || '--';
        document.getElementById('failed-backups').textContent = stats.failed || '--';

        // Update agents count from current agents array
        document.getElementById('total-agents').textContent = this.agents.length || '--';
    }

    /**
     * Show empty statistics
     */
    showEmptyStatistics() {
        document.getElementById('total-backups').textContent = '--';
        document.getElementById('successful-backups').textContent = '--';
        document.getElementById('failed-backups').textContent = '--';
        document.getElementById('total-agents').textContent = '--';
    }

    /**
     * Update agents count display
     */
    updateAgentsCount() {
        const countBadge = document.getElementById('agents-count-badge');
        if (countBadge) {
            countBadge.textContent = this.agents.length;
        }
    }

    /**
     * Show/hide agents loading state
     * @param {boolean} show - Whether to show loading state
     */
    showAgentsLoading(show) {
        const loading = document.getElementById('agents-loading');
        const container = document.getElementById('agents-container');

        if (loading) {
            loading.style.display = show ? 'block' : 'none';
        }

        if (container && show) {
            container.innerHTML = '';
        }
    }

    /**
     * Show agents empty state
     */
    showAgentsEmptyState() {
        const emptyState = document.getElementById('agents-empty-state');
        const container = document.getElementById('agents-container');

        if (emptyState) {
            emptyState.style.display = 'block';
        }

        if (container) {
            container.innerHTML = '';
        }

        this.updateAgentsCount();
    }

    /**
     * Show/hide backups loading state
     * @param {boolean} show - Whether to show loading state
     */
    showBackupsLoading(show) {
        const loading = document.getElementById('backups-loading');
        const container = document.getElementById('backups-container');

        if (loading) {
            loading.style.display = show ? 'block' : 'none';
        }

        if (container && show) {
            container.innerHTML = '';
        }
    }

    /**
     * Show backups empty state
     */
    showBackupsEmptyState() {
        const emptyState = document.getElementById('backups-empty-state');
        const container = document.getElementById('backups-container');

        if (emptyState) {
            emptyState.style.display = 'block';
        }

        if (container) {
            container.innerHTML = '';
        }

        // Update count
        const countBadge = document.getElementById('backups-count-badge');
        if (countBadge) {
            countBadge.textContent = '0';
        }
    }

    /**
     * Refresh all data with enhanced feedback
     */
    async refreshData() {
        this.showRefreshIndicator(true);

        const refreshId = this.showNotification('Refreshing Acronis data...', 'info', 0, {
            showSpinner: true,
            id: 'acronis-refresh'
        });

        try {
            await this.loadInitialData();

            // Remove loading notification
            if (window.notificationSystem && window.notificationSystem.remove) {
                window.notificationSystem.remove('acronis-refresh');
            }

            this.showNotification('Acronis data refreshed successfully', 'success', 3000, {
                helpText: 'All backup statistics and agent information have been updated'
            });
        } catch (error) {
            // Remove loading notification
            if (window.notificationSystem && window.notificationSystem.remove) {
                window.notificationSystem.remove('acronis-refresh');
            }

            this.handleError(error, 'refresh data');
        } finally {
            this.showRefreshIndicator(false);
        }
    }

    /**
     * Refresh agent details
     */
    async refreshAgentDetails() {
        if (!this.currentAgentId) return;

        this.showRefreshIndicator(true);

        try {
            await Promise.all([
                this.loadAgentDetails(this.currentAgentId),
                this.loadAgentBackups(this.currentAgentId)
            ]);
            this.showNotification('Agent details refreshed', 'success', 2000);
        } catch (error) {
            this.handleError(error, 'refresh agent details');
        } finally {
            this.showRefreshIndicator(false);
        }
    }

    /**
     * Show/hide refresh indicator
     * @param {boolean} show - Whether to show indicator
     */
    showRefreshIndicator(show) {
        const indicator = document.getElementById('refresh-acronis-indicator');
        if (indicator) {
            indicator.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Start automatic refresh with enhanced error handling and backoff
     */
    startAutoRefresh() {
        this.stopAutoRefresh(); // Ensure clean state

        // Reset backoff if we're starting fresh
        if (this.consecutiveErrors === 0) {
            this.refreshBackoffMultiplier = 1;
        }

        const effectiveRefreshRate = this.refreshRate * this.refreshBackoffMultiplier;

        this.refreshInterval = setInterval(() => {
            if (!this.isActive || document.hidden) {
                return; // Skip refresh if tab is not active or page is hidden
            }

            if (this.currentView === 'dashboard') {
                this.performAutoRefresh();
            } else if (this.currentView === 'details' && this.currentAgentId) {
                this.performAutoRefreshDetails();
            }
        }, effectiveRefreshRate);

        console.log(`Auto-refresh started with ${effectiveRefreshRate}ms interval (backoff: ${this.refreshBackoffMultiplier}x)`);

        // Update UI to reflect auto-refresh state
        this.updateAutoRefreshUI(true);
        
        // Add visual indicator
        const refreshIndicator = document.getElementById('refresh-acronis-indicator');
        if (refreshIndicator) {
            refreshIndicator.classList.add('active');
        }
    }

    /**
     * Stop automatic refresh and cleanup
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }

        // Clear any pending refresh timeouts
        this.refreshTimeouts.forEach(timeout => clearTimeout(timeout));
        this.refreshTimeouts.clear();

        console.log('Auto-refresh stopped');

        // Update UI to reflect auto-refresh state
        this.updateAutoRefreshUI(false);
        
        // Remove visual indicator
        const refreshIndicator = document.getElementById('refresh-acronis-indicator');
        if (refreshIndicator) {
            refreshIndicator.classList.remove('active');
        }
    }

    /**
     * Perform automatic refresh for dashboard view
     */
    async performAutoRefresh() {
        try {
            // Check if enough time has passed since last refresh
            const now = Date.now();
            if (this.lastRefreshTime && (now - this.lastRefreshTime) < (this.refreshRate * 0.8)) {
                return; // Skip if refreshed too recently
            }

            this.lastRefreshTime = now;

            // Perform refresh with timeout
            const refreshPromise = this.loadInitialData();
            const timeoutPromise = new Promise((_, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Auto-refresh timeout'));
                }, 30000); // 30 second timeout
                this.refreshTimeouts.add(timeout);
            });

            await Promise.race([refreshPromise, timeoutPromise]);

            // Reset error tracking on success
            this.consecutiveErrors = 0;
            this.refreshBackoffMultiplier = 1;
            this.performanceMetrics.lastSuccessfulRefresh = now;

            // Restart with normal interval if backoff was applied
            if (this.refreshBackoffMultiplier > 1) {
                this.startAutoRefresh();
            }

        } catch (error) {
            this.handleAutoRefreshError(error);
        }
    }

    /**
     * Perform automatic refresh for details view
     */
    async performAutoRefreshDetails() {
        try {
            const now = Date.now();
            if (this.lastRefreshTime && (now - this.lastRefreshTime) < (this.refreshRate * 0.8)) {
                return;
            }

            this.lastRefreshTime = now;

            await Promise.race([
                this.refreshAgentDetails(),
                new Promise((_, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Auto-refresh timeout'));
                    }, 30000);
                    this.refreshTimeouts.add(timeout);
                })
            ]);

            this.consecutiveErrors = 0;
            this.refreshBackoffMultiplier = 1;
            this.performanceMetrics.lastSuccessfulRefresh = now;

        } catch (error) {
            this.handleAutoRefreshError(error);
        }
    }

    /**
     * Handle auto-refresh errors with backoff strategy
     * @param {Error} error - The error that occurred
     */
    handleAutoRefreshError(error) {
        this.consecutiveErrors++;
        this.performanceMetrics.errorCount++;

        console.warn(`Auto-refresh error (${this.consecutiveErrors}/${this.maxConsecutiveErrors}):`, error.message);

        // Apply exponential backoff
        if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
            this.refreshBackoffMultiplier = Math.min(
                this.refreshBackoffMultiplier * 2,
                this.maxBackoffMultiplier
            );

            // Restart with backoff
            this.startAutoRefresh();

            // Show user notification for persistent errors
            if (this.refreshBackoffMultiplier >= 4) {
                this.showNotification(
                    'Auto-refresh experiencing issues. Retrying with reduced frequency.',
                    'warning',
                    5000,
                    {
                        helpText: 'Check your network connection or API configuration'
                    }
                );
            }
        }

        // Stop auto-refresh if too many consecutive errors
        if (this.consecutiveErrors >= this.maxConsecutiveErrors * 2) {
            this.stopAutoRefresh();
            this.showNotification(
                'Auto-refresh disabled due to persistent errors',
                'error',
                0,
                {
                    customActions: [{
                        text: 'Retry Now',
                        action: () => {
                            this.consecutiveErrors = 0;
                            this.refreshBackoffMultiplier = 1;
                            this.startAutoRefresh();
                        },
                        primary: true
                    }]
                }
            );
        }
    }

    /**
     * Update auto-refresh UI indicators
     * @param {boolean} isActive - Whether auto-refresh is active
     */
    updateAutoRefreshUI(isActive) {
        const toggle = document.getElementById('auto-refresh-acronis-toggle');
        if (toggle && toggle.checked !== isActive) {
            toggle.checked = isActive;
        }

        // Update status indicator if it exists
        const statusIndicator = document.getElementById('auto-refresh-status');
        if (statusIndicator) {
            statusIndicator.textContent = isActive ?
                `Active (${this.refreshRate / 1000}s)` :
                'Inactive';
            statusIndicator.className = `status-indicator ${isActive ? 'status-online' : 'status-offline'}`;
        }
    }

    /**
     * Handle tab activation with enhanced resource management
     * @param {string} previousTab - The previously active tab
     */
    onTabActivated(previousTab = null) {
        this.isActive = true;

        console.log(`Acronis tab activated (from: ${previousTab || 'unknown'})`);

        // If we're switching from acronis to acronis (view change), don't reload data
        if (previousTab === 'acronis') {
            console.log('Internal view change detected, skipping data reload');
            // Still start auto-refresh if needed
            const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
            if (autoRefreshToggle && autoRefreshToggle.checked) {
                this.startAutoRefresh();
            }
            return;
        }

        // Cancel any pending requests from other tabs
        this.cancelPendingRequests();

        // Start auto-refresh if enabled
        const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
        if (autoRefreshToggle && autoRefreshToggle.checked) {
            this.startAutoRefresh();
        }

        // Load data based on current view and staleness
        const shouldRefreshData = this.shouldRefreshOnActivation();

        if (this.currentView === 'dashboard') {
            if (this.agents.length === 0 || shouldRefreshData) {
                // Load data silently when tab is activated
                this.loadInitialData(true);
            }
        } else if (this.currentView === 'details' && this.currentAgentId) {
            if (shouldRefreshData) {
                this.refreshAgentDetails();
            }
        }

        // Update performance metrics
        this.performanceMetrics.requestCount = 0;
        this.performanceMetrics.errorCount = 0;

        // Show connection status
        this.updateConnectionStatus();
    }

    /**
     * Handle tab deactivation with comprehensive cleanup
     * @param {string} newTab - The newly activated tab
     */
    onTabDeactivated(newTab = null) {
        this.isActive = false;

        console.log(`Acronis tab deactivated (to: ${newTab || 'unknown'})`);

        // Stop all refresh operations
        this.stopAutoRefresh();

        // Cancel pending requests to free up resources
        this.cancelPendingRequests();

        // Clear any retry timeouts
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
            this.retryTimeout = null;
        }

        // Clear all refresh timeouts
        this.refreshTimeouts.forEach(timeout => clearTimeout(timeout));
        this.refreshTimeouts.clear();

        // Hide any loading indicators
        this.hideAllLoadingIndicators();

        // Log performance metrics
        this.logPerformanceMetrics();
    }

    /**
     * Determine if data should be refreshed on tab activation
     * @returns {boolean} Whether data should be refreshed
     */
    shouldRefreshOnActivation() {
        // Always refresh if no successful refresh yet
        if (!this.performanceMetrics.lastSuccessfulRefresh) {
            return true;
        }

        // Refresh if data is older than refresh interval
        const dataAge = Date.now() - this.performanceMetrics.lastSuccessfulRefresh;
        return dataAge > this.refreshRate;
    }

    /**
     * Cancel all pending requests
     */
    cancelPendingRequests() {
        this.activeRequests.forEach((controller, requestId) => {
            try {
                controller.abort();
                console.debug(`Cancelled request: ${requestId}`);
            } catch (error) {
                console.warn(`Failed to cancel request ${requestId}:`, error);
            }
        });
        this.activeRequests.clear();
    }

    /**
     * Hide all loading indicators
     */
    hideAllLoadingIndicators() {
        // Hide main loading indicators
        this.showLoadingState('agents', false);
        this.showLoadingState('backup statistics', false);
        this.showAgentsLoading(false);
        this.showBackupsLoading(false);
        this.showRefreshIndicator(false);

        // Remove any loading notifications
        if (window.notificationSystem && window.notificationSystem.remove) {
            ['acronis-loading-agents', 'acronis-loading-backup-statistics', 'acronis-refresh'].forEach(id => {
                window.notificationSystem.remove(id);
            });
        }
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus() {
        // This will be called when tab is activated to show current status
        // The actual status will be updated by API calls
    }

    /**
     * Log performance metrics for debugging
     */
    logPerformanceMetrics() {
        if (this.performanceMetrics.requestCount > 0) {
            console.log('Acronis Performance Metrics:', {
                requests: this.performanceMetrics.requestCount,
                errors: this.performanceMetrics.errorCount,
                errorRate: `${((this.performanceMetrics.errorCount / this.performanceMetrics.requestCount) * 100).toFixed(1)}%`,
                avgResponseTime: `${this.performanceMetrics.averageResponseTime}ms`,
                lastSuccess: this.performanceMetrics.lastSuccessfulRefresh ?
                    new Date(this.performanceMetrics.lastSuccessfulRefresh).toLocaleTimeString() : 'Never',
                consecutiveErrors: this.consecutiveErrors,
                backoffMultiplier: this.refreshBackoffMultiplier
            });
        }
    }

    /**
     * Handle app pause (mobile) with resource cleanup
     */
    onAppPaused() {
        console.log('App paused - stopping Acronis operations');
        this.stopAutoRefresh();
        this.cancelPendingRequests();

        // Clear any retry timeouts
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
            this.retryTimeout = null;
        }
    }

    /**
     * Handle app resume (mobile) with smart restart
     */
    onAppResumed() {
        console.log('App resumed - checking Acronis state');

        if (this.isActive) {
            const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
            if (autoRefreshToggle && autoRefreshToggle.checked) {
                // Reset error tracking on resume
                this.consecutiveErrors = 0;
                this.refreshBackoffMultiplier = 1;
                this.startAutoRefresh();

                // Refresh data if it's stale
                if (this.shouldRefreshOnActivation()) {
                    if (this.currentView === 'dashboard') {
                        // Load silently when page becomes visible
                        this.loadInitialData(true);
                    } else if (this.currentView === 'details' && this.currentAgentId) {
                        this.refreshAgentDetails();
                    }
                }
            }
        }
    }

    /**
     * Handle page hidden event
     */
    onPageHidden() {
        console.log('Page hidden - pausing Acronis operations');
        this.stopAutoRefresh();
        this.cancelPendingRequests();
    }

    /**
     * Handle page visible event
     */
    onPageVisible() {
        console.log('Page visible - resuming Acronis operations');

        if (this.isActive) {
            const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
            if (autoRefreshToggle && autoRefreshToggle.checked) {
                this.startAutoRefresh();
            }
        }
    }

    /**
     * Handle network online event
     */
    onNetworkOnline() {
        console.log('Network online - resuming Acronis operations');

        if (this.isActive) {
            // Reset error tracking
            this.consecutiveErrors = 0;
            this.refreshBackoffMultiplier = 1;

            // Restart auto-refresh if enabled
            const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
            if (autoRefreshToggle && autoRefreshToggle.checked) {
                this.startAutoRefresh();
            }

            // Show reconnection notification
            this.showNotification('Network connection restored', 'success', 3000);
        }
    }

    /**
     * Handle network offline event
     */
    onNetworkOffline() {
        console.log('Network offline - stopping Acronis operations');

        this.stopAutoRefresh();
        this.cancelPendingRequests();

        // Show offline notification
        this.showNotification('Network connection lost. Auto-refresh paused.', 'warning', 0, {
            persistent: true,
            id: 'acronis-offline'
        });
    }

    /**
     * Comprehensive cleanup method
     */
    cleanup() {
        console.log('Cleaning up Acronis resources');

        // Stop all operations
        this.stopAutoRefresh();
        this.cancelPendingRequests();

        // Clear all timeouts
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
            this.retryTimeout = null;
        }

        this.refreshTimeouts.forEach(timeout => clearTimeout(timeout));
        this.refreshTimeouts.clear();

        // Clear data to free memory
        this.agents = [];
        this.statistics = {};

        // Reset state
        this.isActive = false;
        this.currentAgentId = null;
        this.consecutiveErrors = 0;
        this.refreshBackoffMultiplier = 1;
        this.lastRefreshTime = null;

        // Clear performance metrics
        this.performanceMetrics = {
            requestCount: 0,
            errorCount: 0,
            averageResponseTime: 0,
            lastSuccessfulRefresh: null
        };
    }

    /**
     * Make HTTP request to API with enhanced resource management
     * @param {string} method - HTTP method
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @returns {Promise} Response promise
     */
    async makeRequest(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // Create abort controller for this request
        const controller = new AbortController();
        this.activeRequests.set(requestId, controller);

        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-Request-ID': requestId
            },
            signal: controller.signal
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }

        // Log request details
        console.debug(`Making ${method} request to ${url}`, {
            requestId,
            endpoint,
            hasData: !!data,
            timestamp: new Date().toISOString(),
            activeRequests: this.activeRequests.size
        });

        let response;
        let result;
        const startTime = Date.now();

        // Update performance metrics
        this.performanceMetrics.requestCount++;

        try {
            response = await fetch(url, options);
            const duration = Date.now() - startTime;

            // Update performance metrics
            this.updatePerformanceMetrics(duration, true);

            // Log response timing
            console.debug(`Response received for ${method} ${endpoint}`, {
                requestId,
                status: response.status,
                duration: `${duration}ms`,
                ok: response.ok,
                remainingRequests: this.activeRequests.size - 1
            });

            const contentType = response.headers.get('content-type');

            if (contentType && contentType.includes('application/json')) {
                try {
                    result = await response.json();
                } catch (jsonError) {
                    console.error('Failed to parse JSON response:', jsonError);
                    throw new Error(`Invalid JSON response from server: ${jsonError.message}`);
                }
            } else {
                const textResponse = await response.text();
                result = { message: textResponse };

                if (!response.ok) {
                    console.warn(`Non-JSON error response for ${method} ${endpoint}:`, textResponse);
                }
            }

            if (!response.ok) {
                // Create enhanced error with response data
                const errorMessage = result.error || result.message || `HTTP ${response.status}: ${response.statusText}`;
                const error = new Error(errorMessage);
                error.status = response.status;
                error.response = result;
                error.requestId = requestId;
                error.duration = duration;
                error.url = url;
                error.method = method;

                // Add network error context
                if (response.status === 0) {
                    error.networkError = true;
                    error.message = 'Network error - please check your internet connection';
                } else if (response.status >= 500) {
                    error.serverError = true;
                } else if (response.status >= 400) {
                    error.clientError = true;
                }

                console.error(`Request failed: ${method} ${endpoint}`, {
                    requestId,
                    status: response.status,
                    error: errorMessage,
                    duration: `${duration}ms`,
                    response: result
                });

                throw error;
            }

            // Log successful request
            if (duration > 5000) {
                console.warn(`Slow request: ${method} ${endpoint} took ${duration}ms`, {
                    requestId,
                    duration: `${duration}ms`
                });
            }

            return result;

        } catch (error) {
            const duration = Date.now() - startTime;

            // Update performance metrics for errors
            this.updatePerformanceMetrics(duration, false);

            // Handle different types of errors
            if (error.name === 'AbortError') {
                // Check if this was a manual cancellation or timeout
                const wasManualCancel = !this.activeRequests.has(requestId);

                if (wasManualCancel) {
                    console.debug(`Request cancelled: ${method} ${endpoint}`, { requestId });
                    const cancelError = new Error(`Request cancelled: ${method} ${endpoint}`);
                    cancelError.cancelled = true;
                    cancelError.requestId = requestId;
                    throw cancelError;
                } else {
                    const timeoutError = new Error(`Request timeout: ${method} ${endpoint}`);
                    timeoutError.timeout = true;
                    timeoutError.requestId = requestId;
                    timeoutError.duration = duration;
                    timeoutError.url = url;
                    timeoutError.method = method;

                    console.error('Request timeout:', {
                        requestId,
                        method,
                        endpoint,
                        duration: `${duration}ms`
                    });

                    throw timeoutError;
                }
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                // Network error
                const networkError = new Error(`Network error: Unable to connect to ${url}`);
                networkError.networkError = true;
                networkError.requestId = requestId;
                networkError.duration = duration;
                networkError.url = url;
                networkError.method = method;

                console.error('Network error:', {
                    requestId,
                    method,
                    endpoint,
                    duration: `${duration}ms`,
                    originalError: error.message
                });

                throw networkError;
            } else if (!error.status) {
                // Enhance error with request context if not already present
                error.requestId = requestId;
                error.duration = duration;
                error.url = url;
                error.method = method;

                console.error(`Request error: ${method} ${endpoint}`, {
                    requestId,
                    duration: `${duration}ms`,
                    error: error.message,
                    type: error.name
                });
            }

            throw error;
        } finally {
            // Always clean up the request tracking
            this.activeRequests.delete(requestId);
        }
    }

    /**
     * Update performance metrics
     * @param {number} duration - Request duration in milliseconds
     * @param {boolean} success - Whether the request was successful
     */
    updatePerformanceMetrics(duration, success) {
        if (!success) {
            this.performanceMetrics.errorCount++;
        }

        // Update average response time using exponential moving average
        if (this.performanceMetrics.averageResponseTime === 0) {
            this.performanceMetrics.averageResponseTime = duration;
        } else {
            const alpha = 0.1; // Smoothing factor
            this.performanceMetrics.averageResponseTime =
                (alpha * duration) + ((1 - alpha) * this.performanceMetrics.averageResponseTime);
        }
    }

    /**
     * Handle API errors with comprehensive error categorization and user feedback
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     * @param {Object} context - Additional context for error handling
     */
    handleError(error, operation, context = {}) {
        const errorContext = {
            module: 'acronis',
            currentView: this.currentView,
            agentCount: this.agents.length,
            isActive: this.isActive,
            agentId: this.currentAgentId,
            ...context
        };

        // Parse error response if available
        let errorData = null;
        let errorMessage = error.message || 'An unexpected error occurred';
        let errorCode = null;
        let recoverable = true;
        let retryAfter = null;
        let troubleshootingSteps = [];
        let recoverySuggestions = [];

        try {
            if (error.response && typeof error.response === 'object') {
                errorData = error.response;
                errorMessage = errorData.error || errorMessage;
                errorCode = errorData.error_code;
                recoverable = errorData.recoverable !== false;
                retryAfter = errorData.retry_after;
                troubleshootingSteps = errorData.troubleshooting_steps || [];
                recoverySuggestions = errorData.recovery_suggestions || [];
            }
        } catch (e) {
            console.warn('Failed to parse error response:', e);
        }

        // Log error with context
        console.error(`Acronis Error [${operation}]:`, {
            error: errorMessage,
            errorCode,
            recoverable,
            retryAfter,
            context: errorContext,
            originalError: error
        });

        // Use global error handler if available, otherwise handle locally
        if (window.globalErrorHandler) {
            const retryCallback = this.getRetryCallback(operation);
            window.globalErrorHandler.handleApiError(error, operation, errorContext, retryCallback);
        } else {
            // Enhanced local error handling
            this.handleCategorizedError(errorCode, errorMessage, operation, {
                recoverable,
                retryAfter,
                troubleshootingSteps,
                recoverySuggestions,
                context: errorContext
            });
        }
    }

    /**
     * Get retry callback for specific operations
     * @param {string} operation - Operation that failed
     * @returns {Function|null} Retry callback function
     */
    getRetryCallback(operation) {
        const retryCallbacks = {
            'load backup statistics': () => this.loadStatistics(),
            'load agents': () => this.loadAgents(),
            'load agent details': () => this.loadAgentDetails(this.currentAgentId),
            'load agent backups': () => this.loadAgentBackups(this.currentAgentId),
            'refresh data': () => this.refreshData(),
            'refresh agent details': () => this.refreshAgentDetails()
        };

        return retryCallbacks[operation] || null;
    }

    /**
     * Handle categorized errors with specific user feedback
     * @param {string} errorCode - Error code
     * @param {string} errorMessage - Error message
     * @param {string} operation - Operation that failed
     * @param {Object} options - Error handling options
     */
    handleCategorizedError(errorCode, errorMessage, operation, options = {}) {
        const { recoverable, retryAfter, troubleshootingSteps, recoverySuggestions, context } = options;

        let notificationType = 'error';
        let notificationDuration = 0; // Persistent by default
        let showRetryButton = recoverable;
        let customActions = [];

        // Handle specific error codes
        switch (errorCode) {
            case 'ACRONIS_NOT_CONFIGURED':
                notificationType = 'warning';
                showRetryButton = false;
                customActions = [{
                    text: 'Configure Now',
                    action: () => this.showConfigurationView(),
                    primary: true
                }];
                this.showConnectionStatus(false, 'Configuration required');
                break;

            case 'ACRONIS_AUTH_ERROR':
            case 'ACRONIS_INVALID_CREDENTIALS':
                notificationType = 'error';
                showRetryButton = false;
                customActions = [{
                    text: 'Check Configuration',
                    action: () => this.showConfigurationView(),
                    primary: true
                }];
                this.showConnectionStatus(false, 'Authentication failed');
                break;

            case 'ACRONIS_CONNECTION_ERROR':
            case 'ACRONIS_TIMEOUT':
                notificationType = 'warning';
                notificationDuration = 10000;
                if (retryAfter) {
                    customActions = [{
                        text: `Retry in ${retryAfter}s`,
                        action: () => this.scheduleRetry(operation, retryAfter),
                        primary: true
                    }];
                }
                this.showConnectionStatus(false, 'Connection failed');
                break;

            case 'ACRONIS_RATE_LIMIT':
                notificationType = 'warning';
                notificationDuration = (retryAfter || 60) * 1000;
                showRetryButton = false;
                if (retryAfter) {
                    customActions = [{
                        text: `Wait ${retryAfter}s`,
                        action: () => this.scheduleRetry(operation, retryAfter),
                        primary: true
                    }];
                }
                this.showConnectionStatus(false, 'Rate limited');
                break;

            case 'ACRONIS_CIRCUIT_BREAKER_OPEN':
                notificationType = 'error';
                showRetryButton = false;
                if (retryAfter) {
                    customActions = [{
                        text: `Service recovering (${Math.ceil(retryAfter / 60)}min)`,
                        action: () => this.scheduleRetry(operation, retryAfter),
                        primary: true
                    }];
                }
                this.showConnectionStatus(false, 'Service unavailable');
                break;

            case 'ACRONIS_SERVER_ERROR':
                notificationType = 'error';
                notificationDuration = 15000;
                this.showConnectionStatus(false, 'Server error');
                break;

            default:
                // Generic error handling
                if (recoverable) {
                    notificationType = 'warning';
                    notificationDuration = 10000;
                } else {
                    notificationType = 'error';
                }
                this.showConnectionStatus(false, 'Error occurred');
        }

        // Add retry button if needed
        if (showRetryButton && !customActions.length) {
            customActions.push({
                text: 'Retry',
                action: () => this.retryOperation(operation),
                primary: true
            });
        }

        // Show notification with enhanced error information
        this.showNotification(
            this.getUserFriendlyErrorMessage(errorCode, errorMessage, operation),
            notificationType,
            notificationDuration,
            {
                errorCode,
                operation,
                recoverable,
                retryAfter,
                troubleshootingSteps,
                recoverySuggestions,
                customActions,
                context
            }
        );

        // Handle fallback behavior
        this.handleErrorFallback(errorCode, operation, context);
    }

    /**
     * Get user-friendly error message
     * @param {string} errorCode - Error code
     * @param {string} errorMessage - Original error message
     * @param {string} operation - Operation that failed
     * @returns {string} User-friendly error message
     */
    getUserFriendlyErrorMessage(errorCode, errorMessage, operation) {
        const operationNames = {
            'load agents': 'loading agents',
            'load backup statistics': 'loading backup statistics',
            'load agent backups': 'loading backup details',
            'refresh data': 'refreshing data',
            'test connection': 'testing connection'
        };

        const friendlyOperation = operationNames[operation] || operation;

        const errorMessages = {
            'ACRONIS_NOT_CONFIGURED': 'Acronis is not configured. Please set up your API credentials.',
            'ACRONIS_AUTH_ERROR': 'Authentication failed. Please check your API credentials.',
            'ACRONIS_INVALID_CREDENTIALS': 'Invalid API credentials. Please verify your Client ID and Secret.',
            'ACRONIS_CONNECTION_ERROR': `Connection failed while ${friendlyOperation}. Please check your network connection.`,
            'ACRONIS_TIMEOUT': `Request timed out while ${friendlyOperation}. The server may be slow to respond.`,
            'ACRONIS_RATE_LIMIT': `Too many requests while ${friendlyOperation}. Please wait before trying again.`,
            'ACRONIS_CIRCUIT_BREAKER_OPEN': 'Acronis service is temporarily unavailable. Please wait for it to recover.',
            'ACRONIS_SERVER_ERROR': `Server error occurred while ${friendlyOperation}. Please try again later.`,
            'ACRONIS_INSUFFICIENT_PERMISSIONS': 'Your API credentials do not have sufficient permissions for this operation.'
        };

        return errorMessages[errorCode] || `Failed to ${friendlyOperation}: ${errorMessage}`;
    }

    /**
     * Handle error fallback behavior
     * @param {string} errorCode - Error code
     * @param {string} operation - Operation that failed
     * @param {Object} context - Error context
     */
    handleErrorFallback(errorCode, operation, context) {
        // Stop auto-refresh on persistent errors
        if (['ACRONIS_NOT_CONFIGURED', 'ACRONIS_AUTH_ERROR', 'ACRONIS_CIRCUIT_BREAKER_OPEN'].includes(errorCode)) {
            this.stopAutoRefresh();

            // Update auto-refresh toggle
            const autoRefreshToggle = document.getElementById('auto-refresh-acronis-toggle');
            if (autoRefreshToggle) {
                autoRefreshToggle.checked = false;
            }
        }

        // Show appropriate empty states
        if (operation === 'load agents') {
            this.showAgentsEmptyState();
        } else if (operation === 'load backup statistics') {
            this.showEmptyStatistics();
        } else if (operation === 'load agent backups') {
            this.showBackupsEmptyState();
        }
    }

    /**
     * Schedule a retry operation
     * @param {string} operation - Operation to retry
     * @param {number} delaySeconds - Delay in seconds
     */
    scheduleRetry(operation, delaySeconds) {
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
        }

        this.retryTimeout = setTimeout(() => {
            this.retryOperation(operation);
        }, delaySeconds * 1000);

        // Show countdown notification
        this.showRetryCountdown(operation, delaySeconds);
    }

    /**
     * Show retry countdown
     * @param {string} operation - Operation being retried
     * @param {number} seconds - Seconds until retry
     */
    showRetryCountdown(operation, seconds) {
        let remainingSeconds = seconds;

        const countdownId = this.showNotification(
            `Retrying ${operation} in ${remainingSeconds} seconds...`,
            'info',
            0,
            {
                id: 'acronis-retry-countdown',
                showSpinner: true
            }
        );

        const countdownInterval = setInterval(() => {
            remainingSeconds--;

            if (remainingSeconds > 0) {
                // Update notification text if system supports it
                if (window.notificationSystem && window.notificationSystem.update) {
                    window.notificationSystem.update('acronis-retry-countdown',
                        `Retrying ${operation} in ${remainingSeconds} seconds...`);
                }
            } else {
                clearInterval(countdownInterval);

                // Remove countdown notification
                if (window.notificationSystem && window.notificationSystem.remove) {
                    window.notificationSystem.remove('acronis-retry-countdown');
                }
            }
        }, 1000);
    }

    /**
     * Retry a failed operation
     * @param {string} operation - Operation to retry
     */
    retryOperation(operation) {
        console.log(`Retrying operation: ${operation}`);

        switch (operation) {
            case 'load agents':
                this.loadAgents();
                break;
            case 'load backup statistics':
                this.loadStatistics();
                break;
            case 'load agent backups':
                if (this.currentAgentId) {
                    this.loadAgentBackups(this.currentAgentId);
                }
                break;
            case 'refresh data':
                this.refreshData();
                break;
            case 'test connection':
                if (window.acronisConfigManager) {
                    window.acronisConfigManager.testConnection();
                }
                break;
            default:
                console.warn(`Unknown operation for retry: ${operation}`);
        }
    }

    /**
     * Basic error handling fallback
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     */
    handleBasicError(error, operation) {
        let message = `Failed to ${operation}`;

        if (error.message) {
            if (error.message.includes('timeout')) {
                message += ': Request timeout. Please check your connection.';
            } else if (error.message.includes('Authentication failed')) {
                message += ': Authentication failed. Please check your API credentials.';
            } else if (error.message.includes('Connection failed')) {
                message += ': Cannot connect to Acronis server. Please check the server status.';
            } else {
                message += `: ${error.message}`;
            }
        }

        this.showNotification(message, 'error', 0); // Persistent error notifications
        console.error(`Acronis API Error [${operation}]:`, error);
    }

    /**
     * Show notification message with enhanced system integration
     * @param {string} message - Message text
     * @param {string} type - Message type
     * @param {number} duration - Display duration
     * @param {Object} options - Additional options
     */
    showNotification(message, type = 'info', duration = 5000, options = {}) {
        // Use enhanced notification system if available
        if (window.notificationSystem) {
            const notificationOptions = {
                ...options,
                module: 'acronis'
            };

            switch (type) {
                case 'success':
                    return window.notificationSystem.showSuccess(message, { duration, ...notificationOptions });
                case 'error':
                    return window.notificationSystem.showError(message, {
                        persistent: duration === 0,
                        duration: duration || 10000,
                        ...notificationOptions
                    });
                case 'warning':
                    return window.notificationSystem.showWarning(message, { duration, ...notificationOptions });
                case 'info':
                default:
                    return window.notificationSystem.showInfo(message, { duration, ...notificationOptions });
            }
        } else {
            // Fallback to console logging
            console.log(`[ACRONIS ${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Show loading state with status indicator
     * @param {string} operation - Operation being performed
     * @param {boolean} show - Whether to show loading state
     */
    showLoadingState(operation, show) {
        if (show) {
            this.showNotification(`Loading ${operation}...`, 'info', 0, {
                showSpinner: true,
                id: `acronis-loading-${operation.replace(/\s+/g, '-')}`
            });
        } else {
            // Hide loading notification if notification system supports it
            if (window.notificationSystem && window.notificationSystem.remove) {
                const loadingId = `acronis-loading-${operation.replace(/\s+/g, '-')}`;
                window.notificationSystem.remove(loadingId);
            }
        }
    }

    /**
     * Show connection status indicator
     * @param {boolean} isConnected - Whether Acronis API is connected
     * @param {string} message - Status message
     */
    showConnectionStatus(isConnected, message = null) {
        const statusMessage = message || (isConnected ?
            'Connected to Acronis API' :
            'Disconnected from Acronis API');

        const type = isConnected ? 'success' : 'warning';
        const duration = isConnected ? 3000 : 0; // Persistent for disconnected state

        this.showNotification(statusMessage, type, duration, {
            connectionStatus: true,
            persistent: !isConnected
        });
    }

    // Utility Methods

    /**
     * Get CSS class for status
     * @param {string} status - Status value
     * @returns {string} CSS class
     */
    getStatusClass(status) {
        const statusClasses = {
            'online': 'status-online',
            'offline': 'status-offline',
            'connected': 'status-online',
            'disconnected': 'status-offline'
        };

        return statusClasses[status] || 'status-unknown';
    }

    /**
     * Get CSS class for backup state
     * @param {string} state - Backup state
     * @returns {string} CSS class
     */
    getBackupStateClass(state) {
        const stateClasses = {
            'completed': 'state-completed',
            'running': 'state-running',
            'failed': 'state-failed',
            'cancelled': 'state-cancelled'
        };

        return stateClasses[state] || 'state-unknown';
    }

    /**
     * Get CSS class for backup result
     * @param {string} result - Backup result
     * @returns {string} CSS class
     */
    getBackupResultClass(result) {
        const resultClasses = {
            'ok': 'result-success',
            'success': 'result-success',
            'failed': 'result-error',
            'error': 'result-error',
            'warning': 'result-warning'
        };

        return resultClasses[result] || 'result-unknown';
    }

    /**
     * Format bytes to human readable string
     * @param {number} bytes - Bytes value
     * @returns {string} Formatted string
     */
    formatBytes(bytes) {
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
     * Calculate duration between two timestamps
     * @param {string} startTime - Start timestamp
     * @param {string} endTime - End timestamp
     * @returns {string} Duration string
     */
    calculateDuration(startTime, endTime) {
        try {
            const start = new Date(startTime.replace(/(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2}):(\d{2})/, '$3-$2-$1T$4:$5:$6'));
            const end = new Date(endTime.replace(/(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2}):(\d{2})/, '$3-$2-$1T$4:$5:$6'));

            const diffMs = end - start;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMins / 60);

            if (diffHours > 0) {
                return `${diffHours}h ${diffMins % 60}m`;
            } else {
                return `${diffMins}m`;
            }
        } catch (error) {
            return '--';
        }
    }

    /**
     * Perform memory cleanup for long-running sessions
     */
    performMemoryCleanup() {
        console.log('Performing Acronis memory cleanup');

        // Clear old performance metrics if they're getting too large
        if (this.performanceMetrics.requestCount > 1000) {
            this.performanceMetrics.requestCount = Math.floor(this.performanceMetrics.requestCount / 2);
            this.performanceMetrics.errorCount = Math.floor(this.performanceMetrics.errorCount / 2);
        }

        // Clear old agent data if we have too many agents
        if (this.agents.length > 100) {
            console.warn('Large number of agents detected, consider pagination');
        }

        // Force garbage collection if available (development only)
        if (window.gc && typeof window.gc === 'function') {
            try {
                window.gc();
                console.debug('Manual garbage collection triggered');
            } catch (e) {
                // Ignore errors - gc() might not be available
            }
        }
    }

    /**
     * Get current resource usage statistics
     * @returns {Object} Resource usage statistics
     */
    getResourceStats() {
        return {
            activeRequests: this.activeRequests.size,
            refreshTimeouts: this.refreshTimeouts.size,
            agentsCount: this.agents.length,
            isAutoRefreshActive: !!this.refreshInterval,
            consecutiveErrors: this.consecutiveErrors,
            backoffMultiplier: this.refreshBackoffMultiplier,
            performanceMetrics: { ...this.performanceMetrics },
            memoryUsage: this.estimateMemoryUsage()
        };
    }

    /**
     * Estimate memory usage (rough calculation)
     * @returns {Object} Estimated memory usage
     */
    estimateMemoryUsage() {
        const agentsSize = JSON.stringify(this.agents).length;
        const statisticsSize = JSON.stringify(this.statistics).length;
        const totalSize = agentsSize + statisticsSize;

        return {
            agents: `${Math.round(agentsSize / 1024)}KB`,
            statistics: `${Math.round(statisticsSize / 1024)}KB`,
            total: `${Math.round(totalSize / 1024)}KB`,
            activeRequests: this.activeRequests.size,
            timeouts: this.refreshTimeouts.size
        };
    }
}

// Initialize Acronis manager when DOM is ready
let acronisManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        acronisManager = new AcronisManager();
        window.acronisManager = acronisManager; // Make it globally accessible

        // Set up periodic memory cleanup for long-running sessions
        setInterval(() => {
            if (acronisManager && acronisManager.isActive) {
                acronisManager.performMemoryCleanup();
            }
        }, 300000); // Every 5 minutes
    });
} else {
    acronisManager = new AcronisManager();
    window.acronisManager = acronisManager; // Make it globally accessible

    // Set up periodic memory cleanup for long-running sessions
    setInterval(() => {
        if (acronisManager && acronisManager.isActive) {
            acronisManager.performMemoryCleanup();
        }
    }, 300000); // Every 5 minutes
}

// Export for use in other modules
window.AcronisManager = AcronisManager;
window.acronisManager = acronisManager;

// Add global method to check Acronis resource usage (for debugging)
window.getAcronisResourceStats = () => {
    return acronisManager ? acronisManager.getResourceStats() : null;
};