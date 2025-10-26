#!/usr/bin/env python3
"""
Test script to verify the complete authentication and API flow through the Vite proxy.
This simulates the exact flow that the frontend should use.
"""

import requests
import json

def test_full_flow():
    """Test the complete authentication and API flow through the proxy."""
    
    print("Testing complete authentication and API flow through Vite proxy...")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Step 1: Get CSRF token through proxy
    print("\n1. Getting CSRF token through proxy...")
    try:
        response = session.get(
            "http://localhost:5173/api/v1/auth/csrf",
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            csrf_data = response.json()
            csrf_token = csrf_data.get('csrfToken')
            print(f"   CSRF Token: {csrf_token[:20]}..." if csrf_token else "   No CSRF token")
        else:
            print(f"   Error: {response.text}")
            return
    except requests.exceptions.RequestException as e:
        print(f"   Failed: {e}")
        return
    
    # Step 2: Login through proxy
    print("\n2. Logging in through proxy...")
    try:
        login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_token
        }
        
        response = session.post(
            "http://localhost:5173/api/v1/auth/login",
            json=login_data,
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"   Logged in as: {user_data.get('email', 'Unknown')}")
        else:
            print(f"   Error: {response.text}")
            return
    except requests.exceptions.RequestException as e:
        print(f"   Failed: {e}")
        return
    
    # Step 3: Get updated CSRF token from cookie
    print("\n3. Getting CSRF token from cookie...")
    csrf_cookie = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            csrf_cookie = cookie.value
            print(f"   Cookie CSRF Token: {csrf_cookie[:20]}...")
            break
    
    if not csrf_cookie:
        print("   No CSRF cookie found")
        return
    
    # Step 4: Test accessing respostas through proxy
    print("\n4. Testing respostas access through proxy...")
    try:
        headers = {
            "X-CSRFToken": csrf_cookie
        }
        
        response = session.get(
            "http://localhost:5173/api/v1/respostas/2",  # Use ID 2 which belongs to Cliente 1
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            resposta_data = response.json()
            print(f"   Resposta ID: {resposta_data.get('id')}")
            print(f"   Pergunta ID: {resposta_data.get('pergunta_id')}")
        else:
            print(f"   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   Failed: {e}")
    
    # Step 5: Test PUT request through proxy
    print("\n5. Testing PUT request through proxy...")
    try:
        put_data = {
            "resposta_texto": "Test response updated through proxy",
            "status": "rascunho"
        }
        headers = {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf_cookie
        }
        
        response = session.put(
            "http://localhost:5173/api/v1/respostas/2",
            json=put_data,
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            updated_data = response.json()
            print(f"   Updated successfully: {updated_data.get('resposta_texto', '')[:50]}...")
        else:
            print(f"   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   Failed: {e}")
    
    print("\n✓ Test completed!")

if __name__ == "__main__":
    test_full_flow()