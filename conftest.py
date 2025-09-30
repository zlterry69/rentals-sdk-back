"""
Test configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os
from unittest.mock import Mock, patch

# Set test environment - NO external services needed
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"

# Mock database - tests won't connect to real DB
os.environ["SUPABASE_DB_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"

# Mock AWS - tests won't upload to real S3
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-east-1"

# Mock SDK - tests won't call external APIs
os.environ["RENTALS_SDK_URL"] = "http://test-sdk"
os.environ["RENTALS_SDK_API_KEY"] = "test-key"

# Optional variables (not required for basic tests)
os.environ.setdefault("RENTALS_BACK_URL", "http://test-back")
os.environ.setdefault("RENTALS_FRONT_URL", "http://test-front")
os.environ.setdefault("NOWPAYMENTS_API_KEY", "test-key")

from app.main import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    with patch('app.database.get_supabase') as mock:
        mock_client = Mock()
        mock_table = Mock()
        mock_client.table.return_value = mock_table
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing."""
    with patch('app.utils.s3.get_s3_client') as mock:
        mock_client = Mock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_debtor():
    """Sample debtor data for testing."""
    return {
        "name": "Juan Pérez",
        "document_number": "12345678",
        "phone": "+51987654321",
        "email": "juan.perez@email.com"
    }


@pytest.fixture
def sample_unit():
    """Sample unit data for testing."""
    return {
        "floor": "5",
        "unit_type": "apartment",
        "label": "5A"
    }


@pytest.fixture
def sample_payment():
    """Sample payment data for testing."""
    return {
        "debtor_id": "deb_123456789",
        "period": "2024-01",
        "amount": 1500.00,
        "currency_code": "PEN",
        "method": "transfer",
        "due_date": "2024-01-15"
    }


@pytest.fixture
def auth_headers():
    """Generate auth headers for testing."""
    from app.utils.auth import create_access_token
    token = create_access_token(data={"sub": "test_user"})
    return {"Authorization": f"Bearer {token}"}
