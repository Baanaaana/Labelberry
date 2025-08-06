# LabelBerry Implementation Checklist

## 📋 Project Overview
A Raspberry Pi-based label printing system with centralized management for Zebra printers.

## 🏗️ Architecture Components

### ✅ Technology Stack Decisions
- [ ] Language: Python with FastAPI
- [ ] Printer Connection: USB
- [ ] Authentication: API Key
- [ ] Admin-Pi Communication: WebSocket + REST API fallback
- [ ] Database: SQLite
- [ ] Queue System: Simple FIFO
- [ ] Installation: Check and install missing dependencies

## 📁 Project Structure Setup

### Repository Organization
- [ ] Create main repository at https://github.com/Baanaaana/LabelBerry
- [ ] Create `/pi-client` directory
- [ ] Create `/admin-server` directory
- [ ] Create `/shared` directory
- [ ] Create `/docs` directory
- [ ] Create root `README.md`
- [ ] Create `install-pi.sh` script
- [ ] Create `install-server.sh` script

## 🥧 Raspberry Pi Client Development

### Core Application (`/pi-client/app/`)
- [ ] Create `main.py` - FastAPI application entry point
- [ ] Create `printer.py` - Zebra printer USB communication
- [ ] Create `queue.py` - FIFO print queue implementation
- [ ] Create `config.py` - Configuration management
- [ ] Create `websocket_client.py` - WebSocket connection to admin server
- [ ] Create `monitoring.py` - Performance metrics collection
- [ ] Create `models.py` - Pydantic models for Pi client

### API Endpoints Implementation
- [ ] `POST /print` - Accept ZPL URL or raw ZPL
  - [ ] Validate API key
  - [ ] Download ZPL from URL if provided
  - [ ] Validate ZPL format
  - [ ] Add to print queue
  - [ ] Return job ID
- [ ] `GET /status` - Return printer and queue status
- [ ] `GET /health` - Health check endpoint
- [ ] `POST /test-print` - Print test label

### CLI Tool (`/pi-client/cli/`)
- [ ] Create `labelberry_cli.py`
- [ ] Command: `labelberry config set <key> <value>`
- [ ] Command: `labelberry config get <key>`
- [ ] Command: `labelberry status`
- [ ] Command: `labelberry test-print`
- [ ] Command: `labelberry queue list`
- [ ] Command: `labelberry queue clear`

### Print Queue Features
- [ ] Implement FIFO queue with persistence
- [ ] Automatic retry on failure
- [ ] Queue size limits
- [ ] Queue status monitoring
- [ ] Error handling and logging

### Printer Communication
- [ ] USB device detection (`/dev/usb/lp*`)
- [ ] ZPL command sending
- [ ] Printer status checking
- [ ] Error handling for offline printer
- [ ] Connection retry logic

### Configuration Management
- [ ] Load configuration from `/etc/labelberry/client.conf`
- [ ] Support environment variable overrides
- [ ] Configuration validation
- [ ] Dynamic configuration updates via WebSocket

### WebSocket Client Features
- [ ] Connect to admin server on startup
- [ ] Authenticate with API key
- [ ] Receive configuration updates
- [ ] Send status updates
- [ ] Send metrics data
- [ ] Automatic reconnection on disconnect
- [ ] Fallback to REST API polling

### Monitoring & Metrics
- [ ] CPU usage tracking
- [ ] Memory usage tracking
- [ ] Queue size monitoring
- [ ] Print success/failure rates
- [ ] Network connectivity status
- [ ] Send metrics to admin server

## 🖥️ Admin Server Development

### Core Application (`/admin-server/app/`)
- [ ] Create `main.py` - FastAPI application entry point
- [ ] Create `database.py` - SQLite database management
- [ ] Create `websocket_server.py` - WebSocket server for Pi connections
- [ ] Create `models.py` - Pydantic models for admin server
- [ ] Create `auth.py` - Authentication handling

### Database Schema Implementation
- [ ] Create `pis` table
  - [ ] id (UUID)
  - [ ] name (friendly name)
  - [ ] api_key
  - [ ] location
  - [ ] printer_model
  - [ ] status
  - [ ] last_seen
- [ ] Create `configurations` table
  - [ ] id
  - [ ] pi_id
  - [ ] config_json
  - [ ] updated_at
