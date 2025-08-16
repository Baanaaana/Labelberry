#!/bin/bash

# LabelBerry Unified Server Installation Script
# Version: 3.0.0
# Last Updated: 2025-08-16
# Installs unified server with backend (FastAPI) and frontend (Next.js)

set -e

SCRIPT_VERSION="3.0.0"

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}   LabelBerry Complete Server Installation     ${NC}"
echo -e "${GREEN}   Version: $SCRIPT_VERSION                    ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/15] Checking system requirements...${NC}"
if ! lsb_release -d | grep -q "Ubuntu"; then
    echo -e "${YELLOW}Warning: This doesn't appear to be Ubuntu${NC}"
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r </dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}[2/15] Checking Python version...${NC}"
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

echo -e "${YELLOW}[3/15] Installing system dependencies...${NC}"
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

echo -e "${YELLOW}[4/15] Setting up installation directory...${NC}"
INSTALL_DIR="/opt/labelberry"

# Check if directory exists and if it's a git repository
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Installation directory already exists${NC}"
    
    # Check if it's a valid git repository
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo -e "${GREEN}Existing git repository found at $INSTALL_DIR${NC}"
        cd "$INSTALL_DIR"
        
        # Check if this is the LabelBerry repository
        REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
        if [[ "$REMOTE_URL" == *"labelberry"* ]] || [[ "$REMOTE_URL" == *"LabelBerry"* ]]; then
            echo -e "${GREEN}Valid LabelBerry repository detected${NC}"
            echo -e "${YELLOW}Updating repository...${NC}"
            git fetch origin
            git reset --hard origin/main
            git clean -fd
            echo -e "${GREEN}Repository updated${NC}"
            SKIP_CLONE=true
        else
            echo -e "${RED}Directory contains a different git repository${NC}"
            echo -e "${YELLOW}Remote: $REMOTE_URL${NC}"
            read -p "Do you want to remove it and install fresh? (y/N): " -n 1 -r </dev/tty
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$INSTALL_DIR"
                mkdir -p "$INSTALL_DIR"
                SKIP_CLONE=false
            else
                echo -e "${RED}Installation cancelled${NC}"
                exit 1
            fi
        fi
    else
        # Directory exists but is not a git repo
        echo -e "${YELLOW}Directory exists but is not a git repository${NC}"
        read -p "Do you want to reinstall? This will backup any existing data (y/N): " -n 1 -r </dev/tty
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Backup database if it exists
            if [ -f "/var/lib/labelberry/db.sqlite" ]; then
                cp /var/lib/labelberry/db.sqlite /var/lib/labelberry/db.sqlite.backup
                echo -e "${GREEN}Database backed up to /var/lib/labelberry/db.sqlite.backup${NC}"
            fi
            rm -rf "$INSTALL_DIR"
            mkdir -p "$INSTALL_DIR"
            SKIP_CLONE=false
        else
            echo -e "${RED}Installation cancelled${NC}"
            exit 1
        fi
    fi
else
    # Directory doesn't exist, create it
    mkdir -p "$INSTALL_DIR"
    SKIP_CLONE=false
fi

echo -e "${YELLOW}[5/15] Setting up repository...${NC}"
cd "$INSTALL_DIR"

if [ "$SKIP_CLONE" != "true" ]; then
    echo -e "${YELLOW}Cloning repository...${NC}"
    git clone --sparse https://github.com/Baanaaana/labelberry.git .
    git sparse-checkout init --cone
    git sparse-checkout set server shared install
    echo -e "${GREEN}Repository cloned${NC}"
else
    echo -e "${GREEN}Using existing repository${NC}"
    # Ensure we have all required directories
    if [ ! -d "server" ]; then
        echo -e "${YELLOW}Some directories missing, updating sparse-checkout...${NC}"
        git sparse-checkout set server shared install
        git read-tree -m -u HEAD
        echo -e "${GREEN}Directories updated${NC}"
    fi
fi

echo -e "${YELLOW}[6/15] Creating virtual environment...${NC}"
cd server
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[7/15] Installing Python packages...${NC}"
pip install --upgrade pip

