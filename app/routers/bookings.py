"""
Bookings management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.database import get_supabase
from app.utils.auth import verify_token
from app.utils.logging import get_request_logger
from app.utils.id_generator import make_public_id

logger = get_request_logger()
router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UpdateBookingStatusRequest(BaseModel):
    status: str

class CreateBookingRequest(BaseModel):
    unit_id: str
    check_in: str
    check_out: str
    guests: int
    total_amount: float
    status: str = "BOOKING_PENDING"
    nightly_rate: float = 0.0
    cleaning_fee: float = 25.0
    service_fee: float = 15.0

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

@router.post("/")
async def create_booking(
    request: CreateBookingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new booking"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub') or current_user.get('id')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in token"
            )
        
        # Verify unit exists
        unit_result = supabase.table('units').select('id, title, owner_id').eq('public_id', request.unit_id).execute()
        if not unit_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        unit = unit_result.data[0]
        
        # Get status_id for BOOKING_PENDING
        status_result = supabase.table('process_status').select('id').eq('code', request.status).execute()
        if not status_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status {request.status} not found"
            )
        
        status_id = status_result.data[0]['id']
        
        # Calculate nights
        from datetime import datetime
        check_in_date = datetime.strptime(request.check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(request.check_out, '%Y-%m-%d').date()
        total_nights = (check_out_date - check_in_date).days
        
        # Calculate nightly rate
        nightly_rate = request.nightly_rate if request.nightly_rate > 0 else request.total_amount / total_nights if total_nights > 0 else 0
        
        # Create booking
        booking_data = {
            'public_id': make_public_id('bkg'),
            'unit_id': unit['id'],
            'guest_user_id': user_id,
            'check_in_date': request.check_in,
            'check_out_date': request.check_out,
            'guests_count': request.guests,
            'nightly_rate': nightly_rate,
            'total_nights': total_nights,
            'subtotal': nightly_rate * total_nights,
            'cleaning_fee': request.cleaning_fee,
            'service_fee': request.service_fee,
            'taxes': 0.0,
            'total_amount': request.total_amount,
            'status_id': status_id,
            'payment_status': 'PENDING',
            'booking_date': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        result = supabase.table('bookings').insert(booking_data).execute()
        
        if result.data:
            # Create notification for property owner
            try:
                # Get guest user info for notification
                guest_result = supabase.table('users').select('full_name, email').eq('id', user_id).execute()
                guest_name = guest_result.data[0]['full_name'] if guest_result.data else 'Usuario'
                
                # Create notification for property owner
                notification_data = {
                    'public_id': make_public_id('not'),
                    'user_id': unit['owner_id'],  # Notify the property owner
                    'type_id': None,  # Will be set by notification type lookup
                    'title': 'Nueva reserva recibida',
                    'message': f'{guest_name} ha realizado una nueva reserva para tu propiedad',
                    'metadata': {
                        'booking_id': result.data[0]['public_id'],
                        'guest_name': guest_name,
                        'property_title': unit['title'],
                        'check_in': request.check_in,
                        'check_out': request.check_out,
                        'total_amount': request.total_amount
                    },
                    'action_url': f'/bookings/{result.data[0]["public_id"]}',
                    'is_read': False,
                    'created_at': datetime.now().isoformat()
                }
                
                # Get notification type ID for 'new_booking'
                type_result = supabase.table('notification_types').select('id').eq('code', 'new_booking').execute()
                if type_result.data:
                    notification_data['type_id'] = type_result.data[0]['id']
                    supabase.table('notifications').insert(notification_data).execute()
                    logger.info(f"Created notification for property owner {unit['owner_id']}")
                
            except Exception as notification_error:
                logger.error(f"Error creating notification: {str(notification_error)}")
                # Don't fail the booking creation if notification fails
            
            return {
                "message": "Booking created successfully",
                "booking_id": result.data[0]['public_id']
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/users-by-property/{property_id}")
async def get_users_by_property(
    property_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get users who have bookings for a specific property"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Verify property exists and belongs to user
        property_result = supabase.table('units').select('id, title, owner_id').eq('public_id', property_id).execute()
        if not property_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )
        
        property_data = property_result.data[0]
        
        # Check if user owns this property (unless admin)
        if current_user.get('role') not in ['admin', 'superadmin']:
            if property_data['owner_id'] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this property"
                )
        
        # Get users who have bookings for this property
        result = supabase.table('bookings').select('''
            users!guest_user_id(
                id,
                public_id,
                full_name,
                email,
                phone
            )
        ''').eq('unit_id', property_data['id']).execute()
        
        # Extract unique users from bookings
        users = []
        seen_user_ids = set()
        
        for booking in result.data:
            if booking.get('users') and booking['users']['id'] not in seen_user_ids:
                users.append({
                    'id': booking['users']['id'],
                    'public_id': booking['users']['public_id'],
                    'full_name': booking['users']['full_name'],
                    'email': booking['users']['email'],
                    'phone': booking['users'].get('phone')
                })
                seen_user_ids.add(booking['users']['id'])
        
        return users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching users by property: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching users for property"
        )

@router.get("/my-bookings")
async def get_my_bookings(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Get current user's bookings"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        offset = (page - 1) * limit
        
        result = supabase.table('bookings').select('''
            *,
            units!unit_id(
                title,
                public_id,
                images
            ),
            process_status!status_id(
                code,
                description
            )
        ''').eq('guest_user_id', user_id).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "bookings": result.data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(result.data)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching user bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching bookings"
        )

@router.get("/received")
async def get_received_bookings(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Get bookings received by current user (as property owner)"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        offset = (page - 1) * limit
        
        # Primero obtener las unidades del usuario
        units_result = supabase.table('units').select('id').eq('owner_id', user_id).execute()
        unit_ids = [unit['id'] for unit in units_result.data]
        
        if not unit_ids:
            return {
                "bookings": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0
                }
            }
        
        # Luego obtener las reservas de esas unidades
        result = supabase.table('bookings').select('''
            *,
            units!unit_id(
                title,
                public_id,
                owner_id,
                images
            ),
            process_status!status_id(
                code,
                description
            ),
            users!guest_user_id(
                full_name,
                email
            )
        ''').in_('unit_id', unit_ids).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "bookings": result.data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(result.data)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching received bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching received bookings"
        )

@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    request: UpdateBookingStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update booking status"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Status mapping
        status_mapping = {
            'PENDING': 'BOOKING_PENDING',
            'APPROVED': 'BOOKING_CONFIRMED',
            'REJECTED': 'BOOKING_CANCELLED',
            'CONFIRMED': 'BOOKING_CONFIRMED',
            'CANCELLED': 'BOOKING_CANCELLED',
            'COMPLETED': 'BOOKING_COMPLETED',
            'IN_PROGRESS': 'BOOKING_CONFIRMED'
        }
        
        status_code = status_mapping.get(request.status, request.status)
        
        # Get status_id from process_status table
        status_result = supabase.table('process_status').select('id').eq('code', status_code).execute()
        if not status_result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {request.status}"
            )
        
        status_id = status_result.data[0]['id']
        
        # Get booking to verify ownership using public_id
        booking_result = supabase.table('bookings').select('*, units!unit_id(owner_id)').eq('public_id', booking_id).execute()
        if not booking_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        booking = booking_result.data[0]
        unit_owner_id = booking['units']['owner_id']
        
        # Check if user owns the property
        if unit_owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update booking status
        update_data = {
            'status_id': status_id,
            'updated_at': datetime.now().isoformat()
        }
        
        # Set confirmed_at if confirming
        if status_code == 'BOOKING_CONFIRMED':
            update_data['confirmed_at'] = datetime.now().isoformat()
        
        # Set cancelled_at if cancelling
        if status_code == 'BOOKING_CANCELLED':
            update_data['cancelled_at'] = datetime.now().isoformat()
        
        result = supabase.table('bookings').update(update_data).eq('public_id', booking_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update booking status"
            )
        
        # If confirming booking, create/update debtor record
        if status_code == 'BOOKING_CONFIRMED':
            try:
                # Get guest info
                guest_result = supabase.table('users').select('full_name, email, phone').eq('id', booking['guest_user_id']).execute()
                if guest_result.data:
                    guest_info = guest_result.data[0]
                    
                    # Get property info
                    property_result = supabase.table('units').select('monthly_rent').eq('id', booking['unit_id']).execute()
                    property_data = property_result.data[0] if property_result.data else {}
                    
                    # Check if debtor already exists
                    existing_debtor = supabase.table('debtors').select('id, monthly_rent, debt_amount').eq('property_id', booking['unit_id']).eq('email', guest_info['email']).eq('owner_id', user_id).execute()
                    
                    if existing_debtor.data:
                        # Update existing debtor
                        debtor_update = {
                            'monthly_rent': property_data.get('monthly_rent', 0),
                            'debt_amount': existing_debtor.data[0].get('debt_amount', 0),
                            'status': 'current',
                            'name': guest_info.get('full_name', 'Unknown'),
                            'updated_at': datetime.now().isoformat()
                        }
                        
                        supabase.table('debtors').update(debtor_update).eq('id', existing_debtor.data[0]['id']).execute()
                    else:
                        # Create new debtor
                        debtor_data = {
                            'public_id': make_public_id('deb'),
                            'name': guest_info.get('full_name', 'Unknown'),
                            'full_name': guest_info.get('full_name', 'Unknown'),
                            'email': guest_info['email'],
                            'phone': guest_info.get('phone'),
                            'property_id': booking['unit_id'],
                            'monthly_rent': property_data.get('monthly_rent', 0),
                            'debt_amount': property_data.get('monthly_rent', 0),
                            'status': 'current',
                            'owner_id': user_id,
                            'created_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }
                        
                        supabase.table('debtors').insert(debtor_data).execute()
                        
            except Exception as e:
                logger.error(f"Error creating/updating debtor record for booking {booking_id}: {str(e)}")
                # Don't fail the booking update if debtor creation fails
        
        return {"message": "Booking status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating booking status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating booking status"
        )

@router.delete("/{booking_id}")
async def delete_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a booking"""
    try:
        supabase = get_supabase()
        user_id = current_user.get('sub')
        
        # Get booking to verify ownership using public_id
        booking_result = supabase.table('bookings').select('*, units!unit_id(owner_id)').eq('public_id', booking_id).execute()
        if not booking_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        booking = booking_result.data[0]
        unit_owner_id = booking['units']['owner_id']
        guest_user_id = booking['guest_user_id']
        
        # Check if user is either the guest or the property owner
        if guest_user_id != user_id and unit_owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete booking using public_id
        result = supabase.table('bookings').delete().eq('public_id', booking_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete booking"
            )
        
        return {"message": "Booking deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting booking"
        )