- [ ] Create `print_jobs` table
  - [ ] id
  - [ ] pi_id
  - [ ] job_id
  - [ ] status
  - [ ] zpl_source
  - [ ] created_at
  - [ ] completed_at
- [ ] Create `metrics` table
  - [ ] id
  - [ ] pi_id
  - [ ] cpu_usage
  - [ ] memory_usage
  - [ ] queue_size
  - [ ] timestamp
- [ ] Create `error_logs` table
  - [ ] id
  - [ ] pi_id
  - [ ] error_type
  - [ ] message
  - [ ] timestamp
- [ ] Create database migrations system

### API Endpoints Implementation (`/admin-server/app/api/`)
- [ ] `GET /api/pis` - List all Raspberry Pis
- [ ] `GET /api/pis/{id}` - Get specific Pi details
- [ ] `POST /api/pis` - Register new Pi
- [ ] `PUT /api/pis/{id}` - Update Pi information
- [ ] `DELETE /api/pis/{id}` - Remove Pi
- [ ] `PUT /api/pis/{id}/config` - Update Pi configuration
- [ ] `GET /api/pis/{id}/logs` - Get Pi error logs
- [ ] `GET /api/pis/{id}/metrics` - Get Pi performance metrics
- [ ] `POST /api/pis/{id}/command` - Send command to Pi
- [ ] `GET /api/pis/{id}/jobs` - Get print job history
- [ ] `GET /api/dashboard/stats` - Get overall system statistics

### WebSocket Server Features
- [ ] `WS /ws/pi/{id}` - WebSocket endpoint for Pi connections
- [ ] Authentication via API key
- [ ] Configuration push to Pis
- [ ] Status updates from Pis
- [ ] Metrics collection
- [ ] Connection state management
- [ ] Broadcast configuration changes

### Web Interface (`/admin-server/web/`)
- [ ] Create dashboard HTML template
- [ ] Create Pi management page
- [ ] Create configuration editor
- [ ] Create metrics visualization
- [ ] Create print job history view
- [ ] Create error log viewer
- [ ] Implement real-time status updates
- [ ] Add responsive design
- [ ] Create login page
- [ ] Implement user session management

### Admin Features
- [ ] Pi registration workflow
- [ ] Bulk configuration updates
- [ ] Export metrics to CSV
- [ ] System health monitoring
- [ ] Alert system for offline Pis
- [ ] Maintenance mode toggle

## 🔧 Installation Scripts

### Raspberry Pi Installation Script (`install-pi.sh`)
- [ ] System detection (verify Raspberry Pi OS)
- [ ] Python version check (3.9+)
- [ ] Install system dependencies
  - [ ] libusb-1.0-0
  - [ ] python3-pip
  - [ ] python3-venv
  - [ ] git
- [ ] Clone repository (sparse checkout pi-client only)
- [ ] Create virtual environment
- [ ] Install Python packages from requirements.txt
- [ ] Create `/etc/labelberry/` directory
- [ ] Generate unique device ID
- [ ] Generate API key
- [ ] Create systemd service file
- [ ] Enable and start service
- [ ] Run configuration wizard
  - [ ] Prompt for friendly name
  - [ ] Prompt for admin server URL
  - [ ] Test printer connection
  - [ ] Test admin server connection
- [ ] Display success message with next steps

### Ubuntu Server Installation Script (`install-server.sh`)
- [ ] System detection (verify Ubuntu 24.04)
- [ ] Python version check (3.9+)
- [ ] Install system dependencies
  - [ ] python3-pip
  - [ ] python3-venv
  - [ ] nginx
  - [ ] certbot
  - [ ] git
  - [ ] sqlite3
- [ ] Clone repository (sparse checkout admin-server only)
- [ ] Create virtual environment
- [ ] Install Python packages from requirements.txt
- [ ] Create `/etc/labelberry/` directory
- [ ] Create `/var/lib/labelberry/` directory
- [ ] Initialize SQLite database
- [ ] Create systemd service file
- [ ] Configure nginx reverse proxy
- [ ] Setup SSL with certbot (optional)
- [ ] Enable and start services
- [ ] Run setup wizard
  - [ ] Create admin user
  - [ ] Configure port
  - [ ] Configure domain (optional)
- [ ] Display success message with admin URL

## 🔒 Security Implementation

