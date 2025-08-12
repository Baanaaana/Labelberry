// Performance Metrics JavaScript

let volumeChart = null;
let successChart = null;
let metricsData = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadPrinterFilter();
    initCharts();
    loadMetrics();
    
    // Set up auto-refresh every 30 seconds
    setInterval(loadMetrics, 30000);
    
    // Add event listeners
    document.getElementById('pi-filter').addEventListener('change', loadMetrics);
    document.getElementById('time-range').addEventListener('change', loadMetrics);
});

async function loadPrinterFilter() {
    try {
        const response = await fetch('/api/pis');
        const result = await response.json();
        
        if (result.success) {
            const select = document.getElementById('pi-filter');
            result.data.pis.forEach(pi => {
                const option = document.createElement('option');
                option.value = pi.id;
                option.textContent = pi.friendly_name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading printers:', error);
    }
}

function initCharts() {
    // Initialize Volume Chart
    const volumeCtx = document.getElementById('volume-chart').getContext('2d');
    volumeChart = new Chart(volumeCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Print Jobs',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: '#3b82f620',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
    
    // Initialize Success Chart
    const successCtx = document.getElementById('success-chart').getContext('2d');
    successChart = new Chart(successCtx, {
        type: 'doughnut',
        data: {
            labels: ['Successful', 'Failed', 'Cancelled'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    '#10b981',
                    '#ef4444',
                    '#6b7280'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

async function loadMetrics() {
    const piId = document.getElementById('pi-filter').value;
    const timeRange = document.getElementById('time-range').value;
    
    try {
        const endpoint = piId ? `/api/metrics/${piId}` : '/api/metrics';
        const response = await fetch(`${endpoint}?range=${timeRange}`);
        const result = await response.json();
        
        if (result.success) {
            metricsData = result.data;
            updateStats(metricsData.stats);
            updateCharts(metricsData);
            updatePrinterTable(metricsData.printers);
            updateErrorLog(metricsData.errors);
        }
    } catch (error) {
        console.error('Error loading metrics:', error);
        // Show placeholder data for now
        showPlaceholderData();
    }
}

function updateStats(stats) {
    if (!stats) {
        stats = {
            total_prints: 0,
            success_rate: 0,
            avg_print_time: 0,
            total_errors: 0
        };
    }
    
    document.getElementById('total-prints').textContent = stats.total_prints || 0;
    document.getElementById('success-rate').textContent = `${(stats.success_rate || 0).toFixed(1)}%`;
    document.getElementById('avg-print-time').textContent = formatDuration(stats.avg_print_time || 0);
    document.getElementById('total-errors').textContent = stats.total_errors || 0;
}

function updateCharts(data) {
    if (!data) return;
    
    // Update volume chart
    if (data.volume_data && volumeChart) {
        volumeChart.data.labels = data.volume_data.labels || [];
        volumeChart.data.datasets[0].data = data.volume_data.values || [];
        volumeChart.update();
    }
    
    // Update success chart
    if (data.success_data && successChart) {
        const successful = data.success_data.successful || 0;
        const failed = data.success_data.failed || 0;
        const cancelled = data.success_data.cancelled || 0;
        
        successChart.data.datasets[0].data = [successful, failed, cancelled];
        successChart.update();
    }
}

function updatePrinterTable(printers) {
    const tbody = document.getElementById('printer-performance-tbody');
    
    if (!printers || printers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                    No printer data available
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = printers.map(printer => {
        const successRate = printer.total_jobs > 0 
            ? ((printer.successful / printer.total_jobs) * 100).toFixed(1)
            : 0;
        
        const statusBadge = printer.is_online 
            ? '<span class="metric-badge success">Online</span>'
            : '<span class="metric-badge danger">Offline</span>';
        
        return `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${statusBadge}
                        <span>${printer.name}</span>
                    </div>
                </td>
                <td>${printer.total_jobs || 0}</td>
                <td>${printer.successful || 0}</td>
                <td>${printer.failed || 0}</td>
                <td>
                    <span class="metric-badge ${successRate >= 90 ? 'success' : successRate >= 70 ? 'warning' : 'danger'}">
                        ${successRate}%
                    </span>
                </td>
                <td>${formatDuration(printer.avg_print_time || 0)}</td>
                <td>${formatUptime(printer.uptime || 0)}</td>
                <td>${formatTime(printer.last_activity)}</td>
            </tr>
        `;
    }).join('');
}

function updateErrorLog(errors) {
    const errorLog = document.getElementById('error-log');
    
    if (!errors || errors.length === 0) {
        errorLog.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                No errors in selected time range
            </div>
        `;
        return;
    }
    
    errorLog.innerHTML = errors.map(error => `
        <div class="error-item">
            <div class="error-icon ${error.level || 'error'}">
                <i data-lucide="${error.level === 'warning' ? 'alert-triangle' : 'x-circle'}"></i>
            </div>
            <div class="error-content">
                <div class="error-title">${error.title || 'Error'}</div>
                <div class="error-message">${error.message}</div>
                <div class="error-meta">
                    <span>${error.printer_name || 'System'}</span>
                    <span>${formatTime(error.timestamp)}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    // Re-initialize icons
    lucide.createIcons();
}

function refreshMetrics() {
    loadMetrics();
}

// Utility functions
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function formatUptime(minutes) {
    if (minutes < 60) return `${minutes}m`;
    if (minutes < 1440) return `${Math.floor(minutes / 60)}h`;
    return `${Math.floor(minutes / 1440)}d`;
}

function formatTime(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
}

// Show placeholder data when API is not available
function showPlaceholderData() {
    // Update stats with zeros
    updateStats({
        total_prints: 0,
        success_rate: 0,
        avg_print_time: 0,
        total_errors: 0
    });
    
    // Update charts with empty data
    if (volumeChart) {
        volumeChart.data.labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        volumeChart.data.datasets[0].data = [0, 0, 0, 0, 0, 0, 0];
        volumeChart.update();
    }
    
    if (successChart) {
        successChart.data.datasets[0].data = [0, 0, 0];
        successChart.update();
    }
    
    // Update tables with no data messages
    updatePrinterTable([]);
    updateErrorLog([]);
}