// Database overview JavaScript for Cloudflare Manager Pages

// Initialize the database overview
document.addEventListener('DOMContentLoaded', function() {
    loadDatabaseOverview();
    initializeViewToggle();
});

// Initialize view toggle functionality
function initializeViewToggle() {
    document.getElementById('table-view-btn').addEventListener('click', function() {
        showTableView();
    });
    
    document.getElementById('schema-view-btn').addEventListener('click', function() {
        showSchemaView();
    });
}

// Show table view
function showTableView() {
    document.getElementById('table-view').style.display = 'block';
    document.getElementById('schema-view').style.display = 'none';
    document.getElementById('table-view-btn').classList.add('active');
    document.getElementById('schema-view-btn').classList.remove('active');
}

// Show schema view
function showSchemaView() {
    document.getElementById('table-view').style.display = 'none';
    document.getElementById('schema-view').style.display = 'block';
    document.getElementById('table-view-btn').classList.remove('active');
    document.getElementById('schema-view-btn').classList.add('active');
}

// Load database overview from API
async function loadDatabaseOverview() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/database');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to load database overview');
        }
        
        displayDatabaseOverview(data);
        showLoading(false);
        
    } catch (error) {
        console.error('Error loading database overview:', error);
        showError(error.message);
        showLoading(false);
    }
}

// Display database overview
function displayDatabaseOverview(data) {
    const { tables, tables_metadata, db_overview } = data;
    
    // Display summary cards
    displaySummaryCards(db_overview);
    
    // Display zone statistics
    if (db_overview.zone_stats) {
        displayZoneStatistics(db_overview.zone_stats);
    }
    
    // Display analytics statistics
    if (db_overview.zone_stats) {
        displayAnalyticsStatistics(db_overview.zone_stats);
    }
    
    // Display DNS statistics
    if (db_overview.dns_stats) {
        displayDnsStatistics(db_overview.dns_stats);
    }
    
    // Display tables information
    displayTablesInformation(tables, tables_metadata);
    
    // Display schema information
    displaySchemaInformation(tables);
    
    // Show content
    document.getElementById('database-content').style.display = 'block';
}

// Display summary cards
function displaySummaryCards(dbOverview) {
    const container = document.getElementById('summary-cards');
    
    const html = `
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <i class="fas fa-database fa-2x text-primary mb-2"></i>
                    <h5 class="card-title">Database Size</h5>
                    <h3 class="text-primary">${dbOverview.db_size_mb} MB</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <i class="fas fa-table fa-2x text-success mb-2"></i>
                    <h5 class="card-title">Total Tables</h5>
                    <h3 class="text-success">${dbOverview.total_tables}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <i class="fas fa-list fa-2x text-info mb-2"></i>
                    <h5 class="card-title">Total Records</h5>
                    <h3 class="text-info">${formatNumber(dbOverview.total_rows)}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <i class="fas fa-globe fa-2x text-warning mb-2"></i>
                    <h5 class="card-title">Active Zones</h5>
                    <h3 class="text-warning">${dbOverview.zone_stats?.by_status?.active || 0}</h3>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Display zone statistics
function displayZoneStatistics(zoneStats) {
    const container = document.getElementById('zone-stats');
    
    let statusHtml = '';
    for (const [status, count] of Object.entries(zoneStats.by_status || {})) {
        const badgeClass = status === 'active' ? 'success' : 
                          status === 'pending' ? 'warning' : 'secondary';
        statusHtml += `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge bg-${badgeClass} me-2">${status.charAt(0).toUpperCase() + status.slice(1)}</span>
                <span class="fw-bold">${formatNumber(count)}</span>
            </div>
        `;
    }
    
    let planHtml = '';
    for (const [plan, count] of Object.entries(zoneStats.by_plan || {})) {
        planHtml += `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>${plan}</span>
                <span class="fw-bold">${formatNumber(count)}</span>
            </div>
        `;
    }
    
    const html = `
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-chart-pie me-2"></i>Zone Status Distribution</h5>
                </div>
                <div class="card-body">
                    ${statusHtml}
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-layer-group me-2"></i>Plan Distribution</h5>
                </div>
                <div class="card-body">
                    ${planHtml}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    container.style.display = 'flex';
}

