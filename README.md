# LabelBerry 🏷️

A Raspberry Pi-based label printing system for Zebra printers with centralized management.

## Features

- **REST API** for printing ZPL labels from URL or raw content
- **Reliable print confirmation** - API waits for actual print completion (new!)
- **Web Dashboard** for managing all printers from a single interface
- **Real-time monitoring** via WebSocket connections
- **Print queue management** with priority support and automatic retry
- **API key authentication** for secure access
- **Multi-printer support** with broadcast printing capabilities
- **24-hour retry window** for failed print jobs

## Quick Start

### 🎯 Interactive Menu (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-menu.sh | bash
```

Available commands after installation:
- `labelberry` - Main menu
- `labelberry-status` - Service status
- `labelberry-logs` - View logs
- `labelberry-restart` - Restart services

### 🍓 Install on Raspberry Pi

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-pi.sh | sudo bash
```

**Note your Device ID and API Key after installation!**

### 🖥️ Install Admin Server

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-server.sh | sudo bash
```

Access dashboard at: `http://YOUR_SERVER_IP:8080`  
Default login: `admin` / `admin123` (change immediately!)

## API Usage

### Send Print Job

**🎯 New: The API now waits for print completion by default!** This ensures you get confirmation that the label was actually printed, not just sent.

```bash
# Send to admin server (recommended) - waits for print completion
curl -X POST http://admin-server:8080/api/pis/PRINTER_ID/print \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"zpl_raw": "^XA^FO50,50^A0N,50,50^FDHello World^FS^XZ"}'
# Returns success only after label is printed

# Async mode - returns immediately (old behavior)
curl -X POST http://admin-server:8080/api/pis/PRINTER_ID/print \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^A0N,50,50^FDHello World^FS^XZ",
    "wait_for_completion": false
  }'
# Returns immediately with job_id for status polling

# Direct to Pi (legacy) - always immediate return
curl -X POST http://raspberry-pi:8000/print \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"zpl_raw": "^XA^FO50,50^A0N,50,50^FDHello World^FS^XZ"}'
```

### API Response Formats

```json
// Success (default mode - waits for completion)
{
  "success": true,
  "message": "Print job completed successfully",
  "data": {
    "job_id": "abc-123",
    "status": "completed"
  }
}

// Failed print (with wait_for_completion=true)
{
  "detail": "Print job failed: Printer not connected"
}

// Async mode response (with wait_for_completion=false)
{
  "success": true,
  "message": "Print job sent to Pi (async mode)",
  "data": {
    "job_id": "abc-123",
    "status": "sent",
    "note": "Poll /api/jobs/{job_id} to check status"
  }
}
```

### Priority System
Jobs are processed by priority (1-10, higher first). Same priority = FIFO.

## Web Dashboard

### Key Features
- **Printer Management**: Add, edit, and monitor all printers
- **Remote Printing**: Send jobs to any printer from the dashboard
- **Queue Management**: View and manage print queues across all printers
- **Performance Metrics**: Monitor CPU, memory, and job statistics
- **System Logs**: Centralized error and event logging
- **API Documentation**: Interactive API docs at `/api-docs`

### Dashboard Sections
1. **Overview**: Real-time status of all printers
2. **Management Tools**: Quick access to all features
3. **Settings**: Configure base URL, timezone, and account
4. **API Docs**: Full API reference with examples using your actual domain

## CLI Commands

```bash
# Configuration
labelberry config get                           # View all settings
labelberry config set friendly_name "Office"    # Update setting

# Operations
labelberry status                                # Check status
labelberry test-print                           # Send test label
labelberry queue list                           # View queue
labelberry queue clear                          # Clear queue
```

## Configuration Files

### Pi Client (`/etc/labelberry/client.conf`)
- `device_id`: Auto-generated UUID
- `friendly_name`: Human-readable name
- `api_key`: Authentication key
- `admin_server`: URL of admin server
- `printer_device`: USB device path

### Admin Server (`/etc/labelberry/server.conf`)
- `port`: Web interface port (default 8080)
- `database_path`: SQLite database location

## System Requirements

### Raspberry Pi
- Raspberry Pi 3/4/5 or Zero 2 W
- Python 3.9+
- USB port for printer

### Admin Server
- Ubuntu 20.04+ or Debian 11+
- Python 3.9+
- 1GB RAM minimum

### Supported Printers
- All Zebra ZPL-compatible printers
- Tested: ZD220, ZD420, GK420d, ZT230

## Troubleshooting

### Printer Not Detected
```bash
lsusb | grep -i zebra                  # Check USB connection
ls -la /dev/usblp*                     # Check device path
sudo journalctl -u labelberry-client -f # Check service logs
```

### WebSocket Issues
```bash
ping YOUR_ADMIN_SERVER_IP              # Test connectivity
labelberry config get admin_server     # Verify configuration
sudo ufw allow 8080/tcp                # Open firewall port
```

### Service Management
```bash
# Raspberry Pi
sudo systemctl restart labelberry-client
sudo journalctl -u labelberry-client -f

# Admin Server
sudo systemctl restart labelberry-admin
sudo journalctl -u labelberry-admin -f
```

## File Locations

### Raspberry Pi
- `/opt/labelberry/` - Application files
- `/etc/labelberry/client.conf` - Configuration
- `/var/log/labelberry/` - Logs

### Admin Server
- `/opt/labelberry-admin/` - Application files
- `/etc/labelberry/server.conf` - Configuration
- `/var/lib/labelberry/db.sqlite` - Database

## Uninstall

```bash
# Raspberry Pi
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/uninstall-pi.sh | sudo bash

# Admin Server
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/uninstall-server.sh | sudo bash
```

## Development

```bash
# Clone repository
git clone https://github.com/Baanaaana/Labelberry.git
cd LabelBerry

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r pi_client/requirements.txt     # For Pi development
pip install -r admin_server/requirements.txt  # For server development

# Run locally
cd pi_client && python -m uvicorn app.main:app --reload --port 8000
cd admin_server && python -m uvicorn app.main:app --reload --port 8080
```

## Security Best Practices

- Change default credentials immediately
- Use unique API keys for each Pi
- Implement HTTPS with reverse proxy
- Monitor access logs regularly
- Keep dependencies updated

## Support

Issues and feature requests: [GitHub Issues](https://github.com/Baanaaana/Labelberry/issues)

## License

MIT License - see LICENSE file for details

---

Built with ❤️ for Raspberry Pi and Zebra printers