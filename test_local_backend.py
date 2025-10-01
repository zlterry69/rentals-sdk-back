#!/usr/bin/env python3
"""
Script para probar el backend local de HogarPeru Rentals
Prueba endpoints de autenticación, unidades, pagos, etc.
"""

import requests
import json
import sys
from datetime import datetime

# Configuración
BACKEND_URL = 'https://r3k8sn86cl.execute-api.us-east-1.amazonaws.com/Prod'
# Nota: Probando backend deployado en AWS Lambda

def print_separator(title=""):
    """Imprimir separador con título"""
    print("\n" + "="*60)
    if title:
        print(f" 🔍 {title}")
        print("="*60)

def print_result(test_name, success, details=""):
    """Imprimir resultado de prueba"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   📝 {details}")

def test_health_check():
    """Probar endpoint de salud"""
    print_separator("HEALTH CHECK")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # En Lambda, el health check puede estar en /health o en la raíz
        if response.status_code != 200:
            print("   🔄 Probando endpoint raíz...")
            response = requests.get(f"{BACKEND_URL}/", timeout=10)
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_cors():
    """Probar CORS con frontend deployado"""
    print_separator("CORS TEST")
    try:
        # Probar CORS con el frontend real deployado
        headers = {
            "Origin": "https://rentals-sdk-front.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        }
        response = requests.options(f"{BACKEND_URL}/units/featured", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"CORS Headers:")
        print(f"  - Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NO')}")
        print(f"  - Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'NO')}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_register():
    """Probar registro de usuario"""
    print_separator("USER REGISTRATION")
    try:
        user_data = {
            "email": "trry@test.com",
            "password": "123456",
            "name": "Terry Test",  # Cambiado de first_name/last_name a name
            "phone": "+1234567890"
        }
        response = requests.post(f"{BACKEND_URL}/auth/register", json=user_data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 201:
            return True
        elif response.status_code == 400 and "already exists" in str(response.json()):
            print("   📝 Usuario ya existe (esperado)")
            return True
        else:
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_login():
    """Probar login de usuario"""
    print_separator("USER LOGIN")
    try:
        login_data = {
            "email": "trry@test.com",
            "password": "123456"
        }
        response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                print(f"   🎟️ Token obtenido: {token[:20]}...")
                return token
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_protected_endpoint(token):
    """Probar endpoint protegido"""
    print_separator("PROTECTED ENDPOINT")
    if not token:
        print("❌ No hay token, saltando prueba")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/auth/me", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_units():
    """Probar endpoints de unidades"""
    print_separator("UNITS ENDPOINTS")
    
    # Featured units
    try:
        response = requests.get(f"{BACKEND_URL}/units/featured", timeout=10)
        print(f"Featured Units - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # Manejar tanto listas como objetos con 'data'
            if isinstance(data, list):
                print(f"  📊 Unidades destacadas: {len(data)}")
            else:
                print(f"  📊 Unidades destacadas: {len(data.get('data', []))}")
        else:
            print(f"  ❌ Error: {response.json()}")
    except Exception as e:
        print(f"  ❌ Error Featured Units: {e}")
    
    # All units (requiere autenticación)
    try:
        response = requests.get(f"{BACKEND_URL}/units", timeout=10)
        print(f"All Units - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"  📊 Total unidades: {len(data)}")
            else:
                print(f"  📊 Total unidades: {len(data.get('data', []))}")
        else:
            print(f"  ❌ Error: {response.json()}")
    except Exception as e:
        print(f"  ❌ Error All Units: {e}")

def test_currencies():
    """Probar endpoint de monedas"""
    print_separator("CURRENCIES")
    try:
        response = requests.get(f"{BACKEND_URL}/currencies", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # Manejar tanto listas como objetos con 'data'
            if isinstance(data, list):
                print(f"  💰 Monedas disponibles: {len(data)}")
            else:
                print(f"  💰 Monedas disponibles: {len(data.get('data', []))}")
        else:
            print(f"  ❌ Error: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_payments():
    """Probar endpoints de pagos"""
    print_separator("PAYMENTS")
    try:
        response = requests.get(f"{BACKEND_URL}/payments", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"  💳 Pagos: {len(data)}")
            else:
                print(f"  💳 Pagos: {len(data.get('data', []))}")
        else:
            print(f"  ❌ Error: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_protected_units(token):
    """Probar unidades con autenticación"""
    print_separator("PROTECTED UNITS")
    if not token:
        print("❌ No hay token, saltando prueba")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/units", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"  📊 Total unidades: {len(data)}")
            else:
                print(f"  📊 Total unidades: {len(data.get('data', []))}")
            return True
        else:
            print(f"  ❌ Error: {response.json()}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_protected_payments(token):
    """Probar pagos con autenticación"""
    print_separator("PROTECTED PAYMENTS")
    if not token:
        print("❌ No hay token, saltando prueba")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BACKEND_URL}/payments", headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"  💳 Pagos: {len(data)}")
            else:
                print(f"  💳 Pagos: {len(data.get('data', []))}")
            return True
        else:
            print(f"  ❌ Error: {response.json()}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 INICIANDO PRUEBAS DEL BACKEND AWS LAMBDA")
    print(f"📍 Backend URL: {BACKEND_URL}")
    print(f"📍 Frontend: No se prueba")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Lista de pruebas
    tests = [
        ("Health Check", test_health_check),
        ("CORS", test_cors),
        ("User Registration", test_register),
        ("User Login", test_login),
        ("Units", test_units),
        ("Currencies", test_currencies),
        ("Payments", test_payments),
    ]
    
    results = []
    token = None
    
    for test_name, test_func in tests:
        print_separator(f"EJECUTANDO: {test_name}")
        
        try:
            if test_name == "User Login":
                result = test_func()
                if result:
                    token = result
                    results.append(True)
                else:
                    results.append(False)
            elif test_name == "Protected Endpoint":
                result = test_func(token)
                results.append(result)
            else:
                result = test_func()
                results.append(result)
        except Exception as e:
            print(f"❌ ERROR inesperado en {test_name}: {e}")
            results.append(False)
    
    # Probar endpoints protegidos si tenemos token
    if token:
        print_separator("PROTECTED ENDPOINTS")
        try:
            result1 = test_protected_endpoint(token)
            results.append(("Protected Endpoint", result1))
            
            result2 = test_protected_units(token)
            results.append(("Protected Units", result2))
            
            result3 = test_protected_payments(token)
            results.append(("Protected Payments", result3))
        except Exception as e:
            print(f"❌ ERROR en endpoints protegidos: {e}")
            results.append(("Protected Endpoints", False))
    
    # Resumen final
    print_separator("RESUMEN FINAL")
    passed = sum(1 for r in results if r is True)
    total = len(results)
    
    print(f"🎯 Resultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El backend local está funcionando correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar la configuración del backend.")
    
    print("\n" + "="*60)
    print("🏁 PRUEBAS COMPLETADAS")
    print("="*60)

if __name__ == "__main__":
    main()
