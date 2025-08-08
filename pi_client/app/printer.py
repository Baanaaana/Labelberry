import os
import time
import logging
from pathlib import Path
from typing import Optional, List
import usb.core
import usb.util
import atexit
import signal


logger = logging.getLogger(__name__)


class ZebraPrinter:
    def __init__(self, device_path: str = "/dev/usb/lp0"):
        self.device_path = device_path
        self.is_connected = False
        self._active_device = None
        self._active_interface = None
        self._driver_was_detached = False
        
        # Register cleanup handlers
        atexit.register(self._emergency_cleanup)
        signal.signal(signal.SIGTERM, self._signal_cleanup)
        signal.signal(signal.SIGINT, self._signal_cleanup)
        
        # Check if printer exists on init
        self.connect()
    
    def _signal_cleanup(self, signum, frame):
        """Clean up on signal"""
        logger.info(f"Received signal {signum}, cleaning up USB resources")
        self._emergency_cleanup()
    
    def _emergency_cleanup(self):
        """Emergency cleanup of USB resources"""
        try:
            if self._active_device:
                if self._active_interface:
                    try:
                        usb.util.release_interface(self._active_device, self._active_interface)
                    except:
                        pass
                if self._driver_was_detached and self._active_interface:
                    try:
                        self._active_device.attach_kernel_driver(self._active_interface.bInterfaceNumber)
                    except:
                        pass
                try:
                    usb.util.dispose_resources(self._active_device)
                except:
                    pass
                self._active_device = None
                self._active_interface = None
                self._driver_was_detached = False
        except:
            pass
    
    def send_to_printer(self, zpl_data: str) -> bool:
        """Send ZPL data to the printer"""
        logger.info(f"=== PRINT JOB START ===")
        logger.info(f"Printer instance device path: {self.device_path}")
        logger.info(f"ZPL data length: {len(zpl_data)} bytes")
        
        result = self.print_zpl(zpl_data)
        
        logger.info(f"=== PRINT JOB END (Success: {result}) ===")
        return result
    
    def connect(self) -> bool:
        """Check if printer is available"""
        try:
            # If a specific device path was provided, check if it exists
            if self.device_path and self.device_path != "auto":
                if Path(self.device_path).exists():
                    self.is_connected = True
                    logger.info(f"Printer device found at configured path: {self.device_path}")
                    return True
                else:
                    logger.warning(f"Configured device path {self.device_path} does not exist")
                    # Continue to USB fallback instead of failing immediately
            
            # Check device files first (fastest method if they exist)
            device_paths = ["/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
            for path in device_paths:
                if Path(path).exists():
                    # Only update device_path if it was "auto" or not set
                    if not self.device_path or self.device_path == "auto":
                        self.device_path = path
                    self.is_connected = True
                    logger.info(f"Printer device found at {path}")
                    return True
            
            # Check if USB device exists (fallback for when device files don't exist)
            ZEBRA_VENDOR_ID = 0x0A5F
            device = usb.core.find(idVendor=ZEBRA_VENDOR_ID)
            if device:
                self.is_connected = True
                logger.info(f"Zebra printer found via USB (will use USB fallback for printing)")
                # Keep the configured device_path for index extraction during print
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
        logger.info(f"print_zpl called for device {self.device_path}")
        logger.info(f"ZPL content length: {len(zpl_content)} bytes")
        logger.info(f"First 100 chars of ZPL: {zpl_content[:100]}")
        
        # Always clean up any stuck resources before printing
        self._emergency_cleanup()
        
        try:
            # First try the specific device path assigned to this printer
            if self.device_path and self.device_path != "auto":
                if Path(self.device_path).exists():
                    try:
                        logger.info(f"Attempting to print to assigned device: {self.device_path}")
                        # Simple direct write - most reliable method
                        with open(self.device_path, 'wb') as printer:
                            data = zpl_content.encode('utf-8')
                            bytes_written = printer.write(data)
                            printer.flush()
                            logger.info(f"Successfully sent {bytes_written} bytes to {self.device_path}")
                            return True
                    except Exception as e:
                        logger.error(f"Failed to print to assigned device {self.device_path}: {e}")
                        # Continue to fallback methods
                else:
                    logger.warning(f"Assigned device {self.device_path} does not exist")
            
            # Try common device paths as fallback
            device_paths = ["/dev/usb/lp0", "/dev/usblp0", "/dev/lp0"]
            for path in device_paths:
                if path != self.device_path and Path(path).exists():  # Don't retry the same path
                    try:
                        logger.info(f"Trying fallback device: {path}")
                        with open(path, 'wb') as printer:
                            data = zpl_content.encode('utf-8')
                            bytes_written = printer.write(data)
                            printer.flush()
                            logger.info(f"Successfully sent {bytes_written} bytes to {path}")
                            return True
                    except Exception as e:
                        logger.error(f"Failed to print to {path}: {e}")
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
            
            # Extract printer index from device path if available
            # Handles: /dev/usb/lp1, /dev/usblp1, /dev/lp1 -> index 1
            printer_index = 0
            if self.device_path:
                try:
                    import re
                    # Match patterns like lp0, lp1, usblp0, usblp1
                    match = re.search(r'lp(\d+)', self.device_path)
                    if match:
                        printer_index = int(match.group(1))
                        logger.info(f"Extracted index {printer_index} from device path {self.device_path}")
                        logger.info(f"Looking for USB printer at index {printer_index}")
                except Exception as e:
                    logger.warning(f"Could not extract index from {self.device_path}: {e}")
            
            # Find all Zebra devices
            devices = list(usb.core.find(find_all=True, idVendor=ZEBRA_VENDOR_ID))
            
            if not devices:
                logger.error("No Zebra printers found via USB")
                return False
            
            if len(devices) > 1:
                logger.info(f"Found {len(devices)} Zebra printers via USB")
            
            # Select the device based on index
            if printer_index < len(devices):
                device = devices[printer_index]
                logger.info(f"Using USB printer at index {printer_index}")
            else:
                logger.warning(f"Printer index {printer_index} not found, using first available")
                device = devices[0]
            
            if not device:
                logger.error("No Zebra printer found via USB")
                return False
            
            # Store for emergency cleanup
            self._active_device = device
            
            # Reset device if it seems stuck
            try:
                device.reset()
                time.sleep(0.1)
            except:
                pass  # Reset might fail but that's OK
            
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
            self._active_interface = intf
            
            # CRITICAL: Detach kernel driver if active
            if device.is_kernel_driver_active(intf.bInterfaceNumber):
                logger.debug("Detaching kernel driver")
                device.detach_kernel_driver(intf.bInterfaceNumber)
                driver_reattach = True
                self._driver_was_detached = True
            
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
            
            # Success - clean up properly
            usb.util.release_interface(device, intf)
            
            if driver_reattach:
                try:
                    device.attach_kernel_driver(intf.bInterfaceNumber)
                except:
                    pass
            
            usb.util.dispose_resources(device)
            
            # Clear stored references
            self._active_device = None
            self._active_interface = None
            self._driver_was_detached = False
            
            return True
            
        except usb.core.USBError as e:
            logger.error(f"USB error: {e}")
            if e.errno == 16:  # Resource busy
                logger.info("USB device busy, trying to reset")
                try:
                    if device:
                        device.reset()
                except:
                    pass
            return False
        except Exception as e:
            logger.error(f"Print error: {e}")
            return False
        finally:
            # Always clean up
            try:
                if device:
                    if intf:
                        try:
                            usb.util.release_interface(device, intf)
                        except:
                            pass
                    if driver_reattach:
                        try:
                            device.attach_kernel_driver(intf.bInterfaceNumber)
                        except:
                            pass
                    try:
                        usb.util.dispose_resources(device)
                    except:
                        pass
            except:
                pass
            
            # Clear stored references
            self._active_device = None
            self._active_interface = None
            self._driver_was_detached = False
    
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
        self._emergency_cleanup()
        self.is_connected = False
        logger.info("Printer disconnected")