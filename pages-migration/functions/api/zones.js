/**
 * Get all zones from D1 database
 * Equivalent to Flask route: GET /
 */
export async function onRequestGet(context) {
    const { env } = context;
    
    try {
        // Get all zones with analytics data
        const { results } = await env.DB.prepare(`
            SELECT 
                id,
                name,
                status,
                plan_name,
                type,
                account_id,
                analytics_requests,
                analytics_bandwidth,
                analytics_threats,
                created_on,
                modified_on,
                last_updated
            FROM zones 
            ORDER BY name ASC
        `).all();
        
        // Get last sync time
        const lastSyncResult = await env.DB.prepare(`
            SELECT MAX(last_updated) as last_sync FROM zones
        `).first();
        
        return new Response(JSON.stringify({
            success: true,
            zones: results,
            last_sync: lastSyncResult?.last_sync,
            total: results.length
        }), {
            headers: { 
                'Content-Type': 'application/json',
                'Cache-Control': 'public, max-age=60'
            }
        });
        
    } catch (error) {
        console.error('Error fetching zones:', error);
        return new Response(JSON.stringify({
            success: false,
            error: 'Failed to fetch zones',
            details: error.message
        }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}