# LabelBerry 🏷️

A Raspberry Pi-based label printing system for Zebra printers with centralized management capabilities.

## Features

- **Print ZPL labels** via REST API from URL or raw ZPL content
- **Web Dashboard** for managing all printers from a single interface
- **Real-time monitoring** via WebSocket connections
- **Print queue management** with automatic retry on failure
- **Remote printing** from admin dashboard to any connected Pi
- **CLI tool** for local Pi management
- **Performance metrics** tracking (CPU, memory, queue status)
- **API key authentication** for secure printing
- **Auto-discovery** of USB printers on multiple device paths
- **Responsive design** works on desktop and mobile devices
- **User authentication** with secure login system
- **Account management** for username and password changes
- **Multi-size label support** with predefined templates (57mm x 32mm, 102mm x 150mm)

## System Requirements

### Raspberry Pi Client
- Raspberry Pi 3/4/5 or Zero 2 W
- Raspberry Pi OS (32-bit or 64-bit)
- Python 3.9 or higher
- 512MB RAM minimum
- USB port for printer connection

### Admin Server
- Ubuntu 20.04/22.04/24.04 or Debian 11/12
- Python 3.9 or higher
- 1GB RAM minimum
- Port 8080 available (configurable)

### Supported Printers
- All Zebra ZPL-compatible printers
- Tested models:
  - Zebra ZD220
  - Zebra ZD420
  - Zebra GK420d
  - Zebra ZT230
- Connection: USB (detected on `/dev/usblp0` or similar)

## Architecture

LabelBerry consists of two main components:

### 1. Pi Client (`pi_client`)
- Runs on each Raspberry Pi connected to a Zebra printer
- Receives print requests via REST API
- Manages local print queue
- Reports status and metrics to admin server

### 2. Admin Server (`admin_server`)
- Runs on Ubuntu 24.04 server
- Web interface for managing all Raspberry Pis
- Collects metrics and logs
- Pushes configuration updates

## Quick Start

### Install on Raspberry Pi

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-pi.sh | sudo bash
```

During installation, you'll be prompted for:
- Friendly name for the Pi
- Admin server URL

After installation, note your:
- **Device ID**: Unique identifier for this Pi
- **API Key**: Authentication key for API access

### Install Admin Server on Ubuntu

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-server.sh | sudo bash
```

After installation, access the dashboard at:
```
http://YOUR_SERVER_IP:8080
```

Default login credentials:
- Username: `admin`
- Password: `admin123`

⚠️ **Important**: Change the default credentials after first login!

### Uninstall

To remove LabelBerry from your system:

**Raspberry Pi:**
```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/uninstall-pi.sh | sudo bash
```

**Ubuntu Server:**
```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/uninstall-server.sh | sudo bash
```

Both uninstall scripts will:
- Backup your configuration and data to `/tmp/labelberry-backup/`
- Remove all LabelBerry files and services
- Optionally remove data directories (with confirmation)
- Display saved credentials for future reinstallation

## Web Dashboard

The admin server includes a full-featured web dashboard for managing all your printers.

### Dashboard Features

#### 🔐 Authentication
- Secure login with username/password
- Session management with remember me option
- Auto-hide default credentials after change
- Logout functionality

#### 📊 Overview
- Real-time printer status monitoring
- Total printers, online count, and job statistics
- Auto-refresh with configurable interval
- WebSocket connectivity indicators

#### 🖨️ Printer Management
- **Register New Printers**: Add Raspberry Pis using their Device ID and API Key
- **View Details**: See configuration, metrics, and current status
- **Remote Control**: Send commands and configuration updates
- **Broadcast Print**: Send same job to multiple printers
- **Search & Filter**: Find printers by name, location, or model

#### 🎯 Test Printing
Send test prints to any connected printer:
- **Label Size Selection**: Choose from 57mm x 32mm or 102mm x 150mm
- **Raw ZPL**: Type or paste ZPL code directly
- **File Upload**: Upload .zpl files from your computer
- **URL**: Provide a URL to a ZPL file
- **Pre-configured Templates**: Use built-in test labels for each size

#### 📈 Metrics & Monitoring
- CPU and memory usage tracking
- Print queue status and size
- Job success/failure rates
- Network connectivity status
- Historical metrics with time range selection
- Error logs with severity filtering

