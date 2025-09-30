"""
Favorites management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List
from app.config import settings
from app.database import get_supabase
from app.utils.auth import verify_token
from app.utils.logging import get_request_logger

logger = get_request_logger()
router = APIRouter()
security = HTTPBearer()

# Helper function for FastAPI dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extract user payload from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return payload

# Pydantic models
class FavoriteResponse(BaseModel):
    id: str
    user_id: str
    unit_id: str
    unit_public_id: str
    created_at: str

class FavoriteToggleRequest(BaseModel):
    unit_public_id: str

@router.get("/", response_model=List[FavoriteResponse])
async def get_user_favorites(current_user: dict = Depends(get_current_user)):
    """Get all favorites for the current user"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get user's favorites with unit information
        result = supabase.table('user_favorites').select(
            'id, user_id, unit_id, created_at, units!inner(public_id)'
        ).eq('user_id', user_id).execute()
        
        favorites = []
        for fav in result.data:
            favorites.append(FavoriteResponse(
                id=fav['id'],
                user_id=fav['user_id'],
                unit_id=fav['unit_id'],
                unit_public_id=fav['units']['public_id'],
                created_at=fav['created_at']
            ))
        
        return favorites
        
    except Exception as e:
        logger.error(f"Error fetching user favorites: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching favorites"
        )

@router.post("/toggle", response_model=dict)
async def toggle_favorite(
    request: FavoriteToggleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Toggle favorite status for a unit"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        unit_public_id = request.unit_public_id
        
        # Get unit internal ID from public_id
        unit_result = supabase.table('units').select('id').eq('public_id', unit_public_id).execute()
        if not unit_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit_id = unit_result.data[0]['id']
        
        # Check if favorite already exists
        existing_fav = supabase.table('user_favorites').select('id').eq('user_id', user_id).eq('unit_id', unit_id).execute()
        
        if existing_fav.data:
            # Remove favorite
            supabase.table('user_favorites').delete().eq('id', existing_fav.data[0]['id']).execute()
            return {"is_favorite": False, "message": "Removed from favorites"}
        else:
            # Add favorite
            supabase.table('user_favorites').insert({
                'user_id': user_id,
                'unit_id': unit_id
            }).execute()
            return {"is_favorite": True, "message": "Added to favorites"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error toggling favorite"
        )

@router.get("/check/{unit_public_id}", response_model=dict)
async def check_favorite_status(
    unit_public_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if a unit is favorited by the current user"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get unit internal ID from public_id
        unit_result = supabase.table('units').select('id').eq('public_id', unit_public_id).execute()
        if not unit_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit_id = unit_result.data[0]['id']
        
        # Check if favorite exists
        existing_fav = supabase.table('user_favorites').select('id').eq('user_id', user_id).eq('unit_id', unit_id).execute()
        
        return {"is_favorite": len(existing_fav.data) > 0}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking favorite status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking favorite status"
        )
