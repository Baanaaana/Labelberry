// Global variables
let allJobs = [];
let filteredJobs = [];
let currentPage = 1;
const jobsPerPage = 20;
let currentJobDetails = null;

// Load print history on page load
document.addEventListener('DOMContentLoaded', () => {
    loadPrinters();
    loadHistory();
    
    // Auto-refresh every 10 seconds
    setInterval(loadHistory, 10000);
});

// Load available printers for filter
async function loadPrinters() {
    try {
        const response = await fetch('/api/pis');
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('printer-filter');
            select.innerHTML = '<option value="">All Printers</option>';
            
            data.data.pis.forEach(pi => {
                const option = document.createElement('option');
                option.value = pi.id;
                option.textContent = pi.friendly_name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load printers:', error);
    }
}

// Load print history
async function loadHistory() {
    try {
        const response = await fetch('/api/print-history?limit=1000');
        const data = await response.json();
        
        if (data.success) {
            allJobs = data.data.jobs;
            filterHistory();
        }
    } catch (error) {
        console.error('Failed to load history:', error);
        showAlert('Failed to load print history', 'error');
    }
}

// Filter history based on selected filters
function filterHistory() {
    const printerFilter = document.getElementById('printer-filter').value;
    const statusFilter = document.getElementById('status-filter').value;
    const dateFilter = parseInt(document.getElementById('date-filter').value);
    
    const now = new Date();
    const cutoffTime = new Date(now.getTime() - dateFilter * 60 * 60 * 1000);
    
    filteredJobs = allJobs.filter(job => {
        // Printer filter
        if (printerFilter && job.pi_id !== printerFilter) {
            return false;
        }
        
        // Status filter
        if (statusFilter && job.status !== statusFilter) {
            return false;
        }
        
        // Date filter
        const jobDate = new Date(job.created_at);
        if (jobDate < cutoffTime) {
            return false;
        }
        
        return true;
    });
    
    // Reset to first page
    currentPage = 1;
    renderHistory();
}

// Render history table with pagination
function renderHistory() {
    const tbody = document.getElementById('history-tbody');
    const noJobs = document.getElementById('no-jobs');
    const table = document.getElementById('history-table');
    
    if (filteredJobs.length === 0) {
        tbody.innerHTML = '';
        table.style.display = 'none';
        noJobs.style.display = 'block';
        document.getElementById('pagination-controls').style.display = 'none';
        document.getElementById('job-count').textContent = '';
        document.getElementById('showing-info').textContent = '';
        return;
    }
    
    table.style.display = 'table';
    noJobs.style.display = 'none';
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredJobs.length / jobsPerPage);
    const startIndex = (currentPage - 1) * jobsPerPage;
    const endIndex = Math.min(startIndex + jobsPerPage, filteredJobs.length);
    const pageJobs = filteredJobs.slice(startIndex, endIndex);
    
    // Update job count
    document.getElementById('job-count').textContent = `(${filteredJobs.length})`;
    document.getElementById('showing-info').textContent = 
        `Showing ${startIndex + 1}-${endIndex} of ${filteredJobs.length}`;
    
    // Render jobs
    tbody.innerHTML = pageJobs.map(job => {
        const createdAt = new Date(job.created_at);
        const completedAt = job.completed_at ? new Date(job.completed_at) : null;
        const duration = completedAt ? formatDuration(completedAt - createdAt) : '-';
        
        const statusClass = getStatusClass(job.status);
        const sourceIcon = getSourceIcon(job.source);
        
        return `
            <tr>
                <td>${formatDateTime(createdAt)}</td>
                <td>${job.printer_name || 'Unknown'}</td>
                <td><span class="status-badge ${statusClass}">${job.status}</span></td>
                <td>${sourceIcon} ${job.source || 'unknown'}</td>
                <td>${duration}</td>
                <td>
                    <button class="action-btn" onclick="viewJobDetails('${job.id}')">
                        <i data-lucide="eye"></i> View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Update pagination controls
    updatePagination(totalPages);
    
    // Re-initialize Lucide icons
    setTimeout(() => lucide.createIcons({
        attrs: {
            width: 16,
            height: 16
        }
    }), 10);
}

// Update pagination controls
function updatePagination(totalPages) {
    const controls = document.getElementById('pagination-controls');
    
    if (totalPages <= 1) {
        controls.style.display = 'none';
        return;
    }
    
    controls.style.display = 'flex';
    
    document.getElementById('pagination-info').textContent = 
        `Page ${currentPage} of ${totalPages}`;
    document.getElementById('page-info').textContent = 
        `Page ${currentPage} of ${totalPages}`;
    
    document.getElementById('prev-btn').disabled = currentPage === 1;
    document.getElementById('next-btn').disabled = currentPage === totalPages;
}

// Change page
function changePage(direction) {
    currentPage += direction;
    renderHistory();
}

// View job details
async function viewJobDetails(jobId) {
    const job = allJobs.find(j => j.id === jobId);
    if (!job) return;
    
    currentJobDetails = job;
    
    const modal = document.getElementById('job-modal');
    const details = document.getElementById('job-details');
    const copyBtn = document.getElementById('copy-zpl-btn');
    
    // Show/hide copy button based on ZPL content
    copyBtn.style.display = (job.zpl_content || job.zpl_url) ? 'inline-flex' : 'none';
    
    // Generate label preview if ZPL content is available
    if (job.zpl_content) {
        generateLabelPreview(job.zpl_content);
    }
    
    // Format job details
    details.innerHTML = `
        <div class="job-detail-grid">
            <div class="detail-row">
                <span class="detail-label">Job ID:</span>
                <span class="detail-value" style="font-family: monospace;">${job.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Printer:</span>
                <span class="detail-value">${job.printer_name || 'Unknown'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status:</span>
                <span class="detail-value">
                    <span class="status-badge ${getStatusClass(job.status)}">${job.status}</span>
                </span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Source:</span>
                <span class="detail-value">${job.source || 'unknown'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Created:</span>
                <span class="detail-value">${formatDateTime(new Date(job.created_at))}</span>
            </div>
            ${job.completed_at ? `
            <div class="detail-row">
                <span class="detail-label">Completed:</span>
                <span class="detail-value">${formatDateTime(new Date(job.completed_at))}</span>
            </div>
            ` : ''}
            ${job.error_message ? `
            <div class="detail-row">
                <span class="detail-label">Error:</span>
                <span class="detail-value" style="color: var(--danger-color);">${job.error_message}</span>
            </div>
            ` : ''}
        </div>
        
        ${job.zpl_content ? `
        <div class="zpl-preview-container">
            <div class="zpl-section zpl-code-section">
                <h3>ZPL Content</h3>
                <div class="zpl-content">
                    <pre>${escapeHtml(job.zpl_content)}</pre>
                </div>
            </div>
            <div class="zpl-section zpl-preview-section">
                <h3>Label Preview</h3>
                <div id="label-preview" class="label-preview">
                    <div class="preview-loading">
                        <i data-lucide="loader-2" class="spinner"></i>
                        <p>Generating preview...</p>
                    </div>
                </div>
            </div>
        </div>
        ` : ''}
        
        ${job.zpl_url ? `
        <div class="zpl-section">
            <h3>ZPL URL</h3>
            <div class="zpl-url">
                <a href="${job.zpl_url}" target="_blank">${job.zpl_url}</a>
            </div>
        </div>
        ` : ''}
    `;
    
    modal.style.display = 'block';
    
    // Re-initialize Lucide icons for the modal content
    setTimeout(() => lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    }), 10);
}

// Generate label preview using Labelary API via proxy
async function generateLabelPreview(zplContent) {
    const previewContainer = document.getElementById('label-preview');
    if (!previewContainer) return;
    
    try {
        // Use our proxy endpoint to avoid CORS issues
        const response = await fetch('/api/generate-label-preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain'
            },
            body: zplContent
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);
            
            previewContainer.innerHTML = `
                <img src="${imageUrl}" alt="Label Preview" class="preview-image" />
                <div class="preview-info">
                    <small>Preview rendered at 203 dpi</small>
                </div>
            `;
        } else {
            // Try to get error message
            let errorMessage = 'Failed to generate preview';
            
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorMessage = errorData.detail;
                }
            } catch {
                // If not JSON, try text
                const errorText = await response.text();
                if (errorText) {
                    errorMessage = errorText;
                }
            }
            
            previewContainer.innerHTML = `
                <div class="preview-error">
                    <i data-lucide="alert-circle"></i>
                    <p>Could not generate preview</p>
                    <small>${escapeHtml(errorMessage)}</small>
                </div>
            `;
            
            // Re-initialize icons
            lucide.createIcons({
                attrs: {
                    width: 20,
                    height: 20
                }
            });
        }
    } catch (error) {
        console.error('Failed to generate label preview:', error);
        previewContainer.innerHTML = `
            <div class="preview-error">
                <i data-lucide="alert-circle"></i>
                <p>Could not generate preview</p>
                <small>Network error</small>
            </div>
        `;
        
        // Re-initialize icons
        lucide.createIcons({
            attrs: {
                width: 20,
                height: 20
            }
        });
    }
}

// Close job modal
function closeJobModal() {
    document.getElementById('job-modal').style.display = 'none';
    currentJobDetails = null;
}

// Copy ZPL content
function copyZPL() {
    if (!currentJobDetails) return;
    
    const content = currentJobDetails.zpl_content || currentJobDetails.zpl_url || '';
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(content).then(() => {
            showAlert('ZPL content copied to clipboard', 'success');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = content;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showAlert('ZPL content copied to clipboard', 'success');
    }
}

// Clear filters
function clearFilters() {
    document.getElementById('printer-filter').value = '';
    document.getElementById('status-filter').value = '';
    document.getElementById('date-filter').value = '48';
    filterHistory();
}

// Refresh history
function refreshHistory() {
    loadHistory();
    showAlert('History refreshed', 'info');
}

// Helper functions
function getStatusClass(status) {
    switch (status) {
        case 'completed': return 'status-success';
        case 'failed': return 'status-error';
        case 'queued': return 'status-warning';
        case 'processing': return 'status-info';
        case 'sent': return 'status-info';
        default: return 'status-default';
    }
}

function getSourceIcon(source) {
    switch (source) {
        case 'api': return '<i data-lucide="terminal" style="width: 14px; height: 14px;"></i>';
        case 'test': return '<i data-lucide="flask" style="width: 14px; height: 14px;"></i>';
        case 'broadcast': return '<i data-lucide="send" style="width: 14px; height: 14px;"></i>';
        default: return '<i data-lucide="file" style="width: 14px; height: 14px;"></i>';
    }
}

function formatDateTime(date) {
    const options = {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    return date.toLocaleString('en-US', options);
}

function formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show alert toast
function showAlert(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info'}"></i>
        <span>${message}</span>
    `;
    
    const container = document.getElementById('toast-container');
    container.appendChild(toast);
    
    // Re-initialize Lucide icons for the toast
    lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        closeJobModal();
    }
}