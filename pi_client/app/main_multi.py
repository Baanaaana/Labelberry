import asyncio
import logging
import sys
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
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


class PrinterInstance:
    """Represents a single printer instance with its own queue and websocket connection"""
    
    def __init__(self, config_file: str, admin_server: str):
        """Initialize a printer instance from config file"""
        with open(config_file, 'r') as f:
            printer_config = yaml.safe_load(f)
        
        self.name = printer_config['name']
        self.device_id = printer_config['device_id']
        self.api_key = printer_config['api_key']
        self.device_path = printer_config['device_path']
        self.printer_model = printer_config.get('printer_model')
        self.enabled = printer_config.get('enabled', True)
        
        if self.enabled:
            self.printer = ZebraPrinter(self.device_path)
            self.print_queue = PrintQueue(max_size=100)  # Each printer gets its own queue
            self.monitoring = MonitoringService(self.device_id)
            self.ws_client = WebSocketClient(
                admin_server, 
                self.device_id, 
                self.api_key,
                printer_model=self.printer_model
            )
        else:
            logger.info(f"Printer {self.name} is disabled")
            self.printer = None
            self.print_queue = None
            self.monitoring = None
            self.ws_client = None


class MultiPrinterManager:
    """Manages multiple printer instances"""
    
    def __init__(self):
        self.printers: Dict[str, PrinterInstance] = {}
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.load_printers()
    
    def load_printers(self):
        """Load all printer configurations"""
        printers_dir = Path("/etc/labelberry/printers")
        
        if not printers_dir.exists():
            logger.error("No printers directory found at /etc/labelberry/printers")
            return
        
        for config_file in printers_dir.glob("*.conf"):
            try:
                printer = PrinterInstance(str(config_file), self.config.admin_server)
                self.printers[printer.device_id] = printer
                logger.info(f"Loaded printer: {printer.name} (ID: {printer.device_id})")
            except Exception as e:
                logger.error(f"Failed to load printer config {config_file}: {e}")
    
    def get_printer(self, device_id: str) -> Optional[PrinterInstance]:
        """Get a specific printer by device ID"""
        return self.printers.get(device_id)
    
    def get_all_printers(self) -> List[PrinterInstance]:
        """Get all printer instances"""
        return list(self.printers.values())
    
    def get_enabled_printers(self) -> List[PrinterInstance]:
        """Get all enabled printer instances"""
        return [p for p in self.printers.values() if p.enabled]


# Global printer manager instance
printer_manager = MultiPrinterManager()


async def process_queue(printer_instance: PrinterInstance):
    """Process print queue for a specific printer"""
    while True:
        try:
            if not printer_instance.print_queue.processing and printer_instance.printer.is_connected:
                job = printer_instance.print_queue.get_next_job()
                if job:
                    printer_instance.print_queue.processing = True
                    success = await process_print_job(printer_instance, job)
                    printer_instance.print_queue.processing = False
                    
                    # Update job status in admin server
                    await update_job_status(
                        printer_instance, 
                        job.id, 
                        PrintJobStatus.COMPLETED if success else PrintJobStatus.FAILED
                    )
        except Exception as e:
            logger.error(f"Error processing queue for {printer_instance.name}: {e}")
            printer_instance.print_queue.processing = False
        
        await asyncio.sleep(1)


async def process_print_job(printer_instance: PrinterInstance, job: PrintJob) -> bool:
    """Process a single print job on a specific printer"""
    try:
        logger.info(f"Processing job {job.id} on printer {printer_instance.name}")
        
        # Update status to processing
        await update_job_status(printer_instance, job.id, PrintJobStatus.PROCESSING)
        
        # Download if URL
        zpl_data = job.zpl_data
        if job.zpl_url:
            zpl_data = await download_zpl(job.zpl_url)
        
        # Send to printer
        success = printer_instance.printer.send_to_printer(zpl_data)
        
        if success:
            logger.info(f"Job {job.id} completed successfully on {printer_instance.name}")
        else:
            logger.error(f"Job {job.id} failed on {printer_instance.name}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error processing job {job.id} on {printer_instance.name}: {e}")
        return False


async def update_job_status(printer_instance: PrinterInstance, job_id: str, status: PrintJobStatus):
    """Update job status in admin server for a specific printer"""
    try:
        if printer_instance.ws_client and printer_instance.ws_client.connected:
            await printer_instance.ws_client.send_job_update(job_id, status)
    except Exception as e:
        logger.error(f"Failed to update job status for {printer_instance.name}: {e}")


