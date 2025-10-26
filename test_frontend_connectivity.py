#!/usr/bin/env python
"""Script para testar conectividade entre frontend e backend."""

import requests
import json
import time

def test_connectivity():
    """Testa a conectividade básica entre frontend e backend."""
    
    # URLs para testar
    backend_url = "http://localhost:8000"
    frontend_url = "http://localhost:5173"
    
    print("🔍 Testando conectividade...")
    
    # Teste 1: Backend está respondendo?
    try:
        response = requests.get(f"{backend_url}/api/v1/", timeout=5)
        print(f"✅ Backend responde: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend não responde: {e}")
        return False
    
    # Teste 2: Frontend está respondendo?
    try:
        response = requests.get(frontend_url, timeout=5)
        print(f"✅ Frontend responde: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend não responde: {e}")
        return False
    
    # Teste 3: CORS está configurado?
    try:
        headers = {
            'Origin': frontend_url,
            'Access-Control-Request-Method': 'PUT',
            'Access-Control-Request-Headers': 'Content-Type,Authorization,X-CSRFToken'
        }
        response = requests.options(f"{backend_url}/api/v1/respostas/1", headers=headers, timeout=5)
        print(f"✅ CORS preflight: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
    except Exception as e:
        print(f"❌ CORS preflight falhou: {e}")
    
    # Teste 4: Endpoint específico
    try:
        response = requests.get(f"{backend_url}/api/v1/respostas/1", timeout=5)
        print(f"✅ Endpoint /respostas/1: {response.status_code}")
    except Exception as e:
        print(f"❌ Endpoint /respostas/1 falhou: {e}")
    
    return True

if __name__ == "__main__":
    test_connectivity()