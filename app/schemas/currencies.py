from pydantic import Field
from .base import BaseSchema, BaseCreateSchema, BaseUpdateSchema

class CurrencySchema(BaseSchema):
    """Currency schema"""
    code: str
    name: str
    decimals: int

class CurrencyCreateSchema(BaseCreateSchema):
    """Currency creation schema"""
    code: str = Field(..., min_length=3, max_length=10, description="Currency code (e.g., PEN, USD)")
    name: str = Field(..., min_length=1, max_length=100, description="Currency name")
    decimals: int = Field(2, ge=0, le=8, description="Number of decimal places")

class CurrencyUpdateSchema(BaseUpdateSchema):
    """Currency update schema"""
    code: str = Field(None, min_length=3, max_length=10, description="Currency code")
    name: str = Field(None, min_length=1, max_length=100, description="Currency name")
    decimals: int = Field(None, ge=0, le=8, description="Number of decimal places")
