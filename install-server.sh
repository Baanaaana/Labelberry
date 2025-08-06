#!/bin/bash

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   LabelBerry Admin Server Installation Script ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/12] Checking system requirements...${NC}"
if ! lsb_release -d | grep -q "Ubuntu"; then
    echo -e "${YELLOW}Warning: This doesn't appear to be Ubuntu${NC}"
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r </dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}[2/12] Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}Python $PYTHON_VERSION found${NC}"

echo -e "${YELLOW}[3/12] Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    build-essential \
    python3-dev \
    uuid-runtime

echo -e "${YELLOW}[4/12] Creating installation directory...${NC}"
INSTALL_DIR="/opt/labelberry-admin"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Installation directory already exists${NC}"
    read -p "Do you want to reinstall? This will backup your database (y/N): " -n 1 -r </dev/tty
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "/var/lib/labelberry/db.sqlite" ]; then
            cp /var/lib/labelberry/db.sqlite /var/lib/labelberry/db.sqlite.backup
            echo -e "${GREEN}Database backed up to /var/lib/labelberry/db.sqlite.backup${NC}"
        fi
        rm -rf "$INSTALL_DIR"
    else
        exit 1
    fi
fi
mkdir -p "$INSTALL_DIR"

echo -e "${YELLOW}[5/12] Cloning repository...${NC}"
cd "$INSTALL_DIR"
git clone --sparse https://github.com/Baanaaana/LabelBerry.git .
git sparse-checkout init --cone
git sparse-checkout set admin_server shared

echo -e "${YELLOW}[6/12] Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[7/12] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r admin_server/requirements.txt

# Create __init__.py files for proper Python package structure
touch admin_server/__init__.py
touch admin_server/app/__init__.py
touch shared/__init__.py

echo -e "${YELLOW}[8/12] Creating directories...${NC}"
mkdir -p /etc/labelberry
mkdir -p /var/lib/labelberry
mkdir -p /var/log/labelberry

echo -e "${YELLOW}[9/12] Creating configuration...${NC}"
if [ ! -f "/etc/labelberry/server.conf" ]; then
    read -p "Enter the port for the admin server (default 8080): " PORT </dev/tty
    PORT=${PORT:-8080}
    
    cat > /etc/labelberry/server.conf <<EOF
host: 0.0.0.0
port: $PORT
database_path: /var/lib/labelberry/db.sqlite
log_level: INFO
log_file: /var/log/labelberry/server.log
cors_origins: ["*"]
rate_limit: 100
session_timeout: 3600
EOF
    
    echo -e "${GREEN}Configuration created${NC}"
else
    echo -e "${YELLOW}Configuration already exists, skipping...${NC}"
    PORT=$(grep "port:" /etc/labelberry/server.conf | cut -d' ' -f2)
fi

echo -e "${YELLOW}[10/12] Creating systemd service...${NC}"
cat > /etc/systemd/system/labelberry-admin.service <<EOF
[Unit]
Description=LabelBerry Admin Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn admin_server.app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable labelberry-admin.service

echo -e "${YELLOW}[11/11] Starting service...${NC}"
systemctl start labelberry-admin.service

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Installation Complete!                     ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Access the dashboard at:${NC}"
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "   http://$SERVER_IP:$PORT"
echo ""
echo -e "${YELLOW}Service Status:${NC}"
echo "   sudo systemctl status labelberry-admin"
echo ""
echo -e "${YELLOW}View Logs:${NC}"
echo "   sudo journalctl -u labelberry-admin -f"
echo ""
echo -e "${YELLOW}Note:${NC}"
echo "   For domain/SSL setup, use Nginx Proxy Manager or similar"
echo "   The service is running directly on port $PORT"
echo ""

read -p "Do you want to start the service now? (Y/n): " -n 1 -r </dev/tty
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    systemctl start labelberry-admin
    echo -e "${GREEN}Service started!${NC}"
    echo -e "${YELLOW}Access the admin interface at: http://$DOMAIN${NC}"
fi