// Display analytics statistics
function displayAnalyticsStatistics(zoneStats) {
    const container = document.getElementById('analytics-stats');
    
    const html = `
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-chart-line me-2"></i>Analytics Overview (Last 30 Days)</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="text-center">
                                <h6 class="text-muted">Zones with Analytics</h6>
                                <h4 class="text-primary">${formatNumber(zoneStats.with_analytics || 0)}</h4>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h6 class="text-muted">Avg. Requests</h6>
                                <h4 class="text-success">${formatNumber(Math.round(zoneStats.avg_analytics?.requests || 0))}</h4>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h6 class="text-muted">Avg. Bandwidth</h6>
                                <h4 class="text-info">${formatBandwidth(zoneStats.avg_analytics?.bandwidth || 0)}</h4>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="text-center">
                                <h6 class="text-muted">Avg. Threats</h6>
                                <h4 class="text-danger">${formatNumber(Math.round(zoneStats.avg_analytics?.threats || 0))}</h4>
                            </div>
                        </div>
                    </div>
                    <hr>
                    <div class="row">
                        <div class="col-md-4">
                            <div class="text-center">
                                <h6 class="text-muted">Peak Requests</h6>
                                <h5 class="text-success">${formatNumber(zoneStats.max_analytics?.requests || 0)}</h5>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="text-center">
                                <h6 class="text-muted">Peak Bandwidth</h6>
                                <h5 class="text-info">${formatBandwidth(zoneStats.max_analytics?.bandwidth || 0)}</h5>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="text-center">
                                <h6 class="text-muted">Peak Threats</h6>
                                <h5 class="text-danger">${formatNumber(zoneStats.max_analytics?.threats || 0)}</h5>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    container.style.display = 'flex';
}

// Display DNS statistics
function displayDnsStatistics(dnsStats) {
    const container = document.getElementById('dns-stats');
    
    let recordTypesHtml = '';
    for (const [type, count] of Object.entries(dnsStats.by_type || {})) {
        recordTypesHtml += `
            <div class="col-md-4 mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge bg-info">${type}</span>
                    <span class="fw-bold">${formatNumber(count)}</span>
                </div>
            </div>
        `;
    }
    
    const html = `
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-dns me-2"></i>DNS Record Types</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        ${recordTypesHtml}
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-shield-alt me-2"></i>Proxy Status</h5>
                </div>
                <div class="card-body">
                    <div class="text-center mb-3">
                        <h6 class="text-muted">Proxied Records</h6>
                        <h4 class="text-warning">${formatNumber(dnsStats.proxied_count || 0)}</h4>
                    </div>
                    <div class="text-center">
                        <h6 class="text-muted">Zones with Records</h6>
                        <h4 class="text-primary">${formatNumber(dnsStats.zones_with_records || 0)}</h4>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    container.style.display = 'flex';
}

