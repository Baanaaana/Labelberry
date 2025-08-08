// API Documentation JavaScript

let availablePrinters = [];
let userApiKeys = [];
let labelSizes = [];

// Flag to prevent scroll spy during programmatic scrolling
let isScrolling = false;

// Initialize page on load
window.addEventListener('DOMContentLoaded', async () => {
    // Set base URL
    const baseUrl = window.labelberryBaseUrl || window.location.origin;
    document.getElementById('base-url').textContent = baseUrl;
    
    // Load data
    await loadPrinters();
    await loadApiKeys();
    await loadLabelSizes();
    
    // Update dynamic content
    updateDynamicContent();
    
    // Initialize Lucide icons
    lucide.createIcons();
    
    // Setup scroll spy
    setupScrollSpy();
});

// Scroll to section smoothly
function scrollToSection(sectionId, navItem) {
    isScrolling = true;
    
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    if (navItem) navItem.classList.add('active');
    
    // Scroll to section
    const section = document.getElementById(sectionId);
    if (section) {
        // Get the header height for offset
        const header = document.querySelector('.docs-header');
        const headerHeight = header ? header.offsetHeight : 0;
        
        // Add some padding so the section title isn't right at the top
        const padding = 20;
        const offset = headerHeight + padding;
        
        // Calculate the target scroll position
        const sectionTop = section.getBoundingClientRect().top + window.pageYOffset;
        const targetPosition = sectionTop - offset;
        
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
    
    setTimeout(() => { isScrolling = false; }, 500);
}

// Copy code to clipboard
async function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    let code = codeBlock.querySelector('code').textContent;
    
    // Replace placeholders with actual values
    const baseUrl = window.labelberryBaseUrl || window.location.origin;
    code = code.replace(/http:\/\/your-server:8080/g, baseUrl);
    code = code.replace(/\{pi_id\}/g, availablePrinters.length > 0 ? availablePrinters[0].id : 'YOUR_PRINTER_ID');
    code = code.replace(/labk_your_api_key_here/g, 'YOUR_API_KEY');
    
    try {
        await navigator.clipboard.writeText(code);
        
        // Show feedback
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i data-lucide="check" style="width: 16px; height: 16px;"></i>';
        button.style.color = '#12b886';
        lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.color = '';
            lucide.createIcons({
                attrs: {
                    width: 20,
                    height: 20
                }
            });
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        showAlert('Failed to copy to clipboard', 'error');
    }
}

// Load available printers
async function loadPrinters() {
    try {
        const response = await fetch('/api/pis');
        const data = await response.json();
        
        if (data.success) {
            availablePrinters = data.data.pis;
            updatePrinterSelects();
        }
    } catch (error) {
        console.error('Failed to load printers:', error);
    }
}

// Load API keys
async function loadApiKeys() {
    try {
        const response = await fetch('/api/keys');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                userApiKeys = data.data.keys || [];
                updateApiKeySelects();
                displayUserApiKeys();
            }
        }
    } catch (error) {
        // User might not be logged in
        console.log('Could not load API keys');
    }
}

// Load label sizes
async function loadLabelSizes() {
    try {
        const response = await fetch('/api/label-sizes');
        const data = await response.json();
        
        if (data.success) {
            labelSizes = data.data.sizes || [];
        }
    } catch (error) {
        console.error('Failed to load label sizes:', error);
    }
}

// Update all dynamic commands with actual values
function updateDynamicCommands() {
    const baseUrl = window.labelberryBaseUrl || window.location.origin;
    
    // Update all base URLs
    document.querySelectorAll('.dynamic-url').forEach(el => {
        el.textContent = baseUrl;
    });
    
    // Update printer IDs if available
    if (availablePrinters.length > 0) {
        const firstPrinter = availablePrinters[0];
        document.querySelectorAll('.dynamic-printer-id').forEach(el => {
            el.textContent = firstPrinter.id;
        });
        
        // Update printer info displays
        document.querySelectorAll('.dynamic-printer-info').forEach(el => {
            el.textContent = `${firstPrinter.friendly_name} (${firstPrinter.id})`;
        });
    }
    
    // Generate actual cURL commands
    generateCurlCommands();
}

