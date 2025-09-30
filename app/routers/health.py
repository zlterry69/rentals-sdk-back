from fastapi import APIRouter, Depends
from app.utils.logging import get_request_logger

router = APIRouter()

@router.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RENTALS-BACK",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    # TODO: Add database connection check
    return {
        "status": "ready",
        "database": "connected",
        "timestamp": "2024-01-01T00:00:00Z"
    }