async def download_zpl(url: str) -> str:
    """Download ZPL data from URL"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


async def start_printer_services():
    """Start all services for all enabled printers"""
    tasks = []
    
    for printer_instance in printer_manager.get_enabled_printers():
        # Start queue processor for each printer
        tasks.append(asyncio.create_task(process_queue(printer_instance)))
        
        # Start monitoring for each printer
        tasks.append(asyncio.create_task(printer_instance.monitoring.start()))
        
        # Connect websocket for each printer
        tasks.append(asyncio.create_task(printer_instance.ws_client.connect()))
    
    if tasks:
        await asyncio.gather(*tasks)
    else:
        logger.warning("No enabled printers found")


async def stop_printer_services():
    """Stop all services for all printers"""
    for printer_instance in printer_manager.get_enabled_printers():
        if printer_instance.ws_client:
            await printer_instance.ws_client.disconnect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting LabelBerry Multi-Printer Client")
    
    # Start background tasks for all printers
    asyncio.create_task(start_printer_services())
    
    yield
    
    # Shutdown
    logger.info("Stopping LabelBerry Multi-Printer Client")
    await stop_printer_services()


app = FastAPI(
    title="LabelBerry Multi-Printer Client",
    version="1.0.0",
    lifespan=lifespan
)


def verify_api_key(x_api_key: Optional[str] = Header(None), device_id: Optional[str] = Header(None)):
    """Verify API key for a specific printer"""
    if not x_api_key or not device_id:
        raise HTTPException(status_code=401, detail="Missing authentication headers")
    
    printer = printer_manager.get_printer(device_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    if x_api_key != printer.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return printer


@app.get("/status")
async def get_status():
    """Get status of all printers"""
    statuses = {}
    
    for printer_instance in printer_manager.get_all_printers():
        if printer_instance.enabled:
            status = PiStatus(
                id=printer_instance.device_id,
                friendly_name=printer_instance.name,
                status="online" if printer_instance.printer.is_connected else "offline",
                last_seen=datetime.now(),
                queue_count=printer_instance.print_queue.pending_count if printer_instance.print_queue else 0,
                metrics=printer_instance.monitoring.get_current_metrics() if printer_instance.monitoring else None
            )
            statuses[printer_instance.device_id] = status.dict()
        else:
            statuses[printer_instance.device_id] = {
                "id": printer_instance.device_id,
                "friendly_name": printer_instance.name,
                "status": "disabled",
                "enabled": False
            }
    
    return ApiResponse(
        success=True,
        data={"printers": statuses}
    )


@app.get("/status/{device_id}")
async def get_printer_status(device_id: str):
    """Get status of a specific printer"""
    printer = printer_manager.get_printer(device_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    if not printer.enabled:
        return ApiResponse(
            success=True,
            data={
                "id": printer.device_id,
                "friendly_name": printer.name,
                "status": "disabled",
                "enabled": False
            }
        )
    
    status = PiStatus(
        id=printer.device_id,
        friendly_name=printer.name,
        status="online" if printer.printer.is_connected else "offline",
        last_seen=datetime.now(),
        queue_count=printer.print_queue.pending_count,
        metrics=printer.monitoring.get_current_metrics()
    )
    
    return ApiResponse(
        success=True,
        data=status.dict()
    )


@app.post("/print/{device_id}")
async def create_print_job(
    device_id: str,
    request: PrintRequest,
    background_tasks: BackgroundTasks,
    printer: PrinterInstance = Depends(verify_api_key)
):
    """Create a print job for a specific printer"""
    if not printer.enabled:
        raise HTTPException(status_code=503, detail="Printer is disabled")
    
    if not printer.printer.is_connected:
        raise HTTPException(status_code=503, detail="Printer not connected")
    
    # Create print job
    job = PrintJob(
        pi_id=device_id,
        zpl_data=request.zpl_data,
        zpl_url=request.zpl_url,
        priority=request.priority
    )
    
    # Add to queue
    if not printer.print_queue.add_job(job):
        raise HTTPException(status_code=503, detail="Print queue is full")
    
    logger.info(f"Added job {job.id} to {printer.name} queue")
    
    return ApiResponse(
        success=True,
        data={"job_id": job.id, "queue_position": printer.print_queue.pending_count}
    )


@app.delete("/queue/{device_id}/{job_id}")
async def cancel_job(
    device_id: str,
    job_id: str,
    printer: PrinterInstance = Depends(verify_api_key)
):
    """Cancel a print job for a specific printer"""
    if not printer.enabled:
        raise HTTPException(status_code=503, detail="Printer is disabled")
    
    if printer.print_queue.cancel_job(job_id):
        logger.info(f"Cancelled job {job_id} on {printer.name}")
        return ApiResponse(success=True, message="Job cancelled")
    else:
        raise HTTPException(status_code=404, detail="Job not found")


@app.get("/metrics")
async def get_metrics():
    """Get metrics for all printers"""
    metrics = {}
    
    for printer_instance in printer_manager.get_enabled_printers():
        if printer_instance.monitoring:
            metrics[printer_instance.device_id] = printer_instance.monitoring.get_current_metrics()
    
    return ApiResponse(
        success=True,
        data={"metrics": metrics}
    )


@app.get("/metrics/{device_id}")
async def get_printer_metrics(device_id: str):
    """Get metrics for a specific printer"""
    printer = printer_manager.get_printer(device_id)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    if not printer.enabled or not printer.monitoring:
        raise HTTPException(status_code=503, detail="Printer monitoring not available")
    
    return ApiResponse(
        success=True,
        data=printer.monitoring.get_current_metrics()
    )


def start_server():
    """Start the multi-printer server"""
    logger.info("Starting LabelBerry multi-printer service")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()