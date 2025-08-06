# LabelBerry Project Context

## Project Overview
LabelBerry is a Raspberry Pi-based label printing system for Zebra printers with centralized management capabilities. The system consists of multiple Raspberry Pi clients that receive print requests via API and a central Ubuntu admin server for configuration and monitoring.

## Architecture

### Components
1. **Raspberry Pi Clients** (`/pi_client`)
   - FastAPI application running on each Raspberry Pi
   - Connects to Zebra printers via USB
   - Receives print requests with ZPL (either URL or raw)
   - Maintains WebSocket connection to admin server
   - Local CLI for configuration

2. **Admin Server** (`/admin_server`)
   - Runs on Ubuntu 24.04 server (separate machine)
   - Web interface for managing all Raspberry Pis
   - SQLite database for configuration and monitoring
   - WebSocket server for real-time communication
   - REST API for configuration management

3. **Shared Components** (`/shared`)
   - Common data models and utilities

## Technology Stack
- **Language**: Python 3.9+ with FastAPI
- **Database**: SQLite
- **Communication**: WebSocket + REST API fallback
- **Authentication**: API Key based
- **Queue**: Simple FIFO queue
- **Printer Connection**: USB

## Key Features
- Print ZPL labels from URL or raw ZPL content
- Each Raspberry Pi has a unique friendly name and API key
- Centralized configuration management via web admin
- Local CLI configuration on each Pi
- Real-time monitoring and metrics
- Automatic retry on print failures
- Print job queue management

## Installation
- **Raspberry Pi**: `curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-pi.sh | bash`
- **Admin Server**: `curl -sSL https://raw.githubusercontent.com/Baanaaana/Labelberry/main/install-server.sh | bash`

## Project Structure
```
LabelBerry/
├── pi_client/           # Raspberry Pi client application
│   ├── app/            # FastAPI application
│   ├── cli/            # CLI tool
│   └── requirements.txt
├── admin_server/        # Ubuntu admin server
│   ├── app/            # FastAPI backend
│   ├── web/            # Web interface
│   └── requirements.txt
├── shared/             # Shared components
├── install-pi.sh       # Pi installation script
├── install-server.sh   # Server installation script
├── IMPLEMENTATION_CHECKLIST.md  # Development progress tracker
└── docs/              # Documentation
```

## API Endpoints

### Pi Client
- `POST /print` - Submit print job (requires API key)
- `GET /status` - Get printer and queue status
- `GET /health` - Health check
- `POST /test-print` - Print test label

### Admin Server
- `GET /api/pis` - List all Pis
- `GET /api/pis/{id}` - Get Pi details
- `PUT /api/pis/{id}/config` - Update Pi configuration
- `GET /api/pis/{id}/metrics` - Get Pi metrics
- `WS /ws/pi/{id}` - WebSocket for Pi connection

## Database Schema
- **pis**: Raspberry Pi devices registry
- **configurations**: Pi configurations
- **print_jobs**: Print job history
- **metrics**: Performance metrics
- **error_logs**: Error tracking

## Development Guidelines

### Code Style
- Use type hints for all functions
- Follow PEP 8 conventions
- Keep functions focused and single-purpose
- Add docstrings for all public functions
- No unnecessary comments in code

### Testing
- Write unit tests for all modules
- Test error conditions and edge cases
- Ensure printer communication is mocked in tests
- Test WebSocket reconnection logic

### Security
- Always validate API keys
- Sanitize ZPL input
- Use HTTPS/WSS in production
- Never log sensitive information
- Implement rate limiting

## Current Status
- Project is in initial development phase
- Following the IMPLEMENTATION_CHECKLIST.md for progress tracking
- Starting with Phase 1: Core Functionality

## Important Commands

### Development
```bash
# Run Pi client locally
cd pi_client && python -m uvicorn app.main:app --reload

# Run admin server locally
cd admin_server && python -m uvicorn app.main:app --reload

# Run tests
pytest

# Check code style
flake8
black --check .
```

### Cache Busting
**IMPORTANT**: When making any visual changes to the web interface (CSS, JavaScript, or HTML structure), you MUST update the cache version in `/admin_server/app/main.py`:

```python
STATIC_VERSION = int(time.time()) if os.getenv("DEBUG", "false").lower() == "true" else "1.X"
```

Increment the version number (e.g., from "1.5" to "1.6") to force browsers to reload cached static files. This is required for:
- CSS changes
- JavaScript changes  
- Any visual updates that won't appear without clearing browser cache
- After fixing display issues that seem to persist despite code changes

### Deployment
```bash
# On Raspberry Pi
sudo systemctl status labelberry-client
sudo journalctl -u labelberry-client -f

# On Admin Server
sudo systemctl status labelberry-admin
sudo journalctl -u labelberry-admin -f
```

## Configuration Files

### Pi Client (`/etc/labelberry/client.conf`)
- device_id: Auto-generated UUID
- friendly_name: User-defined name
- api_key: Auto-generated for authentication
- admin_server: URL of admin server
- printer_device: USB device path (usually /dev/usb/lp0)

### Admin Server (`/etc/labelberry/server.conf`)
- port: Web interface port (default 8080)
- database_path: SQLite database location

## Troubleshooting

### Common Issues
1. **Printer not detected**: Check USB connection and permissions
2. **WebSocket disconnects**: Check network connectivity
3. **Print jobs stuck**: Check printer status and queue
4. **API key errors**: Verify key in configuration

### Debug Mode
Set `log_level: DEBUG` in configuration files for verbose logging

## Contact
Repository: https://github.com/Baanaaana/LabelBerry

## Notes for Development
- Always check and install only missing dependencies
- Support both URL-based and raw ZPL printing
- Maintain backward compatibility
- Focus on reliability over features
- Keep resource usage low for Raspberry Pi

## Testing Checklist
- [ ] Test with real Zebra printer
- [ ] Test with multiple Pis connected
- [ ] Test network interruptions
- [ ] Test configuration updates
- [ ] Test queue overflow scenarios
- [ ] Test invalid ZPL handling