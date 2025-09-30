from pydantic import Field
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from .base import BaseSchema, BaseCreateSchema, BaseUpdateSchema

class PaymentSchema(BaseSchema):
    """Payment schema"""
    debtor_id: UUID
    lease_id: Optional[UUID] = None
    period: str
    due_date: Optional[date] = None
    paid_at: Optional[datetime] = None
    amount: float
    currency_id: UUID
    method: Optional[str] = None
    reference: Optional[str] = None
    status_id: UUID
    meter_start: Optional[int] = None
    meter_end: Optional[int] = None
    notes: Optional[str] = None
    s3_key: Optional[str] = None
    bank_id: Optional[UUID] = None
    invoice_id: Optional[str] = None

class PaymentCreateSchema(BaseCreateSchema):
    """Payment creation schema"""
    debtor_id: UUID = Field(..., description="Debtor ID")
    lease_id: Optional[UUID] = Field(None, description="Lease ID (optional)")
    period: str = Field(..., pattern=r'^\d{4}-\d{2}$', description="Period in YYYY-MM format")
    due_date: Optional[date] = Field(None, description="Due date")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency_id: UUID = Field(..., description="Currency ID")
    method: Optional[str] = Field(None, description="Payment method (cash, transfer, crypto)")
    reference: Optional[str] = Field(None, description="Payment reference")
    meter_start: Optional[int] = Field(None, ge=0, description="Meter reading start")
    meter_end: Optional[int] = Field(None, ge=0, description="Meter reading end")
    notes: Optional[str] = Field(None, max_length=500, description="Payment notes")
    bank_id: Optional[UUID] = Field(None, description="Bank/provider ID")

class PaymentUpdateSchema(BaseUpdateSchema):
    """Payment update schema"""
    due_date: Optional[date] = Field(None, description="Due date")
    amount: Optional[float] = Field(None, gt=0, description="Payment amount")
    currency_id: Optional[UUID] = Field(None, description="Currency ID")
    method: Optional[str] = Field(None, description="Payment method")
    reference: Optional[str] = Field(None, description="Payment reference")
    meter_start: Optional[int] = Field(None, ge=0, description="Meter reading start")
    meter_end: Optional[int] = Field(None, ge=0, description="Meter reading end")
    notes: Optional[str] = Field(None, max_length=500, description="Payment notes")

class PaymentConfirmSchema(BaseCreateSchema):
    """Payment confirmation schema"""
    paid_at: Optional[datetime] = Field(None, description="Payment date (defaults to now)")
    reference: Optional[str] = Field(None, description="Payment reference")

class PaymentDetailSchema(PaymentSchema):
    """Payment detail with additional information"""
    debtor_name: str
    currency_code: str
    status_code: str
    status_description: str
    bank_name: Optional[str] = None
    pre_signed_url: Optional[str] = None

class PaymentReceiptSchema(BaseCreateSchema):
    """Payment receipt generation schema"""
    format: str = Field("png", pattern="^(png|pdf)$", description="Receipt format (png or pdf)")
    include_qr: bool = Field(True, description="Include QR code in receipt")
