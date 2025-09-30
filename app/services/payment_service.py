"""
Payment service for handling different payment providers
"""
import httpx
import structlog
from typing import Dict, Any, Optional
from datetime import datetime
import json
import hashlib
import hmac

from app.config import settings
from app.database import fetch_one, execute_query

logger = structlog.get_logger()


class PaymentService:
    """Service for handling payments across different providers"""
    
    def __init__(self):
        self.providers = {
            'mercadopago': MercadoPagoProvider(),
            'izipay': IzipayProvider(),
            'nowpayments': NOWPaymentsProvider()
        }
    
    async def create_payment_url(
        self, 
        invoice: Dict[str, Any], 
        method: Dict[str, Any],
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """Create payment URL for the specified provider"""
        provider = self.providers.get(invoice['origin'])
        if not provider:
            raise ValueError(f"Unknown payment provider: {invoice['origin']}")
        
        return await provider.create_payment(invoice, method, return_url, cancel_url)
    
    async def process_webhook(
        self, 
        provider_name: str, 
        payload: Dict[str, Any], 
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process webhook from payment provider"""
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown payment provider: {provider_name}")
        
        return await provider.process_webhook(payload, signature)


class BasePaymentProvider:
    """Base class for payment providers"""
    
    async def create_payment(
        self, 
        invoice: Dict[str, Any], 
        method: Dict[str, Any],
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """Create payment and return payment URL"""
        raise NotImplementedError
    
    async def process_webhook(
        self, 
        payload: Dict[str, Any], 
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process webhook from provider"""
        raise NotImplementedError
    
    async def verify_signature(
        self, 
        payload: str, 
        signature: str, 
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        raise NotImplementedError


class MercadoPagoProvider(BasePaymentProvider):
    """MercadoPago payment provider"""
    
    async def create_payment(
        self, 
        invoice: Dict[str, Any], 
        method: Dict[str, Any],
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """Create MercadoPago payment"""
        try:
            config = method.get('config', {})
            api_url = config.get('api_url', 'https://api.mercadopago.com')
            
            # Get payment details
            payment = await fetch_one(
                "SELECT p.*, d.name as debtor_name, d.email as debtor_email FROM payments p JOIN debtors d ON p.debtor_id = d.id WHERE p.id = $1",
                (invoice['payment_id'],)
            )
            
            # Create preference
            preference_data = {
                "items": [{
                    "title": f"Pago de alquiler - {payment['period']}",
                    "quantity": 1,
                    "unit_price": float(invoice['amount']),
                    "currency_id": "PEN"  # TODO: Get from currency table
                }],
                "payer": {
                    "name": payment['debtor_name'],
                    "email": payment.get('debtor_email', 'noemail@example.com')
                },
                "external_reference": invoice['public_id'],
                "notification_url": f"{settings.RENTALS_BACK_URL}/invoices/webhooks/mercadopago",
                "back_urls": {
                    "success": return_url or f"{settings.RENTALS_FRONT_URL}/payment/success",
                    "failure": cancel_url or f"{settings.RENTALS_FRONT_URL}/payment/failed",
                    "pending": f"{settings.RENTALS_FRONT_URL}/payment/pending"
                },
                "auto_return": "approved"
            }
            
            # Make API call to MercadoPago
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/checkout/preferences",
                    json=preference_data,
                    headers={
                        "Authorization": f"Bearer {config.get('access_token')}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 201:
                    raise Exception(f"MercadoPago API error: {response.text}")
                
                result = response.json()
                
                # Update invoice with external data
                await execute_query(
                    "UPDATE invoices SET external_id = $1, metadata = $2 WHERE id = $3",
                    (result['id'], json.dumps(result), invoice['id'])
                )
                
                return result['init_point']
                
        except Exception as e:
            logger.error("Error creating MercadoPago payment", error=str(e))
            raise
    
    async def process_webhook(
        self, 
        payload: Dict[str, Any], 
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process MercadoPago webhook"""
        try:
            # Get payment info from MercadoPago
            payment_id = payload.get('data', {}).get('id')
            if not payment_id:
                return {"status": "ignored", "reason": "No payment ID"}
            
            # TODO: Fetch payment details from MercadoPago API
            # TODO: Update invoice status based on payment status
            
            return {"status": "processed", "payment_id": payment_id}
            
        except Exception as e:
            logger.error("Error processing MercadoPago webhook", error=str(e))
            raise


class IzipayProvider(BasePaymentProvider):
    """Izipay payment provider"""
    
    async def create_payment(
        self, 
        invoice: Dict[str, Any], 
        method: Dict[str, Any],
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """Create Izipay payment"""
        try:
            config = method.get('config', {})
            
            # Get payment details
            payment = await fetch_one(
                "SELECT p.*, d.name as debtor_name, d.email as debtor_email FROM payments p JOIN debtors d ON p.debtor_id = d.id WHERE p.id = $1",
                (invoice['payment_id'],)
            )
            
            # Create Izipay payment
            payment_data = {
                "amount": int(float(invoice['amount']) * 100),  # Amount in cents
                "currency": "PEN",
                "orderId": invoice['public_id'],
                "customer": {
                    "email": payment.get('debtor_email', 'noemail@example.com'),
                    "reference": payment['debtor_id']
                }
            }
            
            # TODO: Implement Izipay API integration
            # For now, return a mock URL
            mock_url = f"https://secure.izipay.pe/payment/{invoice['public_id']}"
            
            # Update invoice with external data
            await execute_query(
                "UPDATE invoices SET external_id = $1, external_url = $2 WHERE id = $3",
                (invoice['public_id'], mock_url, invoice['id'])
            )
            
            return mock_url
            
        except Exception as e:
            logger.error("Error creating Izipay payment", error=str(e))
            raise
    
    async def process_webhook(
        self, 
        payload: Dict[str, Any], 
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process Izipay webhook"""
        try:
            # TODO: Implement Izipay webhook processing
            return {"status": "processed"}
            
        except Exception as e:
            logger.error("Error processing Izipay webhook", error=str(e))
            raise


class NOWPaymentsProvider(BasePaymentProvider):
    """NOWPayments crypto provider"""
    
    async def create_payment(
        self, 
        invoice: Dict[str, Any], 
        method: Dict[str, Any],
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> str:
        """Create NOWPayments crypto payment"""
        try:
            config = method.get('config', {})
            api_url = config.get('api_url', 'https://api.nowpayments.io')
            
            # Get payment details
            payment = await fetch_one(
                "SELECT p.*, d.name as debtor_name, d.email as debtor_email FROM payments p JOIN debtors d ON p.debtor_id = d.id WHERE p.id = $1",
                (invoice['payment_id'],)
            )
            
            # Create NOWPayments invoice
            invoice_data = {
                "price_amount": float(invoice['amount']),
                "price_currency": "USD",  # TODO: Get from currency table
                "pay_currency": "btc",  # Default to Bitcoin
                "order_id": invoice['public_id'],
                "order_description": f"Pago de alquiler - {payment['period']}",
                "success_url": return_url or f"{settings.RENTALS_FRONT_URL}/payment/success",
                "cancel_url": cancel_url or f"{settings.RENTALS_FRONT_URL}/payment/failed"
            }
            
            # Make API call to NOWPayments
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{api_url}/v1/invoice",
                    json=invoice_data,
                    headers={
                        "x-api-key": config.get('api_key'),
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 201:
                    raise Exception(f"NOWPayments API error: {response.text}")
                
                result = response.json()
                
                # Update invoice with external data
                await execute_query(
                    "UPDATE invoices SET external_id = $1, metadata = $2 WHERE id = $3",
                    (result['id'], json.dumps(result), invoice['id'])
                )
                
                return result['invoice_url']
                
        except Exception as e:
            logger.error("Error creating NOWPayments payment", error=str(e))
            raise
    
    async def process_webhook(
        self, 
        payload: Dict[str, Any], 
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process NOWPayments webhook"""
        try:
            # Get payment status
            payment_status = payload.get('payment_status')
            order_id = payload.get('order_id')
            
            if not order_id:
                return {"status": "ignored", "reason": "No order ID"}
            
            # Find invoice by public_id
            invoice = await fetch_one(
                "SELECT * FROM invoices WHERE public_id = $1",
                (order_id,)
            )
            
            if not invoice:
                return {"status": "ignored", "reason": "Invoice not found"}
            
            # Update invoice status based on payment status
            new_status = "PENDING"
            if payment_status == "finished":
                new_status = "PAID"
                paid_at = datetime.now()
                
                # Update invoice
                await execute_query(
                    "UPDATE invoices SET status = $1, paid_at = $2, metadata = $3 WHERE id = $4",
                    (new_status, paid_at, json.dumps(payload), invoice['id'])
                )
                
                # Update payment
                await execute_query(
                    "UPDATE payments SET paid_at = $1, status_id = (SELECT id FROM process_status WHERE code = 'PAID') WHERE id = $2",
                    (paid_at, invoice['payment_id'])
                )
            elif payment_status in ["failed", "expired"]:
                new_status = "FAILED" if payment_status == "failed" else "EXPIRED"
                await execute_query(
                    "UPDATE invoices SET status = $1, metadata = $2 WHERE id = $3",
                    (new_status, json.dumps(payload), invoice['id'])
                )
            
            return {"status": "processed", "new_status": new_status}
            
        except Exception as e:
            logger.error("Error processing NOWPayments webhook", error=str(e))
            raise
