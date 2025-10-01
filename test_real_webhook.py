#!/usr/bin/env python3
"""
Script para probar el webhook con el booking_id real
"""
import requests
import json

def test_real_webhook():
    url = "http://localhost:8000/webhooks/nowpayments"
    
    # Usar el booking_id real que existe
    test_data = {
        "payment_id": "DEMO_123456789",
        "order_id": "bkg_IOWxQ7sgOoRA",  # Este es el booking_id real que existe
        "payment_status": "finished",
        "amount": 484.0,
        "currency": "PEN",
        "crypto_amount": 0.121,
        "crypto_currency": "ETH"
    }
    
    print("🧪 Probando webhook con booking_id real...")
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
    test_real_webhook()
