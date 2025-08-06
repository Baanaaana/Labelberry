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
ws_client = WebSocketClient(config.admin_server, config.device_id, config.api_key)


async def process_queue():
    while True:
        try:
            if not print_queue.processing and printer.is_connected:
                job = print_queue.get_next_job()
                if job:
                    print_queue.processing = True
                    success = await process_print_job(job)
                    if success:
                        monitoring.increment_completed()
                    else:
                        monitoring.increment_failed()
                    print_queue.processing = False
            
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
            print_queue.processing = False
            await asyncio.sleep(5)


async def process_print_job(job: PrintJob) -> bool:
    try:
        logger.info(f"Processing job {job.id}")
        
        zpl_content = ""
        
        if job.zpl_source.startswith("http"):
            response = requests.get(job.zpl_source, timeout=30)
            response.raise_for_status()
            zpl_content = response.text
        else:
            zpl_content = job.zpl_source
        
        success = printer.print_zpl(zpl_content)
        
        if success:
            print_queue.complete_job(job.id, success=True)
            await ws_client.send_message("job_complete", {
                "job_id": job.id,
                "status": "completed"
            })
            return True
        else:
            if job.retry_count < config.retry_attempts:
                print_queue.requeue_job(job)
                await asyncio.sleep(config.retry_delay)
            else:
                print_queue.complete_job(job.id, success=False, error_message="Print failed after retries")
                await ws_client.send_error("print_failed", f"Job {job.id} failed")
            return False
            
    except Exception as e:
        logger.error(f"Job processing error: {e}")
        print_queue.complete_job(job.id, success=False, error_message=str(e))
        await ws_client.send_error("job_error", str(e))
        return False


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
        # Create a print job from the data
        job = PrintJob(
            pi_id=config.device_id,
            zpl_source=print_data.get("zpl_url") or print_data.get("zpl_raw", "")
        )
        
        if print_queue.add_job(job):
            logger.info(f"Remote print job {job.id} added to queue")
            await ws_client.send_message("job_received", {
                "job_id": job.id,
                "status": "queued"
            })
        else:
            logger.error("Failed to add remote print job - queue full")
            await ws_client.send_error("queue_full", "Print queue is full")
            
    except Exception as e:
        logger.error(f"Error handling remote print: {e}")
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


if __name__ == "__main__":
    # Check if running in multi-printer mode
    if os.getenv("LABELBERRY_MULTI_PRINTER", "false").lower() == "true":
        logger.info("Starting in multi-printer mode")
        from . import main_multi
        uvicorn.run(main_multi.app, host="0.0.0.0", port=8000)
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)