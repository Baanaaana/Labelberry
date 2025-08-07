#!/bin/bash

echo "Checking for printer device files..."
echo "===================================="
echo

echo "1. Checking /dev/usb/lp* devices:"
ls -la /dev/usb/lp* 2>/dev/null || echo "   No /dev/usb/lp* devices found"
echo

echo "2. Checking /dev/usblp* devices:"
ls -la /dev/usblp* 2>/dev/null || echo "   No /dev/usblp* devices found"
echo

echo "3. Checking /dev/lp* devices:"
ls -la /dev/lp* 2>/dev/null || echo "   No /dev/lp* devices found"
echo

echo "4. Checking loaded kernel modules:"
lsmod | grep -E "usblp|lp" || echo "   No lp/usblp modules loaded"
echo

echo "5. Checking dmesg for printer messages:"
dmesg | grep -i "usb.*print" | tail -5
echo

echo "6. Trying to load usblp module:"
sudo modprobe usblp 2>/dev/null && echo "   usblp module loaded" || echo "   Failed to load usblp"
echo

echo "7. Checking again for device files after module load:"
ls -la /dev/usb/lp* /dev/usblp* 2>/dev/null || echo "   Still no device files"
echo

echo "8. USB devices:"
lsusb | grep -i zebra

echo
echo "===================================="
echo "If no device files exist, we need to use direct USB access"
echo "If device files exist, we should use those instead"