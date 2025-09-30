"""
Tests for all services: CurrencyService, PaymentService, PDFService
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from httpx import Response
import io

from app.services.currency_service import CurrencyService
from app.services.payment_service import PaymentService, MercadoPagoProvider, IzipayProvider, NOWPaymentsProvider
from app.services.pdf_service import PDFService


class TestCurrencyService:
    """Test CurrencyService functionality"""
    
    @pytest.fixture
    def currency_service(self):
        return CurrencyService()
    
    @pytest.mark.asyncio
    async def test_get_nowpayments_currencies_success(self, currency_service):
        """Test successful NOWPayments currency fetch"""
        mock_response_data = {
            "currencies": ["btc", "eth", "usdt", "usdc", "doge"]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await currency_service._get_nowpayments_currencies()
            
            assert len(result) == 5
            assert result[0]["code"] == "BTC"
            assert result[0]["provider"] == "nowpayments"
            assert result[0]["type"] == "crypto"
            assert result[0]["decimals"] == 8
    
    @pytest.mark.asyncio
    async def test_get_nowpayments_currencies_fallback(self, currency_service):
        """Test NOWPayments fallback currencies when API fails"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("API Error"))
            
            result = await currency_service._get_nowpayments_currencies()
            
            # Should return fallback currencies
            assert len(result) == 4
            assert any(c["code"] == "BTC" for c in result)
            assert any(c["code"] == "ETH" for c in result)
            assert any(c["code"] == "USDT" for c in result)
            assert any(c["code"] == "USDC" for c in result)
    
    @pytest.mark.asyncio
    async def test_get_mercadopago_currencies(self, currency_service):
        """Test MercadoPago currencies"""
        result = await currency_service._get_mercadopago_currencies()
        
        assert len(result) >= 3
        assert any(c["code"] == "PEN" for c in result)
        assert any(c["code"] == "USD" for c in result)
        assert all(c["provider"] == "mercadopago" for c in result)
        assert all(c["type"] == "fiat" for c in result)
    
    @pytest.mark.asyncio
    async def test_get_izipay_currencies(self, currency_service):
        """Test Izipay currencies"""
        result = await currency_service._get_izipay_currencies()
        
        assert len(result) >= 2
        assert any(c["code"] == "PEN" for c in result)
        assert any(c["code"] == "USD" for c in result)
        assert all(c["provider"] == "izipay" for c in result)
        assert all(c["type"] == "fiat" for c in result)
    
    @pytest.mark.asyncio
    async def test_get_available_currencies(self, currency_service):
        """Test getting currencies by provider"""
        # Test NOWPayments
        with patch.object(currency_service, '_get_nowpayments_currencies') as mock_now:
            mock_now.return_value = [{"code": "BTC", "provider": "nowpayments"}]
            result = await currency_service.get_available_currencies("nowpayments")
            assert len(result) == 1
            assert result[0]["code"] == "BTC"
        
        # Test unknown provider
        result = await currency_service.get_available_currencies("unknown")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_all_currencies(self, currency_service):
        """Test getting all currencies from all providers"""
        with patch.object(currency_service, 'get_available_currencies') as mock_get:
            mock_get.side_effect = [
                [{"code": "BTC", "provider": "nowpayments"}],
                [{"code": "PEN", "provider": "mercadopago"}],
                [{"code": "USD", "provider": "izipay"}]
            ]
            
            result = await currency_service.get_all_currencies()
            
            assert "nowpayments" in result
            assert "mercadopago" in result
            assert "izipay" in result
            assert len(result["nowpayments"]) == 1
            assert len(result["mercadopago"]) == 1
            assert len(result["izipay"]) == 1


class TestPaymentService:
    """Test PaymentService and providers"""
    
    @pytest.fixture
    def payment_service(self):
        return PaymentService()
    
    def test_payment_service_initialization(self, payment_service):
        """Test PaymentService initializes with all providers"""
        assert 'mercadopago' in payment_service.providers
        assert 'izipay' in payment_service.providers
        assert 'nowpayments' in payment_service.providers
        
        assert isinstance(payment_service.providers['mercadopago'], MercadoPagoProvider)
        assert isinstance(payment_service.providers['izipay'], IzipayProvider)
        assert isinstance(payment_service.providers['nowpayments'], NOWPaymentsProvider)
    
    @pytest.mark.asyncio
    async def test_create_payment_url_unknown_provider(self, payment_service):
        """Test error handling for unknown provider"""
        invoice = {"origin": "unknown_provider"}
        method = {}
        
        with pytest.raises(ValueError, match="Unknown payment provider"):
            await payment_service.create_payment_url(invoice, method)
    
    @pytest.mark.asyncio
    async def test_process_webhook_unknown_provider(self, payment_service):
        """Test error handling for unknown provider webhook"""
        with pytest.raises(ValueError, match="Unknown payment provider"):
            await payment_service.process_webhook("unknown_provider", {})


