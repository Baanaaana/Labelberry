#!/bin/bash

# ============================================
# LABELBERRY INSTALLER
# Version: 2.0.0
# ============================================
# Downloads and runs the installation menu locally
# This approach works reliably with curl piping

set -e

# Colors
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${GREEN}           LabelBerry Installation System                ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This installer must be run as root${NC}"
    echo -e "${YELLOW}Please run with sudo:${NC}"
    echo -e "${GREEN}curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install.sh | sudo bash${NC}"
    exit 1
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT
cd $TEMP_DIR

echo -e "${YELLOW}Downloading LabelBerry installation menu...${NC}"

# Download the install menu script
if command -v curl &> /dev/null; then
    curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install-menu.sh -o install-menu.sh || {
        echo -e "${RED}Failed to download installation menu${NC}"
        exit 1
    }
elif command -v wget &> /dev/null; then
    wget -q https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install-menu.sh -O install-menu.sh || {
        echo -e "${RED}Failed to download installation menu${NC}"
        exit 1
    }
else
    echo -e "${RED}Error: Neither curl nor wget is installed${NC}"
    echo "Please install curl or wget and try again:"
    echo "  apt-get update && apt-get install -y curl"
    exit 1
fi

# Make it executable
chmod +x install-menu.sh

# Run the installation menu
echo -e "${GREEN}Starting LabelBerry installation menu...${NC}"
echo ""
bash install-menu.sh

# The cleanup trap will handle temp directory removal
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Installation process completed!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"