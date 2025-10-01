from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = "https://auwboqgfgmqmuqsguiaa.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF1d2JvcWdmZ21xbXVxc2d1aWFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg5MzA3MDIsImV4cCI6MjA3NDUwNjcwMn0.yaxTq4F7o-6BL4s9bVJpa41WcaSkXqtR29tl-6XC668"
    SUPABASE_SERVICE_ROLE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF1d2JvcWdmZ21xbXVxc2d1aWFhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1ODkzMDcwMiwiZXhwIjoyMDc0NTA2NzAyfQ.CWlF9RvK79_O71n_gzJhMz5EbVYXEhT8TL9gsxg1Zuo"
    
    # Database (legacy - mantenemos por compatibilidad)
    SUPABASE_DB_URL: str = "postgresql://postgres:D6eg0sc60.@db.auwboqgfgmqmuqsguiaa.supabase.co:5432/postgres"

    # JWT
    JWT_SECRET: str = "default-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    
    # RENTALS-SDK
    RENTALS_SDK_URL: str = "http://localhost:8001"
    RENTALS_SDK_API_KEY: str = "default-api-key"
    
    # URLs for payment redirects
    RENTALS_FRONT_URL: str = "https://rentals-sdk-front.vercel.app"
    RENTALS_BACK_URL: str = "https://r3k8sn86cl.execute-api.us-east-1.amazonaws.com/Prod"
    RENTALS_SDK_URL: str = "https://gxloif6egd.execute-api.us-east-1.amazonaws.com/Prod"
    
    # Payment provider API keys
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    IZIPAY_API_KEY: str = ""
    NOWPAYMENTS_API_KEY: str = ""
    
    # Application
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"
    CORS_ORIGINS: List[str] = ["https://rentals-sdk-front.vercel.app", "https://gxloif6egd.execute-api.us-east-1.amazonaws.com/Prod"]
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Override CORS origins if environment variable is set
if os.getenv("CORS_ORIGINS"):
    settings.CORS_ORIGINS = os.getenv("CORS_ORIGINS").split(",")
