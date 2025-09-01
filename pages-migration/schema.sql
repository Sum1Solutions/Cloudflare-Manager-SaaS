-- Cloudflare Manager D1 Database Schema
-- Migration from SQLite to D1

-- Drop tables if they exist (for clean migration)
DROP TABLE IF EXISTS dns_records;
DROP TABLE IF EXISTS zones;
DROP TABLE IF EXISTS db_version;
DROP TABLE IF EXISTS _migrations;

-- Create zones table with all current fields
CREATE TABLE zones (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT,
    plan_name TEXT,
    type TEXT,
    name_servers TEXT,
    original_name_servers TEXT,
    created_on TEXT,
    modified_on TEXT,
    account_id TEXT,
    analytics_requests INTEGER DEFAULT 0,
    analytics_bandwidth INTEGER DEFAULT 0,
    analytics_threats INTEGER DEFAULT 0,
    last_updated TEXT
);

-- Create DNS records table with foreign key constraint
CREATE TABLE dns_records (
    id TEXT PRIMARY KEY,
    zone_id TEXT NOT NULL,
    type TEXT,
    name TEXT,
    content TEXT,
    ttl INTEGER,
    proxied BOOLEAN DEFAULT FALSE,
    created_on TEXT,
    modified_on TEXT,
    FOREIGN KEY (zone_id) REFERENCES zones (id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_zones_name ON zones(name);
CREATE INDEX idx_zones_status ON zones(status);
CREATE INDEX idx_zones_last_updated ON zones(last_updated);
CREATE INDEX idx_dns_records_zone_id ON dns_records(zone_id);
CREATE INDEX idx_dns_records_type ON dns_records(type);

-- Create database version tracking table
CREATE TABLE db_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial version
INSERT INTO db_version (version) VALUES (1);