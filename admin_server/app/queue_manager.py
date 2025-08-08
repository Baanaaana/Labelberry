import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PrintJob, PrintJobStatus, PrintErrorType

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages the server-side print job queue"""
    
    def __init__(self, database, connection_manager):
        self.database = database
        self.connection_manager = connection_manager
        self.running = False
        self.processing_delay = 5  # Seconds between sending jobs (controlled rate)
        self.retry_delays = {
            PrintErrorType.PRINTER_DISCONNECTED: [30, 60, 120],  # Retry after 30s, 1m, 2m
            PrintErrorType.GENERIC_ERROR: [10, 30, 60],  # Retry after 10s, 30s, 1m
            PrintErrorType.NETWORK_ERROR: [5, 15, 30],  # Retry after 5s, 15s, 30s
            PrintErrorType.OUT_OF_PAPER: [],  # No automatic retry
            PrintErrorType.OUT_OF_RIBBON: [],  # No automatic retry
            PrintErrorType.INVALID_ZPL: [],  # No automatic retry
            PrintErrorType.QUEUE_FULL: [60, 120, 300],  # Retry after 1m, 2m, 5m
        }
        self.last_job_sent = {}  # Track when last job was sent to each Pi
    
    async def start(self):
        """Start the queue manager"""
        self.running = True
        logger.info("Queue Manager started")
        
        # Start background tasks
        asyncio.create_task(self.process_queues())
        asyncio.create_task(self.expire_old_jobs())
        asyncio.create_task(self.process_retries())
    
    async def stop(self):
        """Stop the queue manager"""
        self.running = False
        logger.info("Queue Manager stopped")
    
    async def process_queues(self):
        """Main queue processing loop"""
        while self.running:
            try:
                # Get all connected Pis
                connected_pis = self.connection_manager.get_connected_pis()
                
                for pi_id in connected_pis:
                    # Check if enough time has passed since last job sent
                    last_sent = self.last_job_sent.get(pi_id, datetime.min)
                    if (datetime.utcnow() - last_sent).total_seconds() < self.processing_delay:
                        continue
                    
                    # Get next queued job for this Pi
                    jobs = self.database.get_queued_jobs(pi_id, limit=1)
                    if jobs:
                        job = jobs[0]
                        await self.send_job_to_pi(pi_id, job)
                        self.last_job_sent[pi_id] = datetime.utcnow()
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(5)
    
    async def send_job_to_pi(self, pi_id: str, job: Dict[str, Any]) -> bool:
        """Send a queued job to a Pi"""
        try:
            # Update status to 'sent'
            self.database.update_job_status(job['id'], 'sent')
            
            # Send via WebSocket
            success = await self.connection_manager.send_command(
                pi_id,
                "print",
                {
                    "job_id": job['id'],
                    "zpl_raw": job['zpl_source'] if not job['zpl_source'].startswith('http') else None,
                    "zpl_url": job['zpl_source'] if job['zpl_source'].startswith('http') else None,
                    "priority": job.get('priority', 5)
                }
            )
            
            if success:
                logger.info(f"Sent job {job['id']} to Pi {pi_id}")
                # Log the event
                self.database.save_server_log(
                    "job_sent",
                    f"Print job sent to Pi after queuing",
                    "INFO",
                    f"Job ID: {job['id']}, Pi: {pi_id}"
                )
                return True
            else:
                # Failed to send, revert to queued
                self.database.update_job_status(job['id'], 'queued')
                logger.error(f"Failed to send job {job['id']} to Pi {pi_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending job to Pi: {e}")
            # Revert to queued status
            self.database.update_job_status(job['id'], 'queued')
            return False
    
    async def handle_job_result(self, pi_id: str, job_id: str, status: str, 
                               error_message: str = None, error_type: str = None):
        """Handle job completion/failure from Pi"""
        try:
            job = self.database.get_job_by_id(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            if status == 'completed':
                # Job succeeded
                self.database.update_job_status(job_id, 'completed')
                logger.info(f"Job {job_id} completed successfully")
                
            elif status == 'failed':
                # Don't auto-retry, mark as failed but keep for manual retry
                self.database.update_job_status(job_id, 'failed', error_message, error_type)
                
                # Check if job is older than 24 hours
                from datetime import datetime, timedelta
                job_age = datetime.utcnow() - job['created_at']
                if job_age > timedelta(hours=24):
                    logger.info(f"Job {job_id} is older than 24 hours, marking as expired")
                    self.database.update_job_status(job_id, 'expired', error_message, error_type)
                else:
                    hours_left = 24 - (job_age.total_seconds() / 3600)
                    logger.info(f"Job {job_id} failed. Manual retry available for {hours_left:.1f} more hours.")
                    
        except Exception as e:
            logger.error(f"Error handling job result: {e}")
    
    async def should_retry_job(self, job: Dict[str, Any], error_type: str) -> bool:
        """Determine if a job should be retried based on error type and retry count"""
        try:
            # Check if we've exceeded max retries
            if job['retry_count'] >= job.get('max_retries', 3):
                return False
            
            # Check error type for retry policy
            error_enum = PrintErrorType(error_type) if error_type else PrintErrorType.GENERIC_ERROR
            retry_delays = self.retry_delays.get(error_enum, [])
            
            # If no retry delays defined, don't retry
            if not retry_delays:
                return False
            
            # If we haven't exceeded the retry delay list, we can retry
            return job['retry_count'] < len(retry_delays)
            
        except Exception as e:
            logger.error(f"Error checking retry policy: {e}")
            return False
    
    async def expire_old_jobs(self):
        """Periodically expire jobs older than 24 hours"""
        while self.running:
            try:
                expired_count = self.database.expire_old_jobs(hours=24)
                if expired_count > 0:
                    logger.info(f"Expired {expired_count} old jobs")
                    self.database.save_server_log(
                        "jobs_expired",
                        f"Expired {expired_count} jobs older than 24 hours",
                        "INFO"
                    )
                
                # Run every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error expiring old jobs: {e}")
                await asyncio.sleep(3600)
    
    async def process_retries(self):
        """Process jobs that need to be retried after a delay"""
        while self.running:
            try:
                # Get all failed jobs that might need retry
                with self.database.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM print_jobs 
                        WHERE status = 'failed' 
                        AND retry_count < max_retries
                        AND error_type IS NOT NULL
                    """)
                    
                    for row in cursor.fetchall():
                        job = dict(row)
                        if await self.is_ready_for_retry(job):
                            # Requeue the job
                            self.database.update_job_status(job['id'], 'queued')
                            logger.info(f"Requeued job {job['id']} for retry")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error processing retries: {e}")
                await asyncio.sleep(30)
    
    async def is_ready_for_retry(self, job: Dict[str, Any]) -> bool:
        """Check if enough time has passed for a retry"""
        try:
            error_type = PrintErrorType(job['error_type']) if job['error_type'] else PrintErrorType.GENERIC_ERROR
            retry_delays = self.retry_delays.get(error_type, [])
            
            if not retry_delays or job['retry_count'] >= len(retry_delays):
                return False
            
            # Get the delay for this retry attempt
            delay_seconds = retry_delays[job['retry_count']]
            
            # Check if enough time has passed since failure
            if job['completed_at']:
                failed_at = job['completed_at']
                if isinstance(failed_at, str):
                    failed_at = datetime.fromisoformat(failed_at)
                
                time_passed = (datetime.utcnow() - failed_at).total_seconds()
                return time_passed >= delay_seconds
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking retry readiness: {e}")
            return False
    
    def add_job_to_queue(self, job: PrintJob, zpl_content: str = None, zpl_url: str = None) -> bool:
        """Add a new job to the queue"""
        try:
            job.status = PrintJobStatus.QUEUED
            job.queued_at = datetime.utcnow()
            return self.database.queue_print_job(job, zpl_content, zpl_url)
        except Exception as e:
            logger.error(f"Error adding job to queue: {e}")
            return False
    
    def handle_pi_connected(self, pi_id: str):
        """Handle when a Pi comes online"""
        logger.info(f"Pi {pi_id} connected, will start processing its queue")
        # The queue processing loop will automatically pick up this Pi
    
    def handle_pi_disconnected(self, pi_id: str):
        """Handle when a Pi goes offline"""
        logger.info(f"Pi {pi_id} disconnected, jobs will remain queued")
        # Remove from last_job_sent to reset rate limiting when it reconnects
        if pi_id in self.last_job_sent:
            del self.last_job_sent[pi_id]
    
    def get_queue_info(self, pi_id: str = None) -> Dict[str, Any]:
        """Get queue information for dashboard"""
        stats = self.database.get_queue_stats(pi_id)
        
        # Add queue position info for queued jobs
        if pi_id:
            queued_jobs = self.database.get_queued_jobs(pi_id, limit=100)
            stats['queue'] = []
            for i, job in enumerate(queued_jobs):
                stats['queue'].append({
                    'id': job['id'],
                    'position': i + 1,
                    'created_at': job['created_at'],
                    'priority': job.get('priority', 5),
                    'estimated_wait': (i + 1) * self.processing_delay  # Rough estimate
                })
        
        return stats