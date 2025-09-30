#!/usr/bin/env python3
"""
Script para iniciar el servidor FastAPI
"""

import os
import subprocess
import sys

# Configurar variables de entorno
os.environ.update({
    'SUPABASE_URL': 'https://auwboqgfgmqmuqsguiaa.supabase.co',
    'SUPABASE_ANON_KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF1d2JvcWdmZ21xbXVxc2d1aWFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg5MzA3MDIsImV4cCI6MjA3NDUwNjcwMn0.yaxTq4F7o-6BL4s9bVJpa41WcaSkXqtR29tl-6XC668',
    'SUPABASE_SERVICE_ROLE_KEY': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF1d2JvcWdmZ21xbXVxc2d1aWFhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMDcwMiwiZXhwIjoyMDc0NTA2NzAyfQ.CWlF9RvK79_O71n_gzJhMz5EbVYXEhT8TL9gsxg1Zuo',
    'JWT_SECRET': 'mi_jwt_secret_super_seguro_2024',
    'JWT_ALGORITHM': 'HS256',
    'JWT_EXPIRATION': '3600',
    'LOG_LEVEL': 'INFO',
    'ENVIRONMENT': 'development',
    'CORS_ORIGINS': 'http://localhost:3000,http://localhost:8000',
    'RENTALS_FRONT_URL': 'http://localhost:3000',
    'RENTALS_BACK_URL': 'http://localhost:8000',
    'S3_BUCKET': 'rentals-invoices-dev',
    'AWS_REGION': 'us-east-1'
})

def main():
    print("🚀 Iniciando RENTALS-BACK FastAPI Server")
    print("-" * 50)
    print("📍 URL: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🔄 Recarga automática activada")
    print("-" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--log-level", "info"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
