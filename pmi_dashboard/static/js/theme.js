/**
 * Theme Management System
 * Handles light/dark theme switching with localStorage persistence
 */

class ThemeManager {
    constructor() {
        this.storageKey = 'pmi-dashboard-theme';
        this.defaultTheme = 'dark';
        this.currentTheme = this.getStoredTheme() || this.defaultTheme;
        
        this.init();
    }
    
    /**
     * Initialize the theme system
     */
    init() {
        // Sync with preloaded theme
        const currentDataTheme = document.documentElement.getAttribute('data-theme');
        if (currentDataTheme) {
            this.currentTheme = currentDataTheme;
        }
        
        // Apply the current theme with full functionality
        this.applyTheme(this.currentTheme);
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Listen for system theme changes
        this.setupSystemThemeListener();
        
        // Log initialization
        console.log(`Theme system initialized with ${this.currentTheme} theme`);
    }
    
    /**
     * Set up event listeners for theme toggle
     */
    setupEventListeners() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                this.toggleTheme();
            });
            
            // Add keyboard support
            themeToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
        }
    }
    
    /**
     * Listen for system theme preference changes
     */
    setupSystemThemeListener() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                if (!this.getStoredTheme()) {
                    const systemTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(systemTheme);
                    this.currentTheme = systemTheme;
                }
            });
        }
    }
    
    /**
     * Toggle between light and dark themes
     */
    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        
        // Add haptic feedback on supported devices
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Announce theme change to screen readers
        this.announceThemeChange(newTheme);
    }
    
    /**
     * Set a specific theme
     * @param {string} theme - 'light' or 'dark'
     */
    setTheme(theme) {
        if (theme !== 'light' && theme !== 'dark') {
            console.warn(`Invalid theme: ${theme}. Using default theme: ${this.defaultTheme}`);
            theme = this.defaultTheme;
        }
        
        this.currentTheme = theme;
        this.applyTheme(theme);
        this.storeTheme(theme);
        
        // Dispatch custom event for other components to listen to
        this.dispatchThemeChangeEvent(theme);
    }
    
    /**
     * Apply theme to the document
     * @param {string} theme - Theme to apply
     */
    applyTheme(theme) {
        const html = document.documentElement;
        
        // Add transition class for smooth theme switching
        html.classList.add('theme-transitioning');
        
        // Set the theme attribute with animation
        requestAnimationFrame(() => {
            html.setAttribute('data-theme', theme);
            
            // Update theme toggle button aria-label and title
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                const newLabel = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
                const currentThemeLabel = theme === 'dark' ? 'Dark theme active' : 'Light theme active';
                
                themeToggle.setAttribute('aria-label', newLabel);
                themeToggle.setAttribute('title', newLabel);
                
                // Add visual feedback for screen readers
                const srText = themeToggle.querySelector('.sr-only') || document.createElement('span');
                srText.className = 'sr-only';
                srText.textContent = currentThemeLabel;
                if (!themeToggle.querySelector('.sr-only')) {
                    themeToggle.appendChild(srText);
                }
            }
            
            // Update meta theme-color for mobile browsers
            this.updateMetaThemeColor(theme);
        });
        
        // Remove transition class after animation completes
        setTimeout(() => {
            html.classList.remove('theme-transitioning');
        }, 300);
    }
    
    /**
     * Store theme preference in localStorage
     * @param {string} theme - Theme to store
     */
    storeTheme(theme) {
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch (error) {
            console.warn('Failed to store theme preference:', error);
        }
    }
    
    /**
     * Get stored theme preference from localStorage
     * @returns {string|null} Stored theme or null if not found
     */
    getStoredTheme() {
        try {
            return localStorage.getItem(this.storageKey);
        } catch (error) {
            console.warn('Failed to retrieve theme preference:', error);
            return null;
        }
    }
    
    /**
     * Get the current theme
     * @returns {string} Current theme
     */
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    /**
     * Check if current theme is dark
     * @returns {boolean} True if dark theme is active
     */
    isDarkTheme() {
        return this.currentTheme === 'dark';
    }
    
    /**
     * Check if current theme is light
     * @returns {boolean} True if light theme is active
     */
    isLightTheme() {
        return this.currentTheme === 'light';
    }
    
    /**
     * Dispatch custom theme change event
     * @param {string} theme - New theme
     */
    dispatchThemeChangeEvent(theme) {
        const event = new CustomEvent('themechange', {
            detail: {
                theme: theme,
                isDark: theme === 'dark',
                isLight: theme === 'light'
            }
        });
        
        document.dispatchEvent(event);
    }
    
    /**
     * Get system theme preference
     * @returns {string} System theme preference ('dark' or 'light')
     */
    getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    /**
     * Reset theme to system preference
     */
    resetToSystemTheme() {
        const systemTheme = this.getSystemTheme();
        this.setTheme(systemTheme);
        
        // Clear stored preference to follow system changes
        try {
            localStorage.removeItem(this.storageKey);
        } catch (error) {
            console.warn('Failed to clear theme preference:', error);
        }
    }
    
    /**
     * Update meta theme-color for mobile browsers
     * @param {string} theme - Current theme
     */
    updateMetaThemeColor(theme) {
        let metaThemeColor = document.querySelector('meta[name="theme-color"]');
        
        if (!metaThemeColor) {
            metaThemeColor = document.createElement('meta');
            metaThemeColor.name = 'theme-color';
            document.head.appendChild(metaThemeColor);
        }
        
        // Set theme color based on current theme
        const themeColors = {
            dark: '#1a1a1a',
            light: '#ffffff'
        };
        
        metaThemeColor.content = themeColors[theme] || themeColors.dark;
    }
    
    /**
     * Preload theme to prevent flash of unstyled content
     */
    preloadTheme() {
        const storedTheme = this.getStoredTheme();
        const systemTheme = this.getSystemTheme();
        const initialTheme = storedTheme || systemTheme || this.defaultTheme;
        
        // Apply theme immediately without transitions
        document.documentElement.setAttribute('data-theme', initialTheme);
        this.currentTheme = initialTheme;
        
        // Update meta theme color
        this.updateMetaThemeColor(initialTheme);
    }
    
    /**
     * Announce theme change to screen readers
     * @param {string} theme - New theme
     */
    announceThemeChange(theme) {
        const announcement = `Switched to ${theme} theme`;
        
        // Create or update live region for announcements
        let liveRegion = document.getElementById('theme-announcer');
        if (!liveRegion) {
            liveRegion = document.createElement('div');
            liveRegion.id = 'theme-announcer';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            document.body.appendChild(liveRegion);
        }
        
        // Clear and set new announcement
        liveRegion.textContent = '';
        setTimeout(() => {
            liveRegion.textContent = announcement;
        }, 100);
    }
    
    /**
     * Get theme statistics for debugging
     * @returns {Object} Theme statistics
     */
    getThemeStats() {
        return {
            currentTheme: this.currentTheme,
            storedTheme: this.getStoredTheme(),
            systemTheme: this.getSystemTheme(),
            defaultTheme: this.defaultTheme,
            isDarkTheme: this.isDarkTheme(),
            isLightTheme: this.isLightTheme(),
            supportsSystemTheme: window.matchMedia ? true : false
        };
    }
}

