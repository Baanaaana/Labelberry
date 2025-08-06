// Settings page JavaScript

// Load preferences from localStorage
function loadPreferences() {
    const settings = JSON.parse(localStorage.getItem('labelberrySettings') || '{}');
    
    // Apply saved settings to form fields
    if (settings.timezone) {
        document.getElementById('timezone-select').value = settings.timezone;
    }
    if (settings.refreshInterval) {
        document.getElementById('refresh-interval').value = settings.refreshInterval;
    }
    if (settings.dateFormat) {
        document.getElementById('date-format').value = settings.dateFormat;
    }
}

// Switch between sections
function switchSection(sectionName, navItem) {
    // Hide all sections
    document.querySelectorAll('.settings-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Show selected section
    document.getElementById(`${sectionName}-section`).classList.add('active');
    
    // Add active class to clicked nav item
    navItem.classList.add('active');
    
    // Update URL hash without scrolling
    history.replaceState(null, null, `#${sectionName}`);
}

// Handle username change
async function changeUsername(event) {
    event.preventDefault();
    
    const newUsername = document.getElementById('new-username').value.trim();
    const password = document.getElementById('username-password').value;
    
    if (!newUsername) {
        showAlert('Please enter a new username', 'error');
        return;
    }
    
    if (newUsername.length < 3) {
        showAlert('Username must be at least 3 characters', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/change-username', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                new_username: newUsername,
                current_password: password
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Username changed successfully!', 'success');
            document.getElementById('username-form').reset();
        } else {
            showAlert(data.message || 'Failed to change username', 'error');
        }
    } catch (error) {
        console.error('Error changing username:', error);
        showAlert('Failed to change username', 'error');
    }
}

// Handle password change
async function changePassword(event) {
    event.preventDefault();
    
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    if (newPassword.length < 6) {
        showAlert('New password must be at least 6 characters', 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showAlert('New passwords do not match', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Password changed successfully!', 'success');
            document.getElementById('password-form').reset();
        } else {
            showAlert(data.message || 'Failed to change password', 'error');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showAlert('Failed to change password', 'error');
    }
}

// Save preferences
async function savePreferences(event) {
    event.preventDefault();
    
    const settings = {
        timezone: document.getElementById('timezone-select').value,
        refreshInterval: parseInt(document.getElementById('refresh-interval').value),
        dateFormat: document.getElementById('date-format').value
    };
    
    // Save to localStorage
    localStorage.setItem('labelberrySettings', JSON.stringify(settings));
    
    showAlert('Preferences saved successfully!', 'success');
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

// API Key Management Functions
async function loadApiKeys() {
    try {
        const response = await fetch('/api/keys');
        const data = await response.json();
        
        if (data.success) {
            displayApiKeys(data.data.keys);
        }
    } catch (error) {
        console.error('Error loading API keys:', error);
    }
}

function displayApiKeys(keys) {
    const container = document.getElementById('api-keys-list');
    
    if (keys.length === 0) {
        container.innerHTML = `
            <div class="api-keys-empty">
                <i data-lucide="key-round"></i>
                <h3>No API Keys Yet</h3>
                <p>Create your first API key to enable secure programmatic access to the LabelBerry printing API</p>
                <button class="btn btn-primary" onclick="showCreateKeyModal()">
                    <i data-lucide="plus-circle"></i>
                    Create Your First Key
                </button>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="api-keys-grid">
                ${keys.map(key => `
                    <div class="api-key-item">
                        <div class="api-key-header">
                            <div class="api-key-info">
                                <div class="api-key-name">
                                    <i data-lucide="key"></i>
                                    ${escapeHtml(key.name)}
                                </div>
                                ${key.description ? `<p class="api-key-description">${escapeHtml(key.description)}</p>` : '<p class="api-key-description">No description provided</p>'}
                            </div>
                            <span class="api-key-status ${key.is_active ? 'active' : 'revoked'}">
                                ${key.is_active ? '<i data-lucide="check-circle" style="width: 14px; height: 14px;"></i> Active' : '<i data-lucide="x-circle" style="width: 14px; height: 14px;"></i> Revoked'}
                            </span>
                        </div>
                        <div class="api-key-details">
                            <div class="api-key-detail">
                                <span class="api-key-detail-label">Created</span>
                                <span class="api-key-detail-value">
                                    <i data-lucide="calendar"></i>
                                    ${formatDate(key.created_at)}
                                </span>
                            </div>
                            <div class="api-key-detail">
                                <span class="api-key-detail-label">Created By</span>
                                <span class="api-key-detail-value">
                                    <i data-lucide="user"></i>
                                    ${escapeHtml(key.created_by)}
                                </span>
                            </div>
                            <div class="api-key-detail">
                                <span class="api-key-detail-label">Last Used</span>
                                <span class="api-key-detail-value">
                                    <i data-lucide="activity"></i>
                                    ${key.last_used ? formatDate(key.last_used) : '<span style="color: var(--text-secondary);">Never used</span>'}
                                </span>
                            </div>
                            <div class="api-key-detail">
                                <span class="api-key-detail-label">Permissions</span>
                                <span class="api-key-detail-value">
                                    <i data-lucide="shield"></i>
                                    ${key.permissions || 'Print API'}
                                </span>
                            </div>
                        </div>
                        <div class="api-key-actions">
                            ${key.is_active ? `
                                <button class="btn btn-secondary" onclick="revokeApiKey(${key.id})" title="Revoke this API key">
                                    <i data-lucide="ban"></i>
                                    Revoke
                                </button>
                            ` : ''}
                            <button class="btn btn-danger" onclick="deleteApiKey(${key.id})" title="Permanently delete this API key">
                                <i data-lucide="trash-2"></i>
                                Delete
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // Re-initialize Lucide icons
    lucide.createIcons();
}

// Helper function to escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showCreateKeyModal() {
    document.getElementById('create-key-modal').style.display = 'block';
}

function closeCreateKeyModal() {
    const modal = document.getElementById('create-key-modal');
    const form = document.getElementById('create-key-form');
    const submitButton = form.querySelector('button[type="submit"]');
    const cancelButton = form.querySelector('button[type="button"]');
    
    // Reset form
    form.reset();
    
    // Re-enable buttons and restore original text if needed
    submitButton.disabled = false;
    cancelButton.disabled = false;
    submitButton.innerHTML = 'Create Key';
    
    // Hide modal
    modal.style.display = 'none';
}

function closeKeyDisplayModal() {
    document.getElementById('key-display-modal').style.display = 'none';
}

async function createApiKey(event) {
    event.preventDefault();
    
    const name = document.getElementById('key-name').value;
    const description = document.getElementById('key-description').value;
    const submitButton = event.target.querySelector('button[type="submit"]');
    const cancelButton = event.target.querySelector('button[type="button"]');
    
    // Disable both buttons and show loading state
    submitButton.disabled = true;
    cancelButton.disabled = true;
    const originalButtonText = submitButton.innerHTML;
    submitButton.innerHTML = '<i data-lucide="loader-2" class="spinning"></i> Creating...';
    lucide.createIcons();
    
    try {
        const response = await fetch('/api/keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, description })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Close create modal
            closeCreateKeyModal();
            
            // Show the key display modal
            document.getElementById('api-key-display').value = data.data.api_key;
            
            // Format usage example
            const usageExample = `curl -X POST http://your-server:8080/api/pis/{pi_id}/print \\
  -H "Authorization: Bearer ${data.data.api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{"zpl_raw": "^XA^FO50,50^FDTest^FS^XZ"}'`;
            
            document.getElementById('usage-example-code').textContent = usageExample;
            document.getElementById('key-display-modal').style.display = 'block';
            
            // Reload the keys list
            loadApiKeys();
        } else {
            showAlert(data.message || 'Failed to create API key', 'error');
            // Re-enable buttons on error
            submitButton.disabled = false;
            cancelButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
            lucide.createIcons();
        }
    } catch (error) {
        console.error('Error creating API key:', error);
        showAlert('Failed to create API key', 'error');
        // Re-enable buttons on error
        submitButton.disabled = false;
        cancelButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        lucide.createIcons();
    }
}

async function revokeApiKey(keyId) {
    if (!confirm('Are you sure you want to revoke this API key? Applications using this key will lose access.')) {
        return;
    }
    
    // Disable all action buttons to prevent double-clicks
    const allButtons = document.querySelectorAll('.api-key-actions button');
    allButtons.forEach(btn => btn.disabled = true);
    
    try {
        const response = await fetch(`/api/keys/${keyId}/revoke`, {
            method: 'PUT'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('API key revoked successfully', 'success');
            loadApiKeys();
        } else {
            showAlert(data.message || 'Failed to revoke API key', 'error');
            // Re-enable buttons on error
            allButtons.forEach(btn => btn.disabled = false);
        }
    } catch (error) {
        console.error('Error revoking API key:', error);
        showAlert('Failed to revoke API key', 'error');
        // Re-enable buttons on error
        allButtons.forEach(btn => btn.disabled = false);
    }
}

async function deleteApiKey(keyId) {
    if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
        return;
    }
    
    // Disable all action buttons to prevent double-clicks
    const allButtons = document.querySelectorAll('.api-key-actions button');
    allButtons.forEach(btn => btn.disabled = true);
    
    try {
        const response = await fetch(`/api/keys/${keyId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('API key deleted successfully', 'success');
            loadApiKeys();
        } else {
            showAlert(data.message || 'Failed to delete API key', 'error');
            // Re-enable buttons on error
            allButtons.forEach(btn => btn.disabled = false);
        }
    } catch (error) {
        console.error('Error deleting API key:', error);
        showAlert('Failed to delete API key', 'error');
        // Re-enable buttons on error
        allButtons.forEach(btn => btn.disabled = false);
    }
}

function copyApiKey() {
    const input = document.getElementById('api-key-display');
    input.select();
    document.execCommand('copy');
    
    // Show feedback
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i data-lucide="check"></i> Copied!';
    lucide.createIcons();
    
    setTimeout(() => {
        button.innerHTML = originalHTML;
        lucide.createIcons();
    }, 2000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    // If less than 24 hours ago, show relative time
    if (diffMs < 24 * 60 * 60 * 1000) {
        if (diffMs < 60 * 1000) {
            return 'Just now';
        } else if (diffMs < 60 * 60 * 1000) {
            const minutes = Math.floor(diffMs / (60 * 1000));
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            const hours = Math.floor(diffMs / (60 * 60 * 1000));
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }
    }
    // If less than 7 days ago, show days
    else if (diffDays < 7) {
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }
    // Otherwise show date
    else {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check URL hash for initial section
    const hash = window.location.hash.substring(1);
    if (hash) {
        const navItem = document.querySelector(`.nav-item[href="#${hash}"]`);
        if (navItem) {
            switchSection(hash, navItem);
        }
    }
});