from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class PrintJobStatus(str, Enum):
    QUEUED = "queued"  # Job waiting to be sent (Pi offline or rate-limited)
    SENT = "sent"  # Job sent to Pi, awaiting acknowledgment
    PENDING = "pending"  # Job acknowledged by Pi, in Pi's local queue
    PROCESSING = "processing"  # Pi is actively printing
    COMPLETED = "completed"  # Successfully printed
    FAILED = "failed"  # Pi reported failure
    CANCELLED = "cancelled"  # Manually cancelled
    EXPIRED = "expired"  # Exceeded 24-hour limit


class PrintErrorType(str, Enum):
    PRINTER_DISCONNECTED = "printer_disconnected"  # USB printer disconnected from Pi
    OUT_OF_PAPER = "out_of_paper"  # Printer out of paper
    OUT_OF_RIBBON = "out_of_ribbon"  # Printer out of ribbon
    INVALID_ZPL = "invalid_zpl"  # ZPL format error
    NETWORK_ERROR = "network_error"  # Failed to download ZPL from URL
    GENERIC_ERROR = "generic_error"  # Unknown printer error
    QUEUE_FULL = "queue_full"  # Pi's local queue is full


class PiStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class PrintRequest(BaseModel):
    zpl_url: Optional[str] = None
    zpl_raw: Optional[str] = None
    api_key: str
    priority: int = Field(default=5, ge=1, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "zpl_url": "https://files-cdn.picqer.net/label.zpl",
                "api_key": "your-api-key-here",
                "priority": 5
            }
        }


class PrintJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pi_id: str
    status: PrintJobStatus = PrintJobStatus.QUEUED
    zpl_source: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    queued_at: Optional[datetime] = None  # When job entered queue
    sent_at: Optional[datetime] = None  # When job was sent to Pi
    started_at: Optional[datetime] = None  # When Pi started processing
    completed_at: Optional[datetime] = None  # When job completed
    error_message: Optional[str] = None
    error_type: Optional[PrintErrorType] = None
    retry_count: int = 0
    max_retries: int = 3  # Maximum retry attempts
    priority: int = 5  # 1-10, higher = more urgent
    source: str = "api"  # api, dashboard, retry


class PiConfig(BaseModel):
    device_id: str
    api_key: str
    admin_server: str
    printer_device: str = "/dev/usb/lp0"
    printer_model: Optional[str] = None
    queue_size: int = 100
    retry_attempts: int = 3
    retry_delay: int = 5
    log_level: str = "INFO"
    metrics_interval: int = 60
    # MQTT settings
    mqtt_broker: Optional[str] = None  # If None, derives from admin_server
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None


class PiMetrics(BaseModel):
    pi_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_usage: float
    memory_usage: float
    queue_size: int
    jobs_completed: int
    jobs_failed: int
    printer_status: str
    uptime_seconds: int


class PiDevice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    friendly_name: str
    api_key: str
    device_name: Optional[str] = None
    location: Optional[str] = None
    printer_model: Optional[str] = None
    label_size_id: Optional[int] = None
    ip_address: Optional[str] = None
    status: PiStatus = PiStatus.OFFLINE
    last_seen: Optional[datetime] = None
    config: Optional[PiConfig] = None
    current_job_id: Optional[str] = None
    queue_count: int = 0


class WebSocketMessage(BaseModel):
    type: str
    pi_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pi_id: str
    error_type: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    traceback: Optional[str] = None