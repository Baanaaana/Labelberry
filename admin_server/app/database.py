import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from contextlib import contextmanager
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PiDevice, PrintJob, PiMetrics, ErrorLog, PiConfig


logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "/var/lib/labelberry/db.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table for authentication
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create API keys table for admin server API access
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    permissions TEXT DEFAULT 'print'
                )
            """)
            
            # Create default admin user if not exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                import hashlib
                # Hash the default password
                password_hash = hashlib.sha256("admin123".encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("admin", password_hash)
                )
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pis (
                    id TEXT PRIMARY KEY,
                    friendly_name TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    location TEXT,
                    printer_model TEXT,
                    status TEXT DEFAULT 'offline',
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pi_id TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pi_id) REFERENCES pis (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS print_jobs (
                    id TEXT PRIMARY KEY,
                    pi_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    zpl_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (pi_id) REFERENCES pis (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pi_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    memory_usage REAL,
                    queue_size INTEGER,
                    jobs_completed INTEGER,
                    jobs_failed INTEGER,
                    printer_status TEXT,
                    uptime_seconds INTEGER,
                    FOREIGN KEY (pi_id) REFERENCES pis (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id TEXT PRIMARY KEY,
                    pi_id TEXT NOT NULL,
                    error_type TEXT,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    traceback TEXT,
                    FOREIGN KEY (pi_id) REFERENCES pis (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pis_api_key ON pis (api_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_print_jobs_pi_id ON print_jobs (pi_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_pi_id ON metrics (pi_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_pi_id ON error_logs (pi_id)")
            
        logger.info(f"Database initialized at {self.db_path}")
    
    def register_pi(self, device: PiDevice) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO pis (id, friendly_name, api_key, location, printer_model, status, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    device.id,
                    device.friendly_name,
                    device.api_key,
                    device.location,
                    device.printer_model,
                    device.status,
                    datetime.now(timezone.utc)
                ))
                
                if device.config:
                    cursor.execute("""
                        INSERT INTO configurations (pi_id, config_json)
                        VALUES (?, ?)
                    """, (device.id, json.dumps(device.config.model_dump())))
                
                return True
        except Exception as e:
            logger.error(f"Failed to register Pi: {e}")
            return False
    
    def get_pi_by_id(self, pi_id: str) -> Optional[PiDevice]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM pis WHERE id = ?", (pi_id,))
                row = cursor.fetchone()
                
                if row:
                    return PiDevice(
                        id=row['id'],
                        friendly_name=row['friendly_name'],
                        api_key=row['api_key'],
                        location=row['location'],
                        printer_model=row['printer_model'],
                        status=row['status'],
                        last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get Pi by ID: {e}")
            return None
    
    def get_pi_by_api_key(self, api_key: str) -> Optional[PiDevice]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM pis WHERE api_key = ?", (api_key,))
                row = cursor.fetchone()
                
                if row:
                    return PiDevice(
                        id=row['id'],
                        friendly_name=row['friendly_name'],
                        api_key=row['api_key'],
                        location=row['location'],
                        printer_model=row['printer_model'],
                        status=row['status'],
                        last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get Pi by API key: {e}")
            return None
    
    def get_all_pis(self) -> List[PiDevice]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM pis ORDER BY friendly_name")
                rows = cursor.fetchall()
                
                pis = []
                for row in rows:
                    pis.append(PiDevice(
                        id=row['id'],
                        friendly_name=row['friendly_name'],
                        api_key=row['api_key'],
                        location=row['location'],
                        printer_model=row['printer_model'],
                        status=row['status'],
                        last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None
                    ))
                return pis
        except Exception as e:
            logger.error(f"Failed to get all Pis: {e}")
            return []
    
    def update_pi_status(self, pi_id: str, status: str):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Convert enum to string value if needed
                status_value = status.value if hasattr(status, 'value') else status
                # Use UTC with timezone awareness
                cursor.execute("""
                    UPDATE pis SET status = ?, last_seen = ? WHERE id = ?
                """, (status_value, datetime.now(timezone.utc), pi_id))
                logger.info(f"Updated Pi {pi_id} status to {status_value}")
        except Exception as e:
            logger.error(f"Failed to update Pi status: {e}")
    
    def update_last_seen(self, pi_id: str):
        """Update only the last_seen timestamp for a Pi"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Use UTC with timezone awareness
                cursor.execute("""
                    UPDATE pis SET last_seen = ? WHERE id = ?
                """, (datetime.now(timezone.utc), pi_id))
                logger.debug(f"Updated last_seen for Pi {pi_id}")
        except Exception as e:
            logger.error(f"Failed to update last_seen for Pi {pi_id}: {e}")
    
    def delete_pi(self, pi_id: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete related data first (cascade delete)
                cursor.execute("DELETE FROM metrics WHERE pi_id = ?", (pi_id,))
                cursor.execute("DELETE FROM print_jobs WHERE pi_id = ?", (pi_id,))
                cursor.execute("DELETE FROM error_logs WHERE pi_id = ?", (pi_id,))
                cursor.execute("DELETE FROM configurations WHERE pi_id = ?", (pi_id,))
                
                # Delete the Pi record
                cursor.execute("DELETE FROM pis WHERE id = ?", (pi_id,))
                
                logger.info(f"Deleted Pi {pi_id} and all related data")
                return True
        except Exception as e:
            logger.error(f"Failed to delete Pi: {e}")
            return False
    
    def update_pi_config(self, pi_id: str, config: Dict[str, Any]) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO configurations (pi_id, config_json)
                    VALUES (?, ?)
                """, (pi_id, json.dumps(config)))
                return True
        except Exception as e:
            logger.error(f"Failed to update Pi config: {e}")
            return False
    
    def get_pi_config(self, pi_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT config_json FROM configurations 
                    WHERE pi_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT 1
                """, (pi_id,))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row['config_json'])
                return None
        except Exception as e:
            logger.error(f"Failed to get Pi config: {e}")
            return None
    
    def save_print_job(self, job: PrintJob):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO print_jobs 
                    (id, pi_id, status, zpl_source, created_at, started_at, completed_at, error_message, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    job.pi_id,
                    job.status,
                    job.zpl_source,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                    job.error_message,
                    job.retry_count
                ))
        except Exception as e:
            logger.error(f"Failed to save print job: {e}")
    
    def get_print_jobs(self, pi_id: str, limit: int = 100) -> List[PrintJob]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM print_jobs 
                    WHERE pi_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (pi_id, limit))
                rows = cursor.fetchall()
                
                jobs = []
                for row in rows:
                    jobs.append(PrintJob(
                        id=row['id'],
                        pi_id=row['pi_id'],
                        status=row['status'],
                        zpl_source=row['zpl_source'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                        completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                        error_message=row['error_message'],
                        retry_count=row['retry_count']
                    ))
                return jobs
        except Exception as e:
            logger.error(f"Failed to get print jobs: {e}")
            return []
    
    def save_metrics(self, metrics: PiMetrics):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO metrics 
                    (pi_id, timestamp, cpu_usage, memory_usage, queue_size, jobs_completed, jobs_failed, printer_status, uptime_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.pi_id,
                    metrics.timestamp,
                    metrics.cpu_usage,
                    metrics.memory_usage,
                    metrics.queue_size,
                    metrics.jobs_completed,
                    metrics.jobs_failed,
                    metrics.printer_status,
                    metrics.uptime_seconds
                ))
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def get_metrics(self, pi_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM metrics 
                    WHERE pi_id = ? 
                    AND timestamp > datetime('now', '-' || ? || ' hours')
                    ORDER BY timestamp DESC
                """, (pi_id, hours))
                rows = cursor.fetchall()
                
                metrics = []
                for row in rows:
                    metrics.append(dict(row))
                return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    def save_error_log(self, error: ErrorLog):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO error_logs (id, pi_id, error_type, message, timestamp, traceback)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    error.id,
                    error.pi_id,
                    error.error_type,
                    error.message,
                    error.timestamp,
                    error.traceback
                ))
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")
    
    def get_error_logs(self, pi_id: str, limit: int = 100) -> List[ErrorLog]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM error_logs 
                    WHERE pi_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (pi_id, limit))
                rows = cursor.fetchall()
                
                errors = []
                for row in rows:
                    errors.append(ErrorLog(
                        id=row['id'],
                        pi_id=row['pi_id'],
                        error_type=row['error_type'],
                        message=row['message'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        traceback=row['traceback']
                    ))
                return errors
        except Exception as e:
            logger.error(f"Failed to get error logs: {e}")
            return []
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) as total FROM pis")
                total_pis = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as online FROM pis WHERE status = 'online'")
                online_pis = cursor.fetchone()['online']
                
                cursor.execute("""
                    SELECT COUNT(*) as total FROM print_jobs 
                    WHERE created_at > datetime('now', '-24 hours')
                """)
                jobs_24h = cursor.fetchone()['total']
                
                cursor.execute("""
                    SELECT COUNT(*) as failed FROM print_jobs 
                    WHERE status = 'failed' AND created_at > datetime('now', '-24 hours')
                """)
                failed_24h = cursor.fetchone()['failed']
                
                return {
                    "total_pis": total_pis,
                    "online_pis": online_pis,
                    "offline_pis": total_pis - online_pis,
                    "jobs_24h": jobs_24h,
                    "failed_24h": failed_24h,
                    "success_rate": ((jobs_24h - failed_24h) / jobs_24h * 100) if jobs_24h > 0 else 100
                }
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {}
    
    def verify_user(self, username: str, password: str) -> bool:
        """Verify user credentials"""
        try:
            import hashlib
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT password_hash FROM users WHERE username = ?",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    return row['password_hash'] == password_hash
                return False
        except Exception as e:
            logger.error(f"Failed to verify user: {e}")
            return False
    
    def update_user_password(self, username: str, new_password: str) -> bool:
        """Update user password"""
        try:
            import hashlib
            with self.get_connection() as conn:
                cursor = conn.cursor()
                password_hash = hashlib.sha256(new_password.encode()).hexdigest()
                cursor.execute(
                    "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
                    (password_hash, username)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update user password: {e}")
            return False
    
    def update_username(self, old_username: str, new_username: str) -> bool:
        """Update username"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Check if new username already exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (new_username,))
                if cursor.fetchone()[0] > 0:
                    return False  # Username already exists
                
                cursor.execute(
                    "UPDATE users SET username = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
                    (new_username, old_username)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update username: {e}")
            return False
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user details"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, created_at, updated_at FROM users WHERE username = ?",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    def has_default_credentials(self) -> bool:
        """Check if default admin/admin123 credentials exist"""
        try:
            import hashlib
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Check if admin user exists with default password
                default_password_hash = hashlib.sha256("admin123".encode()).hexdigest()
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE username = 'admin' AND password_hash = ?",
                    (default_password_hash,)
                )
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Failed to check default credentials: {e}")
            return False
    
    def create_api_key(self, name: str, description: str, created_by: str) -> Optional[str]:
        """Create a new API key"""
        try:
            import secrets
            import hashlib
            
            # Generate a secure random API key
            api_key = f"labk_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO api_keys (key_hash, name, description, created_by)
                    VALUES (?, ?, ?, ?)
                """, (key_hash, name, description, created_by))
                
                # Return the unhashed key (only shown once)
                return api_key
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return None
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify an API key and update last_used timestamp"""
        try:
            import hashlib
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if key exists and is active
                cursor.execute("""
                    SELECT id FROM api_keys 
                    WHERE key_hash = ? AND is_active = 1
                """, (key_hash,))
                
                result = cursor.fetchone()
                if result:
                    # Update last_used timestamp
                    cursor.execute("""
                        UPDATE api_keys 
                        SET last_used = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (result['id'],))
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to verify API key: {e}")
            return False
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without the actual keys)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, description, created_by, created_at, 
                           last_used, is_active, permissions
                    FROM api_keys
                    ORDER BY created_at DESC
                """)
                
                keys = []
                for row in cursor.fetchall():
                    key_dict = dict(row)
                    # Format timestamps for display
                    if key_dict['created_at']:
                        key_dict['created_at'] = datetime.fromisoformat(key_dict['created_at']).isoformat()
                    if key_dict['last_used']:
                        key_dict['last_used'] = datetime.fromisoformat(key_dict['last_used']).isoformat()
                    keys.append(key_dict)
                return keys
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return []
    
    def revoke_api_key(self, key_id: int) -> bool:
        """Revoke an API key"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE api_keys 
                    SET is_active = 0 
                    WHERE id = ?
                """, (key_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return False
    
    def delete_api_key(self, key_id: int) -> bool:
        """Delete an API key permanently"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete API key: {e}")
            return False