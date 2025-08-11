import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import sys
from pathlib import Path
import paho.mqtt.client as mqtt
from threading import Thread
import queue

sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PiMetrics
from shared.mqtt_config import MQTTConfig


logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self, config):
        self.device_id = config.device_id
        self.api_key = config.api_key
        self.printer_model = config.printer_model if hasattr(config, 'printer_model') else None
        
        # Use MQTT config from configuration file
        if config.mqtt_broker:
            self.broker_host = config.mqtt_broker
        else:
            # Fallback to parsing admin server URL
            self.broker_host = config.admin_server.replace("http://", "").replace("https://", "").split(":")[0]
        
        self.broker_port = config.mqtt_port if hasattr(config, 'mqtt_port') else 1883
        self.mqtt_username = config.mqtt_username if hasattr(config, 'mqtt_username') else None
        self.mqtt_password = config.mqtt_password if hasattr(config, 'mqtt_password') else None
        
        self.config = MQTTConfig()
        self.config.broker_host = self.broker_host
        
        # MQTT client setup
        self.client_id = f"{self.config.client_id_prefix}_pi_{self.device_id}"
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set authentication - use configured credentials or fallback to device_id/api_key
        if self.mqtt_username and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        else:
            self.client.username_pw_set(self.device_id, self.api_key)
        
        # Last will and testament
        will_topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_STATUS_TOPIC, self.device_id)
        will_payload = json.dumps({
            "status": "offline",
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.client.will_set(will_topic, will_payload, qos=1, retain=True)
        
        self.connected = False
        self.running = False
        self.message_queue = queue.Queue()
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.connected = True
            
            # Subscribe to server topics for this Pi
            subscriptions = [
                (MQTTConfig.get_server_topic(MQTTConfig.SERVER_CONFIG_TOPIC, self.device_id), 1),
                (MQTTConfig.get_server_topic(MQTTConfig.SERVER_COMMAND_TOPIC, self.device_id), 1),
                (MQTTConfig.get_server_topic(MQTTConfig.SERVER_PRINT_JOB_TOPIC, self.device_id), 1),
                (MQTTConfig.get_server_topic(MQTTConfig.SERVER_TEST_PRINT_TOPIC, self.device_id), 1),
                (MQTTConfig.BROADCAST_TOPIC, 1)
            ]
            
            for topic, qos in subscriptions:
                self.client.subscribe(topic, qos)
                logger.info(f"Subscribed to {topic}")
            
            # Send connect message
            self._send_connect_message()
            
            # Send online status
            self._send_status("online")
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier", 
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error (code: {rc})")
            logger.error(f"Failed to connect to MQTT broker: {error_msg}")
            if rc == 4:
                logger.error(f"Authentication failed - Username: {self.mqtt_username if self.mqtt_username else 'device_id: ' + self.device_id}")
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
            
            # Determine message type from topic
            if "config" in msg.topic:
                message_type = "config"
            elif "command" in msg.topic:
                message_type = "command"
            elif "print" in msg.topic and "test" not in msg.topic:
                message_type = "print_job"
            elif "test" in msg.topic:
                message_type = "test_print"
            elif "broadcast" in msg.topic:
                message_type = "broadcast"
            elif "job" in msg.topic or "status" in msg.topic or "metrics" in msg.topic:
                # These are Pi->Server messages, we shouldn't receive them
                # but if we do (e.g., retained messages), ignore them
                logger.debug(f"Ignoring Pi->Server message on topic: {msg.topic}")
                return
            else:
                message_type = "unknown"
            
            # Queue message for async processing (always queue, check handler later)
            self.message_queue.put((message_type, payload))
            logger.debug(f"Queued message type: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in MQTT message: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _get_local_ip(self):
        """Get the local IP address of the Pi"""
        import socket
        try:
            # Create a socket to determine the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None
    
    def _send_connect_message(self):
        topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_CONNECT_TOPIC, self.device_id)
        payload = {
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "printer_model": self.printer_model,
            "ip_address": self._get_local_ip()
        }
        self.client.publish(topic, json.dumps(payload), qos=1)
    
    def _send_status(self, status: str):
        topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_STATUS_TOPIC, self.device_id)
        payload = {
            "status": status,
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.client.publish(topic, json.dumps(payload), qos=1, retain=True)
    
    async def send_connect_message(self):
        """Async wrapper for sending connect message"""
        self._send_connect_message()
        logger.info(f"Sent connect message for device {self.device_id}")
    
    async def send_status(self, status: str):
        """Async wrapper for sending status"""
        self._send_status(status)
        logger.info(f"Sent status '{status}' for device {self.device_id}")
    
    def register_handler(self, message_type: str, handler: Callable):
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def connect(self):
        try:
            logger.info(f"Attempting to connect to MQTT broker at {self.broker_host}:{self.broker_port}")
            logger.info(f"Using credentials - Username: {self.mqtt_username if self.mqtt_username else 'device_id: ' + self.device_id}")
            
            self.client.connect(self.broker_host, self.broker_port, keepalive=self.config.keepalive)
            
            # Start MQTT loop in background thread
            self.client.loop_start()
            self.running = True
            
            # Wait a bit for connection to establish
            await asyncio.sleep(2)
            
            if self.connected:
                logger.info(f"Successfully connected to MQTT broker")
            else:
                logger.warning(f"Failed to establish connection to MQTT broker after 2 seconds")
            
            return self.connected
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker at {self.broker_host}:{self.broker_port}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def disconnect(self):
        self.running = False
        
        # Send offline status before disconnecting
        if self.connected:
            self._send_status("offline")
        
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]):
        if not self.connected:
            logger.warning("MQTT client not connected")
            return False
        
        try:
            # Determine topic based on message type
            if message_type == "metrics":
                topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_METRICS_TOPIC, self.device_id)
            elif message_type == "status":
                topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_STATUS_TOPIC, self.device_id)
            elif message_type == "error":
                topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_ERROR_TOPIC, self.device_id)
            elif message_type == "log":
                topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_LOG_TOPIC, self.device_id)
            elif message_type == "job_complete" or message_type == "job_status":
                topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_JOB_UPDATE_TOPIC, self.device_id)
            elif message_type == "config_request":
                topic = MQTTConfig.get_pi_topic(MQTTConfig.PI_CONFIG_REQUEST_TOPIC, self.device_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return False
            
            # Add metadata
            payload = {
                **data,
                "device_id": self.device_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Publish message
            result = self.client.publish(topic, json.dumps(payload), qos=self.config.qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                logger.error(f"Failed to publish message: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send MQTT message: {e}")
            return False
    
    async def send_metrics(self, metrics: PiMetrics):
        return await self.send_message("metrics", metrics.model_dump())
    
    async def send_status(self, status: Dict[str, Any]):
        return await self.send_message("status", status)
    
    async def send_error(self, error_type: str, message: str):
        return await self.send_message("error", {
            "error_type": error_type,
            "message": message
        })
    
    async def send_log(self, log_type: str, message: str, details: Optional[Dict] = None):
        return await self.send_message("log", {
            "log_type": log_type,
            "message": message,
            "details": details or {}
        })
    
    async def send_job_update(self, job_id: str, status: str):
        return await self.send_message("job_complete", {
            "job_id": job_id,
            "status": status
        })
    
    async def request_config(self):
        return await self.send_message("config_request", {})
    
    async def ping(self):
        # MQTT uses built-in keepalive, but we can still send a ping message
        return await self.send_message("status", {"ping": True})
    
    async def listen(self):
        """Process queued messages from MQTT"""
        while self.running:
            try:
                # Check for queued messages
                if not self.message_queue.empty():
                    message_type, payload = self.message_queue.get(timeout=0.1)
                    
                    if message_type in self.message_handlers:
                        try:
                            await self.message_handlers[message_type](payload)
                        except Exception as e:
                            logger.error(f"Error handling message type {message_type}: {e}")
                    else:
                        logger.debug(f"No handler registered for message type: {message_type}, skipping")
                
                # Reconnect if disconnected
                if not self.connected:
                    logger.info("MQTT disconnected, attempting to reconnect...")
                    await self.connect()
                
                await asyncio.sleep(0.1)
                
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in MQTT listen loop: {e}")
                await asyncio.sleep(1)