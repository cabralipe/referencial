#!/usr/bin/env python3

import requests
import json

def test_frontend_issue():
    """Test to reproduce the frontend issue with net::ERR_FAILED"""
    
    session = requests.Session()
    
    print("=== Testing Frontend Issue ===")
    
    # Test 1: Get CSRF token via proxy (correct URL)
    print("\n1. Getting CSRF token via Vite proxy...")
    try:
        csrf_response = session.get('http://localhost:5173/api/v1/auth/csrf')
        print(f"CSRF Status: {csrf_response.status_code}")
        if csrf_response.status_code == 200:
            csrf_data = csrf_response.json()
            csrf_token = csrf_data.get('csrfToken')
            print(f"CSRF Token: {csrf_token[:10]}..." if csrf_token else "No token")
        else:
            print(f"CSRF Error: {csrf_response.text}")
            return
    except Exception as e:
        print(f"CSRF Exception: {e}")
        return
    
    # Test 2: Login via proxy (correct URL)
    print("\n2. Logging in via Vite proxy...")
    try:
        login_data = {
            'email': 'admin@test.com',
            'password': 'admin123'
        }
        login_headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token
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
    
    # Test 3: Try to reproduce the exact error - PUT to respostas/1
    print("\n3. Testing PUT to /api/v1/respostas/1 via Vite proxy...")
    try:
        put_data = {
            'conteudo_html': '<p>Test content from Python</p>',
            'etag': 'test-etag-123'
        }
        put_headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token,
            'X-Cliente-ID': '1'
        }
        
        put_response = session.put(
            'http://localhost:5173/api/v1/respostas/1',
            json=put_data,
            headers=put_headers
        )
        print(f"PUT Status: {put_response.status_code}")
        print(f"PUT Response: {put_response.text}")
        
    except Exception as e:
        print(f"PUT Exception: {e}")
    
    # Test 4: Test direct backend connection
    print("\n4. Testing direct backend connection...")
    try:
        direct_response = session.get('http://localhost:8000/api/v1/respostas/1')
        print(f"Direct Backend Status: {direct_response.status_code}")
        print(f"Direct Backend Response: {direct_response.text}")
    except Exception as e:
        print(f"Direct Backend Exception: {e}")
    
    # Test 5: Check if there are network connectivity issues
    print("\n5. Testing basic connectivity...")
    try:
        # Test if frontend server is responding
        frontend_response = requests.get('http://localhost:5173', timeout=5)
        print(f"Frontend Server Status: {frontend_response.status_code}")
        
        # Test if backend server is responding
        backend_response = requests.get('http://localhost:8000', timeout=5)
        print(f"Backend Server Status: {backend_response.status_code}")
        
    except Exception as e:
        print(f"Connectivity Exception: {e}")
    
    # Test 6: Test the exact frontend flow
    print("\n6. Testing exact frontend flow...")
    try:
        # Simulate what the frontend does - get CSRF from cookie after login
        csrf_cookie = None
        for cookie in session.cookies:
            if cookie.name == 'csrftoken':
                csrf_cookie = cookie.value
                break
        
        if csrf_cookie:
            print(f"CSRF Cookie found: {csrf_cookie[:10]}...")
            
            # Try PUT with cookie-based CSRF
            put_headers_cookie = {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_cookie,
                'X-Cliente-ID': '1'
            }
            
            put_response_cookie = session.put(
                'http://localhost:5173/api/v1/respostas/1',
                json={
                    'conteudo_html': '<p>Test with cookie CSRF</p>',
                    'etag': 'test-etag-cookie'
                },
                headers=put_headers_cookie
            )
            print(f"PUT with Cookie CSRF Status: {put_response_cookie.status_code}")
            print(f"PUT with Cookie CSRF Response: {put_response_cookie.text}")
        else:
            print("No CSRF cookie found")
            
    except Exception as e:
        print(f"Frontend Flow Exception: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_frontend_issue()