#!/usr/bin/env python3
"""
Test all possible USB communication methods
"""
import usb.core
import usb.util
import time
import sys

print("Testing ALL USB communication methods")
print("=" * 50)

ZEBRA_VENDOR_ID = 0x0A5F

# Find the Zebra printer
device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
if not device:
    print("ERROR: No Zebra printer found!")
    exit(1)

print(f"Found: {device.manufacturer} {device.product}")
print()

test_zpl = b"^XA^FO50,50^A0N,40,40^FDTest^FS^XZ"

def test_method_1():
    """Method 1: Direct write without any setup"""
    print("Method 1: Direct write without setup")
    print("-" * 30)
    try:
        device.write(0x01, test_zpl, timeout=5000)
        print("✓ SUCCESS!")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_method_2():
    """Method 2: Set config then write"""
    print("\nMethod 2: Set configuration first")
    print("-" * 30)
    try:
        try:
            device.set_configuration()
        except:
            pass
        device.write(0x01, test_zpl, timeout=5000)
        print("✓ SUCCESS!")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_method_3():
    """Method 3: Full setup with interface claim"""
    print("\nMethod 3: Full setup with interface claim")
    print("-" * 30)
    try:
        # Set configuration
        try:
            device.set_configuration()
        except:
            pass
        
        cfg = device.get_active_configuration()
        intf = cfg[(0, 0)]
        
        # DON'T detach kernel driver - maybe it needs it
        
        # Claim interface
        usb.util.claim_interface(device, intf)
        
        # Find endpoint
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        
        if ep_out:
            bytes_written = ep_out.write(test_zpl, timeout=5000)
            print(f"✓ SUCCESS! Wrote {bytes_written} bytes")
            usb.util.release_interface(device, intf)
            return True
        else:
            print("✗ No endpoint found")
            return False
            
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_method_4():
    """Method 4: With kernel driver detach"""
    print("\nMethod 4: With kernel driver detach")
    print("-" * 30)
    try:
        # Set configuration
        try:
            device.set_configuration()
        except:
            pass
        
        cfg = device.get_active_configuration()
        intf = cfg[(0, 0)]
        
        # Detach kernel driver
        if device.is_kernel_driver_active(intf.bInterfaceNumber):
            device.detach_kernel_driver(intf.bInterfaceNumber)
            print("Kernel driver detached")
        
        # Claim interface
        usb.util.claim_interface(device, intf)
        
        # Find endpoint
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        
        if ep_out:
            bytes_written = ep_out.write(test_zpl, timeout=5000)
            print(f"✓ SUCCESS! Wrote {bytes_written} bytes")
            usb.util.release_interface(device, intf)
            return True
        else:
            print("✗ No endpoint found")
            return False
            
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_method_5():
    """Method 5: Using control transfer"""
    print("\nMethod 5: Using control transfer")
    print("-" * 30)
    try:
        # Try sending via control transfer (some printers need this)
        device.ctrl_transfer(0x21, 0x09, 0x0200, 0, test_zpl)
        print("✓ SUCCESS!")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

# Run all tests
results = []
results.append(("Direct write", test_method_1()))
results.append(("With config", test_method_2()))
results.append(("Full setup", test_method_3()))
results.append(("With driver detach", test_method_4()))
results.append(("Control transfer", test_method_5()))

print("\n" + "=" * 50)
print("RESULTS:")
for name, success in results:
    status = "✓ SUCCESS" if success else "✗ FAILED"
    print(f"  {name}: {status}")

if any(r[1] for r in results):
    print("\nAt least one method worked! Check if a label printed.")
else:
    print("\nAll methods failed. This might be a hardware or firmware issue.")
    print("\nTry:")
    print("1. Disconnect and reconnect the USB cable")
    print("2. Power cycle the printer")
    print("3. Check printer firmware version")