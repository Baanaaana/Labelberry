# LabelBerry API Documentation

## Table of Contents
- [Authentication](#authentication)
- [Printer Management](#printer-management)
  - [List All Printers](#list-all-printers)
  - [Get Printer Details](#get-printer-details)
- [Printing Labels](#printing-labels)
  - [Print via Admin Server](#print-via-admin-server)
  - [Print Directly to Pi](#print-directly-to-pi)
- [Label Sizes](#label-sizes)
- [Error Handling](#error-handling)

---

## Authentication

The LabelBerry API uses Bearer token authentication for print operations. You need to create an API key in the admin dashboard.

### Creating an API Key
1. Login to the admin dashboard
2. Go to Settings → API Keys
3. Click "Create New Key"
4. Save the generated key securely (it won't be shown again)

### Using the API Key
Include the API key in the Authorization header:
```
Authorization: Bearer labk_your_api_key_here
```

---

## Printer Management

### List All Printers

Get a list of all registered printers with their details and label sizes.

**Endpoint:** `GET /api/pis`

**Authentication:** Not required for reading

**Response:**
```json
{
  "success": true,
  "message": "Pis retrieved",
  "data": {
    "pis": [
      {
        "id": "uuid-here",
        "friendly_name": "Warehouse Printer 1",
        "location": "Building A, Floor 2",
        "printer_model": "Zebra ZD220",
        "label_size_id": 1,
        "label_size": {
          "id": 1,
          "name": "Large Shipping",
          "width_mm": 102,
          "height_mm": 150,
          "display_name": "Large Shipping (102mm x 150mm)"
        },
        "status": "online",
        "websocket_connected": true,
        "queue_count": 0,
        "last_seen": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 1
  }
}
```

**cURL Example:**
```bash
curl -X GET http://your-server:8080/api/pis
```

### Get Printer Details

Get detailed information about a specific printer.

**Endpoint:** `GET /api/pis/{pi_id}`

**Authentication:** Not required for reading

**Response:**
```json
{
  "success": true,
  "message": "Pi details retrieved",
  "data": {
    "id": "uuid-here",
    "friendly_name": "Warehouse Printer 1",
    "location": "Building A, Floor 2",
    "printer_model": "Zebra ZD220",
    "label_size": {
      "id": 1,
      "name": "Large Shipping",
      "width_mm": 102,
      "height_mm": 150,
      "display_name": "Large Shipping (102mm x 150mm)"
    },
    "status": "online",
    "websocket_connected": true,
    "config": {
      "device_id": "uuid-here",
      "printer_device": "/dev/usblp0",
      "queue_size": 100
    }
  }
}
```

**cURL Example:**
```bash
curl -X GET http://your-server:8080/api/pis/your-pi-id
```

---

## Printing Labels

### Print via Admin Server

Send a print job to a specific printer through the admin server. The printer must be online and connected via WebSocket.

**Endpoint:** `POST /api/pis/{pi_id}/print`

**Authentication:** Required (Bearer token)

**Method 1: Raw ZPL**

Send ZPL commands directly as a string.

**Request Body:**
```json
{
  "zpl_raw": "^XA^FO50,50^FDHello World^FS^XZ"
}
```

**cURL Example:**
```bash
curl -X POST http://your-server:8080/api/pis/your-pi-id/print \
  -H "Authorization: Bearer labk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^FDHello World^FS^XZ"
  }'
```

**Method 2: ZPL from URL**

Provide a URL where the ZPL file can be downloaded.

**Request Body:**
```json
{
  "zpl_url": "https://example.com/labels/shipping-label.zpl"
}
```

**cURL Example:**
```bash
curl -X POST http://your-server:8080/api/pis/your-pi-id/print \
  -H "Authorization: Bearer labk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_url": "https://example.com/labels/shipping-label.zpl"
  }'
```

**Method 3: ZPL File Upload**

Upload a ZPL file directly (multipart form data).

**cURL Example:**
```bash
curl -X POST http://your-server:8080/api/pis/your-pi-id/print \
  -H "Authorization: Bearer labk_your_api_key_here" \
  -F "zpl_file=@/path/to/label.zpl"
```

**Response (all methods):**
```json
{
  "success": true,
  "message": "Print job sent via WebSocket",
  "data": {
    "pi_id": "uuid-here"
  }
}
```

### Print Directly to Pi

If you have direct network access to the Pi, you can send print jobs directly without going through the admin server.

**Endpoint:** `POST http://pi-ip:5000/print`

**Authentication:** Not required (local network only)

**Method 1: Raw ZPL**

**Request Body:**
```json
{
  "zpl_raw": "^XA^FO50,50^FDDirect Print^FS^XZ"
}
```

**cURL Example:**
```bash
curl -X POST http://192.168.1.100:5000/print \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_raw": "^XA^FO50,50^FDDirect Print^FS^XZ"
  }'
```

**Method 2: ZPL from URL**

**Request Body:**
```json
{
  "zpl_url": "https://example.com/labels/shipping-label.zpl"
}
```

**cURL Example:**
```bash
curl -X POST http://192.168.1.100:5000/print \
  -H "Content-Type: application/json" \
  -d '{
    "zpl_url": "https://example.com/labels/shipping-label.zpl"
  }'
```

**Method 3: ZPL File Upload**

**cURL Example:**
```bash
curl -X POST http://192.168.1.100:5000/print \
  -F "zpl_file=@/path/to/label.zpl"
```

**Response (all methods):**
```json
{
  "success": true,
  "message": "Print job queued",
  "data": {
    "job_id": "job-uuid-here",
    "queue_position": 1
  }
}
```

---

## Label Sizes

### Get Available Label Sizes

List all configured label sizes in the system.

**Endpoint:** `GET /api/label-sizes`

**Authentication:** Not required

**Response:**
```json
{
  "success": true,
  "message": "Label sizes retrieved",
  "data": {
    "sizes": [
      {
        "id": 1,
        "name": "Large Shipping",
        "width_mm": 102,
        "height_mm": 150,
        "is_default": true,
        "display_name": "Large Shipping (102mm x 150mm)"
      },
      {
        "id": 2,
        "name": "Standard",
        "width_mm": 57,
        "height_mm": 32,
        "is_default": true,
        "display_name": "Standard (57mm x 32mm)"
      },
      {
        "id": 3,
        "name": "Small",
        "width_mm": 57,
        "height_mm": 19,
        "is_default": true,
        "display_name": "Small (57mm x 19mm)"
      }
    ]
  }
}
```

**cURL Example:**
```bash
curl -X GET http://your-server:8080/api/label-sizes
```

---

## Error Handling

The API returns standard HTTP status codes and JSON error responses.

### Common Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Resource not found
- `503 Service Unavailable` - Printer offline or not connected

### Error Response Format

```json
{
  "success": false,
  "message": "Error description",
  "detail": "Detailed error information"
}
```

### Common Error Scenarios

**Printer Offline:**
```json
{
  "success": false,
  "message": "Service Unavailable",
  "detail": "Pi is not connected via WebSocket"
}
```

**Invalid API Key:**
```json
{
  "success": false,
  "message": "Unauthorized",
  "detail": "Invalid API key"
}
```

**Invalid ZPL:**
```json
{
  "success": false,
  "message": "Bad Request",
  "detail": "Invalid ZPL format"
}
```

---

## Example Integration

### Python Example

```python
import requests
import json

class LabelBerryClient:
    def __init__(self, server_url, api_key):
        self.server_url = server_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def list_printers(self):
        """Get all available printers"""
        response = requests.get(f"{self.server_url}/api/pis")
        return response.json()
    
    def print_label(self, printer_id, zpl_code):
        """Print a label to specific printer"""
        data = {"zpl_raw": zpl_code}
        response = requests.post(
            f"{self.server_url}/api/pis/{printer_id}/print",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
client = LabelBerryClient("http://your-server:8080", "labk_your_api_key")

# List printers
printers = client.list_printers()
for printer in printers["data"]["pis"]:
    print(f"{printer['friendly_name']} - {printer['status']}")
    if printer.get('label_size'):
        print(f"  Label Size: {printer['label_size']['display_name']}")

# Print a label
zpl = "^XA^FO50,50^FDTest Label^FS^XZ"
result = client.print_label("your-printer-id", zpl)
print(result["message"])
```

### Node.js Example

```javascript
const axios = require('axios');

class LabelBerryClient {
    constructor(serverUrl, apiKey) {
        this.serverUrl = serverUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async listPrinters() {
        const response = await axios.get(`${this.serverUrl}/api/pis`);
        return response.data;
    }
    
    async printLabel(printerId, zplCode) {
        const response = await axios.post(
            `${this.serverUrl}/api/pis/${printerId}/print`,
            { zpl_raw: zplCode },
            { headers: this.headers }
        );
        return response.data;
    }
}

// Usage
const client = new LabelBerryClient('http://your-server:8080', 'labk_your_api_key');

// List printers
client.listPrinters().then(result => {
    result.data.pis.forEach(printer => {
        console.log(`${printer.friendly_name} - ${printer.status}`);
        if (printer.label_size) {
            console.log(`  Label Size: ${printer.label_size.display_name}`);
        }
    });
});

// Print a label
const zpl = '^XA^FO50,50^FDTest Label^FS^XZ';
client.printLabel('your-printer-id', zpl).then(result => {
    console.log(result.message);
});
```

---

## Rate Limiting

Currently, there are no rate limits on the API. However, please be mindful of:
- Queue size limits on individual Pis (default: 100 jobs)
- Network bandwidth when sending large print jobs
- WebSocket connection stability for real-time printing

---

## Support

For issues or questions:
- GitHub: https://github.com/Baanaaana/LabelBerry
- Check printer status in the admin dashboard
- View logs: `sudo journalctl -u labelberry-client -f` (on Pi)