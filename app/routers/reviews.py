"""
Reviews management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.config import settings
from app.database import get_supabase
from app.utils.auth import verify_token
from app.utils.logging import get_request_logger
from app.utils.id_generator import make_public_id

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
class ReviewCreate(BaseModel):
    unit_id: str  # public_id of the unit
    rating: int
    title: Optional[str] = None
    comment: str

class ReviewResponse(BaseModel):
    id: str
    public_id: str
    unit_id: str
    user_id: str
    user_name: str
    user_profile_image: Optional[str] = None
    rating: int
    title: Optional[str]
    comment: str
    is_verified: bool
    helpful_count: int
    created_at: datetime
    updated_at: datetime

class UserReviewResponse(BaseModel):
    id: str
    rating: int
    title: Optional[str]
    comment: str
    created_at: datetime
    unit_title: str
    unit_id: str
    reviewer_name: str
    reviewer_avatar: Optional[str]
    is_verified: bool

@router.get("/unit/{unit_id}", response_model=List[ReviewResponse])
async def get_unit_reviews(unit_id: str):
    """Get all reviews for a specific unit (public endpoint)"""
    try:
        supabase = get_supabase()
        
        # Get unit internal ID from public_id
        unit_result = supabase.table('units').select('id').eq('public_id', unit_id).execute()
        if not unit_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit_internal_id = unit_result.data[0]['id']
        
        # Get reviews without JOIN first
        result = supabase.table('reviews').select('*').eq('unit_id', unit_internal_id).order('created_at', desc=True).execute()
        
        reviews = []
        for review in result.data:
            # Skip reviews with invalid user_id
            if not review.get('user_id'):
                logger.warning(f"Skipping review {review.get('id')} with invalid user_id")
                continue
                
            # Get user information separately
            user_name = 'Usuario'
            user_profile_image = None
            try:
                user_result = supabase.table('users').select('full_name, profile_image').eq('id', review['user_id']).execute()
                if user_result.data:
                    user_name = user_result.data[0].get('full_name', 'Usuario')
                    user_profile_image = user_result.data[0].get('profile_image')
            except Exception as e:
                logger.warning(f"Could not fetch user info for review: {str(e)}")
            
            reviews.append(ReviewResponse(
                id=review['id'],
                public_id=review['public_id'],
                unit_id=unit_id,
                user_id=review['user_id'],
                user_name=user_name,
                user_profile_image=user_profile_image,
                rating=review['rating'],
                title=review.get('title'),
                comment=review['comment'],
                is_verified=review.get('is_verified', False),
                helpful_count=review.get('helpful_count', 0),
                created_at=review['created_at'],
                updated_at=review['updated_at']
            ))
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error fetching reviews: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching reviews"
        )

@router.post("/", response_model=ReviewResponse)
async def create_review(review_data: ReviewCreate, current_user: dict = Depends(get_current_user)):
    """Create a new review"""
    try:
        supabase = get_supabase()
        
        # Get unit internal ID from public_id
        unit_result = supabase.table('units').select('id').eq('public_id', review_data.unit_id).execute()
        if not unit_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit_internal_id = unit_result.data[0]['id']
        user_id = current_user.get('sub')
        
        # Check if user already reviewed this unit
        existing_review = supabase.table('reviews').select('id').eq('unit_id', unit_internal_id).eq('user_id', user_id).execute()
        if existing_review.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this property"
            )
        
        # Create review
        review_public_id = make_public_id('rev')
        
        result = supabase.table('reviews').insert({
            'public_id': review_public_id,
            'unit_id': unit_internal_id,
            'user_id': user_id,
            'rating': review_data.rating,
            'title': review_data.title,
            'comment': review_data.comment,
            'is_verified': False  # TODO: Check if user has actually stayed at the property
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating review"
            )
        
        # Get user info for response
        user_result = supabase.table('users').select('full_name').eq('id', user_id).execute()
        user_name = user_result.data[0].get('full_name', 'Usuario') if user_result.data else 'Usuario'
        
        review = result.data[0]
        return ReviewResponse(
            id=review['id'],
            public_id=review['public_id'],
            unit_id=review_data.unit_id,
            user_id=user_id,
            user_name=user_name,
            rating=review['rating'],
            title=review.get('title'),
            comment=review['comment'],
            is_verified=review.get('is_verified', False),
            helpful_count=review.get('helpful_count', 0),
            created_at=review['created_at'],
            updated_at=review['updated_at']
        )
        
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating review"
        )

@router.delete("/{review_id}")
async def delete_review(review_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a review (only by the author or admin)"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        user_role = current_user.get('role', 'user')
        
        # Get review
        result = supabase.table('reviews').select('*').eq('public_id', review_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        review = result.data[0]
        
        # Check permissions
        if review['user_id'] != user_id and user_role not in ['admin', 'superadmin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this review"
            )
        
        # Delete review
        supabase.table('reviews').delete().eq('public_id', review_id).execute()
        
        return {"message": "Review deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting review: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting review"
        )

@router.get("/user/{user_id}/as-guest", response_model=List[UserReviewResponse])
async def get_user_reviews_as_guest(user_id: str):
    """Get reviews written by a user as a guest"""
    try:
        supabase = get_supabase()
        
        # Get reviews written by this user
        result = supabase.table('reviews').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        
        reviews = []
        for review in result.data:
            # Get unit information
            unit_result = supabase.table('units').select('title, public_id').eq('id', review['unit_id']).execute()
            unit_title = unit_result.data[0]['title'] if unit_result.data else 'Propiedad no encontrada'
            unit_public_id = unit_result.data[0]['public_id'] if unit_result.data else ''
            
            # Get reviewer information
            reviewer_result = supabase.table('users').select('full_name, profile_image').eq('id', review['user_id']).execute()
            reviewer_name = reviewer_result.data[0]['full_name'] if reviewer_result.data else 'Usuario'
            reviewer_avatar = reviewer_result.data[0]['profile_image'] if reviewer_result.data else None
            
            reviews.append({
                'id': review['public_id'],
                'rating': review['rating'],
                'title': review.get('title'),
                'comment': review['comment'],
                'created_at': review['created_at'],
                'unit_title': unit_title,
                'unit_id': unit_public_id,
                'reviewer_name': reviewer_name,
                'reviewer_avatar': reviewer_avatar,
                'is_verified': True
            })
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error fetching user reviews as guest: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user reviews"
        )

@router.get("/user/{user_id}/as-host", response_model=List[UserReviewResponse])
async def get_user_reviews_as_host(user_id: str):
    """Get reviews received by a user as a host"""
    try:
        supabase = get_supabase()
        
        # Get units owned by this user
        units_result = supabase.table('units').select('id, public_id, title').eq('owner_id', user_id).execute()
        if not units_result.data:
            return []
        
        unit_ids = [unit['id'] for unit in units_result.data]
        
        # Get reviews for these units
        result = supabase.table('reviews').select('*').in_('unit_id', unit_ids).order('created_at', desc=True).execute()
        
        reviews = []
        for review in result.data:
            # Get unit information
            unit = next((u for u in units_result.data if u['id'] == review['unit_id']), None)
            unit_title = unit['title'] if unit else 'Propiedad no encontrada'
            unit_public_id = unit['public_id'] if unit else ''
            
            # Get reviewer information
            reviewer_result = supabase.table('users').select('full_name, profile_image').eq('id', review['user_id']).execute()
            reviewer_name = reviewer_result.data[0]['full_name'] if reviewer_result.data else 'Usuario'
            reviewer_avatar = reviewer_result.data[0]['profile_image'] if reviewer_result.data else None
            
            reviews.append({
                'id': review['public_id'],
                'rating': review['rating'],
                'title': review.get('title'),
                'comment': review['comment'],
                'created_at': review['created_at'],
                'unit_title': unit_title,
                'unit_id': unit_public_id,
                'reviewer_name': reviewer_name,
                'reviewer_avatar': reviewer_avatar,
                'is_verified': True
            })
        
        return reviews
        
    except Exception as e:
        logger.error(f"Error fetching user reviews as host: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user reviews"
        )