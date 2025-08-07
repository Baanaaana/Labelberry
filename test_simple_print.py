#!/usr/bin/env python3
"""
Simple USB print test with proper interface claiming
"""
import usb.core
import usb.util
import usb.backend.libusb1
import time

print("Simple USB Print Test")
print("=" * 50)

ZEBRA_VENDOR_ID = 0x0A5F

# Find the Zebra printer
device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
if not device:
    print("ERROR: No Zebra printer found!")
    exit(1)

print(f"Found: {device.manufacturer} {device.product}")
print(f"Serial: {device.serial_number}")

# Reset the device
print("\nResetting device...")
try:
    device.reset()
    time.sleep(1)
except Exception as e:
    print(f"Reset warning: {e}")

# Set configuration
print("Setting configuration...")
try:
    device.set_configuration()
except usb.core.USBError as e:
    if e.errno == 16:  # Already configured
        print("Device already configured")
    else:
        print(f"Configuration error: {e}")

# Get configuration
cfg = device.get_active_configuration()
print(f"Active configuration: {cfg.bConfigurationValue}")

# Get the first interface
intf = cfg[(0, 0)]
print(f"Using interface: {intf.bInterfaceNumber}")

# Check if kernel driver is attached
if device.is_kernel_driver_active(intf.bInterfaceNumber):
    print("Detaching kernel driver...")
    try:
        device.detach_kernel_driver(intf.bInterfaceNumber)
        print("Kernel driver detached")
    except Exception as e:
        print(f"Failed to detach kernel driver: {e}")
        exit(1)

# Claim the interface
print("Claiming interface...")
try:
    usb.util.claim_interface(device, intf)
    print("Interface claimed")
except Exception as e:
    print(f"Failed to claim interface: {e}")
    exit(1)

# Find the OUT endpoint
ep_out = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
)

if not ep_out:
    print("ERROR: No OUT endpoint found!")
    exit(1)

print(f"OUT endpoint: 0x{ep_out.bEndpointAddress:02x}")

# Test ZPL
test_zpl = """^XA
^FO50,50^A0N,40,40^FDSimple Test^FS
^XZ"""

print(f"\nSending {len(test_zpl)} bytes of ZPL...")
print("ZPL content:")
print(test_zpl)

try:
    data = test_zpl.encode('utf-8')
    bytes_written = ep_out.write(data, timeout=5000)
    print(f"✓ SUCCESS: Sent {bytes_written} bytes")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Release the interface
print("\nReleasing interface...")
try:
    usb.util.release_interface(device, intf)
    print("Interface released")
except Exception as e:
    print(f"Failed to release interface: {e}")

# Dispose resources
usb.util.dispose_resources(device)
print("\nTest complete!")
print("\nIf no label printed, try:")
print("1. Press the feed button on the printer")
print("2. Check if printer LED is solid green (ready)")
print("3. Make sure labels are loaded correctly")