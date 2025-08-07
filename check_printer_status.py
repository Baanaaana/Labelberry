#!/usr/bin/env python3
"""
Check Zebra printer status via USB
"""
import usb.core
import usb.util
import time

print("Zebra Printer Status Check")
print("=" * 50)

ZEBRA_VENDOR_ID = 0x0A5F

# Find the Zebra printer
device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
if not device:
    print("ERROR: No Zebra printer found!")
    exit(1)

print(f"Found printer: {device.product}")

# Set configuration if needed
try:
    cfg = device.get_active_configuration()
except usb.core.USBError:
    print("Setting configuration...")
    device.set_configuration()
    cfg = device.get_active_configuration()

# Get interface
intf = cfg[(0, 0)]

# Detach kernel driver if needed
if device.is_kernel_driver_active(intf.bInterfaceNumber):
    print("Detaching kernel driver...")
    device.detach_kernel_driver(intf.bInterfaceNumber)

# Find endpoints
ep_out = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
)

ep_in = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
)

print(f"OUT endpoint: {ep_out}")
print(f"IN endpoint: {ep_in}")
print()

def send_and_read(command, description):
    """Send command and try to read response"""
    print(f"Sending: {description}")
    print(f"Command: {command}")
    
    try:
        # Send command
        ep_out.write(command.encode('utf-8'))
        print("✓ Command sent")
        
        # Try to read response
        if ep_in:
            try:
                time.sleep(0.5)  # Give printer time to respond
                data = ep_in.read(1024, timeout=1000)
                response = ''.join([chr(x) for x in data if x > 0])
                print(f"Response: {response}")
            except usb.core.USBTimeoutError:
                print("No response (timeout)")
            except Exception as e:
                print(f"Read error: {e}")
    except Exception as e:
        print(f"Send error: {e}")
    
    print()

# Test various status commands
print("Testing printer status commands...")
print("-" * 30)

# Host status
send_and_read("~HS", "Host Status")

# Printer configuration
send_and_read("^XA^HH^XZ", "Configuration Label Request")

# Head test
send_and_read("~HD", "Head Diagnostic")

# Reset printer
print("Sending printer reset command...")
try:
    ep_out.write(b"~JR")
    print("✓ Reset command sent")
    time.sleep(2)
except Exception as e:
    print(f"Reset failed: {e}")

print()
print("=" * 50)
print("Status check complete!")
print()
print("Note: Most Zebra printers don't return data over USB")
print("Check the printer's LED indicators:")
print("- Solid green = Ready")
print("- Flashing green = Receiving data")
print("- Amber = Pause")
print("- Red = Error")