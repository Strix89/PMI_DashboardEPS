/**
 * Enhanced Notification System with Error Handling
 * 
 * This module provides a comprehensive toast notification system for user feedback,
 * including error handling, recovery suggestions, and graceful degradation.
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.maxNotifications = 5;
        this.errorQueue = [];
        this.retryCallbacks = new Map();
        this.init();
    }

    /**
     * Initialize the notification system
     */
    init() {
        this.createContainer();
        this.addStyles();
        this.handleConnectionStatus();
        this.setupGlobalErrorHandler();
    }

    /**
     * Create the notification container
     */
    createContainer() {
        // Check if container already exists
        this.container = document.getElementById('notification-container');
        
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        }
    }

    /**
     * Show a notification with enhanced error handling
     * @param {string} message - Message text
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Display duration in milliseconds (0 for persistent)
     * @param {Object} options - Additional options
     * @returns {string} Notification ID
     */
    show(message, type = 'info', duration = 5000, options = {}) {
        // Manage notification queue to prevent spam
        if (this.notifications.size >= this.maxNotifications) {
            this.removeOldest();
        }

        const id = this.generateId();
        const notification = this.createNotification(id, message, type, duration, options);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        // Trigger animation
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });
        
        // Auto-remove after duration (except for errors which should be persistent by default)
        const actualDuration = type === 'error' && duration === 5000 ? 0 : duration;
        if (actualDuration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, actualDuration);
        }
        
        // Log error notifications for debugging
        if (type === 'error') {
            this.logError(message, options);
        }
        
        return id;
    }

    /**
     * Show error notification with recovery options
     * @param {string} message - Error message
     * @param {Object} options - Error options
     * @returns {string} Notification ID
     */
    showError(message, options = {}) {
        const {
            details = null,
            retryCallback = null,
            helpText = null,
            persistent = true
        } = options;

        let fullMessage = message;
        if (helpText) {
            fullMessage += `\n\nSuggestion: ${helpText}`;
        }

        const errorOptions = {
            ...options,
            details,
            retryCallback,
            helpText,
            showRetry: !!retryCallback
        };

        const id = this.show(fullMessage, 'error', persistent ? 0 : 10000, errorOptions);
        
        if (retryCallback) {
            this.retryCallbacks.set(id, retryCallback);
        }

        return id;
    }

    /**
     * Show success notification with optional action
     * @param {string} message - Success message
     * @param {Object} options - Success options
     * @returns {string} Notification ID
     */
    showSuccess(message, options = {}) {
        return this.show(message, 'success', options.duration || 3000, options);
    }

    /**
     * Show warning notification
     * @param {string} message - Warning message
     * @param {Object} options - Warning options
     * @returns {string} Notification ID
     */
    showWarning(message, options = {}) {
        return this.show(message, 'warning', options.duration || 5000, options);
    }

    /**
     * Show info notification
     * @param {string} message - Info message
     * @param {Object} options - Info options
     * @returns {string} Notification ID
     */
    showInfo(message, options = {}) {
        return this.show(message, 'info', options.duration || 4000, options);
    }

    /**
     * Create a notification element with enhanced features
     * @param {string} id - Notification ID
     * @param {string} message - Message text
     * @param {string} type - Notification type
     * @param {number} duration - Display duration
     * @param {Object} options - Additional options
     * @returns {HTMLElement} Notification element
     */
    createNotification(id, message, type, duration, options = {}) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.setAttribute('data-id', id);
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
        
        const icon = this.getIcon(type);
        const lines = message.split('\n');
        const mainMessage = lines[0];
        const additionalInfo = lines.slice(1).join('\n');
        
        let actionsHtml = '';
        if (options.showRetry && options.retryCallback) {
            actionsHtml += `
                <button class="notification-action notification-retry" aria-label="Retry operation">
                    <i class="fas fa-redo"></i>
                    <span>Retry</span>
                </button>
            `;
        }
        
        if (options.details) {
            actionsHtml += `
                <button class="notification-action notification-details" aria-label="Show details">
                    <i class="fas fa-info-circle"></i>
                    <span>Details</span>
                </button>
            `;
        }
        
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="notification-body">
                    <div class="notification-message">${this.escapeHtml(mainMessage)}</div>
                    ${additionalInfo ? `<div class="notification-additional">${this.escapeHtml(additionalInfo)}</div>` : ''}
                    ${options.details ? `<div class="notification-details" style="display: none;">${this.escapeHtml(options.details)}</div>` : ''}
                </div>
                <div class="notification-controls">
                    ${actionsHtml}
                    <button class="notification-close" aria-label="Close notification">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            ${duration > 0 ? `<div class="notification-progress" style="animation-duration: ${duration}ms;"></div>` : ''}
        `;
        
        // Bind event handlers
        this.bindNotificationEvents(notification, id, options);
        
        return notification;
    }

    /**
     * Bind event handlers to notification
     * @param {HTMLElement} notification - Notification element
     * @param {string} id - Notification ID
     * @param {Object} options - Notification options
     */
    bindNotificationEvents(notification, id, options) {
        // Close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.remove(id);
        });
        
        // Retry button
        const retryBtn = notification.querySelector('.notification-retry');
        if (retryBtn && options.retryCallback) {
            retryBtn.addEventListener('click', () => {
                this.handleRetry(id, options.retryCallback);
            });
        }
        
        // Details button
        const detailsBtn = notification.querySelector('.notification-details');
        if (detailsBtn) {
            detailsBtn.addEventListener('click', () => {
                this.toggleDetails(notification);
            });
        }
        
        // Keyboard navigation
        notification.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.remove(id);
            }
        });
        
        // Mobile swipe-to-dismiss
        if (this.isMobileDevice()) {
            this.setupSwipeToDismiss(notification, id);
        }
    }
    
    /**
     * Check if device is mobile
     * @returns {boolean} True if mobile device
     */
    isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (window.innerWidth <= 768) ||
               ('ontouchstart' in window);
    }
    
    /**
     * Setup swipe-to-dismiss functionality for mobile
     * @param {HTMLElement} notification - Notification element
     * @param {string} id - Notification ID
     */
    setupSwipeToDismiss(notification, id) {
        let startX = 0;
        let startY = 0;
        let currentX = 0;
        let isDragging = false;
        let startTime = 0;
        
        const handleTouchStart = (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            currentX = startX;
            isDragging = false;
            startTime = Date.now();
            notification.style.transition = 'none';
        };
        
        const handleTouchMove = (e) => {
            if (!startX) return;
            
            currentX = e.touches[0].clientX;
            const currentY = e.touches[0].clientY;
            const diffX = currentX - startX;
            const diffY = currentY - startY;
            
            // Only handle horizontal swipes
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 10) {
                isDragging = true;
                e.preventDefault();
                
                // Apply transform based on swipe direction
                const opacity = Math.max(0.3, 1 - Math.abs(diffX) / 200);
                notification.style.transform = `translateX(${diffX}px)`;
                notification.style.opacity = opacity;
            }
        };
        
        const handleTouchEnd = (e) => {
            if (!startX || !isDragging) {
                this.resetNotificationPosition(notification);
                return;
            }
            
            const diffX = currentX - startX;
            const diffTime = Date.now() - startTime;
            const velocity = Math.abs(diffX) / diffTime;
            
            // Determine if swipe should dismiss notification
            const shouldDismiss = Math.abs(diffX) > 100 || velocity > 0.5;
            
            if (shouldDismiss) {
                // Animate out and remove
                notification.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
                notification.style.transform = `translateX(${diffX > 0 ? '100%' : '-100%'})`;
                notification.style.opacity = '0';
                
                setTimeout(() => {
                    this.remove(id);
                }, 300);
            } else {
                // Snap back to original position
                this.resetNotificationPosition(notification);
            }
            
            // Reset tracking variables
            startX = 0;
            startY = 0;
            currentX = 0;
            isDragging = false;
        };
        
        const handleTouchCancel = () => {
            this.resetNotificationPosition(notification);
            startX = 0;
            startY = 0;
            currentX = 0;
            isDragging = false;
        };
        
        // Add touch event listeners
        notification.addEventListener('touchstart', handleTouchStart, { passive: true });
        notification.addEventListener('touchmove', handleTouchMove, { passive: false });
        notification.addEventListener('touchend', handleTouchEnd, { passive: true });
        notification.addEventListener('touchcancel', handleTouchCancel, { passive: true });
    }
    
    /**
     * Reset notification position after failed swipe
     * @param {HTMLElement} notification - Notification element
     */
    resetNotificationPosition(notification) {
        notification.style.transition = 'transform 0.2s ease, opacity 0.2s ease';
        notification.style.transform = 'translateX(0)';
        notification.style.opacity = '1';
        
        setTimeout(() => {
            notification.style.transition = '';
        }, 200);
    }

    /**
     * Handle retry action
     * @param {string} id - Notification ID
     * @param {Function} retryCallback - Retry callback function
     */
    async handleRetry(id, retryCallback) {
        const notification = this.notifications.get(id);
        if (!notification) return;
        
        // Show loading state
        const retryBtn = notification.querySelector('.notification-retry');
        if (retryBtn) {
            retryBtn.disabled = true;
            retryBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Retrying...</span>';
        }
        
        try {
            await retryCallback();
            this.remove(id);
            this.showSuccess('Operation completed successfully');
        } catch (error) {
            // Reset retry button
            if (retryBtn) {
                retryBtn.disabled = false;
                retryBtn.innerHTML = '<i class="fas fa-redo"></i><span>Retry</span>';
            }
            
            this.showError('Retry failed: ' + error.message, {
                retryCallback,
                helpText: 'Please check your connection and try again'
            });
        }
    }

    /**
     * Toggle details visibility
     * @param {HTMLElement} notification - Notification element
     */
    toggleDetails(notification) {
        const details = notification.querySelector('.notification-details');
        const detailsBtn = notification.querySelector('.notification-details');
        
        if (details) {
            const isVisible = details.style.display !== 'none';
            details.style.display = isVisible ? 'none' : 'block';
            
            if (detailsBtn) {
                const icon = detailsBtn.querySelector('i');
                const text = detailsBtn.querySelector('span');
                if (isVisible) {
                    icon.className = 'fas fa-info-circle';
                    text.textContent = 'Details';
                } else {
                    icon.className = 'fas fa-eye-slash';
                    text.textContent = 'Hide';
                }
            }
        }
    }

    /**
     * Remove a notification
     * @param {string} id - Notification ID
     */
    remove(id) {
        const notification = this.notifications.get(id);
        if (!notification) return;
        
        notification.classList.add('hide');
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            this.notifications.delete(id);
        }, 300);
    }

    /**
     * Clear all notifications
     */
    clear() {
        this.notifications.forEach((notification, id) => {
            this.remove(id);
        });
    }

    /**
     * Remove oldest notification to make room for new ones
     */
    removeOldest() {
        const oldestId = this.notifications.keys().next().value;
        if (oldestId) {
            this.remove(oldestId);
        }
    }

    /**
     * Log error for debugging purposes
     * @param {string} message - Error message
     * @param {Object} options - Error options
     */
    logError(message, options = {}) {
        const errorEntry = {
            timestamp: new Date().toISOString(),
            message,
            details: options.details,
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        this.errorQueue.push(errorEntry);
        
        // Keep only last 50 errors
        if (this.errorQueue.length > 50) {
            this.errorQueue.shift();
        }
        
        // Log to console for development
        console.error('Notification Error:', errorEntry);
        
        // In production, you might want to send this to a logging service
        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            this.sendErrorToLoggingService(errorEntry);
        }
    }

    /**
     * Send error to logging service (placeholder)
     * @param {Object} errorEntry - Error entry to log
     */
    sendErrorToLoggingService(errorEntry) {
        // This is a placeholder for actual logging service integration
        // You would implement actual error reporting here
        console.log('Would send to logging service:', errorEntry);
    }

    /**
     * Get error queue for debugging
     * @returns {Array} Error queue
     */
    getErrorQueue() {
        return [...this.errorQueue];
    }

    /**
     * Handle offline/online status changes
     */
    handleConnectionStatus() {
        window.addEventListener('online', () => {
            this.showSuccess('Connection restored', {
                duration: 3000
            });
        });
        
        window.addEventListener('offline', () => {
            this.showWarning('Connection lost. Some features may not work properly.', {
                persistent: true
            });
        });
    }

    /**
     * Get icon for notification type
     * @param {string} type - Notification type
     * @returns {string} Font Awesome icon class
     */
    getIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        
        return icons[type] || icons.info;
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Generate unique ID
     * @returns {string} Unique ID
     */
    generateId() {
        return 'notification-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Add notification styles to the page
     */
    addStyles() {
        if (document.getElementById('notification-system-styles')) {
            return; // Styles already added
        }

        const style = document.createElement('style');
        style.id = 'notification-system-styles';
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 420px;
                pointer-events: none;
            }

            .notification {
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                box-shadow: 0 8px 32px var(--shadow-heavy);
                margin-bottom: 12px;
                transform: translateX(100%);
                opacity: 0;
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: auto;
                max-width: 100%;
                word-wrap: break-word;
                position: relative;
                overflow: hidden;
            }

            .notification.show {
                transform: translateX(0);
                opacity: 1;
            }

            .notification.hide {
                transform: translateX(100%);
                opacity: 0;
            }

            .notification-content {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                padding: 16px;
            }

            .notification-icon {
                flex-shrink: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                margin-top: 2px;
            }

            .notification-icon i {
                font-size: 16px;
            }

            .notification-body {
                flex: 1;
                min-width: 0;
            }

            .notification-message {
                color: var(--text-primary);
                font-size: 14px;
                font-weight: 500;
                line-height: 1.4;
                margin-bottom: 4px;
            }

            .notification-additional {
                color: var(--text-secondary);
                font-size: 13px;
                line-height: 1.3;
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid var(--border-light);
            }

            .notification-details {
                color: var(--text-secondary);
                font-size: 12px;
                line-height: 1.3;
                margin-top: 8px;
                padding: 8px;
                background: var(--bg-secondary);
                border-radius: 6px;
                font-family: 'Courier New', monospace;
                white-space: pre-wrap;
                max-height: 120px;
                overflow-y: auto;
            }

            .notification-controls {
                display: flex;
                align-items: flex-start;
                gap: 4px;
                flex-shrink: 0;
            }

            .notification-action {
                background: none;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 6px 8px;
                font-size: 12px;
                display: flex;
                align-items: center;
                gap: 4px;
                transition: all 0.2s ease;
                white-space: nowrap;
            }

            .notification-action:hover:not(:disabled) {
                background: var(--bg-hover);
                color: var(--text-primary);
                border-color: var(--primary-orange);
            }

            .notification-action:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .notification-retry {
                color: var(--primary-orange);
                border-color: var(--primary-orange);
            }

            .notification-retry:hover:not(:disabled) {
                background: var(--primary-orange);
                color: white;
            }

            .notification-close {
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 6px;
                border-radius: 6px;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .notification-close:hover {
                background: var(--bg-hover);
                color: var(--text-primary);
            }

            .notification-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: var(--primary-orange);
                border-radius: 0 0 12px 12px;
                animation: notification-progress linear forwards;
                transform-origin: left;
            }

            @keyframes notification-progress {
                from { transform: scaleX(1); }
                to { transform: scaleX(0); }
            }

            /* Type-specific styles */
            .notification-success {
                border-left: 4px solid var(--success-color);
            }

            .notification-success .notification-icon {
                background: var(--success-color)20;
                color: var(--success-color);
            }

            .notification-error {
                border-left: 4px solid var(--error-color);
            }

            .notification-error .notification-icon {
                background: var(--error-color)20;
                color: var(--error-color);
            }

            .notification-warning {
                border-left: 4px solid var(--warning-color);
            }

            .notification-warning .notification-icon {
                background: var(--warning-color)20;
                color: var(--warning-color);
            }

            .notification-info {
                border-left: 4px solid var(--info-color);
            }

            .notification-info .notification-icon {
                background: var(--info-color)20;
                color: var(--info-color);
            }

            /* Responsive design */
            @media (max-width: 768px) {
                .notification-container {
                    top: 10px;
                    right: 10px;
                    left: 10px;
                    max-width: none;
                    /* Account for mobile safe areas */
                    top: max(10px, env(safe-area-inset-top));
                    right: max(10px, env(safe-area-inset-right));
                    left: max(10px, env(safe-area-inset-left));
                }

                .notification {
                    margin-bottom: 8px;
                    /* Enhanced mobile animations */
                    transform: translateY(-100%);
                }
                
                .notification.show {
                    transform: translateY(0);
                }
                
                .notification.hide {
                    transform: translateY(-100%);
                }

                .notification-content {
                    padding: 14px;
                    gap: 10px;
                }
                
                .notification-icon {
                    width: 28px;
                    height: 28px;
                }
                
                .notification-icon i {
                    font-size: 18px;
                }

                .notification-message {
                    font-size: 15px;
                    line-height: 1.5;
                }
                
                .notification-additional {
                    font-size: 14px;
                }

                .notification-controls {
                    flex-direction: column;
                    gap: 6px;
                    align-items: stretch;
                }

                .notification-action {
                    width: 100%;
                    justify-content: center;
                    padding: 10px 12px;
                    font-size: 14px;
                    min-height: 44px; /* Touch-friendly size */
                }
                
                .notification-close {
                    padding: 10px;
                    min-width: 44px;
                    min-height: 44px;
                }
                
                /* Swipe to dismiss on mobile */
                .notification {
                    touch-action: pan-x;
                }
            }
            
            /* Extra small mobile screens */
            @media (max-width: 480px) {
                .notification-container {
                    top: 5px;
                    right: 5px;
                    left: 5px;
                }
                
                .notification-content {
                    padding: 12px;
                }
                
                .notification-message {
                    font-size: 14px;
                }
                
                .notification-additional {
                    font-size: 13px;
                }
            }
            
            /* Touch device optimizations */
            @media (hover: none) and (pointer: coarse) {
                .notification-action,
                .notification-close {
                    min-height: 44px;
                    min-width: 44px;
                }
                
                .notification-action:active {
                    transform: scale(0.95);
                    background: var(--primary-orange-subtle);
                }
                
                .notification-close:active {
                    transform: scale(0.95);
                    background: var(--bg-hover);
                }
            }

            /* Accessibility improvements */
            @media (prefers-reduced-motion: reduce) {
                .notification {
                    transition-duration: 0.1s;
                }
                
                .notification-progress {
                    animation: none;
                    display: none;
                }
            }

            /* High contrast mode support */
            @media (prefers-contrast: high) {
                .notification {
                    border-width: 2px;
                }
                
                .notification-action {
                    border-width: 2px;
                }
            }
        `;
        
        document.head.appendChild(style);
    }

    /**
     * Setup global error handler for unhandled errors
     */
    setupGlobalErrorHandler() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            
            this.showError('An unexpected error occurred', {
                details: event.reason?.message || String(event.reason),
                helpText: 'Please refresh the page and try again'
            });
        });

        // Handle JavaScript errors
        window.addEventListener('error', (event) => {
            console.error('JavaScript error:', event.error);
            
            // Don't show notifications for script loading errors
            if (event.filename && event.filename.includes('.js')) {
                return;
            }
            
            this.showError('A JavaScript error occurred', {
                details: `${event.message} at ${event.filename}:${event.lineno}`,
                helpText: 'Please refresh the page and try again'
            });
        });
    }
}

