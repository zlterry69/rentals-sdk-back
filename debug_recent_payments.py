#!/usr/bin/env python3
"""
Script para debuggear el endpoint /payments/recent
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client
from app.config import settings

def debug_recent_payments():
    # Usar las credenciales del backend
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    print("🔍 DEBUGGING /payments/recent ENDPOINT")
    print("="*80)
    
    # Usuario de prueba
    user_id = 'cd7c6fe6-43c5-4f32-8691-e53a70481a24'
    print(f"👤 User ID: {user_id}")
    
    # 1. Obtener unidades del usuario
    print("\n🏠 PASO 1: Obtener unidades del usuario")
    print("-" * 50)
    owned_units_result = supabase.table('units').select('id, title, owner_id').eq('owner_id', user_id).execute()
    owned_unit_ids = [unit['id'] for unit in owned_units_result.data]
    print(f"✅ Unidades encontradas: {len(owned_unit_ids)}")
    for unit in owned_units_result.data:
        print(f"  - {unit['title']} (ID: {unit['id']})")
    
    if not owned_unit_ids:
        print("❌ Usuario no tiene unidades - este es el problema!")
        return
    
    # 2. Obtener debtors para las unidades del usuario
    print("\n👥 PASO 2: Obtener debtors de las unidades")
    print("-" * 50)
    debtors_result = supabase.table('debtors').select('id, property_id, owner_id, name, email').in_('property_id', owned_unit_ids).execute()
    print(f"✅ Debtors encontrados: {len(debtors_result.data)}")
    for debtor in debtors_result.data:
        print(f"  - {debtor['name']} (ID: {debtor['id']}) - Property: {debtor['property_id']} - Owner: {debtor['owner_id']}")
    
    if not debtors_result.data:
        print("❌ No hay debtors para las unidades del usuario - este es el problema!")
        return
    
    # 3. Obtener pagos para estos debtors
    print("\n💰 PASO 3: Obtener pagos de los debtors")
    print("-" * 50)
    debtor_ids = [debtor['id'] for debtor in debtors_result.data]
    
    result = supabase.table('payments').select('''
        *,
        debtors!inner(full_name, name, email, phone, property_id, owner_id),
        process_status!inner(code, description)
    ''').in_('debtor_id', debtor_ids).order('created_at', desc=True).limit(10).execute()
    
    print(f"✅ Pagos encontrados: {len(result.data)}")
    for payment in result.data:
        print(f"  - {payment['public_id']} - {payment['amount']} - {payment['method']} - {payment['debtors']['name']}")
    
    # 4. Verificar la query exacta que usa el endpoint
    print("\n🔍 PASO 4: Verificar query exacta del endpoint")
    print("-" * 50)
    
    # Simular exactamente lo que hace el endpoint
    try:
        # Esta es la query exacta del endpoint
        endpoint_result = supabase.table('payments').select('''
            *,
            debtors!inner(full_name, name, email, phone, property_id, owner_id),
            process_status!inner(code, description)
        ''').in_('debtor_id', debtor_ids).order('created_at', desc=True).limit(10).execute()
        
        print(f"✅ Query del endpoint devuelve: {len(endpoint_result.data)} pagos")
        
        if endpoint_result.data:
            print("🎉 ¡El endpoint debería funcionar correctamente!")
            print("\nPagos que debería devolver:")
            for payment in endpoint_result.data:
                print(f"  - {payment['public_id']} - S/ {payment['amount']} - {payment['method']} - {payment['debtors']['name']}")
        else:
            print("❌ El endpoint no devuelve pagos - hay un problema en la query")
            
    except Exception as e:
        print(f"❌ Error en la query del endpoint: {str(e)}")
    
    # 5. Verificar si hay pagos de NOWPayments específicamente
    print("\n🚀 PASO 5: Verificar pagos de NOWPayments")
    print("-" * 50)
    
    nowpayments_result = supabase.table('payments').select('''
        *,
        debtors!inner(full_name, name, email, phone, property_id, owner_id),
        process_status!inner(code, description)
    ''').in_('debtor_id', debtor_ids).eq('payment_origin', 'NOWPayments').order('created_at', desc=True).execute()
    
    print(f"✅ Pagos de NOWPayments: {len(nowpayments_result.data)}")
    for payment in nowpayments_result.data:
        print(f"  - {payment['public_id']} - S/ {payment['amount']} - {payment['debtors']['name']}")

if __name__ == "__main__":
    debug_recent_payments()