# Install packages - ensure all required packages are installed
if [ -f requirements.txt ]; then
    echo -e "${GREEN}Installing from requirements.txt...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}requirements.txt not found, installing essential packages...${NC}"
    pip install fastapi==0.111.0 uvicorn[standard]==0.30.1 python-dotenv==1.0.1 pydantic==2.7.1 pydantic-settings==2.3.4
    pip install asyncpg==0.29.0 psycopg2-binary==2.9.9 sqlalchemy==1.4.48 databases==0.8.0
    pip install python-multipart==0.0.9 aiofiles==24.1.0 httpx==0.27.0 jinja2==3.1.4 
    pip install sse-starlette==2.1.2 itsdangerous==2.2.0 paho-mqtt==2.1.0 pyyaml==6.0.1 requests==2.32.3
fi

# Verify critical packages are installed
echo -e "${YELLOW}Verifying critical packages...${NC}"
for package in uvicorn fastapi pydantic asyncpg psycopg2-binary paho-mqtt; do
    if ! pip show $package > /dev/null 2>&1; then
        echo -e "${YELLOW}Installing missing package: $package${NC}"
        pip install $package
    fi
done
echo -e "${GREEN}All critical packages verified${NC}"

# Create __init__.py files for proper Python package structure
touch __init__.py
touch api/__init__.py
cd ..
touch shared/__init__.py

# Ensure we deactivate the venv properly
deactivate

echo -e "${YELLOW}[8/15] Creating directories...${NC}"
mkdir -p /etc/labelberry
mkdir -p /var/lib/labelberry
mkdir -p /var/log/labelberry

echo -e "${YELLOW}[9/15] MQTT Configuration...${NC}"
echo -e "${CYAN}MQTT settings are managed through the web interface${NC}"
echo -e "${CYAN}You can configure MQTT after installation via the Settings page${NC}"

# Set default placeholder values for MQTT (will be configured via web interface)
MQTT_HOST="localhost"
MQTT_PORT="1883"
MQTT_USER=""
MQTT_PASS=""

echo -e "${YELLOW}[10/15] Creating configuration...${NC}"
if [ ! -f "/etc/labelberry/server.conf" ]; then
    read -p "Enter the port for the admin server (default 8080): " PORT </dev/tty
    PORT=${PORT:-8080}
else
    echo -e "${YELLOW}Configuration already exists, updating MQTT settings...${NC}"
    # Try to extract port from existing config, use default if not found
    PORT=$(grep "^port:" /etc/labelberry/server.conf | head -n1 | cut -d' ' -f2)
    # Validate and set default if empty or invalid
    if [ -z "$PORT" ] || ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
        PORT=8080
        echo -e "${YELLOW}Could not parse existing port, using default: 8080${NC}"
    else
        echo -e "${GREEN}Using existing port: $PORT${NC}"
    fi
    # Backup existing config
    cp /etc/labelberry/server.conf /etc/labelberry/server.conf.backup
fi

# Always create/update the config file (MQTT will be configured via web interface)
cat > /etc/labelberry/server.conf <<EOF
host: 0.0.0.0
port: ${PORT:-8080}
database_path: /var/lib/labelberry/db.sqlite
log_level: INFO
log_file: /var/log/labelberry/server.log
cors_origins: ["*"]
rate_limit: 100
session_timeout: 3600
# MQTT Configuration - Managed via web interface
# These are placeholder values that will be configured through the web UI
mqtt_broker: localhost
mqtt_port: 1883
mqtt_username: 
mqtt_password: 
EOF

echo -e "${GREEN}Configuration created/updated${NC}"
echo -e "${CYAN}Note: MQTT settings are managed through the web interface Settings page${NC}"

echo -e "${YELLOW}[10/15] Creating .env files...${NC}"

# Create unified .env file
SERVER_IP=$(hostname -I | awk '{print $1}')

