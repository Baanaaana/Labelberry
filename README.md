# LabelBerry 🏷️

A modern, enterprise-grade label printing system for Zebra printers with centralized management, real-time monitoring, and a beautiful Next.js web interface.

## 🌟 Features

### Core Functionality
- **Centralized Management**: Manage all your Raspberry Pi-connected Zebra printers from a single dashboard
- **Real-time Monitoring**: Live status updates via MQTT with WebSocket fallback
- **Smart Queue Management**: Automatic job queuing when printers are offline with retry logic
- **Multiple Print Methods**: Support for raw ZPL, URL-based ZPL, and direct file uploads
- **API-First Design**: RESTful API with Bearer token authentication

### Modern Web Interface (Next.js 15)
- **Responsive Dashboard**: Real-time metrics and printer status at a glance
- **Performance Analytics**: Track print times, success rates, and queue lengths
- **API Key Management**: Secure API key generation and management
- **Interactive API Documentation**: Built-in API explorer with curl examples
- **Dark Mode Support**: Automatic theme switching based on system preferences
- **Real-time Updates**: Live printer status and job progress

### Enterprise Features
- **PostgreSQL Database**: Scalable data storage with async operations
- **MQTT Integration**: Real-time bidirectional communication between server and Pi clients
- **Bearer Token Authentication**: Secure API access with `ak_` prefixed keys
- **Automatic Retry Logic**: Failed jobs automatically retry with exponential backoff
- **Comprehensive Logging**: Detailed error tracking and performance metrics
- **48-hour Print History**: Complete job history with ZPL content storage

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Web Interface                    │
│              (React 18 + TypeScript + shadcn/ui)             │
│                        Port: 3000                            │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────────┐
│                    Admin Server (FastAPI)                    │
│              PostgreSQL + MQTT Broker + REST API             │
│                        Port: 8080                            │
└────────┬───────────────────────────────────┬────────────────┘
         │ MQTT (Port 1883)                  │ MQTT
┌────────▼──────────┐               ┌────────▼──────────┐
│   Raspberry Pi    │               │   Raspberry Pi    │
│   Client (Pi 1)   │               │   Client (Pi 2)   │
│   Port: 5000      │               │   Port: 5000      │
│   ┌────────────┐  │               │   ┌────────────┐  │
│   │Zebra Printer│ │               │   │Zebra Printer│ │
│   └────────────┘  │               │   └────────────┘  │
└───────────────────┘               └───────────────────┘
```

## 📋 Requirements

### Admin Server
- Ubuntu 24.04 LTS (recommended) or any Linux distribution
- Python 3.9+
- PostgreSQL 14+
- Node.js 18+ and npm 9+
- Mosquitto MQTT broker
- 2GB RAM minimum
- 10GB disk space

### Raspberry Pi Clients
- Raspberry Pi 3/4/5 or Zero 2 W
- Raspberry Pi OS (32-bit or 64-bit)
- Python 3.9+
- USB-connected Zebra printer
- Network connectivity to admin server

## 🚀 Quick Installation

### One-Command Installation

```bash
# Run this single command to install LabelBerry:
curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install.sh | sudo bash
```

The installer will:
1. Download the installation menu to a temporary directory
2. Display an interactive menu to choose between **Server** or **Pi Client**
3. Detect your system type and provide appropriate warnings
4. Run the selected installation automatically
5. Clean up temporary files after completion

### Server Installation

Choose option **1** when prompted by the installer. The complete server installation includes:

- **Backend**: FastAPI with PostgreSQL database connection
- **Frontend**: Next.js web interface  
- **Services**: MQTT broker, systemd services, PM2 process manager
- **Dependencies**: Python, Node.js, npm, and all required packages

After installation:
- **Web Interface**: `http://your-server-ip:3000`
- **API Endpoint**: `http://your-server-ip:8080`
- **MQTT Broker**: `your-server-ip:1883`

### Pi Client Installation

Choose option **2** when prompted by the installer. You'll be asked for:

1. Admin server URL (e.g., `http://192.168.1.100:8080`)
2. MQTT broker details
3. Printer configuration

The installer will automatically detect connected Zebra printers and register them with the server.

### Post-Installation

#### Access the Management Menu

After server installation, the management menu is available:

```bash
cd /opt/labelberry
./labelberry-menu.sh  # Opens the management interface
```

The menu provides easy access to:
- Service management (start/stop/restart)
- Log viewing and monitoring
- System updates and deployments
- Database operations
- Configuration editing

#### Updating Your Installation

