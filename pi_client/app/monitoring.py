import psutil
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PiMetrics


logger = logging.getLogger(__name__)


class MonitoringService:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.start_time = datetime.utcnow()
        self.jobs_completed = 0
        self.jobs_failed = 0
    
    def get_metrics(self, queue_size: int = 0, printer_status: str = "unknown") -> PiMetrics:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            metrics = PiMetrics(
                pi_id=self.device_id,
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                queue_size=queue_size,
                jobs_completed=self.jobs_completed,
                jobs_failed=self.jobs_failed,
                printer_status=printer_status,
                uptime_seconds=int(uptime)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return PiMetrics(
                pi_id=self.device_id,
                cpu_usage=0.0,
                memory_usage=0.0,
                queue_size=queue_size,
                jobs_completed=self.jobs_completed,
                jobs_failed=self.jobs_failed,
                printer_status=printer_status,
                uptime_seconds=0
            )
    
    def increment_completed(self):
        self.jobs_completed += 1
    
    def increment_failed(self):
        self.jobs_failed += 1
    
    def get_system_info(self) -> Dict[str, Any]:
        try:
            return {
                "hostname": psutil.os.uname().nodename,
                "platform": psutil.os.uname().system,
                "release": psutil.os.uname().release,
                "cpu_count": psutil.cpu_count(),
                "total_memory": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_interfaces": list(psutil.net_if_addrs().keys())
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}
    
    async def monitor_loop(self, interval: int, callback):
        while True:
            try:
                await asyncio.sleep(interval)
                metrics = self.get_metrics()
                await callback(metrics)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval)