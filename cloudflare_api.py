"""
Cloudflare API Client for managing DNS and Zone operations.
Combines functionality from both cloudflare-manager and cloudflare_data_getter.
"""
import os
import requests
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloudflareAPI:
    """Client for interacting with Cloudflare's API."""
    
    def __init__(self, email: str = None, api_key: str = None, account_id: str = None):
        """
        Initialize the Cloudflare API client.
        
        Args:
            email: Cloudflare account email
            api_key: Cloudflare API key
            account_id: Cloudflare account ID
        """
        self.email = email or os.getenv('CLOUDFLARE_EMAIL')
        self.api_key = api_key or os.getenv('CLOUDFLARE_API_KEY')
        self.account_id = account_id or os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.base_url = 'https://api.cloudflare.com/client/v4'
        
        if not all([self.email, self.api_key]):
            raise ValueError("Missing required Cloudflare credentials. Set CLOUDFLARE_EMAIL and CLOUDFLARE_API_KEY environment variables.")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get the default headers for API requests."""
        return {
            'X-Auth-Email': self.email,
            'X-Auth-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make an authenticated request to the Cloudflare API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self.headers.copy()
        headers.update(kwargs.pop('headers', {}))
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_all_zones(self) -> List[Dict]:
        """Fetch all zones from Cloudflare."""
        zones = []
        page = 1
        per_page = 50
        
        while True:
            try:
                result = self._make_request(
                    'GET',
                    'zones',
                    params={'page': page, 'per_page': per_page}
                )
                
                zones.extend(result.get('result', []))
                
                # Check if there are more pages
                result_info = result.get('result_info', {})
                if page * per_page >= result_info.get('total_count', 0):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to fetch zones: {e}")
                break
                
        return zones
    
    def get_zone_dns_records(self, zone_id: str) -> List[Dict]:
        """Fetch all DNS records for a specific zone."""
        try:
            result = self._make_request(
                'GET',
                f'zones/{zone_id}/dns_records',
                params={'per_page': 100}  # Max per page
            )
            return result.get('result', [])
        except Exception as e:
            logger.error(f"Failed to fetch DNS records for zone {zone_id}: {e}")
            return []
    
    def get_zone_analytics(self, zone_id: str, **kwargs) -> Dict:
        """Fetch analytics data for a zone using GraphQL API (last 30 days summary)."""
        try:
            # Set default time range: last 30 days (GraphQL expects YYYY-MM-DD format)
            since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
            until = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # GraphQL query for zone analytics
            query = {
                "query": """
                query GetZoneAnalytics($zoneTag: String!, $since: String!, $until: String!) {
                  viewer {
                    zones(filter: {zoneTag: $zoneTag}) {
                      httpRequests1dGroups(
                        limit: 10,
                        filter: {
                          date_geq: $since,
                          date_leq: $until
                        }
                      ) {
                        sum {
                          requests
                          bytes
                          threats
                        }
                      }
                    }
                  }
                }
                """,
                "variables": {
                    "zoneTag": zone_id,
                    "since": kwargs.get('since', since),
                    "until": kwargs.get('until', until)
                }
            }
            
            result = self._make_request(
                'POST',
                'graphql',
                json=query
            )
            
            # Extract data from GraphQL response
            data = result.get('data', {})
            if data is None:
                logger.warning(f"No data in GraphQL response for zone {zone_id}")
                return {
                    'requests': 0,
                    'bandwidth': 0,
                    'threats': 0,
                    'updated': datetime.now(timezone.utc).isoformat()
                }
                
            viewer = data.get('viewer', {})
            zones = viewer.get('zones', [])
            
            if zones and len(zones) > 0:
                http_requests = zones[0].get('httpRequests1dGroups', [])
                if http_requests and len(http_requests) > 0:
                    totals = http_requests[0].get('sum', {})
                    return {
                        'requests': totals.get('requests', 0),
                        'bandwidth': totals.get('bytes', 0),
                        'threats': totals.get('threats', 0),
                        'updated': datetime.now(timezone.utc).isoformat()
                    }
            
            # If no data found, return zeros with updated timestamp
            return {
                'requests': 0,
                'bandwidth': 0,
                'threats': 0,
                'updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch analytics for zone {zone_id}: {e}")
            return {
                'requests': 0,
                'bandwidth': 0,
                'threats': 0,
                'updated': None
            }
    
    def update_dns_record(self, zone_id: str, record_id: str, data: Dict) -> Dict:
        """Update a DNS record."""
        return self._make_request(
            'PUT',
            f'zones/{zone_id}/dns_records/{record_id}',
            json=data
        )
    
    def create_dns_record(self, zone_id: str, data: Dict) -> Dict:
        """Create a new DNS record."""
        return self._make_request(
            'POST',
            f'zones/{zone_id}/dns_records',
            json=data
        )
    
    def delete_dns_record(self, zone_id: str, record_id: str) -> bool:
        """Delete a DNS record."""
        try:
            self._make_request(
                'DELETE',
                f'zones/{zone_id}/dns_records/{record_id}'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete DNS record {record_id}: {e}")
            return False


def convert_to_edt(iso_datetime: str) -> str:
    """
    Convert ISO 8601 datetime string to EDT timezone and format it.
    
    Args:
        iso_datetime: ISO 8601 formatted datetime string
        
    Returns:
        Formatted datetime string in EDT (MM/DD/YY HH:MM AM/PM)
    """
    if not iso_datetime:
        return ""
        
    try:
        # Parse the input datetime (handle both with and without timezone)
        if iso_datetime.endswith('Z'):
            dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(iso_datetime)
            
        # Convert to EDT (UTC-4)
        edt_offset = timedelta(hours=-4)
        edt_time = dt + edt_offset
        
        # Format as MM/DD/YY HH:MM AM/PM
        return edt_time.strftime('%m/%d/%y %I:%M %p')
    except ValueError as e:
        logger.warning(f"Failed to parse datetime '{iso_datetime}': {e}")
        return iso_datetime
