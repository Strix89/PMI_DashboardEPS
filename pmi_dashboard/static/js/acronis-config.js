/**
 * Acronis Configuration Management JavaScript Module
 * 
 * This module handles the Acronis API credentials configuration interface,
 * including saving, updating, deleting, and testing API configurations.
 * 
 * Requirements covered:
 * - 1.1: Configuration interface for API credentials
 * - 1.2: Client-side validation for required fields
 * - 1.4: Error handling and user feedback for configuration operations
 */

class AcronisConfigManager {
    constructor() {
        this.baseUrl = '/api/acronis';
        this.currentConfig = null;

        this.init();
    }

    /**
     * Initialize the Acronis configuration manager
     */
    init() {
        this.setupEventListeners();
        this.setupFormValidation();

        console.log('Acronis Configuration Manager initialized');
    }

    /**
     * Set up event listeners for the configuration interface
     */
    setupEventListeners() {
        // Configuration form submission
        const configForm = document.getElementById('acronis-config-form');
        if (configForm) {
            configForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Test connection button
        const testConnectionBtn = document.getElementById('test-connection-btn');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', () => this.testConnection());
        }

        // Cancel configuration button
        const cancelConfigBtn = document.getElementById('cancel-config-btn');
        if (cancelConfigBtn) {
            cancelConfigBtn.addEventListener('click', () => this.cancelConfiguration());
        }

        // Listen for successful configuration operations
        document.addEventListener('acronisConfigUpdated', () => {
            // Notify the main Acronis manager to refresh
            if (window.acronisManager) {
                window.acronisManager.checkInitialConfiguration();
            }
        });
    }