// Preload theme to prevent flash of unstyled content
(function() {
    const storageKey = 'pmi-dashboard-theme';
    const defaultTheme = 'dark';
    
    function getStoredTheme() {
        try {
            return localStorage.getItem(storageKey);
        } catch (error) {
            return null;
        }
    }
    
    function getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }
    
    const storedTheme = getStoredTheme();
    const systemTheme = getSystemTheme();
    const initialTheme = storedTheme || defaultTheme;
    
    // Apply theme immediately to prevent flash
    document.documentElement.setAttribute('data-theme', initialTheme);
    
    // Add meta theme-color
    const metaThemeColor = document.createElement('meta');
    metaThemeColor.name = 'theme-color';
    metaThemeColor.content = initialTheme === 'dark' ? '#1a1a1a' : '#ffffff';
    document.head.appendChild(metaThemeColor);
})();

// Add enhanced transition styles for theme switching
const themeTransitionStyles = `
    .theme-transitioning {
        pointer-events: none;
    }
    
    .theme-transitioning *,
    .theme-transitioning *:before,
    .theme-transitioning *:after {
        transition: background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                   color 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                   border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                   box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        transition-delay: 0s !important;
    }
`;

// Inject transition styles
const styleSheet = document.createElement('style');
styleSheet.id = 'theme-transition-styles';
styleSheet.textContent = themeTransitionStyles;
document.head.appendChild(styleSheet);

// Initialize theme manager when DOM is ready
let themeManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        themeManager = new ThemeManager();
    });
} else {
    themeManager = new ThemeManager();
}

// Export for use in other modules
window.ThemeManager = ThemeManager;
window.themeManager = themeManager;