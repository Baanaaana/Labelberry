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
            return self.db.get_pi_by_id(pi_id)
    
    def register_pi(self, device_id: str, friendly_name: str, api_key: str = None) -> Dict[str, Any]:
        """Register a new Pi device"""
        if self.is_postgres:
            return self._run_async(self.db.register_pi(device_id, friendly_name, api_key))
        else:
            return self.db.register_pi(device_id, friendly_name, api_key)
    
    async def register_pi_async(self, device_id: str, friendly_name: str, api_key: str = None) -> Dict[str, Any]:
        """Register a new Pi device (async)"""
        if self.is_postgres:
            return await self.db.register_pi(device_id, friendly_name, api_key)
        else:
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
            self.db.update_pi_status(device_id, status, ip_address)
    
    def update_pi_config(self, pi_id: str, config: Dict[str, Any]):
        """Update Pi configuration"""
        if self.is_postgres:
            self._run_async(self.db.update_pi_config(pi_id, config))
        else:
            self.db.update_pi_config(pi_id, config)
    
    async def update_pi_config_async(self, pi_id: str, config: Dict[str, Any]):
        """Update Pi configuration (async)"""
        if self.is_postgres:
            await self.db.update_pi_config(pi_id, config)
        else:
            self.db.update_pi_config(pi_id, config)
    
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
            # PostgreSQL version doesn't have delete_api_key yet
            return False
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


# Create singleton instance
_database = None

def get_database() -> DatabaseWrapper:
    """Get database wrapper instance"""
    global _database
    if _database is None:
        _database = DatabaseWrapper()
    return _database