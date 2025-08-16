#!/bin/bash

# LabelBerry Management Menu Script
# Add this to your .bashrc: source /path/to/labelberry-menu.sh

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Installation functions for Pi
labelberry-pi-install() {
    echo -e "${YELLOW}Installing LabelBerry Pi Client...${NC}"
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-pi.sh | sudo bash
}

labelberry-pi-uninstall() {
    echo -e "${YELLOW}Uninstalling LabelBerry Pi Client...${NC}"
    
    # Stop and disable service
    sudo systemctl stop labelberry-client 2>/dev/null
    sudo systemctl disable labelberry-client 2>/dev/null
    
    # Remove service file
    sudo rm -f /etc/systemd/system/labelberry-client.service
    
    # Remove installation directory
    sudo rm -rf /opt/labelberry-client
    
    # Remove configuration
    sudo rm -rf /etc/labelberry
    
    # Remove CLI symlink
    sudo rm -f /usr/local/bin/labelberry
    
    echo -e "${GREEN}LabelBerry Pi Client uninstalled successfully!${NC}"
}

# Installation functions for Server
labelberry-server-install() {
    echo -e "${YELLOW}Installing LabelBerry Admin Server...${NC}"
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-server.sh | sudo bash
}

labelberry-server-uninstall() {
    echo -e "${YELLOW}Uninstalling LabelBerry Admin Server...${NC}"
    
    # Stop and disable service
    sudo systemctl stop labelberry-admin 2>/dev/null
    sudo systemctl disable labelberry-admin 2>/dev/null
    
    # Remove service file
    sudo rm -f /etc/systemd/system/labelberry-admin.service
    
    # Remove installation directory
    sudo rm -rf /opt/labelberry-admin
    
    # Optionally backup database before removal
    if [ -f "/var/lib/labelberry/db.sqlite" ]; then
        echo -e "${YELLOW}Backing up database to /tmp/labelberry-db-backup.sqlite${NC}"
        sudo cp /var/lib/labelberry/db.sqlite /tmp/labelberry-db-backup.sqlite
    fi
    
    # Remove data directory
    sudo rm -rf /var/lib/labelberry
    
    echo -e "${GREEN}LabelBerry Admin Server uninstalled successfully!${NC}"
    echo -e "${YELLOW}Database backup saved to /tmp/labelberry-db-backup.sqlite${NC}"
}

# Helper function to detect what's installed
detect_installation() {
    if [ -f "/etc/systemd/system/labelberry-client.service" ]; then
        echo "pi"
    elif [ -f "/etc/systemd/system/labelberry-admin.service" ]; then
        echo "server"
    else
        echo "none"
    fi
}

# Function to prompt for next action
prompt_next_action() {
    echo ""
    echo -e "${CYAN}Press any key to return to menu...${NC}"
    read -rsn1
    labelberry
}

