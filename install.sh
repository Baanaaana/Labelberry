#!/bin/bash

# ============================================
# LABELBERRY MASTER INSTALLER
# Version: 1.0.0
# ============================================
# Single entry point for all LabelBerry installations
# Supports both server and Pi client installations

set -e

# Color definitions
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ASCII Art Header
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}║${GREEN}     _          _         _ ____                          ${CYAN}║${NC}"
echo -e "${CYAN}║${GREEN}    | |    __ _| |__   ___| | __ )  ___ _ __ _ __ _   _  ${CYAN}║${NC}"
echo -e "${CYAN}║${GREEN}    | |   / _\` | '_ \ / _ \ |  _ \ / _ \ '__| '__| | | | ${CYAN}║${NC}"
echo -e "${CYAN}║${GREEN}    | |__| (_| | |_) |  __/ | |_) |  __/ |  | |  | |_| | ${CYAN}║${NC}"
echo -e "${CYAN}║${GREEN}    |_____\__,_|_.__/ \___|_|____/ \___|_|  |_|   \__, | ${CYAN}║${NC}"
echo -e "${CYAN}║${GREEN}                                                   |___/  ${CYAN}║${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}║${WHITE}           Label Printing System Installer               ${CYAN}║${NC}"
echo -e "${CYAN}║                                                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This installer must be run as root${NC}"
    echo -e "${YELLOW}Please run: sudo bash install.sh${NC}"
    exit 1
fi

# Function to detect system type
detect_system() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    # Check if running on Raspberry Pi
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
        IS_PI=true
    else
        IS_PI=false
    fi
}

# Detect system
detect_system

echo -e "${CYAN}System Information:${NC}"
echo -e "  OS: ${WHITE}$OS${NC}"
echo -e "  Version: ${WHITE}$VER${NC}"
if [ "$IS_PI" = true ]; then
    echo -e "  Device: ${GREEN}Raspberry Pi detected${NC}"
fi
echo ""

# Installation type selection
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}What would you like to install?${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}1)${NC} LabelBerry Server ${WHITE}(Admin Server + Web Interface)${NC}"
echo -e "   • FastAPI backend with PostgreSQL"
echo -e "   • Next.js web interface"  
echo -e "   • MQTT broker for device communication"
echo -e "   • For Ubuntu/Debian servers"
echo ""
echo -e "${GREEN}2)${NC} LabelBerry Pi Client ${WHITE}(Printer Controller)${NC}"
echo -e "   • Connects to Zebra printers"
echo -e "   • Receives print jobs from server"
echo -e "   • For Raspberry Pi devices"
echo ""
echo -e "${GREEN}3)${NC} Exit"
echo ""

# Get user choice
while true; do
    read -p "$(echo -e ${WHITE}Enter your choice [1-3]: ${NC})" choice
    case $choice in
        1)
            echo ""
            echo -e "${GREEN}Starting LabelBerry Server installation...${NC}"
            echo ""
            
            # Check if this is appropriate system for server
            if [ "$IS_PI" = true ]; then
                echo -e "${YELLOW}Warning: You're installing the server on a Raspberry Pi${NC}"
                echo -e "${YELLOW}The server is designed for more powerful systems${NC}"
                read -p "Do you want to continue? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo -e "${RED}Installation cancelled${NC}"
                    exit 1
                fi
            fi
            
            # Download and run server installer
            echo -e "${CYAN}Downloading server installer...${NC}"
            if command -v curl &> /dev/null; then
                curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install/install-server.sh -o /tmp/install-server.sh
            elif command -v wget &> /dev/null; then
                wget -q https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install/install-server.sh -O /tmp/install-server.sh
            else
                echo -e "${RED}Error: Neither curl nor wget is installed${NC}"
                echo "Please install curl or wget and try again"
                exit 1
            fi
            
            if [ -f /tmp/install-server.sh ]; then
                chmod +x /tmp/install-server.sh
                bash /tmp/install-server.sh
                rm -f /tmp/install-server.sh
            else
                echo -e "${RED}Failed to download server installer${NC}"
                exit 1
            fi
            break
            ;;
            
        2)
            echo ""
            echo -e "${GREEN}Starting LabelBerry Pi Client installation...${NC}"
            echo ""
            
            # Check if this is appropriate system for Pi client
            if [ "$IS_PI" = false ]; then
                echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
                echo -e "${YELLOW}The Pi client is designed for Raspberry Pi devices${NC}"
                read -p "Do you want to continue anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo -e "${RED}Installation cancelled${NC}"
                    exit 1
                fi
            fi
            
            # Download and run Pi client installer
            echo -e "${CYAN}Downloading Pi client installer...${NC}"
            if command -v curl &> /dev/null; then
                curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install/install-pi.sh -o /tmp/install-pi.sh
            elif command -v wget &> /dev/null; then
                wget -q https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install/install-pi.sh -O /tmp/install-pi.sh
            else
                echo -e "${RED}Error: Neither curl nor wget is installed${NC}"
                echo "Please install curl or wget and try again"
                exit 1
            fi
            
            if [ -f /tmp/install-pi.sh ]; then
                chmod +x /tmp/install-pi.sh
                bash /tmp/install-pi.sh
                rm -f /tmp/install-pi.sh
            else
                echo -e "${RED}Failed to download Pi client installer${NC}"
                exit 1
            fi
            break
            ;;
            
        3)
            echo -e "${YELLOW}Installation cancelled${NC}"
            exit 0
            ;;
            
        *)
            echo -e "${RED}Invalid option. Please choose 1, 2, or 3${NC}"
            ;;
    esac
done

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Installation process completed!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}For documentation and support:${NC}"
echo -e "${WHITE}https://github.com/Baanaaana/LabelBerry${NC}"
echo ""