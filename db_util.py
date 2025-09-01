# db_util.py

import sqlite3
import os
from pathlib import Path
from datetime import datetime
import logging
try:
    from migrations import run_migrations
except ImportError:
    from .migrations import run_migrations

# Constants
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cloudflare_manager.db')

def setup_database():
    """
    Initialize the database, set up tables if they don't exist, and run migrations.
    Combines schemas from both cloudflare-manager and cloudflare_data_getter.
    """
    # Ensure the database directory exists
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    
    try:
        # Enable foreign key support
        conn.execute('PRAGMA foreign_keys = ON')
        
        # Create initial tables if they don't exist
        cursor = conn.cursor()
        
        # Create zones table (expanded with fields from cloudflare_data_getter)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zones (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT,
                type TEXT,
                plan_name TEXT,
                name_servers TEXT,
                original_name_servers TEXT,
                created_on TEXT,
                modified_on TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auth_code_from_directnic TEXT,
                purchase_date TEXT,
                dns_records TEXT,
                account_id TEXT,
                account_name TEXT,
                owner_email TEXT,
                activated_on TEXT
            )
        ''')
        
        # Create DNS records table (from cloudflare_data_getter)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dns_records (
                id TEXT PRIMARY KEY,
                zone_id TEXT NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                content TEXT,
                ttl INTEGER DEFAULT 1,
                proxied BOOLEAN DEFAULT 0,
                created_on TEXT,
                modified_on TEXT,
                priority INTEGER,
                FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dns_records_zone_id 
            ON dns_records(zone_id);
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dns_records_type 
            ON dns_records(type);
        ''')
        
        # Create table to track the database version
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_version (
                version INTEGER PRIMARY KEY,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Initialize version if not exists
        cursor.execute('INSERT OR IGNORE INTO db_version (version) VALUES (0)')
        
        # Run migrations
        run_migrations(conn)
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"Error setting up database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_database_connection():
    """
    Get a connection to the SQLite database with extended functionality.
    Enables foreign key support and row factory for named tuple access.
    Logs errors if connection fails or file is missing.
    """
    def dict_factory(cursor, row):
        """Convert query results to dictionary."""
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}
    try:
        if not os.path.exists(DATABASE_PATH):
            logging.error(f"Database file not found: {DATABASE_PATH}")
            raise FileNotFoundError(f"Database file not found: {DATABASE_PATH}")
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = dict_factory
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        raise

def backup_database():
    """Create a timestamped backup of the database."""
    if not os.path.exists(DATABASE_PATH):
        return False
        
    backup_dir = os.path.join(os.path.dirname(DATABASE_PATH), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'cloudflare_manager_{timestamp}.db')
    
    try:
        import shutil
        shutil.copy2(DATABASE_PATH, backup_path)
        return backup_path
    except Exception as e:
        logging.error(f"Failed to create database backup: {e}")
        return False