// Generate actual cURL commands
function generateCurlCommands() {
    const baseUrl = window.labelberryBaseUrl || window.location.origin;
    const printerId = availablePrinters.length > 0 ? availablePrinters[0].id : 'PRINTER_ID';
    const printerName = availablePrinters.length > 0 ? availablePrinters[0].friendly_name : 'your printer';
    
    // List printers command
    const listCmd = document.getElementById('curl-list-printers');
    if (listCmd) {
        listCmd.textContent = `curl -X GET ${baseUrl}/api/pis`;
    }
    
    // Second list printers command
    const listCmd2 = document.getElementById('curl-list-printers-2');
    if (listCmd2) {
        listCmd2.textContent = `curl -X GET ${baseUrl}/api/pis`;
    }
    
    // Print command with actual printer ID
    const printCmd = document.getElementById('curl-print');
    if (printCmd) {
        if (availablePrinters.length > 0) {
            printCmd.textContent = `# Print to "${printerName}"
curl -X POST ${baseUrl}/api/pis/${printerId}/print \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_raw": "^XA^FO50,50^FDHello World^FS^XZ"
  }'`;
        } else {
            printCmd.textContent = `# Replace PRINTER_ID with your actual printer ID
curl -X POST ${baseUrl}/api/pis/PRINTER_ID/print \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_raw": "^XA^FO50,50^FDHello World^FS^XZ"
  }'`;
        }
    }
    
    // Print from URL command
    const printUrlCmd = document.getElementById('curl-print-url');
    if (printUrlCmd) {
        if (availablePrinters.length > 0) {
            printUrlCmd.textContent = `# Print from URL to "${printerName}"
curl -X POST ${baseUrl}/api/pis/${printerId}/print \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_url": "https://example.com/label.zpl"
  }'`;
        } else {
            printUrlCmd.textContent = `# Replace PRINTER_ID with your actual printer ID
curl -X POST ${baseUrl}/api/pis/PRINTER_ID/print \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "zpl_url": "https://example.com/label.zpl"
  }'`;
        }
    }
    
    // Print file command
    const printFileCmd = document.getElementById('curl-print-file');
    if (printFileCmd) {
        if (availablePrinters.length > 0) {
            printFileCmd.textContent = `# Upload ZPL file to "${printerName}"
curl -X POST ${baseUrl}/api/pis/${printerId}/print \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "zpl_file=@/path/to/label.zpl"`;
        } else {
            printFileCmd.textContent = `# Replace PRINTER_ID with your actual printer ID
curl -X POST ${baseUrl}/api/pis/PRINTER_ID/print \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "zpl_file=@/path/to/label.zpl"`;
        }
    }
    
    // Label sizes command
    const sizesCmd = document.getElementById('curl-label-sizes');
    if (sizesCmd) {
        sizesCmd.textContent = `curl -X GET ${baseUrl}/api/label-sizes`;
    }
}

// Update all printer select dropdowns
function updatePrinterSelects() {
    const selects = document.querySelectorAll('.printer-select');
    
    selects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '';
        
        if (availablePrinters.length === 0) {
            select.innerHTML = '<option value="">No printers available</option>';
        } else {
            select.innerHTML = '<option value="">Select a printer...</option>';
            availablePrinters.forEach(printer => {
                const status = printer.websocket_connected ? '🟢' : '🔴';
                const option = document.createElement('option');
                option.value = printer.id;
                option.textContent = `${status} ${printer.friendly_name}`;
                select.appendChild(option);
            });
            
            // Restore previous selection if available
            if (currentValue) select.value = currentValue;
        }
    });
}

// Update all API key select dropdowns
function updateApiKeySelects() {
    const selects = document.querySelectorAll('.api-key-select');
    
    selects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '';
        
        if (userApiKeys.length === 0) {
            select.innerHTML = '<option value="">No API keys available</option>';
        } else {
            select.innerHTML = '<option value="">Select an API key...</option>';
            userApiKeys.forEach(key => {
                const option = document.createElement('option');
                option.value = key.key;
                option.textContent = key.name;
                select.appendChild(option);
            });
            
            // Restore previous selection if available
            if (currentValue) select.value = currentValue;
        }
    });
}