For updates to existing installations:

```bash
cd /opt/labelberry
./deploy.sh  # Updates and redeploys the system
```

This will:
- Pull latest changes from GitHub
- Rebuild backend and frontend
- Restart services with zero downtime
- Verify system health

> **Note**: The deploy script is only for updates. For new installations, always use the installer.

## 🛠️ Management Tools

### Interactive Management Menu

The management menu is available after server installation:

```bash
cd /opt/labelberry
./labelberry-menu.sh  # Open the management menu
```

The menu provides:
- **Deployment & Build**: Git pull, build, dependency updates
- **Service Management**: Start/stop/restart all services
- **Logs & Monitoring**: Real-time log streaming, PM2 monitoring
- **Database Access**: PostgreSQL console, configuration editing
- **Utilities**: System info, disk usage, quick navigation

### Updating Your System

For updates to existing installations:

```bash
cd /opt/labelberry
./deploy.sh  # Automated update and deployment
```

This will:
- Pull latest code from git
- Install/update dependencies
- Build Next.js application
- Restart services with zero downtime
- Run health checks

### Uninstallation

To completely remove LabelBerry:

```bash
# Uninstall server
curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install/uninstall-server.sh | sudo bash

# Uninstall Pi client
curl -sSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install/uninstall-pi.sh | sudo bash
```

## 🔧 Configuration

### Nginx Proxy Manager Setup (Recommended)

For production deployments using Nginx Proxy Manager with path-based routing:

#### Create Proxy Host:
1. **Domain**: `labelberry.yourdomain.com`
2. **SSL Certificate**: Enable Let's Encrypt
3. **Locations**:

```nginx
Location: /
Forward to: http://localhost:3000
Websockets Support: Disabled

Location: /api/
Forward to: http://localhost:8080/api/
Websockets Support: ✓ Enabled (Required for real-time updates)
Block Common Exploits: ✓ Enabled
```

**Important**: Use `/api/` (with trailing slash) in both the location and forward URL to ensure proper path forwarding. The backend expects routes like `/api/mqtt-settings`.

#### Update Environment Variables:

**Next.js** (`/opt/labelberry/nextjs/.env`):
```env
NEXTAUTH_URL="https://labelberry.yourdomain.com"
NEXT_PUBLIC_API_URL="https://labelberry.yourdomain.com/api"
NEXT_PUBLIC_WS_URL="wss://labelberry.yourdomain.com/api"
```

**FastAPI** (`/opt/labelberry/admin_server/.env`):
```env
# No changes needed - keeps using localhost
MQTT_HOST=localhost
MQTT_PORT=1883
```

#### Required Ports:
- **80/443**: HTTP/HTTPS (handled by Nginx)
- **1883**: MQTT broker (direct connection for Raspberry Pi clients)

After configuration changes, restart services:
```bash
cd /opt/labelberry
./deploy.sh
```

### Environment Variables (Admin Server)

Create or edit `/etc/labelberry/.env`:

```env
# Database Configuration
DATABASE_URL=postgresql://labelberry:your_password@localhost/labelberry

# MQTT Settings (optional - can be configured via web UI)
MQTT_BROKER=broker.yourdomain.com
MQTT_PORT=1883
MQTT_USERNAME=labelberry
MQTT_PASSWORD=secure_mqtt_password

# Server Settings
DEBUG=false
STATIC_VERSION=1.0
NODE_ENV=production

# Optional: External Access
NEXT_PUBLIC_API_URL=http://your-domain.com:8080
```

### Pi Client Configuration

Located at `/etc/labelberry/client.conf`:

```yaml
device_id: feb9fba3-bcdd-4990-8d89-62ecd33c7efd
friendly_name: "Warehouse Printer 1"
api_key: 0ce5717b-c7ee-4274-8e38-a1525968b036
admin_server: http://192.168.1.100:8080
printer_device: /dev/usb/lp0
mqtt_broker: 192.168.1.100
mqtt_port: 1883
mqtt_username: pi_client
mqtt_password: client_password
log_level: INFO
auto_reconnect: true
max_queue_size: 100
```

## 📡 API Usage

### Authentication

All API requests require a Bearer token in the Authorization header:

```bash
Authorization: Bearer ak_your_api_key_here
```

### Get API Keys

API keys can be created and managed through:
1. **Web Interface**: Settings → API Keys
2. **CLI**: `labelberry api-key create "My App"`

### Print a Label

```bash
# Print with raw ZPL - waits for completion by default
curl -X POST http://your-server:8080/api/pis/YOUR_PI_ID/print \
  -H "Authorization: Bearer ak_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^ADN,36,20^FDHello World^FS^XZ"
  }'

# Print from URL
curl -X POST http://your-server:8080/api/pis/YOUR_PI_ID/print \
  -H "Authorization: Bearer ak_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_url": "https://example.com/label.zpl"
  }'

# Async mode - returns immediately without waiting
curl -X POST http://your-server:8080/api/pis/YOUR_PI_ID/print \
  -H "Authorization: Bearer ak_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^ADN,36,20^FDAsync Print^FS^XZ",
    "wait_for_completion": false
  }'
```

### Direct Pi Printing (Local Network Only)

```bash
# No authentication required when on same network
curl -X POST http://pi-ip:5000/print \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^FDDirect Print^FS^XZ"
  }'
```

### List All Printers

```bash
curl -X GET http://your-server:8080/api/pis \
  -H "Authorization: Bearer ak_your_api_key"
```

### Get Print History

```bash
# Get recent print jobs
curl -X GET http://your-server:8080/api/recent-jobs?limit=50 \
  -H "Authorization: Bearer ak_your_api_key"

# Filter by printer
curl -X GET "http://your-server:8080/api/recent-jobs?pi_id=YOUR_PI_ID" \
  -H "Authorization: Bearer ak_your_api_key"
```

## 🖥️ Web Interface Features

### Dashboard (Home)
- **Real-time Metrics**: Total printers, jobs today, average print time, queue length
- **Printer Overview**: Status, last seen, jobs count for each printer
- **Quick Actions**: Test print, edit settings, delete printer
- **Server Configuration**: Display and copy server URL for Pi installations

### Performance Analytics
- **Live Charts**: Print volume, success rates, response times
- **Printer Metrics**: Individual printer performance statistics
- **System Health**: CPU, memory, and disk usage monitoring
- **Export Data**: Download metrics as CSV or JSON

### Queue Management
- **Live Queue View**: See all pending and processing jobs
- **Priority Management**: Adjust job priorities on the fly
- **Bulk Actions**: Cancel or retry multiple jobs at once
- **Queue Analytics**: Average wait times and throughput

### Settings
- **API Keys**: Create, view, and revoke API keys
- **MQTT Configuration**: Configure broker settings and credentials
- **User Management**: Add users and manage permissions
- **System Settings**: Configure retention, timeouts, and limits

### API Documentation
- **Interactive Explorer**: Test API endpoints directly from the browser
- **Code Examples**: Copy-paste ready examples in multiple languages
- **Authentication Guide**: Step-by-step setup instructions
- **WebSocket Events**: Real-time event documentation

## 🛠️ Development

### Backend Development

```bash
cd admin_server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements_postgres.txt

# Set up environment
cp .env.example .env
# Edit .env with your database credentials

# Run with hot reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Frontend Development

```bash
cd nextjs
npm install

# Development server with hot reload
npm run dev
# Open http://localhost:3000

# Production build
npm run build
npm start
```

### Running Tests

```bash
# Backend tests
cd admin_server
pytest tests/

# Frontend tests
cd nextjs
npm test
npm run test:e2e  # End-to-end tests

# Linting
npm run lint
```

## 🔍 Monitoring & Troubleshooting

### View Logs

```bash
# Admin server (FastAPI)
sudo journalctl -u labelberry-admin -f

# Next.js frontend
sudo journalctl -u labelberry-frontend -f

# MQTT broker
sudo journalctl -u mosquitto -f

