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
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                <i data-lucide="key" style="width: 48px; height: 48px; margin-bottom: 16px;"></i>
                <p>No API keys created yet</p>
                <p style="font-size: 13px;">Create your first API key to enable programmatic access</p>
            </div>
        `;
    } else {
        container.innerHTML = keys.map(key => `
            <div class="api-key-item">
                <div class="api-key-header">
                    <span class="api-key-name">${key.name}</span>
                    <span class="api-key-status ${key.is_active ? 'active' : 'revoked'}">
                        ${key.is_active ? 'Active' : 'Revoked'}
                    </span>
                </div>
                ${key.description ? `<p style="margin: 0 0 12px 0; color: var(--text-secondary); font-size: 13px;">${key.description}</p>` : ''}
                <div class="api-key-details">
                    <div class="api-key-detail">
                        <span class="api-key-detail-label">Created:</span>
                        <span class="api-key-detail-value">${formatDate(key.created_at)}</span>
                    </div>
                    <div class="api-key-detail">
                        <span class="api-key-detail-label">Created by:</span>
                        <span class="api-key-detail-value">${key.created_by}</span>
                    </div>
                    <div class="api-key-detail">
                        <span class="api-key-detail-label">Last used:</span>
                        <span class="api-key-detail-value">${key.last_used ? formatDate(key.last_used) : 'Never'}</span>
                    </div>
                    <div class="api-key-detail">
                        <span class="api-key-detail-label">Permissions:</span>
                        <span class="api-key-detail-value">${key.permissions || 'Print'}</span>
                    </div>
                </div>
                <div class="api-key-actions">
                    ${key.is_active ? `
                        <button class="btn btn-secondary" onclick="revokeApiKey(${key.id})">
                            <i data-lucide="ban"></i> Revoke
                        </button>
                    ` : ''}
                    <button class="btn btn-danger" onclick="deleteApiKey(${key.id})">
                        <i data-lucide="trash-2"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    // Re-initialize Lucide icons
    lucide.createIcons();
}

function showCreateKeyModal() {
    document.getElementById('create-key-modal').style.display = 'block';
}

function closeCreateKeyModal() {
    document.getElementById('create-key-modal').style.display = 'none';
    document.getElementById('create-key-form').reset();
}

function closeKeyDisplayModal() {
    document.getElementById('key-display-modal').style.display = 'none';
}

async function createApiKey(event) {
    event.preventDefault();
    
    const name = document.getElementById('key-name').value;
    const description = document.getElementById('key-description').value;
    
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
            document.getElementById('key-example').textContent = data.data.api_key;
            document.getElementById('key-display-modal').style.display = 'block';
            
            // Reload the keys list
            loadApiKeys();
        } else {
            showAlert(data.message || 'Failed to create API key', 'error');
        }
    } catch (error) {
        console.error('Error creating API key:', error);
        showAlert('Failed to create API key', 'error');
    }
}

async function revokeApiKey(keyId) {
    if (!confirm('Are you sure you want to revoke this API key? Applications using this key will lose access.')) {
        return;
    }
    
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
        }
    } catch (error) {
        console.error('Error revoking API key:', error);
        showAlert('Failed to revoke API key', 'error');
    }
}

async function deleteApiKey(keyId) {
    if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
        return;
    }
    
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
        }
    } catch (error) {
        console.error('Error deleting API key:', error);
        showAlert('Failed to delete API key', 'error');
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
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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