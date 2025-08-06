# WebSocket Connection Troubleshooting Guide

## Problem
The Raspberry Pi shows as "offline" in the dashboard despite being registered successfully.

## Root Cause
The Pi client is not configured with the correct admin server URL, preventing the WebSocket connection from establishing.

## Solution

### On the Raspberry Pi:

1. **Check current configuration:**
```bash
labelberry config get admin_server
```

2. **Update the admin server URL:**
```bash
# Replace with your actual admin server IP/hostname
labelberry config set admin_server http://20.20.20.63:8080
```

3. **Restart the Pi client service:**
```bash
sudo systemctl restart labelberry-client
```

4. **Verify the connection:**
```bash
# Check service status
sudo systemctl status labelberry-client

# Check logs for WebSocket connection
sudo journalctl -u labelberry-client -f

# Check Pi status
labelberry status
```

## Verification Steps

### On the Admin Server:

1. **Check WebSocket connections:**
```bash
# Check admin server logs
sudo journalctl -u labelberry-admin -f

# Check health endpoint
curl http://localhost:8080/health
```

2. **Monitor dashboard:**
- Open http://20.20.20.63:8080/dashboard
- The Pi should show as "Online" within 5-10 seconds after restart
- The status indicator should turn green

## Common Issues and Fixes

### Issue 1: Wrong Admin Server URL
**Symptom:** "WebSocket connection failed" in Pi logs
**Fix:** Update admin_server config with correct IP/hostname

### Issue 2: Firewall Blocking Connection
**Symptom:** Connection timeout errors
**Fix:** 
```bash
# On admin server
sudo ufw allow 8080/tcp
sudo ufw status
```

### Issue 3: API Key Mismatch
**Symptom:** "Invalid credentials" or "Unauthorized" in logs
**Fix:** Re-register the Pi with correct Device ID and API Key

### Issue 4: Network Connectivity
**Symptom:** Cannot reach admin server
**Fix:**
```bash
# From Pi
ping 20.20.20.63
curl http://20.20.20.63:8080/health
```

## Quick Fix Commands

Run these commands on the Raspberry Pi:

```bash
# All-in-one fix (replace IP with your admin server)
labelberry config set admin_server http://20.20.20.63:8080 && \
sudo systemctl restart labelberry-client && \
sleep 5 && \
labelberry status
```

## Expected Output After Fix

When properly connected, you should see:

1. **In Pi status:**
```
WebSocket Connected: True
```

2. **In Pi logs:**
```
Connected to admin server: ws://20.20.20.63:8080/ws/pi/[device-id]
```

3. **In dashboard:**
- Pi status shows "Online"
- Test Print button is enabled
- Real-time metrics are updating

## Testing Remote Print

Once connected, test remote printing from the dashboard:

1. Click "Test Print" on the Pi card
2. Select "Raw ZPL" method
3. Enter test ZPL:
```
^XA
^FO50,50^A0N,50,50^FDLabelberry Test^FS
^FO50,150^A0N,30,30^FDWebSocket Connected!^FS
^FO50,200^A0N,25,25^FD^FDTimestamp: ^FT^FS
^XZ
```
4. Click "Send Print Job"

The print job should be sent via WebSocket and printed immediately.