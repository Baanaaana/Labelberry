#!/bin/bash

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${RED}===============================================${NC}"
echo -e "${RED}  Labelberry Admin Server Uninstallation      ${NC}"
echo -e "${RED}===============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}This will remove Labelberry Admin Server from your system.${NC}"
echo -e "${YELLOW}Database and configuration will be backed up to /tmp/labelberry-backup/${NC}"
echo ""
read -p "Are you sure you want to uninstall? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/9] Stopping service...${NC}"
if systemctl is-active --quiet labelberry-admin; then
    systemctl stop labelberry-admin
    echo "Service stopped"
else
    echo "Service was not running"
fi

echo -e "${YELLOW}[2/9] Disabling service...${NC}"
if systemctl is-enabled --quiet labelberry-admin 2>/dev/null; then
    systemctl disable labelberry-admin
    echo "Service disabled"
else
    echo "Service was not enabled"
fi

echo -e "${YELLOW}[3/9] Backing up database...${NC}"
if [ -f "/var/lib/labelberry/db.sqlite" ]; then
    mkdir -p /tmp/labelberry-backup
    cp /var/lib/labelberry/db.sqlite /tmp/labelberry-backup/db.sqlite.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}Database backed up to /tmp/labelberry-backup/${NC}"
else
    echo "No database found to backup"
fi

echo -e "${YELLOW}[4/9] Backing up configuration...${NC}"
if [ -f "/etc/labelberry/server.conf" ]; then
    mkdir -p /tmp/labelberry-backup
    cp /etc/labelberry/server.conf /tmp/labelberry-backup/server.conf.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}Configuration backed up to /tmp/labelberry-backup/${NC}"
else
    echo "No configuration found to backup"
fi

echo -e "${YELLOW}[5/9] Removing nginx configuration...${NC}"
if [ -f "/etc/nginx/sites-enabled/labelberry" ]; then
    rm -f /etc/nginx/sites-enabled/labelberry
    rm -f /etc/nginx/sites-available/labelberry
    nginx -t 2>/dev/null && systemctl reload nginx
    echo "Nginx configuration removed"
else
    echo "No nginx configuration found"
fi

echo -e "${YELLOW}[6/9] Removing service files...${NC}"
rm -f /etc/systemd/system/labelberry-admin.service
systemctl daemon-reload
echo "Service files removed"

echo -e "${YELLOW}[7/9] Removing application files...${NC}"
if [ -d "/opt/labelberry-admin" ]; then
    rm -rf /opt/labelberry-admin
    echo "Application files removed"
else
    echo "Application directory not found"
fi

echo -e "${YELLOW}[8/9] Cleaning up directories...${NC}"

# Ask about removing config directory
read -p "Remove configuration directory /etc/labelberry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /etc/labelberry
    echo "Configuration directory removed"
else
    echo "Configuration directory kept"
fi

# Ask about removing database directory
read -p "Remove database directory /var/lib/labelberry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /var/lib/labelberry
    echo "Database directory removed"
else
    echo "Database directory kept"
fi

# Ask about removing log directory
read -p "Remove log directory /var/log/labelberry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf /var/log/labelberry
    echo "Log directory removed"
else
    echo "Log directory kept"
fi

echo -e "${YELLOW}[9/9] Optional: Uninstall system packages...${NC}"
echo "The following packages were installed for Labelberry:"
echo "  - nginx"
echo "  - certbot"
echo "  - python3-certbot-nginx"
echo "  - sqlite3"
read -p "Do you want to remove these packages? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    apt-get remove -y nginx certbot python3-certbot-nginx sqlite3
    apt-get autoremove -y
    echo "System packages removed"
else
    echo "System packages kept"
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Uninstallation Complete!                  ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo -e "${YELLOW}Labelberry Admin Server has been removed.${NC}"
echo -e "${YELLOW}Backups saved in: /tmp/labelberry-backup/${NC}"
echo ""
echo "To reinstall, run:"
echo "curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-server.sh | sudo bash"
echo ""
echo -e "${YELLOW}Note: If you had SSL certificates, they may still be in /etc/letsencrypt/${NC}"