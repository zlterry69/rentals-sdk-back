#!/usr/bin/env python3
"""
Script para debuggear las fechas de creación de bookings
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
USER_EMAIL = "normal@test.com"
USER_PASSWORD = "123456"

def debug_bookings_dates():
    """Debuggear las fechas de creación de bookings"""
    
    # 1. Login
    print("🔐 Iniciando sesión...")
    login_data = {
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        return
    
    token = login_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login exitoso")
    
    # 2. Obtener bookings
    print("\n📋 Obteniendo bookings...")
    bookings_response = requests.get(f"{BASE_URL}/bookings/my-bookings?page=1&limit=20", headers=headers)
    
    if bookings_response.status_code != 200:
        print(f"❌ Error obteniendo bookings: {bookings_response.status_code}")
        return
    
    bookings_data = bookings_response.json()
    bookings = bookings_data.get("bookings", [])
    
    print(f"✅ Se obtuvieron {len(bookings)} bookings")
    
    # 3. Mostrar fechas detalladas
    print("\n📅 Fechas detalladas de los primeros 10 bookings:")
    print("-" * 100)
    
    for i, booking in enumerate(bookings[:10], 1):
        public_id = booking.get("public_id", "")
        created_at = booking.get("created_at", "")
        updated_at = booking.get("updated_at", "")
        booking_date = booking.get("booking_date", "")
        check_in = booking.get("check_in_date", "")
        check_out = booking.get("check_out_date", "")
        total_amount = booking.get("total_amount", 0)
        
        # Parsear fechas
        try:
            if created_at:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            else:
                created_str = "Sin fecha"
        except:
            created_str = created_at
        
        try:
            if updated_at:
                updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                updated_str = updated_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            else:
                updated_str = "Sin fecha"
        except:
            updated_str = updated_at
        
        print(f"{i:2d}. {public_id}")
        print(f"    Created: {created_str}")
        print(f"    Updated: {updated_str}")
        print(f"    Booking: {booking_date} | Check-in: {check_in} | Check-out: {check_out}")
        print(f"    Amount: S/ {total_amount}")
        print()
    
    # 4. Verificar si hay bookings con la misma fecha de creación
    print("🔍 Verificando duplicados en created_at...")
    created_dates = []
    for booking in bookings:
        created_at = booking.get("created_at", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_dates.append((dt, booking.get("public_id", "")))
            except:
                pass
    
    # Agrupar por fecha
    from collections import defaultdict
    date_groups = defaultdict(list)
    for dt, public_id in created_dates:
        date_groups[dt].append(public_id)
    
    duplicates = {dt: ids for dt, ids in date_groups.items() if len(ids) > 1}
    
    if duplicates:
        print("⚠️  Se encontraron bookings con la misma fecha de creación:")
        for dt, ids in duplicates.items():
            print(f"  {dt}: {ids}")
    else:
        print("✅ No hay duplicados en created_at")
    
    # 5. Mostrar el booking específico que mencionaste (S/ 484)
    print("\n🎯 Buscando booking de S/ 484...")
    target_booking = None
    for booking in bookings:
        if booking.get("total_amount") == 484.0:
            target_booking = booking
            break
    
    if target_booking:
        print(f"✅ Encontrado: {target_booking.get('public_id')}")
        print(f"   Created: {target_booking.get('created_at')}")
        print(f"   Updated: {target_booking.get('updated_at')}")
        print(f"   Position: {bookings.index(target_booking) + 1}")
    else:
        print("❌ No se encontró el booking de S/ 484")

if __name__ == "__main__":
    debug_bookings_dates()
