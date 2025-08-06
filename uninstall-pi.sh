#!/bin/bash

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${RED}===============================================${NC}"
echo -e "${RED}  Labelberry Pi Client Uninstallation Script  ${NC}"
echo -e "${RED}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}This will remove Labelberry Pi Client from your system.${NC}"
echo -e "${YELLOW}Configuration will be backed up to /tmp/labelberry-backup/${NC}"
echo ""
read -p "Are you sure you want to uninstall? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/7] Stopping service...${NC}"
if systemctl is-active --quiet labelberry-client; then
    systemctl stop labelberry-client
    echo "Service stopped"
else
    echo "Service was not running"
fi

echo -e "${YELLOW}[2/7] Disabling service...${NC}"
if systemctl is-enabled --quiet labelberry-client 2>/dev/null; then
    systemctl disable labelberry-client
    echo "Service disabled"
else
    echo "Service was not enabled"
fi

echo -e "${YELLOW}[3/7] Backing up configuration...${NC}"
if [ -f "/etc/labelberry/client.conf" ]; then
    mkdir -p /tmp/labelberry-backup
    cp /etc/labelberry/client.conf /tmp/labelberry-backup/client.conf.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}Configuration backed up to /tmp/labelberry-backup/${NC}"
    
    # Extract and display the device ID and API key for reference
    DEVICE_ID=$(grep device_id /etc/labelberry/client.conf | cut -d' ' -f2)
    API_KEY=$(grep api_key /etc/labelberry/client.conf | cut -d' ' -f2)
    FRIENDLY_NAME=$(grep friendly_name /etc/labelberry/client.conf | cut -d' ' -f2)
    
    echo ""
    echo -e "${YELLOW}Save these values if you plan to reinstall:${NC}"
    echo "Device ID: $DEVICE_ID"
    echo "API Key: $API_KEY"
    echo "Friendly Name: $FRIENDLY_NAME"
    echo ""
else
    echo "No configuration found to backup"
fi

echo -e "${YELLOW}[4/7] Removing service files...${NC}"
rm -f /etc/systemd/system/labelberry-client.service
systemctl daemon-reload
echo "Service files removed"

echo -e "${YELLOW}[5/7] Removing CLI command...${NC}"
rm -f /usr/local/bin/labelberry
rm -f /usr/local/bin/labelberry-python
echo "CLI command removed"

echo -e "${YELLOW}[6/7] Removing application files...${NC}"
if [ -d "/opt/labelberry" ]; then
    rm -rf /opt/labelberry
    echo "Application files removed"
else
    echo "Application directory not found"
fi

echo -e "${YELLOW}[7/7] Cleaning up directories...${NC}"
# Ask about removing config and data
read -p "Remove configuration directory /etc/labelberry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /etc/labelberry
    echo "Configuration directory removed"
else
    echo "Configuration directory kept"
fi

read -p "Remove data directory /var/lib/labelberry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /var/lib/labelberry
    echo "Data directory removed"
else
    echo "Data directory kept"
fi

read -p "Remove log directory /var/log/labelberry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /var/log/labelberry
    echo "Log directory removed"
else
    echo "Log directory kept"
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Uninstallation Complete!                  ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Labelberry Pi Client has been removed.${NC}"
echo -e "${YELLOW}Configuration backup saved in: /tmp/labelberry-backup/${NC}"
echo ""
echo "To reinstall, run:"
echo "curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-pi.sh | sudo bash"