/**
 * Acronis Charts JavaScript Module
 * 
 * This module provides chart visualization functionality for the Acronis tab including:
 * - Pie chart functions for backup success/failure statistics
 * - Timeline chart for backup frequency visualization
 * - Chart rendering for individual agent backup statistics
 * - Integration with Google Charts library
 * 
 * Requirements covered:
 * - 3.2: Pie charts for backup success/failure statistics
 * - 3.3: Timeline chart for backup frequency visualization
 * - 4.3: Chart rendering for individual agent backup statistics
 * - 6.2: Chart styling integration with dashboard theme
 */

class AcronisCharts {
    constructor() {
        this.isGoogleChartsLoaded = false;
        this.chartsQueue = [];
        this.agentChartData = new Map();
        this.currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';

        this.init();
    }

    /**
     * Initialize the charts module
     */
    init() {
        this.loadGoogleCharts();
        this.setupThemeListener();

        console.log('Acronis Charts initialized');
    }

    /**
     * Load Google Charts library
     */
    loadGoogleCharts() {
        if (window.google && window.google.charts) {
            this.onGoogleChartsLoaded();
            return;
        }

        // Load Google Charts library with font loading disabled
        const script = document.createElement('script');
        script.src = 'https://www.gstatic.com/charts/loader.js';
        script.onload = () => {
            google.charts.load('current', {
                packages: ['corechart', 'timeline', 'bar'],
                // Disable automatic font loading to prevent errors
                'mapsApiKey': null,
                'language': 'en',
                'callback': null
            });
            google.charts.setOnLoadCallback(() => {
                this.onGoogleChartsLoaded();
            });
        };
        script.onerror = () => {
            console.error('Failed to load Google Charts library');
            this.showChartsError('Failed to load charts library');
        };

        document.head.appendChild(script);
    }

    /**
     * Handle Google Charts loaded event
     */
    onGoogleChartsLoaded() {
        this.isGoogleChartsLoaded = true;
        console.log('Google Charts loaded successfully');

        // Process any queued chart requests
        this.chartsQueue.forEach(chartRequest => {
            this.processChartRequest(chartRequest);
        });
        this.chartsQueue = [];
    }

