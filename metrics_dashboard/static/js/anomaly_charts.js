/**
 * AnomalySNMP Charts JavaScript
 * Gestisce le visualizzazioni grafiche per il rilevamento anomalie SNMP
 * Implementa gauge chart, line chart e color coding dinamico
 */

/**
 * Configurazione colori per S-Score con soglie dinamiche
 */
const ANOMALY_CHART_CONFIG = {
    colors: {
        excellent: { color: '#27ae60', threshold: 0.8, label: 'Eccellente', bg: 'rgba(39, 174, 96, 0.1)' },
        good: { color: '#f39c12', threshold: 0.6, label: 'Buono', bg: 'rgba(243, 156, 18, 0.1)' },
        warning: { color: '#ff6b35', threshold: 0.4, label: 'Attenzione', bg: 'rgba(255, 107, 53, 0.1)' },
        critical: { color: '#e74c3c', threshold: 0.0, label: 'Critico', bg: 'rgba(231, 76, 60, 0.1)' }
    },
    labelColors: {
        'Normal': '#27ae60',    // Verde per punti normali
        'Anomaly': '#e74c3c'    // Rosso per anomalie
    },
    animation: {
        duration: 300,
        easing: 'easeOutQuart'
    }
};

/**
 * Classe per gestione avanzata del Gauge Chart
 */
class AnomalyScoreGauge {
    constructor(canvasId, options = {}) {
        this.canvasId = canvasId;
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.currentValue = 0;
        this.targetValue = 0;
        this.animationFrame = null;
        
        this.options = {
            size: 280,
            thickness: 22,
            startAngle: -Math.PI * 0.75,
            endAngle: Math.PI * 0.75,
            showThresholds: true,
            showLabels: true,
            animationDuration: 800,
            ...options
        };
        
        this.setupCanvas();
        this.render();
    }
    
    setupCanvas() {
        const { size } = this.options;
        const dpr = window.devicePixelRatio || 1;
        
        this.canvas.width = size * dpr;
        this.canvas.height = size * 0.7 * dpr;
        this.canvas.style.width = size + 'px';
        this.canvas.style.height = (size * 0.7) + 'px';
        
        this.ctx.scale(dpr, dpr);
    }
    
    getColorZone(value) {
        const { colors } = ANOMALY_CHART_CONFIG;
        
        if (value >= colors.excellent.threshold) return colors.excellent;
        if (value >= colors.good.threshold) return colors.good;
        if (value >= colors.warning.threshold) return colors.warning;
        return colors.critical;
    }
    
    drawBackground() {
        const { size, thickness, startAngle, endAngle } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size / 2) - thickness - 10;
        
