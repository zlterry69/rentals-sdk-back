#!/usr/bin/env python3
"""
Script para probar el webhook de NOWPayments
"""
import requests
import json

def test_webhook():
    url = "http://localhost:8000/webhooks/nowpayments"
    
    # Datos de prueba
    test_data = {
        "payment_id": "DEMO_123456789",
        "order_id": "bkg_test123",  # Usar un booking_id de prueba
        "payment_status": "finished",
        "amount": 100.0,
        "currency": "PEN",
        "crypto_amount": 0.025,
        "crypto_currency": "ETH"
    }
    
    print("🧪 Probando webhook de NOWPayments...")
    print(f"📤 Enviando datos: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(url, json=test_data)
        print(f"📊 Respuesta: {response.status_code}")
        print(f"📄 Contenido: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook funcionando correctamente")
        else:
            print("❌ Error en el webhook")
            
    except Exception as e:
        print(f"❌ Error conectando al webhook: {str(e)}")

if __name__ == "__main__":
    test_webhook()
