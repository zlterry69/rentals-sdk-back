"""
Banks endpoints
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.database import get_supabase

router = APIRouter()

# Pydantic models
class BankResponse(BaseModel):
    id: str
    public_id: str
    code: str
    name: str
    provider_type: str
    status: str
    created_at: datetime

@router.get("/", response_model=List[BankResponse])
async def list_banks(
    provider_type: Optional[str] = None,
    status_filter: Optional[str] = None
):
    """List all banks/providers with optional filters"""
    supabase = get_supabase()
    
    try:
        query = supabase.table('banks').select('*')
        
        # Add filters
        if provider_type:
            query = query.eq('provider_type', provider_type)
        
        if status_filter:
            query = query.eq('status', status_filter)
        else:
            # Default to active only
            query = query.eq('status', 'ACTIVE')
        
        result = query.order('name').execute()
        
        return [BankResponse(**bank) for bank in result.data]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch banks"
        )

@router.get("/{code}", response_model=BankResponse)
async def get_bank(code: str):
    """Get bank by code"""
    supabase = get_supabase()
    
    try:
        result = supabase.table('banks').select('*').eq('code', code.upper()).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        return BankResponse(**result.data[0])
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch bank"
        )
