# Labelberry 🏷️

A Raspberry Pi-based label printing system for Zebra printers with centralized management capabilities.

## Features

- **Print ZPL labels** via REST API from URL or raw ZPL content
- **Centralized management** of multiple Raspberry Pi devices
- **Real-time monitoring** via WebSocket connections
- **Print queue management** with automatic retry
- **Web-based admin interface** for configuration and monitoring
- **CLI tool** for local Pi management
- **Performance metrics** tracking and visualization
- **API key authentication** for secure printing

## Architecture

Labelberry consists of two main components:

### 1. Pi Client
- Runs on each Raspberry Pi connected to a Zebra printer
- Receives print requests via REST API
- Manages local print queue
- Reports status and metrics to admin server

### 2. Admin Server
- Runs on Ubuntu 24.04 server
- Web interface for managing all Raspberry Pis
- Collects metrics and logs
- Pushes configuration updates

## Quick Start

### Install on Raspberry Pi

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-pi.sh | sudo bash
```

### Install Admin Server on Ubuntu

```bash
curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-server.sh | sudo bash
```

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

On the Raspberry Pi:

```bash
# Check status
labelberry status

# View configuration
labelberry config get

# Update configuration
labelberry config set friendly_name "Warehouse Pi 1"

# Send test print
labelberry test-print

# View queue
labelberry queue list

# Clear queue
labelberry queue clear
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
ssl_enabled: false
cors_origins: ["*"]
rate_limit: 100
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
cd Labelberry

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies for Pi client
pip install -r pi-client/requirements.txt

# Install dependencies for admin server
pip install -r admin-server/requirements.txt
```

### Run Locally

**Pi Client:**
```bash
cd pi-client
python -m uvicorn app.main:app --reload --port 8000
```

**Admin Server:**
```bash
cd admin-server
python -m uvicorn app.main:app --reload --port 8080
```

## API Documentation

Once running, access the interactive API documentation:

- Pi Client: http://localhost:8000/docs
- Admin Server: http://localhost:8080/docs

## Troubleshooting

### Printer Not Detected

1. Check USB connection
2. Verify device permissions: `ls -l /dev/usb/`
3. Check service logs: `sudo journalctl -u labelberry-client -f`

### WebSocket Connection Issues

1. Verify network connectivity
2. Check admin server URL in configuration
3. Ensure API key is correct
4. Check firewall settings

### Print Jobs Stuck in Queue

1. Check printer status: `labelberry status`
2. Verify printer is online and ready
3. Clear queue if needed: `labelberry queue clear`
4. Check logs for errors

## Security Considerations

- Always use API key authentication
- Enable SSL/TLS in production
- Restrict CORS origins in production
- Use firewall rules to limit access
- Regularly update dependencies

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