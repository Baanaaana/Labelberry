#!/bin/bash

# LabelBerry Admin Server Installation Script
# Version: 1.0.0
# Last Updated: 2025-08-07

set -e

SCRIPT_VERSION="1.0.4"

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   LabelBerry Admin Server Installation Script ${NC}"
echo -e "${GREEN}   Version: $SCRIPT_VERSION                    ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/13] Checking system requirements...${NC}"
if ! lsb_release -d | grep -q "Ubuntu"; then
    echo -e "${YELLOW}Warning: This doesn't appear to be Ubuntu${NC}"
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r </dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}[2/13] Checking Python version...${NC}"
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

echo -e "${YELLOW}[3/13] Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    build-essential \
    python3-dev \
    uuid-runtime \
    mosquitto \
    mosquitto-clients

echo -e "${YELLOW}[4/13] Creating installation directory...${NC}"
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

echo -e "${YELLOW}[5/13] Cloning repository...${NC}"
cd "$INSTALL_DIR"
git clone --sparse https://github.com/Baanaaana/LabelBerry.git .
git sparse-checkout init --cone
git sparse-checkout set admin_server shared

echo -e "${YELLOW}[6/13] Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[7/13] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r admin_server/requirements.txt

# Create __init__.py files for proper Python package structure
touch admin_server/__init__.py
touch admin_server/app/__init__.py
touch shared/__init__.py

echo -e "${YELLOW}[8/13] Configuring MQTT connection...${NC}"
echo ""
echo -e "${BLUE}MQTT Broker Configuration${NC}"
echo "Choose MQTT broker option:"
echo "1) Use external MQTT broker (recommended if you have one)"
echo "2) Install local Mosquitto broker on this server"
read -p "Enter choice (1 or 2): " MQTT_CHOICE </dev/tty

if [ "$MQTT_CHOICE" = "2" ]; then
    echo -e "${YELLOW}Installing Mosquitto broker...${NC}"
    apt-get install -y mosquitto mosquitto-clients
    
    # Configure Mosquitto
    cat > /etc/mosquitto/conf.d/labelberry.conf <<EOF
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
log_dest file /var/log/mosquitto/mosquitto.log
log_type all
EOF
    
    # Create MQTT user
    read -p "Enter MQTT username (default: labelberry): " MQTT_USER </dev/tty
    MQTT_USER=${MQTT_USER:-labelberry}
    read -s -p "Enter MQTT password: " MQTT_PASS </dev/tty
    echo
    
    touch /etc/mosquitto/passwd
    mosquitto_passwd -b /etc/mosquitto/passwd $MQTT_USER "$MQTT_PASS"
    
    systemctl restart mosquitto
    systemctl enable mosquitto
    
    MQTT_HOST="localhost"
    MQTT_PORT="1883"
else
    echo -e "${YELLOW}Configuring external MQTT broker...${NC}"
    read -p "Enter MQTT broker host/IP: " MQTT_HOST </dev/tty
    read -p "Enter MQTT broker port (default 1883): " MQTT_PORT </dev/tty
    MQTT_PORT=${MQTT_PORT:-1883}
    read -p "Enter MQTT username: " MQTT_USER </dev/tty
    read -s -p "Enter MQTT password: " MQTT_PASS </dev/tty
    echo
fi

echo -e "${YELLOW}[9/13] Creating directories...${NC}"
mkdir -p /etc/labelberry
mkdir -p /var/lib/labelberry
mkdir -p /var/log/labelberry

echo -e "${YELLOW}[10/13] Creating configuration...${NC}"
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
# MQTT Configuration
mqtt_broker: $MQTT_HOST
mqtt_port: $MQTT_PORT
mqtt_username: $MQTT_USER
mqtt_password: $MQTT_PASS
EOF
    
    echo -e "${GREEN}Configuration created${NC}"
else
    echo -e "${YELLOW}Configuration already exists, skipping...${NC}"
    PORT=$(grep "port:" /etc/labelberry/server.conf | cut -d' ' -f2)
fi

echo -e "${YELLOW}[11/13] Creating systemd service...${NC}"
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
Environment="ENABLE_DOCS=false"
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn admin_server.app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable labelberry-admin.service

echo -e "${YELLOW}[12/13] Checking service status...${NC}"

# Check if service is already running
if systemctl is-active --quiet labelberry-admin.service; then
    SERVICE_ACTION="restart"
    SERVICE_STATUS="already running"
else
    SERVICE_ACTION="start"
    SERVICE_STATUS="not running"
fi

echo -e "${YELLOW}Service is ${SERVICE_STATUS}${NC}"

# Get the server IP and port for display
SERVER_IP=$(hostname -I | awk '{print $1}')
PORT=${PORT:-8080}

echo ""
echo -e "${YELLOW}[13/13] Finalizing installation...${NC}"

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Installation Complete!                     ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Access the dashboard at:${NC}"
echo "   http://${SERVER_IP}:${PORT}"
echo ""
echo -e "${YELLOW}MQTT Configuration:${NC}"
echo "   Host: $MQTT_HOST"
echo "   Port: $MQTT_PORT"
echo "   Username: $MQTT_USER"
echo "   Password: [configured]"
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

if [ "$SERVICE_ACTION" = "restart" ]; then
    read -p "Do you want to restart the service now? (Y/n): " -n 1 -r </dev/tty
else
    read -p "Do you want to start the service now? (Y/n): " -n 1 -r </dev/tty
fi
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    systemctl $SERVICE_ACTION labelberry-admin
    echo -e "${GREEN}Service ${SERVICE_ACTION}ed!${NC}"
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo -e "${YELLOW}Access the admin interface at: http://${SERVER_IP}:${PORT}${NC}"
fi