#!/bin/bash

# ============================================
# LABELBERRY SERVICE UPDATE SCRIPT
# Version: 1.0.0
# Purpose: Fix service configuration after installation
# ============================================

# Color definitions
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}     LabelBerry Service Configuration Update${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo -e "${RED}Please run as root or with sudo${NC}"
   exit 1
fi

echo -e "${YELLOW}Updating systemd service configuration...${NC}"

# Create correct service file
cat > /etc/systemd/system/labelberry-admin.service <<EOF
[Unit]
Description=LabelBerry Admin Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/labelberry/admin_server
Environment="PATH=/opt/labelberry/admin_server/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/opt/labelberry/admin_server"
Environment="ENABLE_DOCS=false"
ExecStart=/opt/labelberry/admin_server/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file updated${NC}"

# Reload systemd
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

# Stop old service if running
echo -e "${YELLOW}Stopping service...${NC}"
systemctl stop labelberry-admin 2>/dev/null
echo -e "${GREEN}✓ Service stopped${NC}"

# Enable and start service
echo -e "${YELLOW}Starting service with new configuration...${NC}"
systemctl enable labelberry-admin
systemctl start labelberry-admin

# Check status
sleep 2
if systemctl is-active --quiet labelberry-admin; then
    echo -e "${GREEN}✅ Service is running successfully!${NC}"
    echo ""
    echo -e "${CYAN}Service Status:${NC}"
    systemctl status labelberry-admin --no-pager | head -15
else
    echo -e "${RED}⚠ Service failed to start${NC}"
    echo ""
    echo -e "${YELLOW}Checking logs:${NC}"
    journalctl -u labelberry-admin -n 20 --no-pager
    echo ""
    echo -e "${YELLOW}Common issues:${NC}"
    echo "1. Check if virtual environment exists: ls -la /opt/labelberry/admin_server/venv/"
    echo "2. Check if main.py exists: ls -la /opt/labelberry/admin_server/app/main.py"
    echo "3. Check Python dependencies: /opt/labelberry/admin_server/venv/bin/pip list"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Update complete!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"