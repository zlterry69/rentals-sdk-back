"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from passlib.context import CryptContext
from app.config import settings
from app.database import get_supabase
from app.utils.auth import create_access_token, get_password_hash, verify_password, verify_token
from app.utils.logging import get_request_logger
from app.utils.id_generator import make_public_id
from app.services.s3_service import s3_service

logger = get_request_logger()

router = APIRouter()
security = HTTPBearer()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper function for FastAPI dependency
def get_user_id_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token for FastAPI dependency"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return user_id

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: str
    public_id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "user"
    created_by: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    profile_image: Optional[str] = None
    date_of_birth: Optional[str] = None  # DATE se convierte a string
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login user"""
    supabase = get_supabase()
    
    try:
        # Find user by email
        result = supabase.table('users').select('*').eq('email', request.email).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = result.data[0]
        
        # Verify password
        if not verify_password(request.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token = create_access_token(data={
            "sub": user['id'],
            "email": user['email'],
            "role": user['role']
        })
        
        # Remove password from response
        user_data = {k: v for k, v in user.items() if k != 'password_hash'}
        
        return LoginResponse(
            access_token=access_token,
            user=user_data
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """Register new user (can rent properties AND list their own properties)"""
    supabase = get_supabase()
    
    try:
        # Check if user already exists
        existing = supabase.table('users').select('id').eq('email', request.email).execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password
        password_hash = get_password_hash(request.password)
        
        # Generate public_id
        from app.utils.id_generator import make_public_id
        public_id = make_public_id('usr')
        
        # Create user (default role: user - can be both tenant and owner)
        user_data = {
            'public_id': public_id,
            'email': request.email,
            'password_hash': password_hash,
            'full_name': request.name,
            'phone': request.phone,
            'role': 'user',  # Default role: can rent AND list properties
            'is_active': True,
            'is_verified': False  # Require email verification
        }
        
        result = supabase.table('users').insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        user = result.data[0]
        
        # Create access token
        access_token = create_access_token(data={
            "sub": user['id'],
            "email": user['email'],
            "role": user['role']
        })
        
        # Remove password from response
        user_response = {k: v for k, v in user.items() if k != 'password_hash'}
        
        return LoginResponse(
            access_token=access_token,
            user=user_response
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/refresh")
async def refresh_token(user_id: str = Depends(get_user_id_from_token)):
    """Refresh access token"""
    try:
        # Get user data from database
        supabase = get_supabase()
        result = supabase.table('users').select('email, role').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = result.data[0]
        
        # Create new access token with role
        access_token = create_access_token(data={
            "sub": user_id,
            "email": user['email'],
            "role": user['role']
        })
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(user_id: str = Depends(get_user_id_from_token)):
    """Logout user (client-side token removal)"""
    return {"message": "Logged out successfully"}


# Admin Management Endpoints
class CreateAdminRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    phone: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None  # URL to image
    date_of_birth: Optional[str] = None  # YYYY-MM-DD format
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile information"""
    try:
        supabase = get_supabase()
        
        # Get user by ID from token
        user_id = current_user.get('sub')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Fetch user from database
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = result.data[0]
        
        # Update last_login
        supabase.table('users').update({
            'last_login': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        return UserResponse(
            id=user_data['id'],
            public_id=user_data['public_id'],
            email=user_data['email'],
            username=user_data.get('username'),
            full_name=user_data.get('full_name', ''),
            phone=user_data.get('phone'),
            address=user_data.get('address'),
            date_of_birth=user_data.get('date_of_birth'),
            emergency_contact=user_data.get('emergency_contact'),
            emergency_contact_name=user_data.get('emergency_contact_name'),
            emergency_contact_phone=user_data.get('emergency_contact_phone'),
            profile_image=user_data.get('profile_image'),
            role=user_data.get('role', 'user'),
            is_active=user_data.get('is_active', True),
            is_verified=user_data.get('is_verified', False),
            created_at=user_data['created_at'],
            updated_at=user_data['updated_at']
        )
        
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile"
        )

@router.post("/admin/create", response_model=UserResponse)
async def create_admin(
    request: CreateAdminRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create new admin (ONLY superadmin can do this)"""
    
    # Only superadmin can create admins
    if current_user.get('role') != 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can create administrators"
        )
    
    supabase = get_supabase()
    
    try:
        # Check if user already exists
        existing = supabase.table('users').select('id').eq('email', request.email).execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password
        password_hash = get_password_hash(request.password)
        
        # Generate public_id
        from app.utils.id_generator import make_public_id
        public_id = make_public_id('usr')
        
        # Create admin user
        user_data = {
            'public_id': public_id,
            'email': request.email,
            'username': request.username,
            'password_hash': password_hash,
            'full_name': request.full_name,
            'phone': request.phone,
            'role': 'admin',  # Admin role
            'is_active': True,
            'is_verified': True,  # Admins are pre-verified
            'created_by': current_user.get('sub')  # Track who created this admin
        }
        
        result = supabase.table('users').insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create admin"
            )
        
        # Remove password from response
        user_response = {k: v for k, v in result.data[0].items() if k != 'password_hash'}
        
        return UserResponse(**user_response)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin creation failed"
        )

@router.delete("/admin/{user_id}")
async def delete_admin(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete admin (with hierarchy protection)"""
    
    supabase = get_supabase()
    
    try:
        # Get target user
        target_user = supabase.table('users').select('*').eq('public_id', user_id).execute()
        
        if not target_user.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        target = target_user.data[0]
        current_role = current_user.get('role')
        current_id = current_user.get('sub')
        
        # Protection rules:
        # 1. Cannot delete superadmin
        if target['role'] == 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete superadmin"
            )
        
        # 2. Only superadmin can delete admins
        if target['role'] == 'admin' and current_role != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superadmin can delete administrators"
            )
        
        # 3. Cannot delete yourself
        if target['id'] == current_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete your own account"
            )
        
        # 4. Admins can only delete users they created or regular users
        if current_role == 'admin':
            if target['role'] == 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot delete other admins"
                )
            # Can delete regular users
        
        # Perform deletion
        result = supabase.table('users').delete().eq('id', target['id']).execute()
        
        return {"message": f"User {target['full_name']} deleted successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    emergency_contact: Optional[str] = Form(None),
    emergency_contact_name: Optional[str] = Form(None),
    emergency_contact_phone: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Update user profile (text data and/or image)"""
    
    # Debug: Log received data
    logger.info(f"Profile update request received:")
    logger.info(f"  full_name: {full_name}")
    logger.info(f"  phone: {phone}")
    logger.info(f"  address: {address}")
    logger.info(f"  date_of_birth: {date_of_birth}")
    logger.info(f"  emergency_contact: {emergency_contact}")
    logger.info(f"  emergency_contact_name: {emergency_contact_name}")
    logger.info(f"  emergency_contact_phone: {emergency_contact_phone}")
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    try:
        # Build update data
        update_data = {}
        
        if full_name is not None:
            update_data['full_name'] = full_name
        if phone is not None:
            update_data['phone'] = phone
        if address is not None:
            update_data['address'] = address
        if date_of_birth is not None:
            update_data['date_of_birth'] = date_of_birth
        if emergency_contact is not None:
            update_data['emergency_contact'] = emergency_contact
        if emergency_contact_name is not None:
            update_data['emergency_contact_name'] = emergency_contact_name
        if emergency_contact_phone is not None:
            update_data['emergency_contact_phone'] = emergency_contact_phone
        
        # Debug: Log update data
        logger.info(f"Update data to be saved: {update_data}")
        
        # Handle image upload/removal if provided
        if profile_image is not None:
            if profile_image.filename:  # New image uploaded
                # Validate file type
                allowed_types = ['image/jpeg', 'image/png', 'image/webp']
                if profile_image.content_type not in allowed_types:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Only JPEG, PNG, and WebP images are allowed"
                    )
                
                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024  # 5MB
                file_content = await profile_image.read()
                if len(file_content) > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File size must be less than 5MB"
                    )
                
                # Upload to S3
                s3_url = await s3_service.upload_profile_image(
                    user_id=user_id,
                    file_content=file_content,
                    original_filename=profile_image.filename,
                    content_type=profile_image.content_type
                )
                
                if not s3_url:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to upload image to S3"
                    )
                
                update_data['profile_image'] = s3_url
                logger.info(f"Profile image uploaded: {s3_url}")
            else:  # Empty filename means remove image
                update_data['profile_image'] = None
                logger.info("Profile image removed")
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Add updated timestamp
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update user
        result = supabase.table('users').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove password from response
        user_response = {k: v for k, v in result.data[0].items() if k != 'password_hash'}
        
        logger.info(f"Profile updated successfully for user {user_id}")
        
        return UserResponse(**user_response)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Profile update failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )

@router.post("/validate-password")
async def validate_password(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Validate current password for real-time verification"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    current_password = request.get('current_password')
    
    if not current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is required"
        )
    
    try:
        # Get user from database
        result = supabase.table('users').select('password_hash').eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = result.data[0]
        
        # Verify current password
        if not pwd_context.verify(current_password, user_data['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return {"valid": True, "message": "Password is correct"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Password validation failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password validation failed"
        )

@router.put("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Change user password"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    try:
        # Get current user data
        user_result = supabase.table('users').select('password_hash').eq('id', user_id).execute()
        
        if not user_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        current_hash = user_result.data[0]['password_hash']
        
        # Verify current password
        if not verify_password(request.current_password, current_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_hash = get_password_hash(request.new_password)
        
        # Update password
        result = supabase.table('users').update({
            'password_hash': new_hash,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        return {"message": "Password updated successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.post("/upload-profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload profile image to S3 and update user profile"""
    from app.utils.s3_folders import get_profile_image_key
    from app.utils.s3 import upload_file_to_s3
    import uuid
    import os
    
    try:
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPEG, PNG and WebP images are allowed"
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must be less than 5MB"
            )
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Generate S3 key
        user_id = current_user.get('sub')
        s3_key = get_profile_image_key(user_id, unique_filename)
        
        # Upload to S3
        file_url = await upload_file_to_s3(file_content, s3_key, file.content_type)
        
        # Update user profile with new image URL
        supabase = get_supabase()
        result = supabase.table('users').update({
            'profile_image': file_url,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile image"
            )
        
        return {
            "message": "Profile image uploaded successfully",
            "image_url": file_url
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload profile image"
        )

# New user management endpoints
@router.put("/admin/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Deactivate user (admins can deactivate other admins, superadmin can deactivate anyone)"""
    supabase = get_supabase()
    current_user_role = current_user.get('role')
    current_user_id = current_user.get('sub')
    
    try:
        # Get target user
        target_user = supabase.table('users').select('id, role, is_active').eq('public_id', user_id).execute()
        if not target_user.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        target = target_user.data[0]
        
        # Role-based permissions
        if current_user_role == 'admin':
            # Admins can only deactivate other admins and users, not superadmins
            if target['role'] == 'superadmin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot deactivate superadmins"
                )
        elif current_user_role == 'user':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Users cannot deactivate other users"
            )
        
        # Prevent self-deactivation
        if target['id'] == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot deactivate your own account"
            )
        
        # Deactivate user
        result = supabase.table('users').update({
            'is_active': False,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', target['id']).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )
        
        return {"message": f"User {user_id} deactivated successfully"}
        
    except Exception as e:
        logger.error(f"User deactivation error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deactivation failed"
        )

@router.put("/admin/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Activate user (admins and superadmins can activate users)"""
    supabase = get_supabase()
    current_user_role = current_user.get('role')
    
    if current_user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and superadmins can activate users"
        )
    
    try:
        # Get target user
        target_user = supabase.table('users').select('id, role, is_active').eq('public_id', user_id).execute()
        if not target_user.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        target = target_user.data[0]
        
        # Activate user
        result = supabase.table('users').update({
            'is_active': True,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', target['id']).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate user"
            )
        
        return {"message": f"User {user_id} activated successfully"}
        
    except Exception as e:
        logger.error(f"User activation error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User activation failed"
        )

@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None
):
    """Get all users (admins and superadmins only)"""
    supabase = get_supabase()
    current_user_role = current_user.get('role')
    
    if current_user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and superadmins can view all users"
        )
    
    try:
        # Build query
        query = supabase.table('users').select('*')
        
        
        # Apply filters
        if role_filter:
            query = query.eq('role', role_filter)
        if status_filter == 'active':
            query = query.eq('is_active', True)
        elif status_filter == 'inactive':
            query = query.eq('is_active', False)
        
        result = query.range(skip, skip + limit - 1).execute()
        print(f"🔍 DEBUG: Resultado de la consulta: {result.data}")
        users = []
        for user in result.data:
            users.append(UserResponse(
                id=user['id'],
                public_id=user['public_id'],
                email=user['email'],
                username=user.get('username'),
                full_name=user.get('full_name'),
                phone=user.get('phone'),
                address=user.get('address'),
                date_of_birth=user.get('date_of_birth'),
                emergency_contact=user.get('emergency_contact'),
                profile_image=user.get('profile_image'),
                role=user.get('role', 'user'),
                created_by=user.get('created_by'),
                is_active=user.get('is_active', True),
                is_verified=user.get('is_verified', False),
                last_login=user.get('last_login'),
                created_at=user['created_at'],
                updated_at=user['updated_at']
            ))
        
        return users
        
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching users"
        )