#### ⚙️ Settings
- **Account Management**: Change username and password
- **Timezone Configuration**: Set local timezone for timestamps
- **Auto-refresh Interval**: Configure dashboard update frequency
- **Date Format**: Choose preferred date display format

### Using the Dashboard

1. **Login to Dashboard**
   ```
   http://YOUR_SERVER_IP:8080
   ```
   - Enter username and password
   - Default: `admin` / `admin123`
   - Check "Remember me" to stay logged in

2. **Register a Printer**
   - Click "Register New Pi"
   - Enter Device ID and API Key from Pi installation
   - Add friendly name and optional location/model
   - Click Register

3. **Send Test Print**
   - Click "Test Print" on any printer card
   - Choose label size (57mm x 32mm or 102mm x 150mm)
   - Choose input method (Raw/File/URL)
   - Enter or upload ZPL content
   - Click "Send Print Job"

4. **View Printer Details**
   - Click "Details" on any printer card
   - See configuration, metrics, and logs
   - Monitor real-time performance

5. **Manage Account**
   - Click Settings icon in top-right
   - Change username (minimum 3 characters)
   - Change password (minimum 6 characters)
   - Configure timezone and refresh interval
   - Click "Save Settings"

## API Usage

### Send a Print Job

```bash
curl -X POST http://raspberry-pi:8000/print \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_url": "https://example.com/label.zpl"
  }'
```

Or with raw ZPL:

```bash
curl -X POST http://raspberry-pi:8000/print \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^A0N,50,50^FDHello World^FS^XZ"
  }'
```

### Check Status

```bash
curl http://raspberry-pi:8000/status
```

## CLI Usage

The Raspberry Pi includes a comprehensive CLI tool for local management.

### Available Commands

#### Status & Configuration
```bash
# Check printer and service status
labelberry status

# View all configuration
labelberry config get

# View specific config value
labelberry config get api_key

# Update configuration
labelberry config set friendly_name "Warehouse Pi 1"
labelberry config set printer_device /dev/usblp0
labelberry config set admin_server http://192.168.1.100:8080
```

#### Print Operations
```bash
# Send test print to verify printer connection
labelberry test-print

# View print queue
labelberry queue list

# Clear all queued jobs
labelberry queue clear
```

### CLI Output Examples

**Status Command:**
```
=== LabelBerry Status ===
Device ID: a0973a9f-5d0c-4e6f-81fa-831f851d7b07
Friendly Name: Warehouse Pi 1
WebSocket Connected: True

--- Printer Status ---
Connected: True
Device: /dev/usblp0
Type: USB

--- Queue Status ---
Queue Size: 2/100
Processing: True
Current Job: abc123
Pending Jobs: 1
Failed Jobs: 0
```

## Configuration

### Pi Client (`/etc/labelberry/client.conf`)

```yaml
device_id: auto-generated-uuid
friendly_name: warehouse-pi-1
api_key: your-api-key
admin_server: http://admin.example.com:8080
printer_device: /dev/usb/lp0
queue_size: 100
retry_attempts: 3
retry_delay: 5
log_level: INFO
metrics_interval: 60
```

### Admin Server (`/etc/labelberry/server.conf`)

```yaml
host: 0.0.0.0
port: 8080
database_path: /var/lib/labelberry/db.sqlite
log_level: INFO
cors_origins: ["*"]
rate_limit: 100
session_timeout: 3600
```

## Development

### Prerequisites

- Python 3.9+
- Git
- Virtual environment

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Baanaaana/Labelberry.git
cd LabelBerry

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies for Pi client
pip install -r pi_client/requirements.txt

