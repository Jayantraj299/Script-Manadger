import requests
import time
from datetime import datetime

# ================= FINAL CONFIGURATION =================
# The correct URL from your debug success
LOGIN_URL = "http://172.16.0.1:8090/login.xml" 

USERNAME = "1hk24ai017" 
PASSWORD = "9679589111"  # <--- Put your password here!

# Google's "No Content" generator (Standard for Wi-Fi checks)
TEST_URL = "http://connectivitycheck.gstatic.com/generate_204"
# =======================================================

def log(message):
    """Prints a timestamped message."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {message}")

def get_current_timestamp_ms():
    """Generates the millisecond timestamp required by the server."""
    return str(int(time.time() * 1000))

def is_connected():
    """
    Checks for active internet. 
    Returns True ONLY if we get a 204 status (Success).
    Returns False if we get a 200 (Login Page) or timeout.
    """
    try:
        # allow_redirects=False stops us from being fooled by the login page
        response = requests.get(TEST_URL, timeout=3, allow_redirects=False)
        return response.status_code == 204
    except requests.RequestException:
        return False

def login():
    log(f"Attempting to login user {USERNAME}...")
    
    # The payload that we confirmed works in your debug test
    payload = {
        "mode": "191",
        "username": USERNAME,
        "password": PASSWORD,
        "a": get_current_timestamp_ms(),
        "producttype": "0"
    }

    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.post(LOGIN_URL, data=payload, headers=headers)
        
        # Check for the specific success XML from your college server
        if "successfully logged in" in response.text or "LIVE" in response.text:
            log("Server Reply: Login SUCCESS.")
        else:
            log(f"Server Reply: Unknown response ({response.status_code}).")
            
    except Exception as e:
        log(f"Login Error: {e}")

def main():
    print(f"--- Wi-Fi Automator for {USERNAME} ---")
    print(f"Targeting: {LOGIN_URL}")
    log("Monitoring started. Press Ctrl+C to stop.")
    print("---------------------------------------")

    while True:
        if is_connected():
            log("Status: Connected ✓")
        else:
            log("Status: DISCONNECTED ✗")
            login()
            
            # CRITICAL: Wait 5 seconds for the firewall to actually open the gate
            log("Waiting for network authorization...")
            time.sleep(2)
            
            if is_connected():
                log("Reconnection Successful! Back online.")
            else:
                log("Still offline. The server might be lagging. Retrying in 10 Seconds.")
        
        # Check every 10 seconds
        time.sleep(10)

if __name__ == "__main__":
    main()


