#!/bin/bash

# ============================================
# LABELBERRY UPDATE & DEPLOYMENT SCRIPT
# Version: 2.0.0
# Updated: 2025-08-16
# ============================================
# Purpose: Update existing LabelBerry installations
# For new installations, use ./install.sh instead
# ============================================
# Features:
# - Git pull latest changes
# - Rebuild backend and frontend
# - Restart all services
# - Zero-downtime deployment
# ============================================

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

# Check if this is an existing installation
check_installation() {
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
        echo -e "${RED}ERROR: LabelBerry is not installed${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}This script is for updating existing installations only.${NC}"
        echo -e "${YELLOW}To install LabelBerry for the first time, run:${NC}"
        echo ""
        echo -e "${WHITE}curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install.sh | sudo bash${NC}"
        echo ""
        exit 1
    fi
    
    # Check if essential components exist
    if [ ! -d "$ADMIN_DIR" ] || [ ! -d "$NEXTJS_DIR" ]; then
        echo -e "${RED}ERROR: Installation appears to be incomplete${NC}"
        echo -e "${YELLOW}Missing essential directories. Please run the installer:${NC}"
        echo ""
        echo -e "${WHITE}curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install.sh | sudo bash${NC}"
        echo ""
        exit 1
    fi
}

# Function to run the full deployment
run_full_deploy() {
    echo -e "${CYAN}Starting LabelBerry update...${NC}"
    echo ""
    
    # Check installation first
    check_installation
    
    # Navigate to project directory
    cd $PROJECT_DIR || exit 1
    
    # Check current branch
    current_branch=$(git branch --show-current)
    echo -e "${YELLOW}Current branch:${NC} $current_branch"
    echo ""
    
    # Git pull with status
    echo -e "${YELLOW}1. Pulling latest changes...${NC}"
    echo "🔄 Resetting any local changes..."
    git reset --hard HEAD
    git clean -fd
    
    echo "🔄 Fetching latest changes..."
    git fetch origin
    
    # Get current commit hash before update
    CURRENT_COMMIT=$(git rev-parse HEAD)
    TARGET_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    TARGET_COMMIT=$(git rev-parse origin/$TARGET_BRANCH)
    
    echo "📊 Deployment Summary:"
    echo "  Current commit: ${CURRENT_COMMIT:0:7}"
    echo "  Target commit:  ${TARGET_COMMIT:0:7}"
    echo "  Branch: $TARGET_BRANCH"
    
    # Show what files will be changed if there are differences
    if [ "$CURRENT_COMMIT" != "$TARGET_COMMIT" ]; then
        echo ""
        echo "📝 Files that will be updated:"
        git diff --name-status $CURRENT_COMMIT $TARGET_COMMIT | while read status file; do
            case $status in
                A) echo "  ✅ Added:    $file" ;;
                M) echo "  📝 Modified: $file" ;;
                D) echo "  ❌ Deleted:  $file" ;;
                R*) echo "  🔄 Renamed:  $file" ;;
                *) echo "  📄 Changed:  $file" ;;
            esac
        done
        echo ""
        
        # Show commit messages for new commits
        echo "📋 New commits being deployed:"
        git log --oneline --no-merges $CURRENT_COMMIT..$TARGET_COMMIT | head -10 | while read line; do
            echo "  • $line"
        done
        
        if [ $(git rev-list --count $CURRENT_COMMIT..$TARGET_COMMIT) -gt 10 ]; then
            echo "  ... and $(( $(git rev-list --count $CURRENT_COMMIT..$TARGET_COMMIT) - 10 )) more commits"
        fi
        echo ""
    else
        echo "  ℹ️  No changes to deploy - already up to date"
        echo ""
    fi
    
    echo "🔄 Applying changes..."
    git reset --hard origin/$TARGET_BRANCH
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to pull from GitHub${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Git pull successful${NC}"
    echo ""
    
    # Check Node version
    echo -e "${YELLOW}2. Setting up Node.js environment...${NC}"
    
    # Check if NVM is installed, if not install it
    # Use system-wide NVM installation for consistency with installer
    export NVM_DIR="/opt/nvm"
    
    if [ ! -s "$NVM_DIR/nvm.sh" ] && [ ! -s "/usr/local/opt/nvm/nvm.sh" ]; then
        echo -e "${YELLOW}NVM not found. Installing NVM...${NC}"
        
        # Create NVM directory
        mkdir -p $NVM_DIR
        
        # Download and install NVM (latest version) to /opt/nvm
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | NVM_DIR=$NVM_DIR bash
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ NVM installed successfully${NC}"
            
            # Load NVM for current session
            [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
            [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
        else
            echo -e "${RED}✗ Failed to install NVM${NC}"
            echo "Please install NVM manually and try again"
            exit 1
        fi
    fi
    
    # Load NVM
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
    elif [ -s "/usr/local/opt/nvm/nvm.sh" ]; then
        # macOS with Homebrew
        \. "/usr/local/opt/nvm/nvm.sh"
        [ -s "/usr/local/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/usr/local/opt/nvm/etc/bash_completion.d/nvm"
    fi
    
    # Check if NVM is now available
    if command -v nvm &> /dev/null; then
        # Check if Node version is installed, if not install it
        if ! nvm ls $NODE_VERSION &> /dev/null || [ -z "$(nvm ls $NODE_VERSION 2>/dev/null | grep -v 'N/A')" ]; then
            echo -e "${YELLOW}Installing Node.js $NODE_VERSION...${NC}"
            nvm install $NODE_VERSION
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ Node.js $NODE_VERSION installed successfully${NC}"
                nvm alias default $NODE_VERSION
                echo -e "${GREEN}✓ Set Node.js $NODE_VERSION as default${NC}"
            else
                echo -e "${RED}✗ Failed to install Node.js $NODE_VERSION${NC}"
                exit 1
            fi
        fi
        
        # Use the Node version
        nvm use $NODE_VERSION
        echo -e "${GREEN}✓ Using Node.js $(node --version) via NVM${NC}"
        
        # Verify npm is available
        if ! command -v npm &> /dev/null; then
            echo -e "${RED}✗ npm not found after Node.js installation${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ npm $(npm --version) is available${NC}"
        
        # Update npm to latest version
        echo -e "${YELLOW}Updating npm to latest version...${NC}"
        npm install -g npm@latest
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ npm updated to $(npm --version)${NC}"
        else
            echo -e "${YELLOW}Warning: Could not update npm, continuing with current version${NC}"
        fi
        
    elif command -v node &> /dev/null; then
        echo -e "${GREEN}✓ Using system Node.js $(node --version)${NC}"
    else
        echo -e "${RED}✗ Failed to set up Node.js environment${NC}"
        echo "Please install Node.js manually and try again"
        exit 1
    fi
    echo ""
    
    # Install Python dependencies for admin server
    echo -e "${YELLOW}3. Installing Python dependencies...${NC}"
    cd $ADMIN_DIR
    
    # Activate virtual environment if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    # Install requirements
    if [ -f "requirements_postgres.txt" ]; then
        pip install -r requirements_postgres.txt
        echo -e "${GREEN}✓ Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}Warning: requirements_postgres.txt not found${NC}"
    fi
    echo ""
    
    # Install Next.js dependencies
    echo -e "${YELLOW}4. Installing Next.js dependencies...${NC}"
    cd $NEXTJS_DIR
    
    npm ci
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${YELLOW}npm ci failed, trying npm install...${NC}"
        npm install
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Dependencies installed${NC}"
        else
            echo -e "${RED}✗ Failed to install dependencies${NC}"
            exit 1
        fi
    fi
    echo ""
    
    # Build the application
    echo -e "${YELLOW}5. Building Next.js application...${NC}"
    export NODE_OPTIONS="--max_old_space_size=2048"
    export NEXT_TELEMETRY_DISABLED=1
    npm run build
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Build successful${NC}"
    else
        echo -e "${RED}✗ Build failed${NC}"
        echo "If the build was killed due to memory issues, try:"
        echo "  - Increasing NODE_OPTIONS --max_old_space_size value"
        echo "  - Building locally and deploying the .next folder"
        echo "  - Upgrading server RAM"
        exit 1
    fi
    echo ""
    
    # Check and install PM2 if needed
    echo -e "${YELLOW}6. Checking PM2...${NC}"
    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}PM2 not found. Installing PM2 globally...${NC}"
        npm install -g pm2
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ PM2 installed successfully${NC}"
        else
            echo -e "${RED}✗ Failed to install PM2${NC}"
            echo "Try manually: sudo npm install -g pm2"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ PM2 is installed ($(pm2 --version))${NC}"
    fi
    echo ""
    
    # Deploy with PM2
    echo -e "${YELLOW}7. Deploying Next.js with PM2...${NC}"
    
    # Create ecosystem config if it doesn't exist
    if [ ! -f "ecosystem.config.js" ]; then
        cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'labelberry-nextjs',
    script: 'npm',
    args: 'start',
    cwd: '/opt/labelberry/nextjs',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    max_memory_restart: '500M',
    error_file: '/var/log/labelberry/nextjs-error.log',
    out_file: '/var/log/labelberry/nextjs-out.log',
    merge_logs: true,
    time: true
  }]
}
EOF
        echo -e "${GREEN}✓ Created PM2 ecosystem config${NC}"
    fi
    
    if pm2 list | grep -q "$PM2_APP_NAME"; then
        echo "Reloading application with PM2 (zero downtime)..."
        pm2 reload ecosystem.config.js
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Application reloaded${NC}"
        else
            echo -e "${RED}✗ Failed to reload application${NC}"
            exit 1
        fi
    else
        echo "Starting application with PM2..."
        pm2 start ecosystem.config.js
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Application started${NC}"
        else
            echo -e "${RED}✗ Failed to start application${NC}"
            exit 1
        fi
    fi
    
    # Save PM2 configuration
    pm2 save
    echo -e "${GREEN}✓ PM2 configuration saved${NC}"
    
    # Install PM2 log rotation if not installed
    if ! pm2 list | grep -q "pm2-logrotate"; then
        echo -e "${YELLOW}Installing PM2 log rotation...${NC}"
        NODE_NO_WARNINGS=1 pm2 install pm2-logrotate
        pm2 set pm2-logrotate:retain 7  # Keep logs for 7 days
        pm2 set pm2-logrotate:compress true  # Compress rotated logs
        pm2 set pm2-logrotate:max_size 50M  # Rotate when log reaches 50MB
        echo -e "${GREEN}✓ PM2 log rotation configured${NC}"
    fi
    
    # Setup PM2 startup script
    echo -e "${YELLOW}Setting up PM2 to start on system boot...${NC}"
    
    # Detect the init system and generate startup script
    PM2_STARTUP=$(pm2 startup systemd -u $USER --hp $HOME 2>&1 | grep "sudo")
    
    if [ ! -z "$PM2_STARTUP" ]; then
        echo -e "${YELLOW}To enable auto-start on boot, run this command:${NC}"
        echo -e "${CYAN}$PM2_STARTUP${NC}"
        echo ""
        echo -e "${YELLOW}Do you want to run this command now? (requires sudo) [y/N]:${NC}"
        read -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            eval $PM2_STARTUP
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✓ PM2 startup script installed - app will auto-start on reboot${NC}"
            else
                echo -e "${YELLOW}⚠ Could not install startup script automatically${NC}"
                echo -e "${YELLOW}Please run the command manually with sudo privileges${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ Skipped startup script installation${NC}"
            echo -e "${YELLOW}The app will NOT auto-start on reboot until you run:${NC}"
            echo -e "${CYAN}$PM2_STARTUP${NC}"
        fi
    else
        # Check if startup is already configured
        if systemctl is-enabled pm2-$USER &>/dev/null || systemctl is-enabled pm2-root &>/dev/null; then
            echo -e "${GREEN}✓ PM2 startup already configured - app will auto-start on reboot${NC}"
        else
            echo -e "${YELLOW}⚠ Could not setup PM2 startup automatically${NC}"
            echo -e "${YELLOW}Run 'pm2 startup' and follow the instructions${NC}"
        fi
    fi
    echo ""
    
    # Restart FastAPI backend
    echo -e "${YELLOW}8. Restarting FastAPI backend...${NC}"
    if systemctl is-active --quiet labelberry-admin; then
        sudo systemctl restart labelberry-admin
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ FastAPI backend restarted${NC}"
        else
            echo -e "${YELLOW}⚠ Could not restart backend service${NC}"
        fi
    else
        echo -e "${YELLOW}Backend service not running - starting it...${NC}"
        sudo systemctl start labelberry-admin
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ FastAPI backend started${NC}"
        else
            echo -e "${YELLOW}⚠ Could not start backend service${NC}"
        fi
    fi
    echo ""
    
    # Check MQTT broker
    echo -e "${YELLOW}9. Checking MQTT broker...${NC}"
    if systemctl is-active --quiet mosquitto; then
        echo -e "${GREEN}✓ MQTT broker is running${NC}"
    else
        echo -e "${YELLOW}⚠ MQTT broker is not running${NC}"
        echo "  Try: sudo systemctl start mosquitto"
    fi
    echo ""
    
    # Check application health
    echo -e "${YELLOW}10. Verifying application health...${NC}"
    echo "Waiting 5 seconds for application to initialize..."
    sleep 5
    
    # Check if the Next.js application is responding
    if curl -f -s http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}✅ Next.js application is responding on port 3000${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: Next.js application may not be responding on port 3000${NC}"
        echo "Check PM2 logs: pm2 logs $PM2_APP_NAME"
    fi
    
    # Check if the FastAPI backend is responding
    if curl -f -s http://localhost:8080/health > /dev/null; then
        echo -e "${GREEN}✅ FastAPI backend is responding on port 8080${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: FastAPI backend may not be responding on port 8080${NC}"
        echo "Check logs: sudo journalctl -u labelberry-admin -f"
    fi
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ UPDATE SUCCESSFUL!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${CYAN}System Status:${NC}"
    pm2 status $PM2_APP_NAME
    echo ""
    echo -e "${CYAN}Access Points:${NC}"
    echo "  📱 Web Interface:  http://$(hostname -I | awk '{print $1}'):3000"
    echo "  🔌 API Endpoint:   http://$(hostname -I | awk '{print $1}'):8080"
    echo "  🔊 MQTT Broker:    $(hostname -I | awk '{print $1}'):1883"
    echo ""
    echo -e "${MAGENTA}Useful commands:${NC}"
    echo "  pm2 logs $PM2_APP_NAME       # View Next.js logs"
    echo "  pm2 monit                    # Real-time monitoring"
    echo "  pm2 restart $PM2_APP_NAME    # Restart Next.js"
    echo "  sudo journalctl -u labelberry-admin -f  # View backend logs"
    echo ""
    echo -e "${GREEN}🎉 LabelBerry update completed successfully!${NC}"
    echo ""
}

# Main execution
# Check if we're in the project root or nextjs directory
if [ -f "nextjs/package.json" ]; then
    # We're in the project root, that's good
    echo -e "${GREEN}Running from project root${NC}"
elif [ -f "package.json" ] && [ -f "../deploy.sh" ]; then
    # We're in the nextjs directory, go up one level
    cd ..
    echo -e "${YELLOW}Switching to project root${NC}"
elif [ ! -f "$NEXTJS_DIR/package.json" ]; then
    echo -e "${RED}Error: Cannot find Next.js project at $NEXTJS_DIR${NC}"
    echo "Current directory: $(pwd)"
    echo "Please run this script from the project root or ensure the project is at $PROJECT_DIR"
    exit 1
fi

# Run the deployment
run_full_deploy "$@"