# Ask for domain if not in local mode
echo -e "${YELLOW}Will you be accessing this server via a domain name? (y/N)${NC}"
read -p "" -n 1 -r </dev/tty
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain (e.g., labelberry.yourdomain.com): " DOMAIN </dev/tty
    NEXTAUTH_URL="https://$DOMAIN"
else
    NEXTAUTH_URL="http://$SERVER_IP:3000"
fi

cat > $INSTALL_DIR/server/.env <<EOF
# ==========================================
# LabelBerry Server Configuration
# Single .env file for both API and Web
# ==========================================

# Database Configuration
DATABASE_URL=postgresql://your_user:your_password@your_host/your_database

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=$PORT
DEBUG=false
ENABLE_DOCS=true
STATIC_VERSION=1.0

# Local mode (disables MQTT for development)
# MQTT settings are configured through the web interface
LABELBERRY_LOCAL_MODE=false

# Next.js Frontend Configuration
# Using relative paths for production (works with reverse proxy)
NEXT_PUBLIC_API_URL=/api
NEXT_PUBLIC_WS_URL=/api
NEXTAUTH_URL=$NEXTAUTH_URL
NEXTAUTH_SECRET=$(openssl rand -base64 32)
NODE_ENV=production
EOF

echo -e "${GREEN}Created unified .env file${NC}"

echo -e "${YELLOW}[11/15] Setting up Node.js environment...${NC}"

# Install NVM (Node Version Manager) for better Node.js management
export NVM_DIR="/opt/nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing NVM (Node Version Manager)..."
    mkdir -p $NVM_DIR
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | NVM_DIR=$NVM_DIR bash
    echo -e "${GREEN}NVM installed${NC}"
fi

# Load NVM
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install latest Node.js LTS using NVM
NODE_VERSION="lts/*"
echo "Installing Node.js $NODE_VERSION..."
nvm install $NODE_VERSION
nvm alias default $NODE_VERSION
nvm use $NODE_VERSION
echo -e "${GREEN}Node.js $(node --version) installed via NVM${NC}"

# Update npm to latest version
echo "Updating npm to latest version..."
npm install -g npm@latest
echo -e "${GREEN}npm updated to $(npm --version)${NC}"

# Install PM2 globally
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2 process manager..."
    npm install -g pm2
    echo -e "${GREEN}PM2 installed${NC}"
else
    echo "Updating PM2..."
    npm update -g pm2
    echo -e "${GREEN}PM2 updated${NC}"
fi

echo -e "${YELLOW}[12/15] Building Next.js frontend...${NC}"
cd "$INSTALL_DIR/server"

# Check if lib/utils.ts exists, create if missing
if [ ! -f "lib/utils.ts" ]; then
    mkdir -p lib
    cat > lib/utils.ts << 'EOF'
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
EOF
    echo -e "${GREEN}Created missing lib/utils.ts${NC}"
fi

# Install dependencies
echo "Installing frontend dependencies..."
npm install

# Build the Next.js application
echo "Building Next.js application..."
export NODE_OPTIONS="--max_old_space_size=2048"
export NEXT_TELEMETRY_DISABLED=1
npm run build

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Next.js build successful${NC}"
else
    echo -e "${RED}Next.js build failed${NC}"
    echo "Trying to fix common issues..."
    npm install clsx tailwind-merge
    npm run build || {
        echo -e "${RED}Build still failing. Please check the error messages above${NC}"
        exit 1
    }
fi

echo -e "${YELLOW}[13/15] Configuring PM2 for Next.js...${NC}"

# Create ecosystem config for PM2
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'labelberry-nextjs',
    script: 'npm',
    args: 'start',
    cwd: '/opt/labelberry/server',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    max_memory_restart: '500M',
    error_file: '/var/log/labelberry/nextjs-error.log',
    out_file: '/var/log/labelberry/nextjs-out.log',
    merge_logs: true,
    time: true
  }]
}
EOF

# Start Next.js with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup systemd -u root --hp /root | grep "sudo" | bash

echo -e "${GREEN}Next.js frontend configured with PM2${NC}"

cd "$INSTALL_DIR"

