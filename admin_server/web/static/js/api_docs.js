// API Documentation JavaScript

let availablePrinters = [];
let userApiKeys = [];

// Flag to prevent scroll spy during programmatic scrolling
let isScrolling = false;

// Scroll to section
function scrollToSection(sectionId, navItem) {
    // Set flag to prevent scroll spy interference
    isScrolling = true;
    
    // Update active nav item immediately
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    navItem.classList.add('active');
    
    // Find the section
    const section = document.getElementById(sectionId);
    if (!section) {
        console.error('Section not found:', sectionId);
        isScrolling = false;
        return;
    }
    
    // Get the sidebar nav element for alignment reference
    const sidebarNav = document.querySelector('.docs-nav');
    if (!sidebarNav) {
        // Fallback to simple scroll if sidebar not found
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setTimeout(() => { isScrolling = false; }, 500);
        return;
    }
    
    // Calculate positions
    const sectionRect = section.getBoundingClientRect();
    const sidebarRect = sidebarNav.getBoundingClientRect();
    
    // Current scroll position
    const currentScrollY = window.pageYOffset || document.documentElement.scrollTop;
    
    // Calculate where we need to scroll to
    // We want the section top to align with the sidebar nav top
    const sectionAbsoluteTop = sectionRect.top + currentScrollY;
    const sidebarTop = sidebarRect.top; // This is relative to viewport
    
    // The sidebar is sticky at 24px from top, so when scrolled, it's at 24px
    // We want to scroll so the section is at the same position as the sidebar
    const targetScrollPosition = sectionAbsoluteTop - 24;
    
    // Smooth scroll to target position
    window.scrollTo({
        top: targetScrollPosition,
        behavior: 'smooth'
    });
    
    // Reset flag after scrolling is done
    setTimeout(() => {
        isScrolling = false;
    }, 500);
}

// Copy code to clipboard
async function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    let code = codeBlock.querySelector('code').textContent;
    
    // Replace placeholders with actual values
    const baseUrl = window.location.origin;
    code = code.replace(/http:\/\/your-server:8080/g, baseUrl);
    code = code.replace(/\{pi_id\}/g, availablePrinters.length > 0 ? availablePrinters[0].id : 'YOUR_PRINTER_ID');
    code = code.replace(/labk_your_api_key_here/g, 'YOUR_API_KEY');
    
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
            updateDynamicCommands();
        }
    } catch (error) {
        console.error('Failed to load printers:', error);
    }
}

// Update all dynamic commands with actual values
function updateDynamicCommands() {
    const baseUrl = window.location.origin;
    
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
    const baseUrl = window.location.origin;
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

// Update active section based on scroll position
function updateActiveSection() {
    // Don't update if we're in the middle of programmatic scrolling
    if (isScrolling) return;
    
    const sections = document.querySelectorAll('.doc-section');
    const navItems = document.querySelectorAll('.nav-item');
    
    // Get current scroll position with the same offset as our scroll function (24px)
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;
    const viewportTop = scrollY + 24; // Match the sticky nav position
    
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
        currentSection = 'overview';
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize base URL immediately
    const baseUrl = window.location.origin;
    document.querySelectorAll('.dynamic-url').forEach(el => {
        el.textContent = baseUrl;
    });
    
    // Generate initial commands even before printers load
    generateCurlCommands();
    
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
    
    // Set up scroll spy
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        // Debounce scroll events for better performance
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            updateActiveSection();
        }, 10);
    });
    
    // Update on initial load
    updateActiveSection();
    
    // Load printers and API keys
    loadPrinters();
    loadUserApiKeys();
});