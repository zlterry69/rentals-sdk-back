"""
Authentication utilities
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from passlib.context import CryptContext

from app.config import settings

logger = structlog.get_logger()
security = HTTPBearer()

# Password hashing context
import os
if os.getenv("ENVIRONMENT") == "test":
    # Use simple hashing for tests to avoid bcrypt version conflicts
    pwd_context = None
else:
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    except Exception:
        # Fallback for environments with bcrypt issues
        pwd_context = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user info
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # For now, return a mock user
        # In a real implementation, you would fetch user from database
        return {
            "id": user_id,
            "email": payload.get("email"),
            "name": payload.get("name", "User"),
            "role": payload.get("role", "user")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None
    except Exception as e:
        logger.error("Token verification error", error=str(e))
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token"""
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None
    except Exception as e:
        logger.error("Token verification error", error=str(e))
        return None


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt or fallback"""
    if pwd_context:
        return pwd_context.hash(password)
    else:
        # Fallback for testing - NOT for production
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    if pwd_context:
        return pwd_context.verify(plain_password, hashed_password)
    else:
        # Fallback for testing - NOT for production
        import hashlib
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username and password"""
    try:
        # This would normally fetch from database
        # For now, we'll mock the database call
        from app.database import fetch_one
        
        user = await fetch_one(
            "SELECT * FROM users WHERE username = $1 AND is_active = TRUE",
            (username,)
        )
        
        if not user:
            return None
        
        if not verify_password(password, user["password_hash"]):
            return None
        
        return user
        
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        return None


# Optional: Mock authentication for development
async def get_mock_user() -> Dict[str, Any]:
    """Get mock user for development/testing"""
    return {
        "id": "user_123",
        "email": "test@example.com",
        "name": "Test User",
        "role": "admin"
    }