    /**
     * Setup theme change listener
     */
    setupThemeListener() {
        // Listen for theme changes
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                    const newTheme = document.documentElement.getAttribute('data-theme');
                    if (newTheme !== this.currentTheme) {
                        this.currentTheme = newTheme;
                        this.refreshAllCharts();
                    }
                }
            });
        });

        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme']
        });
    }

    /**
     * Update charts with new data
     * @param {Object} backupData - Backup data from API
     */
    updateCharts(backupData) {
        if (!backupData) return;

        // Update main dashboard charts
        this.updateBackupSuccessChart(backupData.summary);
        this.updateBackupFrequencyChart(backupData.workload_data);

        // Store workload data for agent charts
        if (backupData.workload_data) {
            Object.entries(backupData.workload_data).forEach(([workloadId, data]) => {
                // Try to associate with agent data if available
                if (window.acronisManager && window.acronisManager.agents) {
                    const matchingAgent = window.acronisManager.agents.find(agent =>
                        agent.hostname === data.hostname ||
                        agent.id_tenant === data.id_tenant
                    );
                    if (matchingAgent) {
                        data.id_agent = matchingAgent.id_agent;
                    }
                }
                this.agentChartData.set(workloadId, data);
            });
        }
    }

    /**
     * Update backup success/failure pie chart
     * @param {Object} summary - Backup summary statistics
     */
    updateBackupSuccessChart(summary) {
        if (!summary) return;

        const successful = summary.success || 0;
        const failed = summary.failed || 0;
        const total = successful + failed;
        const successRate = total > 0 ? Math.round((successful / total) * 100) : 0;

        // Update the mini-stat display
        const successRateElement = document.getElementById('success-rate-percent');
        if (successRateElement) {
            successRateElement.textContent = `${successRate}%`;
        }

        const chartData = [
            ['Status', 'Count'],
            ['Successful', successful],
            ['Failed', failed]
        ];

        const options = {
            title: '',  // Remove title since we have it in the header
            backgroundColor: 'transparent',
            legend: {
                textStyle: this.getTextStyle(),
                position: 'bottom'
            },
            colors: ['#28a745', '#dc3545'],
            pieSliceText: 'percentage',
            pieSliceTextStyle: this.getTextStyle(),
            chartArea: {
                left: 20,
                top: 20,
                width: '90%',
                height: '80%'
            },
            tooltip: {
                textStyle: this.getTextStyle()
            }
        };

        this.renderChart('backup-success-chart', 'PieChart', chartData, options);
    }

    /**
     * Update backup frequency timeline chart
     * @param {Object} workloadData - Workload backup data
     */
    updateBackupFrequencyChart(workloadData) {
        if (!workloadData) return;

        // Process backup data to create frequency chart
        const frequencyData = this.processBackupFrequencyData(workloadData);

        if (frequencyData.length <= 1) {
            this.showEmptyChart('backup-frequency-chart', 'No backup frequency data available');
            return;
        }

        const options = {
            title: '',  // Remove title since we have it in the header
            backgroundColor: 'transparent',
            hAxis: {
                title: 'Date',
                titleTextStyle: this.getTextStyle(),
                textStyle: this.getTextStyle(),
                gridlines: {
                    color: this.getGridlineColor()
                }
            },
            vAxis: {
                title: 'Number of Backups',
                titleTextStyle: this.getTextStyle(),
                textStyle: this.getTextStyle(),
                gridlines: {
                    color: this.getGridlineColor()
                },
                minValue: 0
            },
            legend: {
                textStyle: this.getTextStyle(),
                position: 'none'
            },
            colors: ['#007bff'],
            chartArea: {
                left: 60,
                top: 50,
                width: '85%',
                height: '70%'
            },
            tooltip: {
                textStyle: this.getTextStyle()
            }
        };

        this.renderChart('backup-frequency-chart', 'ColumnChart', frequencyData, options);
    }

    /**
     * Render chart for individual agent
     * @param {string} agentId - Agent ID
     * @param {HTMLElement} container - Chart container element
     */
    renderAgentChart(agentId, container) {
        if (!container) {
            return;
        }

        // Ensure container has valid dimensions first
        this.ensureValidContainerDimensions(container);

        // Find workload data for this agent
        const workloadData = this.findWorkloadDataForAgent(agentId);

        if (!workloadData || !workloadData.backups || workloadData.backups.length === 0) {
            this.showNoBackupsMessage(container);
            return;
        }

        // Calculate success/failure statistics
        const stats = this.calculateBackupStats(workloadData.backups);

        const chartData = [
            ['Status', 'Count'],
            ['Successful', stats.success],
            ['Failed', stats.failed]
        ];

        // Get container dimensions for chart sizing
        const containerRect = container.getBoundingClientRect();
        const chartWidth = Math.max(200, containerRect.width - 20);
        const chartHeight = Math.max(150, containerRect.height - 20);

        const options = {
            backgroundColor: this.getBackgroundColor(),
            legend: {
                position: 'none'
            },
            colors: ['#28a745', '#dc3545'],
            pieSliceText: 'value',
            pieSliceTextStyle: {
                ...this.getTextStyle(),
                fontSize: 12
            },
            chartArea: {
                left: 10,
                top: 10,
                width: Math.max(180, chartWidth - 20),
                height: Math.max(130, chartHeight - 20)
            },
            tooltip: {
                textStyle: this.getTextStyle()
            },
            width: chartWidth,
            height: chartHeight
        };

        // Set unique chart ID for agent
        const chartId = `agent-chart-${agentId}`;
        container.setAttribute('id', chartId);

        this.renderChart(chartId, 'PieChart', chartData, options);
    }

    /**
     * Ensure container has valid dimensions
     * @param {HTMLElement} container - Chart container
     */
    ensureValidContainerDimensions(container) {
        if (!container) {
            return;
        }

        const rect = container.getBoundingClientRect();
        const computedStyle = window.getComputedStyle(container);

        // Check for invalid dimensions
        if (rect.width <= 0 || rect.height <= 0 ||
            parseFloat(computedStyle.width) <= 0 ||
            parseFloat(computedStyle.height) <= 0) {

            // Force valid dimensions
            container.style.width = '100%';
            container.style.height = '200px';
            container.style.minWidth = '200px';
            container.style.minHeight = '200px';
            container.style.display = 'block';
            container.style.visibility = 'visible';
            container.style.position = 'relative';

            console.warn(`Fixed invalid dimensions for container: ${container.id || 'unnamed'}`);
        }
    }

    /**
     * Process backup frequency data for timeline chart
     * @param {Object} workloadData - Workload backup data
     * @returns {Array} Processed frequency data
     */
    processBackupFrequencyData(workloadData) {
        const frequencyMap = new Map();

        // Process all workload backups
        Object.values(workloadData).forEach(workload => {
            if (workload.backups) {
                workload.backups.forEach(backup => {
                    if (backup.started_at) {
                        const date = this.extractDateFromTimestamp(backup.started_at);
                        if (date) {
                            const count = frequencyMap.get(date) || 0;
                            frequencyMap.set(date, count + 1);
                        }
                    }
                });
            }
        });

        // Convert to chart data format
        const chartData = [['Date', 'Backups']];

        // Sort dates and add to chart data
        const sortedDates = Array.from(frequencyMap.keys()).sort();
        sortedDates.forEach(date => {
            chartData.push([date, frequencyMap.get(date)]);
        });

        return chartData;
    }

    /**
     * Find workload data for specific agent
     * @param {string} agentId - Agent ID
     * @returns {Object|null} Workload data or null
     */
    findWorkloadDataForAgent(agentId) {
        // Try to find by agent ID in stored data
        for (const [workloadId, data] of this.agentChartData.entries()) {
            // Check if the workload data has an associated agent ID
            if (data.id_agent === agentId ||
                data.agent_id === agentId ||
                workloadId.includes(agentId) ||
                (data.hostname && window.acronisManager &&
                    window.acronisManager.agents.find(agent =>
                        agent.id_agent === agentId && agent.hostname === data.hostname))) {
                return data;
            }
        }
        return null;
    }

    /**
     * Calculate backup statistics
     * @param {Array} backups - Array of backup objects
     * @returns {Object} Statistics object
     */
    calculateBackupStats(backups) {
        const stats = {
            total: backups.length,
            success: 0,
            failed: 0
        };

        backups.forEach(backup => {
            if (backup.result === 'ok' || backup.result === 'success') {
                stats.success++;
            } else {
                stats.failed++;
            }
        });

        return stats;
    }

    /**
     * Extract date from timestamp string
     * @param {string} timestamp - Timestamp string
     * @returns {string|null} Date string or null
     */
    extractDateFromTimestamp(timestamp) {
        try {
            // Handle different timestamp formats
            let date;

            if (timestamp.includes('/')) {
                // Format: DD/MM/YYYY HH:mm:ss
                const parts = timestamp.split(' ')[0].split('/');
                if (parts.length === 3) {
                    date = new Date(parts[2], parts[1] - 1, parts[0]);
                }
            } else {
                // ISO format or other standard formats
                date = new Date(timestamp);
            }

            if (date && !isNaN(date.getTime())) {
                return date.toISOString().split('T')[0]; // Return YYYY-MM-DD format
            }
        } catch (error) {
            console.warn('Failed to parse timestamp:', timestamp, error);
        }

        return null;
    }

    /**
     * Render a chart
     * @param {string} containerId - Container element ID
     * @param {string} chartType - Google Charts chart type
     * @param {Array} data - Chart data
     * @param {Object} options - Chart options
     */
    renderChart(containerId, chartType, data, options) {
        if (!this.isGoogleChartsLoaded) {
            // Queue the chart for later rendering
            this.chartsQueue.push({
                containerId,
                chartType,
                data,
                options
            });
            return;
        }

        this.processChartRequest({
            containerId,
            chartType,
            data,
            options
        });
    }

    /**
     * Process a chart rendering request
     * @param {Object} chartRequest - Chart request object
     */
    processChartRequest(chartRequest) {
        const { containerId, chartType, data, options } = chartRequest;
        const container = document.getElementById(containerId);

        if (!container) {
            console.warn(`Chart container not found: ${containerId}`);
            return;
        }

        // Validate container dimensions before rendering
        const rect = container.getBoundingClientRect();
        const computedStyle = window.getComputedStyle(container);

        if (rect.width <= 0 || rect.height <= 0 ||
            parseFloat(computedStyle.width) <= 0 ||
            parseFloat(computedStyle.height) <= 0) {

            console.warn(`Invalid container dimensions for ${containerId}, fixing...`);

            // Force valid dimensions
            container.style.width = '100%';
            container.style.height = '200px';
            container.style.minWidth = '200px';
            container.style.minHeight = '200px';
            container.style.display = 'block';
            container.style.visibility = 'visible';

            // Retry after layout update
            setTimeout(() => {
                this.processChartRequest(chartRequest);
            }, 150);
            return;
        }

        try {
            // Clear loading state
            this.clearChartLoading(container);

            // Ensure options have valid dimensions
            const finalOptions = { ...options };
            if (!finalOptions.width || finalOptions.width <= 0) {
                finalOptions.width = Math.max(200, container.offsetWidth);
            }
            if (!finalOptions.height || finalOptions.height <= 0) {
                finalOptions.height = Math.max(150, container.offsetHeight);
            }

            // Create chart
            const chart = new google.visualization[chartType](container);
            const dataTable = google.visualization.arrayToDataTable(data);

            chart.draw(dataTable, finalOptions);

        } catch (error) {
            console.error(`Failed to render chart ${containerId}:`, error);
            this.showChartError(container, 'Failed to render chart');
        }
    }

    /**
     * Show empty chart message
     * @param {string} containerId - Container element ID
     * @param {string} message - Message to display
     */
    showEmptyChart(containerId, message = 'No data available') {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="chart-empty-state">
                <i class="fas fa-chart-pie"></i>
                <span>${message}</span>
            </div>
        `;
    }

    /**
     * Show chart error
     * @param {HTMLElement} container - Container element
     * @param {string} message - Error message
     */
    showChartError(container, message = 'Chart error') {
        if (!container) return;

        container.innerHTML = `
            <div class="chart-error-state">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
            </div>
        `;
    }

    /**
     * Show charts library error
     * @param {string} message - Error message
     */
    showChartsError(message) {
        const chartContainers = [
            'backup-success-chart',
            'backup-frequency-chart'
        ];

        chartContainers.forEach(containerId => {
            const container = document.getElementById(containerId);
            if (container) {
                this.showChartError(container, message);
            }
        });
    }

    /**
     * Show "No Backups" message for agent chart
     * @param {HTMLElement} container - Chart container
     */
    showNoBackupsMessage(container) {
        const noBackupsMsg = container.querySelector('.no-backups-message');
        if (noBackupsMsg) {
            noBackupsMsg.style.display = 'block';
        } else {
            container.innerHTML = `
                <div class="no-backups-message">
                    <i class="fas fa-info-circle"></i>
                    <span>No Backups</span>
                </div>
            `;
        }
    }

    /**
     * Clear chart loading state
     * @param {HTMLElement} container - Chart container
     */
    clearChartLoading(container) {
        const loading = container.querySelector('.chart-loading');
        if (loading) {
            loading.style.display = 'none';
        }
    }

    /**
     * Refresh all charts (useful for theme changes)
     */
    refreshAllCharts() {
        if (!this.isGoogleChartsLoaded) return;

        // Re-render main charts if data is available
        if (window.acronisManager && window.acronisManager.statistics) {
            this.updateBackupSuccessChart(window.acronisManager.statistics);
        }

        // Re-render agent charts
        this.agentChartData.forEach((data, workloadId) => {
            const agentId = data.id_agent;
            if (agentId) {
                const container = document.getElementById(`agent-chart-${agentId}`);
                if (container) {
                    this.renderAgentChart(agentId, container);
                }
            }
        });
    }

    // Theme-related methods

    /**
     * Get background color based on current theme
     * @returns {string} Background color
     */
    getBackgroundColor() {
        return this.currentTheme === 'dark' ? '#2d3748' : '#ffffff';
    }

    /**
     * Get text style based on current theme
     * @returns {Object} Text style object
     */
    getTextStyle() {
        return {
            color: this.currentTheme === 'dark' ? '#e2e8f0' : '#2d3748',
            fontSize: 12,
            fontName: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        };
    }

    /**
     * Get title style based on current theme
     * @returns {Object} Title style object
     */
    getTitleStyle() {
        return {
            color: this.currentTheme === 'dark' ? '#f7fafc' : '#1a202c',
            fontSize: 16,
            fontName: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            bold: true
        };
    }

    /**
     * Get gridline color based on current theme
     * @returns {string} Gridline color
     */
    getGridlineColor() {
        return this.currentTheme === 'dark' ? '#4a5568' : '#e2e8f0';
    }

    /**
     * Cleanup when component is destroyed
     */
    destroy() {
        this.chartsQueue = [];
        this.agentChartData.clear();
    }
}

// Initialize Acronis charts when DOM is ready
let acronisCharts;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        acronisCharts = new AcronisCharts();
        // Make the instance available globally
        window.acronisCharts = acronisCharts;
    });
} else {
    acronisCharts = new AcronisCharts();
    // Make the instance available globally
    window.acronisCharts = acronisCharts;
}

// Export class and instance for use in other modules
window.AcronisCharts = AcronisCharts;