// Global notification system instance
const notificationSystem = new NotificationSystem();

/**
 * Global function to show notifications
 * @param {string} message - Message text
 * @param {string} type - Notification type (success, error, warning, info)
 * @param {number} duration - Display duration in milliseconds
 * @param {Object} options - Additional options
 * @returns {string} Notification ID
 */
function showNotification(message, type = 'info', duration = 5000, options = {}) {
    return notificationSystem.show(message, type, duration, options);
}

/**
 * Show error notification with enhanced features
 * @param {string} message - Error message
 * @param {Object} options - Error options
 * @returns {string} Notification ID
 */
function showError(message, options = {}) {
    return notificationSystem.showError(message, options);
}

/**
 * Show success notification
 * @param {string} message - Success message
 * @param {Object} options - Success options
 * @returns {string} Notification ID
 */
function showSuccess(message, options = {}) {
    return notificationSystem.showSuccess(message, options);
}

/**
 * Show warning notification
 * @param {string} message - Warning message
 * @param {Object} options - Warning options
 * @returns {string} Notification ID
 */
function showWarning(message, options = {}) {
    return notificationSystem.showWarning(message, options);
}

/**
 * Show info notification
 * @param {string} message - Info message
 * @param {Object} options - Info options
 * @returns {string} Notification ID
 */
