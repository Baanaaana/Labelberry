// Global variables
let currentPis = [];
let selectedPiId = null;
let refreshInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    // Refresh every 10 seconds
    refreshInterval = setInterval(loadDashboard, 10000);
});

// Load dashboard data
async function loadDashboard() {
    try {
        // Get dashboard stats
        const statsResponse = await fetch('/api/dashboard/stats');
        const statsData = await statsResponse.json();
        
        if (statsData.success) {
            updateStats(statsData.data);
        }
        
        // Get all Pis
        const pisResponse = await fetch('/api/pis');
        const pisData = await pisResponse.json();
        
        if (pisData.success) {
            currentPis = pisData.data.pis;
            renderPrinters(currentPis);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showAlert('Failed to load dashboard data', 'error');
    }
}

// Update dashboard statistics
function updateStats(stats) {
    document.getElementById('total-pis').textContent = stats.total_pis || 0;
    document.getElementById('online-pis').textContent = stats.online_pis || 0;
    document.getElementById('jobs-today').textContent = stats.jobs_24h || 0;
}

// Render printer cards
function renderPrinters(pis) {
    const grid = document.getElementById('printers-grid');
    
    if (pis.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; background: white; border-radius: 12px;">
                <i class="ri-printer-line" style="font-size: 3em; color: #ccc;"></i>
                <p style="margin-top: 20px; color: #666;">No printers registered yet</p>
                <p style="margin-top: 10px; color: #999;">Click "Register New Pi" to add your first printer</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = pis.map(pi => createPrinterCard(pi)).join('');
}

// Create printer card HTML
function createPrinterCard(pi) {
    const statusClass = pi.status === 'online' ? 'status-online' : 
                       pi.status === 'error' ? 'status-error' : 'status-offline';
    const statusText = pi.status === 'online' ? 'Online' : 
                      pi.status === 'error' ? 'Error' : 'Offline';
    
    return `
        <div class="printer-card">
            <div class="printer-header">
                <div class="printer-name">${pi.friendly_name}</div>
                <div class="printer-status ${statusClass}">${statusText}</div>
            </div>
            <div class="printer-info">
                <div class="info-row">
                    <span class="info-label">Location:</span>
                    <span class="info-value">${pi.location || 'Not specified'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Model:</span>
                    <span class="info-value">${pi.printer_model || 'Unknown'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Queue:</span>
                    <span class="info-value">${pi.queue_count || 0} jobs</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Last Seen:</span>
                    <span class="info-value">${formatDateTime(pi.last_seen)}</span>
                </div>
            </div>
            <div class="printer-actions-grid">
                <button class="btn btn-primary" onclick="showPrintModal('${pi.id}', '${pi.friendly_name}')">
                    <i class="ri-printer-line"></i> Test Print
                </button>
                <button class="btn btn-secondary" onclick="showDetailsModal('${pi.id}')">
                    <i class="ri-information-line"></i> Details
                </button>
                <button class="btn btn-edit" onclick="showEditModal('${pi.id}')">
                    <i class="ri-edit-line"></i> Edit
                </button>
                <button class="btn btn-delete" onclick="showDeleteModal('${pi.id}', '${pi.friendly_name}')">
                    <i class="ri-delete-bin-line"></i> Delete
                </button>
            </div>
        </div>
    `;
}

// Show register Pi modal
function showRegisterModal() {
    document.getElementById('register-modal').style.display = 'block';
}

// Close register modal
function closeRegisterModal() {
    document.getElementById('register-modal').style.display = 'none';
    document.getElementById('register-form').reset();
}

// Register new Pi
async function registerPi(event) {
    event.preventDefault();
    
    const deviceId = document.getElementById('device-id').value;
    const apiKey = document.getElementById('api-key').value;
    const friendlyName = document.getElementById('friendly-name').value;
    const location = document.getElementById('location').value;
    const printerModel = document.getElementById('printer-model').value;
    
    const piData = {
        id: deviceId,
        api_key: apiKey,
        friendly_name: friendlyName,
        location: location || null,
        printer_model: printerModel || null,
        status: 'offline'
    };
    
    try {
        const response = await fetch('/api/pis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(piData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Raspberry Pi registered successfully!', 'success');
            closeRegisterModal();
            loadDashboard();
        } else {
            showAlert(data.detail || 'Failed to register Pi', 'error');
        }
    } catch (error) {
        console.error('Error registering Pi:', error);
        showAlert('Failed to register Pi', 'error');
    }
}

// Show print modal
function showPrintModal(piId, piName) {
    selectedPiId = piId;
    document.getElementById('print-pi-name').textContent = piName;
    document.getElementById('print-modal').style.display = 'block';
}

// Close print modal
function closePrintModal() {
    document.getElementById('print-modal').style.display = 'none';
    document.getElementById('print-form').reset();
    selectedPiId = null;
}

// Toggle print method inputs
function togglePrintMethod() {
    const method = document.querySelector('input[name="print-method"]:checked').value;
    
    document.getElementById('raw-input').style.display = method === 'raw' ? 'block' : 'none';
    document.getElementById('file-input').style.display = method === 'file' ? 'block' : 'none';
    document.getElementById('url-input').style.display = method === 'url' ? 'block' : 'none';
}

// Send print job
async function sendPrint(event) {
    event.preventDefault();
    
    if (!selectedPiId) {
        showAlert('No printer selected', 'error');
        return;
    }
    
    const pi = currentPis.find(p => p.id === selectedPiId);
    if (!pi) {
        showAlert('Printer not found', 'error');
        return;
    }
    
    const method = document.querySelector('input[name="print-method"]:checked').value;
    let printData = {};
    
    if (method === 'raw') {
        const zplRaw = document.getElementById('zpl-raw').value;
        if (!zplRaw) {
            showAlert('Please enter ZPL code', 'error');
            return;
        }
        printData = { zpl_raw: zplRaw };
    } else if (method === 'url') {
        const zplUrl = document.getElementById('zpl-url').value;
        if (!zplUrl) {
            showAlert('Please enter ZPL URL', 'error');
            return;
        }
        printData = { zpl_url: zplUrl };
    } else if (method === 'file') {
        const fileInput = document.getElementById('zpl-file');
        if (!fileInput.files[0]) {
            showAlert('Please select a ZPL file', 'error');
            return;
        }
        
        const fileContent = await readFileContent(fileInput.files[0]);
        printData = { zpl_raw: fileContent };
    }
    
    // Send print job to Pi
    try {
        // First, get Pi details to find its IP/URL
        const piResponse = await fetch(`/api/pis/${selectedPiId}`);
        const piData = await piResponse.json();
        
        if (!piData.success) {
            showAlert('Failed to get printer details', 'error');
            return;
        }
        
        // For now, we'll send a command through the admin server
        // In production, you'd want to either:
        // 1. Have the admin server forward the request
        // 2. Get the Pi's IP and send directly
        
        const response = await fetch(`/api/pis/${selectedPiId}/print`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(printData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Print job sent successfully!', 'success');
            closePrintModal();
        } else {
            showAlert(data.detail || 'Failed to send print job', 'error');
        }
    } catch (error) {
        console.error('Error sending print job:', error);
        showAlert('Failed to send print job', 'error');
    }
}

// Read file content
function readFileContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

// Show details modal
async function showDetailsModal(piId) {
    selectedPiId = piId;
    const pi = currentPis.find(p => p.id === piId);
    
    if (!pi) return;
    
    document.getElementById('details-pi-name').textContent = pi.friendly_name;
    document.getElementById('details-modal').style.display = 'block';
    
    // Load detailed information
    try {
        const response = await fetch(`/api/pis/${piId}`);
        const data = await response.json();
        
        if (data.success) {
            renderPiDetails(data.data);
        }
        
        // Load metrics
        const metricsResponse = await fetch(`/api/pis/${piId}/metrics?hours=1`);
        const metricsData = await metricsResponse.json();
        
        if (metricsData.success && metricsData.data.metrics.length > 0) {
            const latestMetrics = metricsData.data.metrics[0];
            renderMetrics(latestMetrics);
        }
    } catch (error) {
        console.error('Error loading Pi details:', error);
    }
}

// Close details modal
function closeDetailsModal() {
    document.getElementById('details-modal').style.display = 'none';
    selectedPiId = null;
}

// Render Pi details
function renderPiDetails(pi) {
    const content = document.getElementById('pi-details-content');
    
    content.innerHTML = `
        <div class="info-row">
            <span class="info-label">Device ID:</span>
            <span class="info-value" style="font-family: monospace;">${pi.id}</span>
        </div>
        <div class="info-row">
            <span class="info-label">API Key:</span>
            <span class="info-value" style="font-family: monospace;">${pi.api_key}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Status:</span>
            <span class="info-value">${pi.status}</span>
        </div>
        <div class="info-row">
            <span class="info-label">WebSocket:</span>
            <span class="info-value">${pi.websocket_connected ? 'Connected' : 'Disconnected'}</span>
        </div>
        ${pi.config ? `
        <h3 style="margin-top: 20px;">Configuration</h3>
        <div class="info-row">
            <span class="info-label">Printer Device:</span>
            <span class="info-value">${pi.config.printer_device}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Queue Size:</span>
            <span class="info-value">${pi.config.queue_size}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Log Level:</span>
            <span class="info-value">${pi.config.log_level}</span>
        </div>
        ` : ''}
        <div id="metrics-display"></div>
    `;
}

// Render metrics
function renderMetrics(metrics) {
    const metricsDisplay = document.getElementById('metrics-display');
    
    metricsDisplay.innerHTML = `
        <h3 style="margin-top: 20px;">Latest Metrics</h3>
        <div class="metrics-grid">
            <div class="metric-item">
                <div class="metric-label">CPU Usage</div>
                <div class="metric-value">${metrics.cpu_usage?.toFixed(1) || 0}%</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Memory Usage</div>
                <div class="metric-value">${metrics.memory_usage?.toFixed(1) || 0}%</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Queue Size</div>
                <div class="metric-value">${metrics.queue_size || 0}</div>
            </div>
            <div class="metric-item">
                <div class="metric-label">Jobs Completed</div>
                <div class="metric-value">${metrics.jobs_completed || 0}</div>
            </div>
        </div>
    `;
}

// Show alert message
function showAlert(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    document.body.appendChild(alert);
    
    setTimeout(() => {
        alert.remove();
    }, 3000);
}

// Format date time
function formatDateTime(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Refresh dashboard
function refreshDashboard() {
    loadDashboard();
    showAlert('Dashboard refreshed', 'info');
}

// Show edit modal
async function showEditModal(piId) {
    const pi = currentPis.find(p => p.id === piId);
    if (!pi) return;
    
    document.getElementById('edit-pi-id').value = pi.id;
    document.getElementById('edit-pi-name').textContent = pi.friendly_name;
    document.getElementById('edit-friendly-name').value = pi.friendly_name;
    document.getElementById('edit-location').value = pi.location || '';
    document.getElementById('edit-printer-model').value = pi.printer_model || '';
    
    document.getElementById('edit-modal').style.display = 'block';
}

// Close edit modal
function closeEditModal() {
    document.getElementById('edit-modal').style.display = 'none';
    document.getElementById('edit-form').reset();
}

// Update Pi
async function updatePi(event) {
    event.preventDefault();
    
    const piId = document.getElementById('edit-pi-id').value;
    const updates = {
        friendly_name: document.getElementById('edit-friendly-name').value,
        location: document.getElementById('edit-location').value || null,
        printer_model: document.getElementById('edit-printer-model').value || null
    };
    
    try {
        const response = await fetch(`/api/pis/${piId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Printer updated successfully!', 'success');
            closeEditModal();
            loadDashboard();
        } else {
            showAlert(data.detail || 'Failed to update printer', 'error');
        }
    } catch (error) {
        console.error('Error updating printer:', error);
        showAlert('Failed to update printer', 'error');
    }
}

// Show delete modal
function showDeleteModal(piId, piName) {
    document.getElementById('delete-pi-id').value = piId;
    document.getElementById('delete-pi-name').textContent = piName;
    document.getElementById('delete-modal').style.display = 'block';
}

// Close delete modal
function closeDeleteModal() {
    document.getElementById('delete-modal').style.display = 'none';
}

// Confirm delete
async function confirmDelete() {
    const piId = document.getElementById('delete-pi-id').value;
    
    try {
        const response = await fetch(`/api/pis/${piId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Printer deleted successfully!', 'success');
            closeDeleteModal();
            loadDashboard();
        } else {
            showAlert(data.detail || 'Failed to delete printer', 'error');
        }
    } catch (error) {
        console.error('Error deleting printer:', error);
        showAlert('Failed to delete printer', 'error');
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
    }
}