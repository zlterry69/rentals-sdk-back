"""
Process Status endpoints
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.database import get_supabase

router = APIRouter()

# Pydantic models
class ProcessStatusResponse(BaseModel):
    id: str
    public_id: str
    code: str
    description: Optional[str] = None
    created_at: datetime

@router.get("/", response_model=List[ProcessStatusResponse])
async def list_process_status():
    """List all process statuses"""
    supabase = get_supabase()
    
    try:
        result = supabase.table('process_status').select('*').order('code').execute()
        
        return [ProcessStatusResponse(**status) for status in result.data]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch process statuses"
        )

@router.get("/{code}", response_model=ProcessStatusResponse)
async def get_process_status(code: str):
    """Get process status by code"""
    supabase = get_supabase()
    
    try:
        result = supabase.table('process_status').select('*').eq('code', code.upper()).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process status not found"
            )
        
        return ProcessStatusResponse(**result.data[0])
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch process status"
        )
