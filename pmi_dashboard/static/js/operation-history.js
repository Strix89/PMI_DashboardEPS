/**
 * Operation History Management
 * 
 * This module handles the display and management of operation history
 * including filtering, pagination, and detailed views.
 */

class OperationHistoryManager {
    constructor() {
        this.currentNodeId = null;
        this.currentPage = 1;
        this.itemsPerPage = 50;
        this.totalItems = 0;
        this.totalPages = 1;
        this.currentFilters = {
            resource_type: '',
            operation_type: '',
            status: '',
            limit: 50
        };
        this.isLoading = false;
        this.refreshInterval = null;
        
        this.initializeElements();
        this.bindEvents();
    }
    
    initializeElements() {
        // Main elements
        this.historySection = document.querySelector('.operation-history-section');
        this.historyTable = document.getElementById('history-table');
        this.historyTableBody = document.getElementById('history-table-body');
        this.historyLoading = document.getElementById('history-loading');
        this.historyEmptyState = document.getElementById('history-empty-state');
        this.historyErrorState = document.getElementById('history-error-state');
        this.historyErrorMessage = document.getElementById('history-error-message');
        
        // Filter elements
        this.resourceTypeFilter = document.getElementById('resource-type-filter');
        this.operationTypeFilter = document.getElementById('operation-type-filter');
        this.statusFilter = document.getElementById('status-filter');
        this.historyLimit = document.getElementById('history-limit');
        
        // Action buttons
        this.refreshHistoryBtn = document.getElementById('refresh-history-btn');
        this.clearFiltersBtn = document.getElementById('clear-filters-btn');
        this.retryHistoryBtn = document.getElementById('retry-history-btn');
        
        // Pagination elements
        this.paginationInfoText = document.getElementById('pagination-info-text');
        this.currentPageSpan = document.getElementById('current-page');
        this.totalPagesSpan = document.getElementById('total-pages');
        this.prevPageBtn = document.getElementById('prev-page-btn');
        this.nextPageBtn = document.getElementById('next-page-btn');
        
        // Modal elements
        this.operationDetailsModal = document.getElementById('operation-details-modal');
        this.modalCloseButtons = this.operationDetailsModal?.querySelectorAll('.btn-close, .close-modal');
    }
    
