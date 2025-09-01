/**
 * Database overview and statistics
 * Equivalent to Flask route: GET /view_db
 */
export async function onRequestGet(context) {
    const { env } = context;
    
    try {
        // Get database file size (simulated for D1)
        const dbSize = 0.5; // D1 doesn't expose size, so we'll estimate
        
        // Get table metadata
        const tables = {};
        const tablesMetadata = {};
        let totalRows = 0;
        
        // Zones table statistics
        const zonesCount = await env.DB.prepare('SELECT COUNT(*) as count FROM zones').first();
        const zonesColumns = [
            { name: 'id', type: 'TEXT', notnull: 1, default: null, pk: 1 },
            { name: 'name', type: 'TEXT', notnull: 1, default: null, pk: 0 },
            { name: 'status', type: 'TEXT', notnull: 0, default: null, pk: 0 },
            { name: 'plan_name', type: 'TEXT', notnull: 0, default: null, pk: 0 },
            { name: 'analytics_requests', type: 'INTEGER', notnull: 0, default: 0, pk: 0 },
            { name: 'analytics_bandwidth', type: 'INTEGER', notnull: 0, default: 0, pk: 0 },
            { name: 'analytics_threats', type: 'INTEGER', notnull: 0, default: 0, pk: 0 },
            { name: 'last_updated', type: 'TEXT', notnull: 0, default: null, pk: 0 }
        ];
        
        const zonesLastUpdated = await env.DB.prepare('SELECT MAX(last_updated) as last_updated FROM zones').first();
        
        tables['zones'] = zonesColumns;
        tablesMetadata['zones'] = {
            row_count: zonesCount.count,
            last_updated: zonesLastUpdated.last_updated,
            column_count: zonesColumns.length,
            columns: zonesColumns
        };
        totalRows += zonesCount.count;
        
        // DNS records table statistics
        const dnsCount = await env.DB.prepare('SELECT COUNT(*) as count FROM dns_records').first();
        const dnsColumns = [
            { name: 'id', type: 'TEXT', notnull: 1, default: null, pk: 1 },
            { name: 'zone_id', type: 'TEXT', notnull: 1, default: null, pk: 0 },
            { name: 'type', type: 'TEXT', notnull: 0, default: null, pk: 0 },
            { name: 'name', type: 'TEXT', notnull: 0, default: null, pk: 0 },
            { name: 'content', type: 'TEXT', notnull: 0, default: null, pk: 0 },
            { name: 'ttl', type: 'INTEGER', notnull: 0, default: null, pk: 0 },
            { name: 'proxied', type: 'BOOLEAN', notnull: 0, default: false, pk: 0 }
        ];
        
        const dnsLastUpdated = await env.DB.prepare('SELECT MAX(modified_on) as last_updated FROM dns_records').first();
        
        tables['dns_records'] = dnsColumns;
        tablesMetadata['dns_records'] = {
            row_count: dnsCount.count,
            last_updated: dnsLastUpdated.last_updated,
            column_count: dnsColumns.length,
            columns: dnsColumns
        };
        totalRows += dnsCount.count;
        
        // Enhanced zone statistics
        const zoneStatsByStatus = await env.DB.prepare(`
            SELECT status, COUNT(*) as count FROM zones GROUP BY status
        `).all();
        
        const zoneStatsByPlan = await env.DB.prepare(`
            SELECT plan_name, COUNT(*) as count FROM zones GROUP BY plan_name
        `).all();
        
        const zonesWithAnalytics = await env.DB.prepare(`
            SELECT COUNT(*) as count FROM zones WHERE analytics_requests > 0
        `).first();
        
        const analyticsAvg = await env.DB.prepare(`
            SELECT 
                AVG(analytics_requests) as avg_requests,
                AVG(analytics_bandwidth) as avg_bandwidth,
                AVG(analytics_threats) as avg_threats
            FROM zones WHERE analytics_requests > 0
        `).first();
        
        const analyticsMax = await env.DB.prepare(`
            SELECT 
                MAX(analytics_requests) as max_requests,
                MAX(analytics_bandwidth) as max_bandwidth,
                MAX(analytics_threats) as max_threats
            FROM zones
        `).first();
        
        // DNS statistics
        const dnsStatsByType = await env.DB.prepare(`
            SELECT type, COUNT(*) as count FROM dns_records GROUP BY type ORDER BY count DESC
        `).all();
        
        const proxiedCount = await env.DB.prepare(`
            SELECT COUNT(*) as count FROM dns_records WHERE proxied = 1
        `).first();
        
        const zonesWithRecords = await env.DB.prepare(`
            SELECT COUNT(DISTINCT zone_id) as count FROM dns_records
        `).first();
        
        // Build response
        const zoneStats = {
            by_status: Object.fromEntries(zoneStatsByStatus.results.map(r => [r.status, r.count])),
            by_plan: Object.fromEntries(zoneStatsByPlan.results.map(r => [r.plan_name, r.count])),
            with_analytics: zonesWithAnalytics.count,
            avg_analytics: {
                requests: analyticsAvg.avg_requests || 0,
                bandwidth: analyticsAvg.avg_bandwidth || 0,
                threats: analyticsAvg.avg_threats || 0
            },
            max_analytics: {
                requests: analyticsMax.max_requests || 0,
                bandwidth: analyticsMax.max_bandwidth || 0,
                threats: analyticsMax.max_threats || 0
            }
        };
        
        const dnsStats = {
            by_type: Object.fromEntries(dnsStatsByType.results.map(r => [r.type, r.count])),
            proxied_count: proxiedCount.count,
            zones_with_records: zonesWithRecords.count
        };
        
        const dbOverview = {
            total_tables: Object.keys(tables).length,
            total_rows: totalRows,
            db_size_mb: dbSize,
            zone_stats: zoneStats,
            dns_stats: dnsStats
        };
        
        return new Response(JSON.stringify({
            success: true,
            tables: tables,
            tables_metadata: tablesMetadata,
            db_overview: dbOverview
        }), {
            headers: { 
                'Content-Type': 'application/json',
                'Cache-Control': 'public, max-age=300'
            }
        });
        
    } catch (error) {
        console.error('Error fetching database overview:', error);
        return new Response(JSON.stringify({
            success: false,
            error: 'Failed to fetch database overview',
            details: error.message
        }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}