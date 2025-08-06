// API Documentation JavaScript

let availablePrinters = [];
let userApiKeys = [];

// Scroll to section
function scrollToSection(sectionId, navItem) {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    navItem.classList.add('active');
    
    // Scroll to section
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Copy code to clipboard
async function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    const code = codeBlock.querySelector('code').textContent;
    
    try {
        await navigator.clipboard.writeText(code);
        
        // Show feedback
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i data-lucide="check" style="width: 16px; height: 16px;"></i>';
        button.style.color = '#12b886';
        lucide.createIcons();
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.color = '';
            lucide.createIcons();
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
            updatePrinterSelect();
        }
    } catch (error) {
        console.error('Failed to load printers:', error);
    }
}

// Update printer select dropdown
function updatePrinterSelect() {
    const select = document.getElementById('test-printer-select');
    if (!select) return;
    
    if (availablePrinters.length === 0) {
        select.innerHTML = '<option value="">No printers available</option>';
    } else {
        select.innerHTML = '<option value="">Select a printer...</option>';
        availablePrinters.forEach(printer => {
            const status = printer.websocket_connected ? '🟢' : '🔴';
            const labelSize = printer.label_size ? ` - ${printer.label_size.display_name}` : '';
            select.innerHTML += `<option value="${printer.id}">${status} ${printer.friendly_name}${labelSize}</option>`;
        });
    }
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

// Display user's API keys
function displayUserApiKeys() {
    const container = document.getElementById('user-api-keys');
    const list = document.getElementById('api-keys-list');
    
    if (!container || !list) return;
    
    if (userApiKeys.length > 0) {
        container.style.display = 'block';
        list.innerHTML = userApiKeys.map(key => `
            <div class="api-key-item">
                <span>${key.name}</span>
                <button class="btn btn-sm" onclick="useApiKey('${key.id}')">Use This Key</button>
            </div>
        `).join('');
        
        // Auto-fill the first API key in test form
        const testKeyInput = document.getElementById('test-api-key');
        if (testKeyInput && testKeyInput.value === '') {
            testKeyInput.placeholder = 'Click "Use This Key" above or enter manually';
        }
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
    lucide.createIcons();
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Highlight code syntax (basic)
    document.querySelectorAll('.code-block code').forEach(block => {
        // Basic syntax highlighting for JSON
        if (block.textContent.includes('"success"')) {
            block.innerHTML = block.innerHTML
                .replace(/"([^"]+)":/g, '<span style="color: #9cdcfe;">"$1"</span>:')
                .replace(/: "([^"]+)"/g, ': <span style="color: #ce9178;">"$1"</span>')
                .replace(/: (\d+)/g, ': <span style="color: #b5cea8;">$1</span>')
                .replace(/: (true|false)/g, ': <span style="color: #569cd6;">$1</span>');
        }
    });
    
    // Set up smooth scrolling for navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
        });
    });
});