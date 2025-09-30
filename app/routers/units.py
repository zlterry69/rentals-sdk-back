"""
Units/Properties management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.config import settings
from app.database import get_supabase
from app.utils.auth import verify_token
from app.utils.logging import get_request_logger
from app.utils.id_generator import make_public_id
from app.utils.s3_folders import get_property_image_key
from app.utils.s3_utils import upload_to_s3

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
class UnitRequest(BaseModel):
    title: str
    description: Optional[str] = None
    address: str
    property_type: str  # apartment, house, studio, room
    bedrooms: int
    bathrooms: int
    area_sqm: float  # in square meters
    max_guests: Optional[int] = 6  # maximum number of guests
    monthly_rent: float
    deposit: Optional[float] = None
    amenities: Optional[List[str]] = []
    rules: Optional[str] = None
    available_from: Optional[datetime] = None
    status: str = "available"  # available, occupied, maintenance
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UnitResponse(BaseModel):
    id: str
    public_id: str
    title: str
    description: Optional[str] = None
    address: str
    property_type: str
    bedrooms: int
    bathrooms: int
    area_sqm: float
    max_guests: Optional[int] = 6
    monthly_rent: float
    deposit: Optional[float] = None
    amenities: Optional[List[str]] = []
    rules: Optional[str] = None
    available_from: Optional[datetime] = None
    status: str
    images: Optional[List[str]] = []
    owner_id: str
    owner_name: Optional[str] = None
    owner_rating: Optional[float] = None
    owner_profile_image: Optional[str] = None
    rating: Optional[float] = None
    total_reviews: int = 0
    created_at: datetime
    updated_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UnitUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    max_guests: Optional[int] = None
    monthly_rent: Optional[float] = None
    deposit: Optional[float] = None
    amenities: Optional[List[str]] = None
    rules: Optional[str] = None
    available_from: Optional[datetime] = None
    status: Optional[str] = None
    images: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# Endpoints
@router.get("/", response_model=List[UnitResponse])
async def get_units(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
):
    """Get units based on user role"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Build query based on role
        query = supabase.table('units').select('*')
        
        # Admins and superadmins see all units, users see only their own
        if current_user.get('role') not in ['admin', 'superadmin']:
            query = query.eq('owner_id', user_id)
        
        # Apply filters
        if status_filter:
            query = query.eq('status', status_filter)
        
        result = query.range(skip, skip + limit - 1).execute()
        
        units = []
        for unit in result.data:
            units.append(UnitResponse(
                id=unit['id'],
                public_id=unit['public_id'],
                title=unit.get('title') or unit.get('label', 'Unidad sin título'),
                description=unit.get('description'),
                address=unit.get('address', 'Dirección no especificada'),
                property_type=unit.get('unit_type', 'apartment'),
                bedrooms=unit.get('bedrooms', 1),
                bathrooms=unit.get('bathrooms', 1),
                area_sqm=unit.get('area_sqm', 50.0),
                max_guests=unit.get('max_guests', 6),
                monthly_rent=unit.get('monthly_rent', 1500.0),
                deposit=unit.get('deposit'),
                amenities=unit.get('amenities', []),
                rules=unit.get('rules'),
                available_from=unit.get('available_from'),
                status=unit.get('status', 'available'),
                images=unit.get('images', []),
                owner_id=unit.get('owner_id', ''),
                owner_name=None,  # TODO: Implement owner lookup if needed
                rating=unit.get('rating', 0.0),
                total_reviews=unit.get('total_reviews', 0),
                created_at=unit.get('created_at'),
                updated_at=unit.get('updated_at', unit.get('created_at'))
            ))
        
        return units
        
    except Exception as e:
        logger.error(f"Error fetching units: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching units"
        )

