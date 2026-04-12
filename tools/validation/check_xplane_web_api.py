#!/usr/bin/env python3
"""Test X-Plane Web API (REST endpoint on port 8086)."""

import sys
import time

def test_web_api():
    """Check if X-Plane Web API is responding."""
    try:
        import requests
    except ImportError:
        print("Installing requests library...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "requests"])
        import requests
    
    api_url = "http://127.0.0.1:8086/api/v3/capabilities"
    
    print("Testing X-Plane Web API on port 8086...")
    print(f"URL: {api_url}\n")
    
    for attempt in range(5):
        try:
            response = requests.get(api_url, timeout=2)
            
            if response.status_code == 200:
                print(f"✅ SUCCESS! X-Plane Web API is responding")
                print(f"Response: {response.json()}\n")
                return True
            elif response.status_code == 403:
                print(f"⚠️  Got 403 Forbidden - X-Plane security policy may block incoming traffic")
                print("   Fix: X-Plane Settings → Net Connections → Security: Enable 'Allow Incoming Traffic'\n")
                return False
            else:
                print(f"Got HTTP {response.status_code}: {response.text}\n")
                return False
                
        except requests.ConnectionError:
            print(f"Attempt {attempt + 1}/5: Connection refused... (retrying)")
            time.sleep(1)
        except requests.Timeout:
            print(f"Attempt {attempt + 1}/5: Timeout (X-Plane may not be running)")
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}\n")
            return False
    
    print("❌ No response from X-Plane Web API")
    print("\nTroubleshooting:")
    print("  1. X-Plane must be running (not paused)")
    print("  2. Check: X-Plane Settings → Net Connections → 'Enable Web Server'")
    print("  3. Check: X-Plane Settings → Net Connections → Security: 'Allow Incoming Traffic'")
    print("  4. Default port is 8086 (can override with --web_server_port= flag)")
    print("\nAlternatively, check if it's listening:")
    print("  netstat -an | findstr 8086\n")
    return False

if __name__ == "__main__":
    success = test_web_api()
    sys.exit(0 if success else 1)
