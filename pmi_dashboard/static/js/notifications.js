/**
 * Notification System
 * 
 * This module provides a simple toast notification system for user feedback.
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = new Map();
        this.init();
    }

    /**
     * Initialize the notification system
     */
    init() {
        this.createContainer();
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
     * Show a notification
     * @param {string} message - Message text
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Display duration in milliseconds (0 for persistent)
     * @returns {string} Notification ID
     */
    show(message, type = 'info', duration = 5000) {
        const id = this.generateId();
        const notification = this.createNotification(id, message, type, duration);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        // Trigger animation
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.remove(id);
            }, duration);
        }
        
        return id;
    }

    /**
     * Create a notification element
     * @param {string} id - Notification ID
     * @param {string} message - Message text
     * @param {string} type - Notification type
     * @param {number} duration - Display duration
     * @returns {HTMLElement} Notification element
     */
    createNotification(id, message, type, duration) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.setAttribute('data-id', id);
        
        const icon = this.getIcon(type);
        
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="notification-message">${this.escapeHtml(message)}</div>
                <button class="notification-close" aria-label="Close notification">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            ${duration > 0 ? `<div class="notification-progress" style="animation-duration: ${duration}ms;"></div>` : ''}
        `;
        
        // Bind close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.remove(id);
        });
        
        return notification;
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
}

// Global notification system instance
const notificationSystem = new NotificationSystem();

/**
 * Global function to show notifications
 * @param {string} message - Message text
 * @param {string} type - Notification type (success, error, warning, info)
 * @param {number} duration - Display duration in milliseconds
 * @returns {string} Notification ID
 */
function showNotification(message, type = 'info', duration = 5000) {
    return notificationSystem.show(message, type, duration);
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        NotificationSystem,
        showNotification
    };
}