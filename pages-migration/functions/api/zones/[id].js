/**
 * Get zone details and DNS records
 * Equivalent to Flask route: GET /zone/<zone_id>
 */
export async function onRequestGet(context) {
    const { params, env } = context;
    const zoneId = params.id;
    
    if (!zoneId) {
        return new Response(JSON.stringify({
            success: false,
            error: 'Zone ID is required'
        }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    try {
        // Get zone details
        const zone = await env.DB.prepare(`
            SELECT * FROM zones WHERE id = ?
        `).bind(zoneId).first();
        
        if (!zone) {
            return new Response(JSON.stringify({
                success: false,
                error: 'Zone not found'
            }), {
                status: 404,
                headers: { 'Content-Type': 'application/json' }
            });
        }
        
        // Get DNS records for this zone
        const { results: dnsRecords } = await env.DB.prepare(`
            SELECT * FROM dns_records 
            WHERE zone_id = ? 
            ORDER BY type, name
        `).bind(zoneId).all();
        
        return new Response(JSON.stringify({
            success: true,
            zone: zone,
            dns_records: dnsRecords
        }), {
            headers: { 
                'Content-Type': 'application/json',
                'Cache-Control': 'public, max-age=300'
            }
        });
        
    } catch (error) {
        console.error('Error fetching zone details:', error);
        return new Response(JSON.stringify({
            success: false,
            error: 'Failed to fetch zone details',
            details: error.message
        }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}