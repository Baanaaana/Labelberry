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