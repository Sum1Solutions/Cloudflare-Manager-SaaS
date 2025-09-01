#!/usr/bin/env python3
"""
Script to set up the database and run migrations.
This will create any missing tables and run pending migrations.
"""

import logging
from db_util import setup_database

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Setting up database and running migrations...")
    setup_database()
    logging.info("Database setup complete!")
