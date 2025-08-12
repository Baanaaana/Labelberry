#!/bin/bash

# Simple script to run LabelBerry admin server locally with minimal deps

echo "Starting LabelBerry Admin Server (Simple Mode)..."
echo "================================"

cd "$(dirname "$0")"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Create simple venv if needed
if [ ! -d "venv_simple" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv_simple
fi

# Activate venv
source venv_simple/bin/activate

# Install only essential packages
echo "Installing minimal dependencies..."
pip install -q --upgrade pip
pip install -q fastapi uvicorn jinja2 python-multipart pyyaml requests itsdangerous

# Try to install pydantic - if it fails, we'll mock it
pip install -q pydantic 2>/dev/null || {
    echo "Warning: Could not install pydantic, using mock"
    # Create a mock pydantic module
    mkdir -p mock_modules
    cat > mock_modules/pydantic.py << 'EOF'
class BaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class Field:
    def __init__(self, *args, **kwargs):
        pass

def validator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator
EOF
    export PYTHONPATH="$PWD/mock_modules:$PYTHONPATH"
}

# Create data directory
mkdir -p data

# Set environment variables
export LABELBERRY_DB_PATH="$(pwd)/data/labelberry_local.db"
export LABELBERRY_LOCAL_MODE="true"
export DEBUG="true"

# Create a minimal config file if it doesn't exist
if [ ! -f data/server.conf ]; then
    cat > data/server.conf << EOF
port: 8080
database_path: $(pwd)/data/labelberry_local.db
log_level: DEBUG
EOF
fi

export LABELBERRY_CONFIG_PATH="$(pwd)/data/server.conf"

echo "Starting server on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""

cd admin_server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload --log-level debug