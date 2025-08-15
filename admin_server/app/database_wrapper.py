"""
Database wrapper to provide unified interface for SQLite and PostgreSQL
"""

import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseWrapper:
    """Wrapper to provide unified sync/async interface for both databases"""
    
    def __init__(self):
        self.is_postgres = bool(os.getenv("DATABASE_URL"))
        self.db = None
        
        if self.is_postgres:
            from .database_postgres import get_database
            self.db = get_database()
            logger.info("Using PostgreSQL database")
        else:
            # Delay SQLite initialization to avoid permission issues
            logger.info("Will use SQLite database (lazy init)")
    
    def _init_sqlite(self):
        """Initialize SQLite database if not already done"""
        if not self.is_postgres and self.db is None:
            from .database import Database
            from .config import ServerConfig
            config = ServerConfig()
            # Use local database for development
            if os.getenv("LABELBERRY_LOCAL_MODE", "false").lower() == "true":
                config.database_path = "./labelberry.db"
            self.db = Database(config.database_path)
            logger.info(f"Initialized SQLite database at {config.database_path}")
    
    async def init(self):
        """Initialize database connection"""
        if self.is_postgres:
            await self.db.init_pool()
        else:
            self._init_sqlite()
    
    async def close(self):
        """Close database connection"""
        if self.is_postgres:
            await self.db.close_pool()
    
    def _run_async(self, coro):
        """Run async function in sync context"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context, can't block
                # Create a new thread to run the async code
                import concurrent.futures
                import threading
                
                result = None
                exception = None
                
                def run_in_thread():
                    nonlocal result, exception
                    try:
                        result = asyncio.run(coro)
                    except Exception as e:
                        exception = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if exception:
                    raise exception
                return result
            else:
                # We're in sync context
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)
    
    # User Management
    def verify_user(self, username: str, password: str) -> bool:
        """Verify user credentials"""
        if self.is_postgres:
            return self._run_async(self.db.verify_user(username, password))
        else:
            self._init_sqlite()
            return self.db.verify_user(username, password)
    
    async def verify_user_async(self, username: str, password: str) -> bool:
        """Verify user credentials (async)"""
        if self.is_postgres:
            return await self.db.verify_user(username, password)
        else:
            return self.db.verify_user(username, password)
    
    def update_user_password(self, username: str, new_password: str) -> bool:
        """Update user password"""
        if self.is_postgres:
            self._run_async(self.db.update_user_password(username, new_password))
            return True
        else:
            return self.db.update_user_password(username, new_password)
    
    async def update_user_password_async(self, username: str, new_password: str) -> bool:
        """Update user password (async)"""
        if self.is_postgres:
            await self.db.update_user_password(username, new_password)
            return True
        else:
            return self.db.update_user_password(username, new_password)
    
    # Pi Device Management
    def get_all_pis(self) -> List[Dict[str, Any]]:
        """Get all registered Pi devices"""
        if self.is_postgres:
            return self._run_async(self.db.get_all_pis())
        else:
            return self.db.get_all_pis()
    
    async def get_all_pis_async(self) -> List[Dict[str, Any]]:
        """Get all registered Pi devices (async)"""
        if self.is_postgres:
            logger.info("Getting Pi devices from PostgreSQL")
            result = await self.db.get_all_pis()
            logger.info(f"Got {len(result)} Pi devices from PostgreSQL")
            if result and len(result) > 0:
                logger.info(f"First Pi ID from PostgreSQL: {result[0].get('id')}")
            return result
        else:
            self._init_sqlite()
            logger.info("Getting Pi devices from SQLite")
            return self.db.get_all_pis()
    
    def get_pi_by_id(self, pi_id: str) -> Optional[Dict[str, Any]]:
        """Get Pi device by ID"""
        if self.is_postgres:
            return self._run_async(self.db.get_pi_by_id(pi_id))
        else:
            return self.db.get_pi_by_id(pi_id)
    
    async def get_pi_by_id_async(self, pi_id: str) -> Optional[Dict[str, Any]]:
        """Get Pi device by ID (async)"""
        if self.is_postgres:
            return await self.db.get_pi_by_id(pi_id)
        else:
            self._init_sqlite()
            return self.db.get_pi_by_id(pi_id)
    
    def register_pi(self, device_or_id, friendly_name: str = None, api_key: str = None) -> Dict[str, Any]:
        """Register a new Pi device - accepts PiDevice object or individual params"""
        # Handle both PiDevice object and individual parameters
        if hasattr(device_or_id, 'id'):  # It's a PiDevice object
            device = device_or_id
            device_id = device.id
            friendly_name = device.friendly_name
            api_key = device.api_key
        else:  # It's individual parameters
            device_id = device_or_id
            
        if self.is_postgres:
            return self._run_async(self.db.register_pi(device_id, friendly_name, api_key))
        else:
            self._init_sqlite()
            return self.db.register_pi(device_id, friendly_name, api_key)
    
    async def register_pi_async(self, device_or_id, friendly_name: str = None, api_key: str = None) -> Dict[str, Any]:
        """Register a new Pi device (async) - accepts PiDevice object or individual params"""
        # Handle both PiDevice object and individual parameters
        if hasattr(device_or_id, 'id'):  # It's a PiDevice object
            device = device_or_id
            device_id = device.id
            friendly_name = device.friendly_name
            api_key = device.api_key
        else:  # It's individual parameters
            device_id = device_or_id
            
        if self.is_postgres:
            return await self.db.register_pi(device_id, friendly_name, api_key)
        else:
            self._init_sqlite()
            return self.db.register_pi(device_id, friendly_name, api_key)
    
    def update_pi_status(self, device_id: str, status: str, ip_address: str = None):
        """Update Pi device status"""
        if self.is_postgres:
            self._run_async(self.db.update_pi_status(device_id, status, ip_address))
        else:
            self.db.update_pi_status(device_id, status, ip_address)
    
    async def update_pi_status_async(self, device_id: str, status: str, ip_address: str = None):
        """Update Pi device status (async)"""
        if self.is_postgres:
            await self.db.update_pi_status(device_id, status, ip_address)
        else:
            self._init_sqlite()
            self.db.update_pi_status(device_id, status, ip_address)
    
    def update_pi_config(self, pi_id: str, config: Dict[str, Any]):
        """Update Pi configuration"""
        if self.is_postgres:
            self._run_async(self.db.update_pi_config(pi_id, config))
        else:
            self.db.update_pi_config(pi_id, config)
    
    async def update_pi_config_async(self, pi_id: str, config: Dict[str, Any]) -> bool:
        """Update Pi configuration (async)"""
        try:
            if self.is_postgres:
                await self.db.update_pi_config(pi_id, config)
            else:
                self.db.update_pi_config(pi_id, config)
            return True
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return False
    
    def update_pi(self, pi_id: str, updates: Dict[str, Any]) -> bool:
        """Update Pi device details"""
        if self.is_postgres:
            return self._run_async(self.db.update_pi_config(pi_id, updates))
        else:
            self._init_sqlite()
            return self.db.update_pi_config(pi_id, updates)
    
    async def update_pi_async(self, pi_id: str, updates: Dict[str, Any]) -> bool:
        """Update Pi device details (async)"""
        if self.is_postgres:
            await self.db.update_pi_config(pi_id, updates)
            return True
        else:
            self._init_sqlite()
            self.db.update_pi_config(pi_id, updates)
            return True
    
    def delete_pi(self, pi_id: str) -> bool:
        """Delete a Pi device (sync version for SQLite)"""
        if self.is_postgres:
            return self._run_async(self.db.delete_pi(pi_id))
        else:
            self._init_sqlite()
            return self.db.delete_pi(pi_id)
    
    async def delete_pi_async(self, pi_id: str) -> bool:
        """Delete a Pi device (async version)"""
        if self.is_postgres:
            # For PostgreSQL, use the async delete method
            return await self.db.delete_pi(pi_id)
        else:
            # For SQLite, run the sync version in executor to avoid blocking
            self._init_sqlite()
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.db.delete_pi, pi_id)
    
    # Print Job Management
    def create_print_job(self, pi_id: str, zpl_source: str, zpl_content: str = None) -> str:
        """Create a new print job"""
        if self.is_postgres:
            return self._run_async(self.db.create_print_job(pi_id, zpl_source, zpl_content))
        else:
            return self.db.create_print_job(pi_id, zpl_source, zpl_content)
    
    async def create_print_job_async(self, pi_id: str, zpl_source: str, zpl_content: str = None) -> str:
        """Create a new print job (async)"""
        if self.is_postgres:
            return await self.db.create_print_job(pi_id, zpl_source, zpl_content)
        else:
            return self.db.create_print_job(pi_id, zpl_source, zpl_content)
    
    def get_print_jobs(self, pi_id: str = None, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get print jobs with optional filters"""
        if self.is_postgres:
            return self._run_async(self.db.get_print_jobs(pi_id, status, limit))
        else:
            return self.db.get_print_jobs(pi_id, status, limit)
    
    async def get_print_jobs_async(self, pi_id: str = None, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get print jobs with optional filters (async)"""
        if self.is_postgres:
            return await self.db.get_print_jobs(pi_id, status, limit)
        else:
            return self.db.get_print_jobs(pi_id, status, limit)
    
    def update_print_job(self, job_id: str, status: str, error_message: str = None):
        """Update print job status"""
        if self.is_postgres:
            self._run_async(self.db.update_print_job(job_id, status, error_message))
        else:
            self.db.update_print_job(job_id, status, error_message)
    
    async def update_print_job_async(self, job_id: str, status: str, error_message: str = None):
        """Update print job status (async)"""
        if self.is_postgres:
            await self.db.update_print_job(job_id, status, error_message)
        else:
            self.db.update_print_job(job_id, status, error_message)
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get print job by ID"""
        if self.is_postgres:
            jobs = self._run_async(self.db.get_print_jobs(status=None, limit=1))
            return next((j for j in jobs if j['id'] == job_id), None)
        else:
            return self.db.get_job_by_id(job_id)
    
    async def get_job_by_id_async(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get print job by ID (async)"""
        if self.is_postgres:
            pool = await self.db.get_connection()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM print_jobs WHERE id = $1
                """, job_id)
                return dict(row) if row else None
        else:
            return self.db.get_job_by_id(job_id)
    
    # Metrics Management
    def save_metrics(self, metrics):
        """Save Pi metrics"""
        if self.is_postgres:
            self._run_async(self.db.save_metrics(metrics))
        else:
            self.db.save_metrics(metrics)
    
    async def save_metrics_async(self, metrics):
        """Save Pi metrics (async)"""
        if self.is_postgres:
            await self.db.save_metrics(metrics)
        else:
            self.db.save_metrics(metrics)
    
    def get_metrics(self, pi_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a Pi device"""
        if self.is_postgres:
            return self._run_async(self.db.get_metrics(pi_id, hours))
        else:
            return self.db.get_metrics(pi_id, hours)
    
    async def get_metrics_async(self, pi_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a Pi device (async)"""
        if self.is_postgres:
            return await self.db.get_metrics(pi_id, hours)
        else:
            return self.db.get_metrics(pi_id, hours)
    
    # Error Log Management
    def log_error(self, pi_id: str, error_type: str, message: str, stack_trace: str = None):
        """Log an error"""
        if self.is_postgres:
            self._run_async(self.db.log_error(pi_id, error_type, message, stack_trace))
        else:
            self.db.log_error(pi_id, error_type, message, stack_trace)
    
    async def log_error_async(self, pi_id: str, error_type: str, message: str, stack_trace: str = None):
        """Log an error (async)"""
        if self.is_postgres:
            await self.db.log_error(pi_id, error_type, message, stack_trace)
        else:
            self.db.log_error(pi_id, error_type, message, stack_trace)
    
    def get_error_logs(self, pi_id: str = None, resolved: bool = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get error logs"""
        if self.is_postgres:
            return self._run_async(self.db.get_error_logs(pi_id, resolved, limit))
        else:
            return self.db.get_error_logs(pi_id, resolved, limit)
    
    async def get_error_logs_async(self, pi_id: str = None, resolved: bool = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get error logs (async)"""
        if self.is_postgres:
            return await self.db.get_error_logs(pi_id, resolved, limit)
        else:
            return self.db.get_error_logs(pi_id, resolved, limit)
    
    async def get_logs_async(self, pi_id: str = None, log_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs (async)"""
        if self.is_postgres:
            pool = await self.db.get_connection()
            async with pool.acquire() as conn:
                query = "SELECT * FROM server_logs WHERE 1=1"
                params = []
                
                # Note: server_logs uses event_type instead of log_type
                if log_type:
                    query += " AND event_type = $" + str(len(params) + 1)
                    params.append(log_type)
                
                # Note: server_logs doesn't have pi_id, but we can search in details
                if pi_id:
                    query += " AND details LIKE $" + str(len(params) + 1)
                    params.append(f'%{pi_id}%')
                
                query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        else:
            # For SQLite, implement basic log retrieval
            return []
    
    # API Key Management
    def create_api_key(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new API key"""
        if self.is_postgres:
            return self._run_async(self.db.create_api_key(name, description))
        else:
            return self.db.create_api_key(name, description)
    
    async def create_api_key_async(self, name: str, description: str = None) -> Dict[str, Any]:
        """Create a new API key (async)"""
        if self.is_postgres:
            return await self.db.create_api_key(name, description)
        else:
            return self.db.create_api_key(name, description)
    
    def get_api_keys(self) -> List[Dict[str, Any]]:
        """Get all API keys"""
        if self.is_postgres:
            return self._run_async(self.db.get_api_keys())
        else:
            return self.db.get_api_keys()
    
    async def get_api_keys_async(self) -> List[Dict[str, Any]]:
        """Get all API keys (async)"""
        if self.is_postgres:
            return await self.db.get_api_keys()
        else:
            return self.db.get_api_keys()
    
    def verify_api_key(self, key: str) -> bool:
        """Verify an API key"""
        if self.is_postgres:
            return self._run_async(self.db.verify_api_key(key))
        else:
            return self.db.verify_api_key(key)
    
    async def verify_api_key_async(self, key: str) -> bool:
        """Verify an API key (async)"""
        if self.is_postgres:
            return await self.db.verify_api_key(key)
        else:
            return self.db.verify_api_key(key)
    
    def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key"""
        if self.is_postgres:
            return self._run_async(self.db.delete_api_key(key_id))
        else:
            return self.db.delete_api_key(key_id)
    
    async def delete_api_key_async(self, key_id: str) -> bool:
        """Delete an API key (async)"""
        if self.is_postgres:
            return await self.db.delete_api_key(key_id)
        else:
            return self.db.delete_api_key(key_id)
    
    # Label Size Management
    def get_label_sizes(self) -> List[Dict[str, Any]]:
        """Get all label sizes"""
        if self.is_postgres:
            return self._run_async(self.db.get_label_sizes())
        else:
            return self.db.get_label_sizes()
    
    async def get_label_sizes_async(self) -> List[Dict[str, Any]]:
        """Get all label sizes (async)"""
        if self.is_postgres:
            return await self.db.get_label_sizes()
        else:
            return self.db.get_label_sizes()
    
    def create_label_size(self, name: str, width: float, height: float, unit: str = 'inch') -> Dict[str, Any]:
        """Create a new label size"""
        if self.is_postgres:
            return self._run_async(self.db.create_label_size(name, width, height, unit))
        else:
            return self.db.create_label_size(name, width, height, unit)
    
    async def create_label_size_async(self, name: str, width: float, height: float, unit: str = 'inch') -> Dict[str, Any]:
        """Create a new label size (async)"""
        if self.is_postgres:
            return await self.db.create_label_size(name, width, height, unit)
        else:
            return self.db.create_label_size(name, width, height, unit)
    
    def delete_label_size(self, size_id: str) -> bool:
        """Delete a label size"""
        if self.is_postgres:
            # PostgreSQL version doesn't have delete_label_size yet
            return False
        else:
            return self.db.delete_label_size(size_id)
    
    # Server settings (SQLite only)
    def get_server_setting(self, key: str, default: Any = None) -> Any:
        """Get server setting"""
        if self.is_postgres:
            # TODO: Implement server settings in PostgreSQL
            return default
        else:
            return self.db.get_server_setting(key, default)
    
    def set_server_setting(self, key: str, value: Any, description: str = None):
        """Set server setting"""
        if self.is_postgres:
            # TODO: Implement server settings in PostgreSQL
            pass
        else:
            self.db.set_server_setting(key, value, description)
    
    # Server logs (SQLite only)
    def save_server_log(self, event_type: str, message: str, level: str = "INFO", details: Dict[str, Any] = None):
        """Save server log"""
        if self.is_postgres:
            # Use standard logging for PostgreSQL
            logger.log(getattr(logging, level, logging.INFO), f"{event_type}: {message}")
        else:
            self.db.save_server_log(event_type, message, level, details)
    
    # Username management (SQLite only)
    def update_username(self, old_username: str, new_username: str) -> bool:
        """Update username"""
        if self.is_postgres:
            # TODO: Implement username update in PostgreSQL
            return False
        else:
            return self.db.update_username(old_username, new_username)
    
    # System Settings Management (PostgreSQL)
    async def get_system_settings(self) -> Dict[str, Any]:
        """Get system settings including MQTT configuration"""
        if self.is_postgres:
            return await self.db.get_system_settings()
        else:
            # For SQLite, return default MQTT settings
            return {
                'mqtt_broker': 'localhost',
                'mqtt_port': '1883',
                'mqtt_username': '',
                'mqtt_password': ''
            }
    
    async def update_mqtt_settings(self, mqtt_settings: Dict[str, Any]):
        """Update MQTT settings"""
        if self.is_postgres:
            return await self.db.update_mqtt_settings(mqtt_settings)
        else:
            # For SQLite, store in server settings table
            for key, value in mqtt_settings.items():
                self.set_server_setting(key, value)
    
    async def init_pool(self):
        """Initialize database connection pool (PostgreSQL only)"""
        if self.is_postgres:
            return await self.db.init_pool()
    
    async def get_connection(self):
        """Get database connection pool (PostgreSQL only)"""
        if self.is_postgres:
            return await self.db.get_connection()
        else:
            raise NotImplementedError("get_connection is only available for PostgreSQL")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        if self.is_postgres:
            return self._run_async(self.get_dashboard_stats_async())
        else:
            # For SQLite, use the existing method
            return self.db.get_dashboard_stats()
    
    async def get_dashboard_stats_async(self) -> Dict[str, Any]:
        """Get dashboard statistics (async)"""
        if self.is_postgres:
            pool = await self.db.get_connection()
            async with pool.acquire() as conn:
                # Get total and online printers
                total_pis = await conn.fetchval("SELECT COUNT(*) FROM pis")
                online_pis = await conn.fetchval("SELECT COUNT(*) FROM pis WHERE status = 'online'")
                
                # Get jobs in last 24 hours
                jobs_24h = await conn.fetchval("""
                    SELECT COUNT(*) FROM print_jobs 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                
                # Get failed jobs in last 24 hours
                failed_24h = await conn.fetchval("""
                    SELECT COUNT(*) FROM print_jobs 
                    WHERE status = 'failed' 
                    AND created_at > NOW() - INTERVAL '24 hours'
                """)
                
                # Get average print time from completed jobs (in milliseconds)
                # Exclude test prints by filtering out jobs with 'test' in the source
                avg_print_time = await conn.fetchval("""
                    SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) * 1000)
                    FROM print_jobs 
                    WHERE status = 'completed' 
                    AND completed_at IS NOT NULL
                    AND created_at > NOW() - INTERVAL '24 hours'
                    AND (zpl_source NOT LIKE '%test%' OR zpl_source IS NULL)
                """) or 0
                
                # Get current queue length (pending jobs)
                queue_length = await conn.fetchval("""
                    SELECT COUNT(*) FROM print_jobs 
                    WHERE status IN ('pending', 'processing')
                """)
                
                return {
                    "totalPrinters": total_pis,
                    "onlinePrinters": online_pis,
                    "totalJobsToday": jobs_24h,
                    "failedJobsToday": failed_24h,
                    "avgPrintTime": round(avg_print_time) if avg_print_time else 0,
                    "queueLength": queue_length
                }
        else:
            # For SQLite, use the existing method
            stats = self.db.get_dashboard_stats()
            # Convert to frontend format
            return {
                "totalPrinters": stats.get("total_pis", 0),
                "onlinePrinters": stats.get("online_pis", 0),
                "totalJobsToday": stats.get("jobs_24h", 0),
                "failedJobsToday": stats.get("failed_24h", 0),
                "avgPrintTime": 0,  # Not calculated in SQLite version
                "queueLength": 0  # Not calculated in SQLite version
            }
    
    # Additional async methods needed for MQTT handlers
    async def get_pi_config_async(self, pi_id: str) -> Optional[Dict[str, Any]]:
        """Get Pi configuration (async)"""
        if self.is_postgres:
            pool = await self.db.get_connection()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM configurations WHERE pi_id = $1
                """, pi_id)
                return dict(row) if row else None
        else:
            # For SQLite, use sync method
            return self.db.get_pi_config(pi_id)
    
    async def save_log_async(self, pi_id: str, log_type: str, message: str, level: str = "INFO", details: str = None):
        """Save Pi log entry (async)"""
        if self.is_postgres:
            pool = await self.db.get_connection()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO server_logs (event_type, message, level, details, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, log_type, f"Pi {pi_id}: {message}", level, details, datetime.now())
        else:
            # For SQLite, use sync method
            self.db.save_log(pi_id, log_type, message, details)
    
    async def save_error_log_async(self, error_log):
        """Save error log (async)"""
        if self.is_postgres:
            # Handle both traceback and stack_trace attribute names
            stack_trace = getattr(error_log, 'traceback', None) or getattr(error_log, 'stack_trace', None)
            await self.db.log_error(error_log.pi_id, error_log.error_type, error_log.message, stack_trace)
        else:
            self.db.save_error_log(error_log)
    
    async def update_job_status_async(self, job_id: str, status: str, error_message: str = None, error_type: str = None):
        """Update job status (async)"""
        if self.is_postgres:
            await self.db.update_print_job(job_id, status, error_message)
        else:
            self.db.update_job_status(job_id, status)
    
    def update_job_status(self, job_id: str, status: str, error_message: str = None, error_type: str = None):
        """Update job status (sync)"""
        if self.is_postgres:
            self._run_async(self.db.update_print_job(job_id, status, error_message))
        else:
            self._init_sqlite()
            self.db.update_job_status(job_id, status)
    
    async def get_queued_jobs(self, pi_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get queued jobs for processing"""
        if self.is_postgres:
            pool = await self.db.get_connection()
            async with pool.acquire() as conn:
                if pi_id:
                    rows = await conn.fetch("""
                        SELECT * FROM print_jobs 
                        WHERE status = 'pending' 
                        AND pi_id = $1
                        ORDER BY created_at ASC 
                        LIMIT $2
                    """, pi_id, limit)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM print_jobs 
                        WHERE status = 'pending' 
                        ORDER BY created_at ASC 
                        LIMIT $1
                    """, limit)
                return [dict(row) for row in rows]
        else:
            # For SQLite, return empty list as queue management is not fully implemented
            return []
    
    def get_queued_jobs_sync(self, pi_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get queued jobs for processing (sync version)"""
        if self.is_postgres:
            return self._run_async(self.get_queued_jobs(pi_id, limit))
        else:
            # For SQLite, return empty list as queue management is not fully implemented
            return []
    
    def expire_old_jobs(self, hours: int = 24) -> int:
        """Expire old jobs"""
        # Not implemented yet, return 0
        return 0
    
    def get_queue_stats(self, pi_id: str = None) -> Dict[str, Any]:
        """Get queue statistics"""
        # Return basic stats for now
        return {
            'queued': 0,
            'sent': 0,
            'failed': 0,
            'completed': 0,
            'total': 0
        }


# Create singleton instance
_database = None

def get_database() -> DatabaseWrapper:
    """Get database wrapper instance"""
    global _database
    if _database is None:
        _database = DatabaseWrapper()
    return _database