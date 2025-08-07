import os
import time
import logging
from pathlib import Path
from typing import Optional, List
import usb.core
import usb.util


logger = logging.getLogger(__name__)


class ZebraPrinter:
    def __init__(self, device_path: str = "/dev/usb/lp0"):
        self.device_path = device_path
        self.usb_device = None
        self.is_connected = False
        # Don't auto-connect on init - connect only when printing
    
    def send_to_printer(self, zpl_data: str) -> bool:
        """Send ZPL data to the printer"""
        return self.print_zpl(zpl_data)
    
    def connect(self) -> bool:
        """Check if printer is available"""
        try:
            # Check device files first
            device_paths = [self.device_path, "/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
            for path in device_paths:
                if Path(path).exists():
                    self.device_path = path
                    self.is_connected = True
                    logger.info(f"Printer device found at {path}")
                    return True
            
            # Check if USB device exists (but don't hold it)
            ZEBRA_VENDOR_ID = 0x0A5F
            device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if device:
                self.is_connected = True
                logger.info(f"Zebra printer found via USB")
                # Important: Don't store the device, just check it exists
                return True
            
            logger.error("No printer found via device files or USB")
            self.is_connected = False
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}")
            self.is_connected = False
            return False
    
    def print_zpl(self, zpl_content: str) -> bool:
        """Print ZPL content"""
        try:
            # Try device file first
            device_paths = [self.device_path, "/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
            for path in device_paths:
                if Path(path).exists():
                    try:
                        with open(path, 'wb') as printer:
                            printer.write(zpl_content.encode('utf-8'))
                        logger.info(f"Sent {len(zpl_content)} bytes to {path}")
                        return True
                    except Exception as e:
                        logger.debug(f"Failed to print to {path}: {e}")
                        continue
            
            # No device file worked, try USB
            logger.info("No device files available, trying USB direct")
            return self._print_via_usb_direct(zpl_content)
            
        except Exception as e:
            logger.error(f"Print failed: {e}")
            return False
    
    def _print_via_usb_direct(self, zpl_content: str) -> bool:
        """Print via USB - connect, print, disconnect immediately"""
        device = None
        try:
            ZEBRA_VENDOR_ID = 0x0A5F
            
            # Find the device
            device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if not device:
                logger.error("No Zebra printer found via USB")
                return False
            
            # Configure device
            try:
                cfg = device.get_active_configuration()
            except usb.core.USBError:
                device.set_configuration()
                cfg = device.get_active_configuration()
            
            # Get interface
            intf = cfg[(0, 0)]
            
            # Detach kernel driver if needed
            reattach = False
            if device.is_kernel_driver_active(intf.bInterfaceNumber):
                device.detach_kernel_driver(intf.bInterfaceNumber)
                reattach = True
            
            # Find OUT endpoint
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            if not ep_out:
                logger.error("No OUT endpoint found")
                return False
            
            # Send data
            data = zpl_content.encode('utf-8')
            bytes_written = ep_out.write(data)
            logger.info(f"Sent {bytes_written} bytes via USB")
            
            # Reattach kernel driver if we detached it
            if reattach:
                usb.util.dispose_resources(device)
                device.attach_kernel_driver(intf.bInterfaceNumber)
            
            return True
            
        except Exception as e:
            logger.error(f"USB print failed: {e}")
            return False
        finally:
            # Always release the USB device
            if device:
                try:
                    usb.util.dispose_resources(device)
                except:
                    pass
    
    def get_status(self) -> dict:
        # Quick check without holding resources
        self.connect()
        return {
            "connected": self.is_connected,
            "device_path": self.device_path,
            "type": "USB/Device"
        }
    
    def test_print(self) -> bool:
        test_zpl = """^XA
^FO50,50^A0N,50,50^FDLabelBerry Test^FS
^FO50,150^A0N,30,30^FDPrinter Connected Successfully^FS
^FO50,200^A0N,25,25^FDTime: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """^FS
^XZ"""
        return self.print_zpl(test_zpl)
    
    def disconnect(self):
        # Nothing to disconnect since we don't hold resources
        self.is_connected = False
        logger.info("Printer disconnected")