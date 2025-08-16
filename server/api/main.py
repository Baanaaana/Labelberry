import logging
import os
import sys
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Request, Form, Header
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# Removed - using Next.js frontend
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets
import uvicorn
import requests

sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import (
    PiDevice, PrintJob, PiMetrics, ErrorLog,
    ApiResponse, PiStatus, PiConfig, PrintJobStatus
)
from .config import ServerConfig
from .database_wrapper import get_database


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


server_config = ServerConfig()
database = get_database()

# Only initialize MQTT if not in local mode
if os.getenv("LABELBERRY_LOCAL_MODE", "false").lower() != "true":
    try:
        from .mqtt_server import MQTTServer
        from .queue_manager import QueueManager
        mqtt_server = MQTTServer(database, server_config)
        queue_manager = QueueManager(database, mqtt_server)
    except ImportError as e:
        logger.warning(f"Could not import MQTT/Queue modules: {e}")
        mqtt_server = None
        queue_manager = None
else:
    mqtt_server = None
    queue_manager = None
    logger.info("Running in local mode - MQTT disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LabelBerry Admin Server started")
    
    # Initialize database connection
    await database.init()
    database.save_server_log("server_started", "Admin Server started", "INFO")
    
    # Load MQTT settings from database and update server_config
    global mqtt_server, queue_manager
    if mqtt_server:
        try:
            # Load MQTT settings from database
            settings = await database.get_system_settings()
            if settings and settings.get('mqtt_username') and settings.get('mqtt_password'):
                # Update server config dict with MQTT settings from database
                server_config.config['mqtt_broker'] = settings.get('mqtt_broker', 'localhost')
                server_config.config['mqtt_port'] = int(settings.get('mqtt_port', '1883')) if settings.get('mqtt_port') else 1883
                server_config.config['mqtt_username'] = settings.get('mqtt_username', '')
                server_config.config['mqtt_password'] = settings.get('mqtt_password', '')
                
                logger.info(f"Loaded MQTT settings from database - broker: {server_config.mqtt_broker}:{server_config.mqtt_port}, username: {server_config.mqtt_username}")
                
                # Recreate MQTT server with loaded settings
                mqtt_server = MQTTServer(database, server_config)
                queue_manager = QueueManager(database, mqtt_server)
                
                # Start MQTT server
                if await mqtt_server.start():
                    logger.info("MQTT server started successfully")
                    # Start queue manager
                    await queue_manager.start()
                else:
                    logger.warning("MQTT server failed to start - check configuration")
            else:
                logger.info("MQTT not configured in database - please configure via web interface Settings page")
                logger.info("Server will continue without MQTT functionality")
        except Exception as e:
            logger.error(f"Failed to load MQTT settings from database: {e}")
    
    yield
    
    if mqtt_server:
        # Stop queue manager
        await queue_manager.stop()
        
        # Stop MQTT server
        await mqtt_server.stop()
    
    # Close database connection
    await database.close()
    database.save_server_log("server_stopped", "Admin Server stopped", "INFO")
    logger.info("LabelBerry Admin Server stopped")


