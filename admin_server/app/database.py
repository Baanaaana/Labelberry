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
    def __init__(self, db_path: str = None):
        import os
        if db_path is None:
            db_path = os.getenv('LABELBERRY_DB_PATH', '/var/lib/labelberry/db.sqlite')
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
            
            # Create label_sizes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS label_sizes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    width_mm INTEGER NOT NULL,
                    height_mm INTEGER NOT NULL,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(width_mm, height_mm)
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
                    device_name TEXT,
                    location TEXT,
                    printer_model TEXT,
                    label_size_id INTEGER,
                    ip_address TEXT,
                    status TEXT DEFAULT 'offline',
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (label_size_id) REFERENCES label_sizes (id)
                )
            """)
            
            # Add missing columns if they don't exist (migration)
            cursor.execute("PRAGMA table_info(pis)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'ip_address' not in columns:
                cursor.execute("ALTER TABLE pis ADD COLUMN ip_address TEXT")
                logger.info("Added ip_address column to pis table")
            
            if 'device_name' not in columns:
                cursor.execute("ALTER TABLE pis ADD COLUMN device_name TEXT")
                logger.info("Added device_name column to pis table")
            
            # Insert default label sizes if not exist
            default_sizes = [
                ("Large Shipping", 102, 150, 1),  # Default
                ("Standard", 57, 32, 1),
                ("Small", 57, 19, 1)
            ]
            
            for name, width, height, is_default in default_sizes:
                cursor.execute("""
                    INSERT OR IGNORE INTO label_sizes (name, width_mm, height_mm, is_default)
                    VALUES (?, ?, ?, ?)
                """, (name, width, height, is_default))
            
            # Check if label_size_id column exists in pis table, add if missing (for migration)
            cursor.execute("PRAGMA table_info(pis)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'label_size_id' not in columns:
                cursor.execute("ALTER TABLE pis ADD COLUMN label_size_id INTEGER")
            
            # Check if ip_address column exists in pis table, add if missing (for migration)
            if 'ip_address' not in columns:
                cursor.execute("ALTER TABLE pis ADD COLUMN ip_address TEXT")
            
            # Check if device_name column exists in pis table, add if missing (for migration)
            if 'device_name' not in columns:
                cursor.execute("ALTER TABLE pis ADD COLUMN device_name TEXT")
            
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
                    queued_at TIMESTAMP,
                    sent_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    error_type TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    priority INTEGER DEFAULT 5,
                    source TEXT DEFAULT 'api',
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
                    log_level TEXT DEFAULT 'ERROR',
                    details TEXT,
                    FOREIGN KEY (pi_id) REFERENCES pis (id) ON DELETE CASCADE
                )
            """)
            
            # Create server settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add missing columns to error_logs if they don't exist (migration)
            cursor.execute("PRAGMA table_info(error_logs)")
            error_log_columns = [col[1] for col in cursor.fetchall()]
            
            if 'log_level' not in error_log_columns:
                cursor.execute("ALTER TABLE error_logs ADD COLUMN log_level TEXT DEFAULT 'ERROR'")
                logger.info("Added log_level column to error_logs table")
            
            if 'details' not in error_log_columns:
                cursor.execute("ALTER TABLE error_logs ADD COLUMN details TEXT")
                logger.info("Added details column to error_logs table")
            
            # Add missing columns to print_jobs if they don't exist (migration)
            cursor.execute("PRAGMA table_info(print_jobs)")
            print_jobs_columns = [col[1] for col in cursor.fetchall()]
            
            if 'queued_at' not in print_jobs_columns:
                cursor.execute("ALTER TABLE print_jobs ADD COLUMN queued_at TIMESTAMP")
                logger.info("Added queued_at column to print_jobs table")
            
            if 'sent_at' not in print_jobs_columns:
                cursor.execute("ALTER TABLE print_jobs ADD COLUMN sent_at TIMESTAMP")
                logger.info("Added sent_at column to print_jobs table")
            
            if 'error_type' not in print_jobs_columns:
                cursor.execute("ALTER TABLE print_jobs ADD COLUMN error_type TEXT")
                logger.info("Added error_type column to print_jobs table")
            
            if 'max_retries' not in print_jobs_columns:
                cursor.execute("ALTER TABLE print_jobs ADD COLUMN max_retries INTEGER DEFAULT 3")
                logger.info("Added max_retries column to print_jobs table")
            
            if 'priority' not in print_jobs_columns:
                cursor.execute("ALTER TABLE print_jobs ADD COLUMN priority INTEGER DEFAULT 5")
                logger.info("Added priority column to print_jobs table")
            
            if 'source' not in print_jobs_columns:
                cursor.execute("ALTER TABLE print_jobs ADD COLUMN source TEXT DEFAULT 'api'")
                logger.info("Added source column to print_jobs table")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pis_api_key ON pis (api_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_print_jobs_pi_id ON print_jobs (pi_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_print_jobs_status ON print_jobs (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_print_jobs_priority ON print_jobs (priority DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_pi_id ON metrics (pi_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_pi_id ON error_logs (pi_id)")
            
        logger.info(f"Database initialized at {self.db_path}")
    
    def get_label_sizes(self) -> List[Dict[str, Any]]:
        """Get all label sizes"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, width_mm, height_mm, is_default
                    FROM label_sizes
                    ORDER BY width_mm DESC, height_mm DESC
                """)
                
                sizes = []
                for row in cursor.fetchall():
                    sizes.append({
                        'id': row['id'],
                        'name': row['name'],
                        'width_mm': row['width_mm'],
                        'height_mm': row['height_mm'],
                        'is_default': bool(row['is_default']),
                        'display_name': f"{row['name']} ({row['width_mm']}mm x {row['height_mm']}mm)"
                    })
                return sizes
        except Exception as e:
            logger.error(f"Failed to get label sizes: {e}")
            return []
    
    def add_label_size(self, name: str, width_mm: int, height_mm: int) -> Optional[int]:
        """Add a new label size"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO label_sizes (name, width_mm, height_mm, is_default)
                    VALUES (?, ?, ?, 0)
                """, (name, width_mm, height_mm))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to add label size: {e}")
            return None
    
    def delete_label_size(self, size_id: int) -> bool:
        """Delete a label size if not in use and not default"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if it's a default size
                cursor.execute("SELECT is_default FROM label_sizes WHERE id = ?", (size_id,))
                result = cursor.fetchone()
                if result and result['is_default']:
                    logger.warning("Cannot delete default label size")
                    return False
                
                # Check if any printer is using this size
                cursor.execute("SELECT COUNT(*) as count FROM pis WHERE label_size_id = ?", (size_id,))
                if cursor.fetchone()['count'] > 0:
                    logger.warning("Cannot delete label size in use by printers")
                    return False
                
                cursor.execute("DELETE FROM label_sizes WHERE id = ?", (size_id,))
                return True
        except Exception as e:
            logger.error(f"Failed to delete label size: {e}")
            return False
    
    def register_pi(self, device: PiDevice) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert enum to string if needed
                status_value = device.status.value if hasattr(device.status, 'value') else str(device.status)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO pis (id, friendly_name, api_key, device_name, location, printer_model, label_size_id, status, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device.id,
                    device.friendly_name,
                    device.api_key,
                    device.device_name,
                    device.location,
                    device.printer_model,
                    getattr(device, 'label_size_id', None),
                    status_value,
                    datetime.now(timezone.utc)
                ))
                conn.commit()
                
                if device.config:
                    cursor.execute("""
                        INSERT INTO configurations (pi_id, config_json)
                        VALUES (?, ?)
                    """, (device.id, json.dumps(device.config.model_dump())))
                    conn.commit()
                
                logger.info(f"Successfully registered Pi {device.id} in database")
                return True
        except Exception as e:
            logger.error(f"Failed to register Pi: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
                        device_name=row['device_name'] if row['device_name'] is not None else None,
                        location=row['location'],
                        printer_model=row['printer_model'],
                        label_size_id=row['label_size_id'],
                        ip_address=row['ip_address'] if row['ip_address'] is not None else None,
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
                        device_name=row['device_name'] if row['device_name'] is not None else None,
                        location=row['location'],
                        printer_model=row['printer_model'],
                        label_size_id=row['label_size_id'],
                        ip_address=row['ip_address'] if row['ip_address'] is not None else None,
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
                        device_name=row['device_name'] if row['device_name'] is not None else None,
                        location=row['location'],
                        printer_model=row['printer_model'],
                        label_size_id=row['label_size_id'],
                        ip_address=row['ip_address'] if row['ip_address'] is not None else None,
                        status=row['status'],
                        last_seen=datetime.fromisoformat(row['last_seen']) if row['last_seen'] else None
                    ))
                return pis
        except Exception as e:
            logger.error(f"Failed to get all Pis: {e}")
            return []
    
    def update_pi(self, pi_id: str, updates: Dict[str, Any]) -> bool:
        """Update Pi fields"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically
                fields = []
                values = []
                for key, value in updates.items():
                    if key in ['friendly_name', 'api_key', 'device_name', 'printer_model', 'label_size_id', 'location']:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    return False
                
                # Add pi_id to values
                values.append(pi_id)
                
                query = f"UPDATE pis SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
                logger.info(f"Updated Pi {pi_id}: {updates}")
                return True
        except Exception as e:
            logger.error(f"Failed to update Pi: {e}")
            return False
    
    def update_pi_ip_address(self, pi_id: str, ip_address: str):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pis 
                    SET ip_address = ?
                    WHERE id = ?
                """, (ip_address, pi_id))
                conn.commit()
                logger.info(f"Successfully updated IP address for Pi {pi_id} to {ip_address}")
        except Exception as e:
            logger.error(f"Failed to update Pi IP address for {pi_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def update_pi_printer_model(self, pi_id: str, printer_model: str):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pis 
                    SET printer_model = ?
                    WHERE id = ?
                """, (printer_model, pi_id))
                conn.commit()
                logger.info(f"Updated printer model for Pi {pi_id}: {printer_model}")
        except Exception as e:
            logger.error(f"Failed to update Pi printer model: {e}")
    
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
                    (id, pi_id, status, zpl_source, created_at, started_at, completed_at, error_message, retry_count, source, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    job.pi_id,
                    job.status,
                    job.zpl_source,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                    job.error_message,
                    job.retry_count,
                    getattr(job, 'source', 'api'),
                    getattr(job, 'priority', 5)
                ))
        except Exception as e:
            logger.error(f"Failed to save print job: {e}")
    
    def get_print_job(self, job_id: str) -> Optional[Dict]:
        """Get a single print job by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, pi_id, status, zpl_source, created_at, started_at, 
                           completed_at, error_message, retry_count, source, priority, error_type
                    FROM print_jobs WHERE id = ?
                """, (job_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row['id'],
                        'pi_id': row['pi_id'],
                        'status': row['status'],
                        'zpl_source': row['zpl_source'],
                        'created_at': row['created_at'],
                        'started_at': row['started_at'],
                        'completed_at': row['completed_at'],
                        'error_message': row['error_message'],
                        'retry_count': row['retry_count'],
                        'source': row.get('source', 'api'),
                        'priority': row.get('priority', 5),
                        'error_type': row.get('error_type')
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get print job: {e}")
            return None
    
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
                    INSERT INTO error_logs (id, pi_id, error_type, message, timestamp, traceback, log_level, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    error.id,
                    error.pi_id,
                    error.error_type,
                    error.message,
                    error.timestamp,
                    error.traceback,
                    'ERROR',
                    None
                ))
        except Exception as e:
            logger.error(f"Failed to save error log: {e}")
    
    def save_log(self, pi_id: str, log_type: str, message: str, level: str = "INFO", details: Optional[str] = None):
        """Save a general log entry (not just errors)"""
        try:
            import uuid
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO error_logs (id, pi_id, error_type, message, timestamp, log_level, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    pi_id,
                    log_type,
                    message,
                    datetime.now(timezone.utc),
                    level,
                    details
                ))
        except Exception as e:
            logger.error(f"Failed to save log: {e}")
    
    def save_server_log(self, log_type: str, message: str, level: str = "INFO", details: Optional[str] = None):
        """Save a server log entry"""
        self.save_log("__server__", log_type, message, level, details)
    
    def get_error_logs(self, pi_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs for a specific Pi (including both errors and general logs)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, pi_id, error_type, message, timestamp, traceback, log_level, details
                    FROM error_logs 
                    WHERE pi_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (pi_id, limit))
                rows = cursor.fetchall()
                
                logs = []
                for row in rows:
                    log_entry = {
                        'id': row['id'],
                        'pi_id': row['pi_id'],
                        'error_type': row['error_type'],
                        'message': row['message'],
                        'timestamp': row['timestamp'],
                        'traceback': row['traceback'],
                        'level': row['log_level'] if row['log_level'] else 'INFO',
                        'details': row['details']
                    }
                    logs.append(log_entry)
                return logs
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
    
    def get_server_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a server setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM server_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row['value'] if row else default
        except Exception as e:
            logger.error(f"Failed to get server setting {key}: {e}")
            return default
    
    def set_server_setting(self, key: str, value: str, description: str = None) -> bool:
        """Set a server setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO server_settings (key, value, description, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, value, description))
                return True
        except Exception as e:
            logger.error(f"Failed to set server setting {key}: {e}")
            return False
    
    def get_all_server_settings(self) -> Dict[str, Any]:
        """Get all server settings"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, description FROM server_settings")
                settings = {}
                for row in cursor.fetchall():
                    settings[row['key']] = {
                        'value': row['value'],
                        'description': row['description']
                    }
                return settings
        except Exception as e:
            logger.error(f"Failed to get server settings: {e}")
            return {}
    
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
                    # Format timestamps for display - ensure they include timezone info
                    if key_dict['created_at']:
                        # SQLite stores as UTC, make sure we indicate that
                        dt = datetime.fromisoformat(key_dict['created_at'])
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        key_dict['created_at'] = dt.isoformat()
                    if key_dict['last_used']:
                        dt = datetime.fromisoformat(key_dict['last_used'])
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        key_dict['last_used'] = dt.isoformat()
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
    
    # Queue Management Methods
    
    def queue_print_job(self, job: PrintJob) -> bool:
        """Add a print job to the queue"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO print_jobs 
                    (id, pi_id, status, zpl_source, created_at, queued_at, priority, source, retry_count, max_retries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    job.pi_id,
                    'queued',
                    job.zpl_source,
                    job.created_at,
                    datetime.utcnow(),  # queued_at
                    job.priority,
                    job.source,
                    0,  # retry_count
                    job.max_retries
                ))
                return True
        except Exception as e:
            logger.error(f"Failed to queue print job: {e}")
            return False
    
    def get_queued_jobs(self, pi_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get queued jobs for a specific Pi, ordered by priority and creation time"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM print_jobs 
                    WHERE pi_id = ? AND status = 'queued'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                """, (pi_id, limit))
                
                jobs = []
                for row in cursor.fetchall():
                    job = dict(row)
                    # Convert timestamps to datetime objects if they're strings
                    for field in ['created_at', 'queued_at', 'sent_at', 'started_at', 'completed_at']:
                        if job.get(field) and isinstance(job[field], str):
                            job[field] = datetime.fromisoformat(job[field])
                    jobs.append(job)
                return jobs
        except Exception as e:
            logger.error(f"Failed to get queued jobs: {e}")
            return []
    
    def get_all_queued_jobs(self) -> List[Dict[str, Any]]:
        """Get all queued jobs across all Pis"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT j.*, p.friendly_name as pi_name
                    FROM print_jobs j
                    JOIN pis p ON j.pi_id = p.id
                    WHERE j.status = 'queued'
                    ORDER BY j.priority DESC, j.created_at ASC
                """)
                
                jobs = []
                for row in cursor.fetchall():
                    job = dict(row)
                    for field in ['created_at', 'queued_at', 'sent_at', 'started_at', 'completed_at']:
                        if job.get(field) and isinstance(job[field], str):
                            job[field] = datetime.fromisoformat(job[field])
                    jobs.append(job)
                return jobs
        except Exception as e:
            logger.error(f"Failed to get all queued jobs: {e}")
            return []
    
    def update_job_status(self, job_id: str, status: str, error_message: str = None, error_type: str = None) -> bool:
        """Update job status and related timestamps"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.utcnow()
                
                # Build dynamic update query based on status
                update_fields = ["status = ?"]
                params = [status]
                
                if status == 'sent':
                    update_fields.append("sent_at = ?")
                    params.append(now)
                elif status == 'processing':
                    update_fields.append("started_at = ?")
                    params.append(now)
                elif status in ['completed', 'failed', 'cancelled', 'expired']:
                    update_fields.append("completed_at = ?")
                    params.append(now)
                
                if error_message:
                    update_fields.append("error_message = ?")
                    params.append(error_message)
                
                if error_type:
                    update_fields.append("error_type = ?")
                    params.append(error_type)
                
                params.append(job_id)
                
                cursor.execute(f"""
                    UPDATE print_jobs 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, params)
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            return False
    
    def increment_job_retry(self, job_id: str) -> bool:
        """Increment retry count for a job"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE print_jobs 
                    SET retry_count = retry_count + 1
                    WHERE id = ?
                """, (job_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to increment job retry: {e}")
            return False
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM print_jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    job = dict(row)
                    for field in ['created_at', 'queued_at', 'sent_at', 'started_at', 'completed_at']:
                        if job.get(field) and isinstance(job[field], str):
                            job[field] = datetime.fromisoformat(job[field])
                    return job
                return None
        except Exception as e:
            logger.error(f"Failed to get job by ID: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or pending job"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE print_jobs 
                    SET status = 'cancelled', completed_at = ?
                    WHERE id = ? AND status IN ('queued', 'pending', 'sent')
                """, (datetime.utcnow(), job_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            return False
    
    def expire_old_jobs(self, hours: int = 24) -> int:
        """Mark jobs older than specified hours as expired"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
                cursor.execute("""
                    UPDATE print_jobs 
                    SET status = 'expired', completed_at = CURRENT_TIMESTAMP
                    WHERE status IN ('queued', 'failed')
                    AND CAST(strftime('%s', created_at) AS INTEGER) < ?
                """, (cutoff_time,))
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to expire old jobs: {e}")
            return 0
    
    def clear_queue(self, pi_id: str = None) -> int:
        """Clear all queued jobs for a Pi (or all if pi_id is None)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if pi_id:
                    cursor.execute("""
                        UPDATE print_jobs 
                        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
                        WHERE pi_id = ? AND status = 'queued'
                    """, (pi_id,))
                else:
                    cursor.execute("""
                        UPDATE print_jobs 
                        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
                        WHERE status = 'queued'
                    """)
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return 0
    
    def get_queue_stats(self, pi_id: str = None) -> Dict[str, Any]:
        """Get queue statistics for a Pi or all Pis"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if pi_id:
                    where_clause = "WHERE pi_id = ?"
                    params = (pi_id,)
                else:
                    where_clause = ""
                    params = ()
                
                # Get counts by status
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM print_jobs
                    {where_clause}
                    GROUP BY status
                """, params)
                
                stats = {'total': 0}
                for row in cursor.fetchall():
                    stats[row['status']] = row['count']
                    stats['total'] += row['count']
                
                # Get oldest queued job
                cursor.execute(f"""
                    SELECT MIN(created_at) as oldest
                    FROM print_jobs
                    {where_clause + (' AND' if where_clause else 'WHERE')} status = 'queued'
                """, params)
                
                result = cursor.fetchone()
                if result and result['oldest']:
                    stats['oldest_queued'] = datetime.fromisoformat(result['oldest'])
                else:
                    stats['oldest_queued'] = None
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}