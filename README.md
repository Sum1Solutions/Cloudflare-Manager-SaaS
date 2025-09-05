# Cloudflare Manager

A web application for managing multiple Cloudflare zones (domains) and their DNS records. Useful for developers and small agencies managing multiple domains. Available in two versions: **Flask + SQLite** (traditional) and **Cloudflare Pages + D1** (serverless).

> **Note**: This is a working tool that's been used with multiple domains in real environments, but it's still evolving. Test thoroughly in your own environment before relying on it.

## Deployment Options

### Option 1: Flask Application (Traditional)
- Self-hosted Python Flask application
- SQLite database for local storage
- Full server control and customization

### Option 2: Cloudflare Pages + D1 (Serverless)
- Serverless deployment on Cloudflare's global network
- D1 database for edge storage
- Zero maintenance, automatic scaling
- Complete Pages migration available in `pages-migration/` directory

## Features

### Dashboard
- Analytics overview with key metrics
- Search interface for finding domains quickly
- Sortable, searchable table for all domains
- Real-time analytics data via GraphQL API
- Custom sorting, pagination, responsive design

### Database Administration
- Toggle between Tables and Schema views
- Detailed column information, data types, constraints
- Row counts, timestamps, sortable table listings
- Optional detailed analytics section

### Other Features
- **Background Synchronization**: Async sync with real-time progress tracking and cancellation
- **Theme Support**: Dark/light mode toggle with persistent preferences
- **Configurable Authentication**: Choose between Auth0 OAuth or Cloudflare Access zero-trust authentication
- **Export Capabilities**: CSV export for domain listings and analytics
- **Responsive Design**: Bootstrap 5 with mobile-first approach
- **Tested**: Used with multiple domains in development and real environments


## Installation

### Prerequisites

- Python 3.8+
- Cloudflare account with API access
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Cloudflare-Manager.git
   cd Cloudflare-Manager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your configuration:
   ```bash
   # Cloudflare API credentials
   CLOUDFLARE_EMAIL=your-email@example.com
   CLOUDFLARE_API_KEY=your-global-api-key
   CLOUDFLARE_ACCOUNT_ID=your-account-id
   
   # Authentication method (choose one)
   AUTH_METHOD=auth0  # or 'cloudflare_access'
   
   # Auth0 configuration (if using AUTH_METHOD=auth0)
   AUTH0_DOMAIN=your-tenant.auth0.com
   AUTH0_CLIENT_ID=your-client-id
   AUTH0_CLIENT_SECRET=your-client-secret
   
   # Flask security
   SECRET_KEY=your-flask-secret-key
   ```

5. **Initialize database**
   ```bash
   python setup_db.py
   ```

6. **Run the application**
   ```bash
   python app.py
   # or
   flask run
   ```

The application will be available at `http://localhost:5001`

## Usage

### First Time Setup

1. **Sync with Cloudflare**: Click the "Sync with Cloudflare" button to download all your domains, DNS records, and analytics data
2. **Wait for completion**: The sync process shows real-time progress for large domain counts
3. **Explore your domains**: Use the search, filters, and sorting to find specific domains

### Key Functions

#### Domain Management
- **Search Domains**: Use the search box to find domains by name with real-time filtering
- **Filter by Status**: Filter domains by active, pending, or paused status
- **Sort Analytics**: Click any column header to sort including analytics data (requests, bandwidth, threats)
- **View DNS Records**: Click the info icon to see detailed DNS records for a domain
- **Open in Cloudflare**: Click the external link icon to open the domain in Cloudflare dashboard
- **Export Data**: Export domain lists as CSV for reporting

#### Database Insights
- **Database Overview**: Comprehensive statistics dashboard showing database size, table counts, and data distribution
- **Zone Analytics**: Visual breakdown of zone status, plan distribution, and performance metrics
- **DNS Statistics**: Record type distribution, proxy status, and zones with records count
- **Table Schema Viewer**: Inspect database structure with collapsible schema details

#### Advanced Features
- **Background Sync**: Start sync operations and continue working while they run in background
- **Progress Cancellation**: Cancel long-running operations with confirmation dialogs
- **Theme Toggle**: Switch between light and dark themes with persistent preference
- **Toast Notifications**: Non-intrusive notifications for completed operations
- **Check DNSSEC**: Use the "Zones Without DNSSEC" feature to audit security across all domains

### Analytics Data

The application displays comprehensive 30-day analytics including:
- **Requests**: Total HTTP requests to your domain with numeric sorting
- **Bandwidth**: Total data transfer in MB with proper formatting
- **Threats**: Security threats blocked by Cloudflare with threat analysis
- **Peak Performance**: Maximum values across all metrics for benchmarking
- **Average Performance**: Mean values for performance baseline analysis

Analytics data is powered by Cloudflare's GraphQL API and refreshed each time you sync with Cloudflare. The enhanced analytics system provides both individual domain metrics and aggregate statistics across your entire account.

## Architecture

### Core Components

