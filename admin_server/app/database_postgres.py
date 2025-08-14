import os
import json
import logging
import uuid
import asyncpg
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import sys
import hashlib

sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PiDevice, PrintJob, PiMetrics, ErrorLog, PiConfig

logger = logging.getLogger(__name__)


class PostgresDatabase:
    def __init__(self):
        # Get database URL from environment variable
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Parse the URL to get connection parameters
        self.pool = None
        
    async def init_pool(self):
        """Initialize connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                timeout=60,
                command_timeout=60
            )
    
    async def close_pool(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def get_connection(self):
        """Get a connection from the pool"""
        if not self.pool:
            await self.init_pool()
        return self.pool
    
    # Pi Device Management
    async def register_pi(self, device_id: str, friendly_name: str, api_key: str = None) -> Dict[str, Any]:
        """Register a new Pi device"""
        if not api_key:
            api_key = f"ak_{uuid.uuid4().hex[:12]}"
        
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            try:
                # Insert Pi device
                pi = await conn.fetchrow("""
                    INSERT INTO pis (id, device_id, friendly_name, api_key, status, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (device_id) 
                    DO UPDATE SET 
                        friendly_name = EXCLUDED.friendly_name,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                """, str(uuid.uuid4()), device_id, friendly_name, api_key, 'offline', 
                    datetime.now(), datetime.now())
                
                # Create default configuration
                await conn.execute("""
                    INSERT INTO configurations (id, pi_id, printer_device, label_size, 
                        default_darkness, default_speed, auto_reconnect, max_queue_size, 
                        retry_attempts, retry_delay, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (pi_id) DO NOTHING
                """, str(uuid.uuid4()), pi['id'], '/dev/usb/lp0', '4x6', 
                    15, 4, True, 100, 3, 5, 
                    datetime.now(), datetime.now())
                
                return dict(pi)
            except Exception as e:
                logger.error(f"Failed to register Pi: {e}")
                raise
    
    async def get_all_pis(self) -> List[Dict[str, Any]]:
        """Get all registered Pi devices"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    p.id, p.device_id, p.friendly_name, p.api_key, p.ip_address, 
                    p.status, p.last_seen, p.created_at, p.updated_at, p.printer_model,
                    c.id as config_id, c.pi_id, c.printer_device, c.label_size, 
                    c.default_darkness, c.default_speed, c.auto_reconnect, 
                    c.max_queue_size, c.retry_attempts, c.retry_delay
                FROM pis p
                LEFT JOIN configurations c ON p.id = c.pi_id
                ORDER BY p.friendly_name
            """)
            return [dict(row) for row in rows]
    
    async def get_pi_by_id(self, pi_id: str) -> Optional[Dict[str, Any]]:
        """Get Pi device by ID"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    p.id, p.device_id, p.friendly_name, p.api_key, p.ip_address, 
                    p.status, p.last_seen, p.created_at, p.updated_at, p.printer_model,
                    c.id as config_id, c.pi_id, c.printer_device, c.label_size, 
                    c.default_darkness, c.default_speed, c.auto_reconnect, 
                    c.max_queue_size, c.retry_attempts, c.retry_delay
                FROM pis p
                LEFT JOIN configurations c ON p.id = c.pi_id
                WHERE p.id = $1 OR p.device_id = $1
            """, pi_id)
            return dict(row) if row else None
    
    async def update_pi_status(self, device_id: str, status: str, ip_address: str = None):
        """Update Pi device status"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE pis 
                SET status = $1, ip_address = $2, last_seen = $3, updated_at = $4
                WHERE device_id = $5
            """, status, ip_address, datetime.now(), 
                datetime.now(), device_id)
    
    async def update_pi_config(self, pi_id: str, config: Dict[str, Any]):
        """Update Pi configuration and details"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            # Update pis table fields if present
            if 'printer_model' in config or 'friendly_name' in config:
                pi_updates = []
                pi_values = []
                pi_param_count = 1
                
                if 'printer_model' in config:
                    pi_updates.append(f"printer_model = ${pi_param_count}")
                    pi_values.append(config['printer_model'])
                    pi_param_count += 1
                    
                if 'friendly_name' in config:
                    pi_updates.append(f"friendly_name = ${pi_param_count}")
                    pi_values.append(config['friendly_name'])
                    pi_param_count += 1
                    
                if pi_updates:
                    pi_values.append(pi_id)
                    query = f"""UPDATE pis SET {', '.join(pi_updates)}, updated_at = NOW() 
                               WHERE id = ${pi_param_count} OR device_id = ${pi_param_count}"""
                    await conn.execute(query, *pi_values)
            
            # Build dynamic update query for configuration fields
            update_fields = []
            values = []
            param_count = 1
            
            for key, value in config.items():
                if key in ['printer_device', 'label_size', 'default_darkness', 
                          'default_speed', 'auto_reconnect', 'max_queue_size', 
                          'retry_attempts', 'retry_delay']:
                    update_fields.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if update_fields:
                update_fields.append(f"updated_at = ${param_count}")
                values.append(datetime.now())
                param_count += 1
                
                values.append(pi_id)  # WHERE clause
                
                query = f"""
                    UPDATE configurations 
                    SET {', '.join(update_fields)}
                    WHERE pi_id = ${param_count}
                """
                await conn.execute(query, *values)
    
    async def delete_pi(self, pi_id: str) -> bool:
        """Delete a Pi device and all related data"""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            try:
                # Start a transaction
                async with conn.transaction():
                    # First get the actual database ID if we're given a device_id
                    pi_row = await conn.fetchrow("""
                        SELECT id FROM pis WHERE id = $1 OR device_id = $1
                    """, pi_id)
                    
                    if not pi_row:
                        logger.warning(f"Pi {pi_id} not found for deletion")
                        return False
                    
                    actual_id = pi_row['id']
                    
                    # Delete related data first (cascade delete)
                    await conn.execute("DELETE FROM metrics WHERE pi_id = $1", actual_id)
                    await conn.execute("DELETE FROM print_jobs WHERE pi_id = $1", actual_id)
                    await conn.execute("DELETE FROM error_logs WHERE pi_id = $1", actual_id)
                    await conn.execute("DELETE FROM configurations WHERE pi_id = $1", actual_id)
                    
                    # Delete the Pi record
                    result = await conn.execute("DELETE FROM pis WHERE id = $1", actual_id)
                    
                    # Check if any row was deleted (result is like "DELETE 1")
                    deleted_count = int(result.split()[-1]) if result and ' ' in result else 0
                    if deleted_count > 0:
                        logger.info(f"Deleted Pi {pi_id} and all related data")
                        return True
                    else:
                        logger.warning(f"Pi {pi_id} not found for deletion")
                        return False
            except Exception as e:
                logger.error(f"Error deleting Pi {pi_id}: {e}")
                return False
    
    # Print Job Management
    async def create_print_job(self, pi_id: str, zpl_source: str, zpl_content: str = None) -> str:
        """Create a new print job"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            job_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO print_jobs (id, pi_id, zpl_source, zpl_content, status, 
                    created_at, retry_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, job_id, pi_id, zpl_source, zpl_content, 'pending', 
                datetime.now(), 0)
            return job_id
    
    async def get_print_jobs(self, pi_id: str = None, status: str = None, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """Get print jobs with optional filters"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            query = "SELECT * FROM print_jobs WHERE 1=1"
            params = []
            param_count = 1
            
            if pi_id:
                query += f" AND pi_id = ${param_count}"
                params.append(pi_id)
                param_count += 1
            
            if status:
                query += f" AND status = ${param_count}"
                params.append(status)
                param_count += 1
            
            query += f" ORDER BY created_at DESC LIMIT ${param_count}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def update_print_job(self, job_id: str, status: str, 
                              error_message: str = None):
        """Update print job status"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            update_fields = {
                'status': status,
                'updated_at': datetime.now()
            }
            
            if status == 'processing':
                update_fields['started_at'] = datetime.now()
            elif status in ['completed', 'failed']:
                update_fields['completed_at'] = datetime.now()
            
            if error_message:
                update_fields['error_message'] = error_message
            
            # Build update query
            set_clause = ', '.join([f"{k} = ${i+1}" for i, k in enumerate(update_fields.keys())])
            values = list(update_fields.values())
            values.append(job_id)
            
            await conn.execute(
                f"UPDATE print_jobs SET {set_clause} WHERE id = ${len(values)}",
                *values
            )
    
    # Metrics Management
    async def save_metrics(self, metrics: PiMetrics):
        """Save Pi metrics"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            # Get Pi ID from device_id
            pi = await conn.fetchrow("SELECT id FROM pis WHERE device_id = $1", metrics.pi_id)
            if not pi:
                logger.error(f"Pi not found: {metrics.pi_id}")
                return
            
            await conn.execute("""
                INSERT INTO metrics (id, pi_id, cpu_usage, memory_usage, disk_usage, 
                    temperature, jobs_processed, jobs_failed, avg_print_time, uptime, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, str(uuid.uuid4()), pi['id'], metrics.cpu_usage, metrics.memory_usage,
                metrics.disk_usage, metrics.temperature, metrics.jobs_processed,
                metrics.jobs_failed, metrics.avg_print_time, metrics.uptime,
                datetime.now())
    
    async def get_metrics(self, pi_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a Pi device"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            since = datetime.now() - timedelta(hours=hours)
            rows = await conn.fetch("""
                SELECT * FROM metrics 
                WHERE pi_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
            """, pi_id, since)
            return [dict(row) for row in rows]
    
    # Error Log Management
    async def log_error(self, pi_id: str, error_type: str, message: str, 
                       stack_trace: str = None):
        """Log an error"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO error_logs (id, pi_id, error_type, message, 
                    stack_trace, resolved, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, str(uuid.uuid4()), pi_id, error_type, message, 
                stack_trace, False, datetime.now())
    
    async def get_error_logs(self, pi_id: str = None, resolved: bool = None, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """Get error logs"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            query = "SELECT * FROM error_logs WHERE 1=1"
            params = []
            param_count = 1
            
            if pi_id:
                query += f" AND pi_id = ${param_count}"
                params.append(pi_id)
                param_count += 1
            
            if resolved is not None:
                query += f" AND resolved = ${param_count}"
                params.append(resolved)
                param_count += 1
            
            query += f" ORDER BY created_at DESC LIMIT ${param_count}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    # User Management
    async def verify_user(self, username: str, password: str) -> bool:
        """Verify user credentials"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            # Hash the password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            user = await conn.fetchrow("""
                SELECT * FROM users 
                WHERE username = $1 AND password = $2
            """, username, password_hash)
            
            return user is not None
    
    async def update_user_password(self, username: str, new_password: str):
        """Update user password"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            await conn.execute("""
                UPDATE users 
                SET password = $1, updated_at = $2
                WHERE username = $3
            """, password_hash, datetime.now(), username)
    
    # API Key Management
    async def create_api_key(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new API key"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            key_id = str(uuid.uuid4())
            key = f"ak_{uuid.uuid4().hex[:20]}"
            
            row = await conn.fetchrow("""
                INSERT INTO api_keys (id, name, key, description, created_at)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
            """, key_id, name, key, description, datetime.now())
            
            return dict(row)
    
    async def get_api_keys(self) -> List[Dict[str, Any]]:
        """Get all API keys"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM api_keys ORDER BY created_at DESC")
            return [dict(row) for row in rows]
    
    async def verify_api_key(self, key: str) -> bool:
        """Verify an API key"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            # Update last_used timestamp
            await conn.execute("""
                UPDATE api_keys 
                SET last_used = $1
                WHERE key = $2
            """, datetime.now(), key)
            
            # Check if key exists
            row = await conn.fetchrow("SELECT * FROM api_keys WHERE key = $1", key)
            return row is not None
    
    # Label Size Management
    async def get_label_sizes(self) -> List[Dict[str, Any]]:
        """Get all label sizes"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM label_sizes 
                ORDER BY name
            """)
            return [dict(row) for row in rows]
    
    async def create_label_size(self, name: str, width: float, height: float, 
                               unit: str = 'inch') -> Dict[str, Any]:
        """Create a new label size"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO label_sizes (id, name, width, height, unit, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (name) DO NOTHING
                RETURNING *
            """, str(uuid.uuid4()), name, width, height, unit, 
                datetime.now(), datetime.now())
            
            return dict(row) if row else None
    
    # System Settings Management
    async def get_system_settings(self) -> Dict[str, Any]:
        """Get system settings including MQTT configuration"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            # Use a different table name to avoid conflicts
            # First check if settings table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'mqtt_configuration'
                )
            """)
            
            if not table_exists:
                # Create the table if it doesn't exist
                await conn.execute("""
                    CREATE TABLE mqtt_configuration (
                        setting_key VARCHAR(255) PRIMARY KEY,
                        setting_value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert default settings
                await conn.execute("""
                    INSERT INTO mqtt_configuration (setting_key, setting_value) VALUES
                    ('mqtt_broker', 'localhost'),
                    ('mqtt_port', '1883'),
                    ('mqtt_username', ''),
                    ('mqtt_password', '')
                    ON CONFLICT (setting_key) DO NOTHING
                """)
            
            # Get all settings
            rows = await conn.fetch("SELECT setting_key, setting_value FROM mqtt_configuration")
            settings = {row['setting_key']: row['setting_value'] for row in rows}
            
            # Ensure all expected keys exist with defaults
            defaults = {
                'mqtt_broker': 'localhost',
                'mqtt_port': '1883',
                'mqtt_username': '',
                'mqtt_password': ''
            }
            
            for key, default_value in defaults.items():
                if key not in settings:
                    settings[key] = default_value
            
            return settings
    
    async def update_system_setting(self, key: str, value: str):
        """Update a system setting"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO mqtt_configuration (setting_key, setting_value, updated_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (setting_key) 
                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at
            """, key, value)
    
    async def update_mqtt_settings(self, mqtt_settings: Dict[str, Any]):
        """Update MQTT settings"""
        pool = await self.get_connection()
        async with pool.acquire() as conn:
            # Ensure the table exists with correct structure
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mqtt_configuration (
                    setting_key VARCHAR(255) PRIMARY KEY,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            async with conn.transaction():
                for key, value in mqtt_settings.items():
                    if key.startswith('mqtt_'):
                        # Convert value to string and ensure it's not None
                        str_value = str(value) if value is not None else ''
                        
                        try:
                            await conn.execute("""
                                INSERT INTO mqtt_configuration (setting_key, setting_value, updated_at)
                                VALUES ($1, $2, CURRENT_TIMESTAMP)
                                ON CONFLICT (setting_key) 
                                DO UPDATE SET setting_value = EXCLUDED.setting_value, updated_at = EXCLUDED.updated_at
                            """, key, str_value)
                            logger.info(f"Updated MQTT setting {key}={str_value}")
                        except Exception as e:
                            logger.error(f"Failed to update setting {key}={str_value}: {e}")
                            raise


# Create a singleton instance
database = None

def get_database() -> PostgresDatabase:
    """Get database instance"""
    global database
    if database is None:
        database = PostgresDatabase()
    return database

async def init_database():
    """Initialize database connection"""
    db = get_database()
    await db.init_pool()
    return db

async def close_database():
    """Close database connection"""
    db = get_database()
    await db.close_pool()