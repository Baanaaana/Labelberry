import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
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
    logger.info("Labelberry Admin Server started")
    yield
    logger.info("Labelberry Admin Server stopped")


app = FastAPI(
    title="Labelberry Admin Server",
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

# Mount static files and templates
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "web" / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "web" / "templates")


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Labelberry Admin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .info { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Labelberry Admin Server</h1>
        <div class="info">
            <p>The admin server is running successfully!</p>
            <p>API Documentation: <a href="/docs">/docs</a></p>
            <p>Dashboard: <a href="/dashboard">/dashboard</a></p>
        </div>
    </body>
    </html>
    """


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/pis", response_model=ApiResponse)
async def list_pis():
    try:
        pis = database.get_all_pis()
        
        pi_list = []
        for pi in pis:
            pi_dict = pi.model_dump()
            pi_dict["websocket_connected"] = connection_manager.is_connected(pi.id)
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
        pi_dict["websocket_connected"] = connection_manager.is_connected(pi_id)
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
        return ApiResponse(
            success=True,
            message="Pi deletion not implemented",
            data={}
        )
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
    auth_header = websocket.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    api_key = auth_header.replace("Bearer ", "")
    pi = database.get_pi_by_api_key(api_key)
    
    if not pi or pi.id != pi_id:
        await websocket.close(code=1008, reason="Invalid credentials")
        return
    
    await connection_manager.connect(pi_id, websocket)
    
    try:
        await connection_manager.handle_pi_message(pi_id, websocket)
    except WebSocketDisconnect:
        connection_manager.disconnect(pi_id)
    except Exception as e:
        logger.error(f"WebSocket error for Pi {pi_id}: {e}")
        connection_manager.disconnect(pi_id)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "connected_pis": len(connection_manager.get_connected_pis())
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)