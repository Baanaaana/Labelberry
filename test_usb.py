#!/usr/bin/env python3
"""
Test USB printer detection
"""
import usb.core
import usb.util

print("Testing USB printer detection...")
print("=" * 50)

ZEBRA_VENDOR_ID = 0x0A5F

# Method 1: Find Zebra by vendor ID
print("\n1. Looking for Zebra printer by vendor ID (0x0A5F)...")
zebra = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
if zebra:
    print(f"   ✓ Found: {zebra}")
    print(f"   Vendor: {hex(zebra.idVendor)}, Product: {hex(zebra.idProduct)}")
else:
    print("   ✗ Not found")

# Method 2: Find all Zebra devices
print("\n2. Looking for ALL Zebra devices...")
zebra_devices = list(usb.core.find(find_all=True, idVendor=ZEBRA_VENDOR_ID))
print(f"   Found {len(zebra_devices)} Zebra device(s)")
for i, dev in enumerate(zebra_devices):
    print(f"   Device {i}: {dev}")

# Method 3: Find printer class devices
print("\n3. Looking for printer class devices (class 7)...")
printers = list(usb.core.find(find_all=True, bDeviceClass=7))
print(f"   Found {len(printers)} printer(s)")
for i, printer in enumerate(printers):
    print(f"   Printer {i}: Vendor={hex(printer.idVendor)}, Product={hex(printer.idProduct)}")

# Method 4: Find ALL USB devices and filter
print("\n4. Looking through ALL USB devices...")
all_devices = list(usb.core.find(find_all=True))
print(f"   Total USB devices: {len(all_devices)}")
zebra_found = False
for dev in all_devices:
    if dev.idVendor == ZEBRA_VENDOR_ID:
        print(f"   ✓ Found Zebra: {dev}")
        print(f"     Vendor: {hex(dev.idVendor)}, Product: {hex(dev.idProduct)}")
        print(f"     Bus: {dev.bus}, Address: {dev.address}")
        zebra_found = True
if not zebra_found:
    print("   ✗ No Zebra devices found in all USB devices")

print("\n" + "=" * 50)
print("Test complete!")