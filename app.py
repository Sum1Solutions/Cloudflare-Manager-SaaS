from flask import Flask, render_template, redirect, url_for, Response, jsonify, request, flash, session
import requests
import os
import logging
import sqlite3
import csv
import io
import json
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from urllib.parse import quote_plus, urlencode

# Load environment variables
load_dotenv()

# Local imports
import db_util
from cloudflare_api import CloudflareAPI
from sync_manager import SyncManager, sync_all_data
from auth_manager import auth_manager

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app with custom template folder
app = Flask(__name__, template_folder='templates')

# Configuration - Production Security
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    logger.warning("SECRET_KEY not set! Using development key. CHANGE IN PRODUCTION!")
    secret_key = 'dev-key-please-change-in-production'
app.secret_key = secret_key

# Auth0 Configuration (only if using Auth0)
oauth = None
auth0 = None
if os.getenv('AUTH_METHOD', 'auth0').lower() == 'auth0':
    oauth = OAuth(app)
    auth0 = oauth.register(
        'auth0',
        client_id=os.getenv('AUTH0_CLIENT_ID'),
        client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
        server_metadata_url=f'https://{os.getenv("AUTH0_DOMAIN")}/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid profile email'}
    )

# Custom template filters
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return "Never"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return value
    return value.strftime(format)

# Register the filter with the app
app.jinja_env.filters['datetimeformat'] = datetimeformat

# Flask Configuration
app.config['PER_PAGE'] = 50  # Number of items per page
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload

# Initialize Cloudflare API client
try:
    cf_api = CloudflareAPI()
    sync_manager = SyncManager(cf_api)
except Exception as e:
    logger.error(f"Failed to initialize Cloudflare client: {e}")
    cf_api = None
    sync_manager = None


# Utility Functions

# --- Global Error Handlers ---
@app.errorhandler(403)
def forbidden_error(error):
    logger.error(f"403 Forbidden: {error}")
    return render_template('error.html', code=403, message="Forbidden: You don't have permission to access this resource."), 403

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 Not Found: {error}")
    return render_template('error.html', code=404, message="Page not found."), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    logger.error(f"405 Method Not Allowed: {error}")
    return render_template('error.html', code=405, message="Method not allowed for this endpoint."), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}")
    return render_template('error.html', code=500, message="An internal server error occurred."), 500

# --- END Global Error Handlers ---

