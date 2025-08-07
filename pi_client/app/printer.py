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
                # Don't store device here to avoid holding it
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
        # Always clean up any stuck resources before printing
        self._emergency_cleanup()
        
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