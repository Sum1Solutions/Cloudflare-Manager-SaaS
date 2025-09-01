// Main application JavaScript for Cloudflare Manager Pages

let domainsTable = null;
let syncProgressInterval = null;
let backgroundSyncMonitor = null;
let syncModal = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadDomains();
    loadDatabaseOverview();
    initializeSyncButton();
});

// Load domains from API
async function loadDomains() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/zones', {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load domains');
        }
        
        displayDomains(data.zones);
        updateLastSyncTime(data.last_sync);
        showLoading(false);
        
    } catch (error) {
        console.error('Error loading domains:', error);
        showError(error.message);
        showLoading(false);
    }
}

// Display domains in DataTable
function displayDomains(zones) {
    const tbody = document.getElementById('domains-tbody');
    
    // Build table rows
    let html = '';
    zones.forEach(zone => {
        html += buildDomainRow(zone);
    });
    
    tbody.innerHTML = html;
    
    // Show table and initialize DataTable
    document.getElementById('domains-container').style.display = 'block';
    initializeDataTable();
}

// Build HTML for a domain row
function buildDomainRow(zone) {
    const statusClass = zone.status === 'active' ? 'success' : 
                       zone.status === 'pending' ? 'warning' : 'secondary';
    
    const requests = zone.analytics_requests ? formatNumber(zone.analytics_requests) : 'N/A';
    const bandwidth = zone.analytics_bandwidth ? formatBandwidth(zone.analytics_bandwidth) : 'N/A';
    const threats = zone.analytics_threats ? formatNumber(zone.analytics_threats) : '0';
    const lastModified = zone.modified_on ? formatDate(zone.modified_on) : 'N/A';
    
    return `
        <tr data-zone-id="${zone.id}">
            <td>
                <div class="d-flex align-items-center">
                    <a href="https://${zone.name}" target="_blank" class="text-decoration-none domain-name">
                        <strong>${zone.name}</strong>
                    </a>
                </div>
            </td>
            <td data-order="${zone.status}">
                <span class="badge bg-${statusClass}">${zone.status}</span>
            </td>
            <td>${zone.plan_name || 'Unknown'}</td>
            <td data-order="${zone.analytics_requests || 0}">${requests}</td>
            <td data-order="${zone.analytics_bandwidth || 0}">${bandwidth}</td>
            <td data-order="${zone.analytics_threats || 0}">${threats}</td>
            <td data-order="${zone.modified_on || '0'}">${lastModified}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <a href="https://dash.cloudflare.com/${zone.account_id}/${zone.name}" 
                       target="_blank" 
                       class="btn btn-outline-primary"
                       title="Open in Cloudflare">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                    <button class="btn btn-outline-info" 
                            onclick="viewZoneDetails('${zone.id}')"
                            title="View Details">
                        <i class="fas fa-info-circle"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

// Initialize DataTable
function initializeDataTable() {
    // Destroy existing table if it exists
    if (domainsTable) {
        domainsTable.destroy();
    }
    
    // Custom sorting for analytics columns
    $.fn.dataTable.ext.type.order['analytics-numeric-pre'] = function(data) {
        if (data === null || data === '' || data === 'N/A' || data === undefined) {
            return 0;
        }
        var numericValue = parseFloat(data.replace(/[^0-9.-]+/g, ''));
        return isNaN(numericValue) ? 0 : numericValue;
    };
    
    domainsTable = $('#domainsTable').DataTable({
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        order: [[6, "desc"]], // Sort by Last Modified
        ordering: true,
        stateSave: true,
        stateDuration: 0,
        searching: true,
        dom: '<"row mb-3"<"col-sm-12 col-md-8"f><"col-sm-12 col-md-4"l>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        columnDefs: [
            { type: "string", targets: [0, 2] },
            { type: "string", targets: 1 },
            { type: "analytics-numeric", targets: [3, 4, 5] },
            { type: "date", targets: 6 },
            { orderable: false, targets: [7] }
        ],
        language: {
            search: "_INPUT_",
            searchPlaceholder: "Search domains...",
            lengthMenu: "Show _MENU_ domains per page",
            zeroRecords: "No matching domains found",
            info: "Showing _START_ to _END_ of _TOTAL_ domains",
            infoEmpty: "No domains available",
            infoFiltered: "(filtered from _MAX_ total domains)"
        },
        responsive: true
    });
}

// Initialize sync button functionality
function initializeSyncButton() {
    const syncBtn = document.getElementById('sync-btn');
    syncBtn.addEventListener('click', startSync);
}

// Start synchronization
async function startSync() {
    try {
        // Show modal
        syncModal = new bootstrap.Modal(document.getElementById('syncProgressModal'));
        syncModal.show();
        
        // Reset progress
        updateSyncProgress(0, 'Initializing sync...', []);
        
        // Start sync
        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error('Sync failed to start');
        }
        
        // Start polling for progress
        startProgressPolling();
        
    } catch (error) {
        console.error('Sync error:', error);
        showToast('Sync failed: ' + error.message, 'danger');
        if (syncModal) {
            syncModal.hide();
        }
    }
}

// Poll for sync progress
function startProgressPolling() {
    if (syncProgressInterval) {
        clearInterval(syncProgressInterval);
    }
    
    syncProgressInterval = setInterval(async function() {
        try {
            const response = await fetch('/api/sync', {
                credentials: 'same-origin'
            });
            const progress = await response.json();
            
            if (progress.syncing) {
                let percentage = 0;
                if (progress.total_zones > 0) {
                    percentage = Math.floor(Math.min(95, (progress.zones_processed / progress.total_zones) * 100));
                }
                
                let details = [];
                if (progress.total_zones > 0) {
                    details.push(`${progress.zones_processed} of ${progress.total_zones} zones processed`);
                }
                if (progress.current_zone) {
                    details.push(`Currently syncing: ${progress.current_zone}`);
                }
                if (progress.elapsed_seconds > 0) {
                    const elapsed = Math.floor(progress.elapsed_seconds);
                    details.push(`Elapsed: ${Math.floor(elapsed / 60)}:${(elapsed % 60).toString().padStart(2, '0')}`);
                }
                
                updateSyncProgress(percentage, progress.current_phase || 'Syncing...', details);
            } else {
                // Sync completed
                clearInterval(syncProgressInterval);
                syncProgressInterval = null;
                
                updateSyncProgress(100, 'Sync completed successfully!', ['✅ All zones and data synchronized']);
                enableSyncCloseButton();
                
                // Show toast if modal is not visible
                if (!document.getElementById('syncProgressModal').classList.contains('show')) {
                    showToast('Synchronization completed successfully!', 'success');
                }
                
                // Reload domains data and database overview
                setTimeout(() => {
                    loadDomains();
                    loadDatabaseOverview();
                }, 1000);
            }
        } catch (error) {
            console.error('Progress polling error:', error);
        }
    }, 1000);
}

// Update sync progress display
function updateSyncProgress(percentage, statusText, details) {
    const progressBar = document.getElementById('sync-progress-bar');
    const progressText = document.getElementById('sync-progress-text');
    const statusElement = document.getElementById('sync-status-text');
    const detailsElement = document.getElementById('sync-details');
    
    progressBar.style.width = percentage + '%';
    progressBar.setAttribute('aria-valuenow', percentage);
    progressText.textContent = Math.floor(percentage) + '%';
    statusElement.textContent = statusText;
    
    if (details && details.length > 0) {
        detailsElement.innerHTML = details.map(detail => 
            `<div class="small text-themed-secondary mb-1">${detail}</div>`
        ).join('');
    }
    
    if (percentage === 100) {
        if (statusText.includes('successfully')) {
            progressBar.className = 'progress-bar bg-success';
        } else if (statusText.includes('failed')) {
            progressBar.className = 'progress-bar bg-danger';
        }
    }
}

// Enable sync close button
function enableSyncCloseButton() {
    const closeBtn = document.getElementById('sync-close-btn');
    closeBtn.style.display = 'inline-block';
    closeBtn.disabled = false;
}

// View zone details
function viewZoneDetails(zoneId) {
    // For now, just log - can be expanded later
    console.log('View details for zone:', zoneId);
    showToast('Zone details view coming soon!', 'info');
}

// Utility functions
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    document.getElementById('error').style.display = 'none';
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('error').style.display = 'block';
    document.getElementById('domains-container').style.display = 'none';
}

function updateLastSyncTime(lastSync) {
    if (lastSync) {
        document.getElementById('last-sync-time').textContent = formatDate(lastSync);
        document.getElementById('last-sync').style.display = 'block';
    }
}

function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function formatBandwidth(bytes) {
    const mb = bytes / (1024 * 1024);
    return mb.toFixed(1) + ' MB';
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch (error) {
        return dateString;
    }
}

function showToast(message, type = 'success') {
    // Create toast dynamically
    const toastContainer = document.querySelector('.toast-container');
    const toastId = 'toast-' + Date.now();
    
    const iconClass = type === 'success' ? 'fa-check-circle text-success' :
                     type === 'danger' ? 'fa-exclamation-triangle text-danger' :
                     type === 'warning' ? 'fa-exclamation-triangle text-warning' :
                     'fa-info-circle text-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert">
            <div class="toast-header">
                <i class="fas ${iconClass} me-2"></i>
                <strong class="me-auto">Notification</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toast = new bootstrap.Toast(document.getElementById(toastId), {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove toast element after it's hidden
    document.getElementById(toastId).addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Load database overview for compact display
async function loadDatabaseOverview() {
    try {
        const response = await fetch('/api/database', {
            credentials: 'same-origin'
        });
        const data = await response.json();
        
        if (!data.success) {
            console.warn('Failed to load database overview:', data.error);
            return;
        }
        
        displayCompactDatabaseOverview(data.db_overview);
        
    } catch (error) {
        console.error('Error loading database overview:', error);
    }
}

// Display compact database overview
function displayCompactDatabaseOverview(overview) {
    if (!overview) return;
    
    const container = document.getElementById('db-overview');
    
    // Build compact stats cards
    const html = `
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="card h-100 border-0 shadow-sm">
                <div class="card-body text-center p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <i class="fas fa-globe text-primary me-2"></i>
                        <h6 class="mb-0 text-muted">Total Zones</h6>
                    </div>
                    <h3 class="mb-0 text-primary">${overview.zone_stats?.by_status?.active || 0}</h3>
                    <small class="text-muted">Active domains</small>
                </div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="card h-100 border-0 shadow-sm">
                <div class="card-body text-center p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <i class="fas fa-chart-line text-success me-2"></i>
                        <h6 class="mb-0 text-muted">Avg Requests</h6>
                    </div>
                    <h3 class="mb-0 text-success">${formatNumber(Math.round(overview.zone_stats?.avg_analytics?.requests || 0))}</h3>
                    <small class="text-muted">per domain (30d)</small>
                </div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="card h-100 border-0 shadow-sm">
                <div class="card-body text-center p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <i class="fas fa-cloud text-info me-2"></i>
                        <h6 class="mb-0 text-muted">Avg Bandwidth</h6>
                    </div>
                    <h3 class="mb-0 text-info">${formatBandwidth(overview.zone_stats?.avg_analytics?.bandwidth || 0)}</h3>
                    <small class="text-muted">per domain (30d)</small>
                </div>
            </div>
        </div>
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="card h-100 border-0 shadow-sm">
                <div class="card-body text-center p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <i class="fas fa-shield-alt text-warning me-2"></i>
                        <h6 class="mb-0 text-muted">Threats Blocked</h6>
                    </div>
                    <h3 class="mb-0 text-warning">${formatNumber(Math.round(overview.zone_stats?.avg_analytics?.threats || 0))}</h3>
                    <small class="text-muted">avg per domain (30d)</small>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    container.style.display = 'flex';
}