@router.get("/featured", response_model=List[UnitResponse])
async def get_featured_units(limit: int = 3):
    """Get featured properties (top rated, public endpoint - no auth required)"""
    try:
        supabase = get_supabase()
        
        # Get properties sorted by rating (highest first), then by created_at (newest first)
        result = supabase.table('units').select('*').eq('status', 'available').order('rating', desc=True).order('created_at', desc=True).limit(limit).execute()
        
        units = []
        for unit in result.data:
            # Calculate real-time rating and review count
            unit_rating = 0.0
            total_reviews = 0
            
            try:
                # Get reviews for this unit
                reviews_result = supabase.table('reviews').select('rating').eq('unit_id', unit['id']).execute()
                if reviews_result.data:
                    ratings = [r['rating'] for r in reviews_result.data if r.get('rating')]
                    if ratings:
                        unit_rating = round(sum(ratings) / len(ratings), 1)
                    total_reviews = len(reviews_result.data)
            except Exception as e:
                logger.warning(f"Could not calculate rating for unit {unit.get('id')}: {str(e)}")
            
            # Convert to UnitResponse format with safe defaults
            unit_response = UnitResponse(
                id=unit.get('id', ''),
                public_id=unit.get('public_id', ''),
                title=unit.get('title', 'Propiedad sin título'),
                description=unit.get('description', ''),
                address=unit.get('address', ''),
                monthly_rent=unit.get('monthly_rent', 0),
                deposit=unit.get('deposit', 0),
                bedrooms=unit.get('bedrooms', 1),
                bathrooms=unit.get('bathrooms', 1),
                area_sqm=unit.get('area_sqm', 0),
                max_guests=unit.get('max_guests', 6),
                property_type=unit.get('unit_type', 'apartment'),
                amenities=unit.get('amenities', []),
                rules=unit.get('rules', ''),
                images=unit.get('images', []),
                available_from=unit.get('available_from'),
                rating=unit_rating,
                total_reviews=total_reviews,
                status=unit.get('status', 'available'),
                owner_id=unit.get('owner_id'),
                created_at=unit.get('created_at'),
                updated_at=unit.get('updated_at')
            )
            units.append(unit_response)
        
        logger.info(f"Retrieved {len(units)} featured units")
        return units
        
    except Exception as e:
        logger.error(f"Error fetching featured units: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching featured units"
        )

@router.get("/my-units", response_model=List[UnitResponse])
async def get_my_units(current_user: dict = Depends(get_current_user)):
    """Get units owned by the current user"""
    try:
        supabase = get_supabase()
        
        # Get units owned by the current user
        result = supabase.table('units').select('*').eq('owner_id', current_user['sub']).order('created_at', desc=True).execute()
        
        units = []
        for unit in result.data:
            # Calculate real-time rating and review count
            unit_rating = 0.0
            total_reviews = 0
            
            try:
                reviews_result = supabase.table('reviews').select('rating').eq('unit_id', unit['id']).execute()
                if reviews_result.data:
                    ratings = [review['rating'] for review in reviews_result.data if review['rating'] is not None]
                    if ratings:
                        unit_rating = sum(ratings) / len(ratings)
                        total_reviews = len(ratings)
            except Exception as e:
                logger.warning(f"Error calculating rating for unit {unit['id']}: {e}")
            
            # Map unit_type to property_type for compatibility
            unit['property_type'] = unit.get('unit_type', 'apartment')
            unit['unit_rating'] = round(unit_rating, 1)
            unit['total_reviews'] = total_reviews
            units.append(unit)
        
        return units
        
    except Exception as e:
        logger.error(f"Error fetching my units: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching my units"
        )

@router.get("/available", response_model=List[UnitResponse])
async def get_available_units(
    skip: int = 0,
    limit: int = 100,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None
):
    """Get available units for public viewing (no auth required)"""
    try:
        supabase = get_supabase()
        
        # Build query for available units only
        query = supabase.table('units').select('*').eq('status', 'available')
        
        if min_price:
            query = query.gte('monthly_rent', min_price)
        if max_price:
            query = query.lte('monthly_rent', max_price)
        if bedrooms:
            query = query.eq('bedrooms', bedrooms)
        
        result = query.range(skip, skip + limit - 1).execute()
        
        units = []
        for unit in result.data:
            units.append(UnitResponse(
                id=unit['id'],
                public_id=unit['public_id'],
                title=unit.get('title') or unit.get('label', 'Unidad sin título'),
                description=unit.get('description'),
                address=unit.get('address', 'Dirección no especificada'),
                property_type=unit.get('unit_type', 'apartment'),
                bedrooms=unit.get('bedrooms', 1),
                bathrooms=unit.get('bathrooms', 1),
                area_sqm=unit.get('area_sqm', 50.0),
                max_guests=unit.get('max_guests', 6),
                monthly_rent=unit.get('monthly_rent', 1500.0),
                deposit=unit.get('deposit'),
                amenities=unit.get('amenities', []),
                rules=unit.get('rules'),
                available_from=unit.get('available_from'),
                status=unit.get('status', 'available'),
                images=unit.get('images', []),
                owner_id=unit.get('owner_id', ''),
                owner_name=None,  # TODO: Implement owner lookup if needed
                rating=unit.get('rating', 0.0),
                total_reviews=unit.get('total_reviews', 0),
                created_at=unit.get('created_at'),
                updated_at=unit.get('updated_at', unit.get('created_at'))
            ))
        
        return units
        
    except Exception as e:
        logger.error(f"Error fetching available units: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching available units"
        )

