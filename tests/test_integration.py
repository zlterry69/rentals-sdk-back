"""
Integration tests for the complete rental system workflow
"""
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, date


class TestRentalSystemIntegration:
    """Test complete rental system workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_rental_workflow(self, async_client, auth_headers):
        """Test complete workflow: create debtor -> unit -> lease -> payment -> invoice"""
        
        # Step 1: Create a debtor
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
            
            debtor_response = await async_client.post(
                "/debtors", 
                json=debtor_data, 
                headers=auth_headers
            )
            
            assert debtor_response.status_code == 201
            debtor = debtor_response.json()
            assert debtor["public_id"] == mock_debtor_id
        
        # Step 2: Create a unit
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
            
            unit_response = await async_client.post(
                "/units", 
                json=unit_data, 
                headers=auth_headers
            )
            
            assert unit_response.status_code == 201
            unit = unit_response.json()
            assert unit["public_id"] == mock_unit_id
        
        # Step 3: Create a payment
        payment_data = {
            "debtor_id": mock_debtor_id,
            "period": "2024-01",
            "amount": 1500.00,
            "currency_code": "PEN",
            "method": "transfer",
            "due_date": "2024-01-15"
        }
        
        mock_payment_id = "pay_123456789"
        mock_debtor_fetch = {"id": "uuid1", "public_id": mock_debtor_id, "name": "Juan Pérez"}
        mock_currency = {"id": "uuid2", "code": "PEN", "name": "Soles Peruanos"}
        mock_status = {"id": "uuid3", "code": "PENDING"}
        
        with patch('app.routers.payments.fetch_one') as mock_fetch, \
             patch('app.routers.payments.execute_query') as mock_execute, \
             patch('app.utils.id_generator.make_public_id') as mock_id:
            
            mock_id.return_value = mock_payment_id
            mock_fetch.side_effect = [mock_debtor_fetch, mock_currency, mock_status]
            mock_execute.return_value = None
            
            payment_response = await async_client.post(
                "/payments", 
                json=payment_data, 
                headers=auth_headers
            )
            
            assert payment_response.status_code == 201
            payment = payment_response.json()
            assert payment["public_id"] == mock_payment_id
        
        # Step 4: Create invoice for payment
        invoice_data = {
            "payment_id": mock_payment_id,
            "origin": "mercadopago",
            "amount": 1500.00,
            "currency_code": "PEN"
        }
        
        mock_invoice_id = "inv_123456789"
        mock_payment_fetch = {
            "id": "uuid1", 
            "public_id": mock_payment_id, 
            "amount": 1500.00,
            "debtor_id": "uuid_debtor"
        }
        mock_currency_fetch = {"id": "uuid2", "code": "PEN"}
        mock_method = {
            "id": "uuid3",
            "code": "mercadopago",
            "name": "MercadoPago",
            "config": {"api_url": "https://api.mercadopago.com", "access_token": "test-token"}
        }
        
        with patch('app.routers.invoices.fetch_one') as mock_fetch, \
             patch('app.routers.invoices.execute_query') as mock_execute, \
             patch('app.utils.id_generator.make_public_id') as mock_id:
            
            mock_id.return_value = mock_invoice_id
            mock_fetch.side_effect = [mock_payment_fetch, mock_currency_fetch, mock_method]
            mock_execute.return_value = None
            
            invoice_response = await async_client.post(
                "/invoices", 
                json=invoice_data, 
                headers=auth_headers
            )
            
            assert invoice_response.status_code == 201
            invoice = invoice_response.json()
            assert invoice["public_id"] == mock_invoice_id
        
        # Step 5: Confirm payment
        confirm_data = {
            "reference": "TXN123456",
            "notes": "Pago confirmado por transferencia"
        }
        
        mock_payment_fetch = {
            "id": "uuid1",
            "public_id": mock_payment_id,
            "status": "PENDING",
            "amount": 1500.00
        }
        mock_paid_status = {"id": "uuid2", "code": "PAID"}
        
        with patch('app.routers.payments.fetch_one') as mock_fetch, \
             patch('app.routers.payments.execute_query') as mock_execute:
            
            mock_fetch.side_effect = [mock_payment_fetch, mock_paid_status]
            mock_execute.return_value = None
            
            confirm_response = await async_client.post(
                f"/payments/{mock_payment_id}/confirm", 
                json=confirm_data, 
                headers=auth_headers
            )
            
            assert confirm_response.status_code == 200
            confirmed_payment = confirm_response.json()
            assert confirmed_payment["status"] == "PAID"
    
    @pytest.mark.asyncio
    async def test_payment_webhook_integration(self, async_client):
        """Test payment webhook processing integration"""
        
        # Test NOWPayments webhook
        nowpayments_payload = {
            "payment_status": "finished",
            "order_id": "inv_123456789",
            "payment_id": "now_payment_123",
            "price_amount": 1500.00,
            "price_currency": "USD",
            "pay_amount": 0.05,
            "pay_currency": "BTC"
        }
        
        mock_invoice = {
            "id": "uuid_invoice",
            "public_id": "inv_123456789",
            "payment_id": "uuid_payment",
            "status": "PENDING"
        }
        
        with patch('app.routers.invoices.fetch_one') as mock_fetch, \
             patch('app.routers.invoices.execute_query') as mock_execute:
            
            mock_fetch.return_value = mock_invoice
            mock_execute.return_value = None
            
            response = await async_client.post(
                "/invoices/webhooks/nowpayments",
                json=nowpayments_payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_currency_sync_integration(self, async_client, auth_headers):
        """Test currency synchronization from payment providers"""
        
        # Mock currency service responses
        mock_currencies = {
            "nowpayments": [
                {"code": "BTC", "name": "Bitcoin", "type": "crypto", "provider": "nowpayments", "decimals": 8},
                {"code": "ETH", "name": "Ethereum", "type": "crypto", "provider": "nowpayments", "decimals": 18}
            ],
            "mercadopago": [
                {"code": "PEN", "name": "Soles Peruanos", "type": "fiat", "provider": "mercadopago", "decimals": 2}
            ],
            "izipay": [
                {"code": "USD", "name": "US Dollar", "type": "fiat", "provider": "izipay", "decimals": 2}
            ]
        }
        
        with patch('app.services.currency_service.CurrencyService.get_all_currencies') as mock_get_currencies, \
             patch('app.database.fetch_one') as mock_fetch, \
             patch('app.database.execute_query') as mock_execute:
            
            mock_get_currencies.return_value = mock_currencies
            mock_fetch.return_value = None  # Currency doesn't exist
            mock_execute.return_value = None
            
            # This would be called by a scheduled task or admin endpoint
            from app.services.currency_service import CurrencyService
            currency_service = CurrencyService()
            
            await currency_service.sync_currencies_to_db()
            
            # Verify currencies were synced (4 currencies total)
            assert mock_execute.call_count == 4
    
    @pytest.mark.asyncio
    async def test_pdf_generation_integration(self, async_client, auth_headers):
        """Test PDF generation integration"""
        
        invoice_id = "inv_123456789"
        
        mock_invoice_data = {
            'public_id': invoice_id,
            'invoice_number': 'INV-2024-001',
            'amount': 1500.00,
            'currency_code': 'PEN',
            'debtor_name': 'Juan Pérez',
            'period': '2024-01',
            'status': 'PAID',
            'created_at': datetime.now(),
            'origin': 'mercadopago',
            'document_number': '12345678',
            'debtor_email': 'juan@email.com'
        }
        
        with patch('app.services.pdf_service.PDFService._get_invoice_data') as mock_get_data, \
             patch('app.services.pdf_service.PDFService.s3_service.upload_file') as mock_upload, \
             patch('app.services.pdf_service.execute_query') as mock_execute:
            
            mock_get_data.return_value = mock_invoice_data
            mock_upload.return_value = 'https://s3.amazonaws.com/bucket/invoice.pdf'
            mock_execute.return_value = None
            
            from app.services.pdf_service import PDFService
            pdf_service = PDFService()
            
            pdf_url = await pdf_service.generate_invoice_pdf(invoice_id)
            
            assert pdf_url == 'https://s3.amazonaws.com/bucket/invoice.pdf'
            mock_upload.assert_called_once()
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, async_client, auth_headers):
        """Test error handling across the system"""
        
        # Test creating payment with invalid debtor
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
            data = response.json()
            assert "not found" in data["detail"].lower()
        
        # Test creating invoice with invalid payment
        invoice_data = {
            "payment_id": "pay_nonexistent",
            "origin": "mercadopago",
            "amount": 1500.00,
            "currency_code": "PEN"
        }
        
        with patch('app.routers.invoices.fetch_one') as mock_fetch:
            mock_fetch.return_value = None  # Payment not found
            
            response = await async_client.post(
                "/invoices", 
                json=invoice_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_authentication_integration(self, async_client):
        """Test authentication integration across endpoints"""
        
        # Test accessing protected endpoint without auth
        response = await async_client.get("/debtors")
        assert response.status_code == 401
        
        # Test accessing protected endpoint with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_client.get("/debtors", headers=headers)
        assert response.status_code == 401
        
        # Test login and access protected endpoint
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
            
            login_response = await async_client.post("/auth/login", json=login_data)
            assert login_response.status_code == 200
            
            token_data = login_response.json()
            auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            
            # Now access protected endpoint with valid token
            mock_debtors = [{"id": "uuid1", "public_id": "deb_123", "name": "Test Debtor"}]
            
            with patch('app.routers.debtors.fetch_all') as mock_fetch:
                mock_fetch.return_value = mock_debtors
                
                protected_response = await async_client.get("/debtors", headers=auth_headers)
                assert protected_response.status_code == 200
                data = protected_response.json()
                assert len(data) == 1