# Install dependencies for admin server
pip install -r admin_server/requirements.txt
```

### Run Locally

**Pi Client:**
```bash
cd pi_client
python -m uvicorn app.main:app --reload --port 8000
```

**Admin Server:**
```bash
cd admin_server
python -m uvicorn app.main:app --reload --port 8080
```

## API Documentation

Once running, access the interactive API documentation:

- Pi Client: http://localhost:8000/docs
- Admin Server: http://localhost:8080/docs

## Troubleshooting

### Printer Not Detected

1. **Check USB connection**
   ```bash
   lsusb | grep -i zebra
   ls -la /dev/usblp*
   ```

2. **Verify device permissions**
   ```bash
   sudo usermod -a -G lp $USER
   ls -l /dev/usblp0
   ```

3. **Check service logs**
   ```bash
   sudo journalctl -u labelberry-client -f
   ```

4. **Common device paths**
   - Primary: `/dev/usblp0`
   - Alternatives: `/dev/usb/lp0`, `/dev/lp0`

5. **If USB controller crashes**
   ```bash
   sudo reboot  # Resets USB controller
   ```

### WebSocket Connection Issues

1. **Verify network connectivity**
   ```bash
   ping YOUR_ADMIN_SERVER_IP
   curl http://YOUR_ADMIN_SERVER_IP:8080/health
   ```

2. **Check configuration**
   ```bash
   labelberry config get admin_server
   labelberry config get api_key
   ```

3. **Firewall settings**
   ```bash
   # On admin server
   sudo ufw allow 8080/tcp
   ```

### Print Jobs Stuck in Queue

1. **Check printer status**
   ```bash
   labelberry status
   ```

2. **View queue details**
   ```bash
   labelberry queue list
   ```

3. **Clear stuck jobs**
   ```bash
   labelberry queue clear
   ```

4. **Restart service**
   ```bash
   sudo systemctl restart labelberry-client
   ```

### Dashboard Not Loading

1. **Check admin service**
   ```bash
   sudo systemctl status labelberry-admin
   sudo journalctl -u labelberry-admin -f
   ```

2. **Verify nginx is running**
   ```bash
   sudo systemctl status nginx
   ```

3. **Check port availability**
   ```bash
   sudo netstat -tlnp | grep 8080
   ```

## Authentication & Security

### Login System
- **Session-based authentication** protects the admin dashboard
- **Default credentials** shown only until changed
- **Password requirements**: Minimum 6 characters
- **Username requirements**: Minimum 3 characters
- **Session management** with configurable timeout

### Account Management
1. **Change Username**
   - Navigate to Settings (gear icon)
   - Enter new username in Account Settings
   - Enter current password for verification
   - Click "Save Settings"

2. **Change Password**
   - Navigate to Settings (gear icon)
   - Enter current password
   - Enter new password (min 6 characters)
   - Confirm new password
   - Click "Save Settings"

3. **Logout**
   - Click logout icon in top-right corner
   - Returns to login page
   - Session is cleared

### Security Best Practices
- **Change default credentials immediately** after installation
- **Use strong passwords** with mix of characters
- **Unique API keys** for each Raspberry Pi
- **Use HTTPS** with reverse proxy (Nginx/Caddy)
- **Restrict CORS origins** in production
- **Firewall rules** to limit access
- **Regular updates** of dependencies
- **Monitor access logs** for suspicious activity

## Quick Reference

### Service Management
```bash
# Raspberry Pi
sudo systemctl start labelberry-client
sudo systemctl stop labelberry-client
sudo systemctl restart labelberry-client
sudo systemctl status labelberry-client
sudo journalctl -u labelberry-client -f

# Admin Server
sudo systemctl start labelberry-admin
sudo systemctl stop labelberry-admin
sudo systemctl restart labelberry-admin
sudo systemctl status labelberry-admin
sudo journalctl -u labelberry-admin -f
```

### File Locations
```
# Raspberry Pi
/opt/labelberry/                 # Application files
/etc/labelberry/client.conf      # Configuration
/var/lib/labelberry/queue.json   # Queue persistence
/var/log/labelberry/client.log   # Logs

# Admin Server
/opt/labelberry-admin/           # Application files
/etc/labelberry/server.conf      # Configuration
/var/lib/labelberry/db.sqlite    # Database
/var/log/labelberry/server.log   # Logs
```

### Default Ports
- Pi Client API: `8000`
- Admin Server: `8080`
- Dashboard: `http://SERVER_IP:8080`
- API Docs: `http://SERVER_IP:8080/docs`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and feature requests, please use the GitHub issue tracker:
https://github.com/Baanaaana/Labelberry/issues

## Acknowledgments

- FastAPI for the excellent web framework
- The Raspberry Pi Foundation
- Zebra Technologies for printer documentation