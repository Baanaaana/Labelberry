from dataclasses import dataclass
from typing import Optional


@dataclass
class MQTTConfig:
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id_prefix: str = "labelberry"
    keepalive: int = 60
    qos: int = 1
    retain: bool = False
    
    # Topic structure
    BASE_TOPIC = "labelberry"
    
    # Pi -> Server topics
    PI_STATUS_TOPIC = f"{BASE_TOPIC}/pi/+/status"
    PI_METRICS_TOPIC = f"{BASE_TOPIC}/pi/+/metrics"
    PI_LOG_TOPIC = f"{BASE_TOPIC}/pi/+/log"
    PI_ERROR_TOPIC = f"{BASE_TOPIC}/pi/+/error"
    PI_JOB_UPDATE_TOPIC = f"{BASE_TOPIC}/pi/+/job"
    PI_CONNECT_TOPIC = f"{BASE_TOPIC}/pi/+/connect"
    PI_CONFIG_REQUEST_TOPIC = f"{BASE_TOPIC}/pi/+/config/request"
    
    # Server -> Pi topics
    SERVER_CONFIG_TOPIC = f"{BASE_TOPIC}/server/+/config"
    SERVER_COMMAND_TOPIC = f"{BASE_TOPIC}/server/+/command"
    SERVER_PRINT_JOB_TOPIC = f"{BASE_TOPIC}/server/+/print"
    SERVER_TEST_PRINT_TOPIC = f"{BASE_TOPIC}/server/+/test"
    
    # Broadcast topics (server to all Pis)
    BROADCAST_TOPIC = f"{BASE_TOPIC}/broadcast"
    
    @staticmethod
    def get_pi_topic(base: str, device_id: str) -> str:
        return base.replace("+", device_id)
    
    @staticmethod
    def get_server_topic(base: str, device_id: str) -> str:
        return base.replace("+", device_id)