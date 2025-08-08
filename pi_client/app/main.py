import asyncio
import logging
import sys
import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import (
    PrintRequest, PrintJob, PrintJobStatus, 
    ApiResponse, PiStatus, PiMetrics
)
from .config import ConfigManager
from .printer import ZebraPrinter
from .queue import PrintQueue
from .websocket_client import WebSocketClient
from .monitoring import MonitoringService


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


config_manager = ConfigManager()
config = config_manager.get_config()

printer = ZebraPrinter(config.printer_device)
print_queue = PrintQueue(max_size=config.queue_size)
monitoring = MonitoringService(config.device_id)
ws_client = WebSocketClient(
    config.admin_server, 
    config.device_id, 
    config.api_key,
    printer_model=config.printer_model
)


async def process_queue():
    while True:
        try:
            if not print_queue.processing:
                job = print_queue.get_next_job()
                if job:
                    print_queue.processing = True
                    logger.info(f"Starting to process job {job.id} from queue")
                    try:
                        # Add timeout to prevent hanging
                        success = await asyncio.wait_for(process_print_job(job), timeout=30.0)
                        if success:
                            monitoring.increment_completed()
                            logger.info(f"Job {job.id} marked as completed in monitoring")
                        else:
                            monitoring.increment_failed()
                            logger.info(f"Job {job.id} marked as failed in monitoring")
                    except asyncio.TimeoutError:
                        logger.error(f"Job {job.id} timed out after 30 seconds")
                        monitoring.increment_failed()
                        print_queue.complete_job(job.id, success=False, error_message="Job timed out")
                    finally:
                        print_queue.processing = False
                        logger.info(f"Queue processing flag reset after job {job.id}")
            
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Queue processing error: {e}", exc_info=True)
            print_queue.processing = False
            await asyncio.sleep(5)


async def process_print_job(job: PrintJob) -> bool:
    try:
        logger.info(f"Processing job {job.id}")
        
        # Notify server that job is being processed
        await ws_client.send_message("job_status", {
            "job_id": job.id,
            "status": "processing"
        })
        
        zpl_content = ""
        error_type = None
        error_message = None
        
        try:
            if job.zpl_source.startswith("http"):
                response = requests.get(job.zpl_source, timeout=30)
                response.raise_for_status()
                zpl_content = response.text
            else:
                zpl_content = job.zpl_source
        except Exception as e:
            error_type = "network_error"
            error_message = f"Failed to download ZPL: {str(e)}"
            logger.error(error_message)
            
            await ws_client.send_message("job_complete", {
                "job_id": job.id,
                "status": "failed",
                "error_type": error_type,
                "error_message": error_message
            })
            return False
        
        # Check printer connection (reconnect if needed)
        if not printer.is_connected:
            logger.info("Printer not connected, attempting to reconnect...")
            if not printer.connect():
                error_type = "printer_disconnected"
                error_message = "Printer is not connected and reconnection failed"
                logger.error(error_message)
                
                await ws_client.send_message("job_complete", {
                    "job_id": job.id,
                    "status": "failed",
                    "error_type": error_type,
                    "error_message": error_message
                })
                return False
            else:
                logger.info("Printer reconnected successfully")
        
        logger.info(f"Sending ZPL to printer for job {job.id}, content length: {len(zpl_content)}")
        success = printer.print_zpl(zpl_content)
        logger.info(f"Printer returned {'success' if success else 'failure'} for job {job.id}")
        
        if success:
            print_queue.complete_job(job.id, success=True)
            logger.info(f"Job {job.id} completed successfully")
            await ws_client.send_message("job_complete", {
                "job_id": job.id,
                "status": "completed"
            })
            return True
        else:
            # Determine error type
            error_type = "generic_error"
            error_message = "Print failed"
            logger.error(f"Job {job.id} failed to print")
            
            # Send failure status to server
            await ws_client.send_message("job_complete", {
                "job_id": job.id,
                "status": "failed",
                "error_type": error_type,
                "error_message": error_message
            })
            
            print_queue.complete_job(job.id, success=False, error_message=error_message)
            return False
            
    except Exception as e:
        logger.error(f"Job processing error: {e}")
        print_queue.complete_job(job.id, success=False, error_message=str(e))
        await ws_client.send_error("job_error", str(e))
        return False


async def handle_ping(data: Dict[str, Any]):
    """Handle ping message from server"""
    logger.debug("Received ping from server")
    # The ping response is handled automatically by the websocket client


async def handle_config_update(data: Dict[str, Any]):
    logger.info(f"Received config update: {data}")
    for key, value in data.items():
        if hasattr(config, key):
            config_manager.update_config(key, value)


async def handle_command(data: Dict[str, Any]):
    command = data.get("command")
    params = data.get("params", {})
    logger.info(f"Received command: {command}")
    
    if command == "clear_queue":
        print_queue.clear_queue()
    elif command == "test_print":
        printer.test_print()
    elif command == "print":
        # Handle print job from admin server
        await handle_remote_print(params)
    elif command == "restart":
        logger.info("Restart requested")


async def handle_remote_print(print_data: Dict[str, Any]):
    """Handle print job sent from admin server"""
    try:
        # Get job details from server
        job_id = print_data.get("job_id")
        zpl_url = print_data.get("zpl_url")
        zpl_raw = print_data.get("zpl_raw")
        priority = print_data.get("priority", 5)
        
        # Create a print job from the data
        job_data = {
            "pi_id": config.device_id,
            "zpl_source": zpl_url or zpl_raw or "",
            "priority": priority
        }
        
        # Only add id if provided by server
        if job_id:
            job_data["id"] = job_id
        
        job = PrintJob(**job_data)
        
        # If this is a queued job from server, acknowledge receipt
        if job_id:
            await ws_client.send_message("job_status", {
                "job_id": job_id,
                "status": "pending"
            })
        
        if print_queue.add_job(job):
            logger.info(f"Remote print job {job.id} added to queue (from server queue: {bool(job_id)})")
            await ws_client.send_log("print_queued", f"Remote print job queued", {
                "job_id": job.id,
                "source": "server_queue" if job_id else "direct"
            })
        else:
            logger.error("Failed to add remote print job - queue full")
            if job_id:
                # Report failure back to server for queued job
                await ws_client.send_message("job_complete", {
                    "job_id": job_id,
                    "status": "failed",
                    "error_type": "queue_full",
                    "error_message": "Pi local queue is full"
                })
            await ws_client.send_error("queue_full", "Print queue is full")
            
    except Exception as e:
        logger.error(f"Error handling remote print: {e}")
        if print_data.get("job_id"):
            await ws_client.send_message("job_complete", {
                "job_id": print_data.get("job_id"),
                "status": "failed",
                "error_type": "generic_error",
                "error_message": str(e)
            })
        await ws_client.send_error("print_error", str(e))


async def send_metrics_periodically():
    while True:
        try:
            await asyncio.sleep(config.metrics_interval)
            
            metrics = monitoring.get_metrics(
                queue_size=len(print_queue.queue),
                printer_status="connected" if printer.is_connected else "disconnected"
            )
            
            await ws_client.send_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Metrics sending error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ws_client.register_handler("ping", handle_ping)
    ws_client.register_handler("config_update", handle_config_update)
    ws_client.register_handler("command", handle_command)
    
    asyncio.create_task(ws_client.listen())
    asyncio.create_task(process_queue())
    asyncio.create_task(send_metrics_periodically())
    
    logger.info(f"LabelBerry Pi Client started - Device ID: {config.device_id}")
    
    yield
    
    await ws_client.disconnect()
    printer.disconnect()
    logger.info("LabelBerry Pi Client stopped")


app = FastAPI(
    title="LabelBerry Pi Client",
    version="1.0.0",
    lifespan=lifespan
)


def verify_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    
    api_key = authorization.replace("Bearer ", "")
    if api_key != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key


@app.post("/print", response_model=ApiResponse)
async def print_label(request: PrintRequest, api_key: str = Depends(verify_api_key)):
    try:
        if not request.zpl_url and not request.zpl_raw:
            raise HTTPException(status_code=400, detail="Either zpl_url or zpl_raw must be provided")
        
        job = PrintJob(
            pi_id=config.device_id,
            zpl_source=request.zpl_url or request.zpl_raw
        )
        
        if not print_queue.add_job(job):
            raise HTTPException(status_code=503, detail="Print queue is full")
        
        logger.info(f"Print job {job.id} added to queue")
        
        return ApiResponse(
            success=True,
            message="Print job queued",
            data={"job_id": job.id, "queue_position": len(print_queue.queue)}
        )
        
    except Exception as e:
        logger.error(f"Print request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=ApiResponse)
async def get_status():
    try:
        status_data = {
            "device_id": config.device_id,
            "printer": printer.get_status(),
            "queue": print_queue.get_status(),
            "system": monitoring.get_system_info(),
            "websocket_connected": ws_client.ws and not ws_client.ws.closed
        }
        
        return ApiResponse(
            success=True,
            message="Status retrieved",
            data=status_data
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": config.device_id
    }


@app.post("/test-print", response_model=ApiResponse)
async def test_print(api_key: str = Depends(verify_api_key)):
    try:
        success = printer.test_print()
        
        if success:
            return ApiResponse(
                success=True,
                message="Test print successful",
                data={}
            )
        else:
            raise HTTPException(status_code=503, detail="Test print failed")
            
    except Exception as e:
        logger.error(f"Test print error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue", response_model=ApiResponse)
async def get_queue(api_key: str = Depends(verify_api_key)):
    try:
        jobs = print_queue.get_jobs(limit=50)
        
        return ApiResponse(
            success=True,
            message="Queue retrieved",
            data={
                "jobs": [job.model_dump() for job in jobs],
                "total": len(print_queue.queue)
            }
        )
    except Exception as e:
        logger.error(f"Queue retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/queue/{job_id}", response_model=ApiResponse)
async def cancel_job(job_id: str, api_key: str = Depends(verify_api_key)):
    try:
        if print_queue.remove_job(job_id):
            return ApiResponse(
                success=True,
                message="Job cancelled",
                data={"job_id": job_id}
            )
        else:
            raise HTTPException(status_code=404, detail="Job not found")
            
    except Exception as e:
        logger.error(f"Job cancellation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start_server():
    """Start the single-printer server"""
    logger.info("Starting LabelBerry single-printer service")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()