/**
 * Comprehensive Error Handler for PMI Dashboard
 * 
 * This module provides centralized error handling, logging, and user feedback
 * for all application errors, with graceful degradation for offline scenarios.
 */

// Prevent duplicate declarations
if (typeof window.ErrorHandler !== 'undefined') {
    console.warn('ErrorHandler already exists, skipping redefinition');
} else {

class ErrorHandler {
    constructor() {
        this.errorQueue = [];
        this.maxErrorQueue = 100;
        this.offlineNodes = new Set();
        this.retryAttempts = new Map();
        this.maxRetryAttempts = 3;
        
        this.init();
    }

    /**
     * Initialize error handler
     */
    init() {
        this.setupGlobalErrorHandlers();
        this.setupNetworkMonitoring();
        this.setupPerformanceMonitoring();
    }

    /**
     * Setup global error handlers
     */
    setupGlobalErrorHandlers() {
        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleUnhandledError(event.reason, 'unhandled_promise');
            event.preventDefault(); // Prevent console error
        });

        // JavaScript errors
        window.addEventListener('error', (event) => {
            // Skip script loading errors
            if (event.filename && event.filename.includes('.js') && event.message.includes('Loading')) {
                return;
            }
            
            this.handleUnhandledError(event.error || event.message, 'javascript_error', {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });

        // Resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target !== window && event.target.tagName) {
                this.handleResourceError(event.target);
            }
        }, true);
    }

    /**
     * Setup network monitoring
     */
    setupNetworkMonitoring() {
        // Online/offline detection
        window.addEventListener('online', () => {
            this.handleNetworkStatusChange(true);
        });

        window.addEventListener('offline', () => {
            this.handleNetworkStatusChange(false);
        });

        // Monitor connection quality
        if ('connection' in navigator) {
            navigator.connection.addEventListener('change', () => {
                this.handleConnectionChange(navigator.connection);
            });
        }
    }

    /**
     * Setup performance monitoring
     */
    setupPerformanceMonitoring() {
        // Monitor long tasks with throttling to reduce noise
        if ('PerformanceObserver' in window) {
            try {
                let lastLogTime = 0;
                const LOG_THROTTLE_MS = 5000; // Only log performance issues every 5 seconds
                
                const observer = new PerformanceObserver((list) => {
                    const now = Date.now();
                    if (now - lastLogTime < LOG_THROTTLE_MS) {
                        return; // Throttle performance logging
                    }
                    
                    for (const entry of list.getEntries()) {
                        if (entry.duration > 100) { // Only log tasks longer than 100ms (more significant)
                            this.logPerformanceIssue(entry);
                            lastLogTime = now;
                            break; // Only log one issue per throttle period
                        }
                    }
                });
                observer.observe({ entryTypes: ['longtask'] });
            } catch (e) {
                console.warn('Performance monitoring not available:', e);
            }
        }
    }

    /**
     * Handle API errors with context and recovery options
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     * @param {Object} context - Additional context
     * @param {Function} retryCallback - Retry function
     * @returns {string} Error ID for tracking
     */
    handleApiError(error, operation = 'operation', context = {}, retryCallback = null) {
        const errorId = this.generateErrorId();
        
        // Categorize error
        const errorCategory = this.categorizeError(error);
        
        // Create error entry
        const errorEntry = {
            id: errorId,
            timestamp: new Date().toISOString(),
            type: 'api_error',
            category: errorCategory,
            operation,
            message: error.message || 'Unknown error',
            context: {
                ...context,
                url: window.location.href,
                userAgent: navigator.userAgent,
                stack: error.stack
            }
        };

        // Log error
        this.logError(errorEntry);

        // Determine user message and help text
        const { userMessage, helpText, recoveryActions } = this.getErrorMessages(error, operation, errorCategory);

        // Show notification with recovery options
        const notificationOptions = {
            details: error.message,
            helpText,
            recoveryActions
        };

        if (retryCallback && this.shouldAllowRetry(errorId, errorCategory)) {
            notificationOptions.retryCallback = () => this.handleRetry(errorId, retryCallback);
        }

        if (typeof showError !== 'undefined') {
            showError(userMessage, notificationOptions);
        } else {
            console.error('Error notification system not available:', userMessage);
        }

        return errorId;
    }

    /**
     * Handle connection errors specifically
     * @param {Error} error - Connection error
     * @param {string} nodeId - Node ID
     * @param {Function} retryCallback - Retry callback
     * @returns {string} Error ID
     */
    handleConnectionError(error, nodeId, retryCallback = null) {
        // Mark node as offline
        this.markNodeOffline(nodeId);

        return this.handleApiError(error, `connect to node ${nodeId}`, { nodeId }, retryCallback);
    }

    /**
     * Handle validation errors
     * @param {Array|Object} errors - Validation errors
     * @param {string} context - Context where validation failed
     * @returns {string} Error ID
     */
    handleValidationError(errors, context = 'form') {
        const errorArray = Array.isArray(errors) ? errors : [errors];
        const message = `Validation failed for ${context}`;
        const details = errorArray.join('\n');

        if (typeof showError !== 'undefined') {
            return showError(message, {
                details,
                helpText: 'Please correct the highlighted fields and try again'
            });
        }

        return this.generateErrorId();
    }

    /**
     * Handle unhandled errors
     * @param {Error|string} error - Error object or message
     * @param {string} type - Error type
     * @param {Object} context - Additional context
     */
    handleUnhandledError(error, type, context = {}) {
        const errorEntry = {
            id: this.generateErrorId(),
            timestamp: new Date().toISOString(),
            type: 'unhandled_error',
            subtype: type,
            message: error?.message || String(error),
            context: {
                ...context,
                url: window.location.href,
                userAgent: navigator.userAgent,
                stack: error?.stack
            }
        };

        this.logError(errorEntry);

        // Only show notification for critical errors
        if (type === 'unhandled_promise' && typeof showError !== 'undefined') {
            showError('An unexpected error occurred', {
                details: errorEntry.message,
                helpText: 'Please refresh the page and try again'
            });
        }
    }

    /**
     * Handle resource loading errors
     * @param {HTMLElement} element - Failed element
     */
    handleResourceError(element) {
        const errorEntry = {
            id: this.generateErrorId(),
            timestamp: new Date().toISOString(),
            type: 'resource_error',
            element: element.tagName,
            src: element.src || element.href,
            context: {
                url: window.location.href
            }
        };

        this.logError(errorEntry);

        // Show notification for critical resources
        if (element.tagName === 'SCRIPT' && typeof showWarning !== 'undefined') {
            showWarning('Some features may not work properly due to a loading error', {
                helpText: 'Please refresh the page to reload all resources'
            });
        }
    }

    /**
     * Handle network status changes
     * @param {boolean} isOnline - Whether the network is online
     */
    handleNetworkStatusChange(isOnline) {
        if (isOnline) {
            if (typeof showSuccess !== 'undefined') {
                showSuccess('Connection restored');
            }
            this.retryOfflineOperations();
        } else {
            if (typeof showWarning !== 'undefined') {
                showWarning('You are now offline. Some features may not work properly.', {
                    persistent: true
                });
            }
        }
    }

    /**
     * Handle connection quality changes
     * @param {NetworkInformation} connection - Connection object
     */
    handleConnectionChange(connection) {
        if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
            if (typeof showInfo !== 'undefined') {
                showInfo('Slow connection detected. Some features may be limited.', {
                    duration: 5000
                });
            }
        }
    }

    /**
     * Categorize error for better handling
     * @param {Error} error - Error object
     * @returns {string} Error category
     */
    categorizeError(error) {
        const message = error.message?.toLowerCase() || '';
        
        if (message.includes('timeout') || error.code === 'TIMEOUT') {
            return 'timeout';
        } else if (message.includes('network') || error.code === 'NETWORK_ERROR') {
            return 'network';
        } else if (message.includes('auth') || error.status === 401) {
            return 'authentication';
        } else if (error.status === 403) {
            return 'authorization';
        } else if (error.status === 404) {
            return 'not_found';
        } else if (error.status >= 500) {
            return 'server_error';
        } else if (error.status >= 400) {
            return 'client_error';
        } else {
            return 'unknown';
        }
    }

    /**
     * Get user-friendly error messages
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     * @param {string} category - Error category
     * @returns {Object} Message object
     */
    getErrorMessages(error, operation, category) {
        const messages = {
            timeout: {
                userMessage: `${operation} timed out`,
                helpText: 'The request took too long. Check your network connection and try again.',
                recoveryActions: ['Check network connection', 'Try again', 'Contact support if problem persists']
            },
            network: {
                userMessage: `Cannot connect for ${operation}`,
                helpText: 'Check if the server is running and accessible from your network.',
                recoveryActions: ['Check server status', 'Verify network connectivity', 'Try again later']
            },
            authentication: {
                userMessage: `Authentication failed for ${operation}`,
                helpText: 'Please check your API credentials in the node configuration.',
                recoveryActions: ['Verify API token', 'Check token permissions', 'Update credentials']
            },
            authorization: {
                userMessage: `Access denied for ${operation}`,
                helpText: 'Your API token may not have sufficient permissions for this operation.',
                recoveryActions: ['Check token permissions', 'Contact administrator', 'Use different credentials']
            },
            not_found: {
                userMessage: `Resource not found for ${operation}`,
                helpText: 'The requested resource may have been deleted or moved.',
                recoveryActions: ['Refresh the page', 'Check resource exists', 'Try different resource']
            },
            server_error: {
                userMessage: `Server error during ${operation}`,
                helpText: 'There was an internal server error. Please try again later.',
                recoveryActions: ['Try again later', 'Check server logs', 'Contact administrator']
            },
            client_error: {
                userMessage: `Request error for ${operation}`,
                helpText: 'There was an issue with the request. Please check your input.',
                recoveryActions: ['Check input data', 'Verify request format', 'Try again']
            },
            unknown: {
                userMessage: `${operation} failed`,
                helpText: 'An unexpected error occurred. Please try again.',
                recoveryActions: ['Try again', 'Refresh page', 'Contact support']
            }
        };

        return messages[category] || messages.unknown;
    }

    /**
     * Check if retry should be allowed
     * @param {string} errorId - Error ID
     * @param {string} category - Error category
     * @returns {boolean} Whether retry is allowed
     */
    shouldAllowRetry(errorId, category) {
        const retryableCategories = ['timeout', 'network', 'server_error'];
        
        if (!retryableCategories.includes(category)) {
            return false;
        }

        const attempts = this.retryAttempts.get(errorId) || 0;
        return attempts < this.maxRetryAttempts;
    }

    /**
     * Handle retry attempt
     * @param {string} errorId - Error ID
     * @param {Function} retryCallback - Retry function
     */
    async handleRetry(errorId, retryCallback) {
        const attempts = this.retryAttempts.get(errorId) || 0;
        this.retryAttempts.set(errorId, attempts + 1);

        try {
            await retryCallback();
            this.retryAttempts.delete(errorId);
            
            if (typeof showSuccess !== 'undefined') {
                showSuccess('Operation completed successfully');
            }
        } catch (error) {
            const newAttempts = this.retryAttempts.get(errorId) || 0;
            
            if (newAttempts >= this.maxRetryAttempts) {
                this.retryAttempts.delete(errorId);
                
                if (typeof showError !== 'undefined') {
                    showError('Maximum retry attempts reached', {
                        details: error.message,
                        helpText: 'Please try again later or contact support'
                    });
                }
            } else {
                this.handleApiError(error, 'retry operation', { originalErrorId: errorId }, retryCallback);
            }
        }
    }

    /**
     * Mark node as offline
     * @param {string} nodeId - Node ID
     */
    markNodeOffline(nodeId) {
        this.offlineNodes.add(nodeId);
        
        if (typeof showWarning !== 'undefined') {
            showWarning(`Node ${nodeId} is offline`, {
                helpText: 'Some features for this node may not be available',
                duration: 8000
            });
        }
    }

    /**
     * Mark node as online
     * @param {string} nodeId - Node ID
     */
    markNodeOnline(nodeId) {
        if (this.offlineNodes.has(nodeId)) {
            this.offlineNodes.delete(nodeId);
            
            if (typeof showSuccess !== 'undefined') {
                showSuccess(`Node ${nodeId} is back online`);
            }
        }
    }

    /**
     * Check if node is offline
     * @param {string} nodeId - Node ID
     * @returns {boolean} Whether node is offline
     */
    isNodeOffline(nodeId) {
        return this.offlineNodes.has(nodeId);
    }

    /**
     * Retry offline operations
     */
    retryOfflineOperations() {
        // Clear offline nodes and let them be re-detected
        this.offlineNodes.clear();
        
        // Trigger refresh of node status
        if (typeof window.dashboard !== 'undefined' && window.dashboard.refreshNodes) {
            window.dashboard.refreshNodes();
        }
    }

    /**
     * Log error to queue and console
     * @param {Object} errorEntry - Error entry
     */
    logError(errorEntry) {
        // Add to error queue
        this.errorQueue.push(errorEntry);
        
        // Maintain queue size
        if (this.errorQueue.length > this.maxErrorQueue) {
            this.errorQueue.shift();
        }

        // Log to console
        console.error('Error logged:', errorEntry);

        // In production, send to logging service
        if (this.shouldSendToLoggingService()) {
            this.sendToLoggingService(errorEntry);
        }
    }

    /**
     * Log performance issue
     * @param {PerformanceEntry} entry - Performance entry
     */
    logPerformanceIssue(entry) {
        const perfEntry = {
            id: this.generateErrorId(),
            timestamp: new Date().toISOString(),
            type: 'performance_issue',
            name: entry.name,
            duration: Math.round(entry.duration),
            startTime: Math.round(entry.startTime)
        };

        // Only log to console in development mode and only for significant issues
        if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && 
            perfEntry.duration > 200) { // Only log tasks longer than 200ms
            console.warn('Performance issue detected:', perfEntry);
        }
        
        // Add to error queue for tracking but don't spam console in production
        this.errorQueue.push(perfEntry);
        if (this.errorQueue.length > this.maxErrorQueue) {
            this.errorQueue.shift();
        }
    }

    /**
     * Check if errors should be sent to logging service
     * @returns {boolean} Whether to send to logging service
     */
    shouldSendToLoggingService() {
        return window.location.hostname !== 'localhost' && 
               window.location.hostname !== '127.0.0.1' &&
               !window.location.hostname.includes('dev');
    }

    /**
     * Send error to logging service (placeholder)
     * @param {Object} errorEntry - Error entry
     */
    sendToLoggingService(errorEntry) {
        // This would integrate with your actual logging service
        console.log('Would send to logging service:', errorEntry);
    }

    /**
     * Generate unique error ID
     * @returns {string} Error ID
     */
    generateErrorId() {
        return 'err_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Get error statistics
     * @returns {Object} Error statistics
     */
    getErrorStats() {
        const stats = {
            totalErrors: this.errorQueue.length,
            errorsByType: {},
            errorsByCategory: {},
            recentErrors: this.errorQueue.slice(-10)
        };

        this.errorQueue.forEach(error => {
            stats.errorsByType[error.type] = (stats.errorsByType[error.type] || 0) + 1;
            if (error.category) {
                stats.errorsByCategory[error.category] = (stats.errorsByCategory[error.category] || 0) + 1;
            }
        });

        return stats;
    }

    /**
     * Clear error queue
     */
    clearErrorQueue() {
        this.errorQueue = [];
        this.retryAttempts.clear();
    }
}

// Create global error handler instance
const globalErrorHandler = new ErrorHandler();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ErrorHandler,
        globalErrorHandler
    };
}

// Make available globally
window.ErrorHandler = ErrorHandler;
window.globalErrorHandler = globalErrorHandler;

} // End of duplicate prevention check