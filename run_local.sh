#!/bin/bash

# Script to run LabelBerry admin server locally for testing

echo "Starting LabelBerry Admin Server locally..."
echo "================================"

cd "$(dirname "$0")"

# Find the best Python version available (prefer 3.11 or 3.12)
PYTHON_CMD=""
for cmd in python3.11 python3.12 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3 not found"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip first
pip install --upgrade pip -q

# Install minimal dependencies for local testing
echo "Installing dependencies..."
pip install -q fastapi uvicorn jinja2 python-multipart pyyaml requests itsdangerous aiohttp
# Try to install pydantic with compatible version
pip install -q "pydantic==2.5.0" || pip install -q "pydantic<2.0"
# Install paho-mqtt if not already installed
pip install -q paho-mqtt 2>/dev/null || true

# Create local data directory
mkdir -p data

# Set environment variables for local development
export LABELBERRY_DB_PATH="$(pwd)/data/labelberry.db"
export LABELBERRY_LOCAL_MODE="true"
export DEBUG="true"

# Run the server
echo "Starting server on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""
cd admin_server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload