"""
Schemas para facturas e invoices
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.base import BaseSchema


class PaymentMethodBase(BaseModel):
    """Schema base para métodos de pago"""
    name: str = Field(..., description="Nombre del método de pago")
    code: str = Field(..., description="Código único del método")
    type: str = Field(..., description="Tipo: traditional o crypto")
    description: Optional[str] = Field(None, description="Descripción del método")
    is_active: bool = Field(True, description="Si está activo")
    icon_url: Optional[str] = Field(None, description="URL del ícono")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuración del proveedor")


class PaymentMethodCreate(PaymentMethodBase):
    """Schema para crear método de pago"""
    pass


class PaymentMethodUpdate(BaseModel):
    """Schema para actualizar método de pago"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    icon_url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class PaymentMethod(PaymentMethodBase, BaseSchema):
    """Schema completo de método de pago"""
    pass


class InvoiceBase(BaseModel):
    """Schema base para facturas"""
    payment_id: str = Field(..., description="ID del pago asociado")
    amount: Decimal = Field(..., description="Monto de la factura")
    currency_id: str = Field(..., description="ID de la moneda")
    origin: str = Field(..., description="Origen del pago: mercadopago, izipay, nowpayments")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata del SDK")
    external_id: Optional[str] = Field(None, description="ID externo del proveedor")
    external_url: Optional[str] = Field(None, description="URL de pago del proveedor")
    webhook_url: Optional[str] = Field(None, description="URL del webhook")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")


class InvoiceCreate(InvoiceBase):
    """Schema para crear factura"""
    pass


class InvoiceUpdate(BaseModel):
    """Schema para actualizar factura"""
    status: Optional[str] = Field(None, description="Estado de la factura")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata del SDK")
    external_id: Optional[str] = Field(None, description="ID externo del proveedor")
    external_url: Optional[str] = Field(None, description="URL de pago del proveedor")
    pdf_s3_key: Optional[str] = Field(None, description="Clave del PDF en S3")
    pdf_url: Optional[str] = Field(None, description="URL del PDF")
    paid_at: Optional[datetime] = Field(None, description="Fecha de pago")


class Invoice(InvoiceBase, BaseSchema):
    """Schema completo de factura"""
    invoice_number: str = Field(..., description="Número de factura")
    status: str = Field(..., description="Estado de la factura")
    pdf_s3_key: Optional[str] = Field(None, description="Clave del PDF en S3")
    pdf_url: Optional[str] = Field(None, description="URL del PDF")
    paid_at: Optional[datetime] = Field(None, description="Fecha de pago")


class WebhookLogBase(BaseModel):
    """Schema base para logs de webhooks"""
    invoice_id: str = Field(..., description="ID de la factura")
    provider: str = Field(..., description="Proveedor del webhook")
    event_type: Optional[str] = Field(None, description="Tipo de evento")
    headers: Optional[Dict[str, Any]] = Field(None, description="Headers de la request")
    payload: Optional[Dict[str, Any]] = Field(None, description="Payload del webhook")
    processed: bool = Field(False, description="Si fue procesado")
    error_message: Optional[str] = Field(None, description="Mensaje de error")


class WebhookLogCreate(WebhookLogBase):
    """Schema para crear log de webhook"""
    pass


class WebhookLog(WebhookLogBase, BaseSchema):
    """Schema completo de log de webhook"""
    pass


# Schemas para requests de pago
class PaymentRequest(BaseModel):
    """Schema para solicitar un pago"""
    payment_id: str = Field(..., description="ID del pago")
    method_code: str = Field(..., description="Código del método de pago")
    return_url: Optional[str] = Field(None, description="URL de retorno")
    cancel_url: Optional[str] = Field(None, description="URL de cancelación")
    
    
class PaymentResponse(BaseModel):
    """Schema para respuesta de pago"""
    invoice_id: str = Field(..., description="ID de la factura generada")
    payment_url: str = Field(..., description="URL para realizar el pago")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")
    qr_code: Optional[str] = Field(None, description="Código QR para pago")


class WebhookPayload(BaseModel):
    """Schema genérico para webhooks"""
    provider: str = Field(..., description="Proveedor del webhook")
    event_type: str = Field(..., description="Tipo de evento")
    data: Dict[str, Any] = Field(..., description="Datos del webhook")
    signature: Optional[str] = Field(None, description="Firma del webhook")
