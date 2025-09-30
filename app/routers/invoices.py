"""
Router para manejo de facturas e invoices
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, Dict, Any
import structlog
from datetime import datetime, timedelta
import json

from app.database import get_supabase
from app.schemas.invoices import (
    Invoice, InvoiceCreate, InvoiceUpdate,
    PaymentMethod, PaymentMethodCreate, PaymentMethodUpdate,
    PaymentRequest, PaymentResponse, WebhookPayload
)
from app.utils.auth import get_current_user
from app.utils.id_generator import make_public_id
from app.services.payment_service import PaymentService

logger = structlog.get_logger()
router = APIRouter()


# Payment Methods endpoints
@router.get("/payment-methods", response_model=list[PaymentMethod])
async def list_payment_methods(
    type_filter: Optional[str] = Query(None, description="Filter by type: traditional or crypto"),
    active_only: bool = Query(True, description="Show only active methods"),
    current_user: dict = Depends(get_current_user)
):
    """List available payment methods"""
    try:
        supabase = get_supabase()
        
        # Construir query con filtros
        query = supabase.table('payment_methods').select('*')
        
        if type_filter:
            query = query.eq('type', type_filter)
        
        if active_only:
            query = query.eq('is_active', True)
        
        query = query.order('type').order('name')
        
        result = query.execute()
        
        if result.data:
            return result.data
        else:
            return []
        
    except Exception as e:
        logger.error("Error listing payment methods", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/payment-methods", response_model=PaymentMethod, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    method_data: PaymentMethodCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new payment method"""
    try:
        public_id = make_public_id("pm")
        
        query = """
            INSERT INTO payment_methods (
                public_id, name, code, type, description, 
                is_active, icon_url, config
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        
        method = await fetch_one(query, (
            public_id, method_data.name, method_data.code, method_data.type,
            method_data.description, method_data.is_active, method_data.icon_url,
            json.dumps(method_data.config) if method_data.config else None
        ))
        
        if not method:
            raise HTTPException(status_code=400, detail="Failed to create payment method")
        
        logger.info("Payment method created", public_id=public_id, code=method_data.code)
        return method
        
    except Exception as e:
        logger.error("Error creating payment method", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# Invoices endpoints
@router.get("/invoices", response_model=Dict[str, Any])
async def list_invoices(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    origin_filter: Optional[str] = Query(None, description="Filter by origin"),
    current_user: dict = Depends(get_current_user)
):
    """List invoices with pagination"""
    try:
        query = """
            SELECT 
                i.*,
                p.debtor_id,
                p.amount as payment_amount,
                d.name as debtor_name
            FROM invoices i
            JOIN payments p ON i.payment_id = p.id
            JOIN debtors d ON p.debtor_id = d.id
            WHERE ($1::text IS NULL OR i.status = $1)
            AND ($2::text IS NULL OR i.origin = $2)
            ORDER BY i.created_at DESC
        """
        
        result = await fetch_paginated(
            query, 
            (status_filter, origin_filter),
            page, 
            size
        )
        
        return result
        
    except Exception as e:
        logger.error("Error listing invoices", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/invoices/{public_id}", response_model=Invoice)
async def get_invoice(
    public_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get invoice by public ID"""
    try:
        query = """
            SELECT 
                i.*,
                p.debtor_id,
                p.amount as payment_amount,
                d.name as debtor_name,
                c.code as currency_code
            FROM invoices i
            JOIN payments p ON i.payment_id = p.id
            JOIN debtors d ON p.debtor_id = d.id
            LEFT JOIN currencies c ON i.currency_id = c.id
            WHERE i.public_id = $1
        """
        
        invoice = await fetch_one(query, (public_id,))
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting invoice", error=str(e), public_id=public_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/invoices", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payment_request: PaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new invoice for payment"""
    try:
        # Verify payment exists
        payment_query = """
            SELECT p.*, c.code as currency_code 
            FROM payments p
            LEFT JOIN currencies c ON p.currency_id = c.id
            WHERE p.public_id = $1
        """
        
        payment = await fetch_one(payment_query, (payment_request.payment_id,))
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Verify payment method exists
        method_query = "SELECT * FROM payment_methods WHERE code = $1 AND is_active = true"
        method = await fetch_one(method_query, (payment_request.method_code,))
        if not method:
            raise HTTPException(status_code=404, detail="Payment method not found or inactive")
        
        # Create invoice
        public_id = make_public_id("inv")
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{public_id[-8:]}"
        expires_at = datetime.now() + timedelta(hours=24)  # 24 hours to pay
        
        invoice_query = """
            INSERT INTO invoices (
                public_id, payment_id, invoice_number, amount, 
                currency_id, origin, expires_at, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'PENDING')
            RETURNING *
        """
        
        invoice = await fetch_one(invoice_query, (
            public_id, payment['id'], invoice_number, payment['amount'],
            payment['currency_id'], payment_request.method_code, expires_at
        ))
        
        if not invoice:
            raise HTTPException(status_code=400, detail="Failed to create invoice")
        
        # Generate payment URL using PaymentService
        payment_service = PaymentService()
        payment_url = await payment_service.create_payment_url(
            invoice, method, payment_request.return_url, payment_request.cancel_url
        )
        
        # Update invoice with external data
        update_query = """
            UPDATE invoices 
            SET external_url = $1, updated_at = NOW()
            WHERE id = $2
        """
        await execute_query(update_query, (payment_url, invoice['id']))
        
        logger.info("Invoice created", public_id=public_id, method=payment_request.method_code)
        
        return PaymentResponse(
            invoice_id=public_id,
            payment_url=payment_url,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating invoice", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/invoices/{public_id}", response_model=Invoice)
async def update_invoice(
    public_id: str,
    invoice_data: InvoiceUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update invoice"""
    try:
        # Check if invoice exists
        existing = await fetch_one("SELECT * FROM invoices WHERE public_id = $1", (public_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Build update query dynamically
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in invoice_data.dict(exclude_unset=True).items():
            if field == "metadata" and value is not None:
                update_fields.append(f"metadata = ${param_count}")
                params.append(json.dumps(value))
            else:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_fields.append("updated_at = NOW()")
        params.append(public_id)
        
        query = f"""
            UPDATE invoices 
            SET {', '.join(update_fields)}
            WHERE public_id = ${param_count}
            RETURNING *
        """
        
        updated_invoice = await fetch_one(query, tuple(params))
        
        if not updated_invoice:
            raise HTTPException(status_code=400, detail="Failed to update invoice")
        
        logger.info("Invoice updated", public_id=public_id)
        return updated_invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating invoice", error=str(e), public_id=public_id)
        raise HTTPException(status_code=500, detail="Internal server error")


# Webhook endpoint
@router.post("/webhooks/{provider}")
async def handle_webhook(
    provider: str,
    payload: Dict[str, Any],
    signature: Optional[str] = None
):
    """Handle webhooks from payment providers"""
    try:
        # Log webhook
        log_query = """
            INSERT INTO webhook_logs (provider, event_type, payload, processed)
            VALUES ($1, $2, $3, false)
            RETURNING id
        """
        
        event_type = payload.get('type', payload.get('event_type', 'unknown'))
        log_result = await fetch_one(log_query, (
            provider, event_type, json.dumps(payload)
        ))
        
        # Process webhook based on provider
        payment_service = PaymentService()
        result = await payment_service.process_webhook(provider, payload, signature)
        
        # Update log as processed
        if log_result:
            await execute_query(
                "UPDATE webhook_logs SET processed = true WHERE id = $1",
                (log_result['id'],)
            )
        
        logger.info("Webhook processed", provider=provider, event_type=event_type)
        return {"status": "ok", "processed": True}
        
    except Exception as e:
        logger.error("Error processing webhook", error=str(e), provider=provider)
        
        # Update log with error
        if 'log_result' in locals() and log_result:
            await execute_query(
                "UPDATE webhook_logs SET error_message = $1 WHERE id = $2",
                (str(e), log_result['id'])
            )
        
        return {"status": "error", "message": str(e)}
