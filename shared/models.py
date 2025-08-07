from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class PrintJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
    status: PrintJobStatus = PrintJobStatus.PENDING
    zpl_source: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class PiConfig(BaseModel):
    device_id: str
    api_key: str
    admin_server: str
    printer_device: str = "/dev/usb/lp0"
    queue_size: int = 100
    retry_attempts: int = 3
    retry_delay: int = 5
    log_level: str = "INFO"
    metrics_interval: int = 60


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