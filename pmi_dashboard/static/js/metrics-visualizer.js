/**
 * Metrics Visualization Components
 * 
 * This module provides various visualization components for displaying metrics
 * including progress bars, gauges, charts, and other visual indicators.
 */

class MetricsVisualizer {
    constructor() {
        this.animationDuration = 300;
        this.init();
    }

    /**
     * Initialize the visualizer
     */
    init() {
        this.addVisualizationStyles();
        console.log('MetricsVisualizer initialized');
    }

    /**
     * Create a progress bar component
     * @param {Object} options - Configuration options
     * @returns {HTMLElement} Progress bar element
     */
    createProgressBar(options = {}) {
        const {
            value = 0,
            max = 100,
            label = '',
            showPercentage = true,
            showValue = false,
            size = 'medium',
            color = 'auto',
            animated = true,
            striped = false,
            className = ''
        } = options;

        const percentage = Math.min(100, Math.max(0, (value / max) * 100));
        const colorClass = color === 'auto' ? this.getProgressColor(percentage) : `bg-${color}`;

        const progressBar = document.createElement('div');
        progressBar.className = `progress-bar-container ${size} ${className}`;

        progressBar.innerHTML = `
            <div class="progress-bar-wrapper">
                ${label ? `<div class="progress-label">${label}</div>` : ''}
                <div class="progress-track">
                    <div class="progress-fill ${colorClass} ${animated ? 'animated' : ''} ${striped ? 'striped' : ''}" 
                         style="width: ${percentage}%"
                         data-value="${value}"
                         data-percentage="${percentage.toFixed(1)}">
                    </div>
                </div>
                <div class="progress-info">
                    ${showPercentage ? `<span class="progress-percentage">${percentage.toFixed(1)}%</span>` : ''}
                    ${showValue ? `<span class="progress-value">${this.formatValue(value, max)}</span>` : ''}
                </div>
            </div>
        `;

        return progressBar;
    }

    /**
     * Create a circular gauge component
     * @param {Object} options - Configuration options
     * @returns {HTMLElement} Gauge element
     */
    createGauge(options = {}) {
        const {
            value = 0,
            max = 100,
            label = '',
            size = 100,
            strokeWidth = 8,
            color = 'auto',
            showValue = true,
            animated = true,
            className = ''
        } = options;

        const percentage = Math.min(100, Math.max(0, (value / max) * 100));
        const colorClass = color === 'auto' ? this.getProgressColor(percentage) : color;
        
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const strokeDasharray = circumference;
        const strokeDashoffset = circumference - (percentage / 100) * circumference;

        const gauge = document.createElement('div');
        gauge.className = `gauge-container ${className}`;
        gauge.style.width = `${size}px`;
        gauge.style.height = `${size}px`;

        gauge.innerHTML = `
            <svg class="gauge-svg" width="${size}" height="${size}">
                <!-- Background circle -->
                <circle
                    class="gauge-background"
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                    stroke-width="${strokeWidth}"
                    fill="none"
                />
                <!-- Progress circle -->
                <circle
                    class="gauge-progress ${colorClass} ${animated ? 'animated' : ''}"
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                    stroke-width="${strokeWidth}"
                    fill="none"
                    stroke-dasharray="${strokeDasharray}"
                    stroke-dashoffset="${strokeDashoffset}"
                    transform="rotate(-90 ${size / 2} ${size / 2})"
                    data-value="${value}"
                    data-percentage="${percentage.toFixed(1)}"
                />
            </svg>
            <div class="gauge-content">
                ${showValue ? `<div class="gauge-value">${percentage.toFixed(1)}%</div>` : ''}
                ${label ? `<div class="gauge-label">${label}</div>` : ''}
            </div>
        `;

        return gauge;
    }

