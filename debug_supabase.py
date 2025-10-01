#!/usr/bin/env python3
"""
Script para debuggear directamente con Supabase y arreglar las relaciones
"""
import os
from supabase import create_client, Client
from datetime import datetime

def debug_supabase():
    # Configuración de Supabase
    url = "https://auwboqgfgmqmuqsguiaa.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF1d2JvcWdmZ21xbXVxc2d1aWFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU1NzQ5NzIsImV4cCI6MjA1MTE1MDk3Mn0.8QZqJqJqJqJqJqJqJqJqJqJqJqJqJqJqJqJqJqJqJq"
    
    supabase: Client = create_client(url, key)
    
    print("🔍 DEBUGGING SUPABASE DATABASE")
    print("="*80)
    
    # 1. USUARIO ACTUAL
    print("\n👤 USUARIO ACTUAL")
    print("-" * 40)
    user_result = supabase.table('users').select('*').eq('email', 'normal@test.com').execute()
    if user_result.data:
        user = user_result.data[0]
        print(f"Email: {user.get('email')}")
        print(f"ID: {user.get('id')}")
        print(f"Rol: {user.get('role')}")
        print(f"Nombre: {user.get('full_name')}")
        user_id = user.get('id')
    else:
        print("❌ Usuario no encontrado")
        return
    
    # 2. UNIDADES DEL USUARIO
    print("\n🏠 UNIDADES DEL USUARIO")
    print("-" * 40)
    units_result = supabase.table('units').select('*').eq('owner_id', user_id).execute()
    print(f"Unidades encontradas: {len(units_result.data)}")
    for unit in units_result.data:
        print(f"  - {unit.get('title')} (ID: {unit.get('id')})")
        print(f"    Public ID: {unit.get('public_id')}")
        print(f"    Owner ID: {unit.get('owner_id')}")
    
    # 3. TODOS LOS DEBTORS
    print("\n👥 TODOS LOS DEBTORS")
    print("-" * 40)
    debtors_result = supabase.table('debtors').select('*').execute()
    print(f"Total debtors: {len(debtors_result.data)}")
    for debtor in debtors_result.data:
        print(f"  - {debtor.get('name', 'Sin nombre')} (ID: {debtor.get('id')})")
        print(f"    Property ID: {debtor.get('property_id')}")
        print(f"    Owner ID: {debtor.get('owner_id')}")
        print(f"    Email: {debtor.get('email')}")
    
    # 4. TODOS LOS PAGOS
    print("\n💰 TODOS LOS PAGOS")
    print("-" * 40)
    payments_result = supabase.table('payments').select('*').execute()
    print(f"Total pagos: {len(payments_result.data)}")
    for payment in payments_result.data:
        print(f"  - Pago ID: {payment.get('id')}")
        print(f"    Public ID: {payment.get('public_id')}")
        print(f"    Amount: S/ {payment.get('amount')}")
        print(f"    Method: {payment.get('method')}")
        print(f"    Debtor ID: {payment.get('debtor_id')}")
        print(f"    Created: {payment.get('created_at')}")
    
    # 5. PAYMENT_DETAILS
    print("\n📋 PAYMENT_DETAILS")
    print("-" * 40)
    payment_details_result = supabase.table('payment_details').select('*').execute()
    print(f"Total payment details: {len(payment_details_result.data)}")
    for detail in payment_details_result.data:
        print(f"  - Detail ID: {detail.get('id')}")
        print(f"    Payment ID: {detail.get('payment_id')}")
        print(f"    Payer Name: {detail.get('payer_name')}")
        print(f"    Method: {detail.get('payment_method_name')}")
        print(f"    SDK Response: {detail.get('sdk_response')}")
    
    # 6. ANÁLISIS DEL PROBLEMA
    print("\n🔍 ANÁLISIS DEL PROBLEMA")
    print("-" * 40)
    
    # Verificar si los pagos tienen debtor_id
    payments_with_debtor = [p for p in payments_result.data if p.get('debtor_id')]
    payments_without_debtor = [p for p in payments_result.data if not p.get('debtor_id')]
    
    print(f"Pagos CON debtor_id: {len(payments_with_debtor)}")
    print(f"Pagos SIN debtor_id: {len(payments_without_debtor)}")
    
    if payments_without_debtor:
        print("\n❌ PROBLEMA ENCONTRADO: Los siguientes pagos no tienen debtor_id:")
        for payment in payments_without_debtor:
            print(f"  - {payment.get('public_id')} (Amount: S/ {payment.get('amount')})")
    
    # 7. INTENTAR ARREGLAR EL PROBLEMA
    print("\n🔧 INTENTANDO ARREGLAR EL PROBLEMA")
    print("-" * 40)
    
    # Buscar debtors que podrían estar relacionados con los pagos
    user_units = [u.get('id') for u in units_result.data]
    print(f"IDs de unidades del usuario: {user_units}")
    
    # Buscar debtors que pertenecen a las unidades del usuario
    user_debtors = [d for d in debtors_result.data if d.get('property_id') in user_units]
    print(f"Debtors de las unidades del usuario: {len(user_debtors)}")
    
    if user_debtors:
        print("Debtors encontrados:")
        for debtor in user_debtors:
            print(f"  - {debtor.get('name')} (ID: {debtor.get('id')}) - Property: {debtor.get('property_id')}")
    
    # Buscar pagos que podrían estar relacionados con NOWPayments
    nowpayments_payments = [p for p in payments_result.data if p.get('payment_origin') == 'NOWPayments']
    print(f"\nPagos de NOWPayments: {len(nowpayments_payments)}")
    
    for payment in nowpayments_payments:
        print(f"  - {payment.get('public_id')} (Amount: S/ {payment.get('amount')}) - Debtor ID: {payment.get('debtor_id')}")
    
    # 8. CREAR DEBTORS FALTANTES SI ES NECESARIO
    print("\n🛠️ CREANDO DEBTORS FALTANTES")
    print("-" * 40)
    
    if nowpayments_payments and user_debtors:
        # Intentar asociar los pagos de NOWPayments con los debtors existentes
        for payment in nowpayments_payments:
            if not payment.get('debtor_id'):
                # Buscar un debtor que coincida con el email del usuario
                matching_debtor = None
                for debtor in user_debtors:
                    if debtor.get('email') == user.get('email'):
                        matching_debtor = debtor
                        break
                
                if matching_debtor:
                    print(f"Actualizando pago {payment.get('public_id')} con debtor_id: {matching_debtor.get('id')}")
                    try:
                        update_result = supabase.table('payments').update({
                            'debtor_id': matching_debtor.get('id')
                        }).eq('id', payment.get('id')).execute()
                        
                        if update_result.data:
                            print(f"✅ Pago {payment.get('public_id')} actualizado correctamente")
                        else:
                            print(f"❌ Error actualizando pago {payment.get('public_id')}")
                    except Exception as e:
                        print(f"❌ Error actualizando pago: {str(e)}")
                else:
                    print(f"⚠️ No se encontró debtor para el pago {payment.get('public_id')}")
    
    # 9. VERIFICAR RESULTADO FINAL
    print("\n✅ VERIFICACIÓN FINAL")
    print("-" * 40)
    
    # Verificar pagos actualizados
    updated_payments = supabase.table('payments').select('*').eq('debtor_id', user_debtors[0].get('id')).execute() if user_debtors else []
    print(f"Pagos asociados al debtor del usuario: {len(updated_payments.data)}")
    
    for payment in updated_payments.data:
        print(f"  - {payment.get('public_id')} (Amount: S/ {payment.get('amount')})")

if __name__ == "__main__":
    debug_supabase()
