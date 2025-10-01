#!/usr/bin/env python3
"""
Script completo para debuggear toda la base de datos y sus relaciones
"""
import requests
import json
from datetime import datetime

def debug_database():
    base_url = "http://localhost:8000"
    
    # Login
    print("🔐 Haciendo login...")
    login_data = {"email": "normal@test.com", "password": "123456"}
    login_response = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        return
    
    token = login_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("✅ Login exitoso")
    
    # 1. USUARIO ACTUAL
    print("\n" + "="*80)
    print("👤 USUARIO ACTUAL")
    print("="*80)
    me_response = requests.get(f"{base_url}/auth/me", headers=headers)
    if me_response.status_code == 200:
        user_data = me_response.json()
        print(f"Email: {user_data.get('email')}")
        print(f"ID: {user_data.get('id')}")
        print(f"Rol: {user_data.get('role')}")
        print(f"Nombre: {user_data.get('full_name')}")
    else:
        print(f"❌ Error obteniendo usuario: {me_response.status_code}")
        return
    
    # 2. UNIDADES (PROPIEDADES)
    print("\n" + "="*80)
    print("🏠 UNIDADES/PROPIEDADES")
    print("="*80)
    units_response = requests.get(f"{base_url}/units", headers=headers)
    if units_response.status_code == 200:
        units = units_response.json()
        print(f"Total unidades: {len(units)}")
        for i, unit in enumerate(units, 1):
            print(f"\n{i}. {unit.get('title', 'Sin título')}")
            print(f"   ID: {unit.get('id')}")
            print(f"   Public ID: {unit.get('public_id')}")
            print(f"   Owner ID: {unit.get('owner_id')}")
            print(f"   Tipo: {unit.get('unit_type', 'N/A')}")
            print(f"   Precio: S/ {unit.get('monthly_rent', 0)}")
            print(f"   Estado: {unit.get('status', 'N/A')}")
    else:
        print(f"❌ Error obteniendo unidades: {units_response.status_code}")
    
    # 3. DEBTORS (DEUDORES/INQUILINOS)
    print("\n" + "="*80)
    print("👥 DEBTORS (DEUDORES/INQUILINOS)")
    print("="*80)
    debtors_response = requests.get(f"{base_url}/debtors", headers=headers)
    if debtors_response.status_code == 200:
        debtors = debtors_response.json()
        print(f"Total debtors: {len(debtors)}")
        for i, debtor in enumerate(debtors, 1):
            print(f"\n{i}. {debtor.get('name', 'Sin nombre')}")
            print(f"   ID: {debtor.get('id')}")
            print(f"   Public ID: {debtor.get('public_id')}")
            print(f"   Email: {debtor.get('email', 'N/A')}")
            print(f"   Property ID: {debtor.get('property_id')}")
            print(f"   Owner ID: {debtor.get('owner_id')}")
            print(f"   Full Name: {debtor.get('full_name', 'N/A')}")
    else:
        print(f"❌ Error obteniendo debtors: {debtors_response.status_code}")
    
    # 4. PAGOS
    print("\n" + "="*80)
    print("💰 PAGOS")
    print("="*80)
    payments_response = requests.get(f"{base_url}/payments", headers=headers)
    if payments_response.status_code == 200:
        payments = payments_response.json()
        print(f"Total pagos: {len(payments)}")
        for i, payment in enumerate(payments, 1):
            print(f"\n{i}. Pago ID: {payment.get('id')}")
            print(f"   Public ID: {payment.get('public_id')}")
            print(f"   Amount: S/ {payment.get('amount', 0)}")
            print(f"   Method: {payment.get('method', 'N/A')}")
            print(f"   Status: {payment.get('process_status', {}).get('code', 'N/A')}")
            print(f"   Debtor ID: {payment.get('debtor_id')}")
            print(f"   Created: {payment.get('created_at', 'N/A')}")
            print(f"   Debtor Info: {payment.get('debtors', {})}")
    else:
        print(f"❌ Error obteniendo pagos: {payments_response.status_code}")
    
    # 5. BOOKINGS (RESERVAS)
    print("\n" + "="*80)
    print("📅 BOOKINGS (RESERVAS)")
    print("="*80)
    bookings_response = requests.get(f"{base_url}/bookings/my-bookings", headers=headers)
    if bookings_response.status_code == 200:
        bookings_data = bookings_response.json()
        bookings = bookings_data.get('bookings', [])
        print(f"Total bookings: {len(bookings)}")
        for i, booking in enumerate(bookings, 1):
            print(f"\n{i}. Booking ID: {booking.get('public_id')}")
            print(f"   Unit: {booking.get('units', {}).get('title', 'N/A')}")
            print(f"   Amount: S/ {booking.get('total_amount', 0)}")
            print(f"   Status: {booking.get('process_status', {}).get('code', 'N/A')}")
            print(f"   Payment Status: {booking.get('payment_status', 'N/A')}")
            print(f"   Created: {booking.get('created_at', 'N/A')}")
    else:
        print(f"❌ Error obteniendo bookings: {bookings_response.status_code}")
    
    # 6. PAYMENT DETAILS
    print("\n" + "="*80)
    print("📋 PAYMENT DETAILS")
    print("="*80)
    # Intentar obtener payment details de los pagos existentes
    if payments_response.status_code == 200:
        payments = payments_response.json()
        for payment in payments[:3]:  # Solo los primeros 3
            payment_id = payment.get('id')
            if payment_id:
                details_response = requests.get(f"{base_url}/payments/{payment_id}", headers=headers)
                if details_response.status_code == 200:
                    details = details_response.json()
                    print(f"\nPayment {payment.get('public_id')} details:")
                    print(f"  Payer: {details.get('debtors', {}).get('name', 'N/A')}")
                    print(f"  Method: {details.get('method', 'N/A')}")
                    print(f"  Amount: S/ {details.get('amount', 0)}")
                    print(f"  Status: {details.get('process_status', {}).get('code', 'N/A')}")
                else:
                    print(f"❌ Error obteniendo detalles del pago {payment_id}: {details_response.status_code}")
    
    # 7. ANÁLISIS DE RELACIONES
    print("\n" + "="*80)
    print("🔍 ANÁLISIS DE RELACIONES")
    print("="*80)
    
    if units_response.status_code == 200 and debtors_response.status_code == 200 and payments_response.status_code == 200:
        units = units_response.json()
        debtors = debtors_response.json()
        payments = payments_response.json()
        
        user_id = user_data.get('id')
        user_units = [u for u in units if u.get('owner_id') == user_id]
        user_debtors = [d for d in debtors if d.get('property_id') in [u.get('id') for u in user_units]]
        user_payments = [p for p in payments if p.get('debtor_id') in [d.get('id') for d in user_debtors]]
        
        print(f"Unidades del usuario: {len(user_units)}")
        print(f"Debtors de las unidades del usuario: {len(user_debtors)}")
        print(f"Pagos de los debtors del usuario: {len(user_payments)}")
        
        print(f"\nUnidades del usuario:")
        for unit in user_units:
            print(f"  - {unit.get('title')} (ID: {unit.get('id')})")
        
        print(f"\nDebtors de las unidades del usuario:")
        for debtor in user_debtors:
            print(f"  - {debtor.get('name')} (Property: {debtor.get('property_id')})")
        
        print(f"\nPagos de los debtors del usuario:")
        for payment in user_payments:
            print(f"  - S/ {payment.get('amount')} - {payment.get('method')} - {payment.get('created_at')}")
    
    # 8. RECENT PAYMENTS
    print("\n" + "="*80)
    print("🕒 RECENT PAYMENTS")
    print("="*80)
    recent_response = requests.get(f"{base_url}/payments/recent?limit=10", headers=headers)
    if recent_response.status_code == 200:
        recent_data = recent_response.json()
        print(f"Recent payments: {recent_data.get('total', 0)}")
        print(f"Limit: {recent_data.get('limit', 0)}")
        if recent_data.get('payments'):
            for payment in recent_data['payments']:
                print(f"  - S/ {payment.get('amount')} - {payment.get('method')} - {payment.get('created_at')}")
    else:
        print(f"❌ Error obteniendo recent payments: {recent_response.status_code}")

if __name__ == "__main__":
    debug_database()
