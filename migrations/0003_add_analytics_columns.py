"""
Migration 0003: Add Analytics columns to zones table
"""

def upgrade(conn):
    """Add Analytics columns to zones table."""
    cursor = conn.cursor()
    
    # Add Analytics columns
    try:
        cursor.execute('ALTER TABLE zones ADD COLUMN analytics_requests INTEGER DEFAULT 0')
    except Exception:
        pass  # Column might already exist
    
    try:
        cursor.execute('ALTER TABLE zones ADD COLUMN analytics_bandwidth INTEGER DEFAULT 0') 
    except Exception:
        pass  # Column might already exist
        
    try:
        cursor.execute('ALTER TABLE zones ADD COLUMN analytics_threats INTEGER DEFAULT 0')
    except Exception:
        pass  # Column might already exist
        
    try:
        cursor.execute('ALTER TABLE zones ADD COLUMN analytics_updated TIMESTAMP')
    except Exception:
        pass  # Column might already exist
    
    conn.commit()
    print("Added Analytics columns to zones table")

def downgrade(conn):
    """Remove Analytics columns from zones table."""
    cursor = conn.cursor()
    
    # SQLite doesn't support DROP COLUMN directly, so we would need to recreate the table
    # For now, we'll just leave the columns as they don't hurt anything
    print("Analytics columns left in place (SQLite limitation)")