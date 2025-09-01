# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloudflare Manager is an **opensource** web application designed for agencies, developers, and businesses managing multiple Cloudflare zones (domains). Available in two architectures: **Flask + SQLite** (traditional) and **Cloudflare Pages + D1** (serverless). Both provide advanced interfaces for managing multiple domains with synchronized databases, analytics, and modern UI features.

**Alpha Testing**: Currently being production-tested at Sum1Solutions with 400+ domains. The opensource community is welcome to contribute and use this tool for their own domain management needs.

## Current Enhanced Features

### Recent Major Enhancements (v2.2)
- **Configurable Authentication**: Choose between Auth0 OAuth or Cloudflare Access zero-trust authentication
- **Enterprise Authentication**: Professional authentication system supporting multiple auth methods
- **Production Testing**: Real-world testing with 400+ domains for scalability and reliability
- **Enhanced Dashboard**: Compact analytics overview with 4-card summary at page top
- **Prominent Search Interface**: Left-aligned, enhanced search box with modern styling and animations
- **Database Administration Panel**: Dual-view interface with Tables/Schema toggle and detailed column specs
- **Improved Navigation**: Consistent logout button alignment and better responsive navbar
- **Advanced DataTables**: 8-column search layout, wider dropdown menus, better pagination support
- **Schema Explorer**: Detailed database schema viewer with column types, constraints, and keys
- **Full Pagination Support**: Handles 399+ domains with proper API pagination and real-time sync
- **Pages + D1 Migration**: Complete serverless version with Cloudflare Pages Functions and D1 database
- **GraphQL Analytics Integration**: Migrated from deprecated REST API to GraphQL for accurate analytics data
- **Background Sync Operations**: Async sync with cancellation support and toast notifications  
- **Dark/Light Theme Support**: Toggle themes with persistent user preference and full component theming

## Key Commands

### Running the Application

#### Flask Version (Traditional)
```bash
flask run
# or
python app.py
```

#### Pages + D1 Version (Serverless) - **Primary Focus**
```bash
# Navigate to pages migration
cd pages-migration

# Local development
wrangler pages dev public/ --port=3000

# Deploy to production
wrangler pages deploy public/ --project-name=cloudflare-manager
```

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials:
# CLOUDFLARE_EMAIL, CLOUDFLARE_KEY, CLOUDFLARE_ACCOUNT_ID
# AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET
```

### Database Operations
```bash
# Initialize/update database schema
python setup_db.py

# Run migrations
python run_migration.py
```

### Testing
```bash
# Run test suite
python run_tests.py

# Run specific test
python -m pytest tests/test_app.py::TestDNSSECAnalysis -v
```

## Architecture Overview

### Core Components

1. **app.py** - Main Flask application with enhanced routes:
   - `/` - Dashboard with analytics table, theme toggle, and background sync
   - `/sync` - Synchronize data from Cloudflare API with real-time progress
   - `/zone/<zone_id>` - Zone details with DNS records and themed UI
   - `/view_db` - Comprehensive database overview with statistics and schema viewer
   - `/export/domains.csv` - Export domains as CSV
   - `/api/sync/progress` - Real-time sync progress API
   - `/api/sync/cancel` - Cancel running sync operations

2. **cloudflare_api.py** - Enhanced Cloudflare API client wrapper
   - GraphQL API integration for analytics (replaced deprecated REST API)
   - Handles authentication and API requests with improved error handling
   - Methods for zones, DNS records, and GraphQL analytics queries

3. **sync_manager.py** - Advanced database synchronization logic
   - Background sync with cancellation support and progress tracking
   - Analytics data synchronization using GraphQL API
   - Real-time progress updates with zone counting and elapsed time

4. **db_util.py** - Database utilities with enhanced functionality
   - Connection management with row factory for dict access
   - Schema setup and migration runner with version tracking
   - Database backup functionality and statistics queries

### Database Schema

- **zones** table - Cloudflare zones with metadata and analytics columns:
  - Core zone data (id, name, status, plan_name, etc.)
  - Analytics data (analytics_requests, analytics_bandwidth, analytics_threats) 
  - Timestamps (created_on, modified_on, last_updated)
- **dns_records** table - DNS records for each zone with foreign key constraints
- **db_version** table - Migration tracking for schema updates
- **_migrations** table - Migration history and status tracking

### Enhanced UI Components

- **templates/base.html** - Base template with theme toggle and toast notifications
- **templates/domains_combined.html** - Main dashboard with enhanced DataTables and analytics sorting
- **templates/view_db.html** - Database overview with statistics cards and schema viewer
- **templates/zone_details.html** - Zone details with themed components
- **static/css/main.css** - Comprehensive theming with CSS variables for light/dark modes

### Key Environment Variables

- `CLOUDFLARE_EMAIL` - Account email for API auth
- `CLOUDFLARE_API_KEY` or `CLOUDFLARE_KEY` - Global API key
- `CLOUDFLARE_ACCOUNT_ID` - Account identifier
- `SECRET_KEY` - Flask session secret
- `AUTH0_DOMAIN` - Auth0 tenant domain (e.g., dev-xxx.us.auth0.com)
- `AUTH0_CLIENT_ID` - Auth0 application client ID
- `AUTH0_CLIENT_SECRET` - Auth0 application client secret

### Auth0 Configuration

The application uses Auth0 for enterprise-grade authentication:

- **Application Type**: Regular Web Application
- **Allowed Callback URLs**: `https://yourdomain.com/callback, http://127.0.0.1:5001/callback`
- **Allowed Logout URLs**: `https://yourdomain.com/logged_out, http://127.0.0.1:5001/logged_out`
- **Allowed Web Origins**: `https://yourdomain.com, http://127.0.0.1:5001`

#### Multi-Domain Setup
Single Auth0 application handles multiple domains:
- sum1solutions.com (admin portal)
- cloudflaremanager.com (domain management)
- Additional domains as needed

#### Tier-Based Access Control (Framework Ready)
- User metadata in Auth0 stores subscription tiers and allowed sites
- Session contains user permissions and site access rights
- Extensible for future subscription-based access control

### Important Notes

- The app uses SQLite with foreign key constraints enabled
- DNS records table has a foreign key to zones with CASCADE delete
- All datetime conversions use EDT timezone (UTC-4)
- Analytics data is fetched using Cloudflare's GraphQL API (not deprecated REST API)
- Theme preferences are stored in localStorage with CSS variable theming
- Background sync operations use global state management with cancellation support
- Progress tracking uses polling with real-time updates via JavaScript
- DataTables integration includes custom sorting for analytics columns
- Toast notifications provide non-intrusive user feedback for completed operations
- Database overview includes comprehensive statistics and schema inspection tools