#!/usr/bin/env python3

import requests
import json

def debug_csrf_issue():
    """Debug the specific CSRF issue"""
    
    session = requests.Session()
    
    print("=== Debugging CSRF Issue ===")
    
    # Step 1: Get CSRF token via API
    print("\n1. Getting CSRF token via API...")
    try:
        csrf_response = session.get('http://localhost:5173/api/v1/auth/csrf')
        print(f"CSRF API Status: {csrf_response.status_code}")
        if csrf_response.status_code == 200:
            csrf_data = csrf_response.json()
            api_csrf_token = csrf_data.get('csrfToken')
            print(f"API CSRF Token: {api_csrf_token[:20]}..." if api_csrf_token else "No token")
        else:
            print(f"CSRF API Error: {csrf_response.text}")
            return
    except Exception as e:
        print(f"CSRF API Exception: {e}")
        return
    
    # Step 2: Check CSRF cookie
    print("\n2. Checking CSRF cookie...")
    cookie_csrf_token = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            cookie_csrf_token = cookie.value
            print(f"Cookie CSRF Token: {cookie_csrf_token[:20]}...")
            break
    
    if not cookie_csrf_token:
        print("No CSRF cookie found")
    
    # Step 3: Compare tokens
    print("\n3. Comparing tokens...")
    if api_csrf_token and cookie_csrf_token:
        if api_csrf_token == cookie_csrf_token:
            print("✅ API and Cookie tokens match")
        else:
            print("❌ API and Cookie tokens differ")
            print(f"API:    {api_csrf_token}")
            print(f"Cookie: {cookie_csrf_token}")
    
    # Step 4: Login with API token
    print("\n4. Login with API token...")
    try:
        login_data = {
            'email': 'admin@test.com',
            'password': 'admin123'
        }
        login_headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': api_csrf_token
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
    
    # Step 5: Check CSRF cookie after login
    print("\n5. Checking CSRF cookie after login...")
    post_login_csrf_token = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            post_login_csrf_token = cookie.value
            print(f"Post-login Cookie CSRF Token: {post_login_csrf_token[:20]}...")
            break
    
    # Step 6: Test PUT with different CSRF tokens
    print("\n6. Testing PUT with different CSRF tokens...")
    
    # Test with API token
    print("\n6a. Testing with API token...")
    try:
        put_response_api = session.put(
            'http://localhost:5173/api/v1/respostas/1',
            json={
                'conteudo_html': '<p>Test with API token</p>',
                'etag': 'test-etag-api'
            },
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': api_csrf_token,
                'X-Cliente-ID': '1'
            }
        )
        print(f"PUT with API token Status: {put_response_api.status_code}")
        print(f"PUT with API token Response: {put_response_api.text[:200]}...")
    except Exception as e:
        print(f"PUT with API token Exception: {e}")
    
    # Test with post-login cookie token
    if post_login_csrf_token:
        print("\n6b. Testing with post-login cookie token...")
        try:
            put_response_cookie = session.put(
                'http://localhost:5173/api/v1/respostas/1',
                json={
                    'conteudo_html': '<p>Test with cookie token</p>',
                    'etag': 'test-etag-cookie'
                },
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRFToken': post_login_csrf_token,
                    'X-Cliente-ID': '1'
                }
            )
            print(f"PUT with cookie token Status: {put_response_cookie.status_code}")
            print(f"PUT with cookie token Response: {put_response_cookie.text[:200]}...")
        except Exception as e:
            print(f"PUT with cookie token Exception: {e}")
    
    # Step 7: Test without explicit CSRF header (let Django get it from cookie)
    print("\n7. Testing without explicit CSRF header...")
    try:
        put_response_no_header = session.put(
            'http://localhost:5173/api/v1/respostas/1',
            json={
                'conteudo_html': '<p>Test without header</p>',
                'etag': 'test-etag-no-header'
            },
            headers={
                'Content-Type': 'application/json',
                'X-Cliente-ID': '1'
            }
        )
        print(f"PUT without header Status: {put_response_no_header.status_code}")
        print(f"PUT without header Response: {put_response_no_header.text[:200]}...")
    except Exception as e:
        print(f"PUT without header Exception: {e}")
    
    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    debug_csrf_issue()