/**
 * Main JavaScript for PMI Dashboard
 * Handles navigation, tab switching, and general UI interactions
 */

class PMIDashboard {
    constructor() {
        this.currentTab = 'proxmox'; // Default active tab
        this.tabs = ['health', 'acronis', 'proxmox', 'anomaly'];
        this.isMobile = this.detectMobile();
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.isScrolling = false;
        
        this.init();
    }
    
    /**
     * Initialize the dashboard
     */
    init() {
        this.setupNavigation();
        this.setupEventListeners();
        this.setupAccessibility();
        this.setupMobileOptimizations();
        this.setupTouchGestures();
        
        // Set initial active tab
        this.setActiveTab(this.currentTab);
        
        console.log(`PMI Dashboard initialized (${this.isMobile ? 'Mobile' : 'Desktop'} mode)`);
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
        if (['health', 'anomaly'].includes(tabName)) {
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
        
        // Use the enhanced notification system if available
        if (window.notificationSystem) {
            window.notificationSystem.showInfo(`${tabDisplayName} module is under development`, {
                duration: 3000,
                helpText: 'This feature will be available in a future release'
            });
        } else if (typeof showInfo !== 'undefined') {
            showInfo(`${tabDisplayName} module is under development`, {
                duration: 3000
            });
        } else {
            // Fallback to console logging
            console.info(`${tabDisplayName} module is under development`);
        }
    }

    /**
     * Basic notification fallback method
     * @param {string} message - Message text
     * @param {string} type - Message type
     * @param {number} duration - Display duration
     */
    showNotification(message, type = 'info', duration = 5000) {
        if (window.notificationSystem) {
            return window.notificationSystem.show(message, type, duration);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
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
        
        // Handle keyboard shortcuts (desktop only)
        if (!this.isMobile) {
            document.addEventListener('keydown', (e) => {
                this.handleGlobalKeyboard(e);
            });
        }
        
        // Handle orientation changes on mobile
        if (this.isMobile) {
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    this.handleOrientationChange();
                }, 100);
            });
        }
        
        // Handle visibility changes for mobile optimization
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });
    }
    
    /**
     * Handle window resize events
     */
    handleResize() {
        // Add any resize-specific logic here
        // Removed console.log to reduce noise
        
        // Update mobile detection
        this.isMobile = this.detectMobile();
        
        // Trigger custom resize event for other components
        const resizeEvent = new CustomEvent('dashboardResize', {
            detail: { isMobile: this.isMobile }
        });
        document.dispatchEvent(resizeEvent);
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
    
    /**
     * Detect if device is mobile
     * @returns {boolean} True if mobile device
     */
    detectMobile() {
        const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isMobileWidth = window.innerWidth <= 768;
        const hasTouchSupport = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
        const isFoldable = window.screen && window.screen.isExtended;
        
        // Consider foldable devices in expanded mode as desktop-like
        if (isFoldable && window.innerWidth > 1024) {
            return false;
        }
        
        return isMobileUA || isMobileWidth || hasTouchSupport;
    }
    
    /**
     * Setup mobile-specific optimizations
     */
    setupMobileOptimizations() {
        if (!this.isMobile) return;
        
        // Add mobile class to body
        document.body.classList.add('mobile-device');
        
        // Optimize viewport for mobile
        this.optimizeViewport();
        
        // Setup mobile navigation enhancements
        this.setupMobileNavigation();
        
        // Prevent zoom on form inputs
        this.preventFormZoom();
        
        // Setup pull-to-refresh prevention
        this.setupPullToRefreshPrevention();
        
        console.log('Mobile optimizations applied');
    }
    
    /**
     * Setup touch gesture support
     */
    setupTouchGestures() {
        if (!this.isMobile) return;
        
        const navContainer = document.querySelector('.nav-tabs');
        if (!navContainer) return;
        
        // Add touch event listeners for tab swiping
        navContainer.addEventListener('touchstart', (e) => {
            this.handleTouchStart(e);
        }, { passive: true });
        
        navContainer.addEventListener('touchmove', (e) => {
            this.handleTouchMove(e);
        }, { passive: false });
        
        navContainer.addEventListener('touchend', (e) => {
            this.handleTouchEnd(e);
        }, { passive: true });
        
        // Add swipe gesture support for main content
        const mainContent = document.querySelector('.app-main');
        if (mainContent) {
            mainContent.addEventListener('touchstart', (e) => {
                this.handleContentTouchStart(e);
            }, { passive: true });
            
            mainContent.addEventListener('touchmove', (e) => {
                this.handleContentTouchMove(e);
            }, { passive: false });
            
            mainContent.addEventListener('touchend', (e) => {
                this.handleContentTouchEnd(e);
            }, { passive: true });
        }
    }
    
    /**
     * Handle touch start for navigation
     * @param {TouchEvent} e - Touch event
     */
    handleTouchStart(e) {
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
        this.isScrolling = false;
    }
    
    /**
     * Handle touch move for navigation
     * @param {TouchEvent} e - Touch event
     */
    handleTouchMove(e) {
        if (!this.touchStartX || !this.touchStartY) return;
        
        const touchX = e.touches[0].clientX;
        const touchY = e.touches[0].clientY;
        const diffX = this.touchStartX - touchX;
        const diffY = this.touchStartY - touchY;
        
        // Determine if user is scrolling vertically
        if (Math.abs(diffY) > Math.abs(diffX)) {
            this.isScrolling = true;
            return;
        }
        
        // Prevent horizontal scrolling during swipe
        if (Math.abs(diffX) > 10 && !this.isScrolling) {
            e.preventDefault();
        }
    }
    
    /**
     * Handle touch end for navigation
     * @param {TouchEvent} e - Touch event
     */
    handleTouchEnd(e) {
        if (!this.touchStartX || this.isScrolling) {
            this.resetTouch();
            return;
        }
        
        const touchEndX = e.changedTouches[0].clientX;
        const diffX = this.touchStartX - touchEndX;
        const threshold = 50; // Minimum swipe distance
        
        if (Math.abs(diffX) > threshold) {
            if (diffX > 0) {
                // Swipe left - next tab
                this.switchToNextTab();
            } else {
                // Swipe right - previous tab
                this.switchToPreviousTab();
            }
        }
        
        this.resetTouch();
    }
    
    /**
     * Handle content touch start
     * @param {TouchEvent} e - Touch event
     */
    handleContentTouchStart(e) {
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
    }
    
    /**
     * Handle content touch move
     * @param {TouchEvent} e - Touch event
     */
    handleContentTouchMove(e) {
        // Allow normal scrolling
    }
    
    /**
     * Handle content touch end
     * @param {TouchEvent} e - Touch event
     */
    handleContentTouchEnd(e) {
        if (!this.touchStartX) return;
        
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = this.touchStartX - touchEndX;
        const diffY = this.touchStartY - touchEndY;
        const threshold = 100; // Larger threshold for content swipes
        
        // Only handle horizontal swipes that are significantly larger than vertical
        if (Math.abs(diffX) > threshold && Math.abs(diffX) > Math.abs(diffY) * 2) {
            if (diffX > 0) {
                this.switchToNextTab();
            } else {
                this.switchToPreviousTab();
            }
        }
        
        this.resetTouch();
    }
    
    /**
     * Reset touch tracking variables
     */
    resetTouch() {
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.isScrolling = false;
    }
    
    /**
     * Switch to next tab
     */
    switchToNextTab() {
        const currentIndex = this.tabs.indexOf(this.currentTab);
        const nextIndex = (currentIndex + 1) % this.tabs.length;
        this.switchTab(this.tabs[nextIndex]);
    }
    
    /**
     * Switch to previous tab
     */
    switchToPreviousTab() {
        const currentIndex = this.tabs.indexOf(this.currentTab);
        const prevIndex = currentIndex === 0 ? this.tabs.length - 1 : currentIndex - 1;
        this.switchTab(this.tabs[prevIndex]);
    }
    
    /**
     * Optimize viewport for mobile
     */
    optimizeViewport() {
        // Ensure viewport meta tag is properly configured
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        
        // Set optimal viewport configuration
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover';
        
        // Add mobile-web-app-capable for better mobile experience
        if (!document.querySelector('meta[name="mobile-web-app-capable"]')) {
            const mobileCapable = document.createElement('meta');
            mobileCapable.name = 'mobile-web-app-capable';
            mobileCapable.content = 'yes';
            document.head.appendChild(mobileCapable);
        }
        
        // Add apple-mobile-web-app-capable for iOS
        if (!document.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
            const appleCapable = document.createElement('meta');
            appleCapable.name = 'apple-mobile-web-app-capable';
            appleCapable.content = 'yes';
            document.head.appendChild(appleCapable);
        }
        
        // Add apple-mobile-web-app-status-bar-style
        if (!document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]')) {
            const statusBar = document.createElement('meta');
            statusBar.name = 'apple-mobile-web-app-status-bar-style';
            statusBar.content = 'black-translucent';
            document.head.appendChild(statusBar);
        }
    }
    
    /**
     * Setup mobile navigation enhancements
     */
    setupMobileNavigation() {
        const navTabs = document.querySelector('.nav-tabs');
        if (!navTabs) return;
        
        // Add scroll indicators for horizontal navigation
        this.addScrollIndicators(navTabs);
        
        // Improve touch feedback
        this.enhanceTouchFeedback();
        
        // Add haptic feedback support
        this.setupHapticFeedback();
    }
    
    /**
     * Add scroll indicators for navigation
     * @param {Element} container - Navigation container
     */
    addScrollIndicators(container) {
        // Add scroll shadows to indicate more content
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const parent = entry.target.parentElement;
                if (entry.isIntersecting) {
                    if (entry.target === parent.firstElementChild) {
                        parent.classList.remove('scroll-left');
                    }
                    if (entry.target === parent.lastElementChild) {
                        parent.classList.remove('scroll-right');
                    }
                } else {
                    if (entry.target === parent.firstElementChild) {
                        parent.classList.add('scroll-left');
                    }
                    if (entry.target === parent.lastElementChild) {
                        parent.classList.add('scroll-right');
                    }
                }
            });
        }, { threshold: 1.0 });
        
        const firstTab = container.firstElementChild;
        const lastTab = container.lastElementChild;
        
        if (firstTab) observer.observe(firstTab);
        if (lastTab && lastTab !== firstTab) observer.observe(lastTab);
    }
    
    /**
     * Enhance touch feedback for interactive elements
     */
    enhanceTouchFeedback() {
        const interactiveElements = document.querySelectorAll('.nav-link, .btn, .theme-toggle-btn');
        
        interactiveElements.forEach(element => {
            element.addEventListener('touchstart', () => {
                element.classList.add('touch-active');
            }, { passive: true });
            
            element.addEventListener('touchend', () => {
                setTimeout(() => {
                    element.classList.remove('touch-active');
                }, 150);
            }, { passive: true });
            
            element.addEventListener('touchcancel', () => {
                element.classList.remove('touch-active');
            }, { passive: true });
        });
    }
    
    /**
     * Setup haptic feedback for supported devices
     */
    setupHapticFeedback() {
        if (!navigator.vibrate) return;
        
        // Add haptic feedback to navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navigator.vibrate(25); // Short vibration
            });
        });
        
        // Add haptic feedback to theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                navigator.vibrate(50); // Medium vibration
            });
        }
    }
    
    /**
     * Prevent zoom on form inputs (iOS Safari)
     */
    preventFormZoom() {
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.style.fontSize === '' || parseFloat(input.style.fontSize) < 16) {
                input.style.fontSize = '16px';
            }
        });
    }
    
    /**
     * Setup pull-to-refresh prevention
     */
    setupPullToRefreshPrevention() {
        let startY = 0;
        
        document.addEventListener('touchstart', (e) => {
            startY = e.touches[0].pageY;
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            const y = e.touches[0].pageY;
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // Prevent pull-to-refresh when at top of page and pulling down
            if (scrollTop === 0 && y > startY) {
                e.preventDefault();
            }
        }, { passive: false });
    }
    
    /**
     * Handle orientation change
     */
    handleOrientationChange() {
        // Force layout recalculation
        document.body.style.height = '100vh';
        setTimeout(() => {
            document.body.style.height = '';
        }, 100);
        
        // Update mobile detection
        this.isMobile = this.detectMobile();
        
        // Handle foldable device state changes
        this.handleFoldableDeviceChange();
        
        // Adjust UI for new orientation
        this.adjustUIForOrientation();
        
        // Scroll to top to fix potential layout issues
        window.scrollTo(0, 0);
        
        console.log('Orientation changed, layout updated');
    }
    
    /**
     * Handle foldable device state changes
     */
    handleFoldableDeviceChange() {
        if (window.screen && window.screen.isExtended !== undefined) {
            const isExtended = window.screen.isExtended;
            document.body.classList.toggle('foldable-extended', isExtended);
            
            // Dispatch event for other components
            document.dispatchEvent(new CustomEvent('foldablechange', {
                detail: { isExtended }
            }));
        }
    }
    
    /**
     * Adjust UI elements for current orientation
     */
    adjustUIForOrientation() {
        const isLandscape = window.innerWidth > window.innerHeight;
        document.body.classList.toggle('landscape-mode', isLandscape);
        
        // Adjust navigation for landscape on mobile
        if (this.isMobile && isLandscape) {
            this.optimizeForLandscape();
        }
    }
    
    /**
     * Optimize UI for landscape mode on mobile
     */
    optimizeForLandscape() {
        const header = document.querySelector('.app-header');
        if (header && window.innerHeight < 500) {
            header.style.position = 'static';
        } else if (header) {
            header.style.position = '';
        }
    }
    
    /**
     * Handle visibility change for mobile optimization
     */
    handleVisibilityChange() {
        if (document.hidden) {
            // App is hidden - pause any intensive operations
            this.pauseOperations();
        } else {
            // App is visible - resume operations
            this.resumeOperations();
        }
    }
    
    /**
     * Pause operations when app is hidden
     */
    pauseOperations() {
        // Dispatch event for other modules to pause operations
        document.dispatchEvent(new CustomEvent('apppaused'));
    }
    
    /**
     * Resume operations when app becomes visible
     */
    resumeOperations() {
        // Dispatch event for other modules to resume operations
        document.dispatchEvent(new CustomEvent('appresumed'));
    }
}

// Initialize dashboard when DOM is ready
let dashboard;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        dashboard = new PMIDashboard();
        initializeNotificationSystem();
    });
} else {
    dashboard = new PMIDashboard();
    initializeNotificationSystem();
}

/**
 * Initialize the notification system for global use
 */
function initializeNotificationSystem() {
    // Ensure notification system is available globally
    if (typeof NotificationSystem !== 'undefined' && !window.notificationSystem) {
        window.notificationSystem = new NotificationSystem();
        console.log('Global notification system initialized');
    }
    
    // Create convenience functions for backward compatibility
    if (window.notificationSystem) {
        window.showNotification = (message, type, duration, options) => {
            return window.notificationSystem.show(message, type, duration, options);
        };
        
        window.showSuccess = (message, options) => {
            return window.notificationSystem.showSuccess(message, options);
        };
        
        window.showError = (message, options) => {
            return window.notificationSystem.showError(message, options);
        };
        
        window.showWarning = (message, options) => {
            return window.notificationSystem.showWarning(message, options);
        };
        
        window.showInfo = (message, options) => {
            return window.notificationSystem.showInfo(message, options);
        };
    }
}

// Export for use in other modules
window.PMIDashboard = PMIDashboard;
window.dashboard = dashboard;