/**
 * Performance Configuration for PMI Dashboard
 * 
 * This module provides performance optimization settings and utilities
 * for the PMI Dashboard application.
 */

// Performance configuration object
window.PerformanceConfig = {
    // Animation settings
    animations: {
        enabled: true,
        duration: 300,
        easing: 'ease-in-out'
    },
    
    // Refresh intervals (in milliseconds)
    refreshIntervals: {
        nodes: 10000,        // 10 seconds
        resources: 5000,     // 5 seconds
        metrics: 3000        // 3 seconds
    },
    
    // Debounce delays (in milliseconds)
    debounceDelays: {
        search: 300,
        resize: 250,
        scroll: 100
    },
    
    // Throttle limits (in milliseconds)
    throttleLimits: {
        scroll: 16,          // ~60fps
        resize: 100,
        mousemove: 16
    },
    
    // Memory management
    memory: {
        maxCacheSize: 100,   // Maximum cached items
        cleanupInterval: 300000  // 5 minutes
    },
    
    // Network settings
    network: {
        timeout: 30000,      // 30 seconds
        retryAttempts: 3,
        retryDelay: 1000     // 1 second
    }
};

// Detect device capabilities
window.PerformanceConfig.device = {
    isLowEnd: navigator.deviceMemory ? navigator.deviceMemory < 4 : false,
    isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
    supportsWebGL: !!window.WebGLRenderingContext,
    supportsWorkers: !!window.Worker,
    connectionType: navigator.connection ? navigator.connection.effectiveType : 'unknown'
};

// Adjust settings based on device capabilities
if (window.PerformanceConfig.device.isLowEnd) {
    window.PerformanceConfig.animations.enabled = false;
    window.PerformanceConfig.refreshIntervals.nodes = 15000;
    window.PerformanceConfig.refreshIntervals.resources = 10000;
    window.PerformanceConfig.refreshIntervals.metrics = 5000;
}

if (window.PerformanceConfig.device.isMobile) {
    window.PerformanceConfig.throttleLimits.scroll = 32; // ~30fps for mobile
    window.PerformanceConfig.debounceDelays.resize = 500;
}

// Utility functions
window.PerformanceConfig.utils = {
    /**
     * Debounce function
     */
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },
    
    /**
     * Throttle function
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    /**
     * Request animation frame with fallback
     */
    requestAnimFrame: window.requestAnimationFrame || 
                     window.webkitRequestAnimationFrame || 
                     window.mozRequestAnimationFrame || 
                     function(callback) { setTimeout(callback, 1000 / 60); },
    
    /**
     * Check if animations should be enabled
     */
    shouldAnimate: function() {
        return window.PerformanceConfig.animations.enabled && 
               !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
};

console.log('Performance configuration loaded');