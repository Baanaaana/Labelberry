#!/bin/bash

# Script to retry registration of printers with admin server
# This is installed on the Pi and can be run after installation if registration failed

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    Retry Printer Registration                ${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""

# Get admin server from config
if [ -f "/etc/labelberry/client.conf" ]; then
    ADMIN_SERVER=$(grep "admin_server:" /etc/labelberry/client.conf | cut -d' ' -f2)
else
    echo -e "${RED}Configuration file not found${NC}"
    exit 1
fi

if [ -z "$ADMIN_SERVER" ]; then
    read -p "Enter admin server URL (e.g., http://192.168.1.100:8080): " ADMIN_SERVER </dev/tty
fi

echo -e "${YELLOW}Admin Server: $ADMIN_SERVER${NC}"
echo ""

# Test connection to admin server
echo -e "${YELLOW}Testing connection to admin server...${NC}"
if curl -s -f -o /dev/null "$ADMIN_SERVER/api/health" 2>/dev/null; then
    echo -e "${GREEN}✓ Admin server is reachable${NC}"
else
    echo -e "${RED}✗ Cannot connect to admin server at $ADMIN_SERVER${NC}"
    echo "Please check:"
    echo "1. The admin server is running"
    echo "2. The URL is correct"
    echo "3. No firewall is blocking the connection"
    exit 1
fi

echo ""
SUCCESS_COUNT=0
FAIL_COUNT=0

# Check for multi-printer setup
if [ -d "/etc/labelberry/printers" ] && [ "$(ls -A /etc/labelberry/printers)" ]; then
    echo -e "${YELLOW}Found multi-printer configuration${NC}"
    echo ""
    
    for config_file in /etc/labelberry/printers/*.conf; do
        if [ -f "$config_file" ]; then
            # Extract values from config
            DEVICE_ID=$(grep "device_id:" "$config_file" | cut -d' ' -f2)
            API_KEY=$(grep "api_key:" "$config_file" | cut -d' ' -f2)
            NAME=$(grep "name:" "$config_file" | cut -d' ' -f2-)
            MODEL=$(grep "printer_model:" "$config_file" | cut -d' ' -f2-)
            
            echo -e "${BLUE}Registering: $NAME${NC}"
            echo "  Device ID: ${DEVICE_ID:0:8}..."
            
            # Create registration JSON
            REGISTER_DATA="{\"id\":\"$DEVICE_ID\",\"friendly_name\":\"$NAME\",\"api_key\":\"$API_KEY\",\"printer_model\":\"$MODEL\"}"
            
            # Register with admin server
            RESPONSE=$(curl -s -X POST "$ADMIN_SERVER/api/pis/register" \
                -H "Content-Type: application/json" \
                -d "$REGISTER_DATA" \
                -w "\nHTTP_STATUS:%{http_code}" \
                2>/dev/null)
            
            HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
            
            if [ "$HTTP_STATUS" = "200" ]; then
                echo -e "  ${GREEN}✓ Successfully registered${NC}"
                SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            else
                echo -e "  ${RED}✗ Registration failed (HTTP $HTTP_STATUS)${NC}"
                FAIL_COUNT=$((FAIL_COUNT + 1))
            fi
            echo ""
        fi
    done
else
    # Single printer setup
    echo -e "${YELLOW}Found single printer configuration${NC}"
    
    DEVICE_ID=$(grep "device_id:" /etc/labelberry/client.conf | cut -d' ' -f2)
    API_KEY=$(grep "api_key:" /etc/labelberry/client.conf | cut -d' ' -f2)
    NAME=$(grep "friendly_name:" /etc/labelberry/client.conf | cut -d' ' -f2- || echo "LabelBerry Pi")
    MODEL=$(grep "printer_model:" /etc/labelberry/client.conf | cut -d' ' -f2- || echo "Unknown")
    
    echo "  Device ID: ${DEVICE_ID:0:8}..."
    
    # Create registration JSON
    REGISTER_DATA="{\"id\":\"$DEVICE_ID\",\"friendly_name\":\"$NAME\",\"api_key\":\"$API_KEY\",\"printer_model\":\"$MODEL\"}"
    
    # Register with admin server
    RESPONSE=$(curl -s -X POST "$ADMIN_SERVER/api/pis/register" \
        -H "Content-Type: application/json" \
        -d "$REGISTER_DATA" \
        -w "\nHTTP_STATUS:%{http_code}" \
        2>/dev/null)
    
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
    
    if [ "$HTTP_STATUS" = "200" ]; then
        echo -e "  ${GREEN}✓ Successfully registered${NC}"
        SUCCESS_COUNT=1
    else
        echo -e "  ${RED}✗ Registration failed (HTTP $HTTP_STATUS)${NC}"
        FAIL_COUNT=1
    fi
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All printers registered successfully!${NC}"
    echo ""
    echo "Now restart the service:"
    echo "  sudo systemctl restart labelberry-client"
else
    echo -e "${YELLOW}Registration complete${NC}"
    echo -e "${GREEN}✓ Success: $SUCCESS_COUNT${NC}"
    echo -e "${RED}✗ Failed: $FAIL_COUNT${NC}"
    echo ""
    echo "Check the admin server logs for details:"
    echo "  On admin server: sudo journalctl -u labelberry-admin -f"
fi
echo -e "${GREEN}===============================================${NC}"