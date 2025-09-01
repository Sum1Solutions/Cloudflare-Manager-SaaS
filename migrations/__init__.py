"""
Database migration package for Cloudflare Manager.
"""

import os
import importlib
import sqlite3
from pathlib import Path

def get_migration_files():
    """Get all migration files in order."""
    migrations_dir = Path(__file__).parent
    return sorted(
        [f.stem for f in migrations_dir.glob('*.py') 
         if f.is_file() and f.name != '__init__.py']
    )

def run_migrations(conn):
    """Run all pending database migrations."""
    cursor = conn.cursor()
    
    # Create migration tracking table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS _migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Get applied migrations
    cursor.execute('SELECT version FROM _migrations')
    applied_migrations = {row[0] for row in cursor.fetchall()}
    
    # Run pending migrations
    for migration in get_migration_files():
        if migration not in applied_migrations:
            print(f"Running migration: {migration}")
            try:
                module = importlib.import_module(f'migrations.{migration}')
                module.upgrade(conn)
                
                # Record successful migration
                cursor.execute(
                    'INSERT INTO _migrations (version) VALUES (?)',
                    (migration,)
                )
                conn.commit()
                print(f"Successfully applied migration: {migration}")
                
            except Exception as e:
                conn.rollback()
                print(f"Error applying migration {migration}: {e}")
                raise
    
    return True
