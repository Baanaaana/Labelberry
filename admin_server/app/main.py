import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
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
    ApiResponse, PiStatus, PiConfig
)
from .database import Database
from .websocket_server import ConnectionManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


database = Database()
connection_manager = ConnectionManager(database)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LabelBerry Admin Server started")
    yield
    logger.info("LabelBerry Admin Server stopped")


app = FastAPI(
    title="LabelBerry API",
    version="1.0.0",
    lifespan=lifespan
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


# Authentication dependency
async def require_login(request: Request):
    """Check if user is logged in"""
    if "user" not in request.session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.session["user"]


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    # If already logged in, redirect to dashboard
    if "user" in request.session:
        return RedirectResponse(url="/", status_code=302)
    
    # Check if default credentials are still active
    show_default_creds = database.has_default_credentials()
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "show_default_credentials": show_default_creds
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
            # If remember me, extend session (this would need more implementation)
            return JSONResponse({"success": True, "message": "Login successful"})
        else:
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


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Main page - serves the dashboard"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    # Check if user is logged in
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=302)
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
        
        pi_list = []
        for pi in pis:
            pi_dict = pi.model_dump()
            is_connected = connection_manager.is_connected(pi.id)
            pi_dict["websocket_connected"] = is_connected
            # Override status based on actual WebSocket connection
            if is_connected:
                pi_dict["status"] = "online"
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
        
        for key, value in updates.items():
            if hasattr(pi, key):
                setattr(pi, key, value)
        
        if database.register_pi(pi):
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
            data={"logs": [log.model_dump() for log in logs], "total": len(logs)}
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


@app.post("/api/pis/{pi_id}/print", response_model=ApiResponse)
async def send_print_to_pi(pi_id: str, print_data: Dict[str, Any]):
    try:
        pi = database.get_pi_by_id(pi_id)
        if not pi:
            raise HTTPException(status_code=404, detail="Pi not found")
        
        # Send print command through WebSocket if connected
        if connection_manager.is_connected(pi_id):
            success = await connection_manager.send_command(
                pi_id,
                "print",
                print_data
            )
            
            if success:
                return ApiResponse(
                    success=True,
                    message="Print job sent via WebSocket",
                    data={"pi_id": pi_id}
                )
        
        # If WebSocket not connected, show error
        # In production, you might want to queue the job or use HTTP fallback
        raise HTTPException(status_code=503, detail="Pi is not connected via WebSocket")
        
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
    
    if not pi or pi.id != pi_id:
        logger.warning(f"Pi {pi_id} WebSocket rejected - invalid credentials")
        await websocket.close(code=1008, reason="Invalid credentials")
        return
    
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


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connected_pis": len(connection_manager.get_connected_pis())
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)