- **app.py**: Main Flask application with routes and API endpoints
- **cloudflare_api.py**: Cloudflare API client wrapper with authentication
- **sync_manager.py**: Database synchronization logic with progress tracking
- **db_util.py**: Database utilities and connection management
- **templates/**: Jinja2 templates for the web interface
- **static/**: CSS, JavaScript, and other static assets

### Database Schema

- **zones**: Cloudflare domains with metadata and analytics
- **dns_records**: DNS records for each domain
- **_migrations**: Database version tracking

### Key Features

- **Progress Tracking**: Real-time progress for sync and DNSSEC operations
- **Responsive Design**: Bootstrap 5 for mobile-friendly interface
- **DataTables Integration**: Enhanced table functionality with search/sort
- **Error Handling**: Comprehensive error handling and user feedback

## API Endpoints

### Main Routes
- `GET /` - Main dashboard with enhanced analytics table
- `GET /view_db` - Comprehensive database overview with statistics
- `GET /view_table_data/<table_name>` - Individual table data viewer
- `GET /zone/<id>` - Individual zone details with DNS records
- `GET /export/domains.csv` - Export domains as CSV

### Synchronization APIs
- `POST /sync` - Trigger Cloudflare synchronization with progress tracking
- `GET /api/sync/progress` - Get real-time sync progress with cancellation support
- `POST /api/sync/cancel` - Cancel running synchronization operations

### DNSSEC Management
- `GET /no_dnssec` - DNSSEC check interface with progress tracking
- `GET /api/check-dnssec` - Start DNSSEC audit across all zones
- `GET /api/check-dnssec/progress` - Get DNSSEC check progress

### Domain Filtering
- `GET /pending` - View pending zones only
- `GET /reactivate` - View inactive zones needing reactivation

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLOUDFLARE_EMAIL` | Your Cloudflare account email | Yes |
| `CLOUDFLARE_API_KEY` | Global API key from Cloudflare | Yes |
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID | Yes |
| `AUTH_METHOD` | Authentication method: `auth0` or `cloudflare_access` | Yes |
| `AUTH0_DOMAIN` | Auth0 tenant domain (if using Auth0) | Conditional |
| `AUTH0_CLIENT_ID` | Auth0 client ID (if using Auth0) | Conditional |
| `AUTH0_CLIENT_SECRET` | Auth0 client secret (if using Auth0) | Conditional |
| `SECRET_KEY` | Flask session secret key | Yes |

### Application Settings

- **Database**: SQLite (automatically created)
- **Port**: 5001 (configurable in app.py)
- **Debug Mode**: Enabled by default (disable for production)

## Development

### Database Migrations

To add new database columns or tables:

1. Create a new migration file in `migrations/`
2. Follow the naming convention: `XXXX_description.py`
3. Run `python setup_db.py` to apply migrations

### Adding New Features

1. Update database schema if needed (create migration)
2. Add API endpoints in `app.py`
3. Update sync logic in `sync_manager.py` if fetching new data
4. Create/update templates in `templates/`
5. Add JavaScript for dynamic features

### Testing

The application includes error handling and logging. Check `flask_output.log` for detailed operation logs.

## Troubleshooting

### Common Issues

1. **"Module not found" errors**: Ensure virtual environment is activated
2. **API authentication failures**: Check your Cloudflare credentials in `.env`
3. **Port 5000 in use**: The app uses port 5001 by default
4. **Sync failures**: Check network connectivity and API rate limits
5. **Database errors**: Delete `cloudflare_manager.db` and run `python setup_db.py`

### Performance Tips

- **Large domain counts**: Sync operations may take several minutes for many domains
- **Rate limiting**: Cloudflare API has rate limits; the app handles this automatically
- **Browser performance**: Use pagination for large domain lists

## Contributing

We welcome contributions from the community! This project is opensource and actively maintained.

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**: `git clone https://github.com/yourusername/Cloudflare-Manager.git`
3. **Create a feature branch**: `git checkout -b feature-name`
4. **Make changes and test thoroughly**
5. **Update documentation** if needed
6. **Submit a pull request**

### Development Environment

For development, you can use the same setup as installation but with additional testing:

```bash
# Run tests
python run_tests.py

# Check for security vulnerabilities
pip-audit

# Start development server
flask run --debug
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names  
- Add docstrings for functions and classes
- Include error handling for external API calls
- Test with both authentication methods (Auth0 and Cloudflare Access)

### Areas for Contribution

- **New Features**: See our [roadmap](SPEC.md) for planned features
- **Bug Fixes**: Check issues for known bugs
- **Documentation**: Help improve setup guides and API docs
- **Testing**: Add tests for edge cases and new features
- **Performance**: Optimize for larger domain counts (1000+)

### Alpha Testing

This project has been tested with multiple domains in real environments. Community feedback helps identify issues and improve the tool.

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues, questions, or feature requests:

1. **Check the troubleshooting section** above
2. **Review the logs** in `flask_output.log`
3. **Open an issue** on the repository with:
   - Error messages
   - Steps to reproduce
   - Your environment details

## Roadmap

See [SPEC.md](SPEC.md) for detailed feature specifications and planned improvements.

## Authentication Setup

This application supports two authentication methods:

### Auth0 (Default)
1. Create a free Auth0 account at [auth0.com](https://auth0.com)
2. Create a new application (Regular Web Application)
3. Configure callback URLs: `http://localhost:5001/callback`
4. Set `AUTH_METHOD=auth0` in your `.env` file
5. Add your Auth0 credentials to `.env`

### Cloudflare Access (Enterprise)
1. Set up Cloudflare Access on your domain
2. Configure identity providers (Google, GitHub, etc.)
3. Set `AUTH_METHOD=cloudflare_access` in your `.env` file
4. See [CLOUDFLARE_ACCESS_SETUP.md](CLOUDFLARE_ACCESS_SETUP.md) for detailed setup

## Acknowledgements

- **Community**: Contributors and testers
- **Cloudflare**: For their excellent API and services
- **Auth0**: For robust authentication infrastructure
- **Bootstrap Team**: For responsive UI components
- **Flask Community**: For the excellent web framework

- **AND CLAUDE & WINDSURF, without whom this would not exist (or potentially destroy your site(s) - use at your own risk, like I do!
