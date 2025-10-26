"""
Test script for Active NFC Devices API
Run this to see if the endpoint works
"""

import requests
import json
import urllib3

# Disable SSL warnings for self-signed certificate
urllib3.disable_warnings()

# Test the active devices endpoint
url = "https://192.168.1.84:5443/api/nfc/devices/active"

try:
    response = requests.get(url, verify=False)
    
    print("=" * 60)
    print("ACTIVE NFC DEVICES TEST")
    print("=" * 60)
    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse Text: {response.text}")
    if response.text:
        try:
            print(f"\nResponse JSON:")
            print(json.dumps(response.json(), indent=2))
        except:
            pass
    print("=" * 60)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nSUCCESS!")
        print(f"Total Devices: {data.get('total', 0)}")
        print(f"Online Devices: {data.get('online_count', 0)}")
        print("\nDevices:")
        for device in data.get('devices', []):
            print(f"  - {device['nombre']} ({device['device_id']})")
            print(f"    Status: {device['status']}")
            print(f"    Scans Today: {device['scans_today']}")
            print(f"    Total Scans: {device['scans_total']}")
            print(f"    Last Seen: {device['last_seen']}")
            print()
    else:
        print(f"\nERROR: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")