app = FastAPI(
    title="LabelBerry API",
    version="1.0.0",
    lifespan=lifespan,
    # Disable automatic docs in production for security
    # Set ENABLE_DOCS=false in production environment
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MQTT settings are now loaded in the lifespan handler above

# Add session middleware for authentication
SECRET_KEY = secrets.token_urlsafe(32)  # In production, load from environment variable
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static files and templates removed - using Next.js frontend instead
# templates = Jinja2Templates(directory=Path(__file__).parent.parent / "web" / "templates")


# Authentication dependencies
async def require_login(request: Request):
    """Check if user is logged in"""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.session["user"]

security = HTTPBearer()

async def require_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for API calls"""
    api_key = credentials.credentials
    if not database.verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    # If already logged in, redirect to dashboard
    if "user" in request.session:
        return RedirectResponse(url="/", status_code=302)
    
    # Return JSON instead of template - using Next.js frontend
    return JSONResponse({"message": "Please use the Next.js frontend for login"})


@app.post("/auth/login", response_model=ApiResponse)
async def api_login(request: Request):
    """API endpoint for NextAuth authentication"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Verify credentials
        if await database.verify_user_async(username, password):
            # Store user in session
            request.session["user"] = username
            
            return ApiResponse(
                success=True,
                message="Login successful",
                data={
                    "user": {
                        "id": "1",
                        "username": username,
                        "email": f"{username}@labelberry.local"
                    }
                }
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/login")
async def login(request: Request):
    """Handle legacy login - kept for backward compatibility"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        remember = data.get("remember", False)
        
        if database.verify_user(username, password):
            request.session["user"] = username
            # Log successful login
            database.save_server_log("login_success", f"User '{username}' logged in successfully")
            # If remember me, extend session (this would need more implementation)
            return JSONResponse({"success": True, "message": "Login successful"})
        else:
            # Log failed login
            database.save_server_log("login_failed", f"Failed login attempt for user '{username}'", "WARNING")
            return JSONResponse({"success": False, "message": "Invalid username or password"}, status_code=401)
    except Exception as e:
        logger.error(f"Login error: {e}")
        return JSONResponse({"success": False, "message": "Login failed"}, status_code=500)


@app.get("/logout")
async def logout(request: Request):
    """Handle logout"""
    request.session.clear()
    return RedirectResponse(url="/login?message=logout", status_code=302)


@app.post("/api/change-password")
async def change_password(request: Request):
    """Change user password"""
    # Check if user is logged in
    if "user" not in request.session:
        return JSONResponse({"success": False, "message": "Not authenticated"}, status_code=401)
    
    try:
        data = await request.json()
        current_password = data.get("current_password")
        new_password = data.get("new_password")
        username = request.session["user"]
        
        # Verify current password
        if not database.verify_user(username, current_password):
            return JSONResponse({"success": False, "message": "Current password is incorrect"}, status_code=401)
        
        # Update password
        if database.update_user_password(username, new_password):
            return JSONResponse({"success": True, "message": "Password changed successfully"})
        else:
            return JSONResponse({"success": False, "message": "Failed to update password"}, status_code=500)
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return JSONResponse({"success": False, "message": "Failed to change password"}, status_code=500)


@app.post("/api/change-username")
async def change_username(request: Request):
    """Change username"""
    # Check if user is logged in
    if "user" not in request.session:
        return JSONResponse({"success": False, "message": "Not authenticated"}, status_code=401)
    
    try:
        data = await request.json()
        new_username = data.get("new_username")
        current_password = data.get("current_password")
        old_username = request.session["user"]
        
        # Validate new username
        if not new_username or len(new_username) < 3:
            return JSONResponse({"success": False, "message": "Username must be at least 3 characters"}, status_code=400)
        
        # Verify current password for security
        if not database.verify_user(old_username, current_password):
            return JSONResponse({"success": False, "message": "Current password is incorrect"}, status_code=401)
        
        # Update username
        if database.update_username(old_username, new_username):
            # Update session with new username
            request.session["user"] = new_username
            return JSONResponse({"success": True, "message": "Username changed successfully"})
        else:
            return JSONResponse({"success": False, "message": "Username already exists or update failed"}, status_code=400)
    except Exception as e:
        logger.error(f"Username change error: {e}")
        return JSONResponse({"success": False, "message": "Failed to change username"}, status_code=500)


@app.get("/api/server-settings", response_model=ApiResponse)
async def get_server_settings(request: Request):
    """Get server settings"""
    # Check if user is logged in
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get base URL setting
        base_url = database.get_server_setting("base_url", "")
        
        return ApiResponse(
            success=True,
            message="Server settings retrieved successfully",
            data={"base_url": base_url}
        )
    except Exception as e:
        logger.error(f"Failed to get server settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get server settings")


@app.post("/api/server-settings", response_model=ApiResponse)
async def save_server_settings(request: Request, settings: Dict[str, Any]):
    """Save server settings"""
    # Check if user is logged in
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Save base URL if provided
        if "base_url" in settings:
            database.set_server_setting(
                "base_url", 
                settings["base_url"],
                "Base URL for LabelBerry API documentation examples"
            )
        
        return ApiResponse(
            success=True,
            message="Server settings saved successfully"
        )
    except Exception as e:
        logger.error(f"Failed to save server settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to save server settings")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main page - serves the dashboard"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login?next=/", status_code=302)
    return JSONResponse({"message": "Please use the Next.js frontend"})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page - redirect to dashboard with settings panel open"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    # Redirect to dashboard - settings are now inline
    return RedirectResponse(url="/#settings", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Legacy dashboard URL - redirects to root"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=301)


@app.get("/api/pis", response_model=ApiResponse)
async def list_pis():
    try:
        pis = await database.get_all_pis_async()
        label_sizes = await database.get_label_sizes_async()
        
        # Create a map of label sizes by ID
        label_size_map = {}
        for ls in label_sizes:
            label_size_map[ls.get('id')] = ls
        
        # Calculate jobs today for each printer
        jobs_today_map = {}
        if database.is_postgres:
            pool = await database.get_connection()
            async with pool.acquire() as conn:
                # Get jobs count for today for all printers
                rows = await conn.fetch("""
                    SELECT pi_id, COUNT(*) as jobs_today
                    FROM print_jobs
                    WHERE created_at >= CURRENT_DATE
                    GROUP BY pi_id
                """)
                for row in rows:
                    jobs_today_map[row['pi_id']] = row['jobs_today']
        
        pi_list = []
        for pi in pis:
            # Handle dict from database
            if isinstance(pi, dict):
                pi_dict = pi
            else:
                pi_dict = pi.model_dump()
            
            pi_id = pi_dict.get('id')
            device_id = pi_dict.get('device_id')
            
            # Check MQTT connection using device_id
            is_connected = mqtt_server.is_connected(device_id) if mqtt_server and device_id else False
            pi_dict["mqtt_connected"] = is_connected
            
            # Override status based on actual MQTT connection
            if is_connected:
                pi_dict["status"] = "online"
            elif not pi_dict.get("last_seen"):
                pi_dict["status"] = "offline"
            
            # Keep label_size as is - it's now stored directly in the pis table
            # Don't overwrite with None
            
            # Add metrics
            pi_dict["metrics"] = {
                "jobsToday": jobs_today_map.get(pi_id, 0),
                "failedJobs": 0,  # TODO: Calculate failed jobs
                "avgPrintTime": 0,  # TODO: Calculate average print time
                "uptime": "0 days"  # TODO: Calculate uptime
            }
                
            # Keep the database status if not connected (could be offline, error, etc.)
            pi_list.append(pi_dict)
        
        return ApiResponse(
            success=True,
            message="Pis retrieved",
            data={"pis": pi_list, "total": len(pi_list)}
        )
    except Exception as e:
        logger.error(f"Failed to list Pis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pis/{pi_id}", response_model=ApiResponse)
async def get_pi_details(pi_id: str):
    try:
        pi = await database.get_pi_by_id_async(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # pi is already a dict from async method
        pi_dict = pi
        device_id = pi.get('device_id', pi_id)
        is_connected = mqtt_server.is_connected(device_id)
        pi_dict["mqtt_connected"] = is_connected
        # Override status based on actual MQTT connection
        if is_connected:
            pi_dict["status"] = "online"
        pi_dict["config"] = await database.get_pi_config_async(pi_id)
        
        # Get label size details if assigned
        label_size_id = pi.get('label_size_id')
        if label_size_id:
            sizes = await database.get_label_sizes_async()
            for size in sizes:
                if size['id'] == label_size_id:
                    pi_dict["label_size"] = size
                    break
        
        return ApiResponse(
            success=True,
            message="Pi details retrieved",
            data=pi_dict
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Pi details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pis/register", response_model=ApiResponse)
async def register_pi_install(registration_data: Dict[str, Any]):
    """Register a new Pi during installation (no auth required for local network)"""
    try:
        # Create PiDevice from registration data
        device = PiDevice(
            id=registration_data.get("id"),
            friendly_name=registration_data.get("friendly_name", "Unnamed Pi"),
            api_key=registration_data.get("api_key"),
            printer_model=registration_data.get("printer_model")
        )
        
        logger.info(f"Registration request for device {device.id}")
        logger.info(f"  Name: {device.friendly_name}")
        logger.info(f"  Model: {device.printer_model}")
        logger.info(f"  API Key: {device.api_key[:20]}..." if len(device.api_key) > 20 else f"  API Key: {device.api_key}")
        
        # Check if Pi already exists - always use async version since we're in async function
        existing = await database.get_pi_by_id_async(device.id)
            
        if existing:
            logger.info(f"  Device {device.id} already exists, updating...")
            # Update existing Pi - always use async version since we're in async function
            success = await database.update_pi_async(device.id, {
                "api_key": device.api_key,
                "friendly_name": device.friendly_name,
                "printer_model": device.printer_model
            })
            if success:
                logger.info(f"  ✓ Successfully updated device {device.id}")
                database.save_server_log("printer_updated", f"Printer '{device.friendly_name}' updated", "INFO", 
                                        f"ID: {device.id}")
                return ApiResponse(
                    success=True,
                    message="Pi updated successfully",
                    data={"pi_id": device.id}
                )
            else:
                logger.error(f"  ✗ Failed to update device {device.id}")
                raise HTTPException(status_code=400, detail="Failed to update Pi")
        else:
            logger.info(f"  Device {device.id} is new, registering...")
            # Register new Pi - always use async version since we're in async function
            registered = await database.register_pi_async(device)
                
            if registered:
                logger.info(f"  ✓ Successfully registered device {device.id}")
                database.save_server_log("printer_registered", f"New printer '{device.friendly_name}' registered", "INFO",
                                        f"ID: {device.id}, Model: {device.printer_model}")
                return ApiResponse(
                    success=True,
                    message="Pi registered successfully",
                    data={"pi_id": device.id}
                )
            else:
                logger.error(f"  ✗ Failed to register device {device.id}")
                raise HTTPException(status_code=400, detail="Failed to register Pi")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register Pi during installation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pis", response_model=ApiResponse)
async def register_pi(device: PiDevice):
    try:
        if database.register_pi(device):
            return ApiResponse(
                success=True,
                message="Pi registered successfully",
                data={"pi_id": device.id}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to register Pi")
    except Exception as e:
        logger.error(f"Failed to register Pi: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/pis/{pi_id}", response_model=ApiResponse)
async def update_pi(pi_id: str, updates: Dict[str, Any]):
    try:
        logger.info(f"Updating Pi {pi_id} with data: {updates}")
        pi = await database.get_pi_by_id_async(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Use the update_pi method that only updates specified fields
        success = await database.update_pi_async(pi_id, updates)
        logger.info(f"Update result for Pi {pi_id}: {success}")
        if success:
            pi_name = pi.get('friendly_name') if isinstance(pi, dict) else pi.friendly_name
            database.save_server_log("printer_config_updated", f"Configuration updated for '{pi_name}'", "INFO",
                                    f"Updates: {list(updates.keys())}")
            return ApiResponse(
                success=True,
                message="Pi updated successfully",
                data={"pi_id": pi_id}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update Pi")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update Pi: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/pis/{pi_id}", response_model=ApiResponse)
async def delete_pi(pi_id: str):
    try:
        logger.info(f"Attempting to delete Pi: {pi_id}, is_postgres: {database.is_postgres}")
        
        # Use async version of get_pi_by_id since we're in async endpoint
        pi = await database.get_pi_by_id_async(pi_id)
            
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Disconnect MQTT if connected - use device_id for MQTT operations
        device_id = pi.get('device_id', pi_id)
        if mqtt_server and mqtt_server.is_connected(device_id):
            mqtt_server.disconnect(device_id)
        
        # Delete from database - always use async version in async endpoint
        deleted = await database.delete_pi_async(pi_id)
        if deleted:
            friendly_name = pi.get('friendly_name', 'Unknown')
            database.save_server_log("printer_deleted", f"Printer '{friendly_name}' deleted", "WARNING")
            return ApiResponse(
                success=True,
                message="Pi deleted successfully",
                data={"pi_id": pi_id}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to delete Pi")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete Pi: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/pis/{pi_id}/config", response_model=ApiResponse)
async def update_pi_config(pi_id: str, config: Dict[str, Any]):
    try:
        pi = await database.get_pi_by_id_async(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Update the configuration in the database
        success = await database.update_pi_config_async(pi_id, config)
        if success:
            # Get the device_id for MQTT communication
            device_id = pi.get('device_id', pi_id)
            
            # Send the config to the Pi via MQTT if it's connected
            if mqtt_server and mqtt_server.connected:
                if device_id in mqtt_server.connected_pis:
                    logger.info(f"Sending config update to Pi {device_id}: {config}")
                    await mqtt_server.send_config_to_pi(device_id, config)
                else:
                    logger.warning(f"Pi {device_id} not connected via MQTT, config saved but not sent")
            
            return ApiResponse(
                success=True,
                message="Configuration updated and sent to Pi",
                data={"pi_id": pi_id}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to update configuration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update Pi config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pis/{pi_id}/logs", response_model=ApiResponse)
async def get_pi_logs(pi_id: str, limit: int = 100):
    try:
        # Special case for server logs
        if pi_id == "__server__":
            logs = database.get_error_logs("__server__", limit)
            return ApiResponse(
                success=True,
                message="Server logs retrieved",
                data={"logs": logs, "total": len(logs)}
            )
        
        # Regular Pi logs
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        logs = database.get_error_logs(pi_id, limit)
        
        return ApiResponse(
            success=True,
            message="Logs retrieved",
            data={"logs": logs, "total": len(logs)}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pis/{pi_id}/metrics", response_model=ApiResponse)
async def get_pi_metrics(pi_id: str, hours: int = 24):
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        metrics = database.get_metrics(pi_id, hours)
        
        return ApiResponse(
            success=True,
            message="Metrics retrieved",
            data={"metrics": metrics, "total": len(metrics)}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Pi metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pis/{pi_id}/command", response_model=ApiResponse)
async def send_command(pi_id: str, command: Dict[str, Any]):
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        if not mqtt_server.is_connected(pi_id):
            raise HTTPException(status_code=503, detail="Pi is not connected")
        
        success = await mqtt_server.send_command(
            pi_id,
            command.get("command"),
            command.get("params")
        )
        
        if success:
            return ApiResponse(
                success=True,
                message="Command sent",
                data={"pi_id": pi_id, "command": command.get("command")}
            )
        else:
            raise HTTPException(status_code=503, detail="Failed to send command")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Store recently completed jobs for polling
recently_completed_jobs = {}

@app.get("/api/jobs/{job_id}/status", response_model=ApiResponse)
async def get_job_status(job_id: str):
    """Get the status of a print job"""
    try:
        # Check if job was recently completed
        if job_id in recently_completed_jobs:
            status = recently_completed_jobs[job_id]
            # Clean up old entries (keep for 30 seconds)
            if (datetime.utcnow() - status['timestamp']).total_seconds() > 30:
                del recently_completed_jobs[job_id]
            else:
                return ApiResponse(
                    success=True,
                    message="Job status retrieved",
                    data={"job_id": job_id, "status": status['status']}
                )
        
        # Otherwise check database
        job = await database.get_job_by_id_async(job_id) if hasattr(database, 'get_job_by_id_async') else None
        if job:
            return ApiResponse(
                success=True,
                message="Job status retrieved",
                data={"job_id": job_id, "status": job.get('status', 'unknown')}
            )
        else:
            return ApiResponse(
                success=True,
                message="Job not found or pending",
                data={"job_id": job_id, "status": "pending"}
            )
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/{job_id}/cancel", response_model=ApiResponse)
async def cancel_job(job_id: str):
    """Cancel a pending or processing job"""
    try:
        # Get the job details
        job = await database.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Only allow canceling pending or processing jobs
        if job.get('status') not in ['pending', 'processing']:
            raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job.get('status')}")
        
        # Update job status to cancelled
        await database.update_print_job_async(job_id, 'cancelled', 'Job cancelled by user')
        
        return ApiResponse(
            success=True,
            message="Job cancelled successfully",
            data={"job_id": job_id, "status": "cancelled"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/{pi_id}", response_model=ApiResponse)
async def get_pi_metrics(
    pi_id: str,
    timeRange: str = "24h"
):
    """Get performance metrics for a specific Pi"""
    try:
        # Convert time range to hours
        hours_map = {
            "1h": 1,
            "24h": 24,
            "7d": 168,
            "30d": 720
        }
        hours = hours_map.get(timeRange, 24)
        
        # Get metrics from database
        metrics = await database.get_metrics_async(pi_id, hours)
        
        return ApiResponse(
            success=True,
            message="Metrics retrieved",
            data={"metrics": metrics}
        )
    except Exception as e:
        logger.error(f"Failed to get metrics for Pi {pi_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/queue", response_model=ApiResponse)
async def get_queue_items(
    printerId: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """Get queue items with optional filters"""
    try:
        # Get all print jobs
        jobs = await database.get_print_jobs_async(
            pi_id=printerId,
            status=status if status != "all" else None,
            limit=limit
        )
        
        # Get printer information for each job
        pis = await database.get_all_pis_async()
        pi_map = {pi['id']: pi for pi in pis}
        
        # Format the queue items
        queue_items = []
        for job in jobs:
            pi = pi_map.get(job['pi_id'], {})
            queue_items.append({
                "id": job['id'],
                "printerId": job['pi_id'],
                "printerName": pi.get('friendly_name', 'Unknown Printer'),
                "status": job['status'],
                "zplSource": job.get('zpl_source', ''),
                "createdAt": job['created_at'].isoformat() if job.get('created_at') else '',
                "startedAt": job['started_at'].isoformat() if job.get('started_at') else None,
                "completedAt": job['completed_at'].isoformat() if job.get('completed_at') else None,
                "retryCount": job.get('retry_count', 0),
                "errorMessage": job.get('error_message')
            })
        
        return ApiResponse(
            success=True,
            message="Queue items retrieved",
            data={"items": queue_items}
        )
    except Exception as e:
        logger.error(f"Failed to get queue items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/jobs/clear-history", response_model=ApiResponse)
async def clear_print_history():
    """Clear all print job history"""
    try:
        # Get database connection
        if database.is_postgres:
            pool = await database.get_connection()
            async with pool.acquire() as conn:
                # Delete all print jobs
                result = await conn.execute("DELETE FROM print_jobs")
                # Extract the number of deleted rows from the result string
                deleted_count = int(result.split()[-1]) if result and ' ' in result else 0
                
                logger.info(f"Cleared {deleted_count} print jobs from history")
                
                return ApiResponse(
                    success=True,
                    message=f"Cleared {deleted_count} print job(s) from history",
                    data={"deleted_count": deleted_count}
                )
        else:
            # For SQLite, implement the deletion
            # This is a fallback, but the system should be using PostgreSQL
            return ApiResponse(
                success=False,
                message="Clear history not implemented for SQLite",
                data={}
            )
    except Exception as e:
        logger.error(f"Failed to clear print history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/{job_id}/retry", response_model=ApiResponse)
async def retry_job(job_id: str):
    """Retry a failed or cancelled job"""
    try:
        # Get the job details
        job = await database.get_job_by_id_async(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Create a new job with the same details
        new_job_id = await database.create_print_job_async(
            pi_id=job['pi_id'],
            zpl_source=job.get('zpl_source', 'retry'),
            zpl_content=job.get('zpl_content')
        )
        
        # If MQTT is connected, send the job immediately
        pi = await database.get_pi_by_id_async(job['pi_id'])
        if pi and mqtt_server and mqtt_server.connected:
            device_id = pi.get('device_id')
            if mqtt_server.is_connected(device_id):
                job_data = {
                    "job_id": new_job_id,
                    "zpl_source": job.get('zpl_source'),
                    "zpl_content": job.get('zpl_content')
                }
                success = await mqtt_server.send_print_job(device_id, job_data)
                if success:
                    await database.update_print_job_async(new_job_id, 'processing')
        
        return ApiResponse(
            success=True,
            message="Job restarted successfully",
            data={"old_job_id": job_id, "new_job_id": new_job_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pis/{pi_id}/test-print", response_model=ApiResponse)
async def send_test_print_to_pi(
    pi_id: str, 
    print_data: Optional[Dict[str, Any]] = None
):
    """Send test print job to Pi"""
    try:
        # Use default test label if no data provided
        if not print_data:
            from datetime import datetime
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print_data = {
                "zpl_raw": f"""^XA
^PW448
^LL252
^FO20,20^A0N,25,25^FDLabelBerry Test Print^FS
^FO20,50^A0N,20,20^FDPrinter Test Successful^FS
^FO20,80^A0N,18,18^FD{current_time}^FS
^FO20,110^GB400,2,2^FS
^FO20,120^A0N,16,16^FDDevice: Connected^FS
^FO20,145^A0N,16,16^FDMQTT: Active^FS
^FO20,170^A0N,16,16^FDStatus: Ready^FS
^FO20,200^BY2,3,40^BCN,,Y,N^FD12345678^FS
^XZ"""
            }
        pi = await database.get_pi_by_id_async(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Check MQTT connection and log status
        device_id = pi.get('device_id', pi_id)
        is_mqtt_connected = mqtt_server.is_connected(device_id)
        connected_pis = mqtt_server.get_connected_pis()
        logger.info(f"Test print for Pi {pi_id}: MQTT connected={is_mqtt_connected}, Connected Pis: {connected_pis}")
        
        # Send the test print via MQTT if the Pi is connected
        if mqtt_server and mqtt_server.connected:
            # Create print job in database to track result
            test_job_id = await database.create_print_job_async(
                pi_id=pi_id,
                zpl_source=print_data.get("zpl_url") or "test_print",
                zpl_content=print_data.get("zpl_raw")
            )
            
            # Send with job_id so we can track completion
            test_print_data = {
                "job_id": test_job_id,
                "zpl_raw": print_data.get("zpl_raw"),
                "zpl_url": print_data.get("zpl_url"),
                "priority": print_data.get("priority", 5)
            }
            
            # Send as a print job with the test data using device_id
            success = await mqtt_server.send_print_job(device_id, test_print_data)
            
            if success:
                friendly_name = pi.get('friendly_name', 'Unknown')
                database.save_server_log("test_print", f"Test print sent to '{friendly_name}'", "INFO")
                return ApiResponse(
                    success=True,
                    message="Test print job sent to printer",
                    data={"pi_id": pi_id, "job_id": test_job_id}
                )
            else:
                await database.update_print_job_async(test_job_id, "failed", "Failed to send to printer")
                return ApiResponse(
                    success=False,
                    message="Failed to send test print to printer",
                    data={"pi_id": pi_id}
                )
        
        # If MQTT not connected, try HTTP
        if hasattr(pi, 'local_ip') and pi.local_ip:
            try:
                response = requests.post(
                    f"http://{pi.local_ip}:5000/print",
                    json=print_data,
                    timeout=5
                )
                if response.status_code == 200:
                    return ApiResponse(
                        success=True,
                        message="Test print job sent via HTTP",
                        data={"pi_id": pi_id}
                    )
            except:
                pass
        
        # MQTT not connected - return error
        friendly_name = pi.get('friendly_name', 'Unknown')
        raise HTTPException(
            status_code=503,
            detail=f"Cannot send test print to '{friendly_name}' - MQTT broker not connected"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test print: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/print-queue/clear", response_model=ApiResponse)
async def clear_print_queue(
    pi_id: Optional[str] = None,
    _: dict = Depends(require_login)
):
    """Clear queued print jobs"""
    try:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            if pi_id:
                # Cancel ALL active jobs (queued, sent, processing) for this printer
                cursor.execute("""
                    UPDATE print_jobs 
                    SET status = 'cancelled' 
                    WHERE status IN ('queued', 'sent', 'processing') AND pi_id = ?
                """, (pi_id,))
            else:
                # Cancel ALL active jobs globally
                cursor.execute("""
                    UPDATE print_jobs 
                    SET status = 'cancelled' 
                    WHERE status IN ('queued', 'sent', 'processing')
                """)
            
            affected = cursor.rowcount
            
        return ApiResponse(
            success=True,
            message=f"Cancelled {affected} queued jobs",
            data={"cancelled_count": affected}
        )
    except Exception as e:
        logger.error(f"Failed to clear print queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/print-queue", response_model=ApiResponse)
async def get_print_queue(
    pi_id: Optional[str] = None,
    _: dict = Depends(require_login)
):
    """Get active print queue"""
    try:
        with database.get_connection() as conn:
            cursor = conn.cursor()
            if pi_id:
                cursor.execute("""
                    SELECT id, pi_id, status, source, created_at 
                    FROM print_jobs 
                    WHERE status IN ('queued', 'sent', 'processing') AND pi_id = ?
                    ORDER BY created_at DESC
                    LIMIT 50
                """, (pi_id,))
            else:
                cursor.execute("""
                    SELECT id, pi_id, status, source, created_at 
                    FROM print_jobs 
                    WHERE status IN ('queued', 'sent', 'processing')
                    ORDER BY created_at DESC
                    LIMIT 50
                """)
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    "id": row[0],
                    "pi_id": row[1],
                    "status": row[2],
                    "source": row[3],
                    "created_at": row[4]
                })
            
        return ApiResponse(
            success=True,
            message=f"Found {len(jobs)} active jobs",
            data={"jobs": jobs}
        )
    except Exception as e:
        logger.error(f"Failed to get print queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/print-history", response_model=ApiResponse)
async def get_print_history(
    pi_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _: dict = Depends(require_login)
):
    """Get print job history"""
    try:
        jobs = database.get_print_history(pi_id, limit, offset)
        return ApiResponse(
            success=True,
            message="Print history retrieved",
            data={"jobs": jobs, "total": len(jobs)}
        )
    except Exception as e:
        logger.error(f"Failed to get print history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/print-history", response_class=HTMLResponse)
async def print_history_page(request: Request):
    """Print history page"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login?next=/print-history", status_code=302)
    return JSONResponse({"message": "Please use the Next.js frontend"})


@app.get("/performance-metrics", response_class=HTMLResponse)
async def performance_metrics_page(request: Request):
    """Performance metrics page"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login?next=/performance-metrics", status_code=302)
    return JSONResponse({"message": "Please use the Next.js frontend"})


@app.post("/api/reprint", response_model=ApiResponse)
async def reprint_job(
    data: dict,
    _: dict = Depends(require_login)
):
    """Reprint a job to a selected printer - adds to queue like normal"""
    try:
        pi_id = data.get('pi_id')
        zpl_raw = data.get('zpl_raw')
        zpl_url = data.get('zpl_url')
        
        if not pi_id:
            raise HTTPException(status_code=400, detail="Printer ID is required")
        
        if not zpl_raw and not zpl_url:
            raise HTTPException(status_code=400, detail="ZPL content or URL is required")
        
        # Get the printer
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Printer not found")
        
        # Create print job and add to queue - let the queue manager handle it
        job = PrintJob(
            pi_id=pi_id,
            status=PrintJobStatus.QUEUED,  # Add to queue normally
            zpl_source=zpl_url if zpl_url else "raw",
            source="reprint",
            priority=5
        )
        
        # Save job to database
        database.save_print_job(
            job,
            zpl_content=zpl_raw,
            zpl_url=zpl_url
        )
        
        return ApiResponse(
            success=True,
            message=f"Reprint job added to queue for {pi.friendly_name}",
            data={"job_id": job.id, "pi_id": pi_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue reprint job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-label-preview")
async def generate_label_preview(
    request: Request,
    _: dict = Depends(require_login)
):
    """Generate a label preview using Labelary API"""
    try:
        # Get ZPL content from request body
        zpl_content = await request.body()
        zpl_content = zpl_content.decode('utf-8')
        
        if not zpl_content:
            raise HTTPException(status_code=400, detail="No ZPL content provided")
        
        # Validate ZPL has proper markers
        if not zpl_content.strip().startswith('^XA'):
            raise HTTPException(status_code=400, detail="Invalid ZPL: missing ^XA start marker")
        if not zpl_content.strip().endswith('^XZ'):
            raise HTTPException(status_code=400, detail="Invalid ZPL: missing ^XZ end marker")
        
        # Call Labelary API to generate preview
        # Default to 4x6 inch label at 203 dpi
        dpmm = 8  # 203 dpi = 8 dots per mm
        width = 4  # inches
        height = 6  # inches
        
        labelary_url = f"http://api.labelary.com/v1/printers/{dpmm}dpmm/labels/{width}x{height}/0/"
        
        headers = {
            'Accept': 'image/png',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(
            labelary_url,
            data=zpl_content.encode('utf-8'),
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            # Return the PNG image
            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=3600"}
            )
        else:
            # Try to get error message from Labelary
            error_msg = response.text if response.text else f"Labelary API error: {response.status_code}"
            
            # Check for common issues
            if "ERROR" in error_msg.upper() or response.status_code == 400:
                # Check if it's a test/config label with no visible content
                if any(marker in zpl_content for marker in ['^FDPrinter:', '^FDDevice:', '^FDStatus:', 'Test Print', 'Test - Small']):
                    raise HTTPException(
                        status_code=400, 
                        detail="Preview not available - ZPL may only contain positioning or configuration commands without visible elements"
                    )
                raise HTTPException(status_code=400, detail=f"Invalid ZPL: {error_msg}")
            
            raise HTTPException(status_code=response.status_code, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate label preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fetch-zpl-from-url", response_model=ApiResponse)
async def fetch_zpl_from_url(
    data: dict,
    _: dict = Depends(require_login)
):
    """Fetch ZPL content from a URL"""
    try:
        url = data.get('url')
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Fetch the ZPL content from the URL
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Get the content as text
        zpl_content = response.text
        
        # Basic validation - check if it looks like ZPL
        if not zpl_content or (not zpl_content.startswith('^XA') and '^XA' not in zpl_content):
            # Maybe it's binary or encoded differently, try to decode
            if not zpl_content:
                raise HTTPException(status_code=400, detail="Empty ZPL file")
        
        return ApiResponse(
            success=True,
            message="ZPL content fetched successfully",
            data={"zpl_content": zpl_content}
        )
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch ZPL from URL: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch ZPL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ZPL from URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-label-preview")
async def generate_label_preview(
    request: Request,
    _: dict = Depends(require_login)
):
    """Generate label preview using Labelary API"""
    try:
        # Get ZPL content from request body
        body = await request.body()
        zpl_content = body.decode('utf-8').strip()
        
        # Basic ZPL validation - be less strict
        if not zpl_content:
            raise HTTPException(status_code=400, detail="Empty ZPL content")
        
        # Check for basic ZPL structure (case-insensitive)
        zpl_upper = zpl_content.upper()
        if not ('^XA' in zpl_upper):
            raise HTTPException(status_code=400, detail="Invalid ZPL - missing ^XA start command")
        
        if not ('^XZ' in zpl_upper):
            raise HTTPException(status_code=400, detail="Invalid ZPL - missing ^XZ end command")
        
        # Labelary API parameters
        dpmm = 8  # 203 dpi (8 dots per mm)
        width = 4  # 4 inches wide
        height = 6  # 6 inches tall
        
        # Make request to Labelary API
        response = requests.post(
            f"https://api.labelary.com/v1/printers/{dpmm}dpmm/labels/{width}x{height}/0/",
            data=zpl_content,
            headers={
                'Accept': 'image/png',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            # Check if we actually got an image
            if len(response.content) > 0 and response.headers.get('content-type', '').startswith('image'):
                # Return the image directly
                from fastapi.responses import Response
                return Response(
                    content=response.content,
                    media_type="image/png",
                    headers={
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            else:
                # Empty response or not an image
                raise HTTPException(status_code=400, detail="No label image generated - check ZPL syntax")
        else:
            # Return error message
            error_text = response.text
            
            # Common Labelary errors
            if 'Requested 1st label but ZPL generated no labels' in error_text:
                # This ZPL is valid but doesn't produce a visible label
                raise HTTPException(
                    status_code=400, 
                    detail="Preview not available - ZPL may only contain positioning or configuration commands without visible elements"
                )
            elif 'ERROR' in error_text:
                # Extract just the error message
                error_msg = error_text.replace('ERROR: ', '').strip()
                raise HTTPException(status_code=400, detail=f"ZPL Error: {error_msg}")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Preview generation failed: {error_text[:200]}")
    
    except requests.RequestException as e:
        logger.error(f"Labelary API request failed: {e}")
        raise HTTPException(status_code=503, detail="Preview service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate label preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=ApiResponse)
async def get_job_status(job_id: str, _: dict = Depends(require_login)):
    """Get job status - for tracking test prints"""
    try:
        job = database.get_print_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return ApiResponse(
            success=True,
            message="Job retrieved",
            data=job if isinstance(job, dict) else (job.model_dump() if hasattr(job, 'model_dump') else job.__dict__)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/retry", response_model=ApiResponse)
async def retry_failed_job(job_id: str, _: dict = Depends(require_login)):
    """Manually retry a failed print job"""
    try:
        job = database.get_print_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is failed
        if job['status'] not in ['failed', 'error']:
            raise HTTPException(status_code=400, detail=f"Job is not in failed state (current: {job['status']})")
        
        # Check if job is within 24 hour retry window
        from datetime import datetime, timedelta
        job_created = datetime.fromisoformat(job['created_at']) if isinstance(job['created_at'], str) else job['created_at']
        job_age = datetime.utcnow() - job_created
        
        if job_age > timedelta(hours=24):
            raise HTTPException(status_code=400, detail="Job is older than 24 hours and cannot be retried")
        
        # Reset job to queued for retry
        database.update_job_status(job_id, 'queued')
        database.increment_job_retry(job_id)
        
        # If Pi is online, send immediately
        pi_id = job['pi_id']
        if mqtt_server.is_connected(pi_id):
            success = await mqtt_server.send_command(
                pi_id,
                "print",
                {
                    "job_id": job_id,
                    "zpl_raw": job.get('zpl_content') or (job['zpl_source'] if job.get('zpl_source') and not job['zpl_source'].startswith('http') else None),
                    "zpl_url": job.get('zpl_url') or (job['zpl_source'] if job.get('zpl_source') and job['zpl_source'].startswith('http') else None),
                    "priority": job.get('priority', 5)
                }
            )
            
            if success:
                database.update_job_status(job_id, 'sent')
                return ApiResponse(
                    success=True,
                    message="Job sent for retry",
                    data={"job_id": job_id, "status": "sent"}
                )
        
        # Pi offline, job will be sent when it comes online
        return ApiResponse(
            success=True,
            message="Job queued for retry",
            data={"job_id": job_id, "status": "queued"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pis/{pi_id}/print", response_model=ApiResponse)
async def send_print_to_pi(
    pi_id: str, 
    print_data: Dict[str, Any],
    api_key: str = Depends(require_api_key)
):
    """Send print job to Pi - Smart routing: direct send if online, queue if offline
    
    Parameters:
    - wait_for_completion (bool): Wait for print to complete before returning (default: true)
    - timeout (int): Max seconds to wait for completion (default: 30, max: 60)
    """
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Get wait parameters
        wait_for_completion = print_data.get("wait_for_completion", True)
        timeout = min(print_data.get("timeout", 30), 60)  # Cap at 60 seconds
        
        # Create print job object
        job = PrintJob(
            pi_id=pi_id,
            zpl_source=print_data.get("zpl_raw") or print_data.get("zpl_url", ""),
            priority=print_data.get("priority", 5),
            source="api"
        )
        
        # Smart routing: Check if Pi is connected
        if mqtt_server.is_connected(pi_id):
            # Pi is online - try to send directly
            success = await mqtt_server.send_command(
                pi_id,
                "print",
                {
                    "job_id": job.id,
                    "zpl_raw": print_data.get("zpl_raw"),
                    "zpl_url": print_data.get("zpl_url"),
                    "priority": job.priority
                }
            )
            
            if success:
                # Save job with 'sent' status and ZPL content
                job.status = "sent"
                job.sent_at = datetime.utcnow()
                database.save_print_job(
                    job,
                    zpl_content=print_data.get("zpl_raw"),
                    zpl_url=print_data.get("zpl_url")
                )
                
                # If wait_for_completion is true, wait for the job to complete
                if wait_for_completion:
                    import asyncio
                    start_time = asyncio.get_event_loop().time()
                    
                    while asyncio.get_event_loop().time() - start_time < timeout:
                        await asyncio.sleep(0.5)  # Check every 500ms
                        
                        # Get updated job status
                        updated_job = database.get_print_job(job.id)
                        if updated_job:
                            status = updated_job.get('status')
                            
                            if status == 'completed':
                                return ApiResponse(
                                    success=True,
                                    message="Print job completed successfully",
                                    data={
                                        "job_id": job.id,
                                        "pi_id": pi_id,
                                        "status": "completed"
                                    }
                                )
                            elif status == 'failed':
                                error_msg = updated_job.get('error_message', 'Print failed')
                                raise HTTPException(
                                    status_code=500, 
                                    detail=f"Print job failed: {error_msg}"
                                )
                    
                    # Timeout reached
                    raise HTTPException(
                        status_code=504,
                        detail=f"Print job timed out after {timeout} seconds. Job ID: {job.id}"
                    )
                else:
                    # Return immediately without waiting
                    return ApiResponse(
                        success=True,
                        message="Print job sent to Pi (async mode)",
                        data={
                            "job_id": job.id,
                            "pi_id": pi_id,
                            "status": "sent",
                            "note": "Poll /api/jobs/{job_id} to check status"
                        }
                    )
        
        # Pi is offline or send failed - queue the job
        if queue_manager and queue_manager.add_job_to_queue(
            job,
            zpl_content=print_data.get("zpl_raw"),
            zpl_url=print_data.get("zpl_url")
        ):
            database.save_server_log(
                "job_queued",
                f"Print job queued for offline Pi '{pi.friendly_name}'",
                "INFO",
                f"Job ID: {job.id}"
            )
            
            # Get queue position
            queued_jobs = database.get_queued_jobs(pi_id)
            queue_position = next((i for i, j in enumerate(queued_jobs) if j['id'] == job.id), 0) + 1
            
            return ApiResponse(
                success=True,
                message="Print job queued (Pi offline)",
                data={
                    "job_id": job.id,
                    "pi_id": pi_id,
                    "status": "queued",
                    "queue_position": queue_position
                }
            )
        elif not queue_manager:
            # In local mode without queue manager
            return ApiResponse(
                success=False,
                message="Queue manager not available in local mode",
                data={"job_id": job.id}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to queue print job")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send print job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pis/{pi_id}/jobs", response_model=ApiResponse)
async def get_pi_jobs(pi_id: str, limit: int = 100):
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        jobs = database.get_print_jobs(pi_id, limit)
        
        return ApiResponse(
            success=True,
            message="Jobs retrieved",
            data={"jobs": [job.model_dump() for job in jobs], "total": len(jobs)}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Pi jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/stats", response_model=ApiResponse)
async def get_dashboard_stats():
    try:
        # Use async version for PostgreSQL
        if database.is_postgres:
            stats = await database.get_dashboard_stats_async()
        else:
            stats = database.get_dashboard_stats()
        
        # Add connected printers count if MQTT server is available
        if mqtt_server:
            stats["connected_pis"] = len(mqtt_server.get_connected_pis())
        else:
            stats["connected_pis"] = 0
        
        return ApiResponse(
            success=True,
            message="Dashboard stats retrieved",
            data=stats
        )
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Recent jobs endpoint for dashboard
@app.get("/api/recent-jobs", response_model=ApiResponse)
async def get_recent_jobs(limit: int = 50):
    """Get recent print jobs across all printers"""
    try:
        jobs = await database.get_print_jobs_async(status=None, limit=limit)
        
        # Format jobs for frontend
        formatted_jobs = []
        for job in jobs:
            pi = await database.get_pi_by_id_async(job.get('pi_id'))
            formatted_jobs.append({
                "id": job.get('id'),
                "printerName": pi.get('friendly_name') if pi else 'Unknown',
                "status": job.get('status'),
                "createdAt": job.get('created_at'),
                "completedAt": job.get('completed_at'),
                "errorMessage": job.get('error_message'),
                "source": job.get('zpl_source', 'manual')
            })
        
        return ApiResponse(
            success=True,
            message="Recent jobs retrieved",
            data={"jobs": formatted_jobs}
        )
    except Exception as e:
        logger.error(f"Failed to get recent jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Recent alerts endpoint for dashboard
@app.get("/api/recent-alerts", response_model=ApiResponse)
async def get_recent_alerts(limit: int = 20):
    """Get recent system alerts and notifications"""
    try:
        alerts = []
        
        # Get recent error logs
        error_logs = await database.get_error_logs_async(resolved=None, limit=limit)
        for error in error_logs:
            pi = await database.get_pi_by_id_async(error.get('pi_id'))
            alerts.append({
                "type": "error",
                "severity": "high" if error.get('error_type') == 'connection_lost' else "medium",
                "message": error.get('message'),
                "printerName": pi.get('friendly_name') if pi else 'Unknown',
                "timestamp": error.get('created_at'),
                "icon": "AlertCircle"
            })
        
        # Get printer status for connection alerts
        pis = await database.get_all_pis_async()
        for pi in pis:
            if pi.get('status') == 'offline':
                alerts.append({
                    "type": "warning",
                    "severity": "high",
                    "message": f"{pi.get('friendly_name', 'Unknown')} is offline",
                    "printerName": pi.get('friendly_name', 'Unknown'),
                    "timestamp": pi.get('updated_at') or pi.get('created_at'),
                    "icon": "AlertCircle"
                })
            elif pi.get('status') == 'error':
                alerts.append({
                    "type": "error",
                    "severity": "high",
                    "message": f"{pi.get('friendly_name', 'Unknown')} has an error",
                    "printerName": pi.get('friendly_name', 'Unknown'),
                    "timestamp": pi.get('updated_at') or pi.get('created_at'),
                    "icon": "AlertCircle"
                })
        
        # Check for high queue warnings
        stats = await database.get_dashboard_stats_async() if database.is_postgres else database.get_dashboard_stats()
        if stats.get('queueLength', 0) > 10:
            alerts.insert(0, {
                "type": "warning",
                "severity": "medium",
                "message": f"High queue: {stats['queueLength']} jobs pending",
                "printerName": "System",
                "timestamp": datetime.now().isoformat(),
                "icon": "AlertCircle"
            })
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '', reverse=True)
        
        return ApiResponse(
            success=True,
            message="Recent alerts retrieved",
            data={"alerts": alerts[:limit]}
        )
    except Exception as e:
        logger.error(f"Failed to get recent alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MQTT endpoint removed - using MQTT instead


@app.post("/api/keys", response_model=ApiResponse)
async def create_api_key(
    request: Request,
    current_user: str = Depends(require_login)
):
    """Create a new API key"""
    try:
        data = await request.json()
        name = data.get("name")
        description = data.get("description", "")
        
        if not name:
            raise HTTPException(status_code=400, detail="Key name is required")
        
        api_key = database.create_api_key(name, description, current_user)
        
        if api_key:
            return ApiResponse(
                success=True,
                message="API key created successfully",
                data={"api_key": api_key, "name": name}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create API key")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/keys", response_model=ApiResponse)
async def list_api_keys(current_user: str = Depends(require_login)):
    """List all API keys"""
    try:
        keys = database.list_api_keys()
        return ApiResponse(
            success=True,
            message="API keys retrieved",
            data={"keys": keys}
        )
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/keys/{key_id}", response_model=ApiResponse)
async def delete_api_key(
    key_id: int,
    current_user: str = Depends(require_login)
):
    """Delete an API key"""
    try:
        if database.delete_api_key(key_id):
            return ApiResponse(
                success=True,
                message="API key deleted successfully",
                data={"key_id": key_id}
            )
        else:
            raise HTTPException(status_code=404, detail="API key not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/keys/{key_id}/revoke", response_model=ApiResponse)
async def revoke_api_key(
    key_id: int,
    current_user: str = Depends(require_login)
):
    """Revoke an API key"""
    try:
        if database.revoke_api_key(key_id):
            return ApiResponse(
                success=True,
                message="API key revoked successfully",
                data={"key_id": key_id}
            )
        else:
            raise HTTPException(status_code=404, detail="API key not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Queue Management Endpoints

@app.get("/api/queue", response_model=ApiResponse)
async def get_all_queued_jobs(current_user: str = Depends(require_login)):
    """Get all queued jobs across all Pis"""
    try:
        jobs = database.get_all_queued_jobs()
        stats = database.get_queue_stats()
        
        return ApiResponse(
            success=True,
            message="Queue retrieved",
            data={
                "jobs": jobs,
                "stats": stats
            }
        )
    except Exception as e:
        logger.error(f"Failed to get queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/queue/{pi_id}", response_model=ApiResponse)
async def get_pi_queue(pi_id: str, current_user: str = Depends(require_login)):
    """Get queued jobs for a specific Pi"""
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        jobs = database.get_queued_jobs(pi_id, limit=100)
        stats = database.get_queue_stats(pi_id)
        
        return ApiResponse(
            success=True,
            message="Pi queue retrieved",
            data={
                "jobs": jobs,
                "stats": stats
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Pi queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/queue/job/{job_id}", response_model=ApiResponse)
async def cancel_job(job_id: str, current_user: str = Depends(require_login)):
    """Cancel a queued job"""
    try:
        if database.cancel_job(job_id):
            database.save_server_log("job_cancelled", f"Job {job_id} cancelled by user", "INFO")
            return ApiResponse(
                success=True,
                message="Job cancelled",
                data={"job_id": job_id}
            )
        else:
            raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/queue/job/{job_id}/retry", response_model=ApiResponse)
async def retry_job(job_id: str, current_user: str = Depends(require_login)):
    """Retry a failed job"""
    try:
        job = database.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != 'failed':
            raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
        
        # Reset job to queued status
        database.update_job_status(job_id, 'queued')
        database.save_server_log("job_retry", f"Job {job_id} manually retried", "INFO")
        
        return ApiResponse(
            success=True,
            message="Job queued for retry",
            data={"job_id": job_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/queue/{pi_id}/clear", response_model=ApiResponse)
async def clear_pi_queue(pi_id: str, current_user: str = Depends(require_login)):
    """Clear all queued jobs for a Pi"""
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        cancelled_count = database.clear_queue(pi_id)
        database.save_server_log(
            "queue_cleared",
            f"Cleared {cancelled_count} jobs from '{pi.friendly_name}' queue",
            "WARNING"
        )
        
        return ApiResponse(
            success=True,
            message=f"Cancelled {cancelled_count} jobs",
            data={
                "pi_id": pi_id,
                "cancelled_count": cancelled_count
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/queue/job/{job_id}/priority", response_model=ApiResponse)
async def update_job_priority(
    job_id: str,
    request: Request,
    current_user: str = Depends(require_login)
):
    """Update job priority (for reordering queue)"""
    try:
        data = await request.json()
        priority = data.get("priority")
        
        if priority is None or not (1 <= priority <= 10):
            raise HTTPException(status_code=400, detail="Priority must be between 1 and 10")
        
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE print_jobs SET priority = ? WHERE id = ? AND status = 'queued'",
                (priority, job_id)
            )
            
            if cursor.rowcount > 0:
                return ApiResponse(
                    success=True,
                    message="Job priority updated",
                    data={"job_id": job_id, "priority": priority}
                )
            else:
                raise HTTPException(status_code=404, detail="Job not found or not queued")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job priority: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/label-sizes", response_model=ApiResponse)
async def get_label_sizes():
    """Get all available label sizes"""
    try:
        sizes = database.get_label_sizes()
        return ApiResponse(
            success=True,
            message="Label sizes retrieved",
            data={"sizes": sizes}
        )
    except Exception as e:
        logger.error(f"Failed to get label sizes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/label-sizes", response_model=ApiResponse)
async def add_label_size(
    request: Request,
    current_user: str = Depends(require_login)
):
    """Add a new label size"""
    try:
        data = await request.json()
        name = data.get("name")
        width = data.get("width")
        height = data.get("height")
        
        if not all([name, width, height]):
            raise HTTPException(status_code=400, detail="Name, width, and height are required")
        
        size_id = database.add_label_size(name, width, height)
        
        if size_id:
            return ApiResponse(
                success=True,
                message="Label size added successfully",
                data={"id": size_id}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to add label size (may already exist)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add label size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/label-sizes/{size_id}", response_model=ApiResponse)
async def delete_label_size(
    size_id: int,
    current_user: str = Depends(require_login)
):
    """Delete a label size"""
    try:
        if database.delete_label_size(size_id):
            return ApiResponse(
                success=True,
                message="Label size deleted successfully",
                data={"id": size_id}
            )
        else:
            raise HTTPException(status_code=400, detail="Cannot delete default size or size in use")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete label size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api-docs")
async def api_documentation_redirect():
    """Redirect to the actual API docs if enabled"""
    if os.getenv("ENABLE_DOCS", "true").lower() == "true":
        return RedirectResponse(url="/docs", status_code=302)
    else:
        raise HTTPException(status_code=404, detail="API documentation is disabled in production. Set ENABLE_DOCS=true to enable.")


@app.get("/swagger-docs", response_class=HTMLResponse)
async def swagger_docs(request: Request, current_user: str = Depends(require_login)):
    """Protected Swagger documentation - requires authentication"""
    if os.getenv("ENABLE_DOCS", "false").lower() == "true":
        # Redirect to the actual docs if they're enabled
        return RedirectResponse(url="/docs")
    else:
        # Return a simple message if docs are disabled
        return HTMLResponse(content="""
        <html>
            <head>
                <title>API Documentation</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }
                    .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    h1 { color: #333; }
                    p { color: #666; line-height: 1.6; }
                    .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>LabelBerry API Documentation</h1>
                    <div class="warning">
                        <strong>⚠️ Interactive API documentation is disabled for security reasons.</strong>
                    </div>
                    <p>The interactive API documentation (Swagger UI) has been disabled in production to prevent unauthorized API access.</p>
                    <p>To enable documentation for development:</p>
                    <ol>
                        <li>Set the environment variable: <code>ENABLE_DOCS=true</code></li>
                        <li>Restart the LabelBerry admin service</li>
                        <li>Access the docs at <code>/docs</code></li>
                    </ol>
                    <p><strong>Note:</strong> Only enable documentation in secure development environments.</p>
                </div>
            </body>
        </html>
        """)


@app.get("/api/server-info")
async def get_server_info():
    """Get server information including local IP address"""
    import socket
    
    # Get local IP address
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        # Fallback to localhost if unable to determine
        local_ip = "127.0.0.1"
    
    return {
        "local_ip": local_ip,
        "port": 8080,  # Default port for LabelBerry
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connected_pis": len(mqtt_server.get_connected_pis())
    }


# ============== Settings API Endpoints ==============

@app.post("/api/change-username", response_model=ApiResponse)
async def change_username(
    data: dict,
    request: Request,
    _: dict = Depends(require_login)
):
    """Change username"""
    try:
        new_username = data.get('new_username')
        password = data.get('password')
        
        if not new_username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Verify current password
        current_user = request.session.get('user')
        if not database.verify_admin_password(current_user, password):
            raise HTTPException(status_code=401, detail="Invalid password")
        
        # Update username
        if database.update_admin_username(current_user, new_username):
            request.session['user'] = new_username
            return ApiResponse(
                success=True,
                message="Username updated successfully"
            )
        else:
            raise HTTPException(status_code=400, detail="Username already exists")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change username: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/change-password", response_model=ApiResponse)
async def change_password(
    data: dict,
    request: Request,
    _: dict = Depends(require_login)
):
    """Change password"""
    try:
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            raise HTTPException(status_code=400, detail="Both passwords required")
        
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Verify current password
        current_user = request.session.get('user')
        if not database.verify_admin_password(current_user, current_password):
            raise HTTPException(status_code=401, detail="Invalid current password")
        
        # Update password
        if database.update_admin_password(current_user, new_password):
            return ApiResponse(
                success=True,
                message="Password updated successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to update password")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/api-keys", response_model=ApiResponse)
async def get_api_keys():
    """Get all API keys"""
    try:
        keys = await database.get_api_keys_async()
        return ApiResponse(
            success=True,
            message="API keys retrieved successfully",
            data={"keys": keys}
        )
    except Exception as e:
        logger.error(f"Failed to get API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/api-keys", response_model=ApiResponse)
async def create_api_key(
    data: dict
):
    """Create new API key"""
    try:
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            raise HTTPException(status_code=400, detail="Key name is required")
        
        # Save to database (database generates the key)
        result = await database.create_api_key_async(name, description)
        
        return ApiResponse(
            success=True,
            message="API key created successfully",
            data={"id": result.get('id'), "key": result.get('key')}
        )
        
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/api-keys/{key_id}", response_model=ApiResponse)
async def delete_api_key(
    key_id: str
):
    """Delete API key"""
    try:
        if await database.delete_api_key_async(key_id):
            return ApiResponse(
                success=True,
                message="API key deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="API key not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/label-sizes", response_model=ApiResponse)
async def get_label_sizes(_: dict = Depends(require_login)):
    """Get all label sizes"""
    try:
        sizes = database.get_label_sizes()
        return ApiResponse(
            success=True,
            message="Label sizes retrieved successfully",
            data={"sizes": sizes}
        )
    except Exception as e:
        logger.error(f"Failed to get label sizes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/label-sizes", response_model=ApiResponse)
async def create_label_size(
    data: dict,
    _: dict = Depends(require_login)
):
    """Create new label size"""
    try:
        name = data.get('name')
        width = data.get('width')
        height = data.get('height')
        description = data.get('description', '')
        
        if not name or not width or not height:
            raise HTTPException(status_code=400, detail="Name, width, and height are required")
        
        # Save to database
        size_id = database.create_label_size(name, width, height, description)
        
        return ApiResponse(
            success=True,
            message="Label size created successfully",
            data={"id": size_id}
        )
        
    except Exception as e:
        logger.error(f"Failed to create label size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/label-sizes/{size_id}", response_model=ApiResponse)
async def delete_label_size(
    size_id: str,
    _: dict = Depends(require_login)
):
    """Delete label size"""
    try:
        if database.delete_label_size(size_id):
            return ApiResponse(
                success=True,
                message="Label size deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Label size not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete label size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mqtt-status", response_model=ApiResponse)
async def get_mqtt_status():
    """Get MQTT broker connection status"""
    try:
        global mqtt_server
        
        # Check if mqtt_server exists and has a connected attribute
        is_connected = False
        broker_info = None
        
        if mqtt_server:
            # Check the connected attribute
            is_connected = getattr(mqtt_server, 'connected', False)
            
            # Get broker info from config
            settings = await database.get_system_settings()
            broker_info = {
                "broker": settings.get('mqtt_broker', 'localhost'),
                "port": int(settings.get('mqtt_port', '1883')) if settings.get('mqtt_port') else 1883
            }
        
        return ApiResponse(
            success=True,
            message="MQTT status retrieved",
            data={
                "connected": is_connected,
                "broker": broker_info
            }
        )
    except Exception as e:
        logger.error(f"Failed to get MQTT status: {e}")
        return ApiResponse(
            success=False,
            message="Failed to get MQTT status",
            data={"connected": False}
        )


@app.get("/api/mqtt-settings", response_model=ApiResponse)
async def get_mqtt_settings():
    """Get MQTT broker settings from database"""
    try:
        settings = await database.get_system_settings()
        
        # Convert mqtt_port to int if it's a string
        mqtt_port = settings.get('mqtt_port', '1883')
        if isinstance(mqtt_port, str) and mqtt_port.isdigit():
            mqtt_port = int(mqtt_port)
        
        return ApiResponse(
            success=True,
            message="MQTT settings retrieved",
            data={
                "mqtt_broker": settings.get('mqtt_broker', 'localhost'),
                "mqtt_port": mqtt_port,
                "mqtt_username": settings.get('mqtt_username', ''),
                "mqtt_password": "********" if settings.get('mqtt_password') else None  # Don't send actual password
            }
        )
    except Exception as e:
        logger.error(f"Failed to get MQTT settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mqtt-settings", response_model=ApiResponse)
async def update_mqtt_settings(data: dict):
    """Update MQTT broker settings in database"""
    try:
        global mqtt_server, server_config
        
        logger.info(f"Received MQTT settings update: {data}")
        
        # Prepare settings to update
        mqtt_settings = {}
        if 'mqtt_broker' in data:
            mqtt_settings['mqtt_broker'] = data['mqtt_broker']
        if 'mqtt_port' in data:
            mqtt_settings['mqtt_port'] = str(data['mqtt_port'])
        if 'mqtt_username' in data:
            mqtt_settings['mqtt_username'] = data['mqtt_username']
        # Only update password if it's provided and not empty
        if 'mqtt_password' in data and data['mqtt_password'] and data['mqtt_password'].strip() != '' and data['mqtt_password'] != "********":
            mqtt_settings['mqtt_password'] = data['mqtt_password']
        
        logger.info(f"Prepared MQTT settings: {mqtt_settings}")
        
        # Save to database
        await database.update_mqtt_settings(mqtt_settings)
        
        # Update server config with new values from database  
        settings = await database.get_system_settings()
        if hasattr(server_config, 'config') and isinstance(server_config.config, dict):
            server_config.config['mqtt_broker'] = settings.get('mqtt_broker', 'localhost')
            server_config.config['mqtt_port'] = int(settings.get('mqtt_port', '1883'))
            server_config.config['mqtt_username'] = settings.get('mqtt_username', '')
            server_config.config['mqtt_password'] = settings.get('mqtt_password', '')
        
        # Restart MQTT connection if needed
        if mqtt_server:
            try:
                await mqtt_server.stop()
            except:
                pass
            # Update server config dict with the new settings
            server_config.config['mqtt_broker'] = settings.get('mqtt_broker', 'localhost')
            server_config.config['mqtt_port'] = int(settings.get('mqtt_port', '1883')) if settings.get('mqtt_port') else 1883
            server_config.config['mqtt_username'] = settings.get('mqtt_username', '')
            server_config.config['mqtt_password'] = settings.get('mqtt_password', '')
            
            # Create new MQTT server with updated config
            mqtt_server = MQTTServer(database, server_config)
            await mqtt_server.start()
        
        return ApiResponse(
            success=True,
            message="MQTT settings updated successfully",
            data={"status": "Settings saved and MQTT connection restarted"}
        )
    except Exception as e:
        logger.error(f"Failed to update MQTT settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)