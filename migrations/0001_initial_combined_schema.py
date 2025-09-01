"""
Database migration to combine schemas from cloudflare-manager and cloudflare_data_getter
"""

def upgrade(conn):
    cursor = conn.cursor()
    
    # Add columns from cloudflare_data_getter's domain_info table
    cursor.execute('''
        ALTER TABLE zones ADD COLUMN purchase_date TEXT;
    ''')
    
    cursor.execute('''
        ALTER TABLE zones ADD COLUMN dns_records TEXT;
    ''')
    
    # Create a new table for DNS records if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dns_records (
            id TEXT PRIMARY KEY,
            zone_id TEXT,
            type TEXT,
            name TEXT,
            content TEXT,
            ttl INTEGER,
            proxied BOOLEAN,
            created_on TEXT,
            modified_on TEXT,
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )
    ''')
    
    # Create index on zone_id for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_dns_records_zone_id ON dns_records(zone_id);
    ''')
    
    # Update database version
    cursor.execute('''
        UPDATE db_version SET version = 2, last_updated = CURRENT_TIMESTAMP;
    ''')
    
    conn.commit()

def downgrade(conn):
    cursor = conn.cursor()
    
    # Note: SQLite doesn't support DROP COLUMN in ALTER TABLE
    # These would need to be handled by creating a new table and copying data
    
    # Revert database version
    cursor.execute('''
        UPDATE db_version SET version = 1, last_updated = CURRENT_TIMESTAMP;
    ''')
    
    conn.commit()