class TestMercadoPagoProvider:
    """Test MercadoPago provider"""
    
    @pytest.fixture
    def provider(self):
        return MercadoPagoProvider()
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, provider):
        """Test successful MercadoPago payment creation"""
        invoice = {
            'payment_id': 'test-payment-id',
            'amount': 1500.00,
            'public_id': 'inv_123456789',
            'id': 'invoice-uuid'
        }
        method = {
            'config': {
                'api_url': 'https://api.mercadopago.com',
                'access_token': 'test-token'
            }
        }
        
        mock_payment_data = {
            'period': '2024-01',
            'debtor_name': 'Juan Pérez',
            'debtor_email': 'juan@email.com',
            'debtor_id': 'deb_123'
        }
        
        mock_mp_response = {
            'id': 'mp_preference_123',
            'init_point': 'https://www.mercadopago.com.pe/checkout/v1/redirect?pref_id=mp_preference_123'
        }
        
        with patch('app.services.payment_service.fetch_one') as mock_fetch, \
             patch('app.services.payment_service.execute_query') as mock_execute, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_fetch.return_value = mock_payment_data
            mock_execute.return_value = None
            
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_mp_response
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.create_payment(invoice, method)
            
            assert result == mock_mp_response['init_point']
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_webhook_success(self, provider):
        """Test MercadoPago webhook processing"""
        payload = {
            'data': {
                'id': 'payment_123'
            }
        }
        
        result = await provider.process_webhook(payload)
        
        assert result['status'] == 'processed'
        assert result['payment_id'] == 'payment_123'
    
    @pytest.mark.asyncio
    async def test_process_webhook_no_payment_id(self, provider):
        """Test MercadoPago webhook with no payment ID"""
        payload = {'data': {}}
        
        result = await provider.process_webhook(payload)
        
        assert result['status'] == 'ignored'
        assert result['reason'] == 'No payment ID'


class TestIzipayProvider:
    """Test Izipay provider"""
    
    @pytest.fixture
    def provider(self):
        return IzipayProvider()
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, provider):
        """Test successful Izipay payment creation"""
        invoice = {
            'payment_id': 'test-payment-id',
            'amount': 1500.00,
            'public_id': 'inv_123456789',
            'id': 'invoice-uuid'
        }
        method = {
            'config': {
                'api_key': 'test-key'
            }
        }
        
        mock_payment_data = {
            'period': '2024-01',
            'debtor_name': 'Juan Pérez',
            'debtor_email': 'juan@email.com',
            'debtor_id': 'deb_123'
        }
        
        with patch('app.services.payment_service.fetch_one') as mock_fetch, \
             patch('app.services.payment_service.execute_query') as mock_execute:
            
            mock_fetch.return_value = mock_payment_data
            mock_execute.return_value = None
            
            result = await provider.create_payment(invoice, method)
            
            expected_url = f"https://secure.izipay.pe/payment/{invoice['public_id']}"
            assert result == expected_url
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_webhook_success(self, provider):
        """Test Izipay webhook processing"""
        payload = {'status': 'paid'}
        
        result = await provider.process_webhook(payload)
        
        assert result['status'] == 'processed'


