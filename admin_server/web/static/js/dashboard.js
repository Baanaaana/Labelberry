// Global variables
let currentPis = [];
let selectedPiId = null;
let refreshInterval = null;

// Settings with defaults
let dashboardSettings = {
    timezone: 'Europe/Amsterdam',
    refreshInterval: 10000,
    dateFormat: 'DD-MM-YYYY'
};

// Load settings from localStorage
function loadSettings() {
    const saved = localStorage.getItem('labelberrySettings');
    if (saved) {
        try {
            dashboardSettings = JSON.parse(saved);
        } catch (e) {
            console.error('Failed to load settings:', e);
        }
    }
    return dashboardSettings;
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load saved settings
    loadSettings();
    
    // Load dashboard
    loadDashboard();
    
    // Set up auto-refresh based on settings
    setupAutoRefresh();
});

// Setup auto-refresh based on settings
function setupAutoRefresh() {
    // Clear existing interval
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    // Set new interval if not disabled
    if (dashboardSettings.refreshInterval > 0) {
        refreshInterval = setInterval(loadDashboard, dashboardSettings.refreshInterval);
    }
}

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
    document.getElementById('queue-status').textContent = stats.total_queue || 0;
}

// Render printer cards
function renderPrinters(pis) {
    const list = document.getElementById('printers-list');
    
    if (pis.length === 0) {
        list.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #6c757d;">
                <i data-lucide="printer" style="width: 48px; height: 48px; margin: 0 auto 16px;"></i>
                <p style="margin: 0; font-size: 16px; font-weight: 500;">No printers registered yet</p>
                <p style="margin: 8px 0 0; font-size: 14px;">Click "Register Printer" to add your first printer</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    list.innerHTML = pis.map(pi => createPrinterItem(pi)).join('');
    lucide.createIcons();
}

// Create printer item HTML
function createPrinterItem(pi) {
    const isOnline = pi.status === 'online';
    const statusClass = isOnline ? 'status-online' : 'status-offline';
    const statusText = isOnline ? 'Online' : 'Offline';
    
    return `
        <div class="printer-item">
            <div class="printer-item-header">
                <div class="printer-name">${pi.friendly_name}</div>
                <div class="printer-status ${statusClass}">${statusText}</div>
            </div>
            <div class="printer-details">
                <div class="detail-item">
                    <span class="detail-label">Location:</span>
                    <span class="detail-value">${pi.location || 'Not specified'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Model:</span>
                    <span class="detail-value">${pi.printer_model || 'Unknown'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Queue:</span>
                    <span class="detail-value">${pi.queue_count || 0} jobs</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Last Seen:</span>
                    <span class="detail-value">${formatDateTime(pi.last_seen)}</span>
                </div>
            </div>
            <div class="printer-actions">
                <button class="printer-btn primary" onclick="showPrintModal('${pi.id}', '${pi.friendly_name}')">
                    <i data-lucide="printer"></i> Test
                </button>
                <button class="printer-btn" onclick="showEditModal('${pi.id}')">
                    <i data-lucide="edit-2"></i> Edit
                </button>
                <button class="printer-btn" onclick="showDeleteModal('${pi.id}', '${pi.friendly_name}')">
                    <i data-lucide="trash-2"></i> Delete
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
    
    // Determine which tab is active
    const activeTab = document.querySelector('.tab-content.active');
    let printData = {};
    
    if (activeTab.id === 'raw-input') {
        const zplRaw = document.getElementById('zpl-raw').value;
        if (!zplRaw) {
            showAlert('Please enter ZPL code', 'error');
            return;
        }
        printData = { zpl_raw: zplRaw };
    } else if (activeTab.id === 'url-input') {
        const zplUrl = document.getElementById('zpl-url').value;
        if (!zplUrl) {
            showAlert('Please enter ZPL URL', 'error');
            return;
        }
        printData = { zpl_url: zplUrl };
    } else if (activeTab.id === 'file-input') {
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


// Show alert message (toast notification)
function showAlert(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Add icon based on type
    let iconName = '';
    switch(type) {
        case 'success':
            iconName = 'check-circle';
            break;
        case 'error':
            iconName = 'alert-circle';
            break;
        case 'info':
            iconName = 'info';
            break;
    }
    
    toast.innerHTML = `
        <i data-lucide="${iconName}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    lucide.createIcons();
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s reverse';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}

// Format date time based on user settings
function formatDateTime(dateString) {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    
    // Use timezone from settings
    const options = {
        timeZone: dashboardSettings.timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    
    // Choose locale based on date format preference
    let locale = 'en-US';
    if (dashboardSettings.dateFormat === 'DD-MM-YYYY') {
        locale = 'nl-NL';  // European format
    } else if (dashboardSettings.dateFormat === 'YYYY-MM-DD') {
        locale = 'en-CA';  // ISO format (Canadian English uses ISO)
    }
    
    return date.toLocaleString(locale, options);
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

// Show settings modal
function showSettingsModal() {
    // Load current settings into form
    document.getElementById('timezone-select').value = dashboardSettings.timezone;
    document.getElementById('refresh-interval').value = dashboardSettings.refreshInterval;
    document.getElementById('date-format').value = dashboardSettings.dateFormat;
    
    document.getElementById('settings-modal').style.display = 'block';
}

// Close settings modal
function closeSettingsModal() {
    document.getElementById('settings-modal').style.display = 'none';
}

// Save settings
function saveSettings(event) {
    event.preventDefault();
    
    // Get values from form
    dashboardSettings.timezone = document.getElementById('timezone-select').value;
    dashboardSettings.refreshInterval = parseInt(document.getElementById('refresh-interval').value);
    dashboardSettings.dateFormat = document.getElementById('date-format').value;
    
    // Save to localStorage
    localStorage.setItem('labelberrySettings', JSON.stringify(dashboardSettings));
    
    // Apply new settings
    setupAutoRefresh();
    
    // Reload dashboard to apply timezone changes
    loadDashboard();
    
    // Close modal and show success message
    closeSettingsModal();
    showAlert('Settings saved successfully!', 'success');
}

// Search printers
function searchPrinters(searchTerm) {
    const filtered = currentPis.filter(pi => 
        pi.friendly_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (pi.location && pi.location.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (pi.printer_model && pi.printer_model.toLowerCase().includes(searchTerm.toLowerCase()))
    );
    renderPrinters(filtered);
}

// Switch print tab
function switchPrintTab(tabName) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update tab content
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}-input`).classList.add('active');
}

// Show broadcast modal
function showBroadcastModal() {
    showAlert('Broadcast print feature coming soon!', 'info');
}

// View logs
function viewLogs() {
    showAlert('Log viewer coming soon!', 'info');
}

// Show metrics
function showMetrics() {
    showAlert('Metrics dashboard coming soon!', 'info');
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
    }
}