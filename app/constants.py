"""
Configuración centralizada de URLs y constantes del backend
"""

import os
from typing import List

# URLs base para desarrollo local
LOCAL_URLS = {
    "FRONTEND": "http://localhost:3000",
    "BACKEND": "http://localhost:8000", 
    "SDK": "http://localhost:5000",
}

# URLs base para producción (configurar según tu dominio)
PRODUCTION_URLS = {
    "FRONTEND": "https://tu-frontend.vercel.app",
    "BACKEND": "https://tu-backend.vercel.app",
    "SDK": "https://tu-sdk.vercel.app",
}

# Detectar entorno
is_development = os.getenv("ENVIRONMENT", "development") == "development"
is_production = os.getenv("ENVIRONMENT", "development") == "production"

# URLs activas según el entorno
ACTIVE_URLS = LOCAL_URLS if is_development else PRODUCTION_URLS

# Configuración de URLs
FRONTEND_URL = os.getenv("RENTALS_FRONT_URL", ACTIVE_URLS["FRONTEND"])
BACKEND_URL = os.getenv("RENTALS_BACK_URL", ACTIVE_URLS["BACKEND"])
SDK_URL = os.getenv("RENTALS_SDK_URL", ACTIVE_URLS["SDK"])

# Configuración de CORS
CORS_ORIGINS = [
    FRONTEND_URL,
    BACKEND_URL,
    SDK_URL,
    "http://localhost:3000",  # Fallback para desarrollo
    "http://localhost:8000",  # Fallback para desarrollo
    "http://localhost:5000",  # Fallback para desarrollo
]

# Configuración de la aplicación
APP_CONFIG = {
    "NAME": "HogarPeru Rentals API",
    "VERSION": "1.0.0",
    "ENVIRONMENT": "development" if is_development else "production",
}

# Configuración de puertos
PORTS = {
    "BACKEND": 8000,
    "SDK": 5000,
    "FRONTEND": 3000,
}