    bindEvents() {
        // Filter change events
        this.resourceTypeFilter?.addEventListener('change', () => this.onFilterChange());
        this.operationTypeFilter?.addEventListener('change', () => this.onFilterChange());
        this.statusFilter?.addEventListener('change', () => this.onFilterChange());
        this.historyLimit?.addEventListener('change', () => this.onFilterChange()); 
       
        // Action button events
        this.refreshHistoryBtn?.addEventListener('click', () => this.refreshHistory());
        this.clearFiltersBtn?.addEventListener('click', () => this.clearFilters());
        this.retryHistoryBtn?.addEventListener('click', () => this.loadHistory());
        
        // Pagination events
        this.prevPageBtn?.addEventListener('click', () => this.goToPreviousPage());
        this.nextPageBtn?.addEventListener('click', () => this.goToNextPage());
        
        // Modal events
        this.modalCloseButtons?.forEach(button => {
            button.addEventListener('click', () => this.closeModal());
        });
        
        // Close modal on backdrop click
        this.operationDetailsModal?.addEventListener('click', (e) => {
            if (e.target === this.operationDetailsModal || e.target.classList.contains('modal-backdrop')) {
                this.closeModal();
            }
        });
        
        // Escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.operationDetailsModal?.style.display !== 'none') {
                this.closeModal();
            }
        });
    }
    
    onFilterChange() {
        // Update current filters
        this.currentFilters.resource_type = this.resourceTypeFilter?.value || '';
        this.currentFilters.operation_type = this.operationTypeFilter?.value || '';
        this.currentFilters.status = this.statusFilter?.value || '';
        this.currentFilters.limit = parseInt(this.historyLimit?.value || '50');
        
        // Reset to first page when filters change
        this.currentPage = 1;
        this.itemsPerPage = this.currentFilters.limit;
        
        // Reload history with new filters
        this.loadHistory();
    }
    
    clearFilters() {
        // Reset all filters
        if (this.resourceTypeFilter) this.resourceTypeFilter.value = '';
        if (this.operationTypeFilter) this.operationTypeFilter.value = '';
        if (this.statusFilter) this.statusFilter.value = '';
        if (this.historyLimit) this.historyLimit.value = '50';
        
        // Reset filters object
        this.currentFilters = {
            resource_type: '',
            operation_type: '',
            status: '',
            limit: 50
        };
        
        // Reset pagination
        this.currentPage = 1;
        this.itemsPerPage = 50;
        
        // Reload history
        this.loadHistory();
    }
    
    refreshHistory() {
        this.loadHistory();
    }
    
    setNodeId(nodeId) {
        this.currentNodeId = nodeId;
        this.currentPage = 1;
        this.loadHistory();
    }
    
    async loadHistory() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoadingState();
        
        try {
            const params = new URLSearchParams({
                limit: this.itemsPerPage.toString(),
                offset: ((this.currentPage - 1) * this.itemsPerPage).toString()
            });
            
            // Add filters if they exist
            if (this.currentFilters.resource_type) {
                params.append('resource_type', this.currentFilters.resource_type);
            }
            if (this.currentFilters.operation_type) {
                params.append('operation_type', this.currentFilters.operation_type);
            }
            if (this.currentFilters.status) {
                params.append('status', this.currentFilters.status);
            }
            
            // Determine endpoint based on whether we have a specific node
            let endpoint = '/api/proxmox/history';
            if (this.currentNodeId) {
                endpoint = `/api/proxmox/nodes/${this.currentNodeId}/history`;
            }
            
            const response = await fetch(`${endpoint}?${params}`);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Failed to load operation history');
            }
            
            if (result.success) {
                this.displayHistory(result.data);
            } else {
                throw new Error(result.error || 'Failed to load operation history');
            }
            
        } catch (error) {
            console.error('Failed to load operation history:', error);
            this.showErrorState(error.message);
        } finally {
            this.isLoading = false;
        }
    }
    
    displayHistory(historyData) {
        const operations = historyData.operations || [];
        this.totalItems = historyData.total || 0;
        this.totalPages = Math.ceil(this.totalItems / this.itemsPerPage);
        
        // Clear existing content
        this.historyTableBody.innerHTML = '';
        
        if (operations.length === 0) {
            this.showEmptyState();
            return;
        }
        
        // Show table and hide other states
        this.showTableState();
        
        // Populate table
        operations.forEach(operation => {
            const row = this.createHistoryRow(operation);
            this.historyTableBody.appendChild(row);
        });
        
        // Update pagination
        this.updatePagination();
    }
    
    createHistoryRow(operation) {
        const row = document.createElement('tr');
        row.className = 'history-row';
        row.dataset.operationId = operation.id;
        
        // Format timestamp
        const timestamp = new Date(operation.timestamp);
        const timeString = timestamp.toLocaleString();
        
        // Format resource
        let resourceText = operation.node;
        if (operation.resource_id) {
            const resourceType = operation.resource_type.toUpperCase();
            resourceText = `${resourceType}-${operation.resource_id}`;
            if (operation.resource_name) {
                resourceText += ` (${operation.resource_name})`;
            }
        }
        
        // Format operation
        const operationText = operation.operation.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Format status
        const statusClass = `status-${operation.status}`;
        const statusIcon = this.getStatusIcon(operation.status);
        const statusText = operation.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        // Format duration
        let durationText = '--';
        if (operation.duration !== null && operation.duration !== undefined) {
            if (operation.duration < 1) {
                durationText = `${Math.round(operation.duration * 1000)}ms`;
            } else {
                durationText = `${operation.duration.toFixed(2)}s`;
            }
        }
        
        row.innerHTML = `
            <td class="col-timestamp" title="${timeString}">
                <div class="timestamp-content">
                    <div class="timestamp-date">${timestamp.toLocaleDateString()}</div>
                    <div class="timestamp-time">${timestamp.toLocaleTimeString()}</div>
                </div>
            </td>
            <td class="col-resource">
                <div class="resource-content">
                    <i class="fas ${this.getResourceIcon(operation.resource_type)}"></i>
                    <span class="resource-text">${resourceText}</span>
                </div>
            </td>
            <td class="col-operation">
                <div class="operation-content">
                    <i class="fas ${this.getOperationIcon(operation.operation)}"></i>
                    <span class="operation-text">${operationText}</span>
                </div>
            </td>
            <td class="col-status">
                <div class="status-content">
                    <span class="status-badge ${statusClass}">
                        <i class="fas ${statusIcon}"></i>
                        ${statusText}
                    </span>
                </div>
            </td>
            <td class="col-duration">
                <span class="duration-text">${durationText}</span>
            </td>
            <td class="col-details">
                <button class="btn btn-sm btn-outline details-btn" title="View Details">
                    <i class="fas fa-info-circle"></i>
                </button>
            </td>
        `;
        
        // Add click event for details button
        const detailsBtn = row.querySelector('.details-btn');
        detailsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showOperationDetails(operation);
        });
        
        // Add click event for row
        row.addEventListener('click', () => {
            this.showOperationDetails(operation);
        });
        
        return row;
    }
    
    getStatusIcon(status) {
        const icons = {
            'success': 'fa-check-circle',
            'failed': 'fa-times-circle',
            'in_progress': 'fa-spinner fa-spin',
            'pending': 'fa-clock',
            'cancelled': 'fa-ban'
        };
        return icons[status] || 'fa-question-circle';
    }
    
    getResourceIcon(resourceType) {
        const icons = {
            'node': 'fa-server',
            'vm': 'fa-desktop',
            'lxc': 'fa-cube',
            'qemu': 'fa-desktop'
        };
        return icons[resourceType] || 'fa-server';
    }
    
    getOperationIcon(operation) {
        const icons = {
            'start': 'fa-play',
            'stop': 'fa-stop',
            'restart': 'fa-redo',
            'reboot': 'fa-redo',
            'shutdown': 'fa-power-off',
            'suspend': 'fa-pause',
            'resume': 'fa-play',
            'backup': 'fa-save',
            'restore': 'fa-upload',
            'migrate': 'fa-exchange-alt',
            'clone': 'fa-copy',
            'delete': 'fa-trash'
        };
        return icons[operation] || 'fa-cog';
    }
    
    showOperationDetails(operation) {
        if (!this.operationDetailsModal) return;
        
        // Populate modal with operation details
        document.getElementById('detail-operation-id').textContent = operation.id;
        document.getElementById('detail-timestamp').textContent = new Date(operation.timestamp).toLocaleString();
        document.getElementById('detail-node').textContent = operation.node;
        
        // Format resource
        let resourceText = operation.node;
        if (operation.resource_id) {
            const resourceType = operation.resource_type.toUpperCase();
            resourceText = `${resourceType}-${operation.resource_id}`;
            if (operation.resource_name) {
                resourceText += ` (${operation.resource_name})`;
            }
        }
        document.getElementById('detail-resource').textContent = resourceText;
        
        document.getElementById('detail-operation').textContent = operation.operation.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        const statusElement = document.getElementById('detail-status');
        statusElement.textContent = operation.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        statusElement.className = `status-${operation.status}`;
        
        // Duration
        let durationText = 'Not available';
        if (operation.duration !== null && operation.duration !== undefined) {
            if (operation.duration < 1) {
                durationText = `${Math.round(operation.duration * 1000)} milliseconds`;
            } else {
                durationText = `${operation.duration.toFixed(2)} seconds`;
            }
        }
        document.getElementById('detail-duration').textContent = durationText;
        
        // User (optional)
        const userRow = document.getElementById('detail-user-row');
        if (operation.user) {
            document.getElementById('detail-user').textContent = operation.user;
            userRow.style.display = 'block';
        } else {
            userRow.style.display = 'none';
        }
        
        // Error message (optional)
        const errorRow = document.getElementById('detail-error-row');
        if (operation.error_message) {
            document.getElementById('detail-error-message').textContent = operation.error_message;
            errorRow.style.display = 'block';
        } else {
            errorRow.style.display = 'none';
        }
        
        // Additional details (optional)
        const detailsRow = document.getElementById('detail-details-row');
        if (operation.details && Object.keys(operation.details).length > 0) {
            document.getElementById('detail-additional-details').textContent = JSON.stringify(operation.details, null, 2);
            detailsRow.style.display = 'block';
        } else {
            detailsRow.style.display = 'none';
        }
        
        // Show modal
        this.operationDetailsModal.style.display = 'block';
        document.body.classList.add('modal-open');
    }
    
    closeModal() {
        if (this.operationDetailsModal) {
            this.operationDetailsModal.style.display = 'none';
            document.body.classList.remove('modal-open');
        }
    }
    
    goToPreviousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadHistory();
        }
    }
    
    goToNextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            this.loadHistory();
        }
    }
    
    updatePagination() {
        // Update pagination info
        const startItem = ((this.currentPage - 1) * this.itemsPerPage) + 1;
        const endItem = Math.min(this.currentPage * this.itemsPerPage, this.totalItems);
        
        this.paginationInfoText.textContent = `Showing ${startItem} - ${endItem} of ${this.totalItems} operations`;
        this.currentPageSpan.textContent = this.currentPage;
        this.totalPagesSpan.textContent = this.totalPages;
        
        // Update button states
        this.prevPageBtn.disabled = this.currentPage <= 1;
        this.nextPageBtn.disabled = this.currentPage >= this.totalPages;
    }
    
    showLoadingState() {
        this.historyLoading.style.display = 'block';
        this.historyTable.style.display = 'none';
        this.historyEmptyState.style.display = 'none';
        this.historyErrorState.style.display = 'none';
    }
    
    showTableState() {
        this.historyLoading.style.display = 'none';
        this.historyTable.style.display = 'table';
        this.historyEmptyState.style.display = 'none';
        this.historyErrorState.style.display = 'none';
    }
    
    showEmptyState() {
        this.historyLoading.style.display = 'none';
        this.historyTable.style.display = 'none';
        this.historyEmptyState.style.display = 'block';
        this.historyErrorState.style.display = 'none';
    }
    
    showErrorState(errorMessage) {
        this.historyLoading.style.display = 'none';
        this.historyTable.style.display = 'none';
        this.historyEmptyState.style.display = 'none';
        this.historyErrorState.style.display = 'block';
        
        if (this.historyErrorMessage) {
            this.historyErrorMessage.textContent = errorMessage;
        }
    }
    
    startAutoRefresh(intervalMs = 30000) {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            if (!this.isLoading) {
                this.loadHistory();
            }
        }, intervalMs);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    destroy() {
        this.stopAutoRefresh();
        // Remove event listeners if needed
    }
}

// Global instance
let operationHistoryManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if the history section exists
    if (document.querySelector('.operation-history-section')) {
        operationHistoryManager = new OperationHistoryManager();
    }
});

// Export for use in other modules
window.OperationHistoryManager = OperationHistoryManager;
window.operationHistoryManager = operationHistoryManager;