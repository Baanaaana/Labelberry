#!/bin/bash

echo "Fixing USB printer access..."
echo "===================================="
echo

echo "1. Current usblp status:"
lsmod | grep usblp
echo

echo "2. Removing usblp module (this will allow direct USB access):"
sudo rmmod usblp
echo "   usblp module removed"
echo

echo "3. Verifying module is unloaded:"
lsmod | grep usblp || echo "   ✓ usblp module is not loaded"
echo

echo "4. Removing usblp from auto-load:"
sudo sed -i '/^usblp$/d' /etc/modules
echo "   ✓ Removed from /etc/modules"
echo

echo "5. Blacklisting usblp module to prevent auto-loading:"
echo "blacklist usblp" | sudo tee /etc/modprobe.d/blacklist-usblp.conf
echo "   ✓ Module blacklisted"
echo

echo "===================================="
echo "Fix complete!"
echo
echo "The usblp module was preventing direct USB access."
echo "Now pyusb should be able to communicate with the printer."
echo
echo "Test with: sudo /opt/labelberry/venv/bin/python test_simple_print.py"