class Pagination:
    """Pagination helper class with iter_pages method for templates."""
    def __init__(self, page, per_page, total):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        self.has_prev = page > 1
        self.has_next = page * per_page < total
        self.prev_num = page - 1 if page > 1 else None
        self.next_num = page + 1 if page * per_page < total else None
    
    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        """Iterates over the page numbers in the pagination."""
        last = 0
        for num in range(1, self.pages + 1):
            # If it's one of the first left_edge pages
            # or one of the last right_edge pages
            # or it's a page close to the current page
            if (num <= left_edge or
                (num > self.page - left_current - 1 and
                 num < self.page + right_current) or
                num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num

def get_pagination(page, per_page, total):
    """Helper function to create a Pagination object."""
    return Pagination(page, per_page, total)

def get_zones_from_db(page=1, per_page=50, search=None, status=None):
    """Fetch zones from the database with pagination and filtering."""
    conn = db_util.get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Build the query
        query = "SELECT * FROM zones WHERE 1=1"
        params = []
        
        if search:
            query += " AND (name LIKE ? OR account LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
            
        if status:
            query += " AND status = ?"
            params.append(status)
            
        # Get total count for pagination
        count_query = "SELECT COUNT(*) as count FROM (" + query + ") AS count_query"
        logger.info(f"Count query: {count_query}, params: {params}")
        cursor.execute(count_query, params)
        result = cursor.fetchone()
        logger.info(f"Count result: {result}")
        total = result['count'] if result else 0
        logger.info(f"Total count from database: {total}")
        
        # Add pagination
        query += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        
        # Execute the query
        logger.info(f"Final query: {query}, params: {params}")
        cursor.execute(query, params)
        zones = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Fetched {len(zones)} zones from database")
        
        # Get pagination info
        pagination = get_pagination(page, per_page, total)
        
        return zones, pagination
        
    except Exception as e:
        logger.error(f"Error fetching zones from database: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return [], get_pagination(page, per_page, 0)
    finally:
        conn.close()

def get_zone_dns_records(zone_id):
    """Get DNS records for a specific zone from the database."""
    conn = db_util.get_database_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM dns_records WHERE zone_id = ? ORDER BY type, name',
            (zone_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching DNS records: {e}")
        return []
    finally:
        conn.close()

# Cloudflare API functions

def get_zones_with_params(params):
    """Fetch zones from Cloudflare based on provided parameters in a paginated manner."""
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        'X-Auth-Email': CLOUDFLARE_EMAIL,
        'X-Auth-Key': CLOUDFLARE_KEY
    }

    all_zones = []
    page = 0
    total_pages = 1  # Start with 1 for the first iteration
    max_iterations = 10  # Avoid potential infinite loops

    while page < total_pages and page < max_iterations:
        page += 1  # Increment page number
        params['page'] = page

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            result = response.json()
            all_zones.extend(result.get('result', []))

            # Update total_pages based on result_info from Cloudflare
            total_pages = result.get('result_info', {}).get('total_pages', 1)
        else:
            # Log error messages only in debug mode
            if app.debug:
                logging.error(f"Failed to fetch zones for page {page}. Reason: {response.text}")

    return all_zones

def get_all_zones():
    """Retrieve all zones from Cloudflare."""
    return get_zones_with_params({'per_page': 50})

def get_paused_zones():
    """Retrieve paused zones from Cloudflare."""
    return get_zones_with_params({'status': 'paused', 'per_page': 50})


# Authentication decorator
# Use the configurable auth manager
def require_auth(f):
    return auth_manager.require_auth_decorator(f)

# Authentication routes
@app.route('/login')
def login():
    """Handle login for configured auth method."""
    auth_method = os.getenv('AUTH_METHOD', 'auth0').lower()
    
    # If user is already authenticated, redirect to dashboard
    if auth_manager.is_authenticated():
        return redirect(url_for('index'))
    
    if auth_method == 'cloudflare_access':
        # For Cloudflare Access, show info page (user should already be authenticated by Access)
        return render_template('cloudflare_access_info.html')
    
    elif auth_method == 'auth0':
        # Auth0 flow
        if request.args.get('auth') == 'true' and auth0:
            return auth0.authorize_redirect(redirect_uri=url_for('callback', _external=True))
        return render_template('login.html', auth_method='auth0')
    
    else:
        return jsonify({'error': 'Invalid auth method configured'}), 500

@app.route('/logout')
def logout():
    """Handle logout for configured auth method."""
    auth_method = os.getenv('AUTH_METHOD', 'auth0').lower()
    session.clear()
    
    if auth_method == 'cloudflare_access':
        # For Cloudflare Access, redirect to Access logout
        domain = request.headers.get('Host', 'localhost')
        return redirect(f'https://{domain}/cdn-cgi/access/logout')
    
    elif auth_method == 'auth0':
        # Auth0 logout
        return redirect(
            f'https://{os.getenv("AUTH0_DOMAIN")}/v2/logout?' + 
            urlencode({
                'returnTo': url_for('logged_out', _external=True),
                'client_id': os.getenv('AUTH0_CLIENT_ID')
            }, quote_via=quote_plus)
        )
    
    else:
        return redirect(url_for('logged_out'))

@app.route('/logged_out')
def logged_out():
    """Show logout confirmation page."""
    return render_template('logged_out.html')

@app.route('/health')
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Basic health checks
        checks = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.2.0',
            'auth0_configured': bool(os.getenv('AUTH0_DOMAIN')),
            'cloudflare_configured': bool(os.getenv('CLOUDFLARE_API_KEY'))
        }
        
        # Optional database connectivity check
        try:
            conn = db_util.get_database_connection()
            conn.close()
            checks['database'] = 'connected'
        except Exception:
            checks['database'] = 'error'
            checks['status'] = 'degraded'
        
        return jsonify(checks), 200 if checks['status'] == 'healthy' else 503
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/callback')
def callback():
    """Handle Auth0 callback."""
    auth_method = os.getenv('AUTH_METHOD', 'auth0').lower()
    
    if auth_method != 'auth0' or not auth0:
        return jsonify({'error': 'Auth0 callback not available in current auth mode'}), 400
    
    try:
        token = auth0.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            session['user_info'] = {
                'user_id': user_info.get('sub'),
                'name': user_info.get('name'),
                'email': user_info.get('email'),
                'picture': user_info.get('picture')
            }
            
            # For now, allow access to all sites for any authenticated user
            # Later we can add tier-based restrictions here
            session['allowed_sites'] = ['*']  # All sites
            session['subscription_tier'] = 'admin'  # Default admin access
            
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed - no user info received', 'error')
            return redirect(url_for('login'))
            
    except Exception as e:
        logger.error(f"Auth0 callback error: {e}")
        flash('Login failed - authentication error', 'error')
        return redirect(url_for('login'))

# Flask routes

@app.route('/')
@require_auth
def index():
    """Render the main dashboard with all zones using DataTables."""
    # Get zones from database
    zones, _ = get_zones_from_db(per_page=1000)  # Get all zones for DataTables
    
    # Get last sync time from zones table
    conn = db_util.get_database_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(last_updated) as last_sync FROM zones')
        last_sync = cursor.fetchone()['last_sync']
    except Exception as e:
        logger.error(f"Error getting last sync time: {e}")
        last_sync = None
    finally:
        conn.close()

    return render_template(
        'domains_combined.html',
        zones=zones,
        last_sync=last_sync,
        account_id=os.getenv('CLOUDFLARE_ACCOUNT_ID')
    )

@app.route('/sync', methods=['POST'])
@require_auth
def sync_data():
    """Synchronize data with Cloudflare."""
    if not sync_manager:
        flash('Cloudflare client not properly initialized', 'danger')
        return redirect(url_for('index'))
    
    # Check if sync is already running
    if sync_manager.sync_progress.get('syncing', False):
        return jsonify({'success': False, 'error': 'Sync already in progress'}), 409
    
    try:
        success = sync_manager.sync_all_zones()
        if success:
            flash('Successfully synchronized with Cloudflare', 'success')
        else:
            flash('Failed to synchronize all data', 'warning')
    except Exception as e:
        logger.error(f"Error during sync: {e}")
        flash(f'Error during synchronization: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/api/sync/progress')
@require_auth
def api_sync_progress():
    """Get current progress of sync operation."""
    if not sync_manager:
        return jsonify({'error': 'Sync manager not initialized'}), 500
    
    progress = sync_manager.sync_progress.copy()
    
    # Calculate elapsed time
    elapsed = 0
    if progress.get('start_time'):
        elapsed = (datetime.now() - progress['start_time']).total_seconds()
    
    return jsonify({
        'syncing': progress.get('syncing', False),
        'current_phase': progress.get('current_phase', ''),
        'zones_processed': progress.get('zones_processed', 0),
        'total_zones': progress.get('total_zones', 0),
        'current_zone': progress.get('current_zone', ''),
        'elapsed_seconds': elapsed
    })

@app.route('/api/sync/cancel', methods=['POST'])
@require_auth
def api_sync_cancel():
    """Cancel the current sync operation."""
    if not sync_manager:
        return jsonify({'error': 'Sync manager not initialized'}), 500
    
    try:
        # Mark sync as cancelled
        sync_manager.sync_progress['syncing'] = False
        sync_manager.sync_progress['current_phase'] = 'Cancelled by user'
        
        logger.info("Sync operation cancelled by user")
        return jsonify({'success': True, 'message': 'Sync cancelled successfully'})
        
    except Exception as e:
        logger.error(f"Error cancelling sync: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zones/<zone_id>/dns-records')
@require_auth
def api_zone_dns_records(zone_id):
    """API endpoint to get DNS records for a zone."""
    try:
        records = get_zone_dns_records(zone_id)
        return jsonify({
            'success': True,
            'records': records
        })
    except Exception as e:
        logger.error(f"Error getting DNS records: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/pending')
@require_auth
def pending():
    """Render pending zones."""
    zones, pagination = get_zones_from_db(
        status='pending',
        page=request.args.get('page', 1, type=int),
        per_page=app.config['PER_PAGE']
    )
    return render_template(
        'domains_combined.html',
        zones=zones,
        pagination=pagination,
        status_filter='pending',
        title='Pending Zones'
    )

@app.route('/reactivate')
@require_auth
def reactivate():
    """Render reactivate zones."""
    zones, pagination = get_zones_from_db(
        status='inactive',
        page=request.args.get('page', 1, type=int),
        per_page=app.config['PER_PAGE']
    )
    return render_template(
        'domains_combined.html',
        zones=zones,
        pagination=pagination,
        status_filter='inactive',
        title='Inactive Zones'
    )

def analyze_zone_dns_records(zone_id, zone):
    """Analyze DNS records for a zone to determine DNSSEC recommendation priority."""
    try:
        # Get DNS records for this zone from the API
        dns_records_response = cf_api._make_request('GET', f'zones/{zone_id}/dns_records')
        dns_records = dns_records_response.get('result', [])
        
        # Categorize DNS records by type
        record_types = set()
        active_record_types = set()
        security_records = []
        
        for record in dns_records:
            record_type = record.get('type', '').upper()
            record_types.add(record_type)
            
            # Check for records that indicate active usage
            if record_type in ['A', 'AAAA', 'CNAME']:
                active_record_types.add(record_type)
            elif record_type == 'MX':
                active_record_types.add('MX')
            elif record_type == 'TXT':
                content = record.get('content', '').lower()
                if any(x in content for x in ['v=spf1', 'v=dkim1', 'v=dmarc1', 'dmarc', 'spf']):
                    security_records.append(record_type)
                    active_record_types.add('TXT_SECURITY')
            elif record_type == 'SRV':
                active_record_types.add('SRV')
        
        # Determine recommendation level
        if active_record_types:
            if any(x in active_record_types for x in ['A', 'AAAA', 'MX', 'TXT_SECURITY']):
                recommendation = 'Highly Recommended'
                activity_level = 'High'
            elif any(x in active_record_types for x in ['CNAME', 'SRV']):
                recommendation = 'Recommended' 
                activity_level = 'Medium'
            else:
                recommendation = 'Consider'
                activity_level = 'Low'
        else:
            recommendation = 'Optional'
            activity_level = 'Minimal'
        
        # Add analysis results to zone data
        zone_with_analysis = zone.copy()
        zone_with_analysis['dnssec_recommendation'] = recommendation
        zone_with_analysis['dns_activity_level'] = activity_level
        zone_with_analysis['dns_record_types'] = list(record_types)
        zone_with_analysis['active_record_types'] = list(active_record_types)
        zone_with_analysis['security_records'] = len(security_records) > 0
        
        return zone_with_analysis
        
    except Exception as e:
        logger.warning(f"Could not analyze DNS records for zone {zone.get('name', 'unknown')}: {e}")
        zone_with_analysis = zone.copy()
        zone_with_analysis['dnssec_recommendation'] = 'Unknown'
        zone_with_analysis['dns_activity_level'] = 'Unknown'
        zone_with_analysis['dns_record_types'] = []
        zone_with_analysis['active_record_types'] = []
        zone_with_analysis['security_records'] = False
        return zone_with_analysis

@app.route('/no_dnssec')
@require_auth
def no_dnssec():
    """Show loading page for DNSSEC check."""
    # Get total domain count to pass to loading page
    conn = db_util.get_database_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM zones')
        domain_count = cursor.fetchone()['count']
    except:
        domain_count = 400  # Fallback estimate
    finally:
        conn.close()
    
    return render_template('dnssec_loading.html', domain_count=domain_count)

# Global variable to track DNSSEC check progress
dnssec_check_progress = {
    'checking': False,
    'processed': 0,
    'total': 0,
    'without_dnssec': 0,
    'current_domain': '',
    'start_time': None
}

@app.route('/api/check-dnssec')
@require_auth
def api_check_dnssec():
    """API endpoint to check DNSSEC status for all zones."""
    global dnssec_check_progress
    
    if not cf_api:
        return jsonify({'success': False, 'error': 'Cloudflare client not initialized'}), 500
    
    # Prevent multiple simultaneous checks
    if dnssec_check_progress['checking']:
        return jsonify({'success': False, 'error': 'DNSSEC check already in progress'}), 409
    
    try:
        # Initialize progress tracking
        dnssec_check_progress = {
            'checking': True,
            'processed': 0,
            'total': 0,
            'without_dnssec': 0,
            'current_domain': '',
            'start_time': datetime.now()
        }
        
        # Get zones from database first
        zones_data, _ = get_zones_from_db(page=1, per_page=1000)
        
        no_dnssec_zones = []
        total_zones = len(zones_data)
        dnssec_check_progress['total'] = total_zones
        
        logger.info(f"Starting DNSSEC check for {total_zones} zones")
        
        # Check DNSSEC status for each zone via API
        for zone in zones_data:
            try:
                zone_id = zone['id']
                zone_name = zone.get('name', 'unknown')
                dnssec_check_progress['current_domain'] = zone_name
                
                dnssec_result = cf_api._make_request('GET', f'zones/{zone_id}/dnssec')
                
                # If DNSSEC is not active, add to list with DNS record analysis
                if dnssec_result.get('result', {}).get('status') != 'active':
                    # Analyze DNS records to determine recommendation priority
                    zone_with_analysis = analyze_zone_dns_records(zone_id, zone)
                    no_dnssec_zones.append(zone_with_analysis)
                    dnssec_check_progress['without_dnssec'] += 1
                    logger.info(f"Zone {zone_name} has no DNSSEC - Recommendation: {zone_with_analysis.get('dnssec_recommendation', 'Unknown')}")
                    
            except Exception as e:
                logger.warning(f"Could not check DNSSEC for zone {zone.get('name', 'unknown')}: {e}")
                # Add zone to list if we can't determine DNSSEC status
                zone_with_analysis = zone.copy()
                zone_with_analysis['dnssec_recommendation'] = 'Unknown'
                zone_with_analysis['dns_activity_level'] = 'Unknown'
                zone_with_analysis['dns_record_types'] = []
                no_dnssec_zones.append(zone_with_analysis)
                dnssec_check_progress['without_dnssec'] += 1
            
            dnssec_check_progress['processed'] += 1
            
            if dnssec_check_progress['processed'] % 10 == 0:  # Log progress every 10 zones
                logger.info(f"DNSSEC check progress: {dnssec_check_progress['processed']}/{total_zones} zones processed")
        
        logger.info(f"DNSSEC check completed: {len(no_dnssec_zones)} zones without DNSSEC out of {total_zones}")
        
        # Mark as complete
        dnssec_check_progress['checking'] = False
        
        return jsonify({
            'success': True,
            'zones': no_dnssec_zones,
            'total_checked': total_zones,
            'without_dnssec': len(no_dnssec_zones)
        })
        
    except Exception as e:
        logger.error(f"Error checking DNSSEC status: {e}")
        dnssec_check_progress['checking'] = False
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-dnssec/progress')
@require_auth
def api_check_dnssec_progress():
    """Get current progress of DNSSEC check."""
    global dnssec_check_progress
    
    elapsed = 0
    if dnssec_check_progress['start_time']:
        elapsed = (datetime.now() - dnssec_check_progress['start_time']).total_seconds()
    
    return jsonify({
        'checking': dnssec_check_progress['checking'],
        'processed': dnssec_check_progress['processed'],
        'total': dnssec_check_progress['total'],
        'without_dnssec': dnssec_check_progress['without_dnssec'],
        'current_domain': dnssec_check_progress['current_domain'],
        'elapsed_seconds': elapsed
    })

@app.route('/api/enable-dnssec-bulk', methods=['POST'])
@require_auth
def api_enable_dnssec_bulk():
    """API endpoint to bulk enable DNSSEC for multiple zones."""
    if not cf_api:
        return jsonify({'success': False, 'error': 'Cloudflare client not initialized'}), 500
    
    try:
        data = request.get_json()
        zone_ids = data.get('zone_ids', [])
        
        if not zone_ids:
            return jsonify({'success': False, 'error': 'No zone IDs provided'}), 400
        
        results = {
            'success': [],
            'failed': [],
            'total': len(zone_ids)
        }
        
        logger.info(f"Starting bulk DNSSEC enable for {len(zone_ids)} zones")
        
        for zone_id in zone_ids:
            try:
                # Get zone name for logging
                conn = db_util.get_database_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM zones WHERE id = ?', (zone_id,))
                zone_result = cursor.fetchone()
                zone_name = zone_result['name'] if zone_result else zone_id
                
                # Enable DNSSEC for this zone
                dnssec_result = cf_api._make_request('PATCH', f'zones/{zone_id}/dnssec', json={'status': 'active'})
                
                if dnssec_result.get('success'):
                    results['success'].append({'zone_id': zone_id, 'name': zone_name})
                    logger.info(f"Successfully enabled DNSSEC for zone {zone_name}")
                else:
                    error_msg = dnssec_result.get('errors', [{}])[0].get('message', 'Unknown error')
                    results['failed'].append({'zone_id': zone_id, 'name': zone_name, 'error': error_msg})
                    logger.warning(f"Failed to enable DNSSEC for zone {zone_name}: {error_msg}")
                    
            except Exception as e:
                results['failed'].append({'zone_id': zone_id, 'name': zone_name, 'error': str(e)})
                logger.error(f"Error enabling DNSSEC for zone {zone_id}: {e}")
        
        success_count = len(results['success'])
        failed_count = len(results['failed'])
        
        logger.info(f"Bulk DNSSEC enable completed: {success_count} successful, {failed_count} failed")
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': f"Enabled DNSSEC for {success_count} out of {len(zone_ids)} zones"
        })
        
    except Exception as e:
        logger.error(f"Error in bulk DNSSEC enable: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/zone/<zone_id>')
@require_auth
def zone_details(zone_id):
    """Show detailed information for a specific zone."""
    logger.info(f"[ZONE_DETAILS] Accessing zone details for zone_id: {zone_id}")
    conn = db_util.get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Get zone details
        query = "SELECT * FROM zones WHERE id = ?"
        logger.info(f"[ZONE_DETAILS] Executing query: {query} with params: [{zone_id}]")
        cursor.execute(query, [zone_id])
        zone = cursor.fetchone()
        logger.info(f"[ZONE_DETAILS] Query result: {zone}")
        
        if not zone:
            logger.warning(f"[ZONE_DETAILS] Zone not found for ID: {zone_id}")
            flash("Zone not found", "danger")
            return redirect(url_for('index'))
        
        # Get DNS records for this zone
        dns_query = "SELECT * FROM dns_records WHERE zone_id = ? ORDER BY type, name"
        logger.info(f"[ZONE_DETAILS] Executing DNS query: {dns_query} with params: [{zone_id}]")
        cursor.execute(dns_query, [zone_id])
        dns_records = [dict(row) for row in cursor.fetchall()]
        logger.info(f"[ZONE_DETAILS] Found {len(dns_records)} DNS records")
        
        logger.info(f"[ZONE_DETAILS] Rendering template with zone: {zone['name']} and {len(dns_records)} DNS records")
        return render_template(
            'zone_details.html',
            zone=zone,
            dns_records=dns_records
        )
    except Exception as e:
        logger.error(f"[ZONE_DETAILS] Error fetching zone details: {e}")
        import traceback
        logger.error(f"[ZONE_DETAILS] Traceback: {traceback.format_exc()}")
        flash("An error occurred while fetching zone details", "danger")
        return redirect(url_for('index'))
    finally:
        conn.close()

# Removed duplicate reactivate route

# Removed duplicate no_dnssec route

@app.route('/view_db')
@require_auth
def view_db():
    """
    Enhanced database overview with comprehensive statistics and insights.
    
    Provides detailed information about database structure, row counts,
    data distribution, and last update timestamps across all tables.
    """
    conn = sqlite3.connect('cloudflare_manager.db')
    cursor = conn.cursor()
    
    # Get database file size
    db_size = os.path.getsize('cloudflare_manager.db')
    
    # Fetch all table names in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [table[0] for table in cursor.fetchall()]
    
    tables = {}
    tables_metadata = {}
    total_rows = 0
    
    # Enhanced zone statistics
    zone_stats = {}
    dns_stats = {}
    
    for table_name in table_names:
        # For each table, fetch details of its columns
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [{"name": column[1], "type": column[2], "notnull": column[3], "default": column[4], "pk": column[5]} for column in cursor.fetchall()]
        tables[table_name] = columns
        
        # Fetch row count for each table
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        total_rows += row_count
        
        # Check for timestamp columns
        column_names = [column[1] for column in cursor.fetchall()]
        cursor.execute(f"PRAGMA table_info({table_name});")
        column_names = [column[1] for column in cursor.fetchall()]
        
        last_updated = None
        created_count = None
        
        if 'last_updated' in column_names:
            cursor.execute(f"SELECT MAX(last_updated) FROM {table_name}")
            last_updated = cursor.fetchone()[0]
        elif 'modified_on' in column_names:
            cursor.execute(f"SELECT MAX(modified_on) FROM {table_name}")
            last_updated = cursor.fetchone()[0]
        elif 'created_on' in column_names:
            cursor.execute(f"SELECT MAX(created_on) FROM {table_name}")
            last_updated = cursor.fetchone()[0]
        
        # Enhanced statistics for zones table
        if table_name == 'zones':
            cursor.execute("SELECT status, COUNT(*) FROM zones GROUP BY status")
            zone_stats['by_status'] = dict(cursor.fetchall())
            
            cursor.execute("SELECT plan_name, COUNT(*) FROM zones GROUP BY plan_name")
            zone_stats['by_plan'] = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM zones WHERE analytics_requests > 0")
            zone_stats['with_analytics'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(analytics_requests), AVG(analytics_bandwidth), AVG(analytics_threats) FROM zones WHERE analytics_requests > 0")
            analytics_avg = cursor.fetchone()
            zone_stats['avg_analytics'] = {
                'requests': analytics_avg[0] or 0,
                'bandwidth': analytics_avg[1] or 0,
                'threats': analytics_avg[2] or 0
            }
            
            cursor.execute("SELECT MAX(analytics_requests), MAX(analytics_bandwidth), MAX(analytics_threats) FROM zones")
            analytics_max = cursor.fetchone()
            zone_stats['max_analytics'] = {
                'requests': analytics_max[0] or 0,
                'bandwidth': analytics_max[1] or 0,
                'threats': analytics_max[2] or 0
            }
        
        # Enhanced statistics for dns_records table
        if table_name == 'dns_records':
            cursor.execute("SELECT type, COUNT(*) FROM dns_records GROUP BY type ORDER BY COUNT(*) DESC")
            dns_stats['by_type'] = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM dns_records WHERE proxied = 1")
            dns_stats['proxied_count'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT zone_id) FROM dns_records")
            dns_stats['zones_with_records'] = cursor.fetchone()[0]
        
        # Store the metadata
        tables_metadata[table_name] = {
            'row_count': row_count,
            'last_updated': last_updated,
            'column_count': len(columns),
            'columns': columns
        }
    
    # Database overview statistics
    db_overview = {
        'total_tables': len(table_names),
        'total_rows': total_rows,
        'db_size_mb': round(db_size / (1024 * 1024), 2),
        'zone_stats': zone_stats,
        'dns_stats': dns_stats
    }
    
    conn.close()
    
    return render_template('view_db.html', 
                         tables=tables, 
                         tables_metadata=tables_metadata,
                         db_overview=db_overview)

@app.route('/view_table_data/<table_name>')
@require_auth
def view_table_data(table_name):
    """Endpoint to view data for a specific table in the database."""
    conn = sqlite3.connect('cloudflare_manager.db')
    cursor = conn.cursor()
    
    # Fetch the column names for the table
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [{"name": column[1]} for column in cursor.fetchall()]
    
    # Fetch the data for the table
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    
    conn.close()
    
    return render_template('view_table_data.html', data=data, table_name=table_name, columns=columns)


@app.route('/save_to_db', methods=['POST'])
@require_auth
def save_to_db():
    """Save zones data to the database."""
    zones = get_all_zones()
    conn = sqlite3.connect('cloudflare_manager.db')
    cursor = conn.cursor()
    
    for zone in zones:
        # Ensure name_servers and original_name_servers are lists before joining
        name_servers = zone.get('name_servers')
        if not isinstance(name_servers, list):
            name_servers = []

        original_name_servers = zone.get('original_name_servers')
        if not isinstance(original_name_servers, list):
            original_name_servers = []

        cursor.execute('''
            INSERT OR REPLACE INTO zones (
                id, name, status, type, plan_name, name_servers, 
                original_name_servers, created_on, modified_on, auth_code_from_directnic, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            zone.get('id'),
            zone.get('name'),
            zone.get('status'),
            zone.get('type'),
            zone.get('plan', {}).get('name'),
            ", ".join(name_servers),
            ", ".join(original_name_servers),
            zone.get('created_on'),
            zone.get('modified_on'),
            ""  # Placeholder for auth_code_from_directnic, replace when you have the data
        ))
        
        # Update the last_updated timestamp for the modified row
        cursor.execute('''
            UPDATE zones SET last_updated = CURRENT_TIMESTAMP WHERE id = ?
        ''', (zone.get('id'),))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/export/domains.csv')
@require_auth
def export_domains_csv():
    """Export all domains as a CSV file."""
    zones = get_all_zones()
    
    # Create a StringIO object to write CSV data
    si = io.StringIO()
    cw = csv.writer(si)
    
    # Write CSV header
    cw.writerow(['Domain', 'Status', 'Created On', 'Name Servers'])
    
    # Write zone data
    for zone in zones:
        cw.writerow([
            zone.get('name', ''),
            zone.get('status', ''),
            zone.get('created_on', ''),
            ', '.join(zone.get('name_servers', []))
        ])
    
    # Create a response with the CSV data
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=cloudflare_domains.csv"}
    )

if __name__ == '__main__':
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize the database and run migrations
    db_util.setup_database()
    
    # Run the application - Production ready configuration
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')
    
    app.run(debug=debug_mode, host=host, port=port)