        // Background arc
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        this.ctx.lineWidth = thickness;
        this.ctx.strokeStyle = '#ecf0f1';
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        
        // Threshold markers
        if (this.options.showThresholds) {
            this.drawThresholdMarkers(centerX, centerY, radius);
        }
    }
    
    drawThresholdMarkers(centerX, centerY, radius) {
        const { startAngle, endAngle, thickness } = this.options;
        const totalAngle = endAngle - startAngle;
        const { colors } = ANOMALY_CHART_CONFIG;
        
        // Draw threshold lines
        [colors.excellent.threshold, colors.good.threshold, colors.warning.threshold].forEach(threshold => {
            const angle = startAngle + (threshold * totalAngle);
            const innerRadius = radius - thickness / 2 - 5;
            const outerRadius = radius + thickness / 2 + 5;
            
            const x1 = centerX + Math.cos(angle) * innerRadius;
            const y1 = centerY + Math.sin(angle) * innerRadius;
            const x2 = centerX + Math.cos(angle) * outerRadius;
            const y2 = centerY + Math.sin(angle) * outerRadius;
            
            this.ctx.beginPath();
            this.ctx.moveTo(x1, y1);
            this.ctx.lineTo(x2, y2);
            this.ctx.strokeStyle = '#bdc3c7';
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
        });
    }
    
    drawValue() {
        const { size, thickness, startAngle, endAngle } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size / 2) - thickness - 10;
        const totalAngle = endAngle - startAngle;
        const valueAngle = startAngle + (this.currentValue * totalAngle);
        
        const colorZone = this.getColorZone(this.currentValue);
        
        // Value arc with gradient
        const gradient = this.ctx.createLinearGradient(0, 0, size, 0);
        gradient.addColorStop(0, colorZone.color);
        gradient.addColorStop(1, colorZone.color + 'CC');
        
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius, startAngle, valueAngle);
        this.ctx.lineWidth = thickness;
        this.ctx.strokeStyle = gradient;
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        
        // Needle indicator
        this.drawNeedle(centerX, centerY, radius, valueAngle, colorZone.color);
    }
    
    drawNeedle(centerX, centerY, radius, angle, color) {
        const needleLength = radius + 15;
        const needleX = centerX + Math.cos(angle) * needleLength;
        const needleY = centerY + Math.sin(angle) * needleLength;
        
        // Needle shadow
        this.ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        this.ctx.shadowBlur = 5;
        this.ctx.shadowOffsetX = 2;
        this.ctx.shadowOffsetY = 2;
        
        // Needle circle
        this.ctx.beginPath();
        this.ctx.arc(needleX, needleY, 8, 0, 2 * Math.PI);
        this.ctx.fillStyle = color;
        this.ctx.fill();
        
        // Inner white circle
        this.ctx.beginPath();
        this.ctx.arc(needleX, needleY, 4, 0, 2 * Math.PI);
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fill();
        
        // Reset shadow
        this.ctx.shadowColor = 'transparent';
        this.ctx.shadowBlur = 0;
        this.ctx.shadowOffsetX = 0;
        this.ctx.shadowOffsetY = 0;
    }
    
    drawLabels() {
        const { size } = this.options;
        const centerX = size / 2;
        const centerY = size / 2;
        const colorZone = this.getColorZone(this.currentValue);
        
        // Main percentage
        this.ctx.textAlign = 'center';
        this.ctx.font = 'bold 32px Segoe UI, sans-serif';
        this.ctx.fillStyle = colorZone.color;
        this.ctx.fillText(`${Math.round(this.currentValue * 100)}%`, centerX, centerY + 10);
        
        // Status label
        this.ctx.font = '14px Segoe UI, sans-serif';
        this.ctx.fillStyle = colorZone.color;
        this.ctx.fillText(colorZone.label, centerX, centerY + 35);
        
        // Title
        this.ctx.font = '12px Segoe UI, sans-serif';
        this.ctx.fillStyle = '#7f8c8d';
        this.ctx.fillText('S-Score Salute Comportamentale', centerX, centerY - 50);
    }
    
    render() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawBackground();
        this.drawValue();
        this.drawLabels();
    }
    
    setValue(value, animate = true) {
        this.targetValue = Math.max(0, Math.min(1, value));
        
        if (animate) {
            this.animateToValue();
        } else {
            this.currentValue = this.targetValue;
            this.render();
        }
    }
    
    animateToValue() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        const startValue = this.currentValue;
        const startTime = performance.now();
        const { animationDuration } = this.options;
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / animationDuration, 1);
            
            // Easing function
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            
            this.currentValue = startValue + (this.targetValue - startValue) * easeOutQuart;
            this.render();
            
            if (progress < 1) {
                this.animationFrame = requestAnimationFrame(animate);
            }
        };
        
        this.animationFrame = requestAnimationFrame(animate);
    }
    
    updateTheme(isDark) {
        // Update colors for dark theme
        this.render();
    }
    
    destroy() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }
}

/**
 * Classe per gestione avanzata del Temporal Chart
 */
class AnomalyTemporalChart {
    constructor(canvasId, options = {}) {
        this.canvasId = canvasId;
        this.ctx = document.getElementById(canvasId).getContext('2d');
        this.data = [];
        this.maxPoints = options.maxPoints || 50;
        
        this.chart = this.initializeChart();
    }
    
