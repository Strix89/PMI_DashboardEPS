/**
 * Acronis Dashboard Fixes
 * Resolves font loading issues and chart container problems
 */

(function() {
    'use strict';

    // COMPLETE Google Fonts blocking
    const blockGoogleFonts = () => {
        // Block any new link elements that try to load Google Fonts
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node.tagName === 'LINK') {
                        const href = node.getAttribute('href');
                        if (href && (href.includes('fonts.googleapis.com') || href.includes('fonts.gstatic.com'))) {
                            console.warn('Blocked Google Fonts loading:', href);
                            node.remove();
                        }
                    }
                });
            });
        });

        observer.observe(document.head, {
            childList: true,
            subtree: true
        });

        // Remove any existing Google Fonts links
        const existingLinks = document.querySelectorAll('link[href*="fonts.googleapis.com"], link[href*="fonts.gstatic.com"]');
        existingLinks.forEach(link => {
            console.warn('Removed existing Google Fonts link:', link.href);
            link.remove();
        });

        // Override XMLHttpRequest to block font requests
        const originalXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = function() {
            const xhr = new originalXHR();
            const originalOpen = xhr.open;
            
            xhr.open = function(method, url, ...args) {
                if (typeof url === 'string' && (url.includes('fonts.googleapis.com') || url.includes('fonts.gstatic.com'))) {
                    console.warn('Blocked XHR Google Fonts request:', url);
                    return;
                }
                return originalOpen.apply(this, [method, url, ...args]);
            };
            
            return xhr;
        };

        // Override fetch to block font requests
        const originalFetch = window.fetch;
        window.fetch = function(url, ...args) {
            if (typeof url === 'string' && (url.includes('fonts.googleapis.com') || url.includes('fonts.gstatic.com'))) {
                console.warn('Blocked fetch Google Fonts request:', url);
                return Promise.reject(new Error('Google Fonts blocked'));
            }
            return originalFetch.apply(this, [url, ...args]);
        };
    };

    // Initialize font blocking immediately
    blockGoogleFonts();

    // Fix chart container issues
    function fixChartContainers() {
        // Find all chart containers that might be missing
        const chartSelectors = [
            '[id*="chart"]',
            '.agent-chart',
            '.chart-container'
        ];

        chartSelectors.forEach(selector => {
            const containers = document.querySelectorAll(selector);
            containers.forEach(container => {
                if (!container.id) {
                    // Generate a unique ID if missing
                    container.id = 'chart-' + Math.random().toString(36).substr(2, 9);
                }

                // Ensure container has valid dimensions
                const rect = container.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(container);
                
                // Check if container has zero or negative dimensions
                if (rect.width <= 0 || rect.height <= 0 || 
                    parseFloat(computedStyle.width) <= 0 || 
                    parseFloat(computedStyle.height) <= 0) {
                    
                    // Force minimum dimensions
                    container.style.minWidth = '200px';
                    container.style.minHeight = '200px';
                    container.style.width = '100%';
                    container.style.height = '200px';
                    container.style.display = 'block';
                    container.style.position = 'relative';
                    
                    console.warn(`Fixed container dimensions for: ${container.id}`);
                }

                // Ensure container is visible
                if (computedStyle.display === 'none' || computedStyle.visibility === 'hidden') {
                    container.style.display = 'block';
                    container.style.visibility = 'visible';
                }

                // Add error handling
                if (!container.hasAttribute('data-error-handler')) {
                    container.setAttribute('data-error-handler', 'true');
                    container.addEventListener('error', function(e) {
                        console.warn('Chart container error:', e);
                        container.classList.add('error');
                    });
                }
            });
        });
    }

    // Enhanced chart rendering with error handling
    function enhanceChartRendering() {
        if (typeof google !== 'undefined' && google.visualization) {
            // Override chart drawing to handle errors better
            const originalDraw = google.visualization.Chart?.prototype?.draw;
            if (originalDraw) {
                google.visualization.Chart.prototype.draw = function(data, options) {
                    try {
                        // Validate container dimensions before drawing
                        if (this.container) {
                            const rect = this.container.getBoundingClientRect();
                            const computedStyle = window.getComputedStyle(this.container);
                            
                            // Check for invalid dimensions
                            if (rect.width <= 0 || rect.height <= 0 || 
                                parseFloat(computedStyle.width) <= 0 || 
                                parseFloat(computedStyle.height) <= 0) {
                                
                                console.warn('Invalid container dimensions detected, fixing...', {
                                    id: this.container.id,
                                    width: rect.width,
                                    height: rect.height,
                                    computedWidth: computedStyle.width,
                                    computedHeight: computedStyle.height
                                });
                                
                                // Force valid dimensions
                                this.container.style.width = '100%';
                                this.container.style.height = '200px';
                                this.container.style.minWidth = '200px';
                                this.container.style.minHeight = '200px';
                                this.container.style.display = 'block';
                                
                                // Wait for layout to update
                                setTimeout(() => {
                                    try {
                                        originalDraw.call(this, data, options);
                                    } catch (retryError) {
                                        console.error('Chart retry failed:', retryError);
                                        this.showErrorState();
                                    }
                                }, 100);
                                return;
                            }
                        }

                        // Ensure font family is set correctly
                        if (options && !options.fontName) {
                            options.fontName = 'inherit';
                        }

                        // Ensure minimum chart dimensions in options
                        if (options) {
                            if (!options.width || options.width <= 0) {
                                options.width = Math.max(200, this.container?.offsetWidth || 200);
                            }
                            if (!options.height || options.height <= 0) {
                                options.height = Math.max(150, this.container?.offsetHeight || 150);
                            }
                        }

                        // Set theme-aware colors
                        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                        if (options) {
                            if (!options.backgroundColor) {
                                options.backgroundColor = 'transparent';
                            }
                            if (!options.titleTextStyle) {
                                options.titleTextStyle = {};
                            }
                            if (!options.hAxis) {
                                options.hAxis = {};
                            }
                            if (!options.vAxis) {
                                options.vAxis = {};
                            }

                            // Set text colors based on theme
                            const textColor = isDark ? '#e2e8f0' : '#2d3748';
                            options.titleTextStyle.color = textColor;
                            if (options.hAxis.textStyle) options.hAxis.textStyle.color = textColor;
                            if (options.vAxis.textStyle) options.vAxis.textStyle.color = textColor;
                        }

                        return originalDraw.call(this, data, options);
                    } catch (error) {
                        console.error('Chart rendering error:', error);
                        this.showErrorState();
                    }
                };

                // Add error state method to chart prototype
                google.visualization.Chart.prototype.showErrorState = function() {
                    if (this.container) {
                        this.container.classList.add('error');
                        this.container.innerHTML = `
                            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--error-red); font-size: 14px;">
                                <i class="fas fa-exclamation-triangle" style="margin-right: 8px;"></i>
                                Chart unavailable
                            </div>
                        `;
                    }
                };
            }
        }
    }

    // Improve tooltip visibility - ENHANCED VERSION
    function improveTooltips() {
        // Create a MutationObserver to watch for tooltip creation
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList && 
                        node.classList.contains('google-visualization-tooltip')) {
                        
                        // Apply theme-aware styling with high contrast
                        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                        
                        // Force high contrast colors
                        node.style.backgroundColor = isDark ? '#1a1a1a' : '#ffffff';
                        node.style.color = isDark ? '#ffffff' : '#000000';
                        node.style.border = `2px solid ${isDark ? '#ffffff' : '#333333'}`;
                        node.style.borderRadius = '8px';
                        node.style.boxShadow = isDark ? 
                            '0 6px 20px rgba(255, 255, 255, 0.2)' : 
                            '0 6px 20px rgba(0, 0, 0, 0.3)';
                        node.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
                        node.style.fontSize = '14px';
                        node.style.fontWeight = '600';
                        node.style.padding = '12px 16px';
                        node.style.zIndex = '9999';
                        node.style.maxWidth = '300px';

                        // Fix text color in tooltip items with high contrast
                        const items = node.querySelectorAll('*');
                        items.forEach(item => {
                            if (item.style) {
                                item.style.color = isDark ? '#ffffff' : '#000000';
                                item.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
                                item.style.fontWeight = '600';
                            }
                        });

                        // Force text content to be visible
                        const textNodes = node.querySelectorAll('div, span, td');
                        textNodes.forEach(textNode => {
                            textNode.style.color = isDark ? '#ffffff' : '#000000';
                            textNode.style.fontWeight = '600';
                        });
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Theme change handler
    function handleThemeChange() {
        document.addEventListener('themechange', function(e) {
            // Update chart colors when theme changes
            setTimeout(() => {
                if (window.acronisCharts && window.acronisCharts.refreshAllCharts) {
                    window.acronisCharts.refreshAllCharts();
                }
            }, 100);
        });
    }

    // Monitor for new chart containers
    function monitorChartContainers() {
        const observer = new MutationObserver(function(mutations) {
            let needsFix = false;
            
            mutations.forEach(function(mutation) {
                // Check for added nodes
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        // Check if it's a chart container or contains chart containers
                        if (node.matches && (
                            node.matches('[id*="chart"]') || 
                            node.matches('.agent-chart') || 
                            node.matches('.chart-container') ||
                            node.querySelector('[id*="chart"], .agent-chart, .chart-container')
                        )) {
                            needsFix = true;
                        }
                    }
                });

                // Check for attribute changes that might affect dimensions
                if (mutation.type === 'attributes' && 
                    (mutation.attributeName === 'style' || 
                     mutation.attributeName === 'class' ||
                     mutation.attributeName === 'id')) {
                    const target = mutation.target;
                    if (target.matches && (
                        target.matches('[id*="chart"]') || 
                        target.matches('.agent-chart') || 
                        target.matches('.chart-container')
                    )) {
                        needsFix = true;
                    }
                }
            });

            if (needsFix) {
                // Debounce the fix to avoid excessive calls
                clearTimeout(window.chartFixTimeout);
                window.chartFixTimeout = setTimeout(fixChartContainers, 100);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class', 'id']
        });

        return observer;
    }

    // Initialize fixes
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        fixChartContainers();
        enhanceChartRendering();
        improveTooltips();
        handleThemeChange();
        
        // Start monitoring for new containers
        monitorChartContainers();

        // Re-run chart container fixes periodically as backup
        setInterval(fixChartContainers, 10000);

        console.log('Acronis fixes initialized with container monitoring');
    }

    // Start initialization
    init();

    // Export for external use
    window.acronisFixes = {
        fixChartContainers,
        enhanceChartRendering,
        improveTooltips
    };

})();