import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
import paho.mqtt.client as mqtt
from threading import Thread
import queue

from shared.mqtt_config import MQTTConfig
from .database import Database


logger = logging.getLogger(__name__)


class MQTTServer:
    def __init__(self, database: Database, server_config=None):
        self.database = database
        self.server_config = server_config
        self.config = MQTTConfig()
        
        # Use server config for MQTT settings if provided
        if server_config:
            self.config.broker_host = server_config.mqtt_broker
            self.config.broker_port = server_config.mqtt_port
        
        # MQTT client setup for admin server
        self.client_id = f"{self.config.client_id_prefix}_admin"
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        
        # Connected Pis tracking
        self.connected_pis: Set[str] = set()
        
        # Message queue for async processing
        self.message_queue = queue.Queue()
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set authentication from config
        if server_config and server_config.mqtt_username and server_config.mqtt_password:
            self.client.username_pw_set(server_config.mqtt_username, server_config.mqtt_password)
        else:
            # Fallback to default credentials
            self.client.username_pw_set("admin", "admin_password")
        
        self.connected = False
        self.running = False
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Admin server connected to MQTT broker")
            self.connected = True
            
            # Subscribe to all Pi topics
            subscriptions = [
                (MQTTConfig.PI_STATUS_TOPIC, 1),
                (MQTTConfig.PI_METRICS_TOPIC, 1),
                (MQTTConfig.PI_LOG_TOPIC, 1),
                (MQTTConfig.PI_ERROR_TOPIC, 1),
                (MQTTConfig.PI_JOB_UPDATE_TOPIC, 1),
                (MQTTConfig.PI_CONNECT_TOPIC, 1),
                (MQTTConfig.PI_CONFIG_REQUEST_TOPIC, 1)
            ]
            
            for topic, qos in subscriptions:
                self.client.subscribe(topic, qos)
                logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker, return code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic_parts = msg.topic.split("/")
            
            # Extract device_id from topic (format: labelberry/pi/{device_id}/...)
            if len(topic_parts) >= 3 and topic_parts[1] == "pi":
                device_id = topic_parts[2]
                message_type = topic_parts[3] if len(topic_parts) > 3 else "unknown"
                
                # Queue message for async processing
                logger.debug(f"Received MQTT message - device: {device_id}, type: {message_type}")
                self.message_queue.put({
                    "device_id": device_id,
                    "type": message_type,
                    "payload": payload,
                    "topic": msg.topic
                })
                logger.debug(f"Queued message for processing, queue size: {self.message_queue.qsize()}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    async def start(self):
        try:
            # Connect to MQTT broker
            self.client.connect(self.config.broker_host, self.config.broker_port, keepalive=self.config.keepalive)
            
            # Start MQTT loop in background thread
            self.client.loop_start()
            self.running = True
            
            logger.info(f"MQTT server started on {self.config.broker_host}:{self.config.broker_port}")
            
            # Start message processor
            asyncio.create_task(self._process_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MQTT server: {e}")
            return False
    
    async def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT server stopped")
    
    async def _process_messages(self):
        """Process queued messages from MQTT"""
        while self.running:
            try:
                if not self.message_queue.empty():
                    message = self.message_queue.get(block=False)
                    await self._handle_pi_message(message)
                
                await asyncio.sleep(0.1)
                
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                await asyncio.sleep(1)
    
    async def _handle_pi_message(self, message: Dict[str, Any]):
        """Handle messages from Pi clients"""
        device_id = message["device_id"]
        msg_type = message["type"]
        payload = message["payload"]
        
        logger.info(f"Processing message from Pi {device_id}: type={msg_type}")
        
        try:
            if msg_type == "connect":
                await self._handle_pi_connect(device_id, payload)
            elif msg_type == "status":
                await self._handle_pi_status(device_id, payload)
            elif msg_type == "metrics":
                await self._handle_pi_metrics(device_id, payload)
            elif msg_type == "log":
                await self._handle_pi_log(device_id, payload)
            elif msg_type == "error":
                await self._handle_pi_error(device_id, payload)
            elif msg_type == "job":
                await self._handle_job_update(device_id, payload)
            elif msg_type == "config":
                if "request" in message["topic"]:
                    await self._handle_config_request(device_id, payload)
            else:
                logger.warning(f"Unknown message type from {device_id}: {msg_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from {device_id}: {e}")
    
    async def _handle_pi_connect(self, device_id: str, data: Dict[str, Any]):
        """Handle Pi connection"""
        self.connected_pis.add(device_id)
        
        # Update database (synchronous calls, no await)
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            self.database.update_pi_status(pi.id, "online")
            
            # Log connection
            self.database.create_log_entry(
                pi_id=pi.id,
                log_type="connection",
                message=f"Pi connected via MQTT",
                details=data
            )
            
            logger.info(f"Pi {device_id} connected")
        else:
            logger.warning(f"Unknown Pi connected: {device_id}")
    
    async def _handle_pi_status(self, device_id: str, data: Dict[str, Any]):
        """Handle Pi status update"""
        status = data.get("status", "unknown")
        
        if status == "offline":
            self.connected_pis.discard(device_id)
        
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            self.database.update_pi_status(pi.id, status)
            logger.info(f"Pi {device_id} status: {status}")
    
    async def _handle_pi_metrics(self, device_id: str, data: Dict[str, Any]):
        """Handle Pi metrics update"""
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            self.database.create_metrics(
                pi_id=pi.id,
                cpu_usage=data.get("cpu_usage", 0),
                memory_usage=data.get("memory_usage", 0),
                disk_usage=data.get("disk_usage", 0),
                temperature=data.get("temperature", 0),
                print_queue_size=data.get("print_queue_size", 0),
                jobs_completed=data.get("jobs_completed", 0),
                jobs_failed=data.get("jobs_failed", 0)
            )
    
    async def _handle_pi_log(self, device_id: str, data: Dict[str, Any]):
        """Handle Pi log entry"""
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            self.database.create_log_entry(
                pi_id=pi.id,
                log_type=data.get("log_type", "general"),
                message=data.get("message", ""),
                details=data.get("details", {})
            )
    
    async def _handle_pi_error(self, device_id: str, data: Dict[str, Any]):
        """Handle Pi error"""
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            self.database.create_error_log(
                pi_id=pi.id,
                error_type=data.get("error_type", "unknown"),
                message=data.get("message", ""),
                traceback=data.get("traceback")
            )
            logger.error(f"Error from Pi {device_id}: {data.get('message')}")
    
    async def _handle_job_update(self, device_id: str, data: Dict[str, Any]):
        """Handle print job update"""
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            job_id = data.get("job_id")
            status = data.get("status")
            
            if job_id:
                # Update job status in database
                self.database.update_print_job_status(job_id, status)
                logger.info(f"Job {job_id} on Pi {device_id}: {status}")
    
    async def _handle_config_request(self, device_id: str, data: Dict[str, Any]):
        """Handle configuration request from Pi"""
        pi = self.database.get_pi_by_id(device_id)
        if pi:
            config = self.database.get_pi_configuration(pi.id)
            if config:
                await self.send_config_to_pi(device_id, config)
    
    async def send_message_to_pi(self, device_id: str, message_type: str, data: Dict[str, Any]):
        """Send message to specific Pi"""
        if not self.connected:
            logger.warning("MQTT server not connected")
            return False
        
        try:
            # Determine topic based on message type
            if message_type == "config":
                topic = MQTTConfig.get_server_topic(MQTTConfig.SERVER_CONFIG_TOPIC, device_id)
            elif message_type == "command":
                topic = MQTTConfig.get_server_topic(MQTTConfig.SERVER_COMMAND_TOPIC, device_id)
            elif message_type == "print_job":
                topic = MQTTConfig.get_server_topic(MQTTConfig.SERVER_PRINT_JOB_TOPIC, device_id)
            elif message_type == "test_print":
                topic = MQTTConfig.get_server_topic(MQTTConfig.SERVER_TEST_PRINT_TOPIC, device_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return False
            
            # Add metadata
            payload = {
                **data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish message
            result = self.client.publish(topic, json.dumps(payload), qos=self.config.qos)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            logger.error(f"Failed to send MQTT message to Pi {device_id}: {e}")
            return False
    
    async def send_config_to_pi(self, device_id: str, config: Dict[str, Any]):
        """Send configuration to Pi"""
        return await self.send_message_to_pi(device_id, "config", config)
    
    async def send_print_job(self, device_id: str, job_data: Dict[str, Any]):
        """Send print job to Pi"""
        return await self.send_message_to_pi(device_id, "print_job", job_data)
    
    async def send_test_print(self, device_id: str):
        """Send test print command to Pi"""
        return await self.send_message_to_pi(device_id, "test_print", {"test": True})
    
    async def broadcast_message(self, data: Dict[str, Any]):
        """Broadcast message to all Pis"""
        if not self.connected:
            logger.warning("MQTT server not connected")
            return False
        
        try:
            payload = {
                **data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = self.client.publish(MQTTConfig.BROADCAST_TOPIC, json.dumps(payload), qos=self.config.qos)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")
            return False
    
    def is_pi_connected(self, device_id: str) -> bool:
        """Check if a Pi is connected"""
        return device_id in self.connected_pis
    
    def is_connected(self, device_id: str) -> bool:
        """Check if a Pi is connected (alias for is_pi_connected)"""
        return device_id in self.connected_pis
    
    def disconnect(self, device_id: str):
        """Remove Pi from connected list"""
        self.connected_pis.discard(device_id)
    
    def get_connected_pis(self) -> Set[str]:
        """Get list of connected Pi device IDs"""
        return self.connected_pis.copy()