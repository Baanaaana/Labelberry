import os
import time
import logging
from pathlib import Path
from typing import Optional, List
import usb.core
import usb.util


logger = logging.getLogger(__name__)


class ZebraPrinter:
    def __init__(self, device_path: str = "/dev/usblp0"):
        self.device_path = device_path
        self.usb_device = None
        self.is_connected = False
        self.connect()
    
    def send_to_printer(self, zpl_data: str) -> bool:
        """Send ZPL data to the printer"""
        return self.print_zpl(zpl_data)
    
    def connect(self) -> bool:
        try:
            # First try to find via USB library (most reliable for Zebra printers)
            self.usb_device = self._find_usb_printer()
            if self.usb_device:
                self.is_connected = True
                logger.info(f"Connected to USB printer via pyusb: {self.usb_device}")
                return True
            
            # Then check if the device path exists
            if Path(self.device_path).exists():
                self.is_connected = True
                logger.info(f"Printer device found at {self.device_path}")
                return True
            
            # Try common USB printer paths
            common_paths = ["/dev/usblp0", "/dev/usb/lp0", "/dev/lp0"]
            for path in common_paths:
                if Path(path).exists():
                    self.device_path = path
                    self.is_connected = True
                    logger.info(f"Printer device found at {path}")
                    return True
            
            logger.warning(f"Printer device not found at {self.device_path} or common paths, but may still work via USB")
            # Even if device file doesn't exist, we might have USB connection
            if self.usb_device:
                self.is_connected = True
                return True
            
            self.is_connected = False
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}")
            self.is_connected = False
            return False
    
    def _find_usb_printer(self):
        ZEBRA_VENDOR_ID = 0x0A5F
        
        try:
            # First look for Zebra printers specifically
            zebra_printer = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if zebra_printer:
                logger.info(f"Found Zebra printer: {zebra_printer}")
                # Try to configure the device
                try:
                    zebra_printer.set_configuration()
                except usb.core.USBError as e:
                    if e.errno != 16:  # Device is not busy
                        logger.warning(f"Could not set configuration: {e}")
                return zebra_printer
            
            # If no Zebra found, look for any printer class device
            printers = usb.core.find(find_all=True, bDeviceClass=7)
            for printer in printers:
                logger.info(f"Found printer class device: {printer}")
                try:
                    printer.set_configuration()
                except usb.core.USBError as e:
                    if e.errno != 16:
                        logger.warning(f"Could not set configuration: {e}")
                return printer
            
            # Also check for devices that might not be class 7 but are Zebra
            all_zebra = usb.core.find(find_all=True, idVendor=ZEBRA_VENDOR_ID)
            for device in all_zebra:
                logger.info(f"Found Zebra device (non-printer class): {device}")
                try:
                    device.set_configuration()
                except usb.core.USBError as e:
                    if e.errno != 16:
                        logger.warning(f"Could not set configuration: {e}")
                return device
            
        except Exception as e:
            logger.error(f"Error finding USB printer: {e}")
        
        return None
    
    def print_zpl(self, zpl_content: str) -> bool:
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
            return False
    
    def _print_via_usb(self, zpl_content: str) -> bool:
        try:
            # Ensure device is configured
            try:
                cfg = self.usb_device.get_active_configuration()
            except usb.core.USBError:
                self.usb_device.set_configuration()
                cfg = self.usb_device.get_active_configuration()
            
            # Find the first interface
            intf = cfg[(0, 0)]
            
            # Find the OUT endpoint
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            if ep_out is None:
                logger.error("No OUT endpoint found")
                return False
            
            # Send the ZPL data
            data = zpl_content.encode('utf-8')
            bytes_written = ep_out.write(data)
            logger.info(f"ZPL sent via USB successfully ({bytes_written} bytes)")
            return True
            
        except usb.core.USBError as e:
            if e.errno == 16:  # Device busy
                logger.warning("USB device busy, trying alternative method")
                # Try to reset and retry
                try:
                    self.usb_device.reset()
                    time.sleep(0.5)
                    return self._print_via_usb(zpl_content)
                except:
                    pass
            logger.error(f"USB print failed: {e}")
            return False
        except Exception as e:
            logger.error(f"USB print failed: {e}")
            return False
    
    def _print_via_device(self, zpl_content: str) -> bool:
        try:
            with open(self.device_path, 'wb') as printer:
                printer.write(zpl_content.encode('utf-8'))
            logger.info(f"ZPL sent to {self.device_path} successfully")
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