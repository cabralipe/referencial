#!/usr/bin/env python
"""Script para testar se a correção do frontend funciona."""

import requests
import json

def test_resposta_update():
    # URL base
    base_url = "http://localhost:8000/api/v1"
    
    # Fazer login
    login_data = {
        "email": "super@test.com",
        "password": "admin"
    }
    
    session = requests.Session()
    
    # Obter token CSRF
    csrf_response = session.get(f"{base_url}/auth/csrf")
    print(f"CSRF Response: {csrf_response.status_code}")
    
    # Obter token CSRF do cookie (como o frontend faz)
    csrf_token = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            csrf_token = cookie.value
            break
    
    if not csrf_token and csrf_response.status_code == 200:
        csrf_token = csrf_response.json().get('csrfToken')
    
    print(f"CSRF Token: {csrf_token}")
    
    # Fazer login
    login_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if csrf_token:
        login_headers["X-CSRFToken"] = csrf_token
        
    login_response = session.post(f"{base_url}/auth/login", 
                                 json=login_data, 
                                 headers=login_headers)
    print(f"Login Response: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("Falha no login!")
        print(f"Erro: {login_response.text}")
        return
    
    # Obter token CSRF atualizado após login
    csrf_token_after_login = None
    for cookie in session.cookies:
        if cookie.name == 'csrftoken':
            csrf_token_after_login = cookie.value
            break
    
    if csrf_token_after_login:
        csrf_token = csrf_token_after_login
        print(f"CSRF Token após login: {csrf_token}")
    
    # Primeiro, fazer GET para obter ETag
    headers = {
        "X-Cliente-ID": "2"  # Cliente 2 para GT 1
    }
    
    get_response = session.get(f"{base_url}/respostas/1", headers=headers)
    print(f"GET Response: {get_response.status_code}")
    
    if get_response.status_code == 200:
        etag = get_response.headers.get('ETag')
        print(f"ETag obtido: {etag}")
        
        # Agora fazer PUT
        put_headers = {
            "X-Cliente-ID": "2",
            "If-Match": etag,
            "Content-Type": "application/json"
        }
        if csrf_token:
            put_headers["X-CSRFToken"] = csrf_token
        
        put_data = {
            "gt": 1,
            "pergunta": 1,
            "conteudo_html": "<p>Teste de atualização via frontend corrigido</p>"
        }
        
        put_response = session.put(f"{base_url}/respostas/1", 
                                  json=put_data, 
                                  headers=put_headers)
        print(f"PUT Response: {put_response.status_code}")
        
        if put_response.status_code == 200:
            print("✅ Sucesso! A correção do frontend funcionou!")
            print(f"Resposta atualizada: {put_response.json()}")
        else:
            print(f"❌ Erro no PUT: {put_response.status_code}")
            print(f"Resposta: {put_response.text}")
    else:
        print(f"❌ Erro no GET: {get_response.status_code}")
        print(f"Resposta: {get_response.text}")

if __name__ == '__main__':
    test_resposta_update()