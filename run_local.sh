#!/bin/bash

# Script to run LabelBerry admin server locally WITHOUT pydantic
# Works with Python 3.13

echo "Starting LabelBerry Admin Server (No Pydantic Mode)..."
echo "================================"

cd "$(dirname "$0")"

# Remove old venvs and create new one
rm -rf venv_nopydantic 2>/dev/null
echo "Creating virtual environment..."
python3 -m venv venv_nopydantic

# Activate virtual environment
source venv_nopydantic/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q

# Install only essential dependencies (no pydantic)
echo "Installing dependencies..."
pip install -q fastapi uvicorn jinja2 python-multipart pyyaml requests itsdangerous aiohttp

# Create data directory
mkdir -p data

# Create mock pydantic in site-packages
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
echo "Creating pydantic mock in $SITE_PACKAGES..."
cat > "$SITE_PACKAGES/pydantic.py" << 'EOF'
# Mock pydantic for compatibility
class BaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def json(self):
        import json
        return json.dumps(self.dict(), default=str)
    
    @classmethod
    def parse_obj(cls, obj):
        return cls(**obj)
    
    @classmethod
    def validate(cls, value):
        return value

def Field(default=None, **kwargs):
    return default

def validator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

class ValidationError(Exception):
    pass
EOF

# Create local config
cat > data/server_local.conf << EOF
port: 8080
database_path: $(pwd)/data/labelberry_local.db
log_level: INFO
mqtt_broker: localhost
mqtt_port: 1883
mqtt_username: ""
mqtt_password: ""
EOF

# Set environment variables
export LABELBERRY_CONFIG_PATH="$(pwd)/data/server_local.conf"
export LABELBERRY_DB_PATH="$(pwd)/data/labelberry_local.db"
export LABELBERRY_LOCAL_MODE="true"
export DEBUG="false"

echo "Starting server on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""

# Run the server
cd admin_server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload