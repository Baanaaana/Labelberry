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
        try:
            if self.device_path.startswith("/dev/usb/"):
                self.usb_device = self._find_usb_printer()
                if self.usb_device:
                    self.is_connected = True
                    logger.info(f"Connected to USB printer: {self.usb_device}")
                    return True
            
            if Path(self.device_path).exists():
                self.is_connected = True
                logger.info(f"Printer device found at {self.device_path}")
                return True
            
            logger.error(f"Printer device not found at {self.device_path}")
            self.is_connected = False
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to printer: {e}")
            self.is_connected = False
            return False
    
    def _find_usb_printer(self):
        ZEBRA_VENDOR_ID = 0x0A5F
        
        printers = usb.core.find(find_all=True, bDeviceClass=7)
        
        for printer in printers:
            if printer.idVendor == ZEBRA_VENDOR_ID:
                return printer
        
        for printer in printers:
            return printer
        
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
            cfg = self.usb_device.get_active_configuration()
            intf = cfg[(0, 0)]
            
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            if ep_out is None:
                logger.error("No OUT endpoint found")
                return False
            
            ep_out.write(zpl_content.encode('utf-8'))
            logger.info("ZPL sent via USB successfully")
            return True
            
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