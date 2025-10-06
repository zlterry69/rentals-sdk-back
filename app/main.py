from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog, uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db, get_supabase
from app.routers import (
    health, auth, currencies, process_status, banks,
    payments, invoices
)
from app.routers import debtors, units, reviews, bookings, notifications, admin, payment_accounts, favorites, leases, webhooks
from app.utils.logging import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting RENTALS-BACK application")
    await init_db()
    logger.info("Database connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RENTALS-BACK application")

# Create FastAPI app
app = FastAPI(
    title="RENTALS-BACK API",
    description="Backend principal del sistema de alquileres",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(currencies.router, prefix="/currencies", tags=["Currencies"])
app.include_router(process_status.router, prefix="/process-status", tags=["Process Status"])
app.include_router(banks.router, prefix="/banks", tags=["Banks"])
app.include_router(debtors.router, prefix="/debtors", tags=["Debtors"])
app.include_router(units.router, prefix="/units", tags=["Units"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
app.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
app.include_router(payment_accounts.router, prefix="/payment-accounts", tags=["Payment Accounts"])
app.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])
app.include_router(leases.router, prefix="/leases", tags=["Leases"])
app.include_router(webhooks.router, tags=["Webhooks"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "RENTALS-BACK API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Favicon endpoint to avoid 404 errors
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {"message": "No favicon configured"}

# Supabase initialization is handled in handler.py for Lambda

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
