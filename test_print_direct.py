#!/usr/bin/env python3
"""
Direct USB print test with various ZPL formats
"""
import usb.core
import usb.util
import time

print("Direct USB Print Test")
print("=" * 50)

ZEBRA_VENDOR_ID = 0x0A5F

# Find the Zebra printer
device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
if not device:
    print("ERROR: No Zebra printer found!")
    exit(1)

print(f"Found printer: {device}")

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

# Find OUT endpoint
ep_out = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
)

if not ep_out:
    print("ERROR: No OUT endpoint found!")
    exit(1)

print(f"Using endpoint: {ep_out}")
print()

def send_zpl(zpl, description):
    """Send ZPL and report result"""
    print(f"Test: {description}")
    print(f"Sending {len(zpl)} bytes...")
    try:
        data = zpl.encode('utf-8')
        bytes_written = ep_out.write(data)
        print(f"✓ Sent {bytes_written} bytes successfully")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False
    finally:
        print()

# Test 1: Basic test label
zpl1 = """^XA
^FO50,50^A0N,50,50^FDTest Label^FS
^XZ"""

send_zpl(zpl1, "Basic test label")
time.sleep(2)

# Test 2: Test with calibration
zpl2 = """~JC
^XA
^FO50,50^A0N,50,50^FDAfter Calibration^FS
^XZ"""

send_zpl(zpl2, "With calibration command")
time.sleep(2)

# Test 3: Full test label with more commands
zpl3 = """^XA
^PW400
^LL200
^FO50,30^A0N,30,30^FDLabelBerry Test^FS
^FO50,70^A0N,25,25^FDTime: """ + time.strftime("%H:%M:%S") + """^FS
^FO50,100^A0N,20,20^FDUSB Direct Print^FS
^XZ"""

send_zpl(zpl3, "Full label with width/length")
time.sleep(2)

# Test 4: Wake up printer and print
zpl4 = """~HS
^XA
^FO20,20^A0N,40,40^FDWake Up Test^FS
^XZ"""

send_zpl(zpl4, "With status command first")
time.sleep(2)

# Test 5: Simple text only
zpl5 = """^XA^FO20,20^ADN,36,20^FDTEST^FS^XZ"""

send_zpl(zpl5, "Minimal ZPL")

print("=" * 50)
print("Tests complete!")
print()
print("If no labels printed, check:")
print("1. Printer has labels loaded")
print("2. Printer is not in pause mode (check LED)")
print("3. Printer is not in an error state")
print("4. Try pressing the feed button to see if labels are queued")