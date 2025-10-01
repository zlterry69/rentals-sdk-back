#!/usr/bin/env python3
"""
Script para debuggear las tablas de pagos
"""
import requests
import json

def debug_payments():
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
        return
    
    token = login_response.json().get("access_token")
    print(f"✅ Login exitoso")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 1. Verificar usuario actual
    print("\n👤 Verificando usuario actual...")
    me_response = requests.get(f"{base_url}/auth/me", headers=headers)
    if me_response.status_code == 200:
        user_data = me_response.json()
        print(f"Usuario: {user_data.get('email')} (ID: {user_data.get('id')})")
        print(f"Rol: {user_data.get('role')}")
    else:
        print(f"❌ Error obteniendo usuario: {me_response.status_code}")
        return
    
    # 2. Verificar unidades del usuario
    print("\n🏠 Verificando unidades del usuario...")
    units_response = requests.get(f"{base_url}/units", headers=headers)
    if units_response.status_code == 200:
        units = units_response.json()
        print(f"Unidades encontradas: {len(units)}")
        for unit in units:
            print(f"  - {unit.get('title')} (ID: {unit.get('id')})")
    else:
        print(f"❌ Error obteniendo unidades: {units_response.status_code}")
    
    # 3. Verificar todos los pagos
    print("\n💰 Verificando todos los pagos...")
    payments_response = requests.get(f"{base_url}/payments", headers=headers)
    if payments_response.status_code == 200:
        payments = payments_response.json()
        print(f"Pagos encontrados: {len(payments)}")
        for payment in payments[:5]:  # Mostrar solo los primeros 5
            print(f"  - ID: {payment.get('id')}, Amount: {payment.get('amount')}, Method: {payment.get('method')}")
    else:
        print(f"❌ Error obteniendo pagos: {payments_response.status_code}")
    
    # 4. Verificar debtors
    print("\n👥 Verificando debtors...")
    debtors_response = requests.get(f"{base_url}/debtors", headers=headers)
    if debtors_response.status_code == 200:
        debtors = debtors_response.json()
        print(f"Debtors encontrados: {len(debtors)}")
        for debtor in debtors[:5]:  # Mostrar solo los primeros 5
            print(f"  - {debtor.get('name')} (Property ID: {debtor.get('property_id')})")
    else:
        print(f"❌ Error obteniendo debtors: {debtors_response.status_code}")

if __name__ == "__main__":
    debug_payments()
