#!/usr/bin/env python3
"""
Debug script to test different printing methods directly
"""
import sys
import os
import time
from pathlib import Path

def test_device_file(device_path="/dev/usblp0"):
    """Test printing via device file"""
    print(f"Testing device file: {device_path}")
    
    if not Path(device_path).exists():
        print(f"  ERROR: Device file {device_path} does not exist")
        return False
    
    test_zpl = """^XA
^FO50,50^A0N,50,50^FDDebug Test^FS
^FO50,150^A0N,30,30^FDDevice File Method^FS
^FO50,200^A0N,25,25^FDTime: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """^FS
^XZ"""
    
    try:
        with open(device_path, 'wb') as printer:
            printer.write(test_zpl.encode('utf-8'))
            printer.flush()
        print(f"  SUCCESS: Sent {len(test_zpl)} bytes to {device_path}")
        return True
    except Exception as e:
        print(f"  ERROR: Failed to write to device: {e}")
        return False


def test_usb_library():
    """Test printing via pyusb"""
    print("Testing USB library (pyusb)")
    
    try:
        import usb.core
        import usb.util
    except ImportError:
        print("  ERROR: pyusb not installed")
        return False
    
    ZEBRA_VENDOR_ID = 0x0A5F
    
    # Find Zebra printer
    device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
    if not device:
        print("  ERROR: No Zebra printer found via USB")
        return False
    
    print(f"  Found Zebra printer: {device}")
    
    test_zpl = """^XA
^FO50,50^A0N,50,50^FDDebug Test^FS
^FO50,150^A0N,30,30^FDUSB Library Method^FS
^FO50,200^A0N,25,25^FDTime: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """^FS
^XZ"""
    
    try:
        # Configure device
        try:
            cfg = device.get_active_configuration()
        except usb.core.USBError:
            device.set_configuration()
            cfg = device.get_active_configuration()
        
        # Get interface
        intf = cfg[(0, 0)]
        
        # Detach kernel driver if needed
        if device.is_kernel_driver_active(intf.bInterfaceNumber):
            print("  Detaching kernel driver...")
            device.detach_kernel_driver(intf.bInterfaceNumber)
        
        # Find OUT endpoint
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        
        if not ep_out:
            print("  ERROR: No OUT endpoint found")
            return False
        
        # Send data
        data = test_zpl.encode('utf-8')
        bytes_written = ep_out.write(data)
        print(f"  SUCCESS: Sent {bytes_written} bytes via USB")
        return True
        
    except Exception as e:
        print(f"  ERROR: USB printing failed: {e}")
        return False


def test_echo_command(device_path="/dev/usblp0"):
    """Test using echo command"""
    print(f"Testing echo command to {device_path}")
    
    if not Path(device_path).exists():
        print(f"  ERROR: Device file {device_path} does not exist")
        return False
    
    test_zpl = """^XA
^FO50,50^A0N,50,50^FDDebug Test^FS
^FO50,150^A0N,30,30^FDEcho Command Method^FS
^FO50,200^A0N,25,25^FDTime: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """^FS
^XZ"""
    
    import subprocess
    try:
        result = subprocess.run(
            f'echo "{test_zpl}" > {device_path}',
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  SUCCESS: Echo command executed")
            return True
        else:
            print(f"  ERROR: Echo command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ERROR: Failed to run echo command: {e}")
        return False


def main():
    print("=" * 50)
    print("LabelBerry Printer Debug Tool")
    print("=" * 50)
    print()
    
    # Check for device files
    print("Checking for printer device files...")
    device_paths = ["/dev/usblp0", "/dev/usb/lp0", "/dev/lp0"]
    found_devices = []
    for path in device_paths:
        if Path(path).exists():
            print(f"  ✓ Found: {path}")
            found_devices.append(path)
        else:
            print(f"  ✗ Not found: {path}")
    print()
    
    # Check USB devices
    print("Checking USB devices...")
    try:
        import subprocess
        result = subprocess.run(["lsusb"], capture_output=True, text=True)
        zebra_lines = [line for line in result.stdout.split('\n') if 'zebra' in line.lower()]
        if zebra_lines:
            print("  Found Zebra devices:")
            for line in zebra_lines:
                print(f"    {line}")
        else:
            print("  No Zebra devices found via lsusb")
    except:
        print("  Could not run lsusb")
    print()
    
    # Check kernel modules
    print("Checking kernel modules...")
    try:
        import subprocess
        result = subprocess.run(["lsmod"], capture_output=True, text=True)
        if "usblp" in result.stdout:
            print("  ✓ usblp module is loaded")
        else:
            print("  ✗ usblp module is NOT loaded")
            print("    Run: sudo modprobe usblp")
    except:
        print("  Could not check kernel modules")
    print()
    
    # Run tests
    print("Running print tests...")
    print("-" * 30)
    
    if found_devices:
        # Test device file method
        for device in found_devices:
            if test_device_file(device):
                print("  Check if a label printed!")
                time.sleep(2)
    
    # Test USB library method
    if test_usb_library():
        print("  Check if a label printed!")
        time.sleep(2)
    
    # Test echo command
    if found_devices:
        if test_echo_command(found_devices[0]):
            print("  Check if a label printed!")
    
    print()
    print("=" * 50)
    print("Debug tests complete!")
    print("If no labels printed, check:")
    print("1. Printer is powered on")
    print("2. Printer has labels loaded")
    print("3. Printer is not in pause/error state")
    print("4. USB cable is properly connected")
    print("=" * 50)


if __name__ == "__main__":
    main()