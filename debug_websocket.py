#!/usr/bin/env python3
"""
WebSocket Connection Diagnostic Script
This script helps debug WebSocket connection issues between Pi and Admin Server
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

async def test_websocket_connection(admin_url, device_id, api_key):
    """Test WebSocket connection to admin server"""
    
    # Convert HTTP URL to WebSocket URL
    ws_url = admin_url.replace("http://", "ws://").replace("https://", "wss://")
    full_url = f"{ws_url}/ws/pi/{device_id}"
    
    print(f"\n=== WebSocket Connection Test ===")
    print(f"Admin URL: {admin_url}")
    print(f"WebSocket URL: {full_url}")
    print(f"Device ID: {device_id}")
    print(f"API Key: {api_key[:8]}...")
    print("\nAttempting connection...")
    
    try:
        session = aiohttp.ClientSession()
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Try to connect
        ws = await session.ws_connect(full_url, headers=headers)
        print("✓ WebSocket connected successfully!")
        
        # Send initial connect message
        connect_msg = {
            "type": "connect",
            "pi_id": device_id,
            "data": {
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await ws.send_str(json.dumps(connect_msg))
        print("✓ Sent connect message")
        
        # Wait for response
        try:
            msg = await asyncio.wait_for(ws.receive(), timeout=5.0)
            if msg.type == aiohttp.WSMsgType.TEXT:
                print(f"✓ Received response: {msg.data}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f"✗ WebSocket error: {ws.exception()}")
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("✗ WebSocket closed by server")
        except asyncio.TimeoutError:
            print("⚠ No response received within 5 seconds")
        
        # Send a test metric
        metrics_msg = {
            "type": "metrics",
            "pi_id": device_id,
            "data": {
                "cpu_usage": 25.5,
                "memory_usage": 45.2,
                "queue_size": 0,
                "jobs_completed": 0,
                "jobs_failed": 0,
                "printer_status": "connected"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await ws.send_str(json.dumps(metrics_msg))
        print("✓ Sent test metrics")
        
        # Close connection
        await ws.close()
        await session.close()
        print("✓ Connection closed cleanly")
        
        return True
        
    except aiohttp.ClientError as e:
        print(f"✗ Connection failed: {e}")
        await session.close()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        if 'session' in locals():
            await session.close()
        return False

async def test_admin_health(admin_url):
    """Test admin server health endpoint"""
    print(f"\n=== Admin Server Health Check ===")
    print(f"URL: {admin_url}/health")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{admin_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ Server is healthy")
                    print(f"  Status: {data.get('status')}")
                    print(f"  Connected Pis: {data.get('connected_pis', 0)}")
                    print(f"  Timestamp: {data.get('timestamp')}")
                    return True
                else:
                    print(f"✗ Server returned status {response.status}")
                    return False
    except aiohttp.ClientError as e:
        print(f"✗ Cannot reach admin server: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

async def test_pi_registration(admin_url, device_id, api_key):
    """Check if Pi is registered in admin server"""
    print(f"\n=== Pi Registration Check ===")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{admin_url}/api/pis/{device_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        pi_data = data.get('data', {})
                        print(f"✓ Pi is registered")
                        print(f"  Friendly Name: {pi_data.get('friendly_name')}")
                        print(f"  Status: {pi_data.get('status')}")
                        print(f"  WebSocket Connected: {pi_data.get('websocket_connected')}")
                        return True
                    else:
                        print(f"✗ Pi data retrieval failed")
                        return False
                elif response.status == 404:
                    print(f"✗ Pi not registered (404)")
                    print(f"  Device ID: {device_id}")
                    print(f"  API Key: {api_key[:8]}...")
                    print("\n  To register, use the dashboard or run:")
                    print(f"  curl -X POST {admin_url}/api/pis \\")
                    print(f"    -H 'Content-Type: application/json' \\")
                    print(f"    -d '{{\"id\":\"{device_id}\",\"api_key\":\"{api_key}\",\"friendly_name\":\"Test Pi\"}}'")
                    return False
                else:
                    print(f"✗ Server returned status {response.status}")
                    return False
    except Exception as e:
        print(f"✗ Error checking registration: {e}")
        return False

async def main():
    print("WebSocket Connection Diagnostic Tool")
    print("=" * 40)
    
    # Get parameters
    if len(sys.argv) != 4:
        print("\nUsage: python debug_websocket.py <admin_url> <device_id> <api_key>")
        print("\nExample:")
        print("  python debug_websocket.py http://20.20.20.63:8080 d4148eab-f972-4ea2-a51e-8fea7ed03c5e your-api-key")
        sys.exit(1)
    
    admin_url = sys.argv[1]
    device_id = sys.argv[2]
    api_key = sys.argv[3]
    
    # Run tests
    health_ok = await test_admin_health(admin_url)
    if not health_ok:
        print("\n⚠ Admin server is not reachable. Check:")
        print("  1. Admin server is running: sudo systemctl status labelberry-admin")
        print("  2. Firewall allows port 8080: sudo ufw status")
        print("  3. Network connectivity: ping <admin_ip>")
        return
    
    registered = await test_pi_registration(admin_url, device_id, api_key)
    if not registered:
        print("\n⚠ Pi is not registered. Register it first using the dashboard.")
        return
    
    ws_ok = await test_websocket_connection(admin_url, device_id, api_key)
    
    # Summary
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    if health_ok and registered and ws_ok:
        print("✓ All tests passed! WebSocket connection is working.")
        print("\nNext steps:")
        print("  1. Restart the Pi client service:")
        print("     sudo systemctl restart labelberry-client")
        print("  2. Check the dashboard - Pi should show as 'Online'")
    else:
        print("✗ Some tests failed. Review the output above for details.")
        print("\nTroubleshooting:")
        print("  1. Check Pi client logs:")
        print("     sudo journalctl -u labelberry-client -f")
        print("  2. Check admin server logs:")
        print("     sudo journalctl -u labelberry-admin -f")

if __name__ == "__main__":
    asyncio.run(main())