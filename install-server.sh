#!/bin/bash

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   Labelberry Admin Server Installation Script ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/12] Checking system requirements...${NC}"
if ! lsb_release -d | grep -q "Ubuntu"; then
    echo -e "${YELLOW}Warning: This doesn't appear to be Ubuntu${NC}"
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
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
    nginx \
    certbot \
    python3-certbot-nginx \
    build-essential \
    python3-dev \
    uuid-runtime

echo -e "${YELLOW}[4/12] Creating installation directory...${NC}"
INSTALL_DIR="/opt/labelberry-admin"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Installation directory already exists${NC}"
    read -p "Do you want to reinstall? This will backup your database (y/N): " -n 1 -r
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
git clone --sparse https://github.com/Baanaaana/Labelberry.git .
git sparse-checkout init --cone
git sparse-checkout set admin_server shared

echo -e "${YELLOW}[6/12] Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[7/12] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r admin_server/requirements.txt

echo -e "${YELLOW}[8/12] Creating directories...${NC}"
mkdir -p /etc/labelberry
mkdir -p /var/lib/labelberry
mkdir -p /var/log/labelberry

echo -e "${YELLOW}[9/12] Creating configuration...${NC}"
if [ ! -f "/etc/labelberry/server.conf" ]; then
    read -p "Enter the port for the admin server (default 8080): " PORT
    PORT=${PORT:-8080}
    
    cat > /etc/labelberry/server.conf <<EOF
host: 0.0.0.0
port: $PORT
database_path: /var/lib/labelberry/db.sqlite
log_level: INFO
log_file: /var/log/labelberry/server.log
ssl_enabled: false
ssl_cert_path: ""
ssl_key_path: ""
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
Description=Labelberry Admin Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python -m uvicorn admin_server.app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable labelberry-admin.service

echo -e "${YELLOW}[11/12] Configuring nginx...${NC}"
SERVER_NAME=$(hostname -I | awk '{print $1}')
read -p "Enter your domain name (or press Enter to use IP: $SERVER_NAME): " DOMAIN
DOMAIN=${DOMAIN:-$SERVER_NAME}

cat > /etc/nginx/sites-available/labelberry <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    location /ws {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF

ln -sf /etc/nginx/sites-available/labelberry /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

echo -e "${YELLOW}[12/12] Setting up SSL (optional)...${NC}"
read -p "Do you want to set up SSL with Let's Encrypt? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your email for Let's Encrypt: " EMAIL
    certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive
    
    sed -i 's/ssl_enabled: false/ssl_enabled: true/' /etc/labelberry/server.conf
    echo -e "${GREEN}SSL configured successfully${NC}"
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Installation Complete!                     ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Access the admin server at:${NC}"
echo "   http://$DOMAIN"
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "   https://$DOMAIN (SSL enabled)"
fi
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Start the service: sudo systemctl start labelberry-admin"
echo "2. Check status: sudo systemctl status labelberry-admin"
echo "3. View logs: sudo journalctl -u labelberry-admin -f"
echo "4. Access API docs: http://$DOMAIN/docs"
echo ""

read -p "Do you want to start the service now? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    systemctl start labelberry-admin
    echo -e "${GREEN}Service started!${NC}"
    echo -e "${YELLOW}Access the admin interface at: http://$DOMAIN${NC}"
fi