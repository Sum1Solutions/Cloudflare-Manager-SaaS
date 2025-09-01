"""
Synchronization manager for keeping local database in sync with Cloudflare.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
try:
    from db_util import get_database_connection
except ImportError:
    from .db_util import get_database_connection
try:
    from cloudflare_api import CloudflareAPI, convert_to_edt
except ImportError:
    from .cloudflare_api import CloudflareAPI, convert_to_edt

logger = logging.getLogger(__name__)

class SyncManager:
    """Manages synchronization between Cloudflare and local database."""
    
    def __init__(self, cf_api: Optional[CloudflareAPI] = None):
        """Initialize the sync manager with an optional Cloudflare API client."""
        self.cf_api = cf_api or CloudflareAPI()
        self.sync_progress = {
            'syncing': False,
            'current_phase': '',
            'zones_processed': 0,
            'total_zones': 0,
            'current_zone': '',
            'start_time': None
        }
    
    def sync_all_zones(self) -> bool:
        """
        Synchronize all zones and their DNS records from Cloudflare.
        Returns True if all zones were synced successfully, False otherwise.
        """
        try:
            # Initialize progress tracking
            self.sync_progress = {
                'syncing': True,
                'current_phase': 'Fetching zones from Cloudflare...',
                'zones_processed': 0,
                'total_zones': 0,
                'current_zone': '',
                'start_time': datetime.now()
            }
            
            # Get all zones from Cloudflare
            logger.info("Starting zone synchronization from Cloudflare...")
            zones = self.cf_api.get_all_zones()
            
            if not zones:
                logger.error("No zones found in Cloudflare account")
                self.sync_progress['syncing'] = False
                return False
                
            logger.info(f"Fetched {len(zones)} zones from Cloudflare")
            self.sync_progress['total_zones'] = len(zones)
            self.sync_progress['current_phase'] = 'Updating zones in database...'
            
            # Update zones in the database
            if not self._update_zones(zones):
                logger.error("Failed to update zones in database")
                self.sync_progress['syncing'] = False
                return False
            
            # Update DNS records and Analytics for each zone
            self.sync_progress['current_phase'] = 'Syncing DNS records, Analytics, and DNSSEC status...'
            success_count = 0
            failure_count = 0
            dnssec_checked = 0
            
            for i, zone in enumerate(zones):
                # Check if sync was cancelled
                if not self.sync_progress.get('syncing', False):
                    logger.info("Sync operation cancelled by user")
                    return False
                
                zone_id = zone['id']
                zone_name = zone.get('name', 'unknown')
                self.sync_progress['current_zone'] = zone_name
                self.sync_progress['zones_processed'] = i
                
                logger.info(f"Syncing zone {i+1}/{len(zones)}: {zone_name} ({zone_id})")
                
                try:
                    # Sync DNS records
                    dns_success = self.sync_zone_dns(zone_id)
                    
                    # Sync Analytics data
                    analytics_success = self._sync_zone_analytics(zone_id)
                    
                    # Check DNSSEC status (non-blocking)
                    dnssec_checked += self._check_zone_dnssec(zone_id, zone_name)
                    
                    if dns_success and analytics_success:
                        success_count += 1
                        logger.info(f"Successfully synced zone {zone_name}")
                    else:
                        failure_count += 1
                        logger.error(f"Failed to sync zone {zone_name}")
                        
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Error syncing zone {zone_name}: {str(e)}", exc_info=True)
                    continue
            
            # Update last sync timestamp for all synced zones
            self.sync_progress['current_phase'] = 'Finalizing sync...'
            self._update_last_sync_timestamp()
            
            # Mark sync as complete
            self.sync_progress['syncing'] = False
            self.sync_progress['zones_processed'] = len(zones)
            
            logger.info(f"Sync completed: {success_count} zones synced successfully, {failure_count} failed, {dnssec_checked} DNSSEC statuses checked")
            return failure_count == 0
            
        except Exception as e:
            logger.error(f"Critical error during zone sync: {e}", exc_info=True)
            self.sync_progress['syncing'] = False
            return False
            
    def _update_last_sync_timestamp(self):
        """Update the last_updated timestamp for all zones."""
        try:
            conn = get_database_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE zones 
                SET last_updated = CURRENT_TIMESTAMP
                WHERE last_updated < datetime('now', '-1 minute') 
                   OR last_updated IS NULL
            """)
            conn.commit()
            logger.info(f"Updated last_updated timestamp for {cursor.rowcount} zones")
            return True
        except Exception as e:
            logger.error(f"Error updating last_updated timestamps: {e}")
            return False
    
    def sync_zone_dns(self, zone_id: str) -> bool:
        """Synchronize DNS records for a specific zone."""
        try:
            # Get zone name for better logging
            conn = get_database_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM zones WHERE id = ?', (zone_id,))
            result = cursor.fetchone()
            zone_name = result['name'] if result else 'unknown'
            conn.close()
            
            # Get DNS records from Cloudflare
            records = self.cf_api.get_zone_dns_records(zone_id)
            logger.info(f"Fetched {len(records)} DNS records for zone {zone_name} ({zone_id})")
            
            if not records:
                logger.warning(f"No DNS records returned from Cloudflare API for zone {zone_name} ({zone_id})")
            
            # Update records in the database
            success = self._update_dns_records(zone_id, records)
            
            if success:
                logger.info(f"Successfully updated {len(records)} DNS records for zone {zone_name}")
            else:
                logger.error(f"Failed to update DNS records in database for zone {zone_name}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to sync DNS records for zone {zone_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _update_zones(self, zones: List[Dict[str, Any]]) -> bool:
        """
        Update the zones in the database with the latest data from Cloudflare.
        Returns True if all zones were updated successfully, False otherwise.
        """
        if not zones:
            logger.warning("No zones provided for update")
            return False
            
        conn = None
        updated_count = 0
        inserted_count = 0
        error_count = 0
        
        try:
            conn = get_database_connection()
            cursor = conn.cursor()
            
            # Get existing zone IDs for comparison
            cursor.execute('SELECT id FROM zones')
            # Convert to list first to avoid cursor issues
            rows = cursor.fetchall()
            # Handle both dict-style and tuple-style rows
            if rows and hasattr(rows[0], 'keys'):  # If rows are dict-like
                existing_zone_ids = {row['id'] for row in rows}
            else:  # If rows are tuple-like
                existing_zone_ids = {row[0] for row in rows}
            current_zone_ids = set()
            
            for zone in zones:
                try:
                    # Prepare zone data with proper defaults
                    zone_id = zone.get('id')
                    if not zone_id:
                        logger.warning("Skipping zone with missing ID")
                        error_count += 1
                        continue
                        
                    current_zone_ids.add(zone_id)
                    zone_name = zone.get('name', '')
                    account = zone.get('account', {})
                    
                    # Prepare values for insertion/update
                    values = {
                        'id': zone_id,
                        'name': zone_name,
                        'status': zone.get('status', ''),
                        'type': zone.get('type', ''),
                        'plan_name': zone.get('plan', {}).get('name', ''),
                        'name_servers': ','.join(zone.get('name_servers') or []),
                        'original_name_servers': ','.join(zone.get('original_name_servers') or []),
                        'created_on': zone.get('created_on', ''),
                        'modified_on': zone.get('modified_on', ''),
                        'account_id': account.get('id', ''),
                        'account_name': account.get('name', ''),
                        'owner_email': zone.get('owner', {}).get('email', ''),
                        'activated_on': zone.get('activated_on', '')
                    }
                    
                    # Check if zone exists
                    cursor.execute('SELECT id FROM zones WHERE id = ?', (zone_id,))
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        # Update existing zone
                        set_clause = ', '.join(f"{k} = ?" for k in values.keys())
                        query = f"""
                            UPDATE zones 
                            SET {set_clause}, last_updated = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """
                        cursor.execute(query, list(values.values()) + [zone_id])
                        updated_count += 1
                    else:
                        # Insert new zone
                        columns = ', '.join(values.keys())
                        placeholders = ', '.join('?' * len(values))
                        query = f"""
                            INSERT INTO zones ({columns}, last_updated)
                            VALUES ({placeholders}, CURRENT_TIMESTAMP)
                        """
                        cursor.execute(query, list(values.values()))
                        inserted_count += 1
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing zone {zone_id} ({zone_name}): {e}", exc_info=True)
                    continue
            
            # Remove zones that no longer exist in Cloudflare
            deleted_zones = existing_zone_ids - current_zone_ids
            if deleted_zones:
                placeholders = ', '.join('?' * len(deleted_zones))
                cursor.execute(
                    f'DELETE FROM zones WHERE id IN ({placeholders})',
                    list(deleted_zones)
                )
                logger.info(f"Removed {len(deleted_zones)} zones that no longer exist in Cloudflare")
            
            conn.commit()
            logger.info(f"Zone update complete: {inserted_count} inserted, {updated_count} updated, {len(deleted_zones)} deleted, {error_count} errors")
            return error_count == 0
            
        except Exception as e:
            logger.error(f"Critical error during zone updates: {e}", exc_info=True)
            if conn:
                conn.rollback()
            return False
            
        finally:
            if conn:
                conn.close()
    
    def _sync_zone_analytics(self, zone_id: str) -> bool:
        """Sync Analytics data for a specific zone."""
        try:
            # Get Analytics data from Cloudflare
            analytics = self.cf_api.get_zone_analytics(zone_id)
            
            # Update the zone's Analytics data in the database
            conn = get_database_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE zones 
                SET analytics_requests = ?, 
                    analytics_bandwidth = ?, 
                    analytics_threats = ?,
                    analytics_updated = ?
                WHERE id = ?
            """, (
                analytics['requests'],
                analytics['bandwidth'], 
                analytics['threats'],
                analytics['updated'],
                zone_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated Analytics for zone {zone_id}: {analytics['requests']} requests, {analytics['bandwidth']} bytes, {analytics['threats']} threats")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync Analytics for zone {zone_id}: {e}")
            return False
    
    def _update_dns_records(self, zone_id: str, records: List[Dict[str, Any]]) -> bool:
        """Update DNS records in the local database."""
        conn = get_database_connection()
        cursor = conn.cursor()
        
        try:
            # Get existing record IDs for this zone
            cursor.execute(
                'SELECT id FROM dns_records WHERE zone_id = ?',
                (zone_id,)
            )
            existing_record_ids = {row['id'] for row in cursor.fetchall()}
            logger.info(f"Found {len(existing_record_ids)} existing DNS records in database for zone {zone_id}")
            
            # Process each record
            current_record_ids = set()
            updated_count = 0
            inserted_count = 0
            
            for record in records:
                try:
                    record_id = record['id']
                    current_record_ids.add(record_id)
                    
                    # Prepare record data
                    record_data = {
                        'id': record_id,
                        'zone_id': zone_id,
                        'type': record.get('type', ''),
                        'name': record.get('name', ''),
                        'content': record.get('content', ''),
                        'ttl': record.get('ttl', 1),
                        'proxied': 1 if record.get('proxied', False) else 0,
                        'created_on': convert_to_edt(record.get('created_on', '')),
                        'modified_on': convert_to_edt(record.get('modified_on', '')),
                        'priority': record.get('priority')
                    }
                    
                    # Check if record exists
                    cursor.execute(
                        'SELECT 1 FROM dns_records WHERE id = ?',
                        (record_id,)
                    )
                    exists = cursor.fetchone() is not None
                    
                    if exists:
                        # Update existing record
                        set_clause = ', '.join(f"{k} = ?" for k in record_data.keys())
                        values = list(record_data.values())
                        query = f"""
                            UPDATE dns_records 
                            SET {set_clause}
                            WHERE id = ?
                        """
                        cursor.execute(query, values + [record_id])
                        updated_count += 1
                    else:
                        # Insert new record
                        columns = ', '.join(record_data.keys())
                        placeholders = ', '.join('?' * len(record_data))
                        values = list(record_data.values())
                        
                        query = f"""
                            INSERT INTO dns_records ({columns})
                            VALUES ({placeholders})
                        """
                        cursor.execute(query, values)
                        inserted_count += 1
                        
                except Exception as record_error:
                    logger.error(f"Error processing DNS record {record.get('id', 'unknown')}: {record_error}")
                    continue  # Skip this record but continue with others
            
            # Remove records that no longer exist in Cloudflare
            deleted_records = existing_record_ids - current_record_ids
            deleted_count = 0
            if deleted_records:
                placeholders = ', '.join('?' * len(deleted_records))
                cursor.execute(
                    f'DELETE FROM dns_records WHERE id IN ({placeholders})',
                    list(deleted_records)
                )
                deleted_count = len(deleted_records)
                logger.info(f"Removed {deleted_count} DNS records that no longer exist in Cloudflare")
            
            # Update the zone's last_updated timestamp
            cursor.execute(
                'UPDATE zones SET last_updated = ? WHERE id = ?',
                (datetime.utcnow().isoformat(), zone_id)
            )
            
            conn.commit()
            logger.info(f"DNS records sync summary for zone {zone_id}: {inserted_count} inserted, {updated_count} updated, {deleted_count} deleted")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update DNS records: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
        finally:
            conn.close()
    
    def _check_zone_dnssec(self, zone_id: str, zone_name: str) -> int:
        """
        Check DNSSEC status for a zone during sync. Returns 1 if checked, 0 if failed.
        Non-blocking - failures don't affect sync success.
        """
        try:
            dnssec_result = self.cf_api._make_request('GET', f'zones/{zone_id}/dnssec')
            dnssec_status = dnssec_result.get('result', {}).get('status', 'unknown')
            
            # Update zone record with DNSSEC status (add column if needed)
            conn = get_database_connection()
            try:
                cursor = conn.cursor()
                # Try to update DNSSEC status - add column if it doesn't exist
                try:
                    cursor.execute(
                        'UPDATE zones SET dnssec_status = ? WHERE id = ?',
                        (dnssec_status, zone_id)
                    )
                except sqlite3.OperationalError:
                    # Add column if it doesn't exist
                    cursor.execute('ALTER TABLE zones ADD COLUMN dnssec_status TEXT')
                    cursor.execute(
                        'UPDATE zones SET dnssec_status = ? WHERE id = ?',
                        (dnssec_status, zone_id)
                    )
                
                conn.commit()
                logger.debug(f"Updated DNSSEC status for {zone_name}: {dnssec_status}")
                return 1
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.debug(f"Could not check DNSSEC for zone {zone_name}: {e}")
            return 0


def sync_all_data():
    """Convenience function to sync all data from Cloudflare."""
    try:
        sync_mgr = SyncManager()
        success = sync_mgr.sync_all_zones()
        if success:
            logger.info("Successfully synchronized all zones and DNS records")
        else:
            logger.error("Failed to synchronize all data")
        return success
    except Exception as e:
        logger.error(f"Error during synchronization: {e}")
        return False
