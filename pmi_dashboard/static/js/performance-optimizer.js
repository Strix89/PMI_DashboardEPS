/**
 * Performance Optimizer for PMI Dashboard
 * 
 * This module helps optimize performance by managing intervals,
 * preventing memory leaks, and throttling expensive operations.
 */

class PerformanceOptimizer {
    constructor() {
        this.intervals = new Map();
        this.timeouts = new Map();
        this.observers = new Map();
        this.isPageVisible = !document.hidden;
        
        this.init();
    }

    init() {
        this.setupVisibilityHandling();
        this.setupBeforeUnloadCleanup();
        this.monitorMemoryUsage();
    }

    /**
     * Setup page visibility handling to pause operations when tab is hidden
     */
    setupVisibilityHandling() {
        document.addEventListener('visibilitychange', () => {
            this.isPageVisible = !document.hidden;
            
            if (this.isPageVisible) {
                this.resumeOperations();
            } else {
                this.pauseOperations();
            }
        });
    }

    /**
     * Setup cleanup before page unload
     */
    setupBeforeUnloadCleanup() {
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    /**
     * Monitor memory usage and warn if it gets too high
     */
    monitorMemoryUsage() {
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                const usedMB = memory.usedJSHeapSize / 1024 / 1024;
                const limitMB = memory.jsHeapSizeLimit / 1024 / 1024;
                
                if (usedMB > limitMB * 0.8) { // 80% of limit
                    console.warn('High memory usage detected:', {
                        used: Math.round(usedMB) + 'MB',
                        limit: Math.round(limitMB) + 'MB',
                        percentage: Math.round((usedMB / limitMB) * 100) + '%'
                    });
                }
            }, 30000); // Check every 30 seconds
        }
    }

    /**
     * Register a managed interval
     * @param {string} name - Unique name for the interval
     * @param {Function} callback - Function to execute
     * @param {number} delay - Delay in milliseconds
     * @param {boolean} pauseWhenHidden - Whether to pause when page is hidden
     * @returns {number} Interval ID
     */
    setManagedInterval(name, callback, delay, pauseWhenHidden = true) {
        // Clear existing interval with same name
        this.clearManagedInterval(name);
        
        const intervalId = setInterval(() => {
            if (pauseWhenHidden && !this.isPageVisible) {
                return; // Skip execution when page is hidden
            }
            
            try {
                callback();
            } catch (error) {
                console.error(`Error in managed interval '${name}':`, error);
            }
        }, delay);
        
        this.intervals.set(name, {
            id: intervalId,
            callback,
            delay,
            pauseWhenHidden,
            paused: false
        });
        
        return intervalId;
    }

    /**
     * Clear a managed interval
     * @param {string} name - Name of the interval to clear
     */
    clearManagedInterval(name) {
        const interval = this.intervals.get(name);
        if (interval) {
            clearInterval(interval.id);
            this.intervals.delete(name);
        }
    }

    /**
     * Register a managed timeout
     * @param {string} name - Unique name for the timeout
     * @param {Function} callback - Function to execute
     * @param {number} delay - Delay in milliseconds
     * @returns {number} Timeout ID
     */
    setManagedTimeout(name, callback, delay) {
        // Clear existing timeout with same name
        this.clearManagedTimeout(name);
        
        const timeoutId = setTimeout(() => {
            try {
                callback();
            } catch (error) {
                console.error(`Error in managed timeout '${name}':`, error);
            } finally {
                this.timeouts.delete(name);
            }
        }, delay);
        
        this.timeouts.set(name, timeoutId);
        return timeoutId;
    }

    /**
     * Clear a managed timeout
     * @param {string} name - Name of the timeout to clear
     */
    clearManagedTimeout(name) {
        const timeoutId = this.timeouts.get(name);
        if (timeoutId) {
            clearTimeout(timeoutId);
            this.timeouts.delete(name);
        }
    }

    /**
     * Pause all pausable operations
     */
    pauseOperations() {
        this.intervals.forEach((interval, name) => {
            if (interval.pauseWhenHidden && !interval.paused) {
                clearInterval(interval.id);
                interval.paused = true;
            }
        });
    }

    /**
     * Resume all paused operations
     */
    resumeOperations() {
        this.intervals.forEach((interval, name) => {
            if (interval.paused) {
                const newId = setInterval(() => {
                    try {
                        interval.callback();
                    } catch (error) {
                        console.error(`Error in resumed interval '${name}':`, error);
                    }
                }, interval.delay);
                
                interval.id = newId;
                interval.paused = false;
            }
        });
    }

    /**
     * Get performance statistics
     * @returns {Object} Performance stats
     */
    getStats() {
        return {
            activeIntervals: this.intervals.size,
            activeTimeouts: this.timeouts.size,
            activeObservers: this.observers.size,
            isPageVisible: this.isPageVisible,
            intervals: Array.from(this.intervals.keys()),
            memory: 'memory' in performance ? {
                used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + 'MB',
                total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024) + 'MB',
                limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024) + 'MB'
            } : 'Not available'
        };
    }

    /**
     * Clean up all managed resources
     */
    cleanup() {
        // Clear all intervals
        this.intervals.forEach((interval, name) => {
            clearInterval(interval.id);
        });
        this.intervals.clear();
        
        // Clear all timeouts
        this.timeouts.forEach((timeoutId, name) => {
            clearTimeout(timeoutId);
        });
        this.timeouts.clear();
        
        // Disconnect all observers
        this.observers.forEach((observer, name) => {
            if (observer && typeof observer.disconnect === 'function') {
                observer.disconnect();
            }
        });
        this.observers.clear();
    }

    /**
     * Throttle function execution
     * @param {Function} func - Function to throttle
     * @param {number} limit - Throttle limit in milliseconds
     * @returns {Function} Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Debounce function execution
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @param {boolean} immediate - Execute immediately on first call
     * @returns {Function} Debounced function
     */
    debounce(func, wait, immediate = false) {
        let timeout;
        return function(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    }
}

// Create global instance
const performanceOptimizer = new PerformanceOptimizer();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        PerformanceOptimizer,
        performanceOptimizer
    };
}

// Make available globally
window.PerformanceOptimizer = PerformanceOptimizer;
window.performanceOptimizer = performanceOptimizer;