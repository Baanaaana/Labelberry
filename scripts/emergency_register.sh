#!/bin/bash

# Emergency registration script for the problematic printer
# Run this on the admin server to manually add the printer

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

DB_PATH="/var/lib/labelberry/db.sqlite"

echo -e "${GREEN}Emergency Printer Registration${NC}"
echo ""

# The problematic printer details from the logs
DEVICE_ID="b7f5d0d0-5e32-423f-b20b-dd3350c616a3"
API_KEY="223c323c-77f1-47f6-b7f6-0e4e0c5e45e6"  # You'll need to get the full key from the Pi
FRIENDLY_NAME="Printer 2"
PRINTER_MODEL="Zebra Printer"

echo "This will register the printer that's failing to connect."
echo ""
echo "Device ID: $DEVICE_ID"
echo ""
read -p "Enter the FULL API key from the Pi config file: " API_KEY </dev/tty
read -p "Enter a friendly name (default: Printer 2): " FRIENDLY_NAME </dev/tty
FRIENDLY_NAME=${FRIENDLY_NAME:-"Printer 2"}

# Check if already exists
EXISTS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM pis WHERE id='$DEVICE_ID';")

if [ "$EXISTS" -eq "1" ]; then
    echo -e "${YELLOW}Updating existing printer...${NC}"
    sqlite3 "$DB_PATH" "UPDATE pis SET api_key='$API_KEY', friendly_name='$FRIENDLY_NAME' WHERE id='$DEVICE_ID';"
else
    echo -e "${GREEN}Adding new printer...${NC}"
    sqlite3 "$DB_PATH" "INSERT INTO pis (id, friendly_name, api_key, status, queue_count) VALUES ('$DEVICE_ID', '$FRIENDLY_NAME', '$API_KEY', 'offline', 0);"
fi

echo -e "${GREEN}✓ Printer registered${NC}"
echo ""
echo "Now restart the admin service:"
echo "  sudo systemctl restart labelberry-admin"
echo ""
echo "And restart the Pi client service:"
echo "  On the Pi: sudo systemctl restart labelberry-client"