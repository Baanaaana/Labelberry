#!/bin/bash

# ============================================
# LABELBERRY MENU SETUP
# ============================================
# Makes the menu command available system-wide

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[1;36m'
NC='\033[0m'

echo -e "${CYAN}Setting up LabelBerry menu command...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This script must be run as root${NC}"
    exit 1
fi

# Check if LabelBerry is installed
if [ ! -d "/opt/labelberry" ]; then
    echo -e "${RED}LabelBerry not found at /opt/labelberry${NC}"
    echo -e "${YELLOW}Please install LabelBerry first${NC}"
    exit 1
fi

# Check if labelberry-menu.sh exists
if [ ! -f "/opt/labelberry/labelberry-menu.sh" ]; then
    echo -e "${YELLOW}labelberry-menu.sh not found, downloading...${NC}"
    curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/labelberry-menu.sh -o /opt/labelberry/labelberry-menu.sh
    chmod +x /opt/labelberry/labelberry-menu.sh
fi

# Add to root's .bashrc if not already there
if ! grep -q "source /opt/labelberry/labelberry-menu.sh" /root/.bashrc 2>/dev/null; then
    echo "" >> /root/.bashrc
    echo "# LabelBerry Management Menu" >> /root/.bashrc
    echo "source /opt/labelberry/labelberry-menu.sh" >> /root/.bashrc
    echo -e "${GREEN}✓ Added labelberry-menu.sh to /root/.bashrc${NC}"
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
            echo -e "${GREEN}✓ Added labelberry-menu.sh to $username's .bashrc${NC}"
        fi
    fi
done

echo -e "${GREEN}✓ Menu installed successfully!${NC}"
echo ""
echo -e "${YELLOW}Run 'source ~/.bashrc' to load the menu in this session${NC}"
echo ""
echo -e "${CYAN}After sourcing, you can use:${NC}"
echo -e "  ${GREEN}labelberry${NC}     - Open the LabelBerry management menu"
echo -e "  ${GREEN}lb${NC}             - Short alias for menu"
echo -e "  ${GREEN}lblogs${NC}         - View live logs"
echo -e "  ${GREEN}lbstatus${NC}       - Check service status"
echo -e "  ${GREEN}lbrestart${NC}      - Restart service"