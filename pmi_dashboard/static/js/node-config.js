/**
 * Node Configuration Management
 * 
 * This module handles the Proxmox node configuration interface,
 * including adding, editing, deleting, and testing node connections.
 */

class NodeConfigManager {
    constructor() {
        this.nodes = [];
        this.currentEditingNode = null;
        
        this.init();
    }
    
    /**
     * Initialize the node configuration manager
     */
    init() {
        this.setupEventListeners();
        
        console.log('Node Configuration Manager initialized');
    }
    
    /**
     * Set up event listeners for the configuration interface
     */
    setupEventListeners() {
        // Add node button
        const addNodeBtn = document.getElementById('add-node-btn');
        if (addNodeBtn) {
            addNodeBtn.addEventListener('click', () => this.showAddNodeForm());
        }
        
        // Close form button
        const closeFormBtn = document.getElementById('close-form-btn');
        if (closeFormBtn) {
            closeFormBtn.addEventListener('click', () => this.hideNodeForm());
        }
        
        // Cancel form button
        const cancelFormBtn = document.getElementById('cancel-form-btn');
        if (cancelFormBtn) {
            cancelFormBtn.addEventListener('click', () => this.hideNodeForm());
        }
        
        // Node form submission
        const nodeForm = document.getElementById('node-form');
        if (nodeForm) {
            nodeForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
        
        // Test connection button
        const testConnectionBtn = document.getElementById('test-connection-btn');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', () => this.testConnection());
        }
        
        // Refresh nodes button - handled by node-dashboard.js
        // No need to bind here as node-dashboard.js handles this
        
        // Form validation on input
        this.setupFormValidation();
        
        // Listen for successful node operations to notify dashboard
        document.addEventListener('nodeUpdated', () => {
            // Notify the dashboard to refresh silently
            if (window.nodeDashboard) {
                window.nodeDashboard.loadNodes(true); // Silent refresh
            }
        });
    }
    
    /**
     * Set up form validation
     */
    setupFormValidation() {
        const form = document.getElementById('node-form');
        if (!form) return;
        
        const inputs = form.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
        
        // Real-time validation for specific fields
        const hostInput = document.getElementById('node-host');
        if (hostInput) {
            hostInput.addEventListener('input', () => this.validateHost(hostInput));
        }
        
        const portInput = document.getElementById('node-port');
        if (portInput) {
            portInput.addEventListener('input', () => this.validatePort(portInput));
        }
    }
    
