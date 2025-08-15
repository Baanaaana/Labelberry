#!/bin/bash

# ============================================
# LABELBERRY MENU INSTALLER
# Version: 1.0.0
# ============================================
# This script installs the menu system to make it
# available as a command from anywhere

# Color definitions
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${WHITE}        LabelBerry Menu System Installer${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run this script as root/sudo${NC}"
   echo "Run as your regular user: ./install-menu.sh"
   exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MENU_SCRIPT="$SCRIPT_DIR/menu.sh"

# Check if menu.sh exists
if [ ! -f "$MENU_SCRIPT" ]; then
    echo -e "${RED}Error: menu.sh not found in $SCRIPT_DIR${NC}"
    echo "Please ensure menu.sh is in the same directory as this installer."
    exit 1
fi

# Function to add menu sourcing to a shell rc file
add_to_rc_file() {
    local rc_file=$1
    local rc_name=$2
    
    if [ -f "$rc_file" ]; then
        # Check if already installed
        if grep -q "source $MENU_SCRIPT" "$rc_file" 2>/dev/null; then
            echo -e "${YELLOW}✓ Menu system already installed in $rc_name${NC}"
            return 0
        fi
        
        # Backup the rc file
        cp "$rc_file" "${rc_file}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Add source command to rc file
        echo "" >> "$rc_file"
        echo "# LabelBerry Menu System" >> "$rc_file"
        echo "# Installed on $(date)" >> "$rc_file"
        echo "if [ -f \"$MENU_SCRIPT\" ]; then" >> "$rc_file"
        echo "    source $MENU_SCRIPT" >> "$rc_file"
        echo "fi" >> "$rc_file"
        
        echo -e "${GREEN}✓ Menu system installed in $rc_name${NC}"
        return 0
    else
        return 1
    fi
}

# Install for current user
echo -e "${YELLOW}Installing LabelBerry menu system...${NC}"
echo ""

# Detect shell and install accordingly
SHELL_NAME=$(basename "$SHELL")
INSTALLED=false

case "$SHELL_NAME" in
    bash)
        if add_to_rc_file "$HOME/.bashrc" ".bashrc"; then
            INSTALLED=true
        fi
        # Also add to .bash_profile for login shells
        if [ -f "$HOME/.bash_profile" ]; then
            add_to_rc_file "$HOME/.bash_profile" ".bash_profile"
        fi
        ;;
    zsh)
        if add_to_rc_file "$HOME/.zshrc" ".zshrc"; then
            INSTALLED=true
        fi
        ;;
    *)
        echo -e "${YELLOW}Unknown shell: $SHELL_NAME${NC}"
        echo "Attempting to install for bash..."
        if add_to_rc_file "$HOME/.bashrc" ".bashrc"; then
            INSTALLED=true
        fi
        ;;
esac

# Create a system-wide link (optional, requires sudo)
echo ""
echo -e "${YELLOW}Would you like to make the menu command available system-wide?${NC}"
echo -e "${GRAY}This will allow any user to run 'labelberry-menu'${NC}"
echo -n "Install system-wide? (requires sudo) [y/N]: "
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    # Create wrapper script
    WRAPPER_SCRIPT="/tmp/labelberry-menu"
    cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# LabelBerry Menu System Wrapper
if [ -f "$MENU_SCRIPT" ]; then
    source $MENU_SCRIPT
    menu
else
    echo "Error: LabelBerry menu system not found at $MENU_SCRIPT"
    exit 1
fi
EOF
    
    chmod +x "$WRAPPER_SCRIPT"
    
    # Install system-wide
    if sudo mv "$WRAPPER_SCRIPT" /usr/local/bin/labelberry-menu; then
        echo -e "${GREEN}✓ System-wide command 'labelberry-menu' installed${NC}"
    else
        echo -e "${RED}✗ Failed to install system-wide command${NC}"
        rm -f "$WRAPPER_SCRIPT"
    fi
fi

# Make scripts executable
chmod +x "$MENU_SCRIPT"
chmod +x "$SCRIPT_DIR/deploy.sh" 2>/dev/null

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         Installation Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$INSTALLED" = true ]; then
    echo -e "${CYAN}The LabelBerry menu system has been installed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}To activate the menu system:${NC}"
    echo -e "  ${WHITE}Option 1:${NC} Open a new terminal window"
    echo -e "  ${WHITE}Option 2:${NC} Run: source ~/.bashrc"
    echo -e "  ${WHITE}Option 3:${NC} Run: source ~/.zshrc (if using zsh)"
    echo ""
    echo -e "${YELLOW}Once activated, you can use these commands:${NC}"
    echo -e "  ${WHITE}menu${NC} or ${WHITE}m${NC}      - Open the LabelBerry management menu"
    echo -e "  ${WHITE}lb${NC}             - Quick shortcut to open menu"
    echo -e "  ${WHITE}labelberry${NC}     - Alternative menu command"
    echo -e "  ${WHITE}deploy${NC}         - Run the deployment script"
    echo -e "  ${WHITE}logs-nextjs${NC}    - View Next.js logs"
    echo -e "  ${WHITE}logs-backend${NC}   - View FastAPI backend logs"
    echo -e "  ${WHITE}logs-mqtt${NC}      - View MQTT broker logs"
    echo -e "  ${WHITE}status${NC}         - Check PM2 status"
    echo ""
    
    # Offer to source now
    echo -e "${YELLOW}Would you like to activate the menu system now?${NC}"
    echo -n "Activate now? [Y/n]: "
    read -r response
    
    if [[ ! "$response" =~ ^[Nn]$ ]]; then
        source "$MENU_SCRIPT"
        echo ""
        echo -e "${GREEN}✓ Menu system activated!${NC}"
        echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to open the LabelBerry management menu${NC}"
    fi
else
    echo -e "${RED}Installation failed. Please check the error messages above.${NC}"
    exit 1
fi

echo ""
echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}Need help? Check the documentation at:${NC}"
echo -e "${WHITE}https://github.com/Baanaaana/LabelBerry${NC}"
echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"