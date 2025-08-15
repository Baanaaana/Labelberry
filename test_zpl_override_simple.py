#!/usr/bin/env python3
"""
Test script for ZPL override functionality (simplified)
"""

import re

def apply_zpl_overrides(zpl_content: str, config: dict) -> str:
    """Apply darkness and speed overrides to ZPL content"""
    try:
        if not config.get('override_settings', False):
            return zpl_content
            
        darkness = config.get('default_darkness', 15)
        speed = config.get('default_speed', 4)
        
        print(f"Applying ZPL overrides: darkness={darkness}, speed={speed}")
        
        # Remove existing ^MD (darkness) commands and add our own
        # ^MD command sets darkness (0-30)
        zpl_content = re.sub(r'\^MD\d+', '', zpl_content)
        
        # Remove existing ^PR (print rate/speed) commands
        # ^PR command sets print, slew, and backfeed speeds
        zpl_content = re.sub(r'\^PR\d+,\d+,\d+', '', zpl_content)
        zpl_content = re.sub(r'\^PR\d+', '', zpl_content)
        
        # Insert our settings right after ^XA (start of label)
        if '^XA' in zpl_content:
            # Add darkness and speed commands after ^XA
            override_commands = f"\n^MD{darkness}\n^PR{speed},{speed},{speed}\n"
            zpl_content = zpl_content.replace('^XA', f'^XA{override_commands}', 1)
            print(f"Inserted override commands: ^MD{darkness} and ^PR{speed}")
        else:
            print("No ^XA found in ZPL, cannot apply overrides")
        
        return zpl_content
        
    except Exception as e:
        print(f"Failed to apply ZPL overrides: {e}")
        return zpl_content  # Return original if override fails

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
    
    result1 = apply_zpl_overrides(test_zpl, config_no_override)
    
    print("Test 1 - Override DISABLED (should remain unchanged):")
    print(f"Config: override={config_no_override['override_settings']}, darkness={config_no_override['default_darkness']}, speed={config_no_override['default_speed']}")
    print("Result:")
    print(result1)
    assert result1 == test_zpl, "ZPL should not change when override is disabled"
    print("✓ Test 1 passed: ZPL unchanged when override disabled")
    print("\n" + "="*50 + "\n")
    
    # Test 2: With override
    config_with_override = {
        'override_settings': True,
        'default_darkness': 25,
        'default_speed': 8
    }
    
    result2 = apply_zpl_overrides(test_zpl, config_with_override)
    
    print("Test 2 - Override ENABLED (should replace ^MD and ^PR values):")
    print(f"Config: override={config_with_override['override_settings']}, darkness={config_with_override['default_darkness']}, speed={config_with_override['default_speed']}")
    print("Result:")
    print(result2)
    print("\n" + "="*50 + "\n")
    
    # Verify the changes
    md_match = re.search(r'\^MD(\d+)', result2)
    pr_match = re.search(r'\^PR(\d+),(\d+),(\d+)', result2)
    
    if md_match and md_match.group(1) == '25':
        print(f"✓ Darkness was correctly set to: {md_match.group(1)}")
    else:
        print(f"✗ Darkness not set correctly. Found: {md_match.group(1) if md_match else 'None'}")
    
    if pr_match and pr_match.group(1) == '8':
        print(f"✓ Speed was correctly set to: {pr_match.group(1)},{pr_match.group(2)},{pr_match.group(3)}")
    else:
        print(f"✗ Speed not set correctly. Found: {pr_match.groups() if pr_match else 'None'}")
    
    # Test 3: ZPL without existing commands
    test_zpl_clean = """^XA
^FO50,50^ADN,36,20^FDClean Label^FS
^XZ"""
    
    print("\n" + "="*50 + "\n")
    print("Test 3 - ZPL without existing ^MD/^PR commands:")
    print("Original:")
    print(test_zpl_clean)
    
    result3 = apply_zpl_overrides(test_zpl_clean, config_with_override)
    print("\nWith override:")
    print(result3)
    
    # Verify insertion
    if "^MD25" in result3 and "^PR8,8,8" in result3:
        print("\n✓ Commands were successfully inserted after ^XA")
    else:
        print("\n✗ Commands were not properly inserted")
    
    # Test 4: Ensure old commands are removed
    old_md_in_result = re.search(r'\^MD20', result2)
    old_pr_in_result = re.search(r'\^PR6,6,6', result2)
    
    print("\n" + "="*50 + "\n")
    print("Test 4 - Verify old commands are removed:")
    if not old_md_in_result and not old_pr_in_result:
        print("✓ Old ^MD20 and ^PR6,6,6 commands were successfully removed")
    else:
        if old_md_in_result:
            print("✗ Old ^MD20 command still present")
        if old_pr_in_result:
            print("✗ Old ^PR6,6,6 command still present")
    
    print("\n" + "="*50 + "\n")
    print("All tests completed!")

if __name__ == "__main__":
    test_zpl_override()