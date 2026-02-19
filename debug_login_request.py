import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def debug_login():
    session = requests.Session()
    
    # 1. Get CSRF Token
    print("Fetching CSRF token...")
    csrf_resp = session.get(f"{BASE_URL}/auth/csrf")
    print(f"CSRF Status: {csrf_resp.status_code}")
    print(f"CSRF Cookies: {session.cookies.get_dict()}")
    
    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        try:
            data = csrf_resp.json()
            csrf_token = data.get("csrfToken")
        except:
            pass
    
    if not csrf_token:
        print("Failed to get CSRF token")
        return

    print(f"CSRF Token: {csrf_token}")
    
    # 2. Attempt Login
    login_url = f"{BASE_URL}/auth/login"
    payload = {
        "email": "admin@test.com", 
        "password": "123456"
    }
    
    headers = {
        "X-CSRFToken": csrf_token,
        "Content-Type": "application/json",
        "Referer": "http://127.0.0.1:3000/"
    }
    
    print(f"Attempting login to {login_url}")
    resp = session.post(login_url, json=payload, headers=headers)
    
    print(f"Login Status: {resp.status_code}")
    try:
        print(f"Login Response: {resp.json()}")
    except:
        print(f"Login Response Text: {resp.text}")

if __name__ == "__main__":
    debug_login()
