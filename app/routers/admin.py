from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional
import structlog
from datetime import datetime

from app.database import get_supabase
from app.utils.auth import get_user_id_from_token

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserResponse(BaseModel):
    id: str
    public_id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str] = None

class UserStats(BaseModel):
    total: int
    active: int
    inactive: int
    users: int
    admins: int
    superadmins: int

class UsersListResponse(BaseModel):
    users: List[UserResponse]
    stats: UserStats

class UpdateUserStatusRequest(BaseModel):
    is_active: bool

class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(user|admin|superadmin)$")

class CreateUserRequest(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = Field(default="user", pattern="^(user|admin|superadmin)$")
    password: str = Field(..., min_length=6)

# Dependency to get current user with admin check
async def get_current_admin_user(token: str = Depends(security)):
    """Get current user and verify admin/superadmin role"""
    try:
        user_id = get_user_id_from_token(token.credentials)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        supabase = get_supabase()
        
        # Get user info including role
        user_response = supabase.table("users").select(
            "id, public_id, email, username, full_name, role"
        ).eq("id", user_id).single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        user = user_response.data
        
        # Check if user is admin or superadmin
        if user['role'] not in ['admin', 'superadmin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado. Se requieren permisos de administrador."
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting current admin user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

def can_manage_user(current_user: dict, target_user: dict) -> bool:
    """Check if current user can manage target user based on roles"""
    current_role = current_user['role']
    target_role = target_user['role']
    
    # Superadmin can manage everyone
    if current_role == 'superadmin':
        return True
    
    # Admin can only manage users (not other admins or superadmins)
    if current_role == 'admin' and target_role == 'user':
        return True
    
    return False

@router.get("/users", response_model=UsersListResponse)
async def get_users(
    role: Optional[str] = None,
    active_only: Optional[bool] = None,
    current_user: dict = Depends(get_current_admin_user)
):
    """Get all users with stats (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        current_role = current_user.get('role', 'user')
        
        # Build query with optional role filter
        query = supabase.table("users").select(
            "id, public_id, email, username, full_name, phone, profile_image, role, is_active, is_verified, created_at, last_login"
        )
        
        # Apply role-based filtering
        if current_role == 'admin':
            # Admin can see users and admins (not superadmins)
            query = query.in_("role", ["user", "admin"])
        elif current_role == 'superadmin':
            # Superadmin can see everyone
            pass
        else:
            # Regular users shouldn't access this endpoint
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado"
            )
        
        # Apply role filter if provided
        if role:
            query = query.eq("role", role)
        
        # Apply active filter if provided
        if active_only is not None:
            query = query.eq("is_active", active_only)
        
        users_response = query.order("created_at", desc=True).execute()
        
        if not users_response.data:
            users_data = []
        else:
            users_data = users_response.data
        
        # Calculate stats
        total = len(users_data)
        active = len([u for u in users_data if u['is_active']])
        inactive = total - active
        users_count = len([u for u in users_data if u['role'] == 'user'])
        admins_count = len([u for u in users_data if u['role'] == 'admin'])
        superadmins_count = len([u for u in users_data if u['role'] == 'superadmin'])
        
        stats = UserStats(
            total=total,
            active=active,
            inactive=inactive,
            users=users_count,
            admins=admins_count,
            superadmins=superadmins_count
        )
        
        # Convert to response format
        users_list = []
        for user in users_data:
            # Filter users based on permissions
            if current_user['role'] == 'admin' and user['role'] in ['admin', 'superadmin']:
                # Admin can see other admins/superadmins but with limited info
                if user['id'] != current_user['id']:  # Don't hide self
                    continue
            
            users_list.append(UserResponse(
                id=user['id'],
                public_id=user['public_id'] or '',
                email=user['email'],
                username=user['username'],
                full_name=user['full_name'],
                phone=user['phone'],
                profile_image=user.get('profile_image'),
                role=user['role'],
                is_active=user['is_active'],
                is_verified=user['is_verified'],
                created_at=user['created_at'],
                last_login=user['last_login']
            ))
        
        return UsersListResponse(users=users_list, stats=stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching users", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener usuarios"
        )

@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: UpdateUserStatusRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """Update user active status (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        
        # Get target user
        target_user_response = supabase.table("users").select(
            "id, role, email"
        ).eq("id", user_id).single().execute()
        
        if not target_user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        target_user = target_user_response.data
        
        # Check permissions
        if not can_manage_user(current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para gestionar este usuario"
            )
        
        # Prevent self-deactivation
        if target_user['id'] == current_user['id'] and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivarte a ti mismo"
            )
        
        # Update user status
        update_response = supabase.table("users").update({
            "is_active": request.is_active,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al actualizar el estado del usuario"
            )
        
        action = "activado" if request.is_active else "desactivado"
        logger.info(f"User status updated", 
                   admin_user=current_user['email'],
                   target_user=target_user['email'],
                   action=action)
        
        return {"message": f"Usuario {action} correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el estado del usuario"
        )

@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """Update user role (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        
        # Get target user
        target_user_response = supabase.table("users").select(
            "id, role, email"
        ).eq("id", user_id).single().execute()
        
        if not target_user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        target_user = target_user_response.data
        
        # Check permissions for role changes
        if current_user['role'] == 'admin':
            # Admin can only promote users to admin, not to superadmin
            if target_user['role'] != 'user':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puedes cambiar el rol de usuarios regulares"
                )
            if request.role == 'superadmin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes asignar el rol de superadmin"
                )
        
        # Prevent self-role change to lower privilege
        if target_user['id'] == current_user['id']:
            current_role_hierarchy = {'user': 1, 'admin': 2, 'superadmin': 3}
            if current_role_hierarchy[request.role] < current_role_hierarchy[current_user['role']]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes reducir tu propio nivel de privilegios"
                )
        
        # Update user role
        update_response = supabase.table("users").update({
            "role": request.role,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al actualizar el rol del usuario"
            )
        
        logger.info(f"User role updated", 
                   admin_user=current_user['email'],
                   target_user=target_user['email'],
                   old_role=target_user['role'],
                   new_role=request.role)
        
        return {"message": f"Rol actualizado a {request.role} correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user role", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el rol del usuario"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """Delete user (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        
        # Get target user
        target_user_response = supabase.table("users").select(
            "id, role, email"
        ).eq("id", user_id).single().execute()
        
        if not target_user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        target_user = target_user_response.data
        
        # Check permissions
        if not can_manage_user(current_user, target_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para eliminar este usuario"
            )
        
        # Prevent self-deletion
        if target_user['id'] == current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes eliminarte a ti mismo"
            )
        
        # Delete user (cascade will handle related data)
        delete_response = supabase.table("users").delete().eq("id", user_id).execute()
        
        if not delete_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al eliminar el usuario"
            )
        
        logger.info(f"User deleted", 
                   admin_user=current_user['email'],
                   deleted_user=target_user['email'],
                   deleted_role=target_user['role'])
        
        return {"message": "Usuario eliminado correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el usuario"
        )

@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """Create new user (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        
        # Check permissions for role assignment
        if current_user['role'] == 'admin' and request.role in ['admin', 'superadmin']:
            if request.role == 'superadmin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes crear usuarios con rol superadmin"
                )
        
        # Check if email already exists
        existing_user = supabase.table("users").select("id").eq("email", request.email).execute()
        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con este email"
            )
        
        # Check if username already exists (if provided)
        if request.username:
            existing_username = supabase.table("users").select("id").eq("username", request.username).execute()
            if existing_username.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un usuario con este username"
                )
        
        # Hash password
        from app.utils.auth import get_password_hash
        hashed_password = get_password_hash(request.password)
        
        # Generate public_id
        import uuid
        public_id = f"usr_{uuid.uuid4().hex[:10]}"
        
        # Create user
        user_data = {
            "public_id": public_id,
            "email": request.email,
            "username": request.username,
            "full_name": request.full_name,
            "phone": request.phone,
            "role": request.role,
            "password_hash": hashed_password,
            "is_active": True,
            "is_verified": False,
            "created_by": current_user['id'],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        create_response = supabase.table("users").insert(user_data).execute()
        
        if not create_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al crear el usuario"
            )
        
        created_user = create_response.data[0]
        
        logger.info(f"User created", 
                   admin_user=current_user['email'],
                   created_user=created_user['email'],
                   created_role=created_user['role'])
        
        return {
            "message": "Usuario creado correctamente",
            "user": UserResponse(
                id=created_user['id'],
                public_id=created_user['public_id'],
                email=created_user['email'],
                username=created_user['username'],
                full_name=created_user['full_name'],
                phone=created_user['phone'],
                role=created_user['role'],
                is_active=created_user['is_active'],
                is_verified=created_user['is_verified'],
                created_at=created_user['created_at'],
                last_login=created_user.get('last_login')
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el usuario"
        )

class UpdateUserRequest(BaseModel):
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = Field(..., pattern="^(user|admin|superadmin)$")
    is_active: bool = True
    is_verified: bool = False
    password: Optional[str] = Field(None, min_length=6)

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """Update user (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        
        # Get target user
        target_user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not target_user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        target_user = target_user_response.data[0]
        
        # Check permissions
        if current_user['role'] == 'admin' and target_user['role'] in ['admin', 'superadmin']:
            if target_user['role'] == 'superadmin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes editar usuarios con rol superadmin"
                )
        
        # Check role assignment permissions
        if current_user['role'] == 'admin' and request.role in ['admin', 'superadmin']:
            if request.role == 'superadmin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No puedes asignar rol superadmin"
                )
        
        # Check if email already exists (excluding current user)
        if request.email != target_user['email']:
            existing_user = supabase.table("users").select("id").eq("email", request.email).neq("id", user_id).execute()
            if existing_user.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un usuario con este email"
                )
        
        # Check if username already exists (if provided and different)
        if request.username and request.username != target_user.get('username'):
            existing_username = supabase.table("users").select("id").eq("username", request.username).neq("id", user_id).execute()
            if existing_username.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un usuario con este username"
                )
        
        # Prepare update data
        update_data = {
            "email": request.email,
            "username": request.username,
            "full_name": request.full_name,
            "phone": request.phone,
            "role": request.role,
            "is_active": request.is_active,
            "is_verified": request.is_verified,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Update password if provided
        if request.password:
            from app.utils.auth import get_password_hash
            update_data["password_hash"] = get_password_hash(request.password)
        
        # Update user
        update_response = supabase.table("users").update(update_data).eq("id", user_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al actualizar el usuario"
            )
        
        updated_user = update_response.data[0]
        
        logger.info(f"User updated", 
                   admin_user=current_user['email'],
                   updated_user=updated_user['email'],
                   updated_role=updated_user['role'])
        
        return {
            "message": "Usuario actualizado correctamente",
            "user": UserResponse(
                id=updated_user['id'],
                public_id=updated_user['public_id'],
                email=updated_user['email'],
                username=updated_user['username'],
                full_name=updated_user['full_name'],
                phone=updated_user['phone'],
                role=updated_user['role'],
                is_active=updated_user['is_active'],
                is_verified=updated_user['is_verified'],
                created_at=updated_user['created_at'],
                last_login=updated_user.get('last_login')
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el usuario"
        )

@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """Get user details (admin/superadmin only)"""
    try:
        supabase = get_supabase()
        
        # Get target user
        target_user_response = supabase.table("users").select(
            "id, public_id, email, username, full_name, phone, profile_image, role, is_active, is_verified, created_at, last_login, address, date_of_birth, emergency_contact"
        ).eq("id", user_id).single().execute()
        
        if not target_user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        target_user = target_user_response.data
        
        # Check permissions (admins can view other admins but not edit)
        if current_user['role'] == 'admin' and target_user['role'] == 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver este usuario"
            )
        
        return UserResponse(
            id=target_user['id'],
            public_id=target_user['public_id'] or '',
            email=target_user['email'],
            username=target_user['username'],
            full_name=target_user['full_name'],
            phone=target_user['phone'],
            profile_image=target_user.get('profile_image'),
            role=target_user['role'],
            is_active=target_user['is_active'],
            is_verified=target_user['is_verified'],
            created_at=target_user['created_at'],
            last_login=target_user['last_login']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching user details", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener detalles del usuario"
        )
