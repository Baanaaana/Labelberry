import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class ServerConfig:
    def __init__(self, config_path: str = "/etc/labelberry/server.conf"):
        import logging
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self.logger.info(f"Loading config from: {self.config_path}")
        self.config = self.load_config()
        self.logger.info(f"Config loaded - MQTT broker: {self.mqtt_broker}, port: {self.mqtt_port}, username: {self.mqtt_username}")
    
    def load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            # Return defaults if config doesn't exist
            return self.get_defaults()
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Apply environment variable overrides
            for key in config_data:
                env_key = f"LABELBERRY_{key.upper()}"
                if env_key in os.environ:
                    config_data[key] = os.environ[env_key]
            
            # Ensure all required fields exist
            defaults = self.get_defaults()
            for key, value in defaults.items():
                if key not in config_data:
                    config_data[key] = value
            
            return config_data
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.get_defaults()
    
    def get_defaults(self) -> Dict[str, Any]:
        return {
            "host": "0.0.0.0",
            "port": 8080,
            "database_path": "/var/lib/labelberry/db.sqlite",
            "log_level": "INFO",
            "log_file": "/var/log/labelberry/server.log",
            "cors_origins": ["*"],
            "rate_limit": 100,
            "session_timeout": 3600,
            # MQTT defaults
            "mqtt_broker": "localhost",
            "mqtt_port": 1883,
            "mqtt_username": None,
            "mqtt_password": None
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
    
    @property
    def mqtt_broker(self) -> str:
        return self.config.get("mqtt_broker", "localhost")
    
    @property
    def mqtt_port(self) -> int:
        return self.config.get("mqtt_port", 1883)
    
    @property
    def mqtt_username(self) -> Optional[str]:
        return self.config.get("mqtt_username")
    
    @property
    def mqtt_password(self) -> Optional[str]:
        return self.config.get("mqtt_password")
    
    @property
    def database_path(self) -> str:
        return self.config.get("database_path", "/var/lib/labelberry/db.sqlite")
    
    @property
    def port(self) -> int:
        return self.config.get("port", 8080)
    
    @property
    def host(self) -> str:
        return self.config.get("host", "0.0.0.0")