function showInfo(message, options = {}) {
    return notificationSystem.showInfo(message, options);
}

/**
 * Enhanced error handling utilities
 */
const ErrorHandler = {
    /**
     * Handle API errors with user-friendly messages and recovery suggestions
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     * @param {Function} retryCallback - Optional retry callback
     * @returns {string} Notification ID
     */
    handleApiError(error, operation = 'operation', retryCallback = null) {
        let message = `Failed to ${operation}`;
        let helpText = null;
        let details = error.message || 'Unknown error';

        // Categorize errors and provide specific help
        if (error.message) {
            if (error.message.includes('timeout') || error.message.includes('Request timeout')) {
                message = `${operation} timed out`;
                helpText = 'The request took too long. Check your network connection and try again.';
            } else if (error.message.includes('Authentication failed') || error.message.includes('401')) {
                message = `Authentication failed for ${operation}`;
                helpText = 'Please check your API credentials in the node configuration.';
            } else if (error.message.includes('Connection failed') || error.message.includes('Network Error')) {
                message = `Cannot connect to server for ${operation}`;
                helpText = 'Check if the Proxmox server is running and accessible from your network.';
            } else if (error.message.includes('403') || error.message.includes('Access denied')) {
                message = `Access denied for ${operation}`;
                helpText = 'Your API token may not have sufficient permissions for this operation.';
            } else if (error.message.includes('404') || error.message.includes('not found')) {
                message = `Resource not found for ${operation}`;
                helpText = 'The requested resource may have been deleted or moved.';
            } else if (error.message.includes('500') || error.message.includes('Internal Server Error')) {
                message = `Server error during ${operation}`;
                helpText = 'There was an internal server error. Please try again later.';
            } else if (error.message.includes('503') || error.message.includes('Service Unavailable')) {
                message = `Service unavailable for ${operation}`;
                helpText = 'The Proxmox service may be temporarily unavailable. Please try again later.';
            } else {
                message = `${operation} failed: ${error.message}`;
            }
        }

        return showError(message, {
            details,
            helpText,
            retryCallback
        });
    },

    /**
     * Handle connection errors specifically
     * @param {Error} error - Connection error
     * @param {string} nodeId - Node ID that failed
     * @param {Function} retryCallback - Retry callback
     * @returns {string} Notification ID
     */
    handleConnectionError(error, nodeId, retryCallback = null) {
        const message = `Connection to node ${nodeId} failed`;
        const helpText = 'Check if the node is online and your network connection is stable.';
        
        return showError(message, {
            details: error.message,
            helpText,
            retryCallback
        });
    },

    /**
     * Handle validation errors
     * @param {Object} validationErrors - Validation error object
     * @param {string} context - Context where validation failed
     * @returns {string} Notification ID
     */
    handleValidationError(validationErrors, context = 'form') {
        const errors = Array.isArray(validationErrors) ? validationErrors : [validationErrors];
        const message = `Validation failed for ${context}`;
        const details = errors.join('\n');
        const helpText = 'Please correct the highlighted fields and try again.';

        return showError(message, {
            details,
            helpText
        });
    },

    /**
     * Handle offline scenarios
     * @param {string} operation - Operation that was attempted offline
     * @returns {string} Notification ID
     */
    handleOfflineError(operation) {
        const message = `Cannot ${operation} while offline`;
        const helpText = 'Please check your internet connection and try again when online.';

        return showError(message, {
            helpText,
            persistent: true
        });
    },

    /**
     * Show graceful degradation message
     * @param {string} feature - Feature that's degraded
     * @param {string} reason - Reason for degradation
     * @returns {string} Notification ID
     */
    showGracefulDegradation(feature, reason) {
        const message = `${feature} is running in limited mode`;
        const helpText = `${reason}. Some features may not be available.`;

        return showWarning(message, {
            helpText,
            duration: 8000
        });
    }
};