    /**
     * Set up form validation
     */
    setupFormValidation() {
        const form = document.getElementById('acronis-config-form');
        if (!form) return;

        const inputs = form.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });

        // Real-time validation for specific fields
        const baseUrlInput = document.getElementById('acronis-base-url');
        if (baseUrlInput) {
            baseUrlInput.addEventListener('input', () => this.validateBaseUrl(baseUrlInput));
        }

        const clientIdInput = document.getElementById('acronis-client-id');
        if (clientIdInput) {
            clientIdInput.addEventListener('input', () => this.validateClientId(clientIdInput));
        }

        const clientSecretInput = document.getElementById('acronis-client-secret');
        if (clientSecretInput) {
            clientSecretInput.addEventListener('input', () => this.validateClientSecret(clientSecretInput));
        }
    }

    /**
     * Load existing configuration into the form
     */
    async loadConfiguration() {
        try {
            const response = await this.makeRequest('GET', '/config');

            if (response && response.success && response.config) {
                this.currentConfig = response.config;
                this.populateForm(response.config);
                return true;
            } else {
                this.currentConfig = null;
                this.resetForm();
                return false;
            }
        } catch (error) {
            console.error('Failed to load configuration:', error);
            this.handleError(error, 'load configuration');
            return false;
        }
    }

    /**
     * Populate form with configuration data
     * @param {Object} config - Configuration data
     */
    populateForm(config) {
        document.getElementById('acronis-base-url').value = config.base_url || '';
        document.getElementById('acronis-client-id').value = config.client_id || '';
        document.getElementById('acronis-client-secret').value = config.client_secret || '';
        document.getElementById('acronis-grant-type').value = config.grant_type || 'client_credentials';
    }

    /**
     * Reset the form to default state
     */
    resetForm() {
        const form = document.getElementById('acronis-config-form');
        if (form) {
            form.reset();

            // Reset validation states
            const inputs = form.querySelectorAll('.form-control');
            inputs.forEach(input => {
                input.classList.remove('is-invalid', 'is-valid');
            });

            // Clear error messages
            const errorElements = form.querySelectorAll('.invalid-feedback');
            errorElements.forEach(element => {
                element.textContent = '';
            });

            // Set default values
            document.getElementById('acronis-grant-type').value = 'client_credentials';
        }

        // Hide test result
        this.hideTestResult();
    }

    /**
     * Handle form submission with enhanced notification integration
     * @param {Event} e - Form submit event
     */
    async handleFormSubmit(e) {
        e.preventDefault();

        if (!this.validateForm()) {
            this.showValidationFeedback(['Please fix the form errors before saving']);
            return;
        }

        const formData = this.getFormData();
        const saveBtn = document.getElementById('save-config-btn');
        const isUpdate = !!this.currentConfig;
        const operation = isUpdate ? 'update configuration' : 'save configuration';

        try {
            this.setButtonLoading(saveBtn, true);

            // Show loading notification
            const loadingId = this.showNotification(
                `${isUpdate ? 'Updating' : 'Saving'} Acronis configuration...`,
                'info',
                0,
                {
                    showSpinner: true,
                    id: 'acronis-config-save'
                }
            );

            let result;
            if (isUpdate) {
                result = await this.makeRequest('PUT', '/config', formData);
            } else {
                result = await this.makeRequest('POST', '/config', formData);
            }

            // Remove loading notification
            if (window.notificationSystem && window.notificationSystem.remove) {
                window.notificationSystem.remove('acronis-config-save');
            }

            if (result && result.success) {
                const action = isUpdate ? 'updated' : 'saved';
                this.showNotification(
                    `Acronis configuration ${action} successfully!`,
                    'success',
                    3000,
                    {
                        helpText: 'You can now use the Acronis backup monitoring features'
                    }
                );

                this.currentConfig = formData;

                // Notify that configuration was updated
                document.dispatchEvent(new CustomEvent('acronisConfigUpdated'));

                // Switch to dashboard view after successful save
                if (window.acronisManager) {
                    setTimeout(() => {
                        window.acronisManager.showDashboardView();
                    }, 1500);
                }
            } else {
                throw new Error(result.error || 'Failed to save configuration');
            }

        } catch (error) {
            console.error('Failed to save configuration:', error);

            // Remove loading notification
            if (window.notificationSystem && window.notificationSystem.remove) {
                window.notificationSystem.remove('acronis-config-save');
            }

            this.handleError(error, operation);
        } finally {
            this.setButtonLoading(saveBtn, false);
        }
    }

    /**
     * Get form data as object
     * @returns {Object} Form data
     */
    getFormData() {
        return {
            base_url: document.getElementById('acronis-base-url').value.trim(),
            client_id: document.getElementById('acronis-client-id').value.trim(),
            client_secret: document.getElementById('acronis-client-secret').value.trim(),
            grant_type: document.getElementById('acronis-grant-type').value.trim()
        };
    }

    /**
     * Validate the entire form
     * @returns {boolean} True if form is valid
     */
    validateForm() {
        const form = document.getElementById('acronis-config-form');
        let isValid = true;

        // Validate required fields
        const requiredInputs = form.querySelectorAll('input[required]');
        requiredInputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        // Validate specific fields
        const baseUrlInput = document.getElementById('acronis-base-url');
        if (!this.validateBaseUrl(baseUrlInput)) {
            isValid = false;
        }

        const clientIdInput = document.getElementById('acronis-client-id');
        if (!this.validateClientId(clientIdInput)) {
            isValid = false;
        }

        const clientSecretInput = document.getElementById('acronis-client-secret');
        if (!this.validateClientSecret(clientSecretInput)) {
            isValid = false;
        }

        return isValid;
    }

    /**
     * Validate a single field
     * @param {HTMLElement} input - Input element to validate
     * @returns {boolean} True if field is valid
     */
    validateField(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';

        if (input.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = 'This field is required';
        }

        this.setFieldValidation(input, isValid, errorMessage);
        return isValid;
    }

    /**
     * Validate base URL field
     * @param {HTMLElement} input - Base URL input element
     * @returns {boolean} True if base URL is valid
     */
    validateBaseUrl(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';

        if (!value) {
            isValid = false;
            errorMessage = 'Base URL is required';
        } else {
            try {
                const url = new URL(value);
                if (!['http:', 'https:'].includes(url.protocol)) {
                    isValid = false;
                    errorMessage = 'URL must use HTTP or HTTPS protocol';
                }
            } catch (e) {
                isValid = false;
                errorMessage = 'Please enter a valid URL';
            }
        }

        this.setFieldValidation(input, isValid, errorMessage);
        return isValid;
    }

    /**
     * Validate client ID field
     * @param {HTMLElement} input - Client ID input element
     * @returns {boolean} True if client ID is valid
     */
    validateClientId(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';

        if (!value) {
            isValid = false;
            errorMessage = 'Client ID is required';
        } else if (value.length < 3) {
            isValid = false;
            errorMessage = 'Client ID must be at least 3 characters long';
        }

        this.setFieldValidation(input, isValid, errorMessage);
        return isValid;
    }

    /**
     * Validate client secret field
     * @param {HTMLElement} input - Client secret input element
     * @returns {boolean} True if client secret is valid
     */
    validateClientSecret(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';

        if (!value) {
            isValid = false;
            errorMessage = 'Client Secret is required';
        } else if (value.length < 8) {
            isValid = false;
            errorMessage = 'Client Secret must be at least 8 characters long';
        }

        this.setFieldValidation(input, isValid, errorMessage);
        return isValid;
    }

    /**
     * Set field validation state
     * @param {HTMLElement} input - Input element
     * @param {boolean} isValid - Whether field is valid
     * @param {string} errorMessage - Error message to display
     */
    setFieldValidation(input, isValid, errorMessage) {
        const formGroup = input.closest('.form-group');
        let feedbackElement = formGroup ? formGroup.querySelector('.invalid-feedback') : null;

        // Create feedback element if it doesn't exist
        if (!feedbackElement && formGroup) {
            feedbackElement = document.createElement('div');
            feedbackElement.className = 'invalid-feedback';
            formGroup.appendChild(feedbackElement);
        }

        if (isValid) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            if (feedbackElement) {
                feedbackElement.textContent = '';
            }
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
            if (feedbackElement) {
                feedbackElement.textContent = errorMessage;
            }
        }
    }

    /**
     * Clear field error state
     * @param {HTMLElement} input - Input element
     */
    clearFieldError(input) {
        input.classList.remove('is-invalid');
        const formGroup = input.closest('.form-group');
        const feedbackElement = formGroup ? formGroup.querySelector('.invalid-feedback') : null;
        if (feedbackElement) {
            feedbackElement.textContent = '';
        }
    }

    /**
     * Test connection to Acronis API with enhanced notification integration
     */
    async testConnection() {
        if (!this.validateForm()) {
            this.showValidationFeedback(['Please fix form errors before testing connection']);
            return;
        }

        const formData = this.getFormData();
        const testBtn = document.getElementById('test-connection-btn');

        try {
            this.setButtonLoading(testBtn, true);
            this.showTestResult('Testing connection...', 'loading');
            this.showConnectionTestProgress('testing');

            const result = await this.makeRequest('POST', '/test-connection', formData);

            if (result && result.success) {
                const successMessage = 'Connection successful! API credentials are valid.';
                this.showTestResult(successMessage, 'success');
                this.showConnectionTestProgress('success', successMessage);
            } else {
                const message = result.error || result.message || 'Connection failed';
                this.showTestResult(message, 'error');
                this.showConnectionTestProgress('failed', message);
            }

        } catch (error) {
            console.error('Connection test failed:', error);

            // Extract more specific error message
            let errorMessage = error.message;
            let helpText = 'Please check your configuration and try again.';

            if (error.message && error.message.includes('Authentication failed')) {
                errorMessage = 'Authentication failed. Please check your Client ID and Client Secret.';
                helpText = 'Verify that your API credentials are correct and have the necessary permissions.';
            } else if (error.message && error.message.includes('Connection failed')) {
                errorMessage = 'Cannot connect to Acronis server. Please check the Base URL and network connectivity.';
                helpText = 'Ensure the Base URL is correct and the Acronis server is accessible from your network.';
            } else if (error.message && error.message.includes('timeout')) {
                errorMessage = 'Connection timeout. Please check if the Acronis server is accessible.';
                helpText = 'The server may be slow to respond or unreachable. Check your network connection.';
            }

            const fullMessage = `Connection failed: ${errorMessage}`;
            this.showTestResult(fullMessage, 'error');
            this.showConnectionTestProgress('failed', fullMessage);

            // Use enhanced error handling for detailed feedback
            if (window.globalErrorHandler) {
                window.globalErrorHandler.handleApiError(error, 'test Acronis API connection', {
                    module: 'acronis-config',
                    operation: 'connection-test',
                    formData: { ...formData, client_secret: '[REDACTED]' } // Don't log sensitive data
                }, () => this.testConnection());
            }

        } finally {
            this.setButtonLoading(testBtn, false);
        }
    }

    /**
     * Show connection test result
     * @param {string} message - Result message
     * @param {string} type - Result type (loading, success, error)
     */
    showTestResult(message, type) {
        const resultDiv = document.getElementById('connection-test-result');
        if (!resultDiv) return;

        const iconElement = resultDiv.querySelector('.test-result-icon');
        const messageElement = resultDiv.querySelector('.test-result-message');

        // Update icon
        if (iconElement) {
            iconElement.className = `test-result-icon ${this.getTestResultIcon(type)}`;
        }

        // Update message
        if (messageElement) {
            messageElement.textContent = message;
        }

        // Update styling
        resultDiv.className = `test-result test-result-${type}`;
        resultDiv.style.display = 'block';

        // Auto-hide after delay (except for loading)
        if (type !== 'loading') {
            setTimeout(() => {
                this.hideTestResult();
            }, 5000);
        }
    }

    /**
     * Hide connection test result
     */
    hideTestResult() {
        const resultDiv = document.getElementById('connection-test-result');
        if (resultDiv) {
            resultDiv.style.display = 'none';
        }
    }

    /**
     * Get icon class for test result type
     * @param {string} type - Result type
     * @returns {string} Icon class
     */
    getTestResultIcon(type) {
        const icons = {
            loading: 'fas fa-spinner fa-spin',
            success: 'fas fa-check-circle',
            error: 'fas fa-times-circle'
        };
        return icons[type] || icons.loading;
    }

    /**
     * Cancel configuration and return to dashboard
     */
    cancelConfiguration() {
        // Reset form
        this.resetForm();

        // Hide test result
        this.hideTestResult();

        // If there's an existing configuration, go back to dashboard
        if (this.currentConfig || window.acronisManager) {
            if (window.acronisManager) {
                window.acronisManager.checkInitialConfiguration();
            }
        }
    }

    /**
     * Delete current configuration
     */
    async deleteConfiguration() {
        if (!this.currentConfig) {
            this.showNotification('No configuration to delete', 'warning');
            return;
        }

        if (!confirm('Are you sure you want to delete the current Acronis configuration? This will remove all saved API credentials.')) {
            return;
        }

        try {
            const result = await this.makeRequest('DELETE', '/config');

            if (result && result.success) {
                this.showNotification('Configuration deleted successfully', 'success');
                this.currentConfig = null;
                this.resetForm();

                // Notify that configuration was updated
                document.dispatchEvent(new CustomEvent('acronisConfigUpdated'));
            } else {
                throw new Error(result.error || 'Failed to delete configuration');
            }

        } catch (error) {
            console.error('Failed to delete configuration:', error);
            this.handleError(error, 'delete configuration');
        }
    }

    /**
     * Set button loading state
     * @param {HTMLElement} button - Button element
     * @param {boolean} loading - Whether button is loading
     */
    setButtonLoading(button, loading) {
        if (!button) return;

        if (loading) {
            button.disabled = true;
            button.classList.add('loading');

            const icon = button.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-spinner fa-spin';
            }
        } else {
            button.disabled = false;
            button.classList.remove('loading');

            // Restore original icon
            const icon = button.querySelector('i');
            if (icon) {
                if (button.id === 'test-connection-btn') {
                    icon.className = 'fas fa-plug';
                } else if (button.id === 'save-config-btn') {
                    icon.className = 'fas fa-save';
                }
            }
        }
    }

    /**
     * Make HTTP request to API
     * @param {string} method - HTTP method
     * @param {string} endpoint - API endpoint
     * @param {Object} data - Request data
     * @returns {Promise} Response promise
     */
    async makeRequest(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;

        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            signal: AbortSignal.timeout(30000) // 30 second timeout
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);

        let result;
        const contentType = response.headers.get('content-type');

        if (contentType && contentType.includes('application/json')) {
            result = await response.json();
        } else {
            result = { message: await response.text() };
        }

        if (!response.ok) {
            const error = new Error(result.error || result.message || `HTTP ${response.status}: ${response.statusText}`);
            error.status = response.status;
            error.response = result;
            throw error;
        }

        return result;
    }

    /**
     * Handle API errors with comprehensive error categorization and user feedback
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     * @param {Object} context - Additional context for error handling
     */
    handleError(error, operation, context = {}) {
        const errorContext = {
            module: 'acronis-config',
            configExists: !!this.currentConfig,
            operation,
            ...context
        };

        // Parse error response if available
        let errorData = null;
        let errorMessage = error.message || 'An unexpected error occurred';
        let errorCode = null;
        let recoverable = true;
        let troubleshootingSteps = [];
        let recoverySuggestions = [];

        try {
            if (error.response && typeof error.response === 'object') {
                errorData = error.response;
                errorMessage = errorData.error || errorMessage;
                errorCode = errorData.error_code;
                recoverable = errorData.recoverable !== false;
                troubleshootingSteps = errorData.troubleshooting_steps || [];
                recoverySuggestions = errorData.recovery_suggestions || [];
            }
        } catch (e) {
            console.warn('Failed to parse error response:', e);
        }

        // Log error with context
        console.error(`Acronis Config Error [${operation}]:`, {
            error: errorMessage,
            errorCode,
            recoverable,
            context: errorContext,
            originalError: error
        });

        // Use global error handler if available, otherwise handle locally
        if (window.globalErrorHandler) {
            const retryCallback = this.getRetryCallback(operation);
            window.globalErrorHandler.handleApiError(error, operation, errorContext, retryCallback);
        } else {
            // Enhanced local error handling
            this.handleCategorizedConfigError(errorCode, errorMessage, operation, {
                recoverable,
                troubleshootingSteps,
                recoverySuggestions,
                context: errorContext
            });
        }
    }

    /**
     * Handle categorized configuration errors
     * @param {string} errorCode - Error code
     * @param {string} errorMessage - Error message
     * @param {string} operation - Operation that failed
     * @param {Object} options - Error handling options
     */
    handleCategorizedConfigError(errorCode, errorMessage, operation, options = {}) {
        const { recoverable, troubleshootingSteps, recoverySuggestions, context } = options;

        let notificationType = 'error';
        let notificationDuration = 0; // Persistent by default
        let showRetryButton = recoverable;
        let customActions = [];

        // Handle specific error codes for configuration operations
        switch (errorCode) {
            case 'ACRONIS_INVALID_CREDENTIALS':
            case 'ACRONIS_AUTH_ERROR':
                notificationType = 'error';
                showRetryButton = false;
                customActions = [{
                    text: 'Check Credentials',
                    action: () => this.focusOnCredentialFields(),
                    primary: true
                }];
                break;

            case 'ACRONIS_CONNECTION_ERROR':
            case 'ACRONIS_TIMEOUT':
                notificationType = 'warning';
                notificationDuration = 15000;
                customActions = [{
                    text: 'Check Server URL',
                    action: () => this.focusOnServerUrl(),
                    primary: true
                }];
                break;

            case 'ACRONIS_CONFIG_ERROR':
                notificationType = 'error';
                showRetryButton = false;
                break;

            case 'ACRONIS_CONNECTION_TEST_FAILED':
                notificationType = 'warning';
                notificationDuration = 0;
                customActions = [{
                    text: 'Test Again',
                    action: () => this.testConnection(),
                    primary: true
                }];
                break;

            default:
                // Generic error handling
                if (recoverable) {
                    notificationType = 'warning';
                    notificationDuration = 10000;
                } else {
                    notificationType = 'error';
                }
        }

        // Add retry button if needed
        if (showRetryButton && !customActions.length) {
            customActions.push({
                text: 'Retry',
                action: () => this.retryConfigOperation(operation),
                primary: true
            });
        }

        // Show notification with enhanced error information
        this.showNotification(
            this.getUserFriendlyConfigErrorMessage(errorCode, errorMessage, operation),
            notificationType,
            notificationDuration,
            {
                errorCode,
                operation,
                recoverable,
                troubleshootingSteps,
                recoverySuggestions,
                customActions,
                context
            }
        );
    }

    /**
     * Get user-friendly error message for configuration operations
     * @param {string} errorCode - Error code
     * @param {string} errorMessage - Original error message
     * @param {string} operation - Operation that failed
     * @returns {string} User-friendly error message
     */
    getUserFriendlyConfigErrorMessage(errorCode, errorMessage, operation) {
        const operationNames = {
            'load configuration': 'loading configuration',
            'save configuration': 'saving configuration',
            'test connection': 'testing connection',
            'delete configuration': 'deleting configuration'
        };

        const friendlyOperation = operationNames[operation] || operation;

        const errorMessages = {
            'ACRONIS_INVALID_CREDENTIALS': 'Invalid API credentials. Please check your Client ID and Client Secret.',
            'ACRONIS_AUTH_ERROR': 'Authentication failed. Please verify your API credentials are correct.',
            'ACRONIS_CONNECTION_ERROR': 'Cannot connect to the Acronis server. Please check the Base URL and network connectivity.',
            'ACRONIS_TIMEOUT': 'Connection timed out. The Acronis server may be slow to respond.',
            'ACRONIS_CONFIG_ERROR': 'Configuration error. Please check all required fields.',
            'ACRONIS_CONNECTION_TEST_FAILED': 'Connection test failed. Please verify your configuration settings.',
            'ACRONIS_INSUFFICIENT_PERMISSIONS': 'Your API credentials do not have sufficient permissions.'
        };

        return errorMessages[errorCode] || `Failed to ${friendlyOperation}: ${errorMessage}`;
    }

    /**
     * Focus on credential fields for user correction
     */
    focusOnCredentialFields() {
        const clientIdField = document.getElementById('acronis-client-id');
        const clientSecretField = document.getElementById('acronis-client-secret');
        
        if (clientIdField) {
            clientIdField.focus();
            clientIdField.select();
        } else if (clientSecretField) {
            clientSecretField.focus();
            clientSecretField.select();
        }
    }

    /**
     * Focus on server URL field for user correction
     */
    focusOnServerUrl() {
        const baseUrlField = document.getElementById('acronis-base-url');
        if (baseUrlField) {
            baseUrlField.focus();
            baseUrlField.select();
        }
    }

    /**
     * Retry a configuration operation
     * @param {string} operation - Operation to retry
     */
    retryConfigOperation(operation) {
        console.log(`Retrying configuration operation: ${operation}`);

        switch (operation) {
            case 'load configuration':
                this.loadConfiguration();
                break;
            case 'save configuration':
                // Re-trigger form submission
                const form = document.getElementById('acronis-config-form');
                if (form) {
                    this.handleFormSubmit(new Event('submit'));
                }
                break;
            case 'test connection':
                this.testConnection();
                break;
            case 'delete configuration':
                this.deleteConfiguration();
                break;
            default:
                console.warn(`Unknown configuration operation for retry: ${operation}`);
        }
    }

    /**
     * Get retry callback for specific operations
     * @param {string} operation - Operation that failed
     * @returns {Function|null} Retry callback function
     */
    getRetryCallback(operation) {
        const retryCallbacks = {
            'load configuration': () => this.loadConfiguration(),
            'save configuration': () => this.handleFormSubmit(new Event('submit')),
            'test connection': () => this.testConnection(),
            'delete configuration': () => this.deleteConfiguration()
        };

        return retryCallbacks[operation] || null;
    }

    /**
     * Basic error handling fallback
     * @param {Error} error - Error object
     * @param {string} operation - Operation that failed
     */
    handleBasicError(error, operation) {
        let message = `Failed to ${operation}`;

        if (error.message) {
            if (error.message.includes('timeout')) {
                message += ': Request timeout. Please check your connection.';
            } else if (error.message.includes('Authentication failed')) {
                message += ': Authentication failed. Please check your API credentials.';
            } else if (error.message.includes('Connection failed')) {
                message += ': Cannot connect to Acronis server. Please check the server status.';
            } else {
                message += `: ${error.message}`;
            }
        }

        this.showNotification(message, 'error', 0); // Persistent error notifications
        console.error(`Acronis Config Error [${operation}]:`, error);
    }

    /**
     * Show notification message with enhanced system integration
     * @param {string} message - Message text
     * @param {string} type - Message type
     * @param {number} duration - Display duration
     * @param {Object} options - Additional options
     */
    showNotification(message, type = 'info', duration = 5000, options = {}) {
        // Use enhanced notification system if available
        if (window.notificationSystem) {
            const notificationOptions = {
                ...options,
                module: 'acronis-config'
            };

            switch (type) {
                case 'success':
                    return window.notificationSystem.showSuccess(message, { duration, ...notificationOptions });
                case 'error':
                    return window.notificationSystem.showError(message, {
                        persistent: duration === 0,
                        duration: duration || 10000,
                        ...notificationOptions
                    });
                case 'warning':
                    return window.notificationSystem.showWarning(message, { duration, ...notificationOptions });
                case 'info':
                default:
                    return window.notificationSystem.showInfo(message, { duration, ...notificationOptions });
            }
        } else {
            // Fallback to console logging
            console.log(`[ACRONIS-CONFIG ${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Show configuration validation feedback
     * @param {Array} validationErrors - Array of validation errors
     */
    showValidationFeedback(validationErrors) {
        if (validationErrors && validationErrors.length > 0) {
            const message = 'Configuration validation failed';
            const details = validationErrors.join('\n');

            this.showNotification(message, 'error', 0, {
                details,
                helpText: 'Please correct the highlighted fields and try again'
            });
        }
    }

    /**
     * Show connection test progress
     * @param {string} status - Test status (testing, success, failed)
     * @param {string} message - Status message
     */
    showConnectionTestProgress(status, message) {
        const options = {
            connectionTest: true
        };

        switch (status) {
            case 'testing':
                this.showNotification('Testing Acronis API connection...', 'info', 0, {
                    ...options,
                    showSpinner: true,
                    id: 'acronis-connection-test'
                });
                break;
            case 'success':
                // Remove testing notification
                if (window.notificationSystem && window.notificationSystem.remove) {
                    window.notificationSystem.remove('acronis-connection-test');
                }
                this.showNotification(message || 'Connection test successful!', 'success', 3000, options);
                break;
            case 'failed':
                // Remove testing notification
                if (window.notificationSystem && window.notificationSystem.remove) {
                    window.notificationSystem.remove('acronis-connection-test');
                }
                this.showNotification(message || 'Connection test failed', 'error', 0, {
                    ...options,
                    helpText: 'Please check your API credentials and server connectivity'
                });
                break;
        }
    }

    /**
     * Cleanup when component is destroyed
     */
    destroy() {
        // Clear any timeouts or intervals if needed
        this.hideTestResult();
    }
}

// Initialize Acronis configuration manager when DOM is ready
let acronisConfigManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        acronisConfigManager = new AcronisConfigManager();
    });
} else {
    acronisConfigManager = new AcronisConfigManager();
}

// Export for use in other modules
window.AcronisConfigManager = AcronisConfigManager;
window.acronisConfigManager = acronisConfigManager;