    initializeChart() {
        const { colors } = ANOMALY_CHART_CONFIG;
        
        return new Chart(this.ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'S-Score',
                    data: [],
                    borderColor: '#ff8c00',
                    backgroundColor: 'rgba(255, 140, 0, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: [],
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointHoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#ff8c00',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            title: (context) => {
                                const index = context[0].dataIndex;
                                const dataPoint = this.data[index];
                                if (dataPoint) {
                                    const timestamp = new Date(dataPoint.timestamp);
                                    return `Punto ${dataPoint.offset} - ${timestamp.toLocaleTimeString()}`;
                                }
                                return 'Punto dati';
                            },
                            label: (context) => {
                                const index = context.dataIndex;
                                const score = context.parsed.y;
                                const dataPoint = this.data[index];
                                
                                if (dataPoint) {
                                    const colorZone = this.getColorZone(score);
                                    return [
                                        `S-Score: ${(score * 100).toFixed(1)}%`,
                                        `Etichetta: ${dataPoint.label}`,
                                        `Livello: ${colorZone.label}`
                                    ];
                                }
                                return `S-Score: ${(score * 100).toFixed(1)}%`;
                            },
                            labelColor: (context) => {
                                const index = context.dataIndex;
                                const dataPoint = this.data[index];
                                const labelColor = dataPoint ? 
                                    ANOMALY_CHART_CONFIG.labelColors[dataPoint.label] || '#e74c3c' : 
                                    '#e74c3c';
                                
                                return {
                                    borderColor: labelColor,
                                    backgroundColor: labelColor
                                };
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            excellentZone: {
                                type: 'box',
                                yMin: colors.excellent.threshold,
                                yMax: 1.0,
                                backgroundColor: colors.excellent.bg,
                                borderColor: colors.excellent.color,
                                borderWidth: 0
                            },
                            goodZone: {
                                type: 'box',
                                yMin: colors.good.threshold,
                                yMax: colors.excellent.threshold,
                                backgroundColor: colors.good.bg,
                                borderColor: colors.good.color,
                                borderWidth: 0
                            },
                            warningZone: {
                                type: 'box',
                                yMin: colors.warning.threshold,
                                yMax: colors.good.threshold,
                                backgroundColor: colors.warning.bg,
                                borderColor: colors.warning.color,
                                borderWidth: 0
                            },
                            criticalZone: {
                                type: 'box',
                                yMin: 0,
                                yMax: colors.warning.threshold,
                                backgroundColor: colors.critical.bg,
                                borderColor: colors.critical.color,
                                borderWidth: 0
                            },
                            excellentLine: {
                                type: 'line',
                                yMin: colors.excellent.threshold,
                                yMax: colors.excellent.threshold,
                                borderColor: colors.excellent.color,
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: 'Eccellente (80%)',
                                    enabled: true,
                                    position: 'end',
                                    backgroundColor: colors.excellent.color,
                                    color: '#fff',
                                    font: { size: 10 }
                                }
                            },
                            goodLine: {
                                type: 'line',
                                yMin: colors.good.threshold,
                                yMax: colors.good.threshold,
                                borderColor: colors.good.color,
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: 'Buono (60%)',
                                    enabled: true,
                                    position: 'end',
                                    backgroundColor: colors.good.color,
                                    color: '#fff',
                                    font: { size: 10 }
                                }
                            },
                            warningLine: {
                                type: 'line',
                                yMin: colors.warning.threshold,
                                yMax: colors.warning.threshold,
                                borderColor: colors.warning.color,
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {
                                    content: 'Attenzione (40%)',
                                    enabled: true,
                                    position: 'end',
                                    backgroundColor: colors.warning.color,
                                    color: '#fff',
                                    font: { size: 10 }
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1.0,
                        ticks: {
                            callback: (value) => (value * 100).toFixed(0) + '%',
                            color: '#6c757d'
                        },
                        title: {
                            display: true,
                            text: 'S-Score (%)',
                            font: { weight: 'bold' },
                            color: '#495057'
                        },
                        grid: {
                            color: (context) => {
                                const value = context.tick.value;
                                if (value === colors.excellent.threshold) return colors.excellent.color + '60';
                                if (value === colors.good.threshold) return colors.good.color + '60';
                                if (value === colors.warning.threshold) return colors.warning.color + '60';
                                return '#e9ecef';
                            },
                            lineWidth: (context) => {
                                const value = context.tick.value;
                                return [colors.excellent.threshold, colors.good.threshold, colors.warning.threshold].includes(value) ? 2 : 1;
                            }
                        }
                    },
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Offset Punti Dati',
                            font: { weight: 'bold' },
                            color: '#495057'
                        },
                        ticks: {
                            color: '#6c757d'
                        },
                        grid: {
                            color: '#e9ecef'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animation: ANOMALY_CHART_CONFIG.animation
            }
        });
    }
    
    getColorZone(value) {
        const { colors } = ANOMALY_CHART_CONFIG;
        
        if (value >= colors.excellent.threshold) return colors.excellent;
        if (value >= colors.good.threshold) return colors.good;
        if (value >= colors.warning.threshold) return colors.warning;
        return colors.critical;
    }
    
    addDataPoint(dataPoint) {
        // Add new data point
        this.data.push({
            offset: dataPoint.offset,
            score: dataPoint.s_score,
            label: dataPoint.real_label,
            timestamp: dataPoint.timestamp,
            features: dataPoint.features
        });
        
        // Maintain max points limit
        if (this.data.length > this.maxPoints) {
            this.data.shift();
        }
        
        // Update chart data
        this.updateChartData();
    }
    
    updateChartData() {
        // Update labels and data
        this.chart.data.labels = this.data.map(d => d.offset);
        this.chart.data.datasets[0].data = this.data.map(d => d.score);
        
        // Color coding dinamico dei punti basato su etichette reali
        this.chart.data.datasets[0].pointBackgroundColor = this.data.map(d => 
            ANOMALY_CHART_CONFIG.labelColors[d.label] || ANOMALY_CHART_CONFIG.labelColors['Anomaly']
        );
        
        // Update with smooth animation
        this.chart.update('active');
    }
    
    reset() {
        this.data = [];
        this.chart.data.labels = [];
        this.chart.data.datasets[0].data = [];
        this.chart.data.datasets[0].pointBackgroundColor = [];
        this.chart.update();
    }
    
    updateTheme(isDark) {
        const textColor = isDark ? '#f0f0f0' : '#495057';
        const gridColor = isDark ? '#404040' : '#e9ecef';
        
        // Update chart colors
        this.chart.options.scales.x.ticks.color = textColor;
        this.chart.options.scales.y.ticks.color = textColor;
        this.chart.options.scales.x.title.color = textColor;
        this.chart.options.scales.y.title.color = textColor;
        this.chart.options.scales.x.grid.color = gridColor;
        
        // Update grid colors for thresholds
        this.chart.options.scales.y.grid.color = (context) => {
            const { colors } = ANOMALY_CHART_CONFIG;
            const value = context.tick.value;
            if (value === colors.excellent.threshold) return colors.excellent.color + '60';
            if (value === colors.good.threshold) return colors.good.color + '60';
            if (value === colors.warning.threshold) return colors.warning.color + '60';
            return gridColor;
        };
        
        this.chart.update();
    }
    
    destroy() {
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

/**
 * Utility functions per color coding avanzato
 */
const AnomalyChartUtils = {
    /**
     * Determina colore e classe CSS basati su S-Score
     */
    getScoreColorAndClass(score) {
        const { colors } = ANOMALY_CHART_CONFIG;
        
        if (score >= colors.excellent.threshold) {
            return { color: colors.excellent.color, cardClass: 'score-excellent', zone: colors.excellent };
        } else if (score >= colors.good.threshold) {
            return { color: colors.good.color, cardClass: 'score-good', zone: colors.good };
        } else if (score >= colors.warning.threshold) {
            return { color: colors.warning.color, cardClass: 'score-warning', zone: colors.warning };
        } else {
            return { color: colors.critical.color, cardClass: 'score-critical', zone: colors.critical };
        }
    },
    
    /**
     * Ottieni livello testuale basato su S-Score
     */
    getScoreLevel(score) {
        const { zone } = this.getScoreColorAndClass(score);
        return zone.label;
    },
    
    /**
     * Genera colore per feature SNMP basato su intensità
     */
    getFeatureColor(value, maxValue, minValue) {
        const absValue = Math.abs(value);
        const normalizedIntensity = maxValue > 0 ? (absValue / maxValue) : 0;
        
        if (normalizedIntensity > 0.7) {
            return {
                color: value >= 0 ? '#27ae60' : '#e74c3c',
                bgColor: value >= 0 ? 'rgba(39, 174, 96, 0.2)' : 'rgba(231, 76, 60, 0.2)',
                textClass: 'fw-bold',
                intensity: normalizedIntensity
            };
        } else if (normalizedIntensity > 0.4) {
            return {
                color: '#f39c12',
                bgColor: 'rgba(243, 156, 18, 0.2)',
                textClass: 'fw-semibold',
                intensity: normalizedIntensity
            };
        } else {
            return {
                color: '#6c757d',
                bgColor: 'rgba(108, 117, 125, 0.1)',
                textClass: '',
                intensity: normalizedIntensity
            };
        }
    },
    
    /**
     * Genera HTML per display feature con color coding
     */
    generateFeaturesHTML(features) {
        const maxValue = Math.max(...features.map(Math.abs));
        const minValue = Math.min(...features.map(Math.abs));
        let html = '';
        
        for (let i = 0; i < features.length; i++) {
            const value = features[i];
            const featureColor = this.getFeatureColor(value, maxValue, minValue);
            const barWidth = Math.max(featureColor.intensity * 100, 5);
            
            html += `
                <div class="col-6 mb-2">
                    <div class="p-2 rounded border" style="background-color: ${featureColor.bgColor}; border-color: ${featureColor.color}40 !important;">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <small class="text-muted">F${i + 1}</small>
                            <div class="progress" style="width: 30px; height: 4px;">
                                <div class="progress-bar" style="width: ${barWidth}%; background-color: ${featureColor.color};"></div>
                            </div>
                        </div>
                        <div class="${featureColor.textClass}" style="color: ${featureColor.color}; font-size: 0.9rem;">
                            ${value.toFixed(3)}
                        </div>
                    </div>
                </div>
            `;
        }
        
        return html;
    }
};

// Export per uso globale
if (typeof window !== 'undefined') {
    window.AnomalyScoreGauge = AnomalyScoreGauge;
    window.AnomalyTemporalChart = AnomalyTemporalChart;
    window.AnomalyChartUtils = AnomalyChartUtils;
    window.ANOMALY_CHART_CONFIG = ANOMALY_CHART_CONFIG;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AnomalyScoreGauge,
        AnomalyTemporalChart,
        AnomalyChartUtils,
        ANOMALY_CHART_CONFIG
    };
}

console.log('✅ AnomalySNMP Charts JS loaded - Implementazione Task 5.2 completata');