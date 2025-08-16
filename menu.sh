#!/bin/bash

# ============================================
# LABELBERRY MENU SYSTEM
# ============================================
# This script can be sourced from .bashrc to provide
# persistent menu access and useful aliases

# Load NVM first so it's available in the menu function
# Use system-wide NVM installation for LabelBerry
export NVM_DIR="/opt/nvm"

# Fallback to user installation if system-wide not found
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        export NVM_DIR="$HOME/.nvm"
    elif [ -s "/root/.nvm/nvm.sh" ] && [ "$EUID" -eq 0 ]; then
        export NVM_DIR="/root/.nvm"
    fi
fi

[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Color definitions for consistent styling
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
MAGENTA='\033[1;35m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_NAME="LabelBerry"
PROJECT_DIR="/opt/labelberry"
NEXTJS_DIR="$PROJECT_DIR/nextjs"
ADMIN_DIR="$PROJECT_DIR/admin_server"
PM2_APP_NAME="labelberry-nextjs"
NODE_VERSION="lts/*"  # Use latest LTS version

# Function to prompt user for next action
prompt_next_action() {
    echo " "
    echo -e "${YELLOW}What would you like to do next?${NC}"
    echo -e "${GREEN}1)${NC} Return to menu"
    echo -e "${GREEN}2)${NC} Exit to CLI"
    echo " "
    read -rsn1 -p "$(echo -e "${WHITE}Enter your choice (1 or 2): ${NC}")" next_choice
    echo  # Add newline after input
    
    case $next_choice in
        1)
            menu
            ;;
        2)
            clear
            echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to reopen the LabelBerry menu.${NC}"
            return
            ;;
        *)
            echo -e "${RED}Invalid option. Please choose 1 or 2.${NC}"
            sleep 1
            prompt_next_action
            ;;
    esac
}

# Function to display section headers
print_section() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
}

