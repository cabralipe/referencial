#!/usr/bin/env python3
"""
Test script to verify that the frontend proxy fix works correctly.
This script simulates a request through the Vite proxy.
"""

import requests
import json

def test_proxy_fix():
    """Test that requests through the Vite proxy work correctly."""
    
    print("Testing API access through Vite proxy...")
    
    # Test 1: CSRF token through proxy
    try:
        response = requests.get(
            "http://localhost:5173/api/v1/auth/csrf",
            timeout=10
        )
        print(f"✓ CSRF through proxy: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Token received: {data.get('csrfToken', 'N/A')[:20]}...")
        else:
            print(f"  Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ CSRF through proxy failed: {e}")
    
    # Test 2: Respostas endpoint through proxy (should get 401 without auth)
    try:
        response = requests.get(
            "http://localhost:5173/api/v1/respostas/1",
            timeout=10
        )
        print(f"✓ Respostas through proxy: {response.status_code}")
        if response.status_code == 401:
            print("  Expected 401 (authentication required)")
        else:
            print(f"  Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Respostas through proxy failed: {e}")
    
    # Test 3: Direct backend access (for comparison)
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/auth/csrf",
            timeout=10
        )
        print(f"✓ Direct backend access: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Direct backend access failed: {e}")

if __name__ == "__main__":
    test_proxy_fix()