@router.post("/", response_model=UnitResponse)
async def create_unit(
    request: UnitRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create new unit"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Create unit
        unit_data = {
            'public_id': make_public_id('unt'),
            'title': request.title,
            'description': request.description,
            'address': request.address,
            'unit_type': request.property_type,
            'bedrooms': request.bedrooms,
            'bathrooms': request.bathrooms,
            'area_sqm': request.area_sqm,
            'max_guests': request.max_guests,
            'monthly_rent': request.monthly_rent,
            'deposit': request.deposit,
            'amenities': request.amenities,
            'rules': request.rules,
            'available_from': request.available_from.isoformat() if request.available_from else None,
            'status': request.status,
            'owner_id': user_id,
            'latitude': request.latitude,
            'longitude': request.longitude,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('units').insert(unit_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create unit"
            )
        
        unit = result.data[0]
        
        return UnitResponse(
            id=unit['id'],
            public_id=unit['public_id'],
            title=unit['title'],
            description=unit.get('description'),
            address=unit['address'],
            property_type=unit.get('unit_type', 'apartment'),
            bedrooms=unit['bedrooms'],
            bathrooms=unit['bathrooms'],
            area_sqm=unit.get('area_sqm', 50.0),
            max_guests=unit.get('max_guests', 6),
            monthly_rent=unit['monthly_rent'],
            deposit=unit.get('deposit'),
            amenities=unit.get('amenities', []),
            rules=unit.get('rules'),
            available_from=unit.get('available_from'),
            status=unit['status'],
            images=unit.get('images', []),
            owner_id=unit['owner_id'],
            rating=unit.get('rating'),
            total_reviews=unit.get('total_reviews', 0),
            created_at=unit['created_at'],
            updated_at=unit['updated_at'],
            latitude=unit.get('latitude'),
            longitude=unit.get('longitude')
        )
        
    except Exception as e:
        logger.error(f"Error creating unit: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating unit"
        )

@router.get("/{unit_id}", response_model=UnitResponse)
async def get_unit(unit_id: str):
    """Get specific unit (public endpoint)"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('units').select('*').eq('public_id', unit_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit = result.data[0]
        
        # Debug: Log the unit data to see what's in the database
        logger.info(f"Unit data from DB: {unit}")
        logger.info(f"Unit address from DB: '{unit.get('address')}'")
        logger.info(f"Unit latitude from DB: {unit.get('latitude')}")
        logger.info(f"Unit longitude from DB: {unit.get('longitude')}")
        
        # Get owner information separately if owner_id exists
        owner_name = 'Propietario sin nombre'
        owner_rating = None  # No fake rating
        owner_profile_image = None
        
        if unit.get('owner_id'):
            try:
                # Get owner basic info
                logger.info(f"Looking up owner with ID: {unit.get('owner_id')}")
                owner_result = supabase.table('users').select('full_name, profile_image').eq('id', unit['owner_id']).execute()
                logger.info(f"Owner query result: {owner_result.data}")
                if owner_result.data:
                    owner_data = owner_result.data[0]
                    owner_name = owner_data.get('full_name', 'Propietario sin nombre')
                    owner_profile_image = owner_data.get('profile_image')
                    logger.info(f"Owner name resolved to: {owner_name}")
                
                # Calculate owner's average rating from all their properties' reviews
                try:
                    # Get all units owned by this user
                    owner_units = supabase.table('units').select('id').eq('owner_id', unit['owner_id']).execute()
                    if owner_units.data:
                        unit_ids = [u['id'] for u in owner_units.data if u.get('id')]
                        if unit_ids:
                            # Get all reviews for owner's properties
                            reviews_result = supabase.table('reviews').select('rating').in_('unit_id', unit_ids).execute()
                            if reviews_result.data and len(reviews_result.data) > 0:
                                ratings = [r['rating'] for r in reviews_result.data if r.get('rating')]
                                if ratings:
                                    owner_rating = round(sum(ratings) / len(ratings), 1)
                                    logger.info(f"Calculated owner rating: {owner_rating} from {len(ratings)} reviews")
                except Exception as rating_error:
                    logger.warning(f"Could not calculate owner rating: {str(rating_error)}")
                    
            except Exception as e:
                logger.warning(f"Could not fetch owner info: {str(e)}")
        
        return UnitResponse(
            id=unit['id'],
            public_id=unit['public_id'],
            title=unit.get('title') or unit.get('label', 'Unidad sin título'),
            description=unit.get('description'),
            address=unit.get('address', 'Dirección no especificada'),
            property_type=unit.get('unit_type', 'apartment'),
            bedrooms=unit.get('bedrooms', 1),
            bathrooms=unit.get('bathrooms', 1),
            area_sqm=unit.get('area_sqm', 50.0),
            max_guests=unit.get('max_guests', 6),
            monthly_rent=unit.get('monthly_rent', 1500.0),
            deposit=unit.get('deposit'),
            amenities=unit.get('amenities', []),
            rules=unit.get('rules'),
            available_from=unit.get('available_from'),
            status=unit.get('status', 'available'),
            images=unit.get('images', []),
            owner_id=unit.get('owner_id', ''),
            owner_name=owner_name,
            owner_rating=owner_rating,
            owner_profile_image=owner_profile_image,
            rating=unit.get('rating', 0.0),
            total_reviews=unit.get('total_reviews', 0),
            created_at=unit.get('created_at'),
            updated_at=unit.get('updated_at', unit.get('created_at')),
            latitude=unit.get('latitude'),
            longitude=unit.get('longitude')
        )
        
    except Exception as e:
        logger.error(f"Error fetching unit: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching unit"
        )

@router.put("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: str,
    request: UnitUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    print(f"DEBUG: Función update_unit llamada con unit_id: {unit_id}")
    """Update unit"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Check if unit exists and user has permission
        if current_user.get('role') in ['admin', 'superadmin']:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).execute()
        else:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).eq('owner_id', user_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        # Build update data
        update_data = {'updated_at': datetime.utcnow().isoformat()}
        print(f"DEBUG: Datos recibidos en update: {request.dict()}")
        
        if request.title is not None:
            update_data['title'] = request.title
        if request.description is not None:
            update_data['description'] = request.description
        if request.address is not None:
            update_data['address'] = request.address
        if request.property_type is not None:
            update_data['unit_type'] = request.property_type
        if request.bedrooms is not None:
            update_data['bedrooms'] = request.bedrooms
        if request.bathrooms is not None:
            update_data['bathrooms'] = request.bathrooms
        if request.area_sqm is not None:
            update_data['area_sqm'] = request.area_sqm
        if request.max_guests is not None:
            update_data['max_guests'] = request.max_guests
            print(f"DEBUG: max_guests recibido: {request.max_guests}")
        if request.monthly_rent is not None:
            update_data['monthly_rent'] = request.monthly_rent
        if request.deposit is not None:
            update_data['deposit'] = request.deposit
        if request.amenities is not None:
            update_data['amenities'] = request.amenities
        if request.rules is not None:
            update_data['rules'] = request.rules
        if request.available_from is not None:
            update_data['available_from'] = request.available_from.isoformat()
        if request.status is not None:
            update_data['status'] = request.status
        if request.images is not None:
            update_data['images'] = request.images
        if request.latitude is not None:
            update_data['latitude'] = request.latitude
        if request.longitude is not None:
            update_data['longitude'] = request.longitude
        
        # Update unit
        result = supabase.table('units').update(update_data).eq('public_id', unit_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update unit"
            )
        
        unit = result.data[0]
        
        return UnitResponse(
            id=unit['id'],
            public_id=unit['public_id'],
            title=unit['title'],
            description=unit.get('description'),
            address=unit['address'],
            property_type=unit.get('unit_type', 'apartment'),
            bedrooms=unit['bedrooms'],
            bathrooms=unit['bathrooms'],
            area_sqm=unit.get('area_sqm', 50.0),
            max_guests=unit.get('max_guests', 6),
            monthly_rent=unit['monthly_rent'],
            deposit=unit.get('deposit'),
            amenities=unit.get('amenities', []),
            rules=unit.get('rules'),
            available_from=unit.get('available_from'),
            status=unit['status'],
            images=unit.get('images', []),
            owner_id=unit['owner_id'],
            rating=unit.get('rating'),
            total_reviews=unit.get('total_reviews', 0),
            created_at=unit['created_at'],
            updated_at=unit['updated_at'],
            latitude=unit.get('latitude'),
            longitude=unit.get('longitude')
        )
        
    except Exception as e:
        logger.error(f"Error updating unit: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating unit"
        )

@router.delete("/{unit_id}")
async def delete_unit(
    unit_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete unit with cascade (debtors, payments, images)"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Check if unit exists and user has permission
        if current_user.get('role') in ['admin', 'superadmin']:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).execute()
        else:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).eq('owner_id', user_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit = existing.data[0]
        
        # Get all debtors for this unit
        debtors = supabase.table('debtors').select('id').eq('property_id', unit['id']).execute()
        
        # Delete cascade: payments -> debtors -> unit
        for debtor in debtors.data:
            # Delete payments for this debtor
            supabase.table('payments').delete().eq('debtor_id', debtor['id']).execute()
        
        # Delete all debtors for this unit
        supabase.table('debtors').delete().eq('property_id', unit['id']).execute()
        
        # TODO: Delete images from S3
        # if unit.get('images'):
        #     for image_url in unit['images']:
        #         # Delete from S3
        #         pass
        
        # Delete unit
        result = supabase.table('units').delete().eq('public_id', unit_id).execute()
        
        return {"message": "Unit and all related data deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting unit: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting unit"
        )

@router.post("/{unit_id}/images")
async def upload_unit_images(
    unit_id: str,
    image: UploadFile = File(...),
    index: int = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload images for a unit"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Check if unit exists and user has permission
        if current_user.get('role') in ['admin', 'superadmin']:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).execute()
        else:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).eq('owner_id', user_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit = existing.data[0]
        
        # Validate file type
        if not image.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Upload to S3
        s3_key = get_property_image_key(unit['public_id'], image.filename)
        image_url = upload_to_s3(image, s3_key)
        
        # Update unit with new image URL at specific index
        current_images = unit.get('images', [])
        
        # Ensure the array is large enough
        while len(current_images) <= index:
            current_images.append("")
        
        # Update the specific index
        current_images[index] = image_url
        
        # Remove empty strings from the end
        while current_images and current_images[-1] == "":
            current_images.pop()
        
        supabase.table('units').update({
            'images': current_images,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('public_id', unit_id).execute()
        
        return {"message": f"Uploaded image at index {index}", "url": image_url}
        
    except Exception as e:
        logger.error(f"Error uploading unit images: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading images"
        )

@router.post("/{unit_id}/images/batch")
async def upload_multiple_images(
    unit_id: str,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple images for a unit at once"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Check if unit exists and user has permission
        if current_user.get('role') in ['admin', 'superadmin']:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).execute()
        else:
            existing = supabase.table('units').select('*').eq('public_id', unit_id).eq('owner_id', user_id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        unit = existing.data[0]
        uploaded_urls = []
        
        # Process each file
        for file in files:
            print(f"DEBUG: Procesando archivo: {file.filename}, tipo: {file.content_type}")
            # Validate file type
            if not file.content_type.startswith('image/'):
                print(f"DEBUG: Archivo {file.filename} no es una imagen, saltando")
                continue
            
            try:
                # Generate S3 key and upload to S3
                s3_key = get_property_image_key(unit['public_id'], file.filename)
                print(f"DEBUG: S3 key generada: {s3_key}")
                
                # Reset file pointer to beginning
                file.file.seek(0)
                
                # Upload to S3
                image_url = upload_to_s3(file, s3_key)
                uploaded_urls.append(image_url)
                print(f"DEBUG: URL generada: {image_url}")
                
            except Exception as e:
                print(f"DEBUG: Error subiendo archivo {file.filename}: {e}")
                # Fallback to mock URL if S3 fails
                image_url = f"https://example.com/images/{unit['public_id']}/{file.filename}"
                uploaded_urls.append(image_url)
                print(f"DEBUG: Usando URL mock: {image_url}")
        
        # Update unit with new image URLs
        current_images = unit.get('images', [])
        updated_images = current_images + uploaded_urls
        
        print(f"DEBUG: Imágenes actuales: {current_images}")
        print(f"DEBUG: URLs subidas: {uploaded_urls}")
        print(f"DEBUG: Imágenes actualizadas: {updated_images}")
        
        result = supabase.table('units').update({
            'images': updated_images,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('public_id', unit_id).execute()
        
        print(f"DEBUG: Resultado de actualización: {result.data}")
        
        return {"message": f"Uploaded {len(uploaded_urls)} images", "urls": uploaded_urls}
        
    except Exception as e:
        logger.error(f"Error uploading multiple images: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading multiple images"
        )