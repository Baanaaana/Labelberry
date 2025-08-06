import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PrintJob, PrintJobStatus


logger = logging.getLogger(__name__)


class PrintQueue:
    def __init__(self, max_size: int = 100, persistence_path: str = "/var/lib/labelberry/queue.json"):
        self.max_size = max_size
        self.persistence_path = Path(persistence_path)
        self.queue: List[PrintJob] = []
        self.current_job: Optional[PrintJob] = None
        self.processing = False
        self.load_queue()
    
    def load_queue(self):
        if self.persistence_path.exists():
            try:
                with open(self.persistence_path, 'r') as f:
                    data = json.load(f)
                    self.queue = [PrintJob(**job) for job in data.get('queue', [])]
                    if data.get('current_job'):
                        self.current_job = PrintJob(**data['current_job'])
                logger.info(f"Loaded {len(self.queue)} jobs from queue")
            except Exception as e:
                logger.error(f"Failed to load queue: {e}")
                self.queue = []
    
    def save_queue(self):
        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'queue': [job.model_dump() for job in self.queue],
                'current_job': self.current_job.model_dump() if self.current_job else None
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(data, f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")
    
    def add_job(self, job: PrintJob) -> bool:
        if len(self.queue) >= self.max_size:
            logger.warning(f"Queue is full ({self.max_size} jobs)")
            return False
        
        self.queue.append(job)
        self.save_queue()
        logger.info(f"Added job {job.id} to queue (position: {len(self.queue)})")
        return True
    
    def get_next_job(self) -> Optional[PrintJob]:
        if not self.queue:
            return None
        
        job = self.queue.pop(0)
        job.status = PrintJobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        self.current_job = job
        self.save_queue()
        return job
    
    def complete_job(self, job_id: str, success: bool = True, error_message: str = None):
        if self.current_job and self.current_job.id == job_id:
            self.current_job.completed_at = datetime.utcnow()
            if success:
                self.current_job.status = PrintJobStatus.COMPLETED
                logger.info(f"Job {job_id} completed successfully")
            else:
                self.current_job.status = PrintJobStatus.FAILED
                self.current_job.error_message = error_message
                logger.error(f"Job {job_id} failed: {error_message}")
            
            self.current_job = None
            self.save_queue()
    
    def requeue_job(self, job: PrintJob) -> bool:
        job.retry_count += 1
        job.status = PrintJobStatus.PENDING
        job.started_at = None
        
        if job.retry_count <= 3:
            self.queue.insert(0, job)
            self.save_queue()
            logger.info(f"Requeued job {job.id} (retry {job.retry_count})")
            return True
        else:
            logger.error(f"Job {job.id} exceeded max retries")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "queue_size": len(self.queue),
            "max_size": self.max_size,
            "current_job": self.current_job.id if self.current_job else None,
            "processing": self.processing,
            "jobs_pending": len([j for j in self.queue if j.status == PrintJobStatus.PENDING]),
            "jobs_failed": len([j for j in self.queue if j.status == PrintJobStatus.FAILED])
        }
    
    def clear_queue(self):
        self.queue = []
        self.current_job = None
        self.save_queue()
        logger.info("Queue cleared")
    
    def get_jobs(self, limit: int = 10) -> List[PrintJob]:
        return self.queue[:limit]
    
    def remove_job(self, job_id: str) -> bool:
        for i, job in enumerate(self.queue):
            if job.id == job_id:
                del self.queue[i]
                self.save_queue()
                logger.info(f"Removed job {job_id} from queue")
                return True
        return False