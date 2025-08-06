import os
import yaml
import json
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from shared.models import PiConfig


class ConfigManager:
    def __init__(self, config_path: str = "/etc/labelberry/client.conf"):
        self.config_path = Path(config_path)
        self.config: Optional[PiConfig] = None
        self.load_config()
    
    def load_config(self) -> PiConfig:
        if not self.config_path.exists():
            self.create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            for key in config_data:
                env_key = f"LABELBERRY_{key.upper()}"
                if env_key in os.environ:
                    config_data[key] = os.environ[env_key]
            
            self.config = PiConfig(**config_data)
            return self.config
        except Exception as e:
            print(f"Error loading config: {e}")
            self.create_default_config()
            return self.load_config()
    
    def create_default_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        default_config = {
            "device_id": str(uuid.uuid4()),
            "friendly_name": "raspberry-pi-" + str(uuid.uuid4())[:8],
            "api_key": str(uuid.uuid4()),
            "admin_server": "http://localhost:8080",
            "printer_device": "/dev/usb/lp0",
            "queue_size": 100,
            "retry_attempts": 3,
            "retry_delay": 5,
            "log_level": "INFO",
            "metrics_interval": 60
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        print(f"Created default config at {self.config_path}")
        print(f"Device ID: {default_config['device_id']}")
        print(f"API Key: {default_config['api_key']}")
    
    def update_config(self, key: str, value: Any) -> bool:
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if key not in config_data:
                return False
            
            config_data[key] = value
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            self.load_config()
            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False
    
    def get_config(self) -> PiConfig:
        if not self.config:
            self.load_config()
        return self.config