- [ ] API key generation and validation
- [ ] HTTPS/WSS setup for production
- [ ] Input validation for all endpoints
- [ ] Rate limiting implementation
- [ ] CORS configuration
- [ ] SQL injection prevention
- [ ] ZPL content sanitization
- [ ] Audit logging system
- [ ] Secure configuration storage
- [ ] Authentication for admin interface

## 📚 Documentation

### User Documentation
- [ ] Installation guide for Raspberry Pi
- [ ] Installation guide for Ubuntu server
- [ ] Configuration reference
- [ ] API documentation
- [ ] Troubleshooting guide
- [ ] FAQ section

### Developer Documentation
- [ ] Architecture overview
- [ ] API specification (OpenAPI/Swagger)
- [ ] Database schema documentation
- [ ] WebSocket protocol documentation
- [ ] Contributing guidelines
- [ ] Code style guide

### Operational Documentation
- [ ] Deployment guide
- [ ] Backup and restore procedures
- [ ] Monitoring setup
- [ ] Performance tuning guide
- [ ] Security best practices
- [ ] Update procedures

## 🧪 Testing

### Unit Tests
- [ ] Pi client printer module tests
- [ ] Queue management tests
- [ ] Configuration handling tests
- [ ] API endpoint tests
- [ ] Database operation tests
- [ ] WebSocket communication tests

### Integration Tests
- [ ] Pi to admin server communication
- [ ] End-to-end print job flow
- [ ] Configuration update propagation
- [ ] Error handling scenarios
- [ ] Network interruption handling

### System Tests
- [ ] Multi-Pi setup testing
- [ ] Load testing with multiple print jobs
- [ ] Long-running stability tests
- [ ] Installation script testing
- [ ] Update/upgrade testing

## 🚀 Deployment Preparation

- [ ] Create GitHub repository
- [ ] Setup CI/CD pipeline
- [ ] Create release workflow
- [ ] Version tagging strategy
- [ ] Create demo/test environment
- [ ] Prepare deployment checklist
- [ ] Create rollback procedures

## 📊 Monitoring & Maintenance

- [ ] Setup logging infrastructure
- [ ] Configure log rotation
- [ ] Create monitoring dashboards
- [ ] Setup alerting rules
- [ ] Create backup schedules
- [ ] Document maintenance procedures
- [ ] Create update notification system

## 🎯 MVP Milestones

### Phase 1: Core Functionality
- [ ] Basic Pi client with print capability
- [ ] Simple admin server with Pi registration
- [ ] Basic WebSocket communication
- [ ] Minimal web interface

### Phase 2: Queue & Monitoring
- [ ] Print queue implementation
- [ ] Metrics collection
- [ ] Enhanced web dashboard
- [ ] Error handling

### Phase 3: Production Ready
- [ ] Installation scripts
- [ ] Full documentation
- [ ] Security hardening
- [ ] Performance optimization

### Phase 4: Advanced Features
- [ ] Advanced queue management
- [ ] Analytics and reporting
- [ ] Multi-user support
- [ ] API extensions

## 📝 Configuration File Templates

### Pi Client Configuration (`/etc/labelberry/client.conf`)
```yaml
device_id: ${AUTO_GENERATED}
friendly_name: ${USER_INPUT}
api_key: ${AUTO_GENERATED}
admin_server: ${USER_INPUT}
printer_device: /dev/usb/lp0
queue_size: 100
retry_attempts: 3
retry_delay: 5
log_level: INFO
log_file: /var/log/labelberry/client.log
metrics_interval: 60
```

### Admin Server Configuration (`/etc/labelberry/server.conf`)
```yaml
host: 0.0.0.0
port: 8080
database_path: /var/lib/labelberry/db.sqlite
log_level: INFO
log_file: /var/log/labelberry/server.log
ssl_enabled: false
ssl_cert_path: ""
ssl_key_path: ""
cors_origins: ["*"]
rate_limit: 100
session_timeout: 3600
```

## ✅ Definition of Done

Each component is considered complete when:
- [ ] Code is implemented and working
- [ ] Unit tests are written and passing
- [ ] Documentation is updated
- [ ] Code review is completed
- [ ] Integration tests pass
- [ ] Deployment tested

---

**Total Items:** ~200+ checkboxes
**Estimated Timeline:** 4-6 weeks for full implementation
**Priority:** Start with Phase 1 MVP for basic functionality

This checklist will be used to track progress throughout the development process.