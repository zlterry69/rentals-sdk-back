#!/usr/bin/env python3
"""
Script para probar el endpoint /payments/recent
"""
import requests
import json

def test_recent_payments():
    base_url = "http://localhost:8000"
    
    # Primero hacer login para obtener el token
    login_data = {
        "email": "normal@test.com",
        "password": "123456"
    }
    
    print("🔐 Haciendo login...")
    login_response = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json().get("access_token")
    print(f"✅ Login exitoso, token obtenido")
    
    # Probar el endpoint /payments/recent
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("\n💰 Probando /payments/recent...")
    recent_response = requests.get(f"{base_url}/payments/recent?limit=5", headers=headers)
    
    print(f"Status Code: {recent_response.status_code}")
    print(f"Response: {recent_response.text}")
    
    if recent_response.status_code == 200:
        data = recent_response.json()
        print(f"✅ Pagos encontrados: {data.get('total', 0)}")
        print(f"Límite: {data.get('limit', 0)}")
    else:
        print(f"❌ Error: {recent_response.status_code}")

if __name__ == "__main__":
    test_recent_payments()
