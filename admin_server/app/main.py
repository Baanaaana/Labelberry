import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Form, Header
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
from .database import Database
from .websocket_server import ConnectionManager
from .queue_manager import QueueManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


database = Database()
connection_manager = ConnectionManager(database)
queue_manager = QueueManager(database, connection_manager)

# Set the queue manager reference in connection manager
connection_manager.queue_manager = queue_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LabelBerry Admin Server started")
    database.save_server_log("server_started", "Admin Server started", "INFO")
    
    # Start queue manager
    await queue_manager.start()
    
    yield
    
    # Stop queue manager
    await queue_manager.stop()
    
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

# Add session middleware for authentication
SECRET_KEY = secrets.token_urlsafe(32)  # In production, load from environment variable
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "web" / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "web" / "templates")

# Add cache busting version for static files
import time
STATIC_VERSION = int(time.time()) if os.getenv("DEBUG", "false").lower() == "true" else "13.3"
templates.env.globals['static_version'] = STATIC_VERSION


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
    
    return templates.TemplateResponse("login.html", {
        "request": request
    })


@app.post("/login")
async def login(request: Request):
    """Handle login"""
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
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login?next=/settings", status_code=302)
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Legacy dashboard URL - redirects to root"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=301)


@app.get("/api/pis", response_model=ApiResponse)
async def list_pis():
    try:
        pis = database.get_all_pis()
        label_sizes = database.get_label_sizes()
        
        # Create a map of label sizes by ID
        label_size_map = {}
        for ls in label_sizes:
            label_size_map[ls['id']] = ls
        
        pi_list = []
        for pi in pis:
            pi_dict = pi.model_dump()
            is_connected = connection_manager.is_connected(pi.id)
            pi_dict["websocket_connected"] = is_connected
            # Override status based on actual WebSocket connection
            if is_connected:
                pi_dict["status"] = "online"
            
            # Add label size details if available
            if pi.label_size_id and pi.label_size_id in label_size_map:
                pi_dict["label_size"] = label_size_map[pi.label_size_id]
            else:
                pi_dict["label_size"] = None
                
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
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        pi_dict = pi.model_dump()
        is_connected = connection_manager.is_connected(pi_id)
        pi_dict["websocket_connected"] = is_connected
        # Override status based on actual WebSocket connection
        if is_connected:
            pi_dict["status"] = "online"
        pi_dict["config"] = database.get_pi_config(pi_id)
        
        # Get label size details if assigned
        if pi.label_size_id:
            sizes = database.get_label_sizes()
            for size in sizes:
                if size['id'] == pi.label_size_id:
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
        
        # Check if Pi already exists
        existing = database.get_pi_by_id(device.id)
        if existing:
            logger.info(f"  Device {device.id} already exists, updating...")
            # Update existing Pi
            success = database.update_pi(device.id, {
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
            # Register new Pi
            if database.register_pi(device):
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
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Use the update_pi method that only updates specified fields
        if database.update_pi(pi_id, updates):
            database.save_server_log("printer_config_updated", f"Configuration updated for '{pi.friendly_name}'", "INFO",
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
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Disconnect WebSocket if connected
        if connection_manager.is_connected(pi_id):
            connection_manager.disconnect(pi_id)
        
        # Delete from database
        if database.delete_pi(pi_id):
            database.save_server_log("printer_deleted", f"Printer '{pi.friendly_name}' deleted", "WARNING")
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
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        if database.update_pi_config(pi_id, config):
            if connection_manager.is_connected(pi_id):
                await connection_manager.send_config_update(pi_id, config)
            
            return ApiResponse(
                success=True,
                message="Configuration updated",
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
        logger.error(f"Failed to get Pi logs: {e}")
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
        
        if not connection_manager.is_connected(pi_id):
            raise HTTPException(status_code=503, detail="Pi is not connected")
        
        success = await connection_manager.send_command(
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


@app.post("/api/pis/{pi_id}/test-print", response_model=ApiResponse)
async def send_test_print_to_pi(
    pi_id: str, 
    print_data: Dict[str, Any],
    _: dict = Depends(require_login)  # Require dashboard login instead of API key
):
    """Send test print job to Pi - Requires dashboard login"""
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Send print command through WebSocket if connected
        if connection_manager.is_connected(pi_id):
            # Create a temporary job to track the test print
            import uuid
            test_job_id = str(uuid.uuid4())
            
            # Store in database temporarily to track result
            test_job = PrintJob(
                id=test_job_id,
                pi_id=pi_id,
                zpl_source=print_data.get("zpl_raw") or print_data.get("zpl_url", ""),
                priority=print_data.get("priority", 5),
                source="test",
                status="pending"
            )
            database.save_print_job(
                test_job,
                zpl_content=print_data.get("zpl_raw"),
                zpl_url=print_data.get("zpl_url")
            )
            
            # Send with job_id so we can track completion
            test_print_data = {
                "job_id": test_job_id,
                "zpl_raw": print_data.get("zpl_raw"),
                "zpl_url": print_data.get("zpl_url"),
                "priority": print_data.get("priority", 5)
            }
            
            success = await connection_manager.send_command(
                pi_id,
                "print",
                test_print_data
            )
            
            if success:
                database.save_server_log("test_print", f"Test print sent to '{pi.friendly_name}'", "INFO")
                return ApiResponse(
                    success=True,
                    message="Test print job sent to printer",
                    data={"pi_id": pi_id, "job_id": test_job_id}
                )
            else:
                database.update_job_status(test_job_id, "failed", "Failed to send to printer")
                return ApiResponse(
                    success=False,
                    message="Failed to send test print to printer",
                    data={"pi_id": pi_id}
                )
        
        # If WebSocket not connected, try HTTP
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
        
        raise HTTPException(status_code=503, detail="Printer not connected")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test print: {e}")
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


@app.get("/print-history")
async def print_history_page(request: Request, current_user: str = Depends(require_login)):
    """Print history page"""
    return templates.TemplateResponse("print_history.html", {
        "request": request,
        "user": current_user
    })


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
        if connection_manager.is_connected(pi_id):
            success = await connection_manager.send_command(
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
        if connection_manager.is_connected(pi_id):
            # Pi is online - try to send directly
            success = await connection_manager.send_command(
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
        if queue_manager.add_job_to_queue(
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
        stats = database.get_dashboard_stats()
        stats["connected_pis"] = len(connection_manager.get_connected_pis())
        
        return ApiResponse(
            success=True,
            message="Dashboard stats retrieved",
            data=stats
        )
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/pi/{pi_id}")
async def websocket_endpoint(websocket: WebSocket, pi_id: str):
    logger.info(f"WebSocket connection attempt from Pi {pi_id}")
    
    auth_header = websocket.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning(f"Pi {pi_id} WebSocket rejected - missing auth header")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    api_key = auth_header.replace("Bearer ", "")
    pi = database.get_pi_by_api_key(api_key)
    
    if not pi:
        logger.warning(f"Pi {pi_id} WebSocket rejected - API key not found in database")
        logger.warning(f"  Provided API key: {api_key[:20]}..." if len(api_key) > 20 else f"  Provided API key: {api_key}")
        # Also check if this device ID exists with a different API key
        existing_pi = database.get_pi_by_id(pi_id)
        if existing_pi:
            logger.warning(f"  Device {pi_id} exists in database but with different API key")
            logger.warning(f"  Expected API key: {existing_pi.api_key[:20]}..." if len(existing_pi.api_key) > 20 else f"  Expected API key: {existing_pi.api_key}")
        else:
            logger.warning(f"  Device {pi_id} not found in database at all")
        await websocket.close(code=1008, reason="Invalid API key")
        return
    
    if pi.id != pi_id:
        logger.warning(f"Pi {pi_id} WebSocket rejected - API key belongs to different device")
        logger.warning(f"  API key belongs to device: {pi.id}")
        logger.warning(f"  Requested device: {pi_id}")
        await websocket.close(code=1008, reason="Device ID mismatch")
        return
    
    # Get client IP address
    client_ip = None
    if websocket.client:
        client_ip = websocket.client.host
        logger.info(f"Pi {pi_id} connecting from IP: {client_ip}")
        # Update the IP address in the database
        database.update_pi_ip_address(pi_id, client_ip)
        logger.info(f"Updated IP address for Pi {pi_id} to {client_ip}")
    else:
        logger.warning(f"Could not determine IP address for Pi {pi_id}")
    
    logger.info(f"Pi {pi_id} WebSocket authenticated - connecting...")
    await connection_manager.connect(pi_id, websocket)
    
    try:
        await connection_manager.handle_pi_message(pi_id, websocket)
    except WebSocketDisconnect:
        logger.info(f"Pi {pi_id} WebSocket disconnected")
        connection_manager.disconnect(pi_id)
    except Exception as e:
        logger.error(f"WebSocket error for Pi {pi_id}: {e}")
        connection_manager.disconnect(pi_id)


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
        width_mm = data.get("width_mm")
        height_mm = data.get("height_mm")
        
        if not all([name, width_mm, height_mm]):
            raise HTTPException(status_code=400, detail="Name, width, and height are required")
        
        size_id = database.add_label_size(name, width_mm, height_mm)
        
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


@app.get("/api-docs", response_class=HTMLResponse)
async def api_documentation(request: Request):
    """Interactive API documentation page - requires authentication"""
    # Check if user is logged in
    if "user" not in request.session:
        # Redirect to login page
        return RedirectResponse(url="/login?next=/api-docs", status_code=302)
    
    # Get base URL from settings
    base_url = database.get_server_setting("base_url", "")
    if not base_url:
        # Try to construct from request if not set
        base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    return templates.TemplateResponse("api_docs.html", {
        "request": request,
        "base_url": base_url
    })


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
        "connected_pis": len(connection_manager.get_connected_pis())
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)