class TestNOWPaymentsProvider:
    """Test NOWPayments provider"""
    
    @pytest.fixture
    def provider(self):
        return NOWPaymentsProvider()
    
    @pytest.mark.asyncio
    async def test_create_payment_success(self, provider):
        """Test successful NOWPayments payment creation"""
        invoice = {
            'payment_id': 'test-payment-id',
            'amount': 1500.00,
            'public_id': 'inv_123456789',
            'id': 'invoice-uuid'
        }
        method = {
            'config': {
                'api_url': 'https://api.nowpayments.io',
                'api_key': 'test-api-key'
            }
        }
        
        mock_payment_data = {
            'period': '2024-01',
            'debtor_name': 'Juan Pérez',
            'debtor_email': 'juan@email.com',
            'debtor_id': 'deb_123'
        }
        
        mock_now_response = {
            'id': 'now_invoice_123',
            'invoice_url': 'https://nowpayments.io/payment/now_invoice_123'
        }
        
        with patch('app.services.payment_service.fetch_one') as mock_fetch, \
             patch('app.services.payment_service.execute_query') as mock_execute, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_fetch.return_value = mock_payment_data
            mock_execute.return_value = None
            
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_now_response
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await provider.create_payment(invoice, method)
            
            assert result == mock_now_response['invoice_url']
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_webhook_paid_status(self, provider):
        """Test NOWPayments webhook with paid status"""
        payload = {
            'payment_status': 'finished',
            'order_id': 'inv_123456789'
        }
        
        mock_invoice = {
            'id': 'invoice-uuid',
            'payment_id': 'payment-uuid'
        }
        
        with patch('app.services.payment_service.fetch_one') as mock_fetch, \
             patch('app.services.payment_service.execute_query') as mock_execute:
            
            mock_fetch.return_value = mock_invoice
            mock_execute.return_value = None
            
            result = await provider.process_webhook(payload)
            
            assert result['status'] == 'processed'
            assert result['new_status'] == 'PAID'
            assert mock_execute.call_count == 2  # Update invoice and payment
    
    @pytest.mark.asyncio
    async def test_process_webhook_failed_status(self, provider):
        """Test NOWPayments webhook with failed status"""
        payload = {
            'payment_status': 'failed',
            'order_id': 'inv_123456789'
        }
        
        mock_invoice = {
            'id': 'invoice-uuid',
            'payment_id': 'payment-uuid'
        }
        
        with patch('app.services.payment_service.fetch_one') as mock_fetch, \
             patch('app.services.payment_service.execute_query') as mock_execute:
            
            mock_fetch.return_value = mock_invoice
            mock_execute.return_value = None
            
            result = await provider.process_webhook(payload)
            
            assert result['status'] == 'processed'
            assert result['new_status'] == 'FAILED'
            assert mock_execute.call_count == 1  # Update invoice only
    
    @pytest.mark.asyncio
    async def test_process_webhook_no_order_id(self, provider):
        """Test NOWPayments webhook with no order ID"""
        payload = {'payment_status': 'finished'}
        
        result = await provider.process_webhook(payload)
        
        assert result['status'] == 'ignored'
        assert result['reason'] == 'No order ID'
    
    @pytest.mark.asyncio
    async def test_process_webhook_invoice_not_found(self, provider):
        """Test NOWPayments webhook with invoice not found"""
        payload = {
            'payment_status': 'finished',
            'order_id': 'inv_nonexistent'
        }
        
        with patch('app.services.payment_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = None
            
            result = await provider.process_webhook(payload)
            
            assert result['status'] == 'ignored'
            assert result['reason'] == 'Invoice not found'


class TestPDFService:
    """Test PDF generation service"""
    
    @pytest.fixture
    def pdf_service(self):
        return PDFService()
    
    @pytest.mark.asyncio
    async def test_generate_invoice_pdf_invoice_not_found(self, pdf_service):
        """Test PDF generation with non-existent invoice"""
        with patch.object(pdf_service, '_get_invoice_data') as mock_get_data:
            mock_get_data.return_value = None
            
            with pytest.raises(ValueError, match="Invoice not found"):
                await pdf_service.generate_invoice_pdf("inv_nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_invoice_data(self, pdf_service):
        """Test getting invoice data for PDF"""
        mock_data = {
            'public_id': 'inv_123456789',
            'invoice_number': 'INV-2024-001',
            'amount': 1500.00,
            'currency_code': 'PEN',
            'debtor_name': 'Juan Pérez',
            'period': '2024-01'
        }
        
        with patch('app.services.pdf_service.fetch_one') as mock_fetch:
            mock_fetch.return_value = mock_data
            
            result = await pdf_service._get_invoice_data('inv_123456789')
            
            assert result == mock_data
            mock_fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_simple_pdf_success(self, pdf_service):
        """Test simple PDF generation when ReportLab not available"""
        mock_invoice_data = {
            'public_id': 'inv_123456789',
            'invoice_number': 'INV-2024-001',
            'amount': 1500.00,
            'currency_code': 'PEN',
            'debtor_name': 'Juan Pérez',
            'period': '2024-01',
            'status': 'PENDING',
            'created_at': '2024-01-15T10:00:00',
            'origin': 'mercadopago'
        }
        
        with patch.object(pdf_service, '_get_invoice_data') as mock_get_data, \
             patch.object(pdf_service.s3_service, 'upload_file') as mock_upload, \
             patch('app.services.pdf_service.execute_query') as mock_execute:
            
            mock_get_data.return_value = mock_invoice_data
            mock_upload.return_value = 'https://s3.amazonaws.com/bucket/invoice.html'
            mock_execute.return_value = None
            
            result = await pdf_service._generate_simple_pdf('inv_123456789')
            
            assert result == 'https://s3.amazonaws.com/bucket/invoice.html'
            mock_upload.assert_called_once()
            mock_execute.assert_called_once()