    /**
     * Show the add node form
     */
    showAddNodeForm() {
        this.currentEditingNode = null;
        this.resetForm();
        
        const formTitle = document.getElementById('form-title');
        if (formTitle) {
            formTitle.textContent = 'Add New Node';
        }
        
        const saveBtn = document.getElementById('save-node-btn');
        if (saveBtn) {
            const btnText = saveBtn.querySelector('.btn-text');
            if (btnText) {
                btnText.textContent = 'Save Node';
            }
        }
        
        const form = document.getElementById('node-config-form');
        if (form) {
            form.style.display = 'block';
            form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        // Focus on first input
        const firstInput = document.getElementById('node-name');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
    
    /**
     * Show the edit node form
     * @param {Object} node - Node data to edit
     */
    showEditNodeForm(node) {
        this.currentEditingNode = node;
        this.populateForm(node);
        
        const formTitle = document.getElementById('form-title');
        if (formTitle) {
            formTitle.textContent = `Edit Node: ${node.name}`;
        }
        
        const saveBtn = document.getElementById('save-node-btn');
        if (saveBtn) {
            const btnText = saveBtn.querySelector('.btn-text');
            if (btnText) {
                btnText.textContent = 'Update Node';
            }
        }
        
        const form = document.getElementById('node-config-form');
        if (form) {
            form.style.display = 'block';
            form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    /**
     * Hide the node configuration form
     */
    hideNodeForm() {
        const form = document.getElementById('node-config-form');
        if (form) {
            form.style.display = 'none';
        }
        
        this.currentEditingNode = null;
        this.resetForm();
    }
    
    /**
     * Reset the form to default state
     */
    resetForm() {
        const form = document.getElementById('node-form');
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
            document.getElementById('node-port').value = '8006';
            document.getElementById('timeout').value = '30';
            document.getElementById('node-enabled').checked = true;
            document.getElementById('ssl-verify').checked = false;
        }
    }
    
    /**
     * Populate form with node data
     * @param {Object} node - Node data
     */
    populateForm(node) {
        document.getElementById('node-id').value = node.id || '';
        document.getElementById('node-name').value = node.name || '';
        document.getElementById('node-host').value = node.host || '';
        document.getElementById('node-port').value = node.port || 8006;
        document.getElementById('api-token-id').value = node.api_token_id || '';
        document.getElementById('api-token-secret').value = node.api_token_secret || '';
        document.getElementById('ssl-verify').checked = node.ssl_verify || false;
        document.getElementById('timeout').value = node.timeout || 30;
        document.getElementById('node-enabled').checked = node.enabled !== false;
    }
    
    /**
     * Handle form submission
     * @param {Event} e - Form submit event
     */
    async handleFormSubmit(e) {
        e.preventDefault();
        
        if (!this.validateForm()) {
            return;
        }
        
        const formData = this.getFormData();
        const saveBtn = document.getElementById('save-node-btn');
        
        try {
            this.setButtonLoading(saveBtn, true);
            
            let result;
            if (this.currentEditingNode) {
                result = await proxmoxAPI.updateNode(this.currentEditingNode.id, formData);
            } else {
                result = await proxmoxAPI.addNode(formData);
            }
            
            if (result.success) {
                const action = this.currentEditingNode ? 'updated' : 'added';
                this.showNotification(`Node successfully ${action}!`, 'success');
                this.hideNodeForm();
                
                // Notify dashboard to refresh
                document.dispatchEvent(new CustomEvent('nodeUpdated'));
            } else {
                throw new Error(result.error || 'Operation failed');
            }
            
        } catch (error) {
            console.error('Failed to save node:', error);
            
            // Extract more specific error message from API response
            let errorMessage = error.message;
            if (error.message && error.message.includes('Connection failed')) {
                errorMessage = 'Cannot connect to Proxmox server. Please check the host, port, and network connectivity.';
            } else if (error.message && error.message.includes('Authentication failed')) {
                errorMessage = 'Authentication failed. Please check your API token credentials.';
            } else if (error.message && error.message.includes('timeout')) {
                errorMessage = 'Connection timeout. Please check if the Proxmox server is running and accessible.';
            }
            
            this.showNotification(`Failed to save node: ${errorMessage}`, 'error');
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
            name: document.getElementById('node-name').value.trim(),
            host: document.getElementById('node-host').value.trim(),
            port: parseInt(document.getElementById('node-port').value) || 8006,
            api_token_id: document.getElementById('api-token-id').value.trim() || null,
            api_token_secret: document.getElementById('api-token-secret').value.trim() || null,
            ssl_verify: document.getElementById('ssl-verify').checked,
            timeout: parseInt(document.getElementById('timeout').value) || 30,
            enabled: document.getElementById('node-enabled').checked
        };
    }
    
    /**
     * Validate the entire form
     * @returns {boolean} True if form is valid
     */
    validateForm() {
        const form = document.getElementById('node-form');
        let isValid = true;
        
        // Validate required fields
        const requiredInputs = form.querySelectorAll('input[required]');
        requiredInputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        // Validate specific fields
        const hostInput = document.getElementById('node-host');
        if (!this.validateHost(hostInput)) {
            isValid = false;
        }
        
        const portInput = document.getElementById('node-port');
        if (!this.validatePort(portInput)) {
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
        } else if (input.type === 'number') {
            const numValue = parseInt(value);
            const min = parseInt(input.getAttribute('min'));
            const max = parseInt(input.getAttribute('max'));
            
            if (isNaN(numValue)) {
                isValid = false;
                errorMessage = 'Please enter a valid number';
            } else if (min !== null && numValue < min) {
                isValid = false;
                errorMessage = `Value must be at least ${min}`;
            } else if (max !== null && numValue > max) {
                isValid = false;
                errorMessage = `Value must be no more than ${max}`;
            }
        }
        
        this.setFieldValidation(input, isValid, errorMessage);
        return isValid;
    }
    
    /**
     * Validate host field
     * @param {HTMLElement} input - Host input element
     * @returns {boolean} True if host is valid
     */
    validateHost(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        if (!value) {
            isValid = false;
            errorMessage = 'Host is required';
        } else {
            // Basic validation for IP or hostname
            const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
            const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/;
            
            if (!ipRegex.test(value) && !hostnameRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid IP address or hostname';
            }
        }
        
        this.setFieldValidation(input, isValid, errorMessage);
        return isValid;
    }
    
    /**
     * Validate port field
     * @param {HTMLElement} input - Port input element
     * @returns {boolean} True if port is valid
     */
    validatePort(input) {
        const value = input.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        if (value) {
            const port = parseInt(value);
            if (isNaN(port) || port < 1 || port > 65535) {
                isValid = false;
                errorMessage = 'Port must be between 1 and 65535';
            }
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
        const feedbackElement = input.parentNode.querySelector('.invalid-feedback');
        
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
        const feedbackElement = input.parentNode.querySelector('.invalid-feedback');
        if (feedbackElement) {
            feedbackElement.textContent = '';
        }
    }
    
    /**
     * Test connection to Proxmox server
     */
    async testConnection() {
        if (!this.validateForm()) {
            this.showNotification('Please fix form errors before testing connection', 'warning');
            return;
        }
        
        const formData = this.getFormData();
        const testBtn = document.getElementById('test-connection-btn');
        
        try {
            this.setButtonLoading(testBtn, true);
            this.showTestResult('Testing connection...', 'loading');
            
            let result;
            
            // For existing nodes, we can use the node ID
            if (this.currentEditingNode) {
                result = await proxmoxAPI.testNodeConnection(this.currentEditingNode.id);
            } else {
                // For new nodes, test the configuration without saving
                result = await proxmoxAPI.testConnectionConfig(formData);
            }
            
            if (result.success && result.data && result.data.connected) {
                this.showTestResult('Connection successful!', 'success');
            } else {
                const message = result.message || 'Connection failed';
                this.showTestResult(message, 'error');
            }
            
        } catch (error) {
            console.error('Connection test failed:', error);
            
            // Extract more specific error message
            let errorMessage = error.message;
            if (error.message && error.message.includes('Connection failed')) {
                errorMessage = 'Cannot connect to server. Check host, port, and network.';
            } else if (error.message && error.message.includes('Authentication failed')) {
                errorMessage = 'Authentication failed. Check API token credentials.';
            } else if (error.message && error.message.includes('timeout')) {
                errorMessage = 'Connection timeout. Server may be unreachable.';
            }
            
            this.showTestResult(`Connection failed: ${errorMessage}`, 'error');
            
            // Also show a notification for better visibility
            this.showNotification(`Connection test failed: ${errorMessage}`, 'error');
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
        
        const iconElement = resultDiv.querySelector('.test-result-icon i');
        const messageElement = resultDiv.querySelector('.test-result-message');
        
        // Update icon
        iconElement.className = this.getTestResultIcon(type);
        
        // Update message
        messageElement.textContent = message;
        
        // Update styling
        resultDiv.className = `test-result test-result-${type}`;
        resultDiv.style.display = 'block';
        
        // Auto-hide after delay (except for loading)
        if (type !== 'loading') {
            setTimeout(() => {
                resultDiv.style.display = 'none';
            }, 5000);
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
    
    // Node loading and rendering is now handled by node-dashboard.js
    // This avoids conflicts and duplicate refreshes
    
    // All node rendering functions moved to node-dashboard.js to avoid conflicts
    
    // Node card interaction functions moved to node-dashboard.js to avoid conflicts
    
    /**
     * Get progress bar color class based on percentage
     * @param {number} percentage - Usage percentage
     * @returns {string} CSS class name
     */
    getProgressColor(percentage) {
        if (percentage >= 90) return 'progress-danger';
        if (percentage >= 75) return 'progress-warning';
        if (percentage >= 50) return 'progress-info';
        return 'progress-success';
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
                } else if (button.id === 'save-node-btn') {
                    icon.className = 'fas fa-save';
                } else if (button.classList.contains('test-node-btn')) {
                    icon.className = 'fas fa-plug';
                }
            }
        }
    }
    
    /**
     * Show notification message
     * @param {string} message - Message text
     * @param {string} type - Message type
     */
    showNotification(message, type = 'info') {
        // Use the global showNotification function from proxmox.js
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
    
    /**
     * Cleanup when component is destroyed
     */
    destroy() {
        // No cleanup needed for configuration manager
    }
}

// Initialize node configuration manager when DOM is ready
let nodeConfigManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        nodeConfigManager = new NodeConfigManager();
    });
} else {
    nodeConfigManager = new NodeConfigManager();
}

// Export for use in other modules
window.NodeConfigManager = NodeConfigManager;
window.nodeConfigManager = nodeConfigManager;