/**
 * Main JavaScript for PMI Dashboard
 * Handles navigation, tab switching, and general UI interactions
 */

class PMIDashboard {
    constructor() {
        this.currentTab = 'proxmox'; // Default active tab
        this.tabs = ['health', 'acronis', 'proxmox', 'anomaly'];
        
        this.init();
    }
    
    /**
     * Initialize the dashboard
     */
    init() {
        this.setupNavigation();
        this.setupEventListeners();
        this.setupAccessibility();
        
        // Set initial active tab
        this.setActiveTab(this.currentTab);
        
        console.log('PMI Dashboard initialized');
    }
    
    /**
     * Set up navigation tab functionality
     */
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = link.getAttribute('data-tab');
                this.switchTab(tabName);
            });
            
            // Keyboard navigation support
            link.addEventListener('keydown', (e) => {
                this.handleTabKeyNavigation(e);
            });
        });
    }
    
    /**
     * Handle keyboard navigation for tabs
     * @param {KeyboardEvent} e - Keyboard event
     */
    handleTabKeyNavigation(e) {
        const currentLink = e.target;
        const allLinks = Array.from(document.querySelectorAll('.nav-link'));
        const currentIndex = allLinks.indexOf(currentLink);
        
        let targetIndex = currentIndex;
        
        switch (e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                targetIndex = currentIndex > 0 ? currentIndex - 1 : allLinks.length - 1;
                break;
            case 'ArrowRight':
                e.preventDefault();
                targetIndex = currentIndex < allLinks.length - 1 ? currentIndex + 1 : 0;
                break;
            case 'Home':
                e.preventDefault();
                targetIndex = 0;
                break;
            case 'End':
                e.preventDefault();
                targetIndex = allLinks.length - 1;
                break;
            case 'Enter':
            case ' ':
                e.preventDefault();
                const tabName = currentLink.getAttribute('data-tab');
                this.switchTab(tabName);
                return;
        }
        
        if (targetIndex !== currentIndex) {
            allLinks[targetIndex].focus();
        }
    }
    
    /**
     * Switch to a specific tab
     * @param {string} tabName - Name of the tab to switch to
     */
    switchTab(tabName) {
        if (!this.tabs.includes(tabName)) {
            console.warn(`Invalid tab: ${tabName}`);
            return;
        }
        
        // Handle development tabs
        if (['health', 'acronis', 'anomaly'].includes(tabName)) {
            this.showDevelopmentMessage(tabName);
            return;
        }
        
        this.setActiveTab(tabName);
        this.currentTab = tabName;
        
        // Dispatch custom event for tab change
        this.dispatchTabChangeEvent(tabName);
    }
    
    /**
     * Set the active tab visually
     * @param {string} tabName - Name of the tab to activate
     */
    setActiveTab(tabName) {
        // Remove active class from all tabs
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            link.setAttribute('aria-selected', 'false');
        });
        
        // Add active class to selected tab
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) {
            activeTab.classList.add('active');
            activeTab.setAttribute('aria-selected', 'true');
        }
    }
    
    /**
     * Show development message for tabs under development
     * @param {string} tabName - Name of the tab
     */
    showDevelopmentMessage(tabName) {
        const tabDisplayName = tabName.toUpperCase();
        
        // Create and show a temporary notification
        this.showNotification(
            `${tabDisplayName} module is under development`,
            'info',
            3000
        );
    }
    
    /**
     * Show a notification message
     * @param {string} message - Message to display
     * @param {string} type - Type of notification ('info', 'success', 'warning', 'error')
     * @param {number} duration - Duration in milliseconds (0 for persistent)
     */
    showNotification(message, type = 'info', duration = 5000) {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(notification => notification.remove());
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="notification-icon ${this.getNotificationIcon(type)}"></i>
                <span class="notification-message">${message}</span>
                <button class="notification-close" aria-label="Close notification">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add styles for notification
        this.addNotificationStyles();
        
        // Add to document
        document.body.appendChild(notification);
        
        // Set up close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            this.removeNotification(notification);
        });
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification);
            }, duration);
        }
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 10);
    }
    
    /**
     * Get icon for notification type
     * @param {string} type - Notification type
     * @returns {string} Icon class
     */
    getNotificationIcon(type) {
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle'
        };
        return icons[type] || icons.info;
    }
    
    /**
     * Remove notification with animation
     * @param {HTMLElement} notification - Notification element to remove
     */
    removeNotification(notification) {
        notification.classList.add('notification-hide');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }
    
    /**
     * Add notification styles to document
     */
    addNotificationStyles() {
        if (document.getElementById('notification-styles')) {
            return; // Styles already added
        }
        
        const styles = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                max-width: 400px;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                box-shadow: 0 4px 12px var(--shadow-medium);
                transform: translateX(100%);
                transition: transform 0.3s ease, opacity 0.3s ease;
                opacity: 0;
            }
            
            .notification-show {
                transform: translateX(0);
                opacity: 1;
            }
            
            .notification-hide {
                transform: translateX(100%);
                opacity: 0;
            }
            
            .notification-content {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px;
            }
            
            .notification-icon {
                font-size: 18px;
                flex-shrink: 0;
            }
            
            .notification-info .notification-icon {
                color: var(--info-color);
            }
            
            .notification-success .notification-icon {
                color: var(--success-color);
            }
            
            .notification-warning .notification-icon {
                color: var(--warning-color);
            }
            
            .notification-error .notification-icon {
                color: var(--error-color);
            }
            
            .notification-message {
                flex: 1;
                color: var(--text-primary);
                font-size: 14px;
                line-height: 1.4;
            }
            
            .notification-close {
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: all 0.2s ease;
                flex-shrink: 0;
            }
            
            .notification-close:hover {
                background: var(--bg-hover);
                color: var(--text-primary);
            }
            
            @media (max-width: 480px) {
                .notification {
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = 'notification-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
    
    /**
     * Set up general event listeners
     */
    setupEventListeners() {
        // Listen for theme changes
        document.addEventListener('themechange', (e) => {
            console.log('Theme changed to:', e.detail.theme);
        });
        
        // Handle window resize for responsive behavior
        window.addEventListener('resize', this.debounce(() => {
            this.handleResize();
        }, 250));
        
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleGlobalKeyboard(e);
        });
    }
    
    /**
     * Handle window resize events
     */
    handleResize() {
        // Add any resize-specific logic here
        console.log('Window resized');
    }
    
    /**
     * Handle global keyboard shortcuts
     * @param {KeyboardEvent} e - Keyboard event
     */
    handleGlobalKeyboard(e) {
        // Alt + number keys for tab switching
        if (e.altKey && !e.ctrlKey && !e.shiftKey) {
            const keyNum = parseInt(e.key);
            if (keyNum >= 1 && keyNum <= this.tabs.length) {
                e.preventDefault();
                const tabName = this.tabs[keyNum - 1];
                this.switchTab(tabName);
            }
        }
        
        // Alt + T for theme toggle
        if (e.altKey && e.key.toLowerCase() === 't') {
            e.preventDefault();
            if (window.themeManager) {
                window.themeManager.toggleTheme();
            }
        }
    }
    
    /**
     * Set up accessibility features
     */
    setupAccessibility() {
        // Add skip link for keyboard navigation
        this.addSkipLink();
        
        // Ensure proper ARIA attributes
        this.setupARIA();
    }
    
    /**
     * Add skip link for accessibility
     */
    addSkipLink() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link sr-only';
        skipLink.textContent = 'Skip to main content';
        skipLink.addEventListener('focus', () => {
            skipLink.classList.remove('sr-only');
        });
        skipLink.addEventListener('blur', () => {
            skipLink.classList.add('sr-only');
        });
        
        document.body.insertBefore(skipLink, document.body.firstChild);
    }
    
    /**
     * Set up ARIA attributes for accessibility
     */
    setupARIA() {
        const mainContent = document.querySelector('.app-main');
        if (mainContent && !mainContent.id) {
            mainContent.id = 'main-content';
        }
    }
    
    /**
     * Dispatch custom tab change event
     * @param {string} tabName - Name of the new active tab
     */
    dispatchTabChangeEvent(tabName) {
        const event = new CustomEvent('tabchange', {
            detail: {
                tab: tabName,
                previousTab: this.currentTab
            }
        });
        
        document.dispatchEvent(event);
    }
    
    /**
     * Debounce utility function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Get current active tab
     * @returns {string} Current active tab name
     */
    getCurrentTab() {
        return this.currentTab;
    }
}

// Initialize dashboard when DOM is ready
let dashboard;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        dashboard = new PMIDashboard();
    });
} else {
    dashboard = new PMIDashboard();
}

// Export for use in other modules
window.PMIDashboard = PMIDashboard;
window.dashboard = dashboard;