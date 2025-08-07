#!/bin/bash

# Simple LabelBerry update function for .bashrc
# Usage: lbupdate

labelberry-install() {
    echo "Installing LabelBerry Admin Server..."
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install-server.sh | sudo bash
}

labelberry-uninstall() {
    echo "Uninstalling LabelBerry Admin Server..."
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/uninstall-server.sh | sudo bash
}

printer-install() {
    echo "Installing LabelBerry Printer..."
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install-pi.sh | sudo bash
}

printer-uninstall() {
    echo "Uninstalling LabelBerry Printer..."
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/uninstall-pi.sh | sudo bash
}