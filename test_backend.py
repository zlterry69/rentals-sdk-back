#!/usr/bin/env python3
"""
Script para probar el backend de HogarPeru Rentals desplegado en AWS Lambda
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BACKEND_URL = 'https://r3k8sn86cl.execute-api.us-east-1.amazonaws.com/Prod'
FRONTEND_URL = 'https://rentals-sdk-front.vercel.app'

def print_separator(title=""):
    """Imprimir separador con título"""
    print("\n" + "="*60)
    if title:
        print(f" {title}")
        print("="*60)

def test_health():
    """Probar health check del backend"""
    print_separator("🔍 PROBANDO HEALTH CHECK")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Headers: {dict(response.headers)}")
        print(f"✅ Response: {response.text}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_cors():
    """Probar CORS del backend"""
    print_separator("🔍 PROBANDO CORS")
    
    try:
        headers = {
            'Origin': FRONTEND_URL,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{BACKEND_URL}/units/featured", 
                              headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ CORS Headers:")
        print(f"   - Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NO ENCONTRADO')}")
        print(f"   - Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'NO ENCONTRADO')}")
        print(f"   - Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Methods', 'NO ENCONTRADO')}")
        print(f"✅ Response: {response.text[:200]}...")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_featured_units():
    """Probar endpoint de unidades destacadas"""
    print_separator("🔍 PROBANDO FEATURED UNITS")
    
    try:
        headers = {
            'Origin': FRONTEND_URL,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{BACKEND_URL}/units/featured", 
                              headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ JSON válido - {len(data)} elementos")
            except:
                print("⚠️  Response no es JSON válido")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_login():
    """Probar login del backend"""
    print_separator("🔍 PROBANDO LOGIN")
    
    try:
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        headers = {
            'Origin': FRONTEND_URL,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(f"{BACKEND_URL}/auth/login", 
                               json=login_data, headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {response.text[:300]}...")
        
        return response.status_code in [200, 401, 422]  # 401/422 son respuestas válidas para credenciales incorrectas
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_units_list():
    """Probar lista de unidades"""
    print_separator("🔍 PROBANDO UNITS LIST")
    
    try:
        headers = {
            'Origin': FRONTEND_URL,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{BACKEND_URL}/units", 
                              headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {response.text[:300]}...")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_cors_preflight():
    """Probar CORS preflight request"""
    print_separator("🔍 PROBANDO CORS PREFLIGHT")
    
    try:
        headers = {
            'Origin': FRONTEND_URL,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        response = requests.options(f"{BACKEND_URL}/units/featured", 
                                  headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ CORS Headers:")
        print(f"   - Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NO ENCONTRADO')}")
        print(f"   - Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'NO ENCONTRADO')}")
        print(f"   - Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'NO ENCONTRADO')}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 INICIANDO PRUEBAS DEL BACKEND AWS LAMBDA")
    print(f"📍 Backend URL: {BACKEND_URL}")
    print(f"📍 Frontend URL: {FRONTEND_URL}")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar todas las pruebas
    tests = [
        ("Health Check", test_health),
        ("CORS Preflight", test_cors_preflight),
        ("CORS Request", test_cors),
        ("Featured Units", test_featured_units),
        ("Units List", test_units_list),
        ("Login", test_login),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen de resultados
    print_separator("📊 RESUMEN DE RESULTADOS")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El backend está funcionando correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar la configuración del backend.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
