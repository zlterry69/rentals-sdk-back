"""
Notifications endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
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
class NotificationResponse(BaseModel):
    id: str
    public_id: str
    title: str
    message: str
    metadata: dict
    action_url: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    type_code: str
    type_name: str
    type_icon: str
    type_color: str

class NotificationStats(BaseModel):
    total: int
    unread: int

class MarkAsReadRequest(BaseModel):
    notification_ids: List[str]

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get user notifications"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    # Debug logging
    logger.info(f"Current user payload: {current_user}")
    logger.info(f"Extracted user_id: {user_id}")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    try:
        # Build query
        query = supabase.table('notifications').select('''
            id,
            public_id,
            title,
            message,
            metadata,
            action_url,
            is_read,
            read_at,
            created_at,
            notification_types!inner(
                code,
                name,
                icon,
                color
            )
        ''').eq('user_id', user_id)
        
        # Filter unread only if requested
        if unread_only:
            query = query.eq('is_read', False)
        
        # Order and paginate
        result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        notifications = []
        for notification in result.data:
            notification_type = notification['notification_types']
            notifications.append(NotificationResponse(
                id=notification['id'],
                public_id=notification['public_id'],
                title=notification['title'],
                message=notification['message'],
                metadata=notification['metadata'] or {},
                action_url=notification['action_url'],
                is_read=notification['is_read'],
                read_at=notification['read_at'],
                created_at=notification['created_at'],
                type_code=notification_type['code'],
                type_name=notification_type['name'],
                type_icon=notification_type['icon'],
                type_color=notification_type['color']
            ))
        
        logger.info(f"Retrieved {len(notifications)} notifications for user {user_id}")
        return notifications
        
    except Exception as e:
        logger.error(f"Error fetching notifications for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching notifications"
        )

@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get notification statistics (total and unread count)"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    # Debug logging
    logger.info(f"Stats - Current user payload: {current_user}")
    logger.info(f"Stats - Extracted user_id: {user_id}")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    try:
        # Get total count
        total_result = supabase.table('notifications').select('id', count='exact').eq('user_id', user_id).execute()
        total_count = total_result.count or 0
        
        # Get unread count
        unread_result = supabase.table('notifications').select('id', count='exact').eq('user_id', user_id).eq('is_read', False).execute()
        unread_count = unread_result.count or 0
        
        stats = NotificationStats(
            total=total_count,
            unread=unread_count
        )
        
        logger.info(f"Notification stats for user {user_id}: {total_count} total, {unread_count} unread")
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching notification stats for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching notification stats"
        )

@router.put("/mark-as-read")
async def mark_notifications_as_read(
    request: MarkAsReadRequest,
    current_user: dict = Depends(get_current_user)
):
    """Mark specific notifications as read"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    try:
        if not request.notification_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No notification IDs provided"
            )
        
        # Update notifications
        result = supabase.table('notifications').update({
            'is_read': True,
            'read_at': datetime.utcnow().isoformat()
        }).in_('id', request.notification_ids).eq('user_id', user_id).execute()
        
        updated_count = len(result.data) if result.data else 0
        
        logger.info(f"Marked {updated_count} notifications as read for user {user_id}")
        return {"message": f"Marked {updated_count} notifications as read"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error marking notifications as read for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error marking notifications as read"
        )

@router.put("/mark-all-as-read")
async def mark_all_notifications_as_read(
    current_user: dict = Depends(get_current_user)
):
    """Mark all notifications as read for the current user"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    try:
        # Update all unread notifications
        result = supabase.table('notifications').update({
            'is_read': True,
            'read_at': datetime.utcnow().isoformat()
        }).eq('user_id', user_id).eq('is_read', False).execute()
        
        updated_count = len(result.data) if result.data else 0
        
        logger.info(f"Marked all {updated_count} notifications as read for user {user_id}")
        return {"message": f"Marked {updated_count} notifications as read"}
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error marking all notifications as read"
        )

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a specific notification"""
    
    supabase = get_supabase()
    user_id = current_user.get('sub')
    
    try:
        # Delete notification (only if it belongs to the user)
        result = supabase.table('notifications').delete().eq('id', notification_id).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        logger.info(f"Deleted notification {notification_id} for user {user_id}")
        return {"message": "Notification deleted successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error deleting notification {notification_id} for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting notification"
        )

@router.post("/create")
async def create_notification(
    user_id: str,
    type_code: str,
    title: str,
    message: str,
    metadata: dict = {},
    action_url: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a new notification (admin only or system use)"""
    
    supabase = get_supabase()
    
    try:
        # Get notification type
        type_result = supabase.table('notification_types').select('id').eq('code', type_code).execute()
        
        if not type_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Notification type '{type_code}' not found"
            )
        
        type_id = type_result.data[0]['id']
        
        # Create notification
        from app.utils.id_generator import make_public_id
        
        result = supabase.table('notifications').insert({
            'public_id': make_public_id('not'),
            'user_id': user_id,
            'type_id': type_id,
            'title': title,
            'message': message,
            'metadata': metadata,
            'action_url': action_url
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notification"
            )
        
        notification = result.data[0]
        logger.info(f"Created notification {notification['id']} for user {user_id}")
        
        return {"message": "Notification created successfully", "notification_id": notification['id']}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating notification"
        )
