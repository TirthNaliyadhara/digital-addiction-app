#!/usr/bin/env python3
"""
Debug script to examine ADB data parsing issues.
Run this to see what raw data is being extracted from the device.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from integrations.adb_integration import (
    get_adb_status, get_adb_device_info, 
    _get_uid_package_maps, _parse_usagestats_7days,
    _adb_text, diagnose_adb_data_fetch
)

def main():
    print("=== ADB Data Debug Analysis ===\n")
    
    # Check ADB status
    status, raw = get_adb_status()
    print(f"ADB Status: {status}")
    print(f"Raw output: {raw[:200]}...\n")
    
    if status != "connected":
        print("❌ Device not connected. Please connect your Android device with USB debugging enabled.")
        return
    
    # Get device info
    device_info = get_adb_device_info()
    print(f"Device: {device_info}\n")
    
    # Get package maps
    print("=== Package Analysis ===")
    uid_map, third_party = _get_uid_package_maps()
    print(f"Total packages found: {len(uid_map)}")
    print(f"Third-party packages: {len(third_party)}")
    print(f"First 10 third-party apps: {list(third_party)[:10]}\n")
    
    # Get raw usagestats
    print("=== Raw UsageStats Sample ===")
    raw_usagestats = _adb_text("shell", "dumpsys", "usagestats", timeout=30)
    print(f"Total usagestats length: {len(raw_usagestats)} characters")
    print("First 1000 characters:")
    print(raw_usagestats[:1000])
    print("\n" + "="*50 + "\n")
    
    # Look for specific patterns
    print("=== Pattern Analysis ===")
    lines = raw_usagestats.split('\n')
    package_lines = [line for line in lines if 'package=' in line.lower()]
    time_lines = [line for line in lines if 'totaltimeinforeground' in line.lower()]
    
    print(f"Found {len(package_lines)} package lines")
    print(f"Found {len(time_lines)} time lines")
    
    if package_lines:
        print("Sample package lines:")
        for line in package_lines[:5]:
            print(f"  {line}")
    
    if time_lines:
        print("Sample time lines:")
        for line in time_lines[:5]:
            print(f"  {line}")
    
    print("\n=== Parsing Results ===")
    try:
        parsed_rows = _parse_usagestats_7days(uid_map, third_party, debug=True)
        print(f"Parsed {len(parsed_rows)} rows")
        
        if parsed_rows:
            print("Sample parsed rows:")
            for row in parsed_rows[:5]:
                print(f"  {row}")
        else:
            print("❌ No rows parsed from usagestats!")
            
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== BatteryStats Deep Analysis ===")
    bs_output = _adb_text("shell", "dumpsys", "batterystats", "--charged", timeout=30)
    print("Full batterystats output:")
    print(bs_output)
    
    print("\n=== Full Diagnostic ===")
    diagnostic = diagnose_adb_data_fetch()
    for key, value in diagnostic.items():
        if key == 'errors':
            print(f"{key}: {value}")
        elif key == 'third_party_packages':
            print(f"{key}: {len(value)} packages - {value[:5]}")
        else:
            print(f"{key}: {str(value)[:200]}...")

if __name__ == "__main__":
    main()
