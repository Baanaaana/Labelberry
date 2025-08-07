#!/bin/bash

echo "Testing with usblp module..."
echo "===================================="
echo

# Load usblp module
echo "1. Loading usblp module:"
sudo modprobe usblp
echo "   Module loaded"
sleep 2

# Check for device
echo
echo "2. Checking for device file:"
ls -la /dev/usblp* 2>/dev/null || echo "   No device file created"

# Check dmesg
echo
echo "3. Checking dmesg:"
dmesg | tail -5

# Try creating device manually
echo
echo "4. Trying to create device manually:"
sudo mknod /dev/usblp0 c 180 0 2>/dev/null && echo "   Device created" || echo "   Device already exists or failed"
sudo chmod 666 /dev/usblp0 2>/dev/null

# Check again
echo
echo "5. Checking device again:"
ls -la /dev/usblp* 2>/dev/null || echo "   Still no device"

# If device exists, try to print
if [ -e /dev/usblp0 ]; then
    echo
    echo "6. Device exists! Trying to print:"
    echo "^XA^FO50,50^A0N,40,40^FDDevice File Test^FS^XZ" > /dev/usblp0 2>/dev/null && echo "   ✓ Data sent to device" || echo "   ✗ Failed to send data"
else
    echo
    echo "6. No device file to test"
fi

echo
echo "===================================="
echo "Check if a label printed!"