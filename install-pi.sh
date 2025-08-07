#!/bin/bash

# LabelBerry Pi Client Installation Script
# Version: 1.0.0
# Last Updated: 2025-08-07

set -e

SCRIPT_VERSION="1.0.2"

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}    LabelBerry Pi Client Installation Script   ${NC}"
echo -e "${GREEN}    Version: $SCRIPT_VERSION                   ${NC}"
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

echo -e "${YELLOW}[3/11] Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    build-essential \
    python3-dev \
    uuid-runtime \
    usbutils

echo -e "${YELLOW}[4/11] Detecting Zebra printers...${NC}"
echo ""

# Detect all Zebra printers
PRINTER_COUNT=0
PRINTER_DEVICES=()

# Check for USB Zebra devices
USB_DEVICES=$(lsusb | grep -i "zebra" || true)

# Load usblp kernel module
if ! lsmod | grep -q usblp; then
    echo -e "${YELLOW}Loading usblp kernel module...${NC}"
    modprobe usblp || true
    sleep 2
    
    # Sometimes the module needs a trigger to create the device
    if [ -n "$USB_DEVICES" ]; then
        echo -e "${YELLOW}Triggering USB device detection...${NC}"
        # Unbind and rebind USB devices to trigger usblp device creation
        for device in /sys/bus/usb/devices/*/idVendor; do
            if grep -q "0a5f" "$device" 2>/dev/null; then
                DEV_PATH=$(dirname "$device")
                DEV_NAME=$(basename "$DEV_PATH")
                echo -e "${YELLOW}Rebinding USB device $DEV_NAME...${NC}"
                echo "$DEV_NAME" > /sys/bus/usb/drivers/usb/unbind 2>/dev/null || true
                sleep 1
                echo "$DEV_NAME" > /sys/bus/usb/drivers/usb/bind 2>/dev/null || true
                sleep 2
            fi
        done
    fi
fi

# Ensure usblp module loads on boot
if ! grep -q "^usblp$" /etc/modules 2>/dev/null; then
    echo -e "${YELLOW}Adding usblp to auto-load on boot...${NC}"
    echo "usblp" >> /etc/modules
fi

if [ -z "$USB_DEVICES" ]; then
    echo -e "${YELLOW}No Zebra printers detected via USB${NC}"
    echo "Continuing with manual configuration..."
    PRINTER_COUNT=1
    PRINTER_DEVICES=("/dev/usblp0")
    PRINTER_MODELS=("Unknown")
else
    echo -e "${GREEN}Found Zebra printer(s):${NC}"
    echo "$USB_DEVICES"
    echo ""
    
    # Extract printer models from lsusb output
    PRINTER_MODELS=()
    while IFS= read -r line; do
        # Extract the model name from lsusb output (e.g., "Zebra Technologies ZTC ZD220-203dpi ZPL")
        MODEL=$(echo "$line" | sed 's/.*Zebra Technologies //' | sed 's/  */ /g')
        PRINTER_MODELS+=("$MODEL")
    done <<< "$USB_DEVICES"
    
    # Count the number of USB devices found
    USB_COUNT=$(echo "$USB_DEVICES" | wc -l)
    
    # Find all USB printer devices
    FOUND_DEVICES=()
    for device in /dev/usblp*; do
        if [ -e "$device" ]; then
            FOUND_DEVICES+=("$device")
        fi
    done
    
    # If we detected multiple USB printers but no devices yet, wait and retry
    if [ $USB_COUNT -gt 1 ] && [ ${#FOUND_DEVICES[@]} -eq 0 ]; then
        echo -e "${YELLOW}Detected $USB_COUNT Zebra printers via USB but devices not ready yet...${NC}"
        echo "Waiting for devices to initialize..."
        sleep 3
        
        # Retry finding devices
        FOUND_DEVICES=()
        for device in /dev/usblp*; do
            if [ -e "$device" ]; then
                FOUND_DEVICES+=("$device")
            fi
        done
    fi
    
    # If still no devices found, inform user about pyusb fallback
    if [ ${#FOUND_DEVICES[@]} -eq 0 ] && [ -n "$USB_DEVICES" ]; then
        echo -e "${YELLOW}Note: /dev/usblp* devices not found, but printer was detected via USB.${NC}"
        echo -e "${YELLOW}LabelBerry will use direct USB communication (pyusb) as fallback.${NC}"
        echo -e "${YELLOW}This is normal and printing should still work.${NC}"
    fi
    
    # Determine printer count and devices
    if [ ${#FOUND_DEVICES[@]} -eq 0 ]; then
        # No devices found, but we know how many USB printers there are
        if [ $USB_COUNT -gt 1 ]; then
            echo -e "${YELLOW}No USB printer devices found in /dev/ yet${NC}"
            echo -e "${YELLOW}Configuring for $USB_COUNT printers based on USB detection${NC}"
            PRINTER_COUNT=$USB_COUNT
            PRINTER_DEVICES=()
            for ((i=0; i<$USB_COUNT; i++)); do
                PRINTER_DEVICES+=("/dev/usblp$i")
            done
            echo -e "${YELLOW}Will use devices: ${PRINTER_DEVICES[@]}${NC}"
        else
            echo -e "${YELLOW}No USB printer devices found in /dev/${NC}"
            echo "Using default device /dev/usblp0"
            PRINTER_COUNT=1
            PRINTER_DEVICES=("/dev/usblp0")
        fi
    else
        PRINTER_COUNT=${#FOUND_DEVICES[@]}
        PRINTER_DEVICES=("${FOUND_DEVICES[@]}")
        echo -e "${GREEN}Found $PRINTER_COUNT printer device(s):${NC}"
        for device in "${PRINTER_DEVICES[@]}"; do
            echo "  - $device"
        done
        echo ""
    fi
fi

echo -e "${YELLOW}[5/11] Creating installation directory...${NC}"
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

echo -e "${YELLOW}[6/11] Cloning repository...${NC}"
cd "$INSTALL_DIR"
git clone --sparse https://github.com/Baanaaana/LabelBerry.git .
git sparse-checkout init --cone
git sparse-checkout set pi_client shared

echo -e "${YELLOW}[7/11] Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}[8/11] Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r pi_client/requirements.txt

# Create __init__.py files for proper Python package structure
touch pi_client/__init__.py
touch pi_client/app/__init__.py
touch shared/__init__.py

echo -e "${YELLOW}[9/11] Creating configuration...${NC}"
mkdir -p /etc/labelberry
mkdir -p /etc/labelberry/printers
mkdir -p /var/lib/labelberry
mkdir -p /var/log/labelberry

if [ -f "/etc/labelberry/client.conf.backup" ]; then
    echo -e "${GREEN}Restoring previous configuration...${NC}"
    mv /etc/labelberry/client.conf.backup /etc/labelberry/client.conf
    # Also restore printer configs if they exist
    if [ -d "/etc/labelberry/printers.backup" ]; then
        rm -rf /etc/labelberry/printers
        mv /etc/labelberry/printers.backup /etc/labelberry/printers
    fi
else
    echo -e "${YELLOW}Running initial configuration...${NC}"
    echo ""
    
    read -p "Enter the admin server URL (e.g., http://192.168.1.100:8080): " ADMIN_SERVER </dev/tty
    echo ""
    
    # Check if we have multiple printers
    if [ $PRINTER_COUNT -gt 1 ]; then
        echo -e "${GREEN}===============================================${NC}"
        echo -e "${GREEN}    Configuring $PRINTER_COUNT printer(s)              ${NC}"
        echo -e "${GREEN}===============================================${NC}"
        echo ""
        echo -e "${YELLOW}Generating credentials for each printer...${NC}"
        echo -e "${YELLOW}You'll need to register each printer in the admin dashboard${NC}"
        echo ""
        
        # Create main config file for multi-printer mode
        cat > /etc/labelberry/client.conf <<EOF
# LabelBerry Multi-Printer Configuration
device_id: multi-printer-mode
api_key: multi-printer-mode
admin_server: $ADMIN_SERVER
printer_device: /dev/usblp0
queue_size: 100
retry_attempts: 3
retry_delay: 5
log_level: INFO
log_file: /var/log/labelberry/client.log
metrics_interval: 60
multi_printer_mode: true
printers:
EOF
        
        ALL_CONFIGS=""
        
        for i in "${!PRINTER_DEVICES[@]}"; do
            PRINTER_NUM=$((i + 1))
            DEVICE="${PRINTER_DEVICES[$i]}"
            
            echo -e "${BLUE}------- Printer $PRINTER_NUM -------${NC}"
            echo -e "Device: ${YELLOW}$DEVICE${NC}"
            
            # Use a generic name for the config file
            PRINTER_NAME="Printer $PRINTER_NUM"
            
            # Generate unique IDs for this printer
            if command -v uuidgen &> /dev/null; then
                DEVICE_ID=$(uuidgen)
                API_KEY=$(uuidgen)
            else
                DEVICE_ID=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
                API_KEY=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
            fi
            
            # Get printer model if available
            if [ ${#PRINTER_MODELS[@]} -gt 0 ]; then
                # If we have models, try to get the corresponding one or use the last one
                if [ $i -lt ${#PRINTER_MODELS[@]} ]; then
                    PRINTER_MODEL="${PRINTER_MODELS[$i]}"
                else
                    # If we have fewer models than devices, use the last model (they might be the same)
                    PRINTER_MODEL="${PRINTER_MODELS[-1]}"
                fi
            else
                PRINTER_MODEL="Unknown"
            fi
            
            # Create individual printer config file
            cat > "/etc/labelberry/printers/printer_${i}.conf" <<EOF
# Configuration for $PRINTER_NAME
name: $PRINTER_NAME
device_id: $DEVICE_ID
api_key: $API_KEY
device_path: $DEVICE
printer_model: $PRINTER_MODEL
enabled: true
EOF
            
            # Add to main config
            echo "  printer_${i}: /etc/labelberry/printers/printer_${i}.conf" >> /etc/labelberry/client.conf
            
            # Store for summary
            ALL_CONFIGS="${ALL_CONFIGS}\n${GREEN}Printer $PRINTER_NUM (${PRINTER_MODEL}):${NC}\n  Device ID: ${BLUE}$DEVICE_ID${NC}\n  API Key: ${BLUE}$API_KEY${NC}\n  Device: ${YELLOW}$DEVICE${NC}\n"
            
            echo -e "${GREEN}✓ Generated credentials for Printer $PRINTER_NUM${NC}"
            
            # Try to register with admin server
            if [ ! -z "$ADMIN_SERVER" ]; then
                echo -e "${YELLOW}  Attempting to register with admin server...${NC}"
                
                # Create registration request
                REGISTER_DATA="{\"id\":\"$DEVICE_ID\",\"friendly_name\":\"$PRINTER_NAME\",\"api_key\":\"$API_KEY\",\"printer_model\":\"$PRINTER_MODEL\"}"
                
                # Try to register (will fail silently if endpoint doesn't exist)
                if curl -s -X POST "$ADMIN_SERVER/api/pis/register" \
                    -H "Content-Type: application/json" \
                    -d "$REGISTER_DATA" \
                    -o /dev/null 2>&1; then
                    echo -e "${GREEN}  ✓ Registered with admin server${NC}"
                else
                    echo -e "${YELLOW}  ⚠ Manual registration required in admin dashboard${NC}"
                    MANUAL_REGISTRATION_NEEDED=true
                fi
            fi
        done
        
        echo ""
        echo -e "${GREEN}All printers configured!${NC}"
        
    else
        # Single printer configuration (backward compatible)
        if command -v uuidgen &> /dev/null; then
            DEVICE_ID=$(uuidgen)
            API_KEY=$(uuidgen)
        else
            DEVICE_ID=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
            API_KEY=$(python3 -c 'import uuid; print(str(uuid.uuid4()))')
        fi
        
        # Get printer model if available
        if [ ${#PRINTER_MODELS[@]} -gt 0 ]; then
            PRINTER_MODEL="${PRINTER_MODELS[0]}"
        else
            PRINTER_MODEL="Unknown"
        fi
        
        cat > /etc/labelberry/client.conf <<EOF
device_id: $DEVICE_ID
api_key: $API_KEY
admin_server: $ADMIN_SERVER
printer_device: ${PRINTER_DEVICES[0]}
printer_model: $PRINTER_MODEL
queue_size: 100
retry_attempts: 3
retry_delay: 5
log_level: INFO
log_file: /var/log/labelberry/client.log
metrics_interval: 60
multi_printer_mode: false
EOF
        
        echo -e "${GREEN}Configuration created${NC}"
        
        # Try to register with admin server
        if [ ! -z "$ADMIN_SERVER" ]; then
            echo -e "${YELLOW}Attempting to register with admin server...${NC}"
            
            # Create registration request
            REGISTER_DATA="{\"id\":\"$DEVICE_ID\",\"friendly_name\":\"$FRIENDLY_NAME\",\"api_key\":\"$API_KEY\",\"printer_model\":\"$PRINTER_MODEL\"}"
            
            # Try to register (will fail silently if endpoint doesn't exist)
            if curl -s -X POST "$ADMIN_SERVER/api/pis/register" \
                -H "Content-Type: application/json" \
                -d "$REGISTER_DATA" \
                -o /dev/null 2>&1; then
                echo -e "${GREEN}✓ Registered with admin server${NC}"
            else
                echo -e "${YELLOW}⚠ Manual registration required in admin dashboard${NC}"
                MANUAL_REGISTRATION_NEEDED=true
            fi
        fi
    fi
fi

echo -e "${YELLOW}[10/11] Creating systemd service...${NC}"

# Check if multi-printer mode
if grep -q "multi_printer_mode: true" /etc/labelberry/client.conf 2>/dev/null; then
    cat > /etc/systemd/system/labelberry-client.service <<EOF
[Unit]
Description=LabelBerry Multi-Printer Client
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="LABELBERRY_MULTI_PRINTER=true"
ExecStart=$INSTALL_DIR/venv/bin/python -m pi_client.app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
else
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
ExecStart=$INSTALL_DIR/venv/bin/python -m pi_client.app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable labelberry-client.service

echo -e "${YELLOW}[11/11] Creating CLI symlink...${NC}"
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
# Display configuration summary
if [ -d "/etc/labelberry/printers" ] && [ "$(ls -A /etc/labelberry/printers)" ]; then
    echo -e "${YELLOW}Register your printer(s) on the admin server dashboard:${NC}"
    echo -e "${YELLOW}You can set friendly names for each printer in the dashboard${NC}"
    echo ""
    for config_file in /etc/labelberry/printers/*.conf; do
        if [ -f "$config_file" ]; then
            DEVICE_ID=$(grep "device_id:" "$config_file" | cut -d' ' -f2)
            API_KEY=$(grep "api_key:" "$config_file" | cut -d' ' -f2)
            DEVICE_PATH=$(grep "device_path:" "$config_file" | cut -d' ' -f2)
            MODEL=$(grep "printer_model:" "$config_file" | cut -d' ' -f2-)
            
            # Extract printer number from filename
            PRINTER_NUM=$(echo "$config_file" | grep -o '[0-9]*' | tail -1)
            PRINTER_NUM=$((PRINTER_NUM + 1))
            
            echo -e "${GREEN}Printer $PRINTER_NUM ($MODEL):${NC}"
            echo -e "  Device ID: ${BLUE}$DEVICE_ID${NC}"
            echo -e "  API Key: ${BLUE}$API_KEY${NC}"
            echo -e "  Device: ${YELLOW}$DEVICE_PATH${NC}"
            echo ""
        fi
    done
else
    echo -e "${YELLOW}Register this Pi on your admin server dashboard:${NC}"
    echo -e "   Device ID: ${BLUE}$(grep device_id /etc/labelberry/client.conf | cut -d' ' -f2)${NC}"
    echo -e "   API Key: ${BLUE}$(grep api_key /etc/labelberry/client.conf | cut -d' ' -f2)${NC}"
    echo ""
    echo -e "${YELLOW}You can set a friendly name in the dashboard${NC}"
fi
echo ""

read -p "Do you want to start the service now? (Y/n): " -n 1 -r </dev/tty
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    systemctl start labelberry-client
    echo -e "${GREEN}Service started!${NC}"
    echo "Check status with: sudo systemctl status labelberry-client"
fi