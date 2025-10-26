#!/usr/bin/env python3

import requests
import json

def simulate_frontend_flow():
    """Simulate exactly what the frontend does"""
    
    session = requests.Session()
    
    print("=== Simulating Frontend Flow ===")
    
    # Step 1: Frontend loads, gets CSRF token via API
    print("\n1. Frontend loads - getting CSRF token via API...")
    try:
        csrf_response = session.get('http://localhost:5173/api/v1/auth/csrf')
        print(f"CSRF API Status: {csrf_response.status_code}")
        if csrf_response.status_code == 200:
            api_csrf_token = csrf_response.json().get('csrfToken')
            print(f"API CSRF Token: {api_csrf_token[:20]}..." if api_csrf_token else "No token")
        else:
            print(f"CSRF API Error: {csrf_response.text}")
            return
    except Exception as e:
        print(f"CSRF API Exception: {e}")
        return
    
    # Check what's in cookies after CSRF API call
    print("\n2. Checking cookies after CSRF API call...")
    cookie_csrf_token = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            cookie_csrf_token = cookie.value
            print(f"Cookie CSRF Token: {cookie_csrf_token[:20]}...")
            break
    
    if not cookie_csrf_token:
        print("No CSRF cookie found after API call")
    
    # Step 2: User logs in - frontend uses cookie token (as per client.ts)
    print("\n3. User logs in - using cookie token...")
    try:
        # The frontend client.ts getCsrfToken() reads from cookie
        csrf_token_to_use = cookie_csrf_token  # This is what client.ts does
        
        login_data = {
            'email': 'admin@test.com',
            'password': 'admin123'
        }
        login_headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token_to_use
        }
        
        login_response = session.post(
            'http://localhost:5173/api/v1/auth/login',
            json=login_data,
            headers=login_headers
        )
        print(f"Login Status: {login_response.status_code}")
        if login_response.status_code != 200:
            print(f"Login Error: {login_response.text}")
            return
        else:
            print("Login successful!")
            
    except Exception as e:
        print(f"Login Exception: {e}")
        return
    
    # Step 3: Check cookies after login
    print("\n4. Checking cookies after login...")
    post_login_csrf_token = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            post_login_csrf_token = cookie.value
            print(f"Post-login Cookie CSRF Token: {post_login_csrf_token[:20]}...")
            break
    
    # Step 4: User tries to save a resposta - frontend uses cookie token
    print("\n5. User saves resposta - using current cookie token...")
    try:
        # This simulates what useUpsertResposta does
        current_csrf_token = post_login_csrf_token  # client.ts getCsrfToken() reads from cookie
        
        put_response = session.put(
            'http://localhost:5173/api/v1/respostas/1',
            json={
                'gt': 1,
                'pergunta': 1,
                'conteudo_html': '<p>Test content from frontend simulation</p>',
            },
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': current_csrf_token,
                'X-Cliente-ID': '1'  # This comes from the GT-Cliente mapping
            }
        )
        print(f"PUT Status: {put_response.status_code}")
        print(f"PUT Response: {put_response.text[:200]}...")
        
        if put_response.status_code == 404:
            print("✅ CSRF passed! (404 means object doesn't exist, not CSRF error)")
        elif put_response.status_code == 403:
            print("❌ CSRF failed!")
        elif put_response.status_code == 200:
            print("✅ Success!")
        
    except Exception as e:
        print(f"PUT Exception: {e}")
    
    print("\n=== Frontend Flow Simulation Complete ===")

if __name__ == "__main__":
    simulate_frontend_flow()