# Function to show the menu
menu() {
    clear
    echo " "
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                     ${GREEN}🏷️  LABELBERRY 🏷️${NC}                     ${CYAN}║${NC}"
    echo -e "${CYAN}║          ${WHITE}Label Printing System Management${NC}                ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo " "
    echo -e "${GRAY}Server: $(hostname) | User: $(whoami) | Date: $(date '+%Y-%m-%d %H:%M')${NC}"
    echo " "
    
    print_section "DEPLOYMENT & BUILD"
    echo -e "  ${GREEN}1)${NC} Run full deploy script ${BLUE}[Default - press Enter]${NC}"
    echo -e "  ${GREEN}2)${NC} Git pull latest changes"
    echo -e "  ${GREEN}3)${NC} Build Next.js application"
    echo -e "  ${GREEN}4)${NC} Install/Update dependencies"
    echo " "
    
    print_section "SERVICE MANAGEMENT"
    echo -e "  ${GREEN}5)${NC} Check all services status"
    echo -e "  ${GREEN}6)${NC} Restart Next.js (PM2)"
    echo -e "  ${GREEN}7)${NC} Restart FastAPI backend"
    echo -e "  ${GREEN}8)${NC} Restart MQTT broker"
    echo -e "  ${GREEN}9)${NC} Stop all services"
    echo -e "  ${GREEN}a)${NC} Start all services"
    echo " "
    
    print_section "LOGS & MONITORING"
    echo -e "  ${GREEN}b)${NC} Stream Next.js logs ${YELLOW}(live)${NC}"
    echo -e "  ${GREEN}c)${NC} Stream FastAPI logs ${YELLOW}(live)${NC}"
    echo -e "  ${GREEN}d)${NC} Stream MQTT logs ${YELLOW}(live)${NC}"
    echo -e "  ${GREEN}e)${NC} View last 100 Next.js log lines"
    echo -e "  ${GREEN}f)${NC} View last 100 FastAPI log lines"
    echo -e "  ${GREEN}g)${NC} PM2 monitoring dashboard"
    echo " "
    
    print_section "DATABASE & CONFIGURATION"
    echo -e "  ${GREEN}h)${NC} PostgreSQL console"
    echo -e "  ${GREEN}i)${NC} Edit environment variables"
    echo -e "  ${GREEN}j)${NC} View current configuration"
    echo -e "  ${GREEN}k)${NC} Test printer connection"
    echo " "
    
    print_section "UTILITIES"
    echo -e "  ${GREEN}l)${NC} Go to project folder"
    echo -e "  ${GREEN}m)${NC} Go to Next.js folder"
    echo -e "  ${GREEN}n)${NC} Go to admin server folder"
    echo -e "  ${GREEN}o)${NC} Check Node.js version"
    echo -e "  ${GREEN}p)${NC} System info"
    echo -e "  ${GREEN}q)${NC} Check disk usage"
    echo " "
    
    print_section "EXIT OPTIONS"
    echo -e "  ${GREEN}x)${NC} Exit to CLI ${BLUE}[Or press ESC]${NC}"
    echo " "
    echo -e "${MAGENTA}Tip: Type ${NC}'menu'${MAGENTA} anytime to reopen this menu.${NC}"
    echo " "
    read -rsn1 -p "$(echo -e "${WHITE}Enter your choice: ${NC}")" choice
    echo  # Add newline after input
    
    # Check for ESC key (ASCII 27)
    if [[ $choice == $'\e' ]]; then
        clear
        echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to reopen the LabelBerry menu.${NC}"
        return
    fi
    
    case $choice in
        1|"")
            clear
            echo -e "${YELLOW}Running the full deploy script...${NC}"
            cd $PROJECT_DIR
            if [ -f "./deploy.sh" ]; then
                bash ./deploy.sh
            else
                echo -e "${RED}Deploy script not found at $PROJECT_DIR/deploy.sh${NC}"
            fi
            prompt_next_action
            ;;
        2)
            clear
            echo -e "${YELLOW}Pulling latest changes from git...${NC}"
            cd $PROJECT_DIR
            git pull
            echo -e "${GREEN}Git pull completed!${NC}"
            prompt_next_action
            ;;
        3)
            clear
            echo -e "${YELLOW}Building Next.js application...${NC}"
            cd $NEXTJS_DIR
            npm run build
            echo -e "${GREEN}Build completed!${NC}"
            prompt_next_action
            ;;
        4)
            clear
            echo -e "${YELLOW}Installing/updating dependencies...${NC}"
            cd $NEXTJS_DIR
            npm install
            cd $ADMIN_DIR
            if [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
            fi
            pip install -r requirements_postgres.txt
            echo -e "${GREEN}Dependencies updated!${NC}"
            prompt_next_action
            ;;
        5)
            clear
            echo -e "${YELLOW}Checking all services status...${NC}"
            echo ""
            echo -e "${CYAN}Next.js (PM2):${NC}"
            pm2 status $PM2_APP_NAME
            echo ""
            echo -e "${CYAN}FastAPI Backend:${NC}"
            systemctl status labelberry-admin --no-pager | head -10
            echo ""
            echo -e "${CYAN}MQTT Broker:${NC}"
            systemctl status mosquitto --no-pager | head -10
            echo ""
            echo -e "${CYAN}PostgreSQL:${NC}"
            systemctl status postgresql --no-pager | head -10
            echo -e "${GREEN}Status check completed!${NC}"
            prompt_next_action
            ;;
        6)
            clear
            echo -e "${YELLOW}Restarting Next.js app (${PM2_APP_NAME})...${NC}"
            pm2 restart $PM2_APP_NAME
            echo -e "${GREEN}Next.js app restarted!${NC}"
            prompt_next_action
            ;;
        7)
            clear
            echo -e "${YELLOW}Restarting FastAPI backend...${NC}"
            if [ "$EUID" -eq 0 ]; then
                systemctl restart labelberry-admin
            else
                sudo systemctl restart labelberry-admin
            fi
            echo -e "${GREEN}FastAPI backend restarted!${NC}"
            prompt_next_action
            ;;
        8)
            clear
            echo -e "${YELLOW}Restarting MQTT broker...${NC}"
            if [ "$EUID" -eq 0 ]; then
                systemctl restart mosquitto
            else
                sudo systemctl restart mosquitto
            fi
            echo -e "${GREEN}MQTT broker restarted!${NC}"
            prompt_next_action
            ;;
        9)
            clear
            echo -e "${YELLOW}Stopping all services...${NC}"
            pm2 stop $PM2_APP_NAME
            if [ "$EUID" -eq 0 ]; then
                systemctl stop labelberry-admin
                systemctl stop mosquitto
            else
                sudo systemctl stop labelberry-admin
                sudo systemctl stop mosquitto
            fi
            echo -e "${GREEN}All services stopped!${NC}"
            prompt_next_action
            ;;
        a|A)
            clear
            echo -e "${YELLOW}Starting all services...${NC}"
            if [ "$EUID" -eq 0 ]; then
                systemctl start mosquitto
                systemctl start labelberry-admin
            else
                sudo systemctl start mosquitto
                sudo systemctl start labelberry-admin
            fi
            pm2 start $PM2_APP_NAME
            echo -e "${GREEN}All services started!${NC}"
            prompt_next_action
            ;;
        b|B)
            clear
            echo -e "${YELLOW}Streaming Next.js logs (Press Ctrl+C to stop)...${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            pm2 logs $PM2_APP_NAME
            prompt_next_action
            ;;
        c|C)
            clear
            echo -e "${YELLOW}Streaming FastAPI logs (Press Ctrl+C to stop)...${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            if [ "$EUID" -eq 0 ]; then
                journalctl -u labelberry-admin -f
            else
                sudo journalctl -u labelberry-admin -f
            fi
            prompt_next_action
            ;;
        d|D)
            clear
            echo -e "${YELLOW}Streaming MQTT logs (Press Ctrl+C to stop)...${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            if [ "$EUID" -eq 0 ]; then
                journalctl -u mosquitto -f
            else
                sudo journalctl -u mosquitto -f
            fi
            prompt_next_action
            ;;
        e|E)
            clear
            echo -e "${YELLOW}Showing last 100 Next.js log lines...${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            pm2 logs $PM2_APP_NAME --lines 100 --nostream
            prompt_next_action
            ;;
        f|F)
            clear
            echo -e "${YELLOW}Showing last 100 FastAPI log lines...${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            if [ "$EUID" -eq 0 ]; then
                journalctl -u labelberry-admin -n 100
            else
                sudo journalctl -u labelberry-admin -n 100
            fi
            prompt_next_action
            ;;
        g|G)
            clear
            echo -e "${YELLOW}Opening PM2 monitoring dashboard (Press Q to exit)...${NC}"
            pm2 monit
            prompt_next_action
            ;;
        h|H)
            clear
            echo -e "${YELLOW}Opening PostgreSQL console (type \\q to exit)...${NC}"
            if [ "$EUID" -eq 0 ]; then
                su - postgres -c "psql labelberry"
            else
                sudo -u postgres psql labelberry
            fi
            prompt_next_action
            ;;
        i|I)
            clear
            echo -e "${YELLOW}Opening environment variables for editing...${NC}"
            if [ -f "/etc/labelberry/.env" ]; then
                if [ "$EUID" -eq 0 ]; then
                    nano /etc/labelberry/.env
                else
                    sudo nano /etc/labelberry/.env
                fi
            else
                echo -e "${RED}.env file not found at /etc/labelberry/.env${NC}"
            fi
            prompt_next_action
            ;;
        j|J)
            clear
            echo -e "${YELLOW}Current Configuration:${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            echo -e "${CYAN}Environment Variables:${NC}"
            if [ -f "/etc/labelberry/.env" ]; then
                if [ "$EUID" -eq 0 ]; then
                    grep -v "PASSWORD\|SECRET" /etc/labelberry/.env | head -20
                else
                    sudo grep -v "PASSWORD\|SECRET" /etc/labelberry/.env | head -20
                fi
            fi
            echo ""
            echo -e "${CYAN}Server Config:${NC}"
            if [ -f "/etc/labelberry/server.conf" ]; then
                if [ "$EUID" -eq 0 ]; then
                    cat /etc/labelberry/server.conf | head -20
                else
                    sudo cat /etc/labelberry/server.conf | head -20
                fi
            fi
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            prompt_next_action
            ;;
        k|K)
            clear
            echo -e "${YELLOW}Testing printer connections...${NC}"
            echo "Enter Pi Device ID (or press Enter to test all):"
            read pi_id
            if [ -z "$pi_id" ]; then
                curl -X GET http://localhost:8080/api/pis
            else
                curl -X POST http://localhost:8080/api/pis/$pi_id/test-print
            fi
            echo ""
            echo -e "${GREEN}Test completed!${NC}"
            prompt_next_action
            ;;
        l|L)
            clear
            cd $PROJECT_DIR
            echo -e "${GREEN}You are now in the project directory: $(pwd)${NC}"
            echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to reopen the LabelBerry menu.${NC}"
            ;;
        m|M)
            clear
            cd $NEXTJS_DIR
            echo -e "${GREEN}You are now in the Next.js directory: $(pwd)${NC}"
            echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to reopen the LabelBerry menu.${NC}"
            ;;
        n|N)
            clear
            cd $ADMIN_DIR
            echo -e "${GREEN}You are now in the admin server directory: $(pwd)${NC}"
            echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to reopen the LabelBerry menu.${NC}"
            ;;
        o|O)
            clear
            echo -e "${YELLOW}Node.js and NPM versions:${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            node --version
            npm --version
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            echo -e "${GREEN}Version check completed!${NC}"
            prompt_next_action
            ;;
        p|P)
            clear
            echo -e "${YELLOW}Displaying system information...${NC}"
            if command -v neofetch &> /dev/null; then
                neofetch
            else
                echo -e "${YELLOW}neofetch not installed. Showing basic info:${NC}"
                uname -a
                echo ""
                echo "CPU: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2)"
                echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
                echo "Disk: $(df -h / | awk 'NR==2 {print $2}')"
            fi
            prompt_next_action
            ;;
        q|Q)
            clear
            echo -e "${YELLOW}Disk usage information:${NC}"
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            df -h
            echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
            echo -e "${YELLOW}Project folder size:${NC}"
            du -sh $PROJECT_DIR
            echo -e "${YELLOW}Next.js folder size:${NC}"
            du -sh $NEXTJS_DIR
            echo -e "${YELLOW}Admin server folder size:${NC}"
            du -sh $ADMIN_DIR
            prompt_next_action
            ;;
        x|X)
            clear
            echo -e "${MAGENTA}Type ${NC}'menu'${MAGENTA} to reopen the LabelBerry menu.${NC}"
            echo -e "${GREEN}Goodbye!${NC}"
            ;;
        *)
            clear
            echo -e "${RED}Invalid option. Please choose a valid option.${NC}"
            sleep 2
            menu
            ;;
    esac
}

# Alias for quick access
alias m='menu'
alias lb='menu'
alias labelberry='menu'
alias logs-nextjs='pm2 logs labelberry-nextjs'
alias status='pm2 status'
alias restart-nextjs='pm2 restart labelberry-nextjs'
alias deploy='cd /opt/labelberry && bash deploy.sh'

# Aliases that need sudo (check if running as root)
if [ "$EUID" -eq 0 ]; then
    alias logs-backend='journalctl -u labelberry-admin -f'
    alias logs-mqtt='journalctl -u mosquitto -f'
    alias restart-backend='systemctl restart labelberry-admin'
else
    alias logs-backend='sudo journalctl -u labelberry-admin -f'
    alias logs-mqtt='sudo journalctl -u mosquitto -f'
    alias restart-backend='sudo systemctl restart labelberry-admin'
fi

# Welcome message when sourced
if [ "$EUID" -eq 0 ]; then
    echo -e "${CYAN}Welcome to LabelBerry Server Management ${YELLOW}(Running as root)${NC}"
else
    echo -e "${CYAN}Welcome to LabelBerry Server Management${NC}"
fi
echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}Quick commands:${NC}"
echo -e "  ${WHITE}menu${NC} or ${WHITE}m${NC}      - Open management menu"
echo -e "  ${WHITE}lb${NC}             - Open management menu (shortcut)"
echo -e "  ${WHITE}deploy${NC}         - Run deployment script"
echo -e "  ${WHITE}logs-nextjs${NC}    - Stream Next.js logs"
echo -e "  ${WHITE}logs-backend${NC}   - Stream FastAPI logs"
echo -e "  ${WHITE}logs-mqtt${NC}      - Stream MQTT logs"
echo -e "  ${WHITE}status${NC}         - Check PM2 status"
echo -e "  ${WHITE}restart-nextjs${NC} - Restart Next.js app"
echo -e "  ${WHITE}restart-backend${NC}- Restart FastAPI backend"
echo -e "${GRAY}───────────────────────────────────────────────────────${NC}"
echo " "

# Optionally auto-open menu on login (can be commented out)
# menu