"""
Tests for CRUD operations: debtors, units, payments, banks
"""
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, date

from app.utils.id_generator import make_public_id


class TestDebtorsCRUD:
    """Test debtors CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_debtor_success(self, async_client, auth_headers):
        """Test successful debtor creation"""
        debtor_data = {
            "name": "Juan Pérez",
            "document_number": "12345678",
            "phone": "+51987654321",
            "email": "juan.perez@email.com"
        }
        
        mock_debtor_id = "deb_123456789"
        
        with patch('app.routers.debtors.execute_query') as mock_execute, \
             patch('app.utils.id_generator.make_public_id') as mock_id:
            
            mock_id.return_value = mock_debtor_id
            mock_execute.return_value = None
            
            response = await async_client.post(
                "/debtors", 
                json=debtor_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["public_id"] == mock_debtor_id
            assert data["name"] == debtor_data["name"]
            assert data["email"] == debtor_data["email"]
    
    @pytest.mark.asyncio
    async def test_get_debtors_list(self, async_client, auth_headers):
        """Test getting list of debtors"""
        mock_debtors = [
            {
                "id": "uuid1",
                "public_id": "deb_123456789",
                "name": "Juan Pérez",
                "document_number": "12345678",
                "phone": "+51987654321",
                "email": "juan.perez@email.com",
                "created_at": datetime.now()
            },
            {
                "id": "uuid2",
                "public_id": "deb_987654321",
                "name": "María García",
                "document_number": "87654321",
                "phone": "+51123456789",
                "email": "maria.garcia@email.com",
                "created_at": datetime.now()
            }
        ]
        
        with patch('app.routers.debtors.fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_debtors
            
            response = await async_client.get("/debtors", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Juan Pérez"
            assert data[1]["name"] == "María García"
    
    @pytest.mark.asyncio
    async def test_get_debtor_by_id_success(self, async_client, auth_headers):
        """Test getting debtor by ID"""
        debtor_id = "deb_123456789"
        mock_debtor = {
            "id": "uuid1",
            "public_id": debtor_id,
            "name": "Juan Pérez",
            "document_number": "12345678",
            "phone": "+51987654321",
            "email": "juan.perez@email.com",
            "created_at": datetime.now()
        }
        
        with patch('app.routers.debtors.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_debtor
            
            response = await async_client.get(f"/debtors/{debtor_id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["public_id"] == debtor_id
            assert data["name"] == "Juan Pérez"
    
    @pytest.mark.asyncio
    async def test_get_debtor_not_found(self, async_client, auth_headers):
        """Test getting non-existent debtor"""
        debtor_id = "deb_nonexistent"
        
        with patch('app.routers.debtors.fetch_one') as mock_fetch:
            mock_fetch.return_value = None
            
            response = await async_client.get(f"/debtors/{debtor_id}", headers=auth_headers)
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_debtor_success(self, async_client, auth_headers):
        """Test successful debtor update"""
        debtor_id = "deb_123456789"
        update_data = {
            "name": "Juan Carlos Pérez",
            "phone": "+51999888777"
        }
        
        mock_existing_debtor = {
            "id": "uuid1",
            "public_id": debtor_id,
            "name": "Juan Pérez",
            "document_number": "12345678",
            "phone": "+51987654321",
            "email": "juan.perez@email.com"
        }
        
        with patch('app.routers.debtors.fetch_one') as mock_fetch, \
             patch('app.routers.debtors.execute_query') as mock_execute:
            
            mock_fetch.return_value = mock_existing_debtor
            mock_execute.return_value = None
            
            response = await async_client.put(
                f"/debtors/{debtor_id}", 
                json=update_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == update_data["name"]
            assert data["phone"] == update_data["phone"]
    
    @pytest.mark.asyncio
    async def test_delete_debtor_success(self, async_client, auth_headers):
        """Test successful debtor deletion"""
        debtor_id = "deb_123456789"
        
        mock_debtor = {
            "id": "uuid1",
            "public_id": debtor_id,
            "name": "Juan Pérez"
        }
        
        with patch('app.routers.debtors.fetch_one') as mock_fetch, \
             patch('app.routers.debtors.execute_query') as mock_execute:
            
            mock_fetch.return_value = mock_debtor
            mock_execute.return_value = None
            
            response = await async_client.delete(f"/debtors/{debtor_id}", headers=auth_headers)
            
            assert response.status_code == 204


class TestUnitsCRUD:
    """Test units CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_unit_success(self, async_client, auth_headers):
        """Test successful unit creation"""
        unit_data = {
            "floor": "5",
            "unit_type": "apartment",
            "label": "5A"
        }
        
        mock_unit_id = "unt_123456789"
        
        with patch('app.routers.units.execute_query') as mock_execute, \
             patch('app.utils.id_generator.make_public_id') as mock_id:
            
            mock_id.return_value = mock_unit_id
            mock_execute.return_value = None
            
            response = await async_client.post(
                "/units", 
                json=unit_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["public_id"] == mock_unit_id
            assert data["floor"] == unit_data["floor"]
            assert data["unit_type"] == unit_data["unit_type"]
            assert data["label"] == unit_data["label"]
    
    @pytest.mark.asyncio
    async def test_get_units_list(self, async_client, auth_headers):
        """Test getting list of units"""
        mock_units = [
            {
                "id": "uuid1",
                "public_id": "unt_123456789",
                "floor": "5",
                "unit_type": "apartment",
                "label": "5A",
                "created_at": datetime.now()
            },
            {
                "id": "uuid2",
                "public_id": "unt_987654321",
                "floor": "3",
                "unit_type": "office",
                "label": "3B",
                "created_at": datetime.now()
            }
        ]
        
        with patch('app.routers.units.fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_units
            
            response = await async_client.get("/units", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["label"] == "5A"
            assert data[1]["label"] == "3B"
    
    @pytest.mark.asyncio
    async def test_create_unit_duplicate_label(self, async_client, auth_headers):
        """Test creating unit with duplicate label"""
        unit_data = {
            "floor": "5",
            "unit_type": "apartment",
            "label": "5A"
        }
        
        with patch('app.routers.units.execute_query') as mock_execute:
            # Simulate unique constraint violation
            mock_execute.side_effect = Exception("duplicate key value violates unique constraint")
            
            response = await async_client.post(
                "/units", 
                json=unit_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 400


class TestPaymentsCRUD:
    """Test payments CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, async_client, auth_headers):
        """Test successful payment creation"""
        payment_data = {
            "debtor_id": "deb_123456789",
            "period": "2024-01",
            "amount": 1500.00,
            "currency_code": "PEN",
            "method": "transfer",
            "due_date": "2024-01-15"
        }
        
        mock_payment_id = "pay_123456789"
        mock_debtor = {"id": "uuid1", "public_id": "deb_123456789", "name": "Juan Pérez"}
        mock_currency = {"id": "uuid2", "code": "PEN", "name": "Soles Peruanos"}
        mock_status = {"id": "uuid3", "code": "PENDING"}
        
        with patch('app.routers.payments.fetch_one') as mock_fetch, \
             patch('app.routers.payments.execute_query') as mock_execute, \
             patch('app.utils.id_generator.make_public_id') as mock_id:
            
            mock_id.return_value = mock_payment_id
            mock_fetch.side_effect = [mock_debtor, mock_currency, mock_status]
            mock_execute.return_value = None
            
            response = await async_client.post(
                "/payments", 
                json=payment_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["public_id"] == mock_payment_id
            assert data["period"] == payment_data["period"]
            assert data["amount"] == payment_data["amount"]
    
    @pytest.mark.asyncio
    async def test_get_payments_list(self, async_client, auth_headers):
        """Test getting list of payments"""
        mock_payments = [
            {
                "id": "uuid1",
                "public_id": "pay_123456789",
                "period": "2024-01",
                "amount": 1500.00,
                "method": "transfer",
                "status": "PENDING",
                "debtor_name": "Juan Pérez",
                "currency_code": "PEN",
                "created_at": datetime.now()
            },
            {
                "id": "uuid2",
                "public_id": "pay_987654321",
                "period": "2024-02",
                "amount": 1500.00,
                "method": "cash",
                "status": "PAID",
                "debtor_name": "María García",
                "currency_code": "PEN",
                "created_at": datetime.now()
            }
        ]
        
        with patch('app.routers.payments.fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_payments
            
            response = await async_client.get("/payments", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["period"] == "2024-01"
            assert data[1]["period"] == "2024-02"
    
    @pytest.mark.asyncio
    async def test_confirm_payment_success(self, async_client, auth_headers):
        """Test successful payment confirmation"""
        payment_id = "pay_123456789"
        confirm_data = {
            "reference": "TXN123456",
            "notes": "Pago confirmado por transferencia"
        }
        
        mock_payment = {
            "id": "uuid1",
            "public_id": payment_id,
            "status": "PENDING",
            "amount": 1500.00
        }
        
        mock_paid_status = {"id": "uuid2", "code": "PAID"}
        
        with patch('app.routers.payments.fetch_one') as mock_fetch, \
             patch('app.routers.payments.execute_query') as mock_execute:
            
            mock_fetch.side_effect = [mock_payment, mock_paid_status]
            mock_execute.return_value = None
            
            response = await async_client.post(
                f"/payments/{payment_id}/confirm", 
                json=confirm_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "PAID"
            assert "paid_at" in data
    
    @pytest.mark.asyncio
    async def test_create_payment_invalid_debtor(self, async_client, auth_headers):
        """Test creating payment with invalid debtor"""
        payment_data = {
            "debtor_id": "deb_nonexistent",
            "period": "2024-01",
            "amount": 1500.00,
            "currency_code": "PEN"
        }
        
        with patch('app.routers.payments.fetch_one') as mock_fetch:
            mock_fetch.return_value = None  # Debtor not found
            
            response = await async_client.post(
                "/payments", 
                json=payment_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 404


class TestBanksCRUD:
    """Test banks catalog operations"""
    
    @pytest.mark.asyncio
    async def test_get_banks_list(self, async_client):
        """Test getting list of banks"""
        mock_banks = [
            {
                "id": "uuid1",
                "public_id": "bnk_123456789",
                "code": "NOWPAY",
                "name": "NOWPayments",
                "provider_type": "gateway",
                "status": "ACTIVE",
                "created_at": datetime.now()
            },
            {
                "id": "uuid2",
                "public_id": "bnk_987654321",
                "code": "MERCADOPAGO",
                "name": "MercadoPago",
                "provider_type": "gateway",
                "status": "ACTIVE",
                "created_at": datetime.now()
            }
        ]
        
        with patch('app.routers.banks.fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_banks
            
            response = await async_client.get("/banks")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["code"] == "NOWPAY"
            assert data[1]["code"] == "MERCADOPAGO"
    
    @pytest.mark.asyncio
    async def test_get_banks_filtered_by_provider_type(self, async_client):
        """Test getting banks filtered by provider type"""
        mock_banks = [
            {
                "id": "uuid1",
                "public_id": "bnk_123456789",
                "code": "NOWPAY",
                "name": "NOWPayments",
                "provider_type": "gateway",
                "status": "ACTIVE",
                "created_at": datetime.now()
            }
        ]
        
        with patch('app.routers.banks.fetch_all') as mock_fetch:
            mock_fetch.return_value = mock_banks
            
            response = await async_client.get("/banks?provider_type=gateway")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["provider_type"] == "gateway"
    
    @pytest.mark.asyncio
    async def test_get_bank_by_code_success(self, async_client):
        """Test getting bank by code"""
        bank_code = "NOWPAY"
        mock_bank = {
            "id": "uuid1",
            "public_id": "bnk_123456789",
            "code": bank_code,
            "name": "NOWPayments",
            "provider_type": "gateway",
            "status": "ACTIVE",
            "created_at": datetime.now()
        }
        
        with patch('app.routers.banks.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_bank
            
            response = await async_client.get(f"/banks/{bank_code}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == bank_code
            assert data["name"] == "NOWPayments"
    
    @pytest.mark.asyncio
    async def test_get_bank_by_code_not_found(self, async_client):
        """Test getting non-existent bank by code"""
        bank_code = "NONEXISTENT"
        
        with patch('app.routers.banks.fetch_one') as mock_fetch:
            mock_fetch.return_value = None
            
            response = await async_client.get(f"/banks/{bank_code}")
            
            assert response.status_code == 404


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, async_client):
        """Test health check endpoint"""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