# PostgreSQL
sudo -u postgres tail -f /var/log/postgresql/*.log

# Pi client (on each Pi)
sudo journalctl -u labelberry-client -f
```

### Database Access

```bash
# Connect to PostgreSQL
sudo -u postgres psql labelberry

# Useful queries
\dt                                    -- List all tables
SELECT * FROM pis;                     -- List all printers
SELECT * FROM api_keys;                -- View API keys
SELECT COUNT(*) FROM print_jobs;       -- Total print jobs
SELECT * FROM print_jobs 
  ORDER BY created_at DESC LIMIT 10;   -- Recent jobs
```

### MQTT Debugging

```bash
# Monitor all MQTT traffic
mosquitto_sub -h localhost -p 1883 -t "labelberry/#" -v

# Test MQTT connection
mosquitto_pub -h localhost -p 1883 -t "labelberry/test" -m "test"

# Check specific printer
mosquitto_sub -h localhost -t "labelberry/pi/YOUR_DEVICE_ID/#" -v
```

### Common Issues

#### Server Setup Issues

##### Services Not Starting After Installation
```bash
# Check each service
systemctl status labelberry-admin      # FastAPI backend
pm2 status                            # Next.js frontend
systemctl status mosquitto            # MQTT broker
systemctl status postgresql           # Database

# Restart services if needed
sudo systemctl restart labelberry-admin
pm2 restart labelberry-nextjs
sudo systemctl restart mosquitto
```

##### Port Already in Use
```bash
# Check what's using the ports
sudo lsof -i :3000                   # Next.js port
sudo lsof -i :8080                   # FastAPI port
sudo lsof -i :1883                   # MQTT port

# Kill the process if needed (replace PID)
sudo kill -9 <PID>
```

##### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "SELECT 1"

# Reset database if needed
sudo -u postgres psql -c "DROP DATABASE IF EXISTS labelberry"
sudo -u postgres psql -c "CREATE DATABASE labelberry"
```

#### Printer Not Detected
```bash
ls -la /dev/usb/lp*                    # Check USB device
lsusb | grep -i zebra                  # Verify printer connected
sudo usermod -a -G lp labelberry       # Fix permissions
sudo systemctl restart labelberry-client
```

#### MQTT Connection Failed
```bash
sudo systemctl status mosquitto        # Check broker status
sudo mosquitto_passwd -b /etc/mosquitto/passwd username password
sudo systemctl restart mosquitto
```

#### Frontend Not Loading
```bash
# Check PM2 status
pm2 status
pm2 logs labelberry-nextjs            # View logs

# Rebuild if needed
cd /opt/labelberry/nextjs
npm run build
pm2 restart labelberry-nextjs

# Check firewall
sudo ufw allow 3000/tcp               # Open frontend port
sudo ufw allow 8080/tcp               # Open API port
```

## 📚 Project Structure

```
LabelBerry/
├── admin_server/              # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Main application & API routes
│   │   ├── database_postgres.py  # PostgreSQL operations
│   │   ├── database_wrapper.py   # Database abstraction
│   │   ├── mqtt_server.py   # MQTT broker integration
│   │   ├── queue_manager.py # Job queue management
│   │   └── config.py        # Configuration management
│   └── requirements_postgres.txt
│
├── nextjs/                   # Next.js frontend
│   ├── src/
│   │   ├── app/             # App router pages
│   │   │   ├── page.tsx     # Dashboard (home)
│   │   │   ├── performance/ # Analytics page
│   │   │   ├── queue/       # Queue management
│   │   │   ├── settings/    # Settings & API keys
│   │   │   └── api-docs/    # API documentation
│   │   └── components/      # Reusable React components
│   │       └── ui/          # shadcn/ui components
│   ├── package.json
│   ├── tailwind.config.ts
│   └── next.config.ts
│
├── pi_client/               # Raspberry Pi client
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── printer.py      # Zebra printer interface
│   │   ├── mqtt_client.py  # MQTT client
│   │   ├── queue.py        # Local queue management
│   │   └── config.py       # Configuration handler
│   ├── cli/
│   │   └── labelberry_cli.py  # CLI tool
│   └── requirements.txt
│
├── shared/                  # Shared code
│   ├── models.py           # Data models
│   └── mqtt_config.py      # MQTT topics
│
├── install/               # Installation scripts
│   ├── install-server.sh  # Server installer
│   ├── install-pi.sh      # Pi client installer
│   ├── uninstall-server.sh # Server uninstaller
│   └── uninstall-pi.sh    # Pi uninstaller
│
├── deploy.sh              # Deployment script
├── labelberry-menu.sh     # Management menu
├── API_DOCUMENTATION.md   # Complete API reference
└── CLAUDE.md              # Development notes
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write tests for new features
- Update documentation for API changes
- Use conventional commits format

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Next.js](https://nextjs.org/) and [FastAPI](https://fastapi.tiangolo.com/)
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- Icons by [Lucide](https://lucide.dev/)
- MQTT broker by [Eclipse Mosquitto](https://mosquitto.org/)
- Database powered by [PostgreSQL](https://www.postgresql.org/)

## 📞 Support

- 📧 Email: support@labelberry.com
- 🐛 Issues: [GitHub Issues](https://github.com/Baanaaana/LabelBerry/issues)
- 📖 Wiki: [GitHub Wiki](https://github.com/Baanaaana/LabelBerry/wiki)

---

Made with ❤️ for Raspberry Pi and Zebra printers