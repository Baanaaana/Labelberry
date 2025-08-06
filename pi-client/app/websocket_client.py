import asyncio
import json
import logging
import aiohttp
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import WebSocketMessage, PiMetrics


logger = logging.getLogger(__name__)


class WebSocketClient:
    def __init__(self, admin_server: str, device_id: str, api_key: str):
        self.admin_server = admin_server.replace("http://", "ws://").replace("https://", "wss://")
        self.device_id = device_id
        self.api_key = api_key
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        self.message_handlers: Dict[str, Callable] = {}
        self.reconnect_interval = 5
        self.max_reconnect_interval = 60
    
    def register_handler(self, message_type: str, handler: Callable):
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def connect(self):
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.admin_server}/ws/pi/{self.device_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            self.ws = await self.session.ws_connect(url, headers=headers)
            self.running = True
            self.reconnect_interval = 5
            
            await self.send_message("connect", {
                "device_id": self.device_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Connected to admin server: {url}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def disconnect(self):
        self.running = False
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        logger.info("Disconnected from admin server")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]):
        if not self.ws or self.ws.closed:
            logger.warning("WebSocket not connected")
            return False
        
        try:
            message = WebSocketMessage(
                type=message_type,
                pi_id=self.device_id,
                data=data
            )
            await self.ws.send_str(message.json())
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_metrics(self, metrics: PiMetrics):
        return await self.send_message("metrics", metrics.dict())
    
    async def send_status(self, status: Dict[str, Any]):
        return await self.send_message("status", status)
    
    async def send_error(self, error_type: str, message: str):
        return await self.send_message("error", {
            "error_type": error_type,
            "message": message
        })
    
    async def handle_message(self, message: Dict[str, Any]):
        message_type = message.get("type")
        
        if message_type in self.message_handlers:
            try:
                await self.message_handlers[message_type](message.get("data", {}))
            except Exception as e:
                logger.error(f"Error handling message type {message_type}: {e}")
        else:
            logger.warning(f"No handler for message type: {message_type}")
    
    async def listen(self):
        while self.running:
            try:
                if not self.ws or self.ws.closed:
                    logger.info("WebSocket disconnected, attempting to reconnect...")
                    if await self.connect():
                        continue
                    else:
                        await asyncio.sleep(self.reconnect_interval)
                        self.reconnect_interval = min(
                            self.reconnect_interval * 2,
                            self.max_reconnect_interval
                        )
                        continue
                
                msg = await self.ws.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_message(data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON received: {msg.data}")
                        
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket connection closed")
                    
            except Exception as e:
                logger.error(f"WebSocket listen error: {e}")
                await asyncio.sleep(self.reconnect_interval)
    
    async def request_config(self):
        return await self.send_message("config_request", {})
    
    async def ping(self):
        return await self.send_message("ping", {"timestamp": datetime.utcnow().isoformat()})