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
        self.is_connected = False
        # Check if printer exists on init
        self.connect()
    
    def send_to_printer(self, zpl_data: str) -> bool:
        """Send ZPL data to the printer"""
        return self.print_zpl(zpl_data)
    
    def connect(self) -> bool:
        """Check if printer is available"""
        try:
            # Check device files first (fastest method if they exist)
            device_paths = ["/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
            for path in device_paths:
                if Path(path).exists():
                    self.device_path = path
                    self.is_connected = True
                    logger.info(f"Printer device found at {path}")
                    return True
            
            # Check if USB device exists
            ZEBRA_VENDOR_ID = 0x0A5F
            device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if device:
                self.is_connected = True
                logger.info(f"Zebra printer found via USB")
                return True
            
            logger.error("No printer found via device files or USB")
            self.is_connected = False
            return False
            
        except Exception as e:
            logger.error(f"Failed to check printer: {e}")
            self.is_connected = False
            return False
    
    def print_zpl(self, zpl_content: str) -> bool:
        """Print ZPL content"""
        try:
            # Try device file first (if it exists)
            device_paths = ["/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
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
            
            # No device file worked, use USB directly with proper kernel driver handling
            logger.info("No device files available, using direct USB")
            return self._print_via_usb_with_driver_detach(zpl_content)
            
        except Exception as e:
            logger.error(f"Print failed: {e}")
            return False
    
    def _print_via_usb_with_driver_detach(self, zpl_content: str) -> bool:
        """Print via USB using Method 4: detach kernel driver"""
        device = None
        driver_reattach = False
        intf = None
        
        try:
            ZEBRA_VENDOR_ID = 0x0A5F
            
            # Find the device
            device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if not device:
                logger.error("No Zebra printer found via USB")
                return False
            
            # Set configuration
            try:
                device.set_configuration()
            except usb.core.USBError as e:
                # Already configured is OK
                if e.errno != 16:
                    logger.warning(f"Configuration warning: {e}")
            
            # Get interface
            cfg = device.get_active_configuration()
            intf = cfg[(0, 0)]
            
            # CRITICAL: Detach kernel driver if active
            if device.is_kernel_driver_active(intf.bInterfaceNumber):
                logger.debug("Detaching kernel driver")
                device.detach_kernel_driver(intf.bInterfaceNumber)
                driver_reattach = True
            
            # Claim interface
            usb.util.claim_interface(device, intf)
            
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
            bytes_written = ep_out.write(data, timeout=5000)
            logger.info(f"Sent {bytes_written} bytes via USB")
            
            # Release interface
            usb.util.release_interface(device, intf)
            
            # Reattach kernel driver if we detached it
            if driver_reattach:
                try:
                    device.attach_kernel_driver(intf.bInterfaceNumber)
                except:
                    pass  # Don't fail if reattach doesn't work
            
            return True
            
        except usb.core.USBError as e:
            logger.error(f"USB error: {e}")
            return False
        except Exception as e:
            logger.error(f"Print error: {e}")
            return False
        finally:
            # Clean up resources
            if device:
                try:
                    if intf:
                        usb.util.release_interface(device, intf)
                    if driver_reattach:
                        try:
                            device.attach_kernel_driver(intf.bInterfaceNumber)
                        except:
                            pass
                    usb.util.dispose_resources(device)
                except:
                    pass
    
    def get_status(self) -> dict:
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
        self.is_connected = False
        logger.info("Printer disconnected")