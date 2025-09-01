/**
 * Sync data from Cloudflare API to D1 database
 * Equivalent to Flask route: POST /sync
 */

// Global sync state
let syncState = {
    syncing: false,
    current_phase: '',
    zones_processed: 0,
    total_zones: 0,
    current_zone: '',
    start_time: null
};

export async function onRequestPost(context) {
    const { env } = context;
    
    // Prevent multiple simultaneous syncs
    if (syncState.syncing) {
        return new Response(JSON.stringify({
            success: false,
            error: 'Sync already in progress'
        }), {
            status: 409,
            headers: { 'Content-Type': 'application/json' }
        });
    }
    
    try {
        // Initialize sync state
        syncState = {
            syncing: true,
            current_phase: 'Fetching zones from Cloudflare',
            zones_processed: 0,
            total_zones: 0,
            current_zone: '',
            start_time: new Date()
        };
        
        // Fetch ALL zones from Cloudflare API with pagination
        const zones = [];
        let page = 1;
        let hasMore = true;
        
        while (hasMore) {
            const zonesResponse = await fetch(`https://api.cloudflare.com/client/v4/zones?per_page=100&page=${page}`, {
                headers: {
                    'X-Auth-Email': env.CLOUDFLARE_EMAIL,
                    'X-Auth-Key': env.CLOUDFLARE_API_KEY,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!zonesResponse.ok) {
                throw new Error(`Cloudflare API error: ${zonesResponse.status}`);
            }
            
            const zonesData = await zonesResponse.json();
            const pageZones = zonesData.result || [];
            
            zones.push(...pageZones);
            
            // Update sync status with current progress
            syncState.current_phase = `Fetching zones from Cloudflare (${zones.length} found so far...)`;
            
            // Check if we have more pages
            hasMore = pageZones.length === 100; // If we got exactly 100, there might be more
            page++;
            
            // Safety check to prevent infinite loops
            if (page > 50) break; // Max 5000 zones
        }
        
        syncState.total_zones = zones.length;
        syncState.current_phase = 'Syncing zones to database';
        
        // Process zones in batches to avoid timeout
        const batchSize = 10;
        for (let i = 0; i < zones.length; i += batchSize) {
            const batch = zones.slice(i, i + batchSize);
            
            // Process batch
            for (const zone of batch) {
                syncState.current_zone = zone.name;
                
                // Sync zone data
                await syncZone(env, zone);
                
                // Sync DNS records for this zone
                await syncDnsRecords(env, zone.id);
                
                // Sync analytics data
                await syncAnalytics(env, zone.id);
                
                syncState.zones_processed++;
            }
        }
        
        // Mark sync as complete
        syncState.syncing = false;
        syncState.current_phase = 'Sync completed successfully';
        
        return new Response(JSON.stringify({
            success: true,
            message: `Successfully synced ${zones.length} zones`,
            zones_processed: zones.length
        }), {
            headers: { 'Content-Type': 'application/json' }
        });
        
    } catch (error) {
        console.error('Sync error:', error);
        syncState.syncing = false;
        syncState.current_phase = `Sync failed: ${error.message}`;
        
        return new Response(JSON.stringify({
            success: false,
            error: 'Sync failed',
            details: error.message
        }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Get sync progress
export async function onRequestGet(context) {
    const elapsed = syncState.start_time ? 
        Math.floor((new Date() - syncState.start_time) / 1000) : 0;
        
    return new Response(JSON.stringify({
        syncing: syncState.syncing,
        current_phase: syncState.current_phase,
        zones_processed: syncState.zones_processed,
        total_zones: syncState.total_zones,
        current_zone: syncState.current_zone,
        elapsed_seconds: elapsed
    }), {
        headers: { 'Content-Type': 'application/json' }
    });
}

async function syncZone(env, zone) {
    const stmt = env.DB.prepare(`
        INSERT OR REPLACE INTO zones (
            id, name, status, plan_name, type, name_servers, 
            original_name_servers, created_on, modified_on, 
            account_id, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    
    await stmt.bind(
        zone.id,
        zone.name,
        zone.status,
        zone.plan?.name || 'Unknown',
        zone.type,
        JSON.stringify(zone.name_servers || []),
        JSON.stringify(zone.original_name_servers || []),
        zone.created_on,
        zone.modified_on,
        zone.account?.id || env.CLOUDFLARE_ACCOUNT_ID,
        new Date().toISOString()
    ).run();
}

async function syncDnsRecords(env, zoneId) {
    try {
        const response = await fetch(`https://api.cloudflare.com/client/v4/zones/${zoneId}/dns_records?per_page=100`, {
            headers: {
                'X-Auth-Email': env.CLOUDFLARE_EMAIL,
                'X-Auth-Key': env.CLOUDFLARE_API_KEY,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) return; // Skip if DNS records can't be fetched
        
        const data = await response.json();
        const records = data.result || [];
        
        // Clear existing DNS records for this zone
        await env.DB.prepare('DELETE FROM dns_records WHERE zone_id = ?').bind(zoneId).run();
        
        // Insert new DNS records
        const stmt = env.DB.prepare(`
            INSERT INTO dns_records (
                id, zone_id, type, name, content, ttl, proxied, created_on, modified_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `);
        
        for (const record of records) {
            await stmt.bind(
                record.id,
                zoneId,
                record.type,
                record.name,
                record.content,
                record.ttl,
                record.proxied || false,
                record.created_on,
                record.modified_on
            ).run();
        }
        
    } catch (error) {
        console.error(`Error syncing DNS records for zone ${zoneId}:`, error);
    }
}

async function syncAnalytics(env, zoneId) {
    try {
        // GraphQL query for analytics
        const since = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        const until = new Date().toISOString().split('T')[0];
        
        const query = {
            query: `
                query GetZoneAnalytics($zoneTag: String!, $since: String!, $until: String!) {
                    viewer {
                        zones(filter: {zoneTag: $zoneTag}) {
                            httpRequests1dGroups(
                                limit: 10,
                                filter: {
                                    date_geq: $since,
                                    date_leq: $until
                                }
                            ) {
                                sum {
                                    requests
                                    bytes
                                    threats
                                }
                            }
                        }
                    }
                }
            `,
            variables: {
                zoneTag: zoneId,
                since: since,
                until: until
            }
        };
        
        const response = await fetch('https://api.cloudflare.com/client/v4/graphql', {
            method: 'POST',
            headers: {
                'X-Auth-Email': env.CLOUDFLARE_EMAIL,
                'X-Auth-Key': env.CLOUDFLARE_API_KEY,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(query)
        });
        
        if (!response.ok) return; // Skip if analytics can't be fetched
        
        const data = await response.json();
        const zones = data.data?.viewer?.zones || [];
        
        if (zones.length > 0 && zones[0].httpRequests1dGroups.length > 0) {
            const analytics = zones[0].httpRequests1dGroups[0].sum;
            
            // Update zone with analytics data
            await env.DB.prepare(`
                UPDATE zones 
                SET analytics_requests = ?, analytics_bandwidth = ?, analytics_threats = ?
                WHERE id = ?
            `).bind(
                analytics.requests || 0,
                analytics.bytes || 0,
                analytics.threats || 0,
                zoneId
            ).run();
        }
        
    } catch (error) {
        console.error(`Error syncing analytics for zone ${zoneId}:`, error);
    }
}