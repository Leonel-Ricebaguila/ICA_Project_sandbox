"""
Debug script for Active NFC Devices API
"""

import requests
import urllib3

urllib3.disable_warnings()

url = "https://192.168.1.84:5443/api/nfc/devices/active"

print("Testing /api/nfc/devices/active endpoint...")
print()

try:
    response = requests.get(url, verify=False)
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print()
    print("Response body:")
    print(response.text)
    print()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