// Load user's API keys
async function loadUserApiKeys() {
    try {
        const response = await fetch('/api/keys');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                userApiKeys = data.data.keys.filter(key => key.is_active);
                displayUserApiKeys();
            }
        }
    } catch (error) {
        // User might not be logged in, that's okay
        console.log('Could not load API keys (user might not be logged in)');
    }
}

// Display user's API keys in Getting Started section
function displayUserApiKeys() {
    const display = document.getElementById('user-api-key-display');
    if (!display) return;
    
    if (userApiKeys.length > 0) {
        const key = userApiKeys[0];
        display.innerHTML = `
            <div class="info-box">
                <i data-lucide="key"></i>
                <div>
                    <strong>Your API Key:</strong> <code>${key.name}</code>
                    <br>
                    <small>Use this key in the Authorization header</small>
                </div>
            </div>
        `;
        lucide.createIcons();
    } else {
        display.innerHTML = `
            <div class="info-box warning">
                <i data-lucide="alert-triangle"></i>
                <div>
                    No API keys found. <a href="/settings#api-keys">Create one now →</a>
                </div>
            </div>
        `;
        lucide.createIcons();
    }
}

// Use an API key in the test form
function useApiKey(keyId) {
    showAlert('Note: For security, you need to enter the full API key manually', 'info');
    document.getElementById('test-api-key').focus();
}

// Try List Printers endpoint
async function tryListPrinters() {
    const responseDiv = document.getElementById('list-response');
    responseDiv.innerHTML = '<pre>Loading...</pre>';
    responseDiv.className = 'response-display show';
    
    try {
        const response = await fetch('/api/pis');
        const data = await response.json();
        
        responseDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        responseDiv.className = 'response-display show success';
    } catch (error) {
        responseDiv.innerHTML = `<pre>Error: ${error.message}</pre>`;
        responseDiv.className = 'response-display show error';
    }
}

// Try Label Sizes endpoint
async function tryLabelSizes() {
    const responseDiv = document.getElementById('sizes-response');
    responseDiv.innerHTML = '<pre>Loading...</pre>';
    responseDiv.className = 'response-display show';
    
    try {
        const response = await fetch('/api/label-sizes');
        const data = await response.json();
        
        responseDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        responseDiv.className = 'response-display show success';
    } catch (error) {
        responseDiv.innerHTML = `<pre>Error: ${error.message}</pre>`;
        responseDiv.className = 'response-display show error';
    }
}

// Send test print
async function testPrint() {
    const printerId = document.getElementById('test-printer-select').value;
    const apiKey = document.getElementById('test-api-key').value;
    const zpl = document.getElementById('test-zpl').value;
    const responseDiv = document.getElementById('print-response');
    
    if (!printerId) {
        showAlert('Please select a printer', 'error');
        return;
    }
    
    if (!apiKey) {
        showAlert('Please enter an API key', 'error');
        return;
    }
    
    if (!zpl) {
        showAlert('Please enter ZPL code', 'error');
        return;
    }
    
    responseDiv.innerHTML = '<pre>Sending print job...</pre>';
    responseDiv.className = 'response-display show';
    
    try {
        const response = await fetch(`/api/pis/${printerId}/print`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ zpl_raw: zpl })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            responseDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            responseDiv.className = 'response-display show success';
            showAlert('Print job sent successfully!', 'success');
        } else {
            responseDiv.innerHTML = `<pre>Error ${response.status}:\n${JSON.stringify(data, null, 2)}</pre>`;
            responseDiv.className = 'response-display show error';
            showAlert(data.detail || 'Print failed', 'error');
        }
    } catch (error) {
        responseDiv.innerHTML = `<pre>Error: ${error.message}</pre>`;
        responseDiv.className = 'response-display show error';
        showAlert('Failed to send print job', 'error');
    }
}

