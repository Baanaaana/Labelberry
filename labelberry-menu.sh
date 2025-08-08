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
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                               ║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}██╗      █████╗ ██████╗ ███████╗██╗     ${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}██║     ██╔══██╗██╔══██╗██╔════╝██║     ${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}██║     ███████║██████╔╝█████╗  ██║     ${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}██║     ██╔══██║██╔══██╗██╔══╝  ██║     ${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}███████╗██║  ██║██████╔╝███████╗███████╗${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}██████╗ ███████╗██████╗ ██████╗ ██╗   ██╗${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}██╔══██╗██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}██████╔╝█████╗  ██████╔╝██████╔╝ ╚████╔╝ ${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}██╔══██╗██╔══╝  ██╔══██╗██╔══██╗  ╚██╔╝  ${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}██████╔╝███████╗██║  ██║██║  ██║   ██║   ${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${PURPLE}╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║                                                               ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
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
        echo -e "${YELLOW}Service Management:${NC}"
        echo -e "${CYAN}1)${NC} View service status"
        echo -e "${CYAN}2)${NC} View logs (live)"
        echo -e "${CYAN}3)${NC} Restart service"
        echo -e "${CYAN}4)${NC} Stop service"
        echo -e "${CYAN}5)${NC} Start service"
        echo ""
        echo -e "${YELLOW}Installation:${NC}"
        echo -e "${CYAN}6)${NC} Update Admin Server (reinstall)"
        echo -e "${CYAN}7)${NC} Uninstall Admin Server"
        echo ""
        echo -e "${YELLOW}Database:${NC}"
        echo -e "${CYAN}8)${NC} Backup database"
        echo -e "${CYAN}9)${NC} View database stats"
        
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
                    echo -e "${YELLOW}Service Status:${NC}"
                    sudo systemctl status labelberry-admin
                    prompt_next_action
                    ;;
                2)
                    clear
                    echo -e "${YELLOW}Viewing logs (press Ctrl+C to exit)...${NC}"
                    sudo journalctl -u labelberry-admin -f
                    prompt_next_action
                    ;;
                3)
                    clear
                    echo -e "${YELLOW}Restarting service...${NC}"
                    sudo systemctl restart labelberry-admin
                    echo -e "${GREEN}Service restarted!${NC}"
                    sleep 2
                    sudo systemctl status labelberry-admin --no-pager
                    prompt_next_action
                    ;;
                4)
                    clear
                    echo -e "${YELLOW}Stopping service...${NC}"
                    sudo systemctl stop labelberry-admin
                    echo -e "${GREEN}Service stopped!${NC}"
                    prompt_next_action
                    ;;
                5)
                    clear
                    echo -e "${YELLOW}Starting service...${NC}"
                    sudo systemctl start labelberry-admin
                    echo -e "${GREEN}Service started!${NC}"
                    sleep 2
                    sudo systemctl status labelberry-admin --no-pager
                    prompt_next_action
                    ;;
                6)
                    clear
                    echo -e "${YELLOW}Updating Admin Server...${NC}"
                    labelberry-server-install
                    prompt_next_action
                    ;;
                7)
                    clear
                    echo -e "${RED}Are you sure you want to uninstall? (y/N)${NC}"
                    read -rsn1 confirm
                    if [[ $confirm == "y" ]] || [[ $confirm == "Y" ]]; then
                        labelberry-server-uninstall
                    fi
                    prompt_next_action
                    ;;
                8)
                    clear
                    echo -e "${YELLOW}Backing up database...${NC}"
                    timestamp=$(date +%Y%m%d_%H%M%S)
                    sudo cp /var/lib/labelberry/db.sqlite /tmp/labelberry-backup-$timestamp.sqlite
                    echo -e "${GREEN}Database backed up to /tmp/labelberry-backup-$timestamp.sqlite${NC}"
                    prompt_next_action
                    ;;
                9)
                    clear
                    echo -e "${YELLOW}Database Statistics:${NC}"
                    echo ""
                    sudo sqlite3 /var/lib/labelberry/db.sqlite <<EOF
.mode column
.headers on
SELECT 'Printers' as Type, COUNT(*) as Count FROM pis
UNION ALL
SELECT 'Print Jobs', COUNT(*) FROM print_jobs
UNION ALL
SELECT 'Error Logs', COUNT(*) FROM error_logs
UNION ALL
SELECT 'Metrics', COUNT(*) FROM metrics;
EOF
                    echo ""
                    echo -e "${YELLOW}Recent Activity:${NC}"
                    sudo sqlite3 /var/lib/labelberry/db.sqlite <<EOF
.mode column
.headers on
SELECT datetime(timestamp) as Time, error_type as Type, message 
FROM error_logs 
WHERE pi_id = '__server__' 
ORDER BY timestamp DESC 
LIMIT 5;
EOF
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