/**
 * Network status monitor for graceful degradation
 */
const NetworkMonitor = {
    isOnline: navigator.onLine,
    offlineNodes: new Set(),

    init() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            showSuccess('Connection restored');
            this.retryOfflineOperations();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            showWarning('You are now offline. Some features may not work properly.', {
                persistent: true
            });
        });
    },

    /**
     * Mark a node as offline
     * @param {string} nodeId - Node ID
     */
    markNodeOffline(nodeId) {
        this.offlineNodes.add(nodeId);
        ErrorHandler.showGracefulDegradation(
            `Node ${nodeId}`,
            'Node is currently unreachable'
        );
    },

    /**
     * Mark a node as online
     * @param {string} nodeId - Node ID
     */
    markNodeOnline(nodeId) {
        if (this.offlineNodes.has(nodeId)) {
            this.offlineNodes.delete(nodeId);
            showSuccess(`Node ${nodeId} is back online`);
        }
    },

    /**
     * Check if a node is offline
     * @param {string} nodeId - Node ID
     * @returns {boolean} True if node is offline
     */
    isNodeOffline(nodeId) {
        return this.offlineNodes.has(nodeId);
    },

    /**
     * Retry operations for nodes that came back online
     */
    retryOfflineOperations() {
        // This would trigger retry of failed operations
        // Implementation depends on your specific retry mechanism
        console.log('Retrying offline operations...');
    }
};

// Initialize network monitor
NetworkMonitor.init();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        NotificationSystem,
        showNotification,
        showError,
        showSuccess,
        showWarning,
        showInfo,
        ErrorHandler,
        NetworkMonitor
    };
}