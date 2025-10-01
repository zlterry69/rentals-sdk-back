#!/usr/bin/env python3
"""
Script para verificar si existe una reserva específica
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client, Client
from app.config import settings

def check_booking():
    # Usar las credenciales del backend
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    print("🔍 VERIFICANDO RESERVA")
    print("="*50)
    
    booking_id = 'bkg_IOWxQ7sgOoRA'
    print(f"Buscando reserva: {booking_id}")
    
    # Buscar la reserva
    result = supabase.table('bookings').select('id, public_id, status_id, guest_user_id, unit_id').eq('public_id', booking_id).execute()
    
    if result.data:
        print(f"✅ Reserva encontrada: {result.data[0]}")
    else:
        print("❌ Reserva no encontrada")
        
        # Buscar reservas similares
        print("\n🔍 Buscando reservas similares...")
        similar_result = supabase.table('bookings').select('id, public_id, status_id').like('public_id', 'bkg_%').order('created_at', desc=True).limit(5).execute()
        
        if similar_result.data:
            print("Reservas recientes:")
            for booking in similar_result.data:
                print(f"  - {booking['public_id']} (ID: {booking['id']})")
        else:
            print("No hay reservas en la base de datos")

if __name__ == "__main__":
    check_booking()
