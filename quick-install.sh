#!/bin/bash

# Quick installer that downloads and runs the install script locally
# This avoids the piping issue

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}LabelBerry Quick Installer${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This installer must be run as root${NC}"
    echo -e "${YELLOW}Please run: sudo bash $0${NC}"
    exit 1
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

echo -e "${YELLOW}Downloading LabelBerry installer...${NC}"

# Download the install script
if command -v curl &> /dev/null; then
    curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install.sh -o install.sh
elif command -v wget &> /dev/null; then
    wget -q https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install.sh -O install.sh
else
    echo -e "${RED}Error: Neither curl nor wget is installed${NC}"
    exit 1
fi

# Make it executable
chmod +x install.sh

# Run it
echo -e "${GREEN}Starting LabelBerry installer...${NC}"
echo ""
bash install.sh

# Cleanup
cd /
rm -rf $TEMP_DIR

echo -e "${GREEN}Installation process completed!${NC}"