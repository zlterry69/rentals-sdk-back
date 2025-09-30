"""
Tests for authentication and JWT functionality
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from jose import jwt

from app.utils.auth import (
    create_access_token, 
    verify_token, 
    get_password_hash, 
    verify_password,
    authenticate_user
)
from app.config import settings


class TestAuthUtils:
    """Test authentication utilities"""
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify content
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == "test_user"
        assert decoded["role"] == "admin"
        assert "exp" in decoded
    
    def test_create_access_token_with_expires_delta(self):
        """Test JWT token creation with custom expiration"""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(decoded["exp"])
        expected_time = datetime.utcnow() + expires_delta
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_time).total_seconds()) < 60
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_token_expired(self):
        """Test token verification with expired token"""
        data = {"sub": "test_user"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta)
        
        payload = verify_token(token)
        
        assert payload is None
    
    def test_get_password_hash(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(password, hashed)
        
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(wrong_password, hashed)
        
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        username = "test_user"
        password = "test_password"
        hashed_password = get_password_hash(password)
        
        mock_user = {
            "id": "user_123",
            "username": username,
            "password_hash": hashed_password,
            "is_active": True
        }
        
        with patch('app.utils.auth.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_user
            
            result = await authenticate_user(username, password)
            
            assert result is not None
            assert result["username"] == username
            assert result["id"] == "user_123"
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        with patch('app.utils.auth.fetch_one') as mock_fetch:
            mock_fetch.return_value = None
            
            result = await authenticate_user("nonexistent", "password")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        username = "test_user"
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed_password = get_password_hash(password)
        
        mock_user = {
            "id": "user_123",
            "username": username,
            "password_hash": hashed_password,
            "is_active": True
        }
        
        with patch('app.utils.auth.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_user
            
            result = await authenticate_user(username, wrong_password)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self):
        """Test authentication with inactive user"""
        username = "test_user"
        password = "test_password"
        hashed_password = get_password_hash(password)
        
        mock_user = {
            "id": "user_123",
            "username": username,
            "password_hash": hashed_password,
            "is_active": False
        }
        
        with patch('app.utils.auth.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_user
            
            result = await authenticate_user(username, password)
            
            assert result is None


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client):
        """Test successful login"""
        login_data = {
            "username": "test_user",
            "password": "test_password"
        }
        
        mock_user = {
            "id": "user_123",
            "username": "test_user",
            "email": "test@email.com"
        }
        
        with patch('app.routers.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = mock_user
            
            response = await async_client.post("/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client):
        """Test login with invalid credentials"""
        login_data = {
            "username": "test_user",
            "password": "wrong_password"
        }
        
        with patch('app.routers.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            response = await async_client.post("/auth/login", json=login_data)
            
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_register_success(self, async_client):
        """Test successful user registration"""
        register_data = {
            "username": "new_user",
            "email": "new@email.com",
            "password": "new_password",
            "full_name": "New User"
        }
        
        mock_user_id = "user_new_123"
        
        with patch('app.routers.auth.fetch_one') as mock_fetch, \
             patch('app.routers.auth.execute_query') as mock_execute:
            
            # User doesn't exist
            mock_fetch.return_value = None
            mock_execute.return_value = None
            
            response = await async_client.post("/auth/register", json=register_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["username"] == register_data["username"]
            assert data["email"] == register_data["email"]
            assert "password" not in data  # Password should not be returned
    
    @pytest.mark.asyncio
    async def test_register_user_exists(self, async_client):
        """Test registration with existing user"""
        register_data = {
            "username": "existing_user",
            "email": "existing@email.com",
            "password": "password"
        }
        
        mock_existing_user = {
            "id": "user_123",
            "username": "existing_user"
        }
        
        with patch('app.routers.auth.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_existing_user
            
            response = await async_client.post("/auth/register", json=register_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "already exists" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client, auth_headers):
        """Test getting current user with valid token"""
        mock_user = {
            "id": "user_123",
            "username": "test_user",
            "email": "test@email.com",
            "full_name": "Test User",
            "is_active": True
        }
        
        with patch('app.routers.auth.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_user
            
            response = await async_client.get("/auth/me", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "test_user"
            assert data["email"] == "test@email.com"
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_client):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = await async_client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, async_client):
        """Test getting current user without token"""
        response = await async_client.get("/auth/me")
        
        assert response.status_code == 401