// Show alert toast
function showAlert(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'alert-circle' : 'info';
    
    toast.innerHTML = `
        <i data-lucide="${icon}"></i>
        <span>${message}</span>
    `;
    
    const container = document.getElementById('toast-container');
    container.appendChild(toast);
    
    // Re-initialize Lucide icons for the new toast
    lucide.createIcons({
        attrs: {
            width: 20,
            height: 20
        }
    });
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Update active section based on scroll position
function updateActiveSection() {
    // Don't update if we're in the middle of programmatic scrolling
    if (isScrolling) return;
    
    const sections = document.querySelectorAll('.doc-section');
    const navItems = document.querySelectorAll('.nav-item');
    
    // Get header height for consistent offset
    const header = document.querySelector('.docs-header');
    const headerHeight = header ? header.offsetHeight : 0;
    const offset = headerHeight + 20; // Same as scrollToSection
    
    // Get current scroll position
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;
    const viewportTop = scrollY + offset;
    
    // Find which section is currently in view
    let currentSection = null;
    let minDistance = Infinity;
    
    // Check each section to find the one closest to our viewport top
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        const sectionBottom = sectionTop + sectionHeight;
        
        // Calculate distance from viewport top to section top
        const distance = Math.abs(sectionTop - viewportTop);
        
        // Check if this section is in view and closer to viewport top
        if (viewportTop >= sectionTop - 10 && viewportTop < sectionBottom) {
            if (distance < minDistance) {
                minDistance = distance;
                currentSection = section.getAttribute('id');
            }
        }
    });
    
    // Special case: if we're near the bottom, highlight the last section
    if ((window.innerHeight + scrollY) >= document.body.offsetHeight - 50) {
        const lastSection = sections[sections.length - 1];
        if (lastSection) {
            currentSection = lastSection.getAttribute('id');
        }
    }
    
    // Special case: if we're at the very top, highlight the first section
    if (scrollY < 10) {
        currentSection = 'getting-started';
    }
    
    // Update active state in navigation
    if (currentSection) {
        navItems.forEach(item => {
            item.classList.remove('active');
            const href = item.getAttribute('href');
            if (href === '#' + currentSection) {
                item.classList.add('active');
            }
        });
    }
}