// Display tables information
function displayTablesInformation(tables, tablesMetadata) {
    const container = document.getElementById('tables-container');
    
    let tableRows = '';
    for (const [tableName, columns] of Object.entries(tables)) {
        const metadata = tablesMetadata[tableName];
        const lastUpdated = metadata.last_updated ? 
            formatDate(metadata.last_updated) : 
            '<span class="text-muted">N/A</span>';
            
        tableRows += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <i class="fas fa-table text-muted me-2"></i>
                        <strong>${tableName}</strong>
                    </div>
                </td>
                <td>
                    <span class="badge bg-primary">${formatNumber(metadata.row_count)}</span>
                </td>
                <td>${metadata.column_count}</td>
                <td>${lastUpdated}</td>
                <td>
                    <button type="button" class="btn btn-outline-info btn-sm" 
                            onclick="toggleTableSchema('${tableName}')" title="Show Schema">
                        <i class="fas fa-info-circle"></i> Schema
                    </button>
                </td>
            </tr>
            <tr id="schema-${tableName}" class="collapse">
                <td colspan="5">
                    <div class="bg-light p-3 rounded">
                        <h6 class="mb-2">Table Schema: <code>${tableName}</code></h6>
                        <div class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead>
                                    <tr>
                                        <th>Column</th>
                                        <th>Type</th>
                                        <th>Not Null</th>
                                        <th>Default</th>
                                        <th>Primary Key</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${buildSchemaRows(columns)}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    }
    
    const html = `
        <table class="table table-hover mb-0">
            <thead class="table-light">
                <tr>
                    <th>Table Name</th>
                    <th>Records</th>
                    <th>Columns</th>
                    <th>Last Updated</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${tableRows}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

// Build schema rows for a table
function buildSchemaRows(columns) {
    return columns.map(column => `
        <tr>
            <td><code>${column.name}</code></td>
            <td><span class="badge bg-secondary">${column.type}</span></td>
            <td>
                ${column.notnull ? 
                    '<i class="fas fa-check text-success"></i>' : 
                    '<i class="fas fa-times text-muted"></i>'
                }
            </td>
            <td>
                ${column.default ? 
                    `<code>${column.default}</code>` : 
                    '<span class="text-muted">NULL</span>'
                }
            </td>
            <td>
                ${column.pk ? 
                    '<i class="fas fa-key text-warning"></i>' : 
                    '<span class="text-muted">-</span>'
                }
            </td>
        </tr>
    `).join('');
}

// Toggle table schema display
function toggleTableSchema(tableName) {
    const schemaRow = document.getElementById('schema-' + tableName);
    const isVisible = schemaRow.classList.contains('show');
    
    if (isVisible) {
        schemaRow.classList.remove('show');
    } else {
        // Hide all other schema rows first
        document.querySelectorAll('[id^="schema-"]').forEach(row => {
            row.classList.remove('show');
        });
        // Show the clicked one
        schemaRow.classList.add('show');
    }
}

// Display schema information
function displaySchemaInformation(tables) {
    const container = document.getElementById('schema-container');
    
    let schemaHtml = '';
    for (const [tableName, columns] of Object.entries(tables)) {
        schemaHtml += `
            <div class="card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-table text-primary me-2"></i>
                        ${tableName}
                    </h6>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th style="width: 30%;">Column</th>
                                    <th style="width: 20%;">Type</th>
                                    <th style="width: 15%;">Null</th>
                                    <th style="width: 20%;">Default</th>
                                    <th style="width: 15%;">Key</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${columns.map(column => `
                                    <tr>
                                        <td>
                                            <strong class="text-monospace">${column.name}</strong>
                                        </td>
                                        <td>
                                            <span class="badge bg-secondary">${column.type}</span>
                                        </td>
                                        <td>
                                            ${column.notnull ? 
                                                '<span class="text-danger">NO</span>' : 
                                                '<span class="text-success">YES</span>'
                                            }
                                        </td>
                                        <td>
                                            <code class="text-muted small">
                                                ${column.default !== null ? column.default : 'NULL'}
                                            </code>
                                        </td>
                                        <td>
                                            ${column.pk ? 
                                                '<i class="fas fa-key text-warning" title="Primary Key"></i>' : 
                                                '<span class="text-muted">-</span>'
                                            }
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = schemaHtml;
}

// Utility functions
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function showError(message) {
    document.getElementById('loading').innerHTML = `
        <div class="alert alert-danger">
            <h5><i class="fas fa-exclamation-triangle"></i> Error</h5>
            <p>${message}</p>
            <button class="btn btn-outline-danger" onclick="loadDatabaseOverview()">
                <i class="fas fa-redo"></i> Retry
            </button>
        </div>
    `;
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