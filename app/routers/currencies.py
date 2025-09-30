"""
Currencies endpoints
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.database import get_supabase

router = APIRouter()

# Pydantic models
class CurrencyResponse(BaseModel):
    id: str
    public_id: str
    code: str
    name: str
    decimals: int
    created_at: datetime

@router.get("/", response_model=List[CurrencyResponse])
async def list_currencies():
    """List all currencies"""
    supabase = get_supabase()
    
    try:
        result = supabase.table('currencies').select('*').order('code').execute()
        
        return [CurrencyResponse(**currency) for currency in result.data]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch currencies"
        )

@router.get("/{code}", response_model=CurrencyResponse)
async def get_currency(code: str):
    """Get currency by code"""
    supabase = get_supabase()
    
    try:
        result = supabase.table('currencies').select('*').eq('code', code.upper()).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Currency not found"
            )
        
        return CurrencyResponse(**result.data[0])
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch currency"
        )