// Search endpoints functionality
function searchEndpoints(query) {
    const sections = document.querySelectorAll('.doc-section');
    const navItems = document.querySelectorAll('.nav-item');
    
    if (!query) {
        // Show all sections and nav items
        sections.forEach(section => section.style.display = '');
        navItems.forEach(item => item.style.display = '');
        return;
    }
    
    const lowerQuery = query.toLowerCase();
    
    // Filter sections
    sections.forEach(section => {
        const text = section.textContent.toLowerCase();
        if (text.includes(lowerQuery)) {
            section.style.display = '';
        } else {
            section.style.display = 'none';
        }
    });
    
    // Filter nav items
    navItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(lowerQuery)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// Switch code tab
function switchCodeTab(button, tabName) {
    const container = button.closest('.code-tabs');
    
    // Update buttons
    container.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');
    
    // Update content
    container.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    
    const targetTab = container.querySelector(`#tab-${tabName}`);
    if (targetTab) {
        targetTab.style.display = 'block';
    }
}

// Switch example tab
function switchExampleTab(button, tabId) {
    const container = button.closest('.code-tabs');
    
    // Update buttons
    container.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');
    
    // Update content
    container.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    
    const targetTab = container.querySelector(`#${tabId}`);
    if (targetTab) {
        targetTab.style.display = 'block';
    }
}

// Try endpoint functions
async function tryEndpoint(endpointId) {
    const detailsDiv = document.getElementById(`${endpointId}-details`);
    const responseDiv = document.getElementById(`${endpointId}-response`);
    
    if (detailsDiv) {
        detailsDiv.style.display = detailsDiv.style.display === 'none' ? 'block' : 'none';
    }
    
    if (responseDiv && detailsDiv.style.display === 'block') {
        responseDiv.textContent = 'Sending request...';
        
        try {
            let response;
            
            switch(endpointId) {
                case 'list-printers':
                    response = await fetch('/api/pis');
                    break;
                case 'label-sizes':
                    response = await fetch('/api/label-sizes');
                    break;
                case 'view-queue':
                    // Note: /api/queue endpoint doesn't exist yet, this is a placeholder
                    response = await fetch('/api/pis', {
                        credentials: 'same-origin'
                    });
                    break;
                default:
                    throw new Error('Unknown endpoint');
            }
            
            const data = await response.json();
            responseDiv.textContent = JSON.stringify(data, null, 2);
        } catch (error) {
            responseDiv.textContent = `Error: ${error.message}`;
        }
    }
}

// Show interactive form
function showInteractiveForm(formId) {
    const form = document.getElementById(`${formId}-form`);
    if (form) {
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    }
}

// Try printer details
async function tryPrinterDetails() {
    const printerId = document.getElementById('printer-details-id').value;
    const responseDiv = document.getElementById('printer-details-response');
    
    if (!printerId) {
        responseDiv.textContent = 'Please select a printer';
        return;
    }
    
    responseDiv.textContent = 'Sending request...';
    
    try {
        const response = await fetch(`/api/pis/${printerId}`);
        const data = await response.json();
        responseDiv.textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        responseDiv.textContent = `Error: ${error.message}`;
    }
}

// Show print form
function showPrintForm() {
    const form = document.getElementById('print-form');
    if (form) {
        form.style.display = form.style.display === 'none' ? 'block' : 'none';
    }
}

// Toggle print method
function togglePrintMethod() {
    const method = document.querySelector('input[name="print-method"]:checked').value;
    
    document.getElementById('zpl-raw-group').style.display = method === 'raw' ? 'block' : 'none';
    document.getElementById('zpl-url-group').style.display = method === 'url' ? 'block' : 'none';
}

// Send print job
async function sendPrintJob() {
    const printerId = document.getElementById('print-printer-id').value;
    const apiKey = document.getElementById('print-api-key').value;
    const priority = document.getElementById('print-priority').value;
    const method = document.querySelector('input[name="print-method"]:checked').value;
    const responseDiv = document.getElementById('print-response');
    
    if (!printerId) {
        alert('Please select a printer');
        return;
    }
    
    // Note: API key field is shown for documentation purposes, but we use session auth for testing
    
    let body = { priority: parseInt(priority) };
    
    if (method === 'raw') {
        const zpl = document.getElementById('print-zpl-raw').value;
        if (!zpl) {
            alert('Please enter ZPL content');
            return;
        }
        body.zpl_raw = zpl;
    } else {
        const url = document.getElementById('print-zpl-url').value;
        if (!url) {
            alert('Please enter a ZPL URL');
            return;
        }
        body.zpl_url = url;
    }
    
    responseDiv.textContent = 'Sending print job...';
    
    try {
        // Use test-print endpoint which uses session authentication
        const response = await fetch(`/api/pis/${printerId}/test-print`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',  // Include session cookies
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        responseDiv.textContent = JSON.stringify(data, null, 2);
        
        if (response.ok) {
            alert('Print job sent successfully!');
        }
    } catch (error) {
        responseDiv.textContent = `Error: ${error.message}`;
    }
}

// Try list printers
async function tryListPrinters() {
    await tryEndpoint('list-printers');
}

// Show print example
function showPrintExample() {
    const exampleSection = document.getElementById('sending-prints');
    if (exampleSection) {
        scrollToSection('sending-prints', null);
        showPrintForm();
    }
}

// Update dynamic content
function updateDynamicContent() {
    // This is called after data loads to update any dynamic placeholders
    const baseUrl = window.labelberryBaseUrl || window.location.origin;
    
    // Update all placeholders
    document.querySelectorAll('.dynamic-content').forEach(el => {
        const type = el.dataset.content;
        
        switch(type) {
            case 'base-url':
                el.textContent = baseUrl;
                break;
            case 'printer-count':
                el.textContent = availablePrinters.length;
                break;
            case 'api-key-count':
                el.textContent = userApiKeys.length;
                break;
        }
    });
}

// Setup scroll spy
function setupScrollSpy() {
    let scrollTimeout;
    
    window.addEventListener('scroll', () => {
        if (isScrolling) return;
        
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            updateActiveSection();
        }, 10);
    });
    
    // Initial update
    updateActiveSection();
}