    /**
     * Create a metric card component
     * @param {Object} options - Configuration options
     * @returns {HTMLElement} Metric card element
     */
    createMetricCard(options = {}) {
        const {
            title = '',
            value = 0,
            max = 100,
            unit = '%',
            icon = '',
            trend = null, // 'up', 'down', 'stable'
            trendValue = null,
            color = 'auto',
            size = 'medium',
            showProgress = true,
            className = ''
        } = options;

        const percentage = Math.min(100, Math.max(0, (value / max) * 100));
        const colorClass = color === 'auto' ? this.getProgressColor(percentage) : color;

        const card = document.createElement('div');
        card.className = `metric-card ${size} ${className}`;

        const trendIcon = trend ? this.getTrendIcon(trend) : '';
        const trendClass = trend ? `trend-${trend}` : '';

        card.innerHTML = `
            <div class="metric-card-header">
                ${icon ? `<div class="metric-icon"><i class="${icon}"></i></div>` : ''}
                <div class="metric-title">${title}</div>
            </div>
            <div class="metric-card-body">
                <div class="metric-main-value">
                    <span class="metric-number">${this.formatNumber(value)}</span>
                    <span class="metric-unit">${unit}</span>
                </div>
                ${trend && trendValue ? `
                    <div class="metric-trend ${trendClass}">
                        <i class="${trendIcon}"></i>
                        <span>${this.formatNumber(Math.abs(trendValue))}${unit}</span>
                    </div>
                ` : ''}
            </div>
            ${showProgress ? `
                <div class="metric-card-footer">
                    <div class="progress-track">
                        <div class="progress-fill ${colorClass}" style="width: ${percentage}%"></div>
                    </div>
                </div>
            ` : ''}
        `;

        return card;
    }

    /**
     * Create a status indicator component
     * @param {Object} options - Configuration options
     * @returns {HTMLElement} Status indicator element
     */
    createStatusIndicator(options = {}) {
        const {
            status = 'unknown',
            label = '',
            size = 'medium',
            animated = true,
            className = ''
        } = options;

        const indicator = document.createElement('div');
        indicator.className = `status-indicator ${status} ${size} ${animated ? 'animated' : ''} ${className}`;

        const statusIcon = this.getStatusIcon(status);
        const statusText = label || status.charAt(0).toUpperCase() + status.slice(1);

        indicator.innerHTML = `
            <i class="${statusIcon}"></i>
            <span class="status-text">${statusText}</span>
        `;

        return indicator;
    }

    /**
     * Create a mini chart component (sparkline)
     * @param {Object} options - Configuration options
     * @returns {HTMLElement} Mini chart element
     */
    createMiniChart(options = {}) {
        const {
            data = [],
            width = 100,
            height = 30,
            color = 'var(--primary-orange)',
            strokeWidth = 2,
            filled = false,
            animated = true,
            className = ''
        } = options;

        if (data.length === 0) {
            return this.createEmptyChart(width, height, className);
        }

        const chart = document.createElement('div');
        chart.className = `mini-chart ${className}`;
        chart.style.width = `${width}px`;
        chart.style.height = `${height}px`;

        const max = Math.max(...data);
        const min = Math.min(...data);
        const range = max - min || 1;

        // Create SVG path
        const points = data.map((value, index) => {
            const x = (index / (data.length - 1)) * width;
            const y = height - ((value - min) / range) * height;
            return `${x},${y}`;
        }).join(' ');

        const pathData = `M ${points.replace(/,/g, ' L ').replace(/ L /, ' ')}`;

        chart.innerHTML = `
            <svg class="mini-chart-svg" width="${width}" height="${height}">
                ${filled ? `
                    <path
                        class="mini-chart-area ${animated ? 'animated' : ''}"
                        d="${pathData} L ${width},${height} L 0,${height} Z"
                        fill="${color}20"
                    />
                ` : ''}
                <path
                    class="mini-chart-line ${animated ? 'animated' : ''}"
                    d="${pathData}"
                    stroke="${color}"
                    stroke-width="${strokeWidth}"
                    fill="none"
                />
            </svg>
        `;

        return chart;
    }