# Main menu function
labelberry() {
    clear
    echo ""
    echo ""
    echo -e "  ${BLUE}██╗      █████╗ ██████╗ ███████╗██╗     ${NC}"
    echo -e "  ${BLUE}██║     ██╔══██╗██╔══██╗██╔════╝██║     ${NC}"
    echo -e "  ${BLUE}██║     ███████║██████╔╝█████╗  ██║     ${NC}"
    echo -e "  ${BLUE}██║     ██╔══██║██╔══██╗██╔══╝  ██║     ${NC}"
    echo -e "  ${BLUE}███████╗██║  ██║██████╔╝███████╗███████╗${NC}"
    echo -e "  ${BLUE}╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝${NC}"
    echo -e "  ${BLUE}██████╗ ███████╗██████╗ ██████╗ ██╗   ██╗${NC}"
    echo -e "  ${BLUE}██╔══██╗██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝${NC}"
    echo -e "  ${BLUE}██████╔╝█████╗  ██████╔╝██████╔╝ ╚████╔╝ ${NC}"
    echo -e "  ${BLUE}██╔══██╗██╔══╝  ██╔══██╗██╔══██╗  ╚██╔╝  ${NC}"
    echo -e "  ${BLUE}██████╔╝███████╗██║  ██║██║  ██║   ██║   ${NC}"
    echo -e "  ${BLUE}╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ${NC}"
    echo ""
    echo -e "${WHITE}Management Console${NC}"
    echo ""
    
    # Detect what's installed
    INSTALLED=$(detect_installation)
    
    if [ "$INSTALLED" = "pi" ]; then
        echo -e "${GREEN}● Pi Client Installed${NC}"
        echo ""
        echo -e "${YELLOW}Service Management:${NC}"
        echo -e "${CYAN}1)${NC} View service status"
        echo -e "${CYAN}2)${NC} View logs (live)"
        echo -e "${CYAN}3)${NC} Restart service"
        echo -e "${CYAN}4)${NC} Stop service"
        echo -e "${CYAN}5)${NC} Start service"
        echo ""
        echo -e "${YELLOW}Installation:${NC}"
        echo -e "${CYAN}6)${NC} Update Pi Client (reinstall)"
        echo -e "${CYAN}7)${NC} Uninstall Pi Client"
        echo ""
        echo -e "${YELLOW}Configuration:${NC}"
        echo -e "${CYAN}8)${NC} Edit configuration"
        echo -e "${CYAN}9)${NC} Test print"
        
    elif [ "$INSTALLED" = "server" ]; then
        echo -e "${GREEN}● Admin Server Installed${NC}"
        echo ""
        echo -e "${YELLOW}Backend Service (API):${NC}"
        echo -e "${CYAN}1)${NC} View backend status"
        echo -e "${CYAN}2)${NC} View backend logs (live)"
        echo -e "${CYAN}3)${NC} Restart backend"
        echo ""
        echo -e "${YELLOW}Frontend Service (Next.js):${NC}"
        echo -e "${CYAN}4)${NC} View frontend status (PM2)"
        echo -e "${CYAN}5)${NC} View frontend logs (PM2)"
        echo -e "${CYAN}6)${NC} Restart frontend (PM2)"
        echo ""
        echo -e "${YELLOW}All Services:${NC}"
        echo -e "${CYAN}7)${NC} Restart all services"
        echo -e "${CYAN}8)${NC} Stop all services"
        echo -e "${CYAN}9)${NC} Start all services"
        echo ""
        echo -e "${YELLOW}Installation:${NC}"
        echo -e "${CYAN}10)${NC} Update Admin Server (reinstall)"
        echo -e "${CYAN}11)${NC} Uninstall Admin Server"
        echo ""
        echo -e "${YELLOW}Configuration:${NC}"
        echo -e "${CYAN}12)${NC} Edit .env file (unified configuration)"
        echo -e "${CYAN}13)${NC} View current configuration"
        
    else
        echo -e "${YELLOW}● No LabelBerry installation detected${NC}"
        echo ""
        echo -e "${YELLOW}Installation Options:${NC}"
        echo -e "${CYAN}1)${NC} Install Pi Client"
        echo -e "${CYAN}2)${NC} Install Admin Server"
    fi
    
    echo ""
    echo -e "${CYAN}0)${NC} Exit"
    echo ""
    echo -e "${WHITE}Type 'labelberry' to reopen this menu${NC}"
    echo ""
    read -rsn1 -p "$(echo -e ${WHITE}Enter your choice: ${NC})" choice
    echo  # Add newline after input
    
    case "$INSTALLED" in
        "pi")
            case $choice in
                1)
                    clear
                    echo -e "${YELLOW}Service Status:${NC}"
                    sudo systemctl status labelberry-client
                    prompt_next_action
                    ;;
                2)
                    clear
                    echo -e "${YELLOW}Viewing logs (press Ctrl+C to exit)...${NC}"
                    sudo journalctl -u labelberry-client -f
                    prompt_next_action
                    ;;
                3)
                    clear
                    echo -e "${YELLOW}Restarting service...${NC}"
                    sudo systemctl restart labelberry-client
                    echo -e "${GREEN}Service restarted!${NC}"
                    sleep 2
                    sudo systemctl status labelberry-client --no-pager
                    prompt_next_action
                    ;;
                4)
                    clear
                    echo -e "${YELLOW}Stopping service...${NC}"
                    sudo systemctl stop labelberry-client
                    echo -e "${GREEN}Service stopped!${NC}"
                    prompt_next_action
                    ;;
                5)
                    clear
                    echo -e "${YELLOW}Starting service...${NC}"
                    sudo systemctl start labelberry-client
                    echo -e "${GREEN}Service started!${NC}"
                    sleep 2
                    sudo systemctl status labelberry-client --no-pager
                    prompt_next_action
                    ;;
                6)
                    clear
                    echo -e "${YELLOW}Updating Pi Client...${NC}"
                    labelberry-pi-install
                    prompt_next_action
                    ;;
                7)
                    clear
                    echo -e "${RED}Are you sure you want to uninstall? (y/N)${NC}"
                    read -rsn1 confirm
                    if [[ $confirm == "y" ]] || [[ $confirm == "Y" ]]; then
                        labelberry-pi-uninstall
                    fi
                    prompt_next_action
                    ;;
                8)
                    clear
                    if [ -f "/etc/labelberry/client.conf" ]; then
                        sudo nano /etc/labelberry/client.conf
                    else
                        echo -e "${YELLOW}Checking for printer configs...${NC}"
                        ls -la /etc/labelberry/printers/*.conf 2>/dev/null
                        echo ""
                        echo -e "${CYAN}Enter config file to edit:${NC}"
                        read config_file
                        if [ -f "$config_file" ]; then
                            sudo nano "$config_file"
                        fi
                    fi
                    prompt_next_action
                    ;;
                9)
                    clear
                    echo -e "${YELLOW}Sending test print...${NC}"
                    if command -v labelberry &> /dev/null; then
                        labelberry test-print
                    else
                        echo -e "${RED}CLI not available${NC}"
                    fi
                    prompt_next_action
                    ;;
                0)
                    clear
                    echo -e "${GREEN}Goodbye!${NC}"
                    ;;
                *)
                    echo -e "${RED}Invalid option${NC}"
                    sleep 2
                    labelberry
                    ;;
            esac
            ;;
            
        "server")
            case $choice in
                1)
                    clear
                    echo -e "${YELLOW}Backend Service Status:${NC}"
                    sudo systemctl status labelberry-admin
                    prompt_next_action
                    ;;
                2)
                    clear
                    echo -e "${YELLOW}Viewing backend logs (press Ctrl+C to exit)...${NC}"
                    sudo journalctl -u labelberry-admin -f
                    prompt_next_action
                    ;;
                3)
                    clear
                    echo -e "${YELLOW}Restarting backend service...${NC}"
                    sudo systemctl restart labelberry-admin
                    echo -e "${GREEN}Backend service restarted!${NC}"
                    sleep 2
                    sudo systemctl status labelberry-admin --no-pager
                    prompt_next_action
                    ;;
                4)
                    clear
                    echo -e "${YELLOW}Frontend Service Status (PM2):${NC}"
                    if command -v pm2 &> /dev/null; then
                        pm2 status
                    else
                        echo -e "${RED}PM2 is not installed${NC}"
                    fi
                    prompt_next_action
                    ;;
                5)
                    clear
                    echo -e "${YELLOW}Viewing frontend logs (press Ctrl+C to exit)...${NC}"
                    if command -v pm2 &> /dev/null; then
                        pm2 logs labelberry-nextjs
                    else
                        echo -e "${RED}PM2 is not installed${NC}"
                    fi
                    prompt_next_action
                    ;;
                6)
                    clear
                    echo -e "${YELLOW}Restarting frontend service...${NC}"
                    if command -v pm2 &> /dev/null; then
                        pm2 restart labelberry-nextjs
                        echo -e "${GREEN}Frontend service restarted!${NC}"
                        sleep 2
                        pm2 status
                    else
                        echo -e "${RED}PM2 is not installed${NC}"
                    fi
                    prompt_next_action
                    ;;
                7)
                    clear
                    echo -e "${YELLOW}Restarting all services...${NC}"
                    sudo systemctl restart labelberry-admin
                    if command -v pm2 &> /dev/null; then
                        pm2 restart labelberry-nextjs
                    fi
                    echo -e "${GREEN}All services restarted!${NC}"
                    sleep 2
                    echo -e "${CYAN}Backend Status:${NC}"
                    sudo systemctl status labelberry-admin --no-pager
                    if command -v pm2 &> /dev/null; then
                        echo ""
                        echo -e "${CYAN}Frontend Status:${NC}"
                        pm2 status
                    fi
                    prompt_next_action
                    ;;
                8)
                    clear
                    echo -e "${YELLOW}Stopping all services...${NC}"
                    sudo systemctl stop labelberry-admin
                    if command -v pm2 &> /dev/null; then
                        pm2 stop labelberry-nextjs
                    fi
                    echo -e "${GREEN}All services stopped!${NC}"
                    prompt_next_action
                    ;;
                9)
                    clear
                    echo -e "${YELLOW}Starting all services...${NC}"
                    sudo systemctl start labelberry-admin
                    if command -v pm2 &> /dev/null; then
                        pm2 start labelberry-nextjs 2>/dev/null || pm2 start /opt/labelberry/server/ecosystem.config.js
                    fi
                    echo -e "${GREEN}All services started!${NC}"
                    sleep 2
                    echo -e "${CYAN}Backend Status:${NC}"
                    sudo systemctl status labelberry-admin --no-pager
                    if command -v pm2 &> /dev/null; then
                        echo ""
                        echo -e "${CYAN}Frontend Status:${NC}"
                        pm2 status
                    fi
                    prompt_next_action
                    ;;
                10)
                    clear
                    echo -e "${YELLOW}Updating Admin Server...${NC}"
                    labelberry-server-install
                    prompt_next_action
                    ;;
                11)
                    clear
                    echo -e "${RED}Are you sure you want to uninstall? (y/N)${NC}"
                    read -rsn1 confirm
                    if [[ $confirm == "y" ]] || [[ $confirm == "Y" ]]; then
                        labelberry-server-uninstall
                    fi
                    prompt_next_action
                    ;;
                12)
                    clear
                    echo -e "${YELLOW}Opening unified .env configuration...${NC}"
                    cd /opt/labelberry/server
                    
                    if [ ! -f .env ]; then
                        echo -e "${YELLOW}.env file not found. Creating from example...${NC}"
                        if [ -f .env.example ]; then
                            cp .env.example .env
                            echo -e "${GREEN}Created .env from .env.example${NC}"
                        else
                            echo -e "${CYAN}Creating new .env file...${NC}"
                            cat > .env << 'EOF'
# ==========================================
# LabelBerry Unified Server Configuration
# ==========================================

# Database Configuration
DATABASE_URL=postgresql://user:password@host/database

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=8080
DEBUG=false
ENABLE_DOCS=false
STATIC_VERSION=1.0

# Local mode (disables MQTT for development)
# MQTT settings are managed through the web interface
LABELBERRY_LOCAL_MODE=false

# Next.js Frontend Configuration
# Using relative paths for production (works with reverse proxy)
NEXT_PUBLIC_API_URL=/api
NEXT_PUBLIC_WS_URL=/api
NEXTAUTH_URL=https://yourdomain.com
NEXTAUTH_SECRET=your-secret-key-here
NODE_ENV=production
EOF
                            echo -e "${GREEN}Created new .env file with default template${NC}"
                        fi
                    fi
                    
                    echo -e "${CYAN}Opening .env file in editor...${NC}"
                    echo -e "${WHITE}Current directory: $(pwd)${NC}"
                    ${EDITOR:-nano} .env
                    echo -e "${GREEN}.env file saved${NC}"
                    echo -e "${YELLOW}Restart services for changes to take effect${NC}"
                    prompt_next_action
                    ;;
                13)
                    clear
                    echo -e "${YELLOW}Current Configuration:${NC}"
                    echo ""
                    if [ -f /opt/labelberry/server/.env ]; then
                        echo -e "${CYAN}Reading from /opt/labelberry/server/.env:${NC}"
                        echo ""
                        # Show only non-sensitive values
                        grep -E "^(DATABASE_URL|API_|NEXT_PUBLIC_|NODE_ENV|DEBUG|STATIC_VERSION|LABELBERRY_MQTT_BROKER|LABELBERRY_MQTT_PORT)" /opt/labelberry/server/.env | while IFS= read -r line; do
                            if [[ $line == *"DATABASE_URL"* ]] || [[ $line == *"SECRET"* ]] || [[ $line == *"PASSWORD"* ]]; then
                                key="${line%%=*}"
                                echo -e "${WHITE}$key${NC}=${GRAY}[hidden]${NC}"
                            else
                                echo -e "${WHITE}$line${NC}"
                            fi
                        done
                    else
                        echo -e "${RED}.env file not found at /opt/labelberry/server/.env${NC}"
                    fi
                    echo ""
                    echo -e "${YELLOW}To edit configuration, use option 12${NC}"
                    prompt_next_action
                    ;;
                0)
                    clear
                    echo -e "${GREEN}Goodbye!${NC}"
                    ;;
                *)
                    echo -e "${RED}Invalid option${NC}"
                    sleep 2
                    labelberry
                    ;;
            esac
            ;;
            
        "none")
            case $choice in
                1)
                    clear
                    labelberry-pi-install
                    prompt_next_action
                    ;;
                2)
                    clear
                    labelberry-server-install
                    prompt_next_action
                    ;;
                0)
                    clear
                    echo -e "${GREEN}Goodbye!${NC}"
                    ;;
                *)
                    echo -e "${RED}Invalid option${NC}"
                    sleep 2
                    labelberry
                    ;;
            esac
            ;;
    esac
}

# Alias for quick access
alias lb='labelberry'
alias lblogs='sudo journalctl -u labelberry-* -f'
alias lbstatus='sudo systemctl status labelberry-*'
alias lbrestart='sudo systemctl restart labelberry-*'

# Display info on sourcing
echo -e "${GREEN}LabelBerry Management Menu loaded!${NC}"
echo -e "${WHITE}Commands available:${NC}"
echo -e "  ${CYAN}labelberry${NC} or ${CYAN}lb${NC} - Open management menu"
echo -e "  ${CYAN}lblogs${NC} - View live logs"
echo -e "  ${CYAN}lbstatus${NC} - Check service status"
echo -e "  ${CYAN}lbrestart${NC} - Restart service"
echo ""