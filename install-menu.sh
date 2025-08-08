#!/bin/bash

# LabelBerry Menu Installation Script
# Install with: curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-menu.sh | bash

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
MENU_URL="https://raw.githubusercontent.com/Baanaaana/Labelberry/main/labelberry-menu.sh"
INSTALL_DIR="$HOME/.labelberry"
MENU_FILE="$INSTALL_DIR/labelberry-menu.sh"
BASHRC="$HOME/.bashrc"
ZSHRC="$HOME/.zshrc"

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   LabelBerry Menu Installer v1.0.0     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"

# Download the menu script
echo -e "${YELLOW}Downloading LabelBerry menu...${NC}"
if curl -fsSL "$MENU_URL" -o "$MENU_FILE"; then
    echo -e "${GREEN}✓ Menu downloaded successfully${NC}"
else
    echo -e "${RED}✗ Failed to download menu script${NC}"
    exit 1
fi

# Make it executable
chmod +x "$MENU_FILE"

# Function to add source line to shell config
add_to_shell_config() {
    local config_file="$1"
    local source_line="source $MENU_FILE"
    
    if [ -f "$config_file" ]; then
        # Check if already added
        if grep -q "labelberry-menu.sh" "$config_file"; then
            echo -e "${YELLOW}  Already configured in $(basename $config_file)${NC}"
        else
            echo "" >> "$config_file"
            echo "# LabelBerry Menu" >> "$config_file"
            echo "$source_line" >> "$config_file"
            echo -e "${GREEN}  ✓ Added to $(basename $config_file)${NC}"
        fi
    fi
}

# Add to shell configurations
echo -e "${YELLOW}Configuring shell environments...${NC}"

# Add to bash
add_to_shell_config "$BASHRC"

# Add to zsh if it exists
if [ -f "$ZSHRC" ]; then
    add_to_shell_config "$ZSHRC"
fi

# Create uninstall script
echo -e "${YELLOW}Creating uninstall script...${NC}"
cat > "$INSTALL_DIR/uninstall-menu.sh" << 'EOF'
#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Uninstalling LabelBerry Menu...${NC}"

# Remove from bashrc
if [ -f "$HOME/.bashrc" ]; then
    sed -i '/# LabelBerry Menu/,+1d' "$HOME/.bashrc"
    echo -e "${GREEN}✓ Removed from .bashrc${NC}"
fi

# Remove from zshrc
if [ -f "$HOME/.zshrc" ]; then
    sed -i '/# LabelBerry Menu/,+1d' "$HOME/.zshrc"
    echo -e "${GREEN}✓ Removed from .zshrc${NC}"
fi

# Remove installation directory
rm -rf "$HOME/.labelberry"
echo -e "${GREEN}✓ Removed LabelBerry menu files${NC}"

echo -e "${GREEN}LabelBerry Menu uninstalled successfully!${NC}"
echo -e "${YELLOW}Please restart your terminal or run: source ~/.bashrc${NC}"
EOF

chmod +x "$INSTALL_DIR/uninstall-menu.sh"

# Show available commands
echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         LabelBerry Menu Installed Successfully!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}Available Commands:${NC}"
echo -e "  ${WHITE}labelberry${NC}              - Show main menu"
echo -e "  ${WHITE}labelberry-status${NC}       - Show service status"
echo -e "  ${WHITE}labelberry-logs${NC}         - View service logs"
echo -e "  ${WHITE}labelberry-restart${NC}      - Restart services"
echo
echo -e "${CYAN}Installation Commands:${NC}"
echo -e "  ${WHITE}labelberry-pi-install${NC}   - Install Pi client"
echo -e "  ${WHITE}labelberry-server-install${NC} - Install admin server"
echo
echo -e "${CYAN}Development Commands:${NC}"
echo -e "  ${WHITE}labelberry-dev${NC}          - Development environment"
echo -e "  ${WHITE}labelberry-update${NC}       - Update from Git"
echo
echo -e "${YELLOW}To uninstall the menu:${NC}"
echo -e "  ${WHITE}$INSTALL_DIR/uninstall-menu.sh${NC}"
echo
echo -e "${GREEN}Please restart your terminal or run:${NC}"
echo -e "  ${WHITE}source ~/.bashrc${NC}"
echo