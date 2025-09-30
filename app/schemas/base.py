from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class BaseSchema(BaseModel):
    """Base schema with common fields"""
    id: Optional[UUID] = None
    public_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BaseCreateSchema(BaseModel):
    """Base schema for creation operations"""
    pass

class BaseUpdateSchema(BaseModel):
    """Base schema for update operations"""
    pass

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")

class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: list
    total: int
    page: int
    size: int
    pages: int
