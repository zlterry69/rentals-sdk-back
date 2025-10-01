#!/usr/bin/env python3
"""
Script para arreglar las relaciones de pagos en Supabase
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client
from app.config import settings

def fix_payments():
    # Usar las credenciales del backend
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    print("🔧 ARREGLANDO RELACIONES DE PAGOS")
    print("="*80)
    
    # 1. OBTENER USUARIO
    print("\n👤 OBTENIENDO USUARIO")
    print("-" * 40)
    user_result = supabase.table('users').select('*').eq('email', 'normal@test.com').execute()
    if not user_result.data:
        print("❌ Usuario no encontrado")
        return
    
    user = user_result.data[0]
    user_id = user.get('id')
    print(f"✅ Usuario: {user.get('email')} (ID: {user_id})")
    
    # 2. OBTENER UNIDADES DEL USUARIO
    print("\n🏠 OBTENIENDO UNIDADES DEL USUARIO")
    print("-" * 40)
    units_result = supabase.table('units').select('*').eq('owner_id', user_id).execute()
    user_units = units_result.data
    print(f"✅ Unidades encontradas: {len(user_units)}")
    for unit in user_units:
        print(f"  - {unit.get('title')} (ID: {unit.get('id')})")
    
    # 3. OBTENER DEBTORS DE LAS UNIDADES DEL USUARIO
    print("\n👥 OBTENIENDO DEBTORS DE LAS UNIDADES")
    print("-" * 40)
    unit_ids = [u.get('id') for u in user_units]
    debtors_result = supabase.table('debtors').select('*').in_('property_id', unit_ids).execute()
    user_debtors = debtors_result.data
    print(f"✅ Debtors encontrados: {len(user_debtors)}")
    for debtor in user_debtors:
        print(f"  - {debtor.get('name')} (ID: {debtor.get('id')}) - Property: {debtor.get('property_id')}")
    
    # 4. OBTENER TODOS LOS PAGOS
    print("\n💰 OBTENIENDO TODOS LOS PAGOS")
    print("-" * 40)
    payments_result = supabase.table('payments').select('*').execute()
    all_payments = payments_result.data
    print(f"✅ Total pagos: {len(all_payments)}")
    
    # 5. IDENTIFICAR PAGOS SIN DEBTOR_ID
    print("\n🔍 IDENTIFICANDO PAGOS SIN DEBTOR_ID")
    print("-" * 40)
    payments_without_debtor = [p for p in all_payments if not p.get('debtor_id')]
    print(f"❌ Pagos sin debtor_id: {len(payments_without_debtor)}")
    
    for payment in payments_without_debtor:
        print(f"  - {payment.get('public_id')} (Amount: S/ {payment.get('amount')}) - Method: {payment.get('method')}")
    
    # 6. BUSCAR PAGOS DE NOWPAYMENTS
    print("\n🚀 BUSCANDO PAGOS DE NOWPAYMENTS")
    print("-" * 40)
    nowpayments_payments = [p for p in payments_without_debtor if p.get('payment_origin') == 'NOWPayments']
    print(f"✅ Pagos de NOWPayments sin debtor_id: {len(nowpayments_payments)}")
    
    # 7. CREAR DEBTOR PARA EL USUARIO SI NO EXISTE
    print("\n🛠️ CREANDO/VERIFICANDO DEBTOR PARA EL USUARIO")
    print("-" * 40)
    
    # Buscar si ya existe un debtor para el usuario en sus unidades
    user_debtor = None
    for debtor in user_debtors:
        if debtor.get('email') == user.get('email'):
            user_debtor = debtor
            break
    
    if not user_debtor and user_units:
        print("⚠️ No existe debtor para el usuario, creando uno...")
        try:
            # Crear debtor para el usuario
            debtor_data = {
                'name': user.get('full_name', 'Usuario'),
                'email': user.get('email'),
                'phone': user.get('phone'),
                'property_id': user_units[0].get('id'),  # Usar la primera unidad
                'owner_id': user_id,
                'full_name': user.get('full_name', 'Usuario')
            }
            
            debtor_result = supabase.table('debtors').insert(debtor_data).execute()
            if debtor_result.data:
                user_debtor = debtor_result.data[0]
                print(f"✅ Debtor creado: {user_debtor.get('id')}")
            else:
                print("❌ Error creando debtor")
                return
        except Exception as e:
            print(f"❌ Error creando debtor: {str(e)}")
            return
    else:
        print(f"✅ Debtor existente: {user_debtor.get('id')}")
    
    # 8. ASOCIAR PAGOS CON EL DEBTOR
    print("\n🔗 ASOCIANDO PAGOS CON EL DEBTOR")
    print("-" * 40)
    
    if user_debtor and nowpayments_payments:
        for payment in nowpayments_payments:
            print(f"Actualizando pago {payment.get('public_id')}...")
            try:
                update_result = supabase.table('payments').update({
                    'debtor_id': user_debtor.get('id')
                }).eq('id', payment.get('id')).execute()
                
                if update_result.data:
                    print(f"✅ Pago {payment.get('public_id')} actualizado correctamente")
                else:
                    print(f"❌ Error actualizando pago {payment.get('public_id')}")
            except Exception as e:
                print(f"❌ Error actualizando pago: {str(e)}")
    else:
        print("⚠️ No hay debtor o pagos para asociar")
    
    # 9. VERIFICAR RESULTADO
    print("\n✅ VERIFICACIÓN FINAL")
    print("-" * 40)
    
    # Verificar pagos actualizados
    updated_payments = supabase.table('payments').select('*').eq('debtor_id', user_debtor.get('id')).execute() if user_debtor else []
    print(f"Pagos asociados al debtor del usuario: {len(updated_payments.data)}")
    
    for payment in updated_payments.data:
        print(f"  - {payment.get('public_id')} (Amount: S/ {payment.get('amount')}) - Method: {payment.get('method')}")
    
    print("\n🎉 PROCESO COMPLETADO")
    print("Ahora deberías poder ver los pagos en la página de pagos del frontend.")

if __name__ == "__main__":
    fix_payments()
