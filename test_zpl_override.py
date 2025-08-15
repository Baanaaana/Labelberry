#!/usr/bin/env python3
"""
Test script for ZPL override functionality
"""

import sys
import re
from pathlib import Path

# Add the project to path
sys.path.append(str(Path(__file__).parent))

from pi_client.app.printer import ZebraPrinter

def test_zpl_override():
    """Test the ZPL override functionality"""
    
    # Test ZPL with existing darkness and speed commands
    test_zpl = """^XA
^MD20
^PR6,6,6
^FO50,50^ADN,36,20^FDTest Label^FS
^FO50,100^BY2,2,40^BCN,,Y,N^FD123456^FS
^XZ"""
    
    print("Original ZPL:")
    print(test_zpl)
    print("\n" + "="*50 + "\n")
    
    # Test 1: Without override
    config_no_override = {
        'override_settings': False,
        'default_darkness': 10,
        'default_speed': 3
    }
    
    printer1 = ZebraPrinter(device_path="/dev/null", config=config_no_override)
    result1 = printer1._apply_zpl_overrides(test_zpl)
    
    print("Test 1 - Override DISABLED (should remain unchanged):")
    print(f"Config: override={config_no_override['override_settings']}, darkness={config_no_override['default_darkness']}, speed={config_no_override['default_speed']}")
    print("Result:")
    print(result1)
    print("\n" + "="*50 + "\n")
    
    # Test 2: With override
    config_with_override = {
        'override_settings': True,
        'default_darkness': 25,
        'default_speed': 8
    }
    
    printer2 = ZebraPrinter(device_path="/dev/null", config=config_with_override)
    result2 = printer2._apply_zpl_overrides(test_zpl)
    
    print("Test 2 - Override ENABLED (should replace ^MD and ^PR values):")
    print(f"Config: override={config_with_override['override_settings']}, darkness={config_with_override['default_darkness']}, speed={config_with_override['default_speed']}")
    print("Result:")
    print(result2)
    print("\n" + "="*50 + "\n")
    
    # Verify the changes
    md_match = re.search(r'\^MD(\d+)', result2)
    pr_match = re.search(r'\^PR(\d+),(\d+),(\d+)', result2)
    
    if md_match:
        print(f"✓ Darkness was set to: {md_match.group(1)}")
    else:
        print("✗ No ^MD command found")
    
    if pr_match:
        print(f"✓ Speed was set to: {pr_match.group(1)},{pr_match.group(2)},{pr_match.group(3)}")
    else:
        print("✗ No ^PR command found")
    
    # Test 3: ZPL without existing commands
    test_zpl_clean = """^XA
^FO50,50^ADN,36,20^FDClean Label^FS
^XZ"""
    
    print("\n" + "="*50 + "\n")
    print("Test 3 - ZPL without existing ^MD/^PR commands:")
    print("Original:")
    print(test_zpl_clean)
    
    result3 = printer2._apply_zpl_overrides(test_zpl_clean)
    print("\nWith override:")
    print(result3)
    
    # Verify insertion
    if "^MD25" in result3 and "^PR8,8,8" in result3:
        print("\n✓ Commands were successfully inserted after ^XA")
    else:
        print("\n✗ Commands were not properly inserted")

if __name__ == "__main__":
    test_zpl_override()