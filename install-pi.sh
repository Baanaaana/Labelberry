#!/bin/bash

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    LabelBerry Pi Client Installation Script   ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/10] Checking system requirements...${NC}"
if ! grep -q "Raspberry Pi" /proc/cpuinfo && ! grep -q "BCM" /proc/cpuinfo; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r </dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}[2/10] Checking Python version...${NC}"
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

echo -e "${YELLOW}[3/10] Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    build-essential \
    python3-dev \
    uuid-runtime

echo -e "${YELLOW}[4/10] Creating installation directory...${NC}"
INSTALL_DIR="/opt/labelberry"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Installation directory already exists${NC}"
    read -p "Do you want to reinstall? This will backup your config (y/N): " -n 1 -r </dev/tty
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "/etc/labelberry/client.conf" ]; then
            cp /etc/labelberry/client.conf /etc/labelberry/client.conf.backup
            echo -e "${GREEN}Config backed up to /etc/labelberry/client.conf.backup${NC}"
        fi
        rm -rf "$INSTALL_DIR"
    else
        exit 1
    fi
fi
mkdir -p "$INSTALL_DIR"

echo -e "${YELLOW}[5/10] Cloning repository...${NC}"
cd "$INSTALL_DIR"
git clone --sparse https://github.com/Baanaaana/LabelBerry.git .
git sparse-checkout init --cone
git sparse-checkout set pi_client shared

echo -e "${YELLOW}[6/10] Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[7/10] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r pi_client/requirements.txt

# Create __init__.py files for proper Python package structure
touch pi_client/__init__.py
touch pi_client/app/__init__.py
touch shared/__init__.py

echo -e "${YELLOW}[8/10] Creating configuration...${NC}"
mkdir -p /etc/labelberry
mkdir -p /var/lib/labelberry
mkdir -p /var/log/labelberry

if [ -f "/etc/labelberry/client.conf.backup" ]; then
    echo -e "${GREEN}Restoring previous configuration...${NC}"
    mv /etc/labelberry/client.conf.backup /etc/labelberry/client.conf
else
    echo -e "${YELLOW}Running initial configuration...${NC}"
    
    # Try uuidgen first, fallback to Python if not available
    if command -v uuidgen &> /dev/null; then
        DEVICE_ID=$(uuidgen)
        API_KEY=$(uuidgen)
    else
        DEVICE_ID=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
        API_KEY=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
    fi
    
    read -p "Enter the admin server URL (e.g., http://192.168.1.100:8080): " ADMIN_SERVER </dev/tty
    
    cat > /etc/labelberry/client.conf <<EOF
device_id: $DEVICE_ID
api_key: $API_KEY
admin_server: $ADMIN_SERVER
printer_device: /dev/usblp0
queue_size: 100
retry_attempts: 3
retry_delay: 5
log_level: INFO
log_file: /var/log/labelberry/client.log
metrics_interval: 60
EOF
    
    echo -e "${GREEN}Configuration created${NC}"
    echo -e "${YELLOW}Device ID: $DEVICE_ID${NC}"
    echo -e "${YELLOW}API Key: $API_KEY${NC}"
    echo -e "${YELLOW}Please save these values for admin server registration${NC}"
fi

echo -e "${YELLOW}[9/10] Creating systemd service...${NC}"
cat > /etc/systemd/system/labelberry-client.service <<EOF
[Unit]
Description=LabelBerry Pi Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn pi_client.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable labelberry-client.service

echo -e "${YELLOW}[10/10] Creating CLI symlink...${NC}"
cat > /usr/local/bin/labelberry <<EOF
#!/bin/bash
export PYTHONPATH=$INSTALL_DIR
$INSTALL_DIR/venv/bin/python $INSTALL_DIR/pi_client/cli/labelberry_cli.py "\$@"
EOF
chmod +x /usr/local/bin/labelberry

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Installation Complete!                     ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Connect your Zebra printer via USB"
echo "2. Start the service: sudo systemctl start labelberry-client"
echo "3. Check status: sudo systemctl status labelberry-client"
echo "4. View logs: sudo journalctl -u labelberry-client -f"
echo "5. Use CLI: labelberry status"
echo ""
echo -e "${YELLOW}Register this Pi on your admin server with:${NC}"
echo "   Device ID: $(grep device_id /etc/labelberry/client.conf | cut -d' ' -f2)"
echo "   API Key: $(grep api_key /etc/labelberry/client.conf | cut -d' ' -f2)"
echo ""

read -p "Do you want to start the service now? (Y/n): " -n 1 -r </dev/tty
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    systemctl start labelberry-client
    echo -e "${GREEN}Service started!${NC}"
    echo "Check status with: sudo systemctl status labelberry-client"
fi