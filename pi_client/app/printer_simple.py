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
        self.connect()
    
    def send_to_printer(self, zpl_data: str) -> bool:
        """Send ZPL data to the printer"""
        return self.print_zpl(zpl_data)
    
    def connect(self) -> bool:
        """Connect to printer - try device files first, then USB"""
        try:
            # Try all common device paths
            device_paths = [self.device_path, "/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
            for path in device_paths:
                if Path(path).exists():
                    self.device_path = path
                    self.is_connected = True
                    logger.info(f"Printer device found at {path}")
                    return True
            
            # No device file found, try USB directly
            logger.info("No device files found, trying USB direct connection...")
            
            ZEBRA_VENDOR_ID = 0x0A5F
            
            # Try to find Zebra printer
            self.usb_device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if self.usb_device:
                self.is_connected = True
                logger.info(f"Connected to Zebra printer via USB: {self.usb_device}")
                return True
            
            # Try any printer
            self.usb_device = usb.core.find(bDeviceClass=7)
            if self.usb_device:
                self.is_connected = True
                logger.info(f"Connected to generic printer via USB: {self.usb_device}")
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
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            if self.usb_device:
                return self._print_via_usb(zpl_content)
            else:
                return self._print_via_device(zpl_content)
        except Exception as e:
            logger.error(f"Print failed: {e}")
            self.is_connected = False
            # Try to reconnect and retry once
            if self.connect():
                try:
                    if self.usb_device:
                        return self._print_via_usb(zpl_content)
                    else:
                        return self._print_via_device(zpl_content)
                except:
                    pass
            return False
    
    def _print_via_usb(self, zpl_content: str) -> bool:
        """Print via USB using pyusb"""
        try:
            # Set configuration if needed
            try:
                cfg = self.usb_device.get_active_configuration()
            except usb.core.USBError:
                self.usb_device.set_configuration()
                cfg = self.usb_device.get_active_configuration()
            
            # Get first interface
            intf = cfg[(0, 0)]
            
            # Detach kernel driver if active
            if self.usb_device.is_kernel_driver_active(intf.bInterfaceNumber):
                self.usb_device.detach_kernel_driver(intf.bInterfaceNumber)
            
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
            ep_out.write(data)
            logger.info(f"Sent {len(data)} bytes via USB")
            return True
            
        except Exception as e:
            logger.error(f"USB print failed: {e}")
            return False
    
    def _print_via_device(self, zpl_content: str) -> bool:
        """Print via device file"""
        try:
            with open(self.device_path, 'wb') as printer:
                printer.write(zpl_content.encode('utf-8'))
            logger.info(f"Sent {len(zpl_content)} bytes to {self.device_path}")
            return True
        except Exception as e:
            logger.error(f"Device print failed: {e}")
            return False
    
    def get_status(self) -> dict:
        return {
            "connected": self.is_connected,
            "device_path": self.device_path,
            "type": "USB" if self.usb_device else "Device"
        }
    
    def test_print(self) -> bool:
        test_zpl = """^XA
^FO50,50^A0N,50,50^FDLabelBerry Test^FS
^FO50,150^A0N,30,30^FDPrinter Connected Successfully^FS
^FO50,200^A0N,25,25^FDTime: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """^FS
^XZ"""
        return self.print_zpl(test_zpl)
    
    def disconnect(self):
        if self.usb_device:
            usb.util.dispose_resources(self.usb_device)
        self.is_connected = False
        logger.info("Printer disconnected")