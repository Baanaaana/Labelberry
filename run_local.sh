#!/bin/bash

# Script to run LabelBerry admin server locally for testing

echo "Starting LabelBerry Admin Server locally..."
echo "================================"

cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q fastapi uvicorn jinja2 python-multipart websockets requests itsdangerous

# Create local data directory
mkdir -p data

# Set environment variable to use local database
export LABELBERRY_DB_PATH="$(pwd)/data/labelberry.db"

# Run the server
echo "Starting server on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""
cd admin_server
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload