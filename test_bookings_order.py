#!/usr/bin/env python3
"""
Script para probar el ordenamiento de bookings en el backend
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
USER_EMAIL = "normal@test.com"
USER_PASSWORD = "123456"

def test_bookings_order():
    """Probar el ordenamiento de bookings"""
    
    # 1. Login
    print("🔐 Iniciando sesión...")
    login_data = {
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    }
    
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if login_response.status_code != 200:
        print(f"❌ Error en login: {login_response.status_code}")
        print(login_response.text)
        return
    
    token = login_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login exitoso")
    
    # 2. Obtener bookings
    print("\n📋 Obteniendo bookings...")
    bookings_response = requests.get(f"{BASE_URL}/bookings/my-bookings?page=1&limit=20", headers=headers)
    
    if bookings_response.status_code != 200:
        print(f"❌ Error obteniendo bookings: {bookings_response.status_code}")
        print(bookings_response.text)
        return
    
    bookings_data = bookings_response.json()
    bookings = bookings_data.get("bookings", [])
    
    print(f"✅ Se obtuvieron {len(bookings)} bookings")
    
    # 3. Mostrar orden de bookings
    print("\n📅 Orden de bookings (más recientes primero):")
    print("-" * 80)
    
    for i, booking in enumerate(bookings, 1):
        created_at = booking.get("created_at", "")
        public_id = booking.get("public_id", "")
        unit_title = booking.get("units", {}).get("title", "Sin título")
        total_amount = booking.get("total_amount", 0)
        status = booking.get("process_status", {}).get("code", "UNKNOWN")
        
        # Parsear fecha para mostrar
        try:
            if created_at:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                formatted_date = "Sin fecha"
        except:
            formatted_date = created_at
        
        print(f"{i:2d}. {public_id} | {unit_title} | S/ {total_amount} | {status} | {formatted_date}")
    
    # 4. Verificar ordenamiento
    print("\n🔍 Verificando ordenamiento...")
    
    # Extraer fechas de creación
    creation_dates = []
    for booking in bookings:
        created_at = booking.get("created_at", "")
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                creation_dates.append(dt)
            except:
                creation_dates.append(datetime.min)
        else:
            creation_dates.append(datetime.min)
    
    # Verificar si está ordenado descendente
    is_sorted = all(creation_dates[i] >= creation_dates[i+1] for i in range(len(creation_dates)-1))
    
    if is_sorted:
        print("✅ Los bookings están ordenados correctamente (más recientes primero)")
    else:
        print("❌ Los bookings NO están ordenados correctamente")
        
        # Mostrar las primeras fechas para debug
        print("\nPrimeras 5 fechas:")
        for i, date in enumerate(creation_dates[:5]):
            print(f"  {i+1}. {date}")
    
    # 5. Mostrar información de paginación
    pagination = bookings_data.get("pagination", {})
    print(f"\n📊 Paginación:")
    print(f"  - Página actual: {pagination.get('page', 1)}")
    print(f"  - Límite por página: {pagination.get('limit', 20)}")
    print(f"  - Total de bookings: {pagination.get('total', 0)}")

if __name__ == "__main__":
    test_bookings_order()
