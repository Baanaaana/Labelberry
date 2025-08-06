#!/bin/bash

# Simple LabelBerry update function for .bashrc
# Usage: lbupdate

lbupdate() {
    echo "Updating LabelBerry Admin Server..."
    curl -fsSL https://raw.githubusercontent.com/Baanaaana/LabelBerry/main/install-server.sh | sudo bash
}