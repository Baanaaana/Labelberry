import asyncio
import json
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import WebSocketMessage, PiMetrics, ErrorLog, PiStatus
from .database import Database


logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, database: Database):
        self.active_connections: Dict[str, WebSocket] = {}
        self.database = database
        self.ping_interval = 30
        self.ping_tasks: Dict[str, asyncio.Task] = {}
        self.queue_manager = None  # Will be set after initialization
    
    async def connect(self, pi_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[pi_id] = websocket
        self.database.update_pi_status(pi_id, PiStatus.ONLINE)
        
        # Don't start ping task immediately to avoid interfering with initial messages
        # self.ping_tasks[pi_id] = asyncio.create_task(self.ping_loop(pi_id))
        
        logger.info(f"Pi {pi_id} connected via WebSocket - Total connected: {len(self.active_connections)}")
        
        # Notify queue manager that Pi is online
        if self.queue_manager:
            self.queue_manager.handle_pi_connected(pi_id)
    
    def disconnect(self, pi_id: str):
        if pi_id in self.active_connections:
            del self.active_connections[pi_id]
        
        if pi_id in self.ping_tasks:
            self.ping_tasks[pi_id].cancel()
            del self.ping_tasks[pi_id]
        
        self.database.update_pi_status(pi_id, PiStatus.OFFLINE)
        logger.info(f"Pi {pi_id} disconnected")
        
        # Notify queue manager that Pi is offline
        if self.queue_manager:
            self.queue_manager.handle_pi_disconnected(pi_id)
    
    async def send_to_pi(self, pi_id: str, message: Dict) -> bool:
        if pi_id not in self.active_connections:
            logger.warning(f"Pi {pi_id} not connected")
            return False
        
        try:
            websocket = self.active_connections[pi_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to Pi {pi_id}: {e}")
            self.disconnect(pi_id)
            return False
    
    async def broadcast_to_all(self, message: Dict):
        disconnected = []
        for pi_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to Pi {pi_id}: {e}")
                disconnected.append(pi_id)
        
        for pi_id in disconnected:
            self.disconnect(pi_id)
    
    async def handle_pi_message(self, pi_id: str, websocket: WebSocket):
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self.process_message(pi_id, message)
                
        except WebSocketDisconnect:
            self.disconnect(pi_id)
        except Exception as e:
            logger.error(f"Error handling Pi {pi_id} message: {e}")
            self.disconnect(pi_id)
    
    async def process_message(self, pi_id: str, message: Dict):
        try:
            msg_type = message.get("type")
            data = message.get("data", {})
            
            logger.info(f"Received {msg_type} from Pi {pi_id}")
            
            # Update last seen on any message
            self.database.update_last_seen(pi_id)
            
            if msg_type == "connect":
                await self.handle_connect(pi_id, data)
            
            elif msg_type == "metrics":
                await self.handle_metrics(pi_id, data)
            
            elif msg_type == "status":
                await self.handle_status(pi_id, data)
            
            elif msg_type == "error":
                await self.handle_error(pi_id, data)
            
            elif msg_type == "log":
                await self.handle_log(pi_id, data)
            
            elif msg_type == "job_complete":
                await self.handle_job_complete(pi_id, data)
            
            elif msg_type == "job_status":
                await self.handle_job_status(pi_id, data)
            
            elif msg_type == "config_request":
                await self.handle_config_request(pi_id)
            
            elif msg_type == "pong":
                await self.handle_pong(pi_id, data)
            
            else:
                logger.warning(f"Unknown message type from Pi {pi_id}: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error processing message from Pi {pi_id}: {e}")
    
    async def handle_connect(self, pi_id: str, data: Dict):
        self.database.update_pi_status(pi_id, PiStatus.ONLINE)
        logger.info(f"Pi {pi_id} sent connect message")
        
        # Update printer model if provided
        if "printer_model" in data and data["printer_model"]:
            self.database.update_pi_printer_model(pi_id, data["printer_model"])
            logger.info(f"Updated printer model for Pi {pi_id}: {data['printer_model']}")
        
        # Start ping task after successful connect
        if pi_id not in self.ping_tasks:
            self.ping_tasks[pi_id] = asyncio.create_task(self.ping_loop(pi_id))
        
        config = self.database.get_pi_config(pi_id)
        if config:
            await self.send_to_pi(pi_id, {
                "type": "config_update",
                "data": config
            })
    
    async def handle_metrics(self, pi_id: str, data: Dict):
        try:
            metrics = PiMetrics(**data)
            self.database.save_metrics(metrics)
            
            await self.broadcast_admin_update("metrics_update", {
                "pi_id": pi_id,
                "metrics": data
            })
        except Exception as e:
            logger.error(f"Failed to handle metrics from Pi {pi_id}: {e}")
    
    async def handle_status(self, pi_id: str, data: Dict):
        # Update last seen timestamp and status
        self.database.update_pi_status(pi_id, PiStatus.ONLINE)
        
        await self.broadcast_admin_update("status_update", {
            "pi_id": pi_id,
            "status": data
        })
    
    async def handle_error(self, pi_id: str, data: Dict):
        try:
            error = ErrorLog(
                pi_id=pi_id,
                error_type=data.get("error_type", "unknown"),
                message=data.get("message", ""),
                traceback=data.get("traceback")
            )
            self.database.save_error_log(error)
            
            await self.broadcast_admin_update("error_occurred", {
                "pi_id": pi_id,
                "error": error.model_dump()
            })
        except Exception as e:
            logger.error(f"Failed to handle error from Pi {pi_id}: {e}")
    
    async def handle_log(self, pi_id: str, data: Dict):
        """Handle general log messages from Pi"""
        try:
            log_type = data.get("log_type", "general")
            message = data.get("message", "")
            details = data.get("details", {})
            
            # Save to database
            import json
            self.database.save_log(
                pi_id=pi_id,
                log_type=log_type,
                message=message,
                level="INFO",
                details=json.dumps(details) if details else None
            )
            
            logger.info(f"Received log from Pi {pi_id}: [{log_type}] {message}")
            
        except Exception as e:
            logger.error(f"Failed to handle log from Pi {pi_id}: {e}")
    
    async def handle_job_status(self, pi_id: str, data: Dict):
        """Handle job status update from Pi"""
        job_id = data.get("job_id")
        status = data.get("status")
        
        # Skip if no job_id (test prints)
        if not job_id:
            return
        
        # Update job status in database
        if status in ["pending", "processing"]:
            self.database.update_job_status(job_id, status)
        
        await self.broadcast_admin_update("job_status", {
            "pi_id": pi_id,
            "job_id": job_id,
            "status": status
        })
    
    async def handle_job_complete(self, pi_id: str, data: Dict):
        """Handle job completion notification from Pi"""
        job_id = data.get("job_id")
        status = data.get("status")
        error_message = data.get("error_message")
        error_type = data.get("error_type")
        
        # Skip database update if no job_id (test prints)
        if not job_id:
            logger.info(f"Test print from Pi {pi_id} completed with status: {status}")
            await self.broadcast_admin_update("job_complete", {
                "pi_id": pi_id,
                "job_id": None,
                "status": status,
                "is_test": True
            })
            return
        
        # Update job status in database
        if status == "completed":
            self.database.update_job_status(job_id, "completed")
        elif status == "failed":
            # Let queue manager handle retry logic
            if self.queue_manager:
                await self.queue_manager.handle_job_result(
                    pi_id, job_id, "failed", error_message, error_type
                )
            else:
                self.database.update_job_status(job_id, "failed", error_message, error_type)
        
        await self.broadcast_admin_update("job_complete", {
            "pi_id": pi_id,
            "job_id": job_id,
            "status": status,
            "error_message": error_message
        })
    
    async def handle_config_request(self, pi_id: str):
        config = self.database.get_pi_config(pi_id)
        if config:
            await self.send_to_pi(pi_id, {
                "type": "config_update",
                "data": config
            })
    
    async def handle_pong(self, pi_id: str, data: Dict):
        # Update last seen on pong (heartbeat)
        self.database.update_last_seen(pi_id)
    
    async def ping_loop(self, pi_id: str):
        while pi_id in self.active_connections:
            try:
                await asyncio.sleep(self.ping_interval)
                await self.send_to_pi(pi_id, {
                    "type": "ping",
                    "data": {"timestamp": datetime.now(timezone.utc).isoformat()}
                })
            except Exception as e:
                logger.error(f"Ping failed for Pi {pi_id}: {e}")
                break
    
    async def send_config_update(self, pi_id: str, config: Dict) -> bool:
        return await self.send_to_pi(pi_id, {
            "type": "config_update",
            "data": config
        })
    
    async def send_command(self, pi_id: str, command: str, params: Dict = None) -> bool:
        return await self.send_to_pi(pi_id, {
            "type": "command",
            "data": {
                "command": command,
                "params": params or {}
            }
        })
    
    async def broadcast_admin_update(self, event_type: str, data: Dict):
        pass
    
    def get_connected_pis(self) -> List[str]:
        return list(self.active_connections.keys())
    
    def is_connected(self, pi_id: str) -> bool:
        return pi_id in self.active_connections