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

# Create system-wide command
cat > /usr/local/bin/labelberry-menu << 'EOF'
#!/bin/bash
cd /opt/labelberry && ./labelberry-menu.sh
EOF

chmod +x /usr/local/bin/labelberry-menu

# Create shorter aliases
ln -sf /usr/local/bin/labelberry-menu /usr/local/bin/menu 2>/dev/null || true
ln -sf /usr/local/bin/labelberry-menu /usr/local/bin/lb 2>/dev/null || true
ln -sf /usr/local/bin/labelberry-menu /usr/local/bin/m 2>/dev/null || true

echo -e "${GREEN}✓ Menu command installed successfully!${NC}"
echo ""
echo -e "${CYAN}You can now use any of these commands from anywhere:${NC}"
echo -e "  ${GREEN}menu${NC}           - Open the LabelBerry management menu"
echo -e "  ${GREEN}m${NC}              - Shortest alias for menu"
echo -e "  ${GREEN}lb${NC}             - Short alias for menu"
echo -e "  ${GREEN}labelberry-menu${NC} - Full command name"
echo ""
echo -e "${YELLOW}Run 'source ~/.bashrc' to make the commands available in this session${NC}"
echo -e "${CYAN}Then try: just type 'menu' and press Enter${NC}"