    /**
     * Update an existing progress bar
     * @param {HTMLElement} progressBar - Progress bar element
     * @param {number} value - New value
     * @param {number} max - Maximum value
     */
    updateProgressBar(progressBar, value, max = 100) {
        const percentage = Math.min(100, Math.max(0, (value / max) * 100));
        const progressFill = progressBar.querySelector('.progress-fill');
        const progressPercentage = progressBar.querySelector('.progress-percentage');
        const progressValue = progressBar.querySelector('.progress-value');

        if (progressFill) {
            // Update width with animation
            progressFill.style.width = `${percentage}%`;
            progressFill.setAttribute('data-value', value);
            progressFill.setAttribute('data-percentage', percentage.toFixed(1));

            // Update color based on new percentage
            const colorClass = this.getProgressColor(percentage);
            progressFill.className = progressFill.className.replace(/bg-\w+/, colorClass);
        }

        if (progressPercentage) {
            progressPercentage.textContent = `${percentage.toFixed(1)}%`;
        }

        if (progressValue) {
            progressValue.textContent = this.formatValue(value, max);
        }
    }

    /**
     * Update an existing gauge
     * @param {HTMLElement} gauge - Gauge element
     * @param {number} value - New value
     * @param {number} max - Maximum value
     */
    updateGauge(gauge, value, max = 100) {
        const percentage = Math.min(100, Math.max(0, (value / max) * 100));
        const progressCircle = gauge.querySelector('.gauge-progress');
        const gaugeValue = gauge.querySelector('.gauge-value');

        if (progressCircle) {
            const radius = parseFloat(progressCircle.getAttribute('r'));
            const circumference = 2 * Math.PI * radius;
            const strokeDashoffset = circumference - (percentage / 100) * circumference;

            progressCircle.style.strokeDashoffset = strokeDashoffset;
            progressCircle.setAttribute('data-value', value);
            progressCircle.setAttribute('data-percentage', percentage.toFixed(1));

            // Update color
            const colorClass = this.getProgressColor(percentage);
            progressCircle.className = progressCircle.className.replace(/\w+-color/, colorClass);
        }

        if (gaugeValue) {
            gaugeValue.textContent = `${percentage.toFixed(1)}%`;
        }
    }

    /**
     * Update an existing metric card
     * @param {HTMLElement} card - Metric card element
     * @param {Object} options - Update options
     */
    updateMetricCard(card, options = {}) {
        const {
            value,
            max = 100,
            trend,
            trendValue
        } = options;

        if (value !== undefined) {
            const metricNumber = card.querySelector('.metric-number');
            if (metricNumber) {
                metricNumber.textContent = this.formatNumber(value);
            }

            // Update progress bar if present
            const progressFill = card.querySelector('.progress-fill');
            if (progressFill) {
                const percentage = Math.min(100, Math.max(0, (value / max) * 100));
                progressFill.style.width = `${percentage}%`;
                
                const colorClass = this.getProgressColor(percentage);
                progressFill.className = progressFill.className.replace(/bg-\w+/, colorClass);
            }
        }

        if (trend !== undefined) {
            const trendElement = card.querySelector('.metric-trend');
            if (trendElement) {
                const trendIcon = trendElement.querySelector('i');
                const trendText = trendElement.querySelector('span');
                
                trendElement.className = `metric-trend trend-${trend}`;
                if (trendIcon) {
                    trendIcon.className = this.getTrendIcon(trend);
                }
                if (trendText && trendValue !== undefined) {
                    trendText.textContent = this.formatNumber(Math.abs(trendValue));
                }
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
            online: 'fas fa-circle',
            offline: 'fas fa-times-circle',
            running: 'fas fa-play-circle',
            stopped: 'fas fa-stop-circle',
            paused: 'fas fa-pause-circle',
            error: 'fas fa-exclamation-triangle',
            warning: 'fas fa-exclamation-circle',
            success: 'fas fa-check-circle',
            unknown: 'fas fa-question-circle'
        };
        return icons[status] || icons.unknown;
    }

    /**
     * Get trend icon based on trend direction
     * @param {string} trend - Trend direction
     * @returns {string} Icon class
     */
    getTrendIcon(trend) {
        const icons = {
            up: 'fas fa-arrow-up',
            down: 'fas fa-arrow-down',
            stable: 'fas fa-minus'
        };
        return icons[trend] || icons.stable;
    }

    /**
     * Format a number for display
     * @param {number} value - Number to format
     * @returns {string} Formatted number
     */
    formatNumber(value) {
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        }
        if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }
        return value.toFixed(1);
    }

    /**
     * Format a value with appropriate units
     * @param {number} value - Current value
     * @param {number} max - Maximum value
     * @returns {string} Formatted value
     */
    formatValue(value, max) {
        // If values are in bytes, format as bytes
        if (max > 1024 * 1024) {
            return `${formatBytes(value)} / ${formatBytes(max)}`;
        }
        return `${this.formatNumber(value)} / ${this.formatNumber(max)}`;
    }

    /**
     * Create an empty chart placeholder
     * @param {number} width - Chart width
     * @param {number} height - Chart height
     * @param {string} className - Additional CSS class
     * @returns {HTMLElement} Empty chart element
     */
    createEmptyChart(width, height, className = '') {
        const chart = document.createElement('div');
        chart.className = `mini-chart empty ${className}`;
        chart.style.width = `${width}px`;
        chart.style.height = `${height}px`;

        chart.innerHTML = `
            <div class="empty-chart-message">
                <i class="fas fa-chart-line"></i>
                <span>No data</span>
            </div>
        `;

        return chart;
    }

    /**
     * Add visualization styles to the document
     */
    addVisualizationStyles() {
        if (document.getElementById('metrics-visualization-styles')) {
            return; // Styles already added
        }

        const styles = `
            /* Progress Bar Styles */
            .progress-bar-container {
                margin-bottom: 1rem;
            }

            .progress-bar-container.small {
                font-size: 0.875rem;
            }

            .progress-bar-container.large {
                font-size: 1.125rem;
            }

            .progress-bar-wrapper {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }

            .progress-label {
                font-weight: 500;
                color: var(--text-primary);
                font-size: 0.875rem;
            }

            .progress-track {
                background-color: var(--bg-tertiary);
                border-radius: 4px;
                height: 8px;
                overflow: hidden;
                position: relative;
            }

            .progress-fill {
                height: 100%;
                border-radius: 4px;
                transition: width 0.3s ease, background-color 0.3s ease;
                position: relative;
            }

            .progress-fill.animated::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(45deg, transparent 25%, rgba(255,255,255,0.2) 25%, rgba(255,255,255,0.2) 50%, transparent 50%, transparent 75%, rgba(255,255,255,0.2) 75%);
                background-size: 20px 20px;
                animation: progress-stripes 1s linear infinite;
            }

            .progress-fill.striped {
                background-image: linear-gradient(45deg, rgba(255,255,255,0.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.15) 75%, transparent 75%, transparent);
                background-size: 1rem 1rem;
            }

            .progress-info {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.75rem;
                color: var(--text-secondary);
            }

            /* Gauge Styles */
            .gauge-container {
                position: relative;
                display: inline-block;
            }

            .gauge-svg {
                transform: rotate(-90deg);
            }

            .gauge-background {
                stroke: var(--bg-tertiary);
            }

            .gauge-progress {
                transition: stroke-dashoffset 0.3s ease;
            }

            .gauge-progress.animated {
                animation: gauge-fill 1s ease-out;
            }

            .gauge-content {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
            }

            .gauge-value {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--text-primary);
            }

            .gauge-label {
                font-size: 0.75rem;
                color: var(--text-secondary);
                margin-top: 0.25rem;
            }

            /* Metric Card Styles */
            .metric-card {
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1rem;
                transition: all 0.2s ease;
            }

            .metric-card:hover {
                box-shadow: 0 4px 12px var(--shadow-medium);
            }

            .metric-card.small {
                padding: 0.75rem;
                font-size: 0.875rem;
            }

            .metric-card.large {
                padding: 1.5rem;
                font-size: 1.125rem;
            }

            .metric-card-header {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-bottom: 0.75rem;
            }

            .metric-icon {
                color: var(--primary-orange);
                font-size: 1.25rem;
            }

            .metric-title {
                font-weight: 500;
                color: var(--text-secondary);
                font-size: 0.875rem;
            }

            .metric-card-body {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 0.75rem;
            }

            .metric-main-value {
                display: flex;
                align-items: baseline;
                gap: 0.25rem;
            }

            .metric-number {
                font-size: 2rem;
                font-weight: 700;
                color: var(--text-primary);
            }

            .metric-unit {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }

            .metric-trend {
                display: flex;
                align-items: center;
                gap: 0.25rem;
                font-size: 0.75rem;
                font-weight: 500;
            }

            .metric-trend.trend-up {
                color: var(--success-color);
            }

            .metric-trend.trend-down {
                color: var(--error-color);
            }

            .metric-trend.trend-stable {
                color: var(--text-secondary);
            }

            .metric-card-footer .progress-track {
                height: 4px;
                margin-top: 0.5rem;
            }

            /* Status Indicator Styles */
            .status-indicator {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-size: 0.875rem;
                font-weight: 500;
            }

            .status-indicator.small {
                padding: 0.125rem 0.375rem;
                font-size: 0.75rem;
                gap: 0.375rem;
            }

            .status-indicator.large {
                padding: 0.375rem 0.75rem;
                font-size: 1rem;
                gap: 0.625rem;
            }

            .status-indicator.online {
                color: var(--success-color);
                background-color: var(--success-color)20;
            }

            .status-indicator.offline {
                color: var(--error-color);
                background-color: var(--error-color)20;
            }

            .status-indicator.running {
                color: var(--success-color);
                background-color: var(--success-color)20;
            }

            .status-indicator.stopped {
                color: var(--text-secondary);
                background-color: var(--text-secondary)20;
            }

            .status-indicator.error {
                color: var(--error-color);
                background-color: var(--error-color)20;
            }

            .status-indicator.animated i {
                animation: pulse 2s infinite;
            }

            /* Mini Chart Styles */
            .mini-chart {
                display: inline-block;
                position: relative;
            }

            .mini-chart-svg {
                display: block;
            }

            .mini-chart-line {
                transition: stroke-dasharray 0.5s ease;
            }

            .mini-chart-area {
                transition: opacity 0.3s ease;
            }

            .mini-chart.empty {
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--bg-tertiary);
                border-radius: 4px;
            }

            .empty-chart-message {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.25rem;
                color: var(--text-muted);
                font-size: 0.75rem;
            }

            /* Color Classes */
            .bg-success { background-color: var(--success-color); }
            .bg-info { background-color: var(--info-color); }
            .bg-warning { background-color: var(--warning-color); }
            .bg-danger { background-color: var(--error-color); }
            .bg-primary { background-color: var(--primary-orange); }

            .success-color { stroke: var(--success-color); }
            .info-color { stroke: var(--info-color); }
            .warning-color { stroke: var(--warning-color); }
            .danger-color { stroke: var(--error-color); }
            .primary-color { stroke: var(--primary-orange); }

            /* Animations */
            @keyframes progress-stripes {
                0% { background-position: 0 0; }
                100% { background-position: 20px 0; }
            }

            @keyframes gauge-fill {
                0% { stroke-dashoffset: 100%; }
                100% { stroke-dashoffset: var(--final-offset, 0); }
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            /* Connection Error State */
            .connection-error {
                opacity: 0.7;
                position: relative;
            }

            .connection-error::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 10px,
                    var(--error-color)20 10px,
                    var(--error-color)20 20px
                );
                pointer-events: none;
                border-radius: inherit;
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.id = 'metrics-visualization-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
}

// Create global instance
const metricsVisualizer = new MetricsVisualizer();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MetricsVisualizer,
        metricsVisualizer
    };
}

// Make available globally
window.MetricsVisualizer = MetricsVisualizer;
window.metricsVisualizer = metricsVisualizer;