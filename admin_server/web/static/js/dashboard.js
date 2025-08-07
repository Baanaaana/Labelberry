// Global variables
let currentPis = [];
let selectedPiId = null;
let refreshInterval = null;
let labelSizes = [];

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

// Display server IP address
async function displayServerIP() {
    const serverIpElement = document.getElementById('server-ip');
    if (serverIpElement) {
        try {
            // Fetch the actual server's local IP
            const response = await fetch('/api/server-info');
            const data = await response.json();
            
            if (data.local_ip) {
                // Display the actual local IP and port
                serverIpElement.textContent = `${data.local_ip}:${data.port}`;
            } else {
                // Fallback to current hostname
                const hostname = window.location.hostname;
                const port = window.location.port || '80';
                serverIpElement.textContent = `${hostname}:${port}`;
            }
        } catch (error) {
            console.error('Failed to get server IP:', error);
            // Fallback to current hostname
            const hostname = window.location.hostname;
            const port = window.location.port || '80';
            serverIpElement.textContent = `${hostname}:${port}`;
        }
    }
}

// Copy server address to clipboard
async function copyServerAddress() {
    const serverIpElement = document.getElementById('server-ip');
    if (serverIpElement) {
        const address = `http://${serverIpElement.textContent}`;
        try {
            await navigator.clipboard.writeText(address);
            showAlert('Server address copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            showAlert('Failed to copy server address', 'error');
        }
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Load saved settings
    loadSettings();
    
    // Load label sizes
    loadLabelSizes();
    
    // Load dashboard
    loadDashboard();
    
    // Display server IP
    displayServerIP();
    
    // Set up auto-refresh based on settings
    setupAutoRefresh();
});

// Load label sizes from server
async function loadLabelSizes() {
    try {
        const response = await fetch('/api/label-sizes');
        const data = await response.json();
        
        if (data.success) {
            labelSizes = data.data.sizes;
            updateLabelSizeDropdowns();
        }
    } catch (error) {
        console.error('Failed to load label sizes:', error);
    }
}

// Update label size dropdowns
function updateLabelSizeDropdowns() {
    const registerSelect = document.getElementById('label-size');
    const editSelect = document.getElementById('edit-label-size');
    
    // Build options HTML
    let optionsHTML = '<option value="">Select label size...</option>';
    labelSizes.forEach(size => {
        optionsHTML += `<option value="${size.id}">${size.display_name}</option>`;
    });
    
    if (registerSelect) {
        registerSelect.innerHTML = optionsHTML;
    }
    if (editSelect) {
        editSelect.innerHTML = optionsHTML;
    }
}

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
    
    if (!list) {
        console.error('Printers list element not found');
        return;
    }
    
    if (pis.length === 0) {
        list.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #6c757d;">
                <i data-lucide="printer" style="width: 48px; height: 48px; margin: 0 auto 16px;"></i>
                <p style="margin: 0; font-size: 16px; font-weight: 500;">No printers registered yet</p>
                <p style="margin: 8px 0 0; font-size: 14px;">Click "Add Printer" to add your first printer</p>
            </div>
        `;
        lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
        return;
    }
    
    list.innerHTML = pis.map(pi => createPrinterItem(pi)).join('');
    lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
}

// Create printer item HTML
function createPrinterItem(pi) {
    try {
        const isOnline = pi.status === 'online';
        const statusClass = isOnline ? 'status-online' : 'status-offline';
        const statusText = isOnline ? 'Online' : 'Offline';
        
        // Extract dimensions from label size display name
        let labelDimensions = 'Not specified';
        let labelSizeClass = 'label-size-default';
        if (pi.label_size && pi.label_size.display_name) {
            const match = pi.label_size.display_name.match(/\(([^)]+)\)/);
            if (match) {
                labelDimensions = match[1];
            } else {
                labelDimensions = pi.label_size.display_name;
            }
            
            // Assign color class based on size
            if (labelDimensions.includes('57mm') || labelDimensions.includes('2.25"')) {
                labelSizeClass = 'label-size-small';
            } else if (labelDimensions.includes('102mm') || labelDimensions.includes('4"')) {
                labelSizeClass = 'label-size-large';
            } else if (labelDimensions.includes('76mm') || labelDimensions.includes('3"')) {
                labelSizeClass = 'label-size-medium';
            } else {
                labelSizeClass = 'label-size-custom';
            }
        }
        
        return `
        <div class="printer-item">
            <div class="printer-item-header">
                <div class="printer-name">${pi.friendly_name}</div>
                <div class="printer-status-container">
                    <div class="label-size-badge ${labelSizeClass}">${labelDimensions}</div>
                    <div class="queue-label">${pi.queue_count || 0} in queue</div>
                    <div class="printer-status ${statusClass}">${statusText}</div>
                </div>
            </div>
            <div class="printer-details">
                <!-- Left column items -->
                <div class="detail-item">
                    <span class="detail-label">Device ID:</span>
                    <span class="detail-value device-id-clickable" onclick="copyDeviceId('${pi.id}')" title="Click to copy">
                        ${pi.id}
                    </span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">IP Address:</span>
                    ${pi.ip_address ? 
                        `<span class="detail-value ip-address-clickable" onclick="copyIpAddress('${pi.ip_address}')" title="Click to copy">
                            ${pi.ip_address}
                        </span>` :
                        `<span class="detail-value" style="color: var(--text-secondary);">Not available</span>`
                    }
                </div>
                <div class="detail-item">
                    <span class="detail-label">Device Name:</span>
                    <span class="detail-value">${pi.device_name || 'Not specified'}</span>
                </div>
                <!-- Right column items -->
                <div class="detail-item">
                    <span class="detail-label">Location:</span>
                    <span class="detail-value">${pi.location || 'Not specified'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Model:</span>
                    <span class="detail-value">${pi.printer_model || 'Unknown'}</span>
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
                <div style="display: flex; gap: 8px;">
                    <button class="printer-btn" onclick="showEditModal('${pi.id}')">
                        <i data-lucide="edit-2"></i> Edit
                    </button>
                    <button class="printer-btn" onclick="showDeleteModal('${pi.id}', '${pi.friendly_name}')">
                        <i data-lucide="trash-2"></i> Delete
                    </button>
                </div>
            </div>
        </div>
    `;
    } catch (error) {
        console.error('Error creating printer item:', error, pi);
        return '';
    }
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
    const deviceName = document.getElementById('device-name').value;
    const location = document.getElementById('location').value;
    const labelSizeId = document.getElementById('label-size').value;
    
    const piData = {
        id: deviceId,
        api_key: apiKey,
        friendly_name: friendlyName,
        device_name: deviceName || null,
        location: location || null,
        label_size_id: labelSizeId ? parseInt(labelSizeId) : null,
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
    
    // Set default label size and ZPL
    document.getElementById('label-size-select').value = 'small';
    updateTestZPL();
}

// Update test ZPL based on label size selection
function updateTestZPL() {
    const sizeSelect = document.getElementById('label-size-select');
    const zplTextarea = document.getElementById('zpl-raw');
    
    if (sizeSelect.value === 'small') {
        // 57mm x 32mm label (approximately 448 x 252 dots at 203 DPI)
        // 57mm = 2.24" = 455 dots, 32mm = 1.26" = 256 dots
        zplTextarea.value = `^XA
^PW448
^LL252
^FO20,20^A0N,25,25^FDLabelBerry Test - Small Label^FS
^FO20,50^A0N,20,20^FD57mm x 32mm^FS
^FO20,80^GB408,1,2^FS
^FO20,90^A0N,18,18^FDPrinter: ${selectedPiId ? currentPis.find(p => p.id === selectedPiId)?.friendly_name : 'Test'}^FS
^FO20,115^A0N,18,18^FDDate: ${new Date().toLocaleDateString()}^FS
^FO20,140^A0N,18,18^FDTime: ${new Date().toLocaleTimeString()}^FS
^FO20,170^BY2,3,50^BCN,50,Y,N,N^FD123456789^FS
^XZ`;
    } else if (sizeSelect.value === 'large') {
        // 102mm x 150mm label (approximately 812 x 1218 dots at 203 DPI)
        // 102mm = 4.02" = 816 dots, 150mm = 5.91" = 1200 dots
        zplTextarea.value = `^XA
^PW812
^LL1218
^FO50,50^A0N,50,50^FDLabelBerry Test - Large Label^FS
^FO50,120^A0N,35,35^FD102mm x 150mm^FS
^FO50,180^GB712,3,3^FS
^FO50,200^A0N,30,30^FDShipping Information^FS
^FO50,250^A0N,25,25^FDFrom: LabelBerry Warehouse^FS
^FO50,285^A0N,25,25^FD      123 Test Street^FS
^FO50,320^A0N,25,25^FD      Amsterdam, 1234 AB^FS
^FO50,370^GB712,2,2^FS
^FO50,390^A0N,30,30^FDTo: Customer Name^FS
^FO50,440^A0N,25,25^FD    456 Delivery Road^FS
^FO50,475^A0N,25,25^FD    Rotterdam, 5678 CD^FS
^FO50,530^GB712,2,2^FS
^FO50,550^A0N,25,25^FDPrinter: ${selectedPiId ? currentPis.find(p => p.id === selectedPiId)?.friendly_name : 'Test'}^FS
^FO50,585^A0N,25,25^FDDate: ${new Date().toLocaleDateString()}^FS
^FO50,620^A0N,25,25^FDTime: ${new Date().toLocaleTimeString()}^FS
^FO50,680^BY3,3,100^BCN,100,Y,N,N^FD987654321^FS
^FO50,850^A0N,20,20^FDTracking: NL-987654321-LB^FS
^FO50,900^BQN,2,10^FDHA,https://labelberry.local/track/987654321^FS
^XZ`;
    } else {
        // Custom - leave it empty or with a basic template
        zplTextarea.value = `^XA
^FO50,50^A0N,40,40^FDCustom Label^FS
^FO50,100^A0N,25,25^FDEnter your custom ZPL code^FS
^XZ`;
    }
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
        
        const response = await fetch(`/api/pis/${selectedPiId}/test-print`, {
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


// Copy device ID to clipboard
async function copyDeviceId(deviceId) {
    try {
        await navigator.clipboard.writeText(deviceId);
        showAlert('Device ID copied to clipboard', 'success');
    } catch (err) {
        console.error('Failed to copy:', err);
        showAlert('Failed to copy Device ID', 'error');
    }
}

// Copy IP address to clipboard
async function copyIpAddress(ipAddress) {
    try {
        await navigator.clipboard.writeText(ipAddress);
        showAlert('IP address copied to clipboard', 'success');
    } catch (err) {
        console.error('Failed to copy:', err);
        showAlert('Failed to copy IP address', 'error');
    }
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
    lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
    
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
    
    // Make sure dropdowns are populated
    updateLabelSizeDropdowns();
    
    document.getElementById('edit-pi-id').value = pi.id;
    document.getElementById('edit-friendly-name').value = pi.friendly_name;
    document.getElementById('edit-device-name').value = pi.device_name || '';
    document.getElementById('edit-location').value = pi.location || '';
    document.getElementById('edit-label-size').value = pi.label_size_id || '';
    
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
    const labelSizeId = document.getElementById('edit-label-size').value;
    const updates = {
        friendly_name: document.getElementById('edit-friendly-name').value,
        device_name: document.getElementById('edit-device-name').value || null,
        location: document.getElementById('edit-location').value || null,
        label_size_id: labelSizeId ? parseInt(labelSizeId) : null
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
    // Populate printer checkboxes
    const list = document.getElementById('broadcast-printer-list');
    const onlinePrinters = currentPis.filter(pi => pi.status === 'online');
    
    if (onlinePrinters.length === 0) {
        list.innerHTML = '<p style="color: #999; margin: 0;">No online printers available</p>';
    } else {
        list.innerHTML = onlinePrinters.map(pi => `
            <label style="display: flex; align-items: center; padding: 12px; cursor: pointer; border-radius: 6px; transition: background 0.2s; margin-bottom: 8px; background: transparent;" 
                   onmouseover="this.style.background='#f8f9fa'" 
                   onmouseout="this.style.background='transparent'">
                <input type="checkbox" 
                       value="${pi.id}" 
                       checked 
                       style="margin-right: 12px; flex-shrink: 0;">
                <span style="flex: 1; font-size: 14px; font-weight: 500; color: var(--text-primary);">${pi.friendly_name}</span>
                <span style="color: var(--text-secondary); font-size: 12px; margin-left: auto; padding-left: 12px;">${pi.location || ''}</span>
            </label>
        `).join('');
    }
    
    document.getElementById('broadcast-modal').style.display = 'block';
}

// Close broadcast modal
function closeBroadcastModal() {
    document.getElementById('broadcast-modal').style.display = 'none';
    document.getElementById('broadcast-form').reset();
}

// Switch broadcast tab
function switchBroadcastTab(tabName) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('#broadcast-modal .tab-btn');
    tabButtons.forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update tab content
    document.getElementById('broadcast-raw-input').classList.toggle('active', tabName === 'raw');
    document.getElementById('broadcast-url-input').classList.toggle('active', tabName === 'url');
}

// Send broadcast print
async function sendBroadcast(event) {
    event.preventDefault();
    
    // Get selected printers
    const checkboxes = document.querySelectorAll('#broadcast-printer-list input[type="checkbox"]:checked');
    const selectedPis = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedPis.length === 0) {
        showAlert('Please select at least one printer', 'error');
        return;
    }
    
    // Determine print data
    const activeTab = document.querySelector('#broadcast-modal .tab-content.active');
    let printData = {};
    
    if (activeTab.id === 'broadcast-raw-input') {
        const zplRaw = document.getElementById('broadcast-zpl-raw').value;
        if (!zplRaw) {
            showAlert('Please enter ZPL code', 'error');
            return;
        }
        printData = { zpl_raw: zplRaw };
    } else if (activeTab.id === 'broadcast-url-input') {
        const zplUrl = document.getElementById('broadcast-zpl-url').value;
        if (!zplUrl) {
            showAlert('Please enter ZPL URL', 'error');
            return;
        }
        printData = { zpl_url: zplUrl };
    }
    
    // Send to each selected printer
    let successCount = 0;
    let failCount = 0;
    
    for (const piId of selectedPis) {
        try {
            const response = await fetch(`/api/pis/${piId}/test-print`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(printData)
            });
            
            if (response.ok) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (error) {
            failCount++;
        }
    }
    
    if (successCount > 0 && failCount === 0) {
        showAlert(`Print job sent to ${successCount} printer(s) successfully!`, 'success');
    } else if (successCount > 0 && failCount > 0) {
        showAlert(`Sent to ${successCount} printer(s), failed for ${failCount}`, 'warning');
    } else {
        showAlert('Failed to send print job to all printers', 'error');
    }
    
    closeBroadcastModal();
}

// View logs
function viewLogs() {
    // Populate printer filter
    const filter = document.getElementById('log-pi-filter');
    filter.innerHTML = '<option value="">All Sources</option>' + 
        '<option value="__server__">Admin Server</option>' +
        currentPis.map(pi => `<option value="${pi.id}">${pi.friendly_name}</option>`).join('');
    
    // Load logs
    loadLogs();
    
    document.getElementById('logs-modal').style.display = 'block';
}

// Close logs modal
function closeLogsModal() {
    document.getElementById('logs-modal').style.display = 'none';
}

// Format log details for display
function formatLogDetails(details) {
    if (!details) return '';
    
    try {
        // Try to parse as JSON
        const parsed = typeof details === 'string' ? JSON.parse(details) : details;
        
        // Format the details nicely
        const items = [];
        for (const [key, value] of Object.entries(parsed)) {
            // Format key nicely (convert snake_case to Title Case)
            const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            
            // Format value based on type
            let formattedValue = value;
            if (typeof value === 'object' && value !== null) {
                formattedValue = JSON.stringify(value, null, 2);
            }
            
            items.push(`<span style="color: #666; font-weight: 500;">${formattedKey}:</span> ${formattedValue}`);
        }
        
        if (items.length > 0) {
            return `<div style="color: #666; font-size: 11px; margin-top: 4px; padding-left: 12px; border-left: 2px solid #e0e0e0;">
                ${items.join('<br>')}
            </div>`;
        }
    } catch (e) {
        // If it's not JSON, just display as text
        return `<div style="color: #666; font-size: 11px; margin-top: 4px;">${details}</div>`;
    }
    
    return '';
}

// Load logs
async function loadLogs() {
    const piFilter = document.getElementById('log-pi-filter').value;
    const levelFilter = document.getElementById('log-level-filter').value;
    const container = document.getElementById('logs-container');
    
    container.innerHTML = '<div style="text-align: center; color: #999;">Loading logs...</div>';
    
    try {
        let logs = [];
        
        if (piFilter) {
            if (piFilter === '__server__') {
                // Get server logs
                const response = await fetch(`/api/pis/__server__/logs?limit=200`);
                const data = await response.json();
                if (data.success) {
                    logs = data.data.logs.map(log => ({...log, pi_name: 'Admin Server'}));
                }
            } else {
                // Get logs for specific Pi
                const response = await fetch(`/api/pis/${piFilter}/logs?limit=200`);
                const data = await response.json();
                if (data.success) {
                    logs = data.data.logs;
                }
            }
        } else {
            // Get logs for all Pis and server
            for (const pi of currentPis) {
                const response = await fetch(`/api/pis/${pi.id}/logs?limit=50`);
                const data = await response.json();
                if (data.success) {
                    logs = logs.concat(data.data.logs.map(log => ({...log, pi_name: pi.friendly_name})));
                }
            }
            
            // Also get server logs
            const serverResponse = await fetch(`/api/pis/__server__/logs?limit=50`);
            const serverData = await serverResponse.json();
            if (serverData.success) {
                logs = logs.concat(serverData.data.logs.map(log => ({...log, pi_name: 'Admin Server'})));
            }
        }
        
        // Filter by level if specified
        if (levelFilter) {
            logs = logs.filter(log => log.level === levelFilter);
        }
        
        // Sort by timestamp (newest first)
        logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        // Render logs
        if (logs.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #999;">No logs found</div>';
        } else {
            container.innerHTML = logs.map(log => {
                const levelColor = log.level === 'ERROR' ? '#dc3545' : 
                                   log.level === 'WARNING' ? '#ffc107' : '#6c757d';
                const logType = log.error_type || 'info';
                return `
                    <div style="margin-bottom: 8px; padding: 8px; background: white; border-radius: 4px; border-left: 3px solid ${levelColor};">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="color: ${levelColor}; font-weight: 600;">[${logType}]</span>
                            <span style="color: #999; font-size: 11px;">${log.pi_name || ''} - ${formatDateTime(log.timestamp)}</span>
                        </div>
                        <div style="color: #333; word-wrap: break-word;">${log.message}</div>
                        ${log.details ? formatLogDetails(log.details) : ''}
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        container.innerHTML = '<div style="text-align: center; color: #dc3545;">Failed to load logs</div>';
    }
}

// Filter logs
function filterLogs() {
    loadLogs();
}

// Refresh logs
function refreshLogs() {
    loadLogs();
    showAlert('Logs refreshed', 'info');
}

// Show metrics
function showMetrics() {
    // Populate printer filter
    const filter = document.getElementById('metrics-pi-filter');
    filter.innerHTML = '<option value="">All Printers</option>' + 
        currentPis.map(pi => `<option value="${pi.id}">${pi.friendly_name}</option>`).join('');
    
    // Load metrics
    loadMetrics();
    
    document.getElementById('metrics-modal').style.display = 'block';
}

// Close metrics modal
function closeMetricsModal() {
    document.getElementById('metrics-modal').style.display = 'none';
}

// Load metrics
async function loadMetrics() {
    const piFilter = document.getElementById('metrics-pi-filter').value;
    const timeRange = parseInt(document.getElementById('metrics-time-range').value);
    
    try {
        let allMetrics = [];
        let pis = piFilter ? [currentPis.find(p => p.id === piFilter)] : currentPis;
        
        for (const pi of pis) {
            if (!pi) continue;
            
            const response = await fetch(`/api/pis/${pi.id}/metrics?hours=${timeRange}`);
            const data = await response.json();
            
            if (data.success && data.data.metrics.length > 0) {
                const piMetrics = data.data.metrics.map(m => ({
                    ...m,
                    pi_id: pi.id,
                    pi_name: pi.friendly_name
                }));
                allMetrics = allMetrics.concat(piMetrics);
            }
        }
        
        // Calculate aggregates
        if (allMetrics.length > 0) {
            const avgCpu = allMetrics.reduce((sum, m) => sum + (m.cpu_usage || 0), 0) / allMetrics.length;
            const avgMemory = allMetrics.reduce((sum, m) => sum + (m.memory_usage || 0), 0) / allMetrics.length;
            const totalJobs = allMetrics.reduce((sum, m) => sum + (m.jobs_completed || 0), 0);
            const totalFailed = allMetrics.reduce((sum, m) => sum + (m.jobs_failed || 0), 0);
            const successRate = totalJobs > 0 ? ((totalJobs - totalFailed) / totalJobs * 100) : 0;
            
            document.getElementById('avg-cpu').textContent = avgCpu.toFixed(1) + '%';
            document.getElementById('avg-memory').textContent = avgMemory.toFixed(1) + '%';
            document.getElementById('total-jobs').textContent = totalJobs;
            document.getElementById('success-rate').textContent = successRate.toFixed(1) + '%';
            
            // Group metrics by Pi and get latest for each
            const latestMetrics = {};
            for (const metric of allMetrics) {
                if (!latestMetrics[metric.pi_id] || 
                    new Date(metric.timestamp) > new Date(latestMetrics[metric.pi_id].timestamp)) {
                    latestMetrics[metric.pi_id] = metric;
                }
            }
            
            // Render table
            const tbody = document.getElementById('metrics-tbody');
            tbody.innerHTML = Object.values(latestMetrics).map(m => `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 12px 8px; font-weight: 500;">${m.pi_name}</td>
                    <td style="padding: 12px 8px; text-align: center;">${(m.cpu_usage || 0).toFixed(1)}%</td>
                    <td style="padding: 12px 8px; text-align: center;">${(m.memory_usage || 0).toFixed(1)}%</td>
                    <td style="padding: 12px 8px; text-align: center;">${m.queue_size || 0}</td>
                    <td style="padding: 12px 8px; text-align: center;">${m.jobs_completed || 0}</td>
                    <td style="padding: 12px 8px; text-align: center; color: ${m.jobs_failed > 0 ? '#dc3545' : 'inherit'};">${m.jobs_failed || 0}</td>
                    <td style="padding: 12px 8px;">${formatDateTime(m.timestamp)}</td>
                </tr>
            `).join('');
        } else {
            document.getElementById('avg-cpu').textContent = '0%';
            document.getElementById('avg-memory').textContent = '0%';
            document.getElementById('total-jobs').textContent = '0';
            document.getElementById('success-rate').textContent = '0%';
            
            document.getElementById('metrics-tbody').innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 24px; color: #999;">
                        No metrics data available for the selected time range
                    </td>
                </tr>
            `;
        }
    } catch (error) {
        console.error('Error loading metrics:', error);
        showAlert('Failed to load metrics', 'error');
    }
    
    // Re-initialize Lucide icons for new content
    lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.className === 'modal') {
        event.target.style.display = 'none';
    }
}

// Queue Management Functions
let currentJobId = null;
let queueData = null;

function showQueueModal() {
    document.getElementById('queue-modal').style.display = 'flex';
    loadQueuePrinters();
    loadQueue();
}

function closeQueueModal() {
    document.getElementById('queue-modal').style.display = 'none';
}

async function loadQueuePrinters() {
    try {
        const response = await fetch('/api/pis');
        const result = await response.json();
        
        if (result.success) {
            const select = document.getElementById('queue-pi-filter');
            const currentValue = select.value;
            
            select.innerHTML = '<option value="">All Printers</option>';
            result.data.pis.forEach(pi => {
                select.innerHTML += `<option value="${pi.id}">${pi.friendly_name}</option>`;
            });
            
            select.value = currentValue;
        }
    } catch (error) {
        console.error('Error loading printers for queue:', error);
    }
}

async function loadQueue() {
    try {
        const piId = document.getElementById('queue-pi-filter').value;
        const endpoint = piId ? `/api/queue/${piId}` : '/api/queue';
        
        const response = await fetch(endpoint);
        const result = await response.json();
        
        if (result.success) {
            queueData = result.data;
            renderQueueStats(result.data.stats);
            renderQueueTable(result.data.jobs);
        }
    } catch (error) {
        console.error('Error loading queue:', error);
        showAlert('Failed to load queue', 'error');
    }
}

function renderQueueStats(stats) {
    document.getElementById('queue-total').textContent = stats.total || 0;
    document.getElementById('queue-queued').textContent = stats.queued || 0;
    document.getElementById('queue-processing').textContent = (stats.processing || 0) + (stats.sent || 0);
    document.getElementById('queue-completed').textContent = stats.completed || 0;
    document.getElementById('queue-failed').textContent = stats.failed || 0;
}

function renderQueueTable(jobs) {
    const tbody = document.getElementById('queue-tbody');
    const emptyDiv = document.getElementById('queue-empty');
    
    if (!jobs || jobs.length === 0) {
        tbody.style.display = 'none';
        emptyDiv.style.display = 'block';
        return;
    }
    
    tbody.style.display = '';
    emptyDiv.style.display = 'none';
    
    tbody.innerHTML = jobs.map((job, index) => {
        const statusColor = {
            'queued': '#fbbf24',
            'sent': '#3b82f6',
            'processing': '#3b82f6',
            'completed': '#10b981',
            'failed': '#ef4444',
            'cancelled': '#6b7280',
            'expired': '#6b7280'
        }[job.status] || '#6b7280';
        
        const canCancel = ['queued', 'sent', 'pending'].includes(job.status);
        const canRetry = job.status === 'failed';
        
        return `
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: 12px;">${job.status === 'queued' ? index + 1 : '-'}</td>
                <td style="padding: 12px; font-family: monospace; font-size: 12px;">
                    ${job.id.substring(0, 8)}...
                </td>
                <td style="padding: 12px;">${job.pi_name || 'Unknown'}</td>
                <td style="padding: 12px;">
                    <span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; background: ${statusColor}20; color: ${statusColor}; border-radius: 4px; font-size: 12px; font-weight: 500;">
                        ${job.status.toUpperCase()}
                    </span>
                </td>
                <td style="padding: 12px; text-align: center;">${job.priority || 5}</td>
                <td style="padding: 12px; font-size: 13px;">${formatDateTime(job.created_at)}</td>
                <td style="padding: 12px;">
                    <div style="display: flex; gap: 8px;">
                        <button class="icon-btn" onclick="showJobDetails('${job.id}')" title="View Details" style="padding: 4px;">
                            <i data-lucide="eye" style="width: 16px; height: 16px;"></i>
                        </button>
                        ${canRetry ? `
                            <button class="icon-btn" onclick="retryJobFromQueue('${job.id}')" title="Retry" style="padding: 4px; color: #fbbf24;">
                                <i data-lucide="refresh-cw" style="width: 16px; height: 16px;"></i>
                            </button>
                        ` : ''}
                        ${canCancel ? `
                            <button class="icon-btn" onclick="cancelJobFromQueue('${job.id}')" title="Cancel" style="padding: 4px; color: #ef4444;">
                                <i data-lucide="x-circle" style="width: 16px; height: 16px;"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    // Re-initialize Lucide icons
    lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
}

function refreshQueue() {
    loadQueue();
    showAlert('Queue refreshed', 'success');
}

async function clearQueue() {
    const piId = document.getElementById('queue-pi-filter').value;
    
    if (!confirm('Are you sure you want to clear all queued jobs? This cannot be undone.')) {
        return;
    }
    
    try {
        const endpoint = piId ? `/api/queue/${piId}/clear` : '/api/queue/clear';
        const response = await fetch(endpoint, { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showAlert(`Cleared ${result.data.cancelled_count} jobs`, 'success');
            loadQueue();
        } else {
            showAlert('Failed to clear queue', 'error');
        }
    } catch (error) {
        console.error('Error clearing queue:', error);
        showAlert('Failed to clear queue', 'error');
    }
}

async function showJobDetails(jobId) {
    currentJobId = jobId;
    
    // Find job in current data
    const job = queueData.jobs.find(j => j.id === jobId);
    if (!job) return;
    
    const modal = document.getElementById('job-details-modal');
    const content = document.getElementById('job-details-content');
    const retryBtn = document.getElementById('job-retry-btn');
    const cancelBtn = document.getElementById('job-cancel-btn');
    
    // Show/hide action buttons based on status
    retryBtn.style.display = job.status === 'failed' ? 'inline-flex' : 'none';
    cancelBtn.style.display = ['queued', 'sent', 'pending'].includes(job.status) ? 'inline-flex' : 'none';
    
    // Render job details
    content.innerHTML = `
        <div style="display: grid; gap: 16px;">
            <div>
                <label style="color: var(--text-secondary); font-size: 12px;">Job ID</label>
                <div style="font-family: monospace; margin-top: 4px;">${job.id}</div>
            </div>
            <div>
                <label style="color: var(--text-secondary); font-size: 12px;">Printer</label>
                <div style="margin-top: 4px;">${job.pi_name || 'Unknown'}</div>
            </div>
            <div>
                <label style="color: var(--text-secondary); font-size: 12px;">Status</label>
                <div style="margin-top: 4px;">${job.status.toUpperCase()}</div>
            </div>
            <div>
                <label style="color: var(--text-secondary); font-size: 12px;">Priority</label>
                <div style="margin-top: 4px;">${job.priority || 5}</div>
            </div>
            <div>
                <label style="color: var(--text-secondary); font-size: 12px;">Created</label>
                <div style="margin-top: 4px;">${formatDateTime(job.created_at)}</div>
            </div>
            ${job.error_message ? `
                <div>
                    <label style="color: var(--text-secondary); font-size: 12px;">Error</label>
                    <div style="margin-top: 4px; color: #ef4444;">${job.error_message}</div>
                </div>
            ` : ''}
            ${job.retry_count > 0 ? `
                <div>
                    <label style="color: var(--text-secondary); font-size: 12px;">Retry Count</label>
                    <div style="margin-top: 4px;">${job.retry_count} / ${job.max_retries || 3}</div>
                </div>
            ` : ''}
        </div>
    `;
    
    modal.style.display = 'flex';
}

function closeJobDetailsModal() {
    document.getElementById('job-details-modal').style.display = 'none';
    currentJobId = null;
}

async function retryJob() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`/api/queue/job/${currentJobId}/retry`, { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showAlert('Job queued for retry', 'success');
            closeJobDetailsModal();
            loadQueue();
        } else {
            showAlert(result.message || 'Failed to retry job', 'error');
        }
    } catch (error) {
        console.error('Error retrying job:', error);
        showAlert('Failed to retry job', 'error');
    }
}

async function cancelJob() {
    if (!currentJobId) return;
    
    if (!confirm('Are you sure you want to cancel this job?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/queue/job/${currentJobId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (result.success) {
            showAlert('Job cancelled', 'success');
            closeJobDetailsModal();
            loadQueue();
        } else {
            showAlert(result.message || 'Failed to cancel job', 'error');
        }
    } catch (error) {
        console.error('Error cancelling job:', error);
        showAlert('Failed to cancel job', 'error');
    }
}

async function retryJobFromQueue(jobId) {
    currentJobId = jobId;
    await retryJob();
}

async function cancelJobFromQueue(jobId) {
    currentJobId = jobId;
    await cancelJob();
}