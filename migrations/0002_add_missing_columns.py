"""Migration to add missing columns to zones table."""

def upgrade(conn):
    """Add missing columns to zones table."""
    cursor = conn.cursor()
    
    # Add missing columns if they don't exist
    cursor.execute('''
        PRAGMA table_info(zones)
    ''')
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'account_id' not in columns:
        cursor.execute('''
            ALTER TABLE zones
            ADD COLUMN account_id TEXT
        ''')
    
    if 'account_name' not in columns:
        cursor.execute('''
            ALTER TABLE zones
            ADD COLUMN account_name TEXT
        ''')
    
    if 'owner_email' not in columns:
        cursor.execute('''
            ALTER TABLE zones
            ADD COLUMN owner_email TEXT
        ''')
    
    if 'activated_on' not in columns:
        cursor.execute('''
            ALTER TABLE zones
            ADD COLUMN activated_on TEXT
        ''')
    
    conn.commit()
    
    # Update the database version
    cursor.execute('''
        UPDATE db_version 
        SET version = 2, 
            last_updated = CURRENT_TIMESTAMP
    ''')
    conn.commit()

def downgrade(conn):
    """Revert the schema changes."""
    # Note: SQLite doesn't support dropping columns, so we'll just update the version
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE db_version 
        SET version = 1, 
            last_updated = CURRENT_TIMESTAMP
    ''')
    conn.commit()