echo -e "${YELLOW}[14/15] Creating backend systemd service...${NC}"
cat > /etc/systemd/system/labelberry-admin.service <<EOF
[Unit]
Description=LabelBerry Admin Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/server
Environment="PATH=$INSTALL_DIR/server/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=$INSTALL_DIR/server"
Environment="ENABLE_DOCS=true"
ExecStart=$INSTALL_DIR/server/venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable labelberry-admin.service

echo -e "${YELLOW}[15/15] Checking services status...${NC}"

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
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Server Installation Complete!               ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Access Points:${NC}"
echo "   Web Interface: http://${SERVER_IP}:3000"
echo "   API Server: http://${SERVER_IP}:${PORT}"
echo ""
echo -e "${YELLOW}MQTT Configuration:${NC}"
echo "   Configure MQTT settings through the web interface Settings page"
echo ""
echo -e "${YELLOW}Service Status:${NC}"
echo "   sudo systemctl status labelberry-admin"
echo ""
echo -e "${YELLOW}View Logs:${NC}"
echo "   sudo journalctl -u labelberry-admin -f"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "   1. Access the web interface at http://${SERVER_IP}:3000"
echo "   2. Configure your Raspberry Pi clients to connect to this server"
echo "   3. For domain/SSL setup, use Nginx Proxy Manager"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "   Backend logs: sudo journalctl -u labelberry-admin -f"
echo "   Frontend logs: pm2 logs labelberry-nextjs"
echo "   Frontend status: pm2 status"
echo "   Update system: cd /opt/labelberry && ./deploy.sh"
echo ""

# Set up menu in .bashrc for easy access
echo -e "${CYAN}Setting up LabelBerry menu...${NC}"

# Download the labelberry-menu.sh if it doesn't exist
if [ ! -f "$INSTALL_DIR/labelberry-menu.sh" ]; then
    curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/labelberry-menu.sh -o $INSTALL_DIR/labelberry-menu.sh
    chmod +x $INSTALL_DIR/labelberry-menu.sh
fi

# Add to root's .bashrc if not already there
if ! grep -q "source /opt/labelberry/labelberry-menu.sh" /root/.bashrc 2>/dev/null; then
    echo "" >> /root/.bashrc
    echo "# LabelBerry Management Menu" >> /root/.bashrc
    echo "source /opt/labelberry/labelberry-menu.sh" >> /root/.bashrc
fi

# Also add to regular user's .bashrc if they exist
for user_home in /home/*; do
    if [ -d "$user_home" ]; then
        username=$(basename "$user_home")
        if ! grep -q "source /opt/labelberry/labelberry-menu.sh" "$user_home/.bashrc" 2>/dev/null; then
            echo "" >> "$user_home/.bashrc"
            echo "# LabelBerry Management Menu" >> "$user_home/.bashrc"
            echo "source /opt/labelberry/labelberry-menu.sh" >> "$user_home/.bashrc"
            chown $username:$username "$user_home/.bashrc"
        fi
    fi
done

echo -e "${GREEN}✓ Menu installed successfully!${NC}"
echo -e "${YELLOW}Run 'source ~/.bashrc' to load the menu in this session${NC}"
echo -e "${CYAN}Commands: labelberry, lb, lblogs, lbstatus, lbrestart${NC}"
echo ""

if [ "$SERVICE_ACTION" = "restart" ]; then
    read -p "Do you want to restart the service now? (Y/n): " -n 1 -r </dev/tty
else
    read -p "Do you want to start the service now? (Y/n): " -n 1 -r </dev/tty
fi
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    systemctl $SERVICE_ACTION labelberry-admin
    echo -e "${GREEN}Services ${SERVICE_ACTION}ed!${NC}"
    
    # Also restart PM2 apps
    pm2 restart labelberry-nextjs 2>/dev/null || pm2 start ecosystem.config.js
    
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}LabelBerry server is now running!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Access the web interface at:${NC}"
    echo -e "${WHITE}http://${SERVER_IP}